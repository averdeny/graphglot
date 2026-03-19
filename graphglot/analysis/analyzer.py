"""Semantic analyzer — runs registered rules and collects diagnostics."""

from __future__ import annotations

import typing as t

from graphglot.analysis.models import AnalysisContext, AnalysisResult
from graphglot.analysis.rules import RULE_REGISTRY, STRUCTURAL_RULES

if t.TYPE_CHECKING:
    from graphglot.ast.base import Expression
    from graphglot.dialect.base import Dialect
    from graphglot.lineage.models import LineageGraph
    from graphglot.typing.annotator import ExternalContext


class SemanticAnalyzer:
    """Orchestrates semantic analysis rules against an AST."""

    def analyze(
        self,
        expression: Expression,
        dialect: Dialect,
        lineage: LineageGraph | None = None,
        annotate_types: bool = True,
        external_context: ExternalContext | None = None,
        disabled_rules: set[str] | None = None,
    ) -> AnalysisResult:
        """Run all registered analysis rules and collect feature usage.

        When *annotate_types* is True (the default), a :class:`TypeAnnotator`
        pass runs before the rules so that ``_resolved_type`` is available on
        every AST node.

        *external_context* is forwarded to the :class:`TypeAnnotator` so that
        user-supplied parameter types (e.g. graph or binding-table parameters)
        are available during type inference.

        *disabled_rules* is an optional set of rule IDs (feature IDs for
        feature-gated rules, or structural rule names) to skip entirely.
        """

        if annotate_types:
            from graphglot.typing import TypeAnnotator

            TypeAnnotator(dialect=dialect, external_context=external_context).annotate(expression)

        ctx = AnalysisContext(expression=expression, dialect=dialect, lineage=lineage)
        result = AnalysisResult()
        for feature_id, rule_fn in RULE_REGISTRY.items():
            if disabled_rules and feature_id in disabled_rules:
                continue
            rule_diagnostics = rule_fn(ctx)
            if not rule_diagnostics:
                continue
            result.features.add(feature_id)
            if not dialect.is_feature_supported(feature_id):
                result.diagnostics.extend(rule_diagnostics)

        # Structural rules always fire (not feature-gated).
        for rule_id, rule_fn in STRUCTURAL_RULES.items():
            if disabled_rules and rule_id in disabled_rules:
                continue
            rule_diagnostics = rule_fn(ctx)
            if rule_diagnostics:
                result.diagnostics.extend(rule_diagnostics)

        return result
