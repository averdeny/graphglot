"""CLI command: lineage."""

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


@click.command(name="lineage")
@query_options
@dialect_option()
@output_option(choices=("pretty", "json", "upstream"))
@click.option(
    "--filter-output",
    "output_filter",
    default=None,
    help="Filter upstream summary to a specific output (name or alias, case-insensitive).",
)
def lineage_cmd(
    query_or_file: str | None,
    query: str | None,
    file_: Path | None,
    dialect: str,
    output_format: str,
    output_filter: str | None,
):
    """Analyze variable lineage and data flow in a query."""
    from graphglot.dialect.base import Dialect
    from graphglot.error import UnsupportedLineageError
    from graphglot.lineage import LineageAnalyzer

    query_text = read_query(query=query, file_path=file_, query_or_file=query_or_file)

    # Validate (tokenize -> parse -> semantic analysis)
    dialect_obj = Dialect.get_or_raise(dialect)
    validation = dialect_obj.validate(query_text)
    if not validation.success:
        console.print(f"[red]Failed[/red] at stage: [bold]{validation.stage}[/bold]")
        print_diagnostics(validation)
        raise SystemExit(1)

    # Analyze lineage on already-parsed expressions (avoids double-parse)
    expressions = dialect_obj.transform(validation.expressions)
    try:
        Dialect._check_unsupported_lineage(expressions[0])
    except UnsupportedLineageError as e:
        console.print(f"[bold red]Lineage error:[/bold red] {e}")
        raise SystemExit(1) from e

    analyzer = LineageAnalyzer()
    graph = analyzer.analyze(expressions[0], query_text=query_text)

    fmt = output_format.lower()
    if fmt == "json":
        from graphglot.lineage.exporter import LineageExporter

        click.echo(LineageExporter(graph).to_json())
    elif fmt == "upstream":
        from graphglot.lineage.impact import ImpactAnalyzer

        ia = ImpactAnalyzer(graph)
        summaries = ia.upstream_all()
        if output_filter:
            summaries = [s for s in summaries if _output_matches(graph, s.output_id, output_filter)]
        data = []
        for s in summaries:
            out = graph.outputs.get(s.output_id)
            label = ia.output_display_name(out) if out else s.output_id
            data.append(s.to_dict(output_label=label))
        console.print_json(json.dumps(data))
    else:
        _print_lineage_pretty(graph)


def _output_matches(graph, output_id: str, filter_str: str) -> bool:
    """Check if an output matches the filter string (case-insensitive)."""
    out = graph.outputs.get(output_id)
    if not out:
        return filter_str.lower() in output_id.lower()
    candidates = [output_id]
    if out.alias:
        candidates.append(out.alias)
    src = graph.source_text(out)
    if src:
        candidates.append(src)
    needle = filter_str.lower()
    return any(needle in c.lower() for c in candidates)


