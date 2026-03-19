"""Data models for GQL lineage analysis.

This module defines the core data structures for representing lineage information:
- Graph: A graph referenced in the query
- Pattern: A graph pattern from a MATCH clause
- Binding: A variable bound in a pattern (node, edge, path)
- PropertyRef: A reference to a property on a binding
- OutputField: A field in a RETURN clause
- Filter: A filter condition (WHERE or inline predicate)
- LineageEdge: A relationship between entities in the lineage graph
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar

from graphglot.error import Span  # canonical definitions

T = TypeVar("T", bound="LineageNode")


class BindingKind(Enum):
    """Kind of binding (node, edge, path, or variable)."""

    NODE = "node"
    EDGE = "edge"
    PATH = "path"
    VARIABLE = "variable"


class MutationKind(Enum):
    """Kind of data-modifying operation."""

    INSERT = "insert"
    SET_PROPERTY = "set_property"
    SET_LABEL = "set_label"
    SET_ALL = "set_all"
    REMOVE_PROPERTY = "remove_property"
    REMOVE_LABEL = "remove_label"
    DELETE = "delete"
    MERGE = "merge"


class LineageEdgeKind(Enum):
    """Kind of edge in the lineage graph."""

    # Data flow
    DEPENDS_ON = "depends_on"
    ORDERED_BY = "ordered_by"

    # Constraints
    CONSTRAINS = "constrains"

    # Aggregation
    AGGREGATES = "aggregates"

    # Scope propagation
    PROPAGATES_TO = "propagates_to"

    # Graph membership
    BELONGS_TO = "belongs_to"

    # Binding → Pattern membership
    IN_PATTERN = "in_pattern"

    # Mutation → target binding
    WRITES = "writes"


@dataclass(kw_only=True)
class LineageNode:
    """Base class for all lineage graph entities."""

    id: str
    node_type: str
    span: Span | None = None


class _TypedView(Generic[T]):
    """Read-only view over nodes filtered by type. Supports O(1) containment."""

    __slots__ = ("_nodes", "_type")

    def __init__(self, nodes: dict[str, LineageNode], node_type: type[T]):
        self._nodes = nodes
        self._type = node_type

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        return isinstance(self._nodes.get(key), self._type)

    def __getitem__(self, key: str) -> T:
        v = self._nodes.get(key)
        if isinstance(v, self._type):
            return v
        raise KeyError(key)

    def get(self, key: str, default: T | None = None) -> T | None:
        v = self._nodes.get(key)
        return v if isinstance(v, self._type) else default

    def values(self) -> list[T]:
        return [v for v in self._nodes.values() if isinstance(v, self._type)]

    def items(self) -> list[tuple[str, T]]:
        return [(k, v) for k, v in self._nodes.items() if isinstance(v, self._type)]

    def keys(self) -> list[str]:
        return [k for k, v in self._nodes.items() if isinstance(v, self._type)]

    def __len__(self) -> int:
        return sum(1 for v in self._nodes.values() if isinstance(v, self._type))

    def __iter__(self):
        return iter(self.keys())


@dataclass
class Graph(LineageNode):
    """A graph referenced in the query (via USE clause or implicit default)."""

    node_type: str = "graph"
    name: str = ""


@dataclass
class Binding(LineageNode):
    """A variable bound in a GQL pattern."""

    node_type: str = "binding"
    name: str | None = None
    kind: BindingKind = BindingKind.VARIABLE
    scope_id: str = ""

    # Label/type constraint expression (e.g. "!Person&Test", "KNOWS|FOLLOWS")
    label_expression: str = ""


@dataclass
class PropertyRef(LineageNode):
    """Reference to a property on a binding."""

    node_type: str = "property_ref"
    property_name: str = ""


@dataclass
class OutputField(LineageNode):
    """An output field in RETURN clause."""

    node_type: str = "output"
    alias: str | None = None
    position: int = 0

    # Aggregation info
    is_aggregated: bool = False
    aggregate_function: str | None = None
    is_distinct: bool = False

    # Scope tracking
    scope_id: str = ""


@dataclass
class Filter(LineageNode):
    """A filter condition (from WHERE clause or inline element predicate)."""

    node_type: str = "filter"


@dataclass
class Mutation(LineageNode):
    """A data-modifying operation (SET, REMOVE, DELETE, INSERT, CREATE, MERGE)."""

    node_type: str = "mutation"
    kind: MutationKind = MutationKind.INSERT
    label_name: str | None = None
    is_detach: bool = False
    scope_id: str = ""


@dataclass
class LineageEdge:
    """Edge in the lineage graph."""

    source_id: str
    target_id: str
    kind: LineageEdgeKind


@dataclass
class Pattern(LineageNode):
    """A graph pattern from a MATCH clause."""

    node_type: str = "pattern"
    match_index: int = 0


@dataclass
class LineageGraph:
    """Complete lineage analysis result."""

    # All entities in a single dict
    nodes: dict[str, LineageNode] = field(default_factory=dict)

    # Edges
    edges: list[LineageEdge] = field(default_factory=list)

    # Metadata
    query_text: str = ""

    # -- typed accessors (backward-compatible) --

    @property
    def graphs(self) -> _TypedView[Graph]:
        return _TypedView(self.nodes, Graph)

    @property
    def bindings(self) -> _TypedView[Binding]:
        return _TypedView(self.nodes, Binding)

    @property
    def patterns(self) -> _TypedView[Pattern]:
        return _TypedView(self.nodes, Pattern)

    @property
    def property_refs(self) -> _TypedView[PropertyRef]:
        return _TypedView(self.nodes, PropertyRef)

    @property
    def outputs(self) -> _TypedView[OutputField]:
        return _TypedView(self.nodes, OutputField)

    @property
    def filters(self) -> _TypedView[Filter]:
        return _TypedView(self.nodes, Filter)

    @property
    def mutations(self) -> _TypedView[Mutation]:
        return _TypedView(self.nodes, Mutation)

    def source_text(self, node: LineageNode) -> str | None:
        """Derive source text for a node from its span and query_text."""
        span = node.span
        if (
            span
            and self.query_text
            and span.start_offset is not None
            and span.end_offset is not None
        ):
            return self.query_text[span.start_offset : span.end_offset]
        return None

    def node(self, node_id: str) -> LineageNode | None:
        """Look up any entity by ID."""
        return self.nodes.get(node_id)

    def targets(self, source_id: str, kind: LineageEdgeKind) -> list[str]:
        """Return target IDs for all edges from source_id with given kind."""
        return [e.target_id for e in self.edges if e.source_id == source_id and e.kind == kind]

    def sources(self, target_id: str, kind: LineageEdgeKind) -> list[str]:
        """Return source IDs for all edges to target_id with given kind."""
        return [e.source_id for e in self.edges if e.target_id == target_id and e.kind == kind]

    def binding_deps(self, entity_id: str) -> list[str]:
        """Binding IDs referenced by dependency-like edges for an entity.

        Includes data-flow edges (``DEPENDS_ON``, ``AGGREGATES``, ``ORDERED_BY``)
        and ``CONSTRAINS`` edges so filters can resolve constrained bindings via
        the same helper.
        """
        result: list[str] = []
        for tid in (
            self.targets(entity_id, LineageEdgeKind.DEPENDS_ON)
            + self.targets(entity_id, LineageEdgeKind.AGGREGATES)
            + self.targets(entity_id, LineageEdgeKind.CONSTRAINS)
            + self.targets(entity_id, LineageEdgeKind.ORDERED_BY)
        ):
            if tid in self.bindings:
                if tid not in result:
                    result.append(tid)
            elif tid in self.property_refs:
                for bid in self.targets(tid, LineageEdgeKind.DEPENDS_ON):
                    if bid in self.bindings and bid not in result:
                        result.append(bid)
        return result


@dataclass
class ExternalContext:
    """External bindings available to the query (session parameters, prior NEXT outputs, etc.).

    By default empty — all identifiers must be bound within the query itself.
    """

    bindings: dict[str, BindingKind] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Impact / upstream analysis models
# ---------------------------------------------------------------------------


class DependencyKind(Enum):
    """How a dependency relates to the output."""

    DIRECT = "direct"
    PATTERN = "pattern"
    CONSTRAINT = "constraint"


@dataclass
class UpstreamNode:
    """A node in the upstream graph (Neo4j-style)."""

    id: str
    labels: list[str]
    properties: dict[str, Any]


@dataclass
class UpstreamRelationship:
    """A relationship in the upstream graph (Neo4j-style)."""

    id: str
    type: str
    start_node: str
    end_node: str
    properties: dict[str, Any]


@dataclass
class UpstreamGraph:
    """Graph-structured upstream result with nodes and relationships."""

    nodes: list[UpstreamNode] = field(default_factory=list)
    relationships: list[UpstreamRelationship] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to Neo4j-style dict."""
        return {
            "nodes": sorted(
                [{"id": n.id, "labels": n.labels, "properties": n.properties} for n in self.nodes],
                key=lambda x: x["id"],
            ),
            "relationships": sorted(
                [
                    {
                        "id": r.id,
                        "type": r.type,
                        "startNode": r.start_node,
                        "endNode": r.end_node,
                        "properties": r.properties,
                    }
                    for r in self.relationships
                ],
                key=lambda x: x["id"],
            ),
        }


