"""GQL Lineage Analysis Module.

This module provides lineage analysis for GQL queries, tracking:
- Variable bindings (nodes, edges, paths)
- Property references and dependencies
- Output field derivations
- Filter constraints

Example:
    >>> from graphglot.dialect import Dialect
    >>> from graphglot.lineage import LineageAnalyzer
    >>>
    >>> ast = Dialect.get_or_raise("fullgql").parse("MATCH (n:Person) RETURN n.name")
    >>> analyzer = LineageAnalyzer()
    >>> graph = analyzer.analyze(ast[0])
    >>> print(graph.bindings)
"""

from graphglot.lineage.analyzer import LineageAnalyzer
from graphglot.lineage.exporter import LineageExporter
from graphglot.lineage.impact import ImpactAnalyzer
from graphglot.lineage.models import (
    Binding,
    BindingKind,
    DependencyKind,
    ExternalContext,
    Filter,
    Graph,
    ImpactPath,
    ImpactResult,
    LineageEdge,
    LineageEdgeKind,
    LineageGraph,
    LineageNode,
    Mutation,
    MutationKind,
    OutputField,
    Pattern,
    PropertyRef,
    Span,
    UpstreamDependency,
    UpstreamGraph,
    UpstreamNode,
    UpstreamRelationship,
    UpstreamSummary,
)

__all__ = [
    "Binding",
    "BindingKind",
    "DependencyKind",
    "ExternalContext",
    "Filter",
    "Graph",
    "ImpactAnalyzer",
    "ImpactPath",
    "ImpactResult",
    "LineageAnalyzer",
    "LineageEdge",
    "LineageEdgeKind",
    "LineageExporter",
    "LineageGraph",
    "LineageNode",
    "Mutation",
    "MutationKind",
    "OutputField",
    "Pattern",
    "PropertyRef",
    "Span",
    "UpstreamDependency",
    "UpstreamGraph",
    "UpstreamNode",
    "UpstreamRelationship",
    "UpstreamSummary",
]
