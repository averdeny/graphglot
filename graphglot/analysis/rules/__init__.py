"""Rule registry for semantic analysis."""

import graphglot.analysis.rules.scope_rules as scope_rules
import graphglot.analysis.rules.scope_validator as scope_validator
import graphglot.analysis.rules.structural_rules as structural_rules

from graphglot.analysis.rules._registry import (
    RULE_REGISTRY,
    STRUCTURAL_RULES,
    AnalysisRuleFn,
    analysis_rule,
    structural_rule,
)

__all__ = [
    "RULE_REGISTRY",
    "STRUCTURAL_RULES",
    "AnalysisRuleFn",
    "analysis_rule",
    "scope_rules",
    "scope_validator",
    "structural_rule",
    "structural_rules",
]
