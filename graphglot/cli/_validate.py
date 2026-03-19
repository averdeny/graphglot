"""CLI command: validate."""

from __future__ import annotations

import json

from pathlib import Path

import click

from graphglot.cli._shared import console, dialect_option, output_option, query_options, read_query


@click.command(name="validate")
@query_options
@dialect_option()
@output_option()
def validate_cmd(
    query_or_file: str | None,
    query: str | None,
    file_: Path | None,
    dialect: str,
    output_format: str,
):
    """Validate a query and report required GQL features."""
    from graphglot.dialect import Dialect

    query_text = read_query(query=query, file_path=file_, query_or_file=query_or_file)
    d = Dialect.get_or_raise(dialect or None)
    result = d.validate(query_text)

    if output_format.lower() == "json":
        data = {
            "success": result.success,
            "stage": result.stage,
            "features": sorted(f.id for f in result.features),
            "diagnostics": [
                {
                    "code": diag.code,
                    "message": diag.message,
                    "severity": diag.severity.value,
                    "phase": diag.phase,
                    "line": diag.span.start_line if diag.span else None,
                    "col": diag.span.start_column if diag.span else None,
                    "highlight": diag.highlight,
                }
                for diag in result.all_diagnostics
            ],
        }
        click.echo(json.dumps(data, indent=2))
    else:
        _print_validate_pretty(result)

    if not result.success:
        raise SystemExit(1)


def _print_validate_pretty(result):
    """Print validation result in a human-readable format."""
    from graphglot.cli._shared import print_diagnostics

    console.print()

    if result.success:
        console.print("[green]Valid[/green]")
    else:
        console.print(f"[red]Failed[/red] at stage: [bold]{result.stage}[/bold]")
        print_diagnostics(result)

    if result.features:
        from rich.table import Table

        console.print()
        table = Table(title="Required Features")
        table.add_column("ID", style="bold")
        table.add_column("Description")

        for f in sorted(result.features, key=lambda f: f.id):
            table.add_row(f.id, f.description)

        console.print(table)

    console.print()
