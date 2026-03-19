"""CLI command: tokenize."""

from __future__ import annotations

import hashlib
import json

from pathlib import Path

import click

from rich.text import Text

from graphglot.cli._shared import console, dialect_option, output_option, query_options, read_query
from graphglot.lexer.lexer import Lexer

_COLOR_PALETTE = [
    "#e6194b",
    "#3cb44b",
    "#ffe119",
    "#4363d8",
    "#f58231",
    "#911eb4",
    "#46f0f0",
    "#f032e6",
    "#bcf60c",
    "#fabebe",
    "#008080",
    "#e6beff",
    "#9a6324",
    "#fffac8",
    "#800000",
    "#aaffc3",
    "#808000",
    "#ffd8b1",
    "#000075",
    "#808080",
    "#ffffff",
    "#000000",
]


def _get_color_for_token_type(token_type) -> str:
    """Generate a high-contrast color for each token type."""
    token_name = str(token_type)
    hash_value = int(hashlib.md5(token_name.encode("utf-8"), usedforsecurity=False).hexdigest(), 16)
    return _COLOR_PALETTE[hash_value % len(_COLOR_PALETTE)]


@click.command(name="tokenize")
@query_options
@dialect_option()
@output_option()
@click.option(
    "--no-color",
    is_flag=True,
    help="Disable colored output (monochrome).",
)
def tokenize(
    query_or_file: str | None,
    query: str | None,
    file_: Path | None,
    dialect: str,
    output_format: str,
    no_color: bool,
):
    """Tokenize a query or file and print tokens."""
    query_text = read_query(query=query, file_path=file_, query_or_file=query_or_file)
    tokens = list(Lexer(dialect=dialect).tokenize(query_text))

    if output_format.lower() == "json":
        data = [
            {
                "type": str(token.token_type),
                "text": token.text,
            }
            for token in tokens
        ]
        click.echo(json.dumps(data, indent=2))
        return

    # Pretty / colored output
    if not tokens:
        console.print("No tokens produced.", style="bold yellow")
        return

    colored_text = Text()
    token_types = {}

    for token in tokens:
        color = _get_color_for_token_type(token.token_type) if not no_color else None
        colored_text.append(token.text, style=color)
        token_types[token.token_type] = color

    console.print("\n")
    console.print("Tokenized Query:", style="bold underline")
    console.print("\n")
    console.print(colored_text)
    console.print("\n")

    console.print("Token Types Legend:", style="bold underline")
    console.print("\n")
    legend_text = Text()

    for token_type in sorted(token_types, key=lambda t: str(t)):
        color = token_types[token_type] if not no_color else None
        legend_text.append(f"{token_type}", style=color)
        legend_text.append("\n")

    console.print(legend_text)
