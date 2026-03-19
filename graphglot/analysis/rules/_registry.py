"""Core registry data structures and decorators for analysis rules."""

from __future__ import annotations

import typing as t

from graphglot.analysis.models import AnalysisContext, SemanticDiagnostic

AnalysisRuleFn = t.Callable[[AnalysisContext], list[SemanticDiagnostic]]

RULE_REGISTRY: dict[str, AnalysisRuleFn] = {}
STRUCTURAL_RULES: dict[str, AnalysisRuleFn] = {}


def analysis_rule(feature_id: str):
    """Register a function as the analysis rule for a feature.

    Rules fire when the feature is **absent** from the dialect — if the dialect
    supports the feature, the restriction doesn't apply.
    """

    def decorator(fn: AnalysisRuleFn) -> AnalysisRuleFn:
        RULE_REGISTRY[feature_id] = fn
        return fn

    return decorator


def structural_rule(rule_id: str):
    """Register a rule that always fires (not feature-gated)."""

    def decorator(fn: AnalysisRuleFn) -> AnalysisRuleFn:
        STRUCTURAL_RULES[rule_id] = fn
        return fn

    return decorator