@dataclass
class UpstreamDependency:
    """A single upstream dependency row for an output field."""

    output_id: str
    graph: str  # graph name, or "" if none
    label: str  # label/type name, or "" if none
    property: str  # property name, or "" if none
    kind: DependencyKind = DependencyKind.DIRECT


@dataclass
class UpstreamSummary:
    """All upstream dependencies for an output field."""

    output_id: str
    dependencies: list[UpstreamDependency] = field(default_factory=list)

    def to_dict(self, output_label: str | None = None) -> dict[str, Any]:
        """Serialize to JSON-friendly dict."""
        return {
            "output": output_label or self.output_id,
            "dependencies": [
                {
                    "graph": d.graph or None,
                    "label": d.label or None,
                    "property": d.property or None,
                    "type": d.kind.value,
                }
                for d in self.dependencies
            ],
        }


@dataclass
class ImpactPath:
    """A path in the lineage graph from source to target."""

    nodes: list[str] = field(default_factory=list)
    edges: list[str] = field(default_factory=list)


@dataclass
class ImpactResult:
    """Result of impact analysis."""

    source_id: str
    direct_impacts: list[str] = field(default_factory=list)
    transitive_impacts: list[str] = field(default_factory=list)
    impacted_outputs: list[str] = field(default_factory=list)
    impacted_filters: list[str] = field(default_factory=list)
    impacted_bindings: list[str] = field(default_factory=list)
    impacted_properties: list[str] = field(default_factory=list)
    impacted_mutations: list[str] = field(default_factory=list)
    impact_paths: list[ImpactPath] = field(default_factory=list)
