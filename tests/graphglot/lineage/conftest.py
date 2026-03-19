"""Fixtures for lineage tests."""

from __future__ import annotations

import pytest

from graphglot.dialect.neo4j import Neo4j
from graphglot.lexer import Lexer
from graphglot.lineage.models import LineageEdgeKind
from graphglot.parser import Parser


def has_edge(graph, source_id, target_id, kind):
    """Check if a specific edge exists in the lineage graph."""
    return target_id in graph.targets(source_id, kind)


def edge_targets(graph, source_id, kind):
    """Find all target IDs for edges from source_id with given kind."""
    return graph.targets(source_id, kind)


def edge_sources(graph, target_id, kind):
    """Find all source IDs for edges to target_id with given kind."""
    return graph.sources(target_id, kind)


def dep_bindings(graph, entity_id):
    """Binding IDs that entity depends on (direct or via property refs)."""
    return graph.binding_deps(entity_id)


def dep_properties(graph, entity_id):
    """PropertyRef IDs that entity depends on (via DEPENDS_ON or ORDERED_BY)."""
    return [
        tid
        for tid in graph.targets(entity_id, LineageEdgeKind.DEPENDS_ON)
        + graph.targets(entity_id, LineageEdgeKind.ORDERED_BY)
        if tid in graph.property_refs
    ]


def constrained_bindings(graph, filter_id):
    """Binding IDs constrained by a filter (direct or via property refs)."""
    return graph.binding_deps(filter_id)


def prop_binding_id(graph, prop):
    """Find the binding ID for a property ref via its DEPENDS_ON edge."""
    for tid in graph.targets(prop.id, LineageEdgeKind.DEPENDS_ON):
        if tid in graph.bindings:
            return tid
    return ""


def inherits_from(graph, binding_id):
    """Source binding ID via PROPAGATES_TO reverse edge, or None."""
    sources = graph.sources(binding_id, LineageEdgeKind.PROPAGATES_TO)
    return sources[0] if sources else None


@pytest.fixture
def lexer() -> Lexer:
    """Create a lexer instance."""
    return Lexer()


@pytest.fixture
def parser() -> Parser:
    """Create a parser instance."""
    return Parser()


@pytest.fixture
def parse(lexer: Lexer, parser: Parser):
    """Fixture that returns a function to parse GQL queries."""

    def _parse(query: str):
        tokens = lexer.tokenize(query)
        result = parser.parse(tokens, query)
        return result[0] if result else None

    return _parse


@pytest.fixture
def cypher_parse():
    """Fixture that returns a function to parse Cypher queries via Neo4j dialect."""
    dialect = Neo4j()

    def _parse(query: str):
        tokens = dialect.Lexer().tokenize(query)
        result = dialect.Parser().parse(tokens, query)
        return result[0] if result else None

    return _parse
