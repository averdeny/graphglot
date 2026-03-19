"""CLI command: dialects."""

from __future__ import annotations

import json

import click

from graphglot.cli._shared import console, output_option


@click.command(name="dialects")
@output_option()
def dialects_cmd(output_format: str):
    """List available dialects and their feature counts."""
    from graphglot.dialect.base import Dialect, Dialects

    rows = []
    for member in Dialects:
        if member == Dialects.IR:
            continue
        dialect_obj = Dialect.get_or_raise(member.value)
        doc = (dialect_obj.__class__.__doc__ or "").strip().split("\n")[0]
        rows.append(
            {
                "name": member.value,
                "features": len(dialect_obj.SUPPORTED_FEATURES),
                "description": doc,
            }
        )

    if output_format.lower() == "json":
        click.echo(json.dumps(rows, indent=2))
        return

    from rich.table import Table

    table = Table(title="Dialects")
    table.add_column("Name", style="bold")
    table.add_column("Features", justify="right")
    table.add_column("Description")

    for row in rows:
        table.add_row(str(row["name"]), str(row["features"]), str(row["description"]))

    console.print()
    console.print(table)
    console.print()
