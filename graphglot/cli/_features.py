"""CLI command: features."""

from __future__ import annotations

import json

import click

from graphglot.cli._shared import console, output_option


@click.command(name="features")
@click.option(
    "-d",
    "--dialect",
    default=None,
    help="Filter to features supported by a dialect.",
)
@click.option(
    "-c",
    "--category",
    default=None,
    help="Case-insensitive substring match on feature category.",
)
@click.option(
    "-k",
    "--kind",
    type=click.Choice(["extension", "optional"], case_sensitive=False),
    default=None,
    help="Filter by feature kind.",
)
@click.option(
    "-s",
    "--search",
    default=None,
    help="Case-insensitive substring search in feature ID or description.",
)
@output_option()
def features_cmd(
    dialect: str | None,
    category: str | None,
    kind: str | None,
    search: str | None,
    output_format: str,
):
    """List GQL features, optionally filtered by dialect/category/kind."""
    from graphglot.features import ALL_FEATURE_MAP, FeatureKind

    features = list(ALL_FEATURE_MAP.values())

    # Filter by dialect
    if dialect:
        from graphglot.dialect.base import Dialect

        dialect_obj = Dialect.get_or_raise(dialect)
        features = [f for f in features if dialect_obj.is_feature_supported(f)]

    # Filter by category
    if category:
        cat_lower = category.lower()
        features = [f for f in features if cat_lower in f.category().lower()]

    # Filter by kind
    if kind:
        target_kind = FeatureKind(kind.lower())
        features = [f for f in features if f.kind == target_kind]

    # Filter by search
    if search:
        s_lower = search.lower()
        features = [
            f for f in features if s_lower in f.id.lower() or s_lower in f.description.lower()
        ]

    features.sort(key=lambda f: f.id)

    if output_format.lower() == "json":
        data = [
            {
                "id": f.id,
                "kind": f.kind.value,
                "category": f.category(),
                "description": f.description,
            }
            for f in features
        ]
        click.echo(json.dumps(data, indent=2))
        return

    from rich.table import Table

    table = Table(title="GQL Features")
    table.add_column("ID", style="bold")
    table.add_column("Kind")
    table.add_column("Category")
    table.add_column("Description")

    for f in features:
        table.add_row(f.id, f.kind.value, f.category(), f.description)

    console.print()
    console.print(table)
    console.print(f"  {len(features)} features", style="dim")
    console.print()
