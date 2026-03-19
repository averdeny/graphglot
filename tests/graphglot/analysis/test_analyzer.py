"""Tests for SemanticAnalyzer orchestration."""

from __future__ import annotations

import unittest

from graphglot import features as F
from graphglot.analysis import AnalysisResult, SemanticAnalyzer
from graphglot.dialect.base import Dialect
from graphglot.features import ALL_FEATURES


class _FullDialect(Dialect):
    """Dialect that supports all features — no rule should fire."""

    SUPPORTED_FEATURES = ALL_FEATURES


class _NoGA07(Dialect):
    """Dialect missing GA07."""

    SUPPORTED_FEATURES = ALL_FEATURES - {F.GA07}


class _NoGE09(Dialect):
    """Dialect missing GE09."""

    SUPPORTED_FEATURES = ALL_FEATURES - {F.GE09}


class _NoGQ17(Dialect):
    """Dialect missing GQ17."""

    SUPPORTED_FEATURES = ALL_FEATURES - {F.GQ17}


class _NoScopeFeatures(Dialect):
    """Dialect missing all three scope features."""

    SUPPORTED_FEATURES = ALL_FEATURES - {
        F.GA07,
        F.GE09,
        F.GQ17,
    }


class TestSemanticAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = SemanticAnalyzer()
        self.full = _FullDialect()
        self.no_ga07 = _NoGA07()
        self.no_ge09 = _NoGE09()
        self.no_gq17 = _NoGQ17()
        self.no_scope = _NoScopeFeatures()

    def _analyze(self, query: str, dialect: Dialect) -> AnalysisResult:
        ast_nodes = dialect.parse(query)
        self.assertTrue(len(ast_nodes) > 0, "Parse returned no AST nodes")
        return self.analyzer.analyze(ast_nodes[0], dialect)

    # --- Orchestration tests ---

    def test_full_dialect_no_diagnostics(self):
        """Full dialect should never produce diagnostics."""
        result = self._analyze("MATCH (n)-[e]->(m) RETURN n.name ORDER BY m.age", self.full)
        self.assertTrue(result.ok)
        self.assertEqual(result.diagnostics, [])

    def test_rules_skip_supported_features(self):
        """Rules for supported features should not fire."""
        # GA07 is supported, so ORDER BY on discarded var should be fine
        result = self._analyze("MATCH (n)-[e]->(m) RETURN n ORDER BY m", self.full)
        self.assertTrue(result.ok)

    def test_multiple_rules_can_fire(self):
        """Multiple rules can produce diagnostics from a single query."""
        # GQ17: m.age outside aggregate with GROUP BY n (m not grouped)
        # GA07: e not in RETURN output but referenced in ORDER BY
        result = self._analyze(
            "MATCH (n)-[e]->(m) RETURN n.name, m.age GROUP BY n ORDER BY e",
            self.no_scope,
        )
        feature_ids = {d.feature_id for d in result.diagnostics}
        self.assertIn("GA07", feature_ids)
        self.assertIn("GQ17", feature_ids)

    def test_result_ok_property(self):
        """AnalysisResult.ok is True when no diagnostics."""
        result = self._analyze("MATCH (n) RETURN n", self.no_ga07)
        self.assertTrue(result.ok)

    def test_result_not_ok_with_diagnostics(self):
        result = self._analyze("MATCH (n)-[e]->(m) RETURN n ORDER BY m", self.no_ga07)
        self.assertFalse(result.ok)


class TestDisabledRules(unittest.TestCase):
    """Tests for the disabled_rules parameter."""

    def setUp(self):
        self.analyzer = SemanticAnalyzer()
        self.no_ga07 = _NoGA07()
        self.full = _FullDialect()

    def _analyze(
        self, query: str, dialect: Dialect, disabled_rules: set[str] | None = None
    ) -> AnalysisResult:
        ast_nodes = dialect.parse(query)
        self.assertTrue(len(ast_nodes) > 0)
        return self.analyzer.analyze(ast_nodes[0], dialect, disabled_rules=disabled_rules)

    def test_disabled_rules_skips_structural(self):
        """disabled_rules={'duplicate-alias'} → no diagnostic for duplicates."""
        result = self._analyze(
            "RETURN 1 AS a, 2 AS a",
            self.full,
            disabled_rules={"duplicate-alias"},
        )
        feature_ids = {d.feature_id for d in result.diagnostics}
        self.assertNotIn("duplicate-alias", feature_ids)

    def test_disabled_rules_skips_feature_gated(self):
        """disabled_rules={'GA04'} → GA04 rule doesn't run."""
        no_ga04 = type(
            "_NoGA04",
            (Dialect,),
            {
                "SUPPORTED_FEATURES": ALL_FEATURES - {F.GA04},
            },
        )()
        result = self._analyze(
            "MATCH (n) WHERE 'hello' = 1 RETURN n",
            no_ga04,
            disabled_rules={"GA04"},
        )
        feature_ids = {d.feature_id for d in result.diagnostics}
        self.assertNotIn("GA04", feature_ids)

    def test_disabled_rules_none_runs_all(self):
        """Default (None) runs all rules — baseline regression."""
        result = self._analyze(
            "RETURN 1 AS a, 2 AS a",
            self.full,
            disabled_rules=None,
        )
        feature_ids = {d.feature_id for d in result.diagnostics}
        self.assertIn("duplicate-alias", feature_ids)

    def test_disabled_rules_empty_set_runs_all(self):
        """Empty set runs all rules."""
        result = self._analyze(
            "RETURN 1 AS a, 2 AS a",
            self.full,
            disabled_rules=set(),
        )
        feature_ids = {d.feature_id for d in result.diagnostics}
        self.assertIn("duplicate-alias", feature_ids)


class TestDialectAnalyze(unittest.TestCase):
    """Tests for the Dialect.analyze() convenience method."""

    def test_analyze_returns_results(self):
        dialect = _NoGA07()
        results = dialect.analyze("MATCH (n)-[e]->(m) RETURN n ORDER BY m")
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].ok)
        self.assertEqual(results[0].diagnostics[0].feature_id, "GA07")

    def test_analyze_clean_query(self):
        dialect = _FullDialect()
        results = dialect.analyze("MATCH (n) RETURN n")
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].ok)

    def test_validate_passes_disabled_rules(self):
        """End-to-end: dialect.validate(query, disabled_rules=...) suppresses rules."""
        dialect = _FullDialect()
        # Without disabled_rules, duplicate-alias fires
        result = dialect.validate("RETURN 1 AS a, 2 AS a")
        self.assertFalse(result.success)
        # With disabled_rules, it's suppressed
        result = dialect.validate("RETURN 1 AS a, 2 AS a", disabled_rules={"duplicate-alias"})
        self.assertTrue(result.success)

    def test_analyze_passes_disabled_rules(self):
        """End-to-end: dialect.analyze(query, disabled_rules=...) suppresses rules."""
        dialect = _FullDialect()
        results = dialect.analyze(
            "RETURN 1 AS a, 2 AS a",
            disabled_rules={"duplicate-alias"},
        )
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].ok)
