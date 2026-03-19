"""Lineage export functionality.

Provides export to JSON and dict formats.
"""

from __future__ import annotations

import json

from dataclasses import asdict
from typing import Any

from graphglot.error import Span
from graphglot.lineage.models import LineageGraph


class LineageExporter:
    """Export lineage graph to various formats."""

    def __init__(self, graph: LineageGraph):
        self.graph = graph

    @staticmethod
    def _span_dict(span: Span | None) -> dict[str, Any] | None:
        return asdict(span) if span is not None else None

    def to_dict(self) -> dict[str, Any]:
        """Export to Python dictionary."""
        nodes: list[dict[str, Any]] = []
        nodes.extend(self._export_graphs())
        nodes.extend(self._export_patterns())
        nodes.extend(self._export_bindings())
        nodes.extend(self._export_property_refs())
        nodes.extend(self._export_outputs())
        nodes.extend(self._export_filters())
        nodes.extend(self._export_mutations())
        nodes.sort(key=lambda n: n["id"])
        return {
            "nodes": nodes,
            "edges": self._export_edges(),
            "query_text": self.graph.query_text,
        }

    def to_json(self, indent: int | None = 2) -> str:
        """Export to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def _export_graphs(self) -> list[dict[str, Any]]:
        """Export graph entities to list of dicts."""
        result: list[dict[str, Any]] = []
        for graph in sorted(self.graph.graphs.values(), key=lambda g: g.id):
            result.append(
                {
                    "id": graph.id,
                    "node_type": "graph",
                    "name": graph.name,
                    "span": self._span_dict(graph.span),
                    "source_text": self.graph.source_text(graph),
                }
            )
        return result

    def _export_patterns(self) -> list[dict[str, Any]]:
        """Export patterns to list of dicts."""
        result: list[dict[str, Any]] = []
        for pattern in sorted(self.graph.patterns.values(), key=lambda p: p.id):
            result.append(
                {
                    "id": pattern.id,
                    "node_type": "pattern",
                    "match_index": pattern.match_index,
                    "span": self._span_dict(pattern.span),
                    "source_text": self.graph.source_text(pattern),
                }
            )
        return result

    def _export_bindings(self) -> list[dict[str, Any]]:
        """Export bindings to list of dicts."""
        result: list[dict[str, Any]] = []
        for binding in sorted(self.graph.bindings.values(), key=lambda b: b.id):
            result.append(
                {
                    "id": binding.id,
                    "node_type": "binding",
                    "name": binding.name,
                    "kind": binding.kind.value,
                    "label_expression": binding.label_expression or None,
                    "span": self._span_dict(binding.span),
                    "source_text": self.graph.source_text(binding),
                }
            )
        return result

    def _export_property_refs(self) -> list[dict[str, Any]]:
        """Export property refs to list of dicts."""
        result: list[dict[str, Any]] = []
        for prop in sorted(self.graph.property_refs.values(), key=lambda p: p.id):
            result.append(
                {
                    "id": prop.id,
                    "node_type": "property_ref",
                    "property_name": prop.property_name,
                    "span": self._span_dict(prop.span),
                    "source_text": self.graph.source_text(prop),
                }
            )
        return result

    def _export_outputs(self) -> list[dict[str, Any]]:
        """Export outputs to list of dicts."""
        result: list[dict[str, Any]] = []
        for output in sorted(self.graph.outputs.values(), key=lambda o: o.id):
            result.append(
                {
                    "id": output.id,
                    "node_type": "output",
                    "alias": output.alias,
                    "position": output.position,
                    "is_aggregated": output.is_aggregated,
                    "is_distinct": output.is_distinct,
                    "aggregate_function": output.aggregate_function,
                    "span": self._span_dict(output.span),
                    "source_text": self.graph.source_text(output),
                }
            )
        return result

    def _export_filters(self) -> list[dict[str, Any]]:
        """Export filters to list of dicts."""
        result: list[dict[str, Any]] = []
        for filt in sorted(self.graph.filters.values(), key=lambda p: p.id):
            result.append(
                {
                    "id": filt.id,
                    "node_type": "filter",
                    "span": self._span_dict(filt.span),
                    "source_text": self.graph.source_text(filt),
                }
            )
        return result

    def _export_mutations(self) -> list[dict[str, Any]]:
        """Export mutations to list of dicts."""
        result: list[dict[str, Any]] = []
        for mut in sorted(self.graph.mutations.values(), key=lambda m: m.id):
            result.append(
                {
                    "id": mut.id,
                    "node_type": "mutation",
                    "kind": mut.kind.value,
                    "label_name": mut.label_name,
                    "is_detach": mut.is_detach,
                    "span": self._span_dict(mut.span),
                    "source_text": self.graph.source_text(mut),
                }
            )
        return result

    def _export_edges(self) -> list[dict[str, Any]]:
        """Export edges to list of dicts."""
        result: list[dict[str, Any]] = []
        for edge in self.graph.edges:
            d: dict[str, Any] = {
                "source_id": edge.source_id,
                "target_id": edge.target_id,
                "kind": edge.kind.value,
            }
            result.append(d)
        # Sort for determinism
        result.sort(key=lambda e: (e["source_id"], e["target_id"], e["kind"]))
        return result
