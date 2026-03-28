"""CLI command: transpile."""

from __future__ import annotations

import json

from pathlib import Path

import click

from graphglot.cli._shared import output_option, query_options, read_query


@click.command(name="transpile")
@query_options
@click.option(
    "-r",
    "--read",
    "read_dialect",
    default="fullgql",
    show_default=True,
    help="Source dialect for parsing.",
)
@click.option(
    "-w",
    "--write",
    "write_dialect",
    default="",
    show_default=True,
    help="Target dialect for generation. Defaults to the read dialect.",
)
@output_option()
@click.option(
    "-p",
    "--pretty",
    "pretty_print",
    is_flag=True,
    default=False,
    help="Format output with clause-level line breaks.",
)
def transpile_cmd(
    query_or_file: str | None,
    query: str | None,
    file_: Path | None,
    read_dialect: str,
    write_dialect: str,
    output_format: str,
    pretty_print: bool,
):
    """Transpile a query from one dialect to another.

    Parses the input with the --read dialect, applies dialect transformations,
    and generates output using the --write dialect. If --write is omitted, the
    read dialect is used (same-dialect roundtrip).

    \b
    Examples:
      gg transpile -r neo4j -w fullgql "MATCH (n) WITH n RETURN n"
      gg transpile -r neo4j "MATCH (n) RETURN n"
      echo "MATCH (n) RETURN n" | gg transpile -r fullgql -w neo4j
    """
    from graphglot.dialect import Dialect

    query_text = read_query(query=query, file_path=file_, query_or_file=query_or_file)

    read_d = Dialect.get_or_raise(read_dialect or None)
    write_d = Dialect.get_or_raise(write_dialect or read_dialect or None)

    # Validate input against the read dialect (lexer + parser + semantic analysis)
    validation = read_d.validate(query_text)
    if not validation.success:
        from graphglot.error import format_diagnostic

        msgs = "; ".join(
            format_diagnostic(d, validation.query, ansi=False) for d in validation.all_diagnostics
        )
        raise SystemExit(f"Error: {msgs}") from None

    # Transform (with_to_next + resolve_ambiguous) + generate with write dialect
    expressions = read_d.transform(validation.expressions)
    results = [
        write_d.generate(expression, copy=False, pretty=pretty_print) for expression in expressions
    ]

    # Validate generated output against the write dialect
    try:
        write_d.validate_output(results)
    except Exception as e:
        raise SystemExit(f"Error: {e}") from None

    if output_format.lower() == "json":
        click.echo(json.dumps(results, indent=2))
    else:
        for stmt in results:
            click.echo(stmt)
