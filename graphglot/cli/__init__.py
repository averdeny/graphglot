"""Command-line interface for GraphGlot."""

from __future__ import annotations

import click

from graphglot import __version__
from graphglot.cli._ast import tree_cmd
from graphglot.cli._dialects import dialects_cmd
from graphglot.cli._features import features_cmd
from graphglot.cli._lineage import lineage_cmd
from graphglot.cli._parse import parse_cmd
from graphglot.cli._shared import _AliasGroup
from graphglot.cli._tokenize import tokenize
from graphglot.cli._transpile import transpile_cmd
from graphglot.cli._type import type_cmd
from graphglot.cli._validate import validate_cmd


@click.group(cls=_AliasGroup)
@click.version_option(version=__version__, prog_name="graphglot")
def cli():
    """GraphGlot - A Graph Query Language Toolkit."""
    pass


cli.add_command(tokenize)
cli.add_alias(tokenize, "t")

cli.add_command(tree_cmd)
cli.add_alias(tree_cmd, "tree")

cli.add_command(lineage_cmd)
cli.add_alias(lineage_cmd, "l")

cli.add_command(validate_cmd)
cli.add_alias(validate_cmd, "v")

cli.add_command(transpile_cmd)
cli.add_alias(transpile_cmd, "tp")

cli.add_command(dialects_cmd)
cli.add_alias(dialects_cmd, "d")

cli.add_command(features_cmd)
cli.add_alias(features_cmd, "f")

cli.add_command(parse_cmd)
cli.add_alias(parse_cmd, "p")

cli.add_command(type_cmd)
cli.add_alias(type_cmd, "ty")


def main():
    """Run the CLI."""
    cli()