def _print_lineage_pretty(graph):
    """Print lineage analysis in a human-readable format."""
    from rich.markup import escape
    from rich.table import Table

    from graphglot.lineage.models import LineageEdgeKind

    console.print()

    # Graphs table
    if graph.graphs:
        table = Table(title="Graphs")
        table.add_column("ID", style="dim")
        table.add_column("Graph")

        for g in sorted(graph.graphs.values(), key=lambda x: x.id):
            table.add_row(g.id, g.name)

        console.print(table)
        console.print()

    # Build pattern -> graph_id lookup from BELONGS_TO edges
    pattern_graph: dict[str, str] = {}
    for e in graph.edges:
        if e.kind == LineageEdgeKind.BELONGS_TO and e.source_id in graph.patterns:
            pattern_graph[e.source_id] = e.target_id

    # Patterns table
    if graph.patterns:
        table = Table(title="Patterns")
        table.add_column("ID", style="dim")
        table.add_column("Source")
        table.add_column("Graph", style="cyan")

        for p in sorted(graph.patterns.values(), key=lambda x: x.id):
            pat_src = graph.source_text(p)
            pat_text = escape(pat_src) if pat_src else p.id
            pat_graph = pattern_graph.get(p.id, "")
            table.add_row(p.id, pat_text, pat_graph)

        console.print(table)
        console.print()

    # Bindings table
    if graph.bindings:
        table = Table(title="Bindings")
        table.add_column("ID", style="dim")
        table.add_column("Name", style="bold")
        table.add_column("Kind")
        table.add_column("Labels")
        table.add_column("Pattern", style="cyan")

        for b in sorted(graph.bindings.values(), key=lambda x: x.id):
            constraint_str = f":{b.label_expression}" if b.label_expression else "-"
            b_pats = graph.targets(b.id, LineageEdgeKind.IN_PATTERN)
            pat = ", ".join(b_pats) if b_pats else "-"
            table.add_row(
                b.id,
                b.name or "",
                b.kind.value,
                constraint_str,
                pat,
            )

        console.print(table)
        console.print()

    # Filters table
    if graph.filters:
        table = Table(title="Filters")
        table.add_column("ID", style="dim")
        table.add_column("Source")
        table.add_column("Constrains", style="cyan")

        for p in sorted(graph.filters.values(), key=lambda x: x.id):
            cbs = [
                tid
                for tid in graph.targets(p.id, LineageEdgeKind.CONSTRAINS)
                if tid in graph.bindings
            ]
            names = ", ".join(cbs) or "-"
            filt_src = graph.source_text(p) or p.id
            table.add_row(p.id, escape(filt_src), names)

        console.print(table)
        console.print()

    # Mutations table
    if graph.mutations:
        table = Table(title="Mutations")
        table.add_column("ID", style="dim")
        table.add_column("Kind")
        table.add_column("Writes To", style="cyan")

        for m in sorted(graph.mutations.values(), key=lambda x: x.id):
            write_targets = graph.targets(m.id, LineageEdgeKind.WRITES)
            writes = ", ".join(write_targets) or "-"
            table.add_row(m.id, m.kind.value, writes)

        console.print(table)
        console.print()

    # Property Refs table
    if graph.property_refs:
        table = Table(title="Property Refs")
        table.add_column("ID", style="dim")
        table.add_column("Property")
        table.add_column("Binding", style="cyan")

        for prop in sorted(graph.property_refs.values(), key=lambda x: x.id):
            pbid = next(
                (
                    t
                    for t in graph.targets(prop.id, LineageEdgeKind.DEPENDS_ON)
                    if t in graph.bindings
                ),
                "",
            )
            table.add_row(prop.id, prop.property_name, pbid)

        console.print(table)
        console.print()

    # Outputs table
    if graph.outputs:
        table = Table(title="Outputs")
        table.add_column("ID", style="dim")
        table.add_column("Pos", style="dim")
        table.add_column("Source")
        table.add_column("Alias")
        table.add_column("Agg")
        table.add_column("Depends On", style="cyan")

        for o in sorted(graph.outputs.values(), key=lambda x: (x.scope_id, x.position)):
            out_src = graph.source_text(o)
            source = escape(out_src) if out_src else (o.alias or o.id)
            agg = o.aggregate_function or "-"
            # Show dependencies using edge lookups
            dep_targets = graph.targets(o.id, LineageEdgeKind.DEPENDS_ON)
            agg_targets = graph.targets(o.id, LineageEdgeKind.AGGREGATES)
            all_deps = dep_targets + [t for t in agg_targets if t not in dep_targets]
            deps = ", ".join(all_deps) or "-"
            table.add_row(
                o.id,
                str(o.position),
                source,
                o.alias or "-",
                agg,
                deps,
            )

        console.print(table)
        console.print()

    # Summary — count visible relationships shown in the tables

    belongs_to_count = sum(1 for e in graph.edges if e.kind == LineageEdgeKind.BELONGS_TO)
    edge_count = belongs_to_count  # pattern -> graph
    edge_count += sum(
        1 for e in graph.edges if e.kind == LineageEdgeKind.IN_PATTERN
    )  # binding -> pattern
    for f in graph.filters.values():
        edge_count += len(graph.targets(f.id, LineageEdgeKind.CONSTRAINS))
    for o in graph.outputs.values():
        out_dep_bindings = set()
        for kind in (LineageEdgeKind.DEPENDS_ON, LineageEdgeKind.ORDERED_BY):
            for tid in graph.targets(o.id, kind):
                if tid in graph.bindings:
                    out_dep_bindings.add(tid)
                elif tid in graph.property_refs:
                    for pbid in graph.targets(tid, LineageEdgeKind.DEPENDS_ON):
                        if pbid in graph.bindings:
                            out_dep_bindings.add(pbid)
        for tid in graph.targets(o.id, LineageEdgeKind.AGGREGATES):
            if tid in graph.bindings:
                out_dep_bindings.add(tid)
        edge_count += len(out_dep_bindings)  # output -> binding/property

    console.print(
        f"Analysis: {len(graph.graphs)} graphs, "
        f"{len(graph.patterns)} patterns, "
        f"{len(graph.bindings)} bindings, "
        f"{len(graph.filters)} filters, "
        f"{len(graph.mutations)} mutations, "
        f"{len(graph.outputs)} outputs, "
        f"{edge_count} edges",
        style="dim",
    )
    console.print("Status: [green]OK[/green]")
    console.print()
