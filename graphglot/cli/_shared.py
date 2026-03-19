"""Shared CLI infrastructure: console, input helpers, option decorators."""

from __future__ import annotations

import sys

from pathlib import Path

import click

from rich.console import Console

console = Console()


def read_query(
    query: str | None,
    file_path: Path | None,
    query_or_file: str | None,
) -> str:
    """Resolve query text from explicit query, file, positional arg, or stdin.

    Precedence:
    1. --query
    2. --file
    3. positional argument (file if exists, else literal query)
    4. stdin (if not a TTY)
    """
    # 1. Explicit query wins
    if query is not None:
        return query

    # 2. Explicit file
    if file_path is not None:
        return file_path.read_text()

    # 3. Positional argument: always treated as a literal query
    if query_or_file is not None:
        return query_or_file

    # 4. Stdin if piped
    if not sys.stdin.isatty():
        data = sys.stdin.read()
        if data.strip():
            return data

    # If we get here, nothing was provided
    raise click.UsageError(
        "No query provided. Use --query, --file, a positional argument, or pipe input via stdin."
    )


def print_diagnostics(result) -> None:
    """Print validation diagnostics using Rich formatting.

    Works with any ``ValidationResult`` — renders all diagnostics with
    color-coded severity, source location, and highlighted code snippets.
    """
    from rich.text import Text

    from graphglot.error import Severity, populate_highlight

    for diag in result.all_diagnostics:
        populate_highlight(diag, result.query)
        pos = f" (line {diag.span.start_line}, col {diag.span.start_column})" if diag.span else ""
        style = "red" if diag.severity == Severity.ERROR else "yellow"
        console.print(Text(f"  [{diag.code}] {diag.message}{pos}", style=style))
        if diag.highlight:
            snippet = Text()
            snippet.append(diag.start_context, style="dim")
            snippet.append(diag.highlight, style=f"{style} underline bold")
            snippet.append(diag.end_context, style="dim")
            console.print(snippet)
    if result.error and not result.all_diagnostics:
        console.print(f"  {result.error}")


class _AliasGroup(click.Group):
    """Click group that hides alias commands from the help listing."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._aliases: dict[str, list[str]] = {}  # canonical name -> [aliases]

    def add_alias(self, cmd: click.Command, alias: str) -> None:
        """Register *alias* as an alternative name for *cmd*."""
        self._aliases.setdefault(cmd.name or alias, []).append(alias)
        self.add_command(cmd, alias)

    def format_usage(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        formatter.write_usage(ctx.command_path, "[OPTIONS] COMMAND [ARGS]...")

    def format_help_text(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        if self.help:
            formatter.write_paragraph()
            formatter.write(f"  {self.help}")
            formatter.write_paragraph()

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        self.format_usage(ctx, formatter)
        self.format_help_text(ctx, formatter)

        # Build rows: "name (a1, a2)  description"
        alias_names = {a for aliases in self._aliases.values() for a in aliases}
        rows = []
        for name in self.list_commands(ctx):
            if name in alias_names:
                continue
            cmd = self.get_command(ctx, name)
            if cmd is None or cmd.hidden:
                continue
            short_help = cmd.get_short_help_str(limit=60)
            aliases = self._aliases.get(name, [])
            label = f"{name} ({', '.join(aliases)})" if aliases else name
            rows.append((label, short_help))

        if rows:
            formatter.write_paragraph()
            formatter.write("Commands:\n")
            with formatter.indentation():
                formatter.write_dl(rows)


def query_options(fn):
    """Stack the standard query-input options on a Click command."""
    fn = click.argument("query_or_file", required=False)(fn)
    fn = click.option(
        "-q",
        "--query",
        help="Query string. If omitted, will read from file, positional arg, or stdin.",
    )(fn)
    fn = click.option(
        "-f",
        "--file",
        "file_",
        type=click.Path(exists=True, dir_okay=False, path_type=Path),
        help="Path to a file containing the query.",
    )(fn)
    return fn


def dialect_option(default="fullgql"):
    """Return a decorator for the -d/--dialect option."""

    def decorator(fn):
        return click.option(
            "-d",
            "--dialect",
            default=default,
            show_default=True,
            help="GQL dialect to use.",
        )(fn)

    return decorator


def output_option(choices=("pretty", "json")):
    """Return a decorator for the -o/--output option."""

    def decorator(fn):
        return click.option(
            "-o",
            "--output",
            "output_format",
            type=click.Choice(list(choices), case_sensitive=False),
            default="pretty",
            show_default=True,
            help="Output format.",
        )(fn)

    return decorator
