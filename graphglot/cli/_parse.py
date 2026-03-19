"""CLI command: parse."""

from __future__ import annotations

import json

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


@click.command(name="parse")
@query_options
@dialect_option()
@output_option()
def parse_cmd(
    query_or_file: str | None,
    query: str | None,
    file_: Path | None,
    dialect: str,
    output_format: str,
):
    """Check whether a query parses successfully (pass/fail)."""
    from graphglot.dialect import Dialect
    from graphglot.error import format_diagnostic

    query_text = read_query(query=query, file_path=file_, query_or_file=query_or_file)
    d = Dialect.get_or_raise(dialect or None)
    result = d.validate(query_text)

    if output_format.lower() == "json":
        if result.success:
            click.echo(json.dumps({"valid": True}))
        else:
            errors = [
                format_diagnostic(diag, result.query, ansi=False) for diag in result.all_diagnostics
            ]
            if result.error and not errors:
                errors = [str(result.error)]
            click.echo(json.dumps({"valid": False, "stage": result.stage, "errors": errors}))
            raise SystemExit(1)
    else:
        if result.success:
            console.print("[green]Valid[/green]")
        else:
            console.print(f"[red]Invalid[/red] at stage: [bold]{result.stage}[/bold]")
            print_diagnostics(result)
            raise SystemExit(1)
