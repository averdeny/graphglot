"""CLI command: type."""

from __future__ import annotations

import json
import typing as t

from pathlib import Path

import click

from graphglot.cli._shared import (
    console,
    dialect_option,
    output_option,
    print_diagnostics,
    query_options,
    read_query,
)


@click.command(name="type")
@query_options
@dialect_option()
@output_option()
def type_cmd(
    query_or_file: str | None,
    query: str | None,
    file_: Path | None,
    dialect: str,
    output_format: str,
):
    """Run type inference and display inferred types for RETURN expressions."""
    from graphglot.ast.expressions import ReturnItem, ReturnStatementBody
    from graphglot.dialect import Dialect
    from graphglot.error import format_diagnostic
    from graphglot.typing.annotator import TypeAnnotator

    query_text = read_query(query=query, file_path=file_, query_or_file=query_or_file)
    dialect_obj = Dialect.get_or_raise(dialect or None)

    # Validate + parse
    validation = dialect_obj.validate(query_text)
    if not validation.success:
        if output_format.lower() == "json":
            errors = [
                format_diagnostic(diag, validation.query, ansi=False)
                for diag in validation.all_diagnostics
            ]
            if validation.error and not errors:
                errors = [str(validation.error)]
            click.echo(json.dumps({"ok": False, "errors": errors}))
        else:
            console.print(f"[red]Failed[/red] at stage: [bold]{validation.stage}[/bold]")
            print_diagnostics(validation)
        raise SystemExit(1)

    # Transform + annotate
    expressions = dialect_obj.transform(validation.expressions)
    annotator = TypeAnnotator(dialect=dialect_obj)
    annotation = annotator.annotate(expressions[0])

    # Extract return items
    fields: list[dict[str, str]] = []
    for i, item_ in enumerate(expressions[0].find_all(ReturnItem), 1):
        item = t.cast(ReturnItem, item_)
        expr_text = dialect_obj.generate(item.aggregating_value_expression, copy=False)
        alias = item.return_item_alias.identifier.name if item.return_item_alias else None
        resolved = item.aggregating_value_expression._resolved_type
        type_str = repr(resolved) if resolved else "UNKNOWN"
        fields.append(
            {
                "position": str(i),
                "expression": expr_text,
                "alias": alias or "",
                "type": type_str,
            }
        )

    # Detect RETURN * only when no return items were found
    has_star = False
    if not fields:
        for rsb_ in expressions[0].find_all(ReturnStatementBody):
            rsb = t.cast(ReturnStatementBody, rsb_)
            body = rsb.return_statement_body
            if isinstance(body, ReturnStatementBody._SetQuantifierAsteriskGroupByClause):
                has_star = True
                break

    if output_format.lower() == "json":
        json_fields = [
            {
                "position": int(f["position"]),
                "expression": f["expression"],
                "alias": f["alias"] or None,
                "type": f["type"],
            }
            for f in fields
        ]
        data = {
            "ok": annotation.ok,
            "fields": json_fields,
            "diagnostics": [
                {"message": d.message, "severity": d.severity.value} for d in annotation.diagnostics
            ],
        }
        click.echo(json.dumps(data, indent=2))
    else:
        from rich.table import Table

        console.print()

        if fields:
            table = Table(title="Inferred Types")
            table.add_column("#", justify="right", style="dim")
            table.add_column("Expression")
            table.add_column("Alias")
            table.add_column("Inferred Type", style="bold")

            for f in fields:
                table.add_row(
                    f["position"],
                    f["expression"],
                    f["alias"] or "-",
                    f["type"],
                )

            console.print(table)
        elif has_star:
            console.print(
                "[dim]RETURN * — individual types not available for star projection[/dim]"
            )
        else:
            console.print("[dim]No RETURN items found.[/dim]")

        if annotation.diagnostics:
            console.print()
            for d in annotation.diagnostics:
                console.print(f"  [{d.severity.value}] {d.message}")

        console.print(f"\n  Annotated {annotation.annotated_count} nodes", style="dim")
        console.print()
