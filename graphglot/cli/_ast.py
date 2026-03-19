"""CLI command: ast."""

from __future__ import annotations

import json

from pathlib import Path

import click

from graphglot.cli._shared import console, dialect_option, output_option, query_options, read_query
from graphglot.lexer.lexer import Lexer
from graphglot.parser import Parser
from graphglot.visualization import ASTVisualizer


@click.command(name="ast")
@query_options
@dialect_option()
@click.option(
    "--depth",
    type=int,
    default=None,
    help="Maximum tree depth to display.",
)
@output_option()
def tree_cmd(
    query_or_file: str | None,
    query: str | None,
    file_: Path | None,
    dialect: str,
    depth: int | None,
    output_format: str,
):
    """Visualize the AST tree structure of a query."""
    query_text = read_query(query=query, file_path=file_, query_or_file=query_or_file)

    # Tokenize, then parse
    tokens = list(Lexer(dialect=dialect).tokenize(query_text))
    ast_nodes = Parser(dialect=dialect).parse(tokens, query_text)

    # Use the first AST node (GqlProgram)
    if not ast_nodes or ast_nodes[0] is None:
        console.print("No AST produced.", style="bold yellow")
        return

    visualizer = ASTVisualizer(ast_nodes[0])

    if output_format.lower() == "json":
        click.echo(json.dumps(visualizer.to_dict(), indent=2, default=str))
        return

    # Pretty text output
    click.echo()
    click.echo("AST Tree:")
    click.echo("-" * 40)
    click.echo(visualizer.to_text(max_depth=depth))
    click.echo()
