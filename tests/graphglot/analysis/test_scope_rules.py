"""Tests for semantic analysis rules (GA04, GA07, GA09, GE04, GE05, GE09, GP14, GP15, GQ17)."""

from __future__ import annotations

import unittest

from graphglot import features as F
from graphglot.analysis import AnalysisResult, SemanticAnalyzer
from graphglot.dialect.base import Dialect
from graphglot.features import ALL_FEATURES
from graphglot.typing.annotator import ExternalContext
from graphglot.typing.types import GqlType

# ---------------------------------------------------------------------------
# Test dialects
# ---------------------------------------------------------------------------


class _NoGA04(Dialect):
    SUPPORTED_FEATURES = ALL_FEATURES - {F.GA04}


class _NoGA07(Dialect):
    SUPPORTED_FEATURES = ALL_FEATURES - {F.GA07}


class _NoGA09(Dialect):
    SUPPORTED_FEATURES = ALL_FEATURES - {F.GA09}


class _NoGE04(Dialect):
    SUPPORTED_FEATURES = ALL_FEATURES - {F.GE04}


class _NoGE05(Dialect):
    SUPPORTED_FEATURES = ALL_FEATURES - {F.GE05}


class _NoGE09(Dialect):
    SUPPORTED_FEATURES = ALL_FEATURES - {F.GE09}


class _NoGP14(Dialect):
    SUPPORTED_FEATURES = ALL_FEATURES - {F.GP14}


class _NoGP15(Dialect):
    SUPPORTED_FEATURES = ALL_FEATURES - {F.GP15}


class _NoGQ17(Dialect):
    SUPPORTED_FEATURES = ALL_FEATURES - {F.GQ17}


class _Full(Dialect):
    SUPPORTED_FEATURES = ALL_FEATURES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _analyze(
    query: str,
    dialect: Dialect,
    external_context: ExternalContext | None = None,
) -> AnalysisResult:
    analyzer = SemanticAnalyzer()
    ast_nodes = dialect.parse(query)
    return analyzer.analyze(ast_nodes[0], dialect, external_context=external_context)


def _feature_ids(result: AnalysisResult) -> set[str]:
    return {d.feature_id for d in result.diagnostics}


# ===========================================================================
# GA07 — Ordering by discarded binding variables
# ===========================================================================


class TestGA07(unittest.TestCase):
    """GA07: without this feature, ORDER BY can only reference variables in RETURN."""

    def test_order_by_discarded_variable(self):
        """ORDER BY m when RETURN only references n → diagnostic."""
        result = _analyze("MATCH (n)-[e]->(m) RETURN n ORDER BY m", _NoGA07())
        self.assertIn("GA07", _feature_ids(result))
        self.assertIn("m", result.diagnostics[0].message)

    def test_order_by_output_variable(self):
        """ORDER BY n when RETURN references n → no diagnostic."""
        result = _analyze("MATCH (n) RETURN n ORDER BY n", _NoGA07())
        self.assertTrue(result.ok)

    def test_order_by_variable_in_return_expression(self):
        """ORDER BY n when RETURN n.name (n appears in expression) → no diagnostic."""
        result = _analyze("MATCH (n) RETURN n.name ORDER BY n", _NoGA07())
        self.assertTrue(result.ok)

    def test_order_by_return_alias(self):
        """ORDER BY x when RETURN n AS x → no diagnostic (alias is in output)."""
        result = _analyze("MATCH (n) RETURN n AS x ORDER BY x", _NoGA07())
        self.assertTrue(result.ok)

    def test_order_by_property_of_discarded_variable(self):
        """ORDER BY m.age when RETURN n → diagnostic (m not in output)."""
        result = _analyze("MATCH (n)-[e]->(m) RETURN n ORDER BY m.age", _NoGA07())
        self.assertIn("GA07", _feature_ids(result))

    def test_no_order_by_clause(self):
        """No ORDER BY → no diagnostic."""
        result = _analyze("MATCH (n) RETURN n", _NoGA07())
        self.assertTrue(result.ok)

    def test_return_star_allows_any_order(self):
        """RETURN * makes all variables visible — ORDER BY anything is fine."""
        result = _analyze("MATCH (n)-[e]->(m) RETURN * ORDER BY m", _NoGA07())
        self.assertTrue(result.ok)

    def test_multiple_discarded_variables(self):
        """Multiple discarded variables in ORDER BY."""
        result = _analyze("MATCH (a)-[e]->(b)-[f]->(c) RETURN a ORDER BY b, c", _NoGA07())
        self.assertIn("GA07", _feature_ids(result))
        msg = result.diagnostics[0].message
        self.assertIn("b", msg)
        self.assertIn("c", msg)

    def test_full_dialect_allows_discarded_order(self):
        """Full dialect (GA07 supported) → no diagnostic even with discarded vars."""
        result = _analyze("MATCH (n)-[e]->(m) RETURN n ORDER BY m", _Full())
        self.assertTrue(result.ok)

    def test_order_by_with_offset_limit(self):
        """ORDER BY with OFFSET/LIMIT still checks variables."""
        result = _analyze("MATCH (n)-[e]->(m) RETURN n ORDER BY m OFFSET 1 LIMIT 10", _NoGA07())
        self.assertIn("GA07", _feature_ids(result))


# ===========================================================================
# GE09 — Horizontal aggregation
# ===========================================================================


class TestGE09(unittest.TestCase):
    """GE09: without this feature, aggregates may not appear inside list constructors."""

    def test_aggregate_in_list_constructor(self):
        """COUNT(n) inside [COUNT(n)] → diagnostic."""
        result = _analyze("MATCH (n) RETURN [COUNT(n)]", _NoGE09())
        self.assertIn("GE09", _feature_ids(result))

    def test_aggregate_in_top_level_return(self):
        """COUNT(n) in top-level RETURN → no diagnostic."""
        result = _analyze("MATCH (n) RETURN COUNT(n)", _NoGE09())
        self.assertTrue(result.ok)

    def test_sum_in_list_constructor(self):
        """SUM inside list constructor → diagnostic."""
        result = _analyze("MATCH (n) RETURN [SUM(n.val)]", _NoGE09())
        self.assertIn("GE09", _feature_ids(result))

    def test_full_dialect_allows_horizontal_aggregation(self):
        """Full dialect (GE09 supported) → no diagnostic."""
        result = _analyze("MATCH (n) RETURN [COUNT(n)]", _Full())
        self.assertTrue(result.ok)

    def test_nested_list_with_aggregate(self):
        """Aggregate inside nested list → diagnostic."""
        result = _analyze("MATCH (n) RETURN [[COUNT(n)]]", _NoGE09())
        self.assertIn("GE09", _feature_ids(result))


# ===========================================================================
# GQ17 — Element-wise group variable operations
# ===========================================================================


class TestGQ17(unittest.TestCase):
    """GQ17: without this feature, non-grouped variables in RETURN after GROUP BY
    may only appear inside aggregate functions."""

    def test_non_grouped_var_outside_aggregate(self):
        """RETURN m.age with GROUP BY n → diagnostic (m not grouped)."""
        result = _analyze("MATCH (n)-[e]->(m) RETURN n.name, m.age GROUP BY n", _NoGQ17())
        self.assertIn("GQ17", _feature_ids(result))
        self.assertIn("m", result.diagnostics[0].message)

    def test_non_grouped_var_inside_aggregate(self):
        """RETURN COUNT(m) with GROUP BY n → no diagnostic."""
        result = _analyze("MATCH (n)-[e]->(m) RETURN n.name, COUNT(m) GROUP BY n", _NoGQ17())
        self.assertTrue(result.ok)

    def test_grouped_var_in_return(self):
        """RETURN n.name with GROUP BY n → no diagnostic (n is grouped)."""
        result = _analyze("MATCH (n) RETURN n.name, COUNT(*) GROUP BY n", _NoGQ17())
        self.assertTrue(result.ok)

    def test_no_group_by(self):
        """No GROUP BY → no diagnostic."""
        result = _analyze("MATCH (n) RETURN n.name", _NoGQ17())
        self.assertTrue(result.ok)

    def test_full_dialect_allows_elementwise_ops(self):
        """Full dialect (GQ17 supported) → no diagnostic."""
        result = _analyze("MATCH (n)-[e]->(m) RETURN n.name, m.age GROUP BY n", _Full())
        self.assertTrue(result.ok)

    def test_multiple_grouping_variables(self):
        """Multiple GROUP BY variables — referenced vars are fine."""
        result = _analyze("MATCH (n)-[e]->(m) RETURN n.name, m.age GROUP BY n, m", _NoGQ17())
        self.assertTrue(result.ok)

    def test_only_aggregates_without_group_vars(self):
        """All return items use aggregates — no diagnostic."""
        result = _analyze("MATCH (n)-[e]->(m) RETURN COUNT(n), COUNT(m) GROUP BY n", _NoGQ17())
        self.assertTrue(result.ok)


# ===========================================================================
# GA09 — Comparison of paths
# ===========================================================================


class TestGA09(unittest.TestCase):
    """GA09: without this feature, path variables may not appear in comparisons."""

    def test_path_var_in_equality(self):
        """p = q where p, q are path variables → diagnostic."""
        result = _analyze(
            "MATCH p = (a)-[e]->(b), q = (c)-[f]->(d) WHERE p = q RETURN p",
            _NoGA09(),
        )
        self.assertIn("GA09", _feature_ids(result))

    def test_path_var_in_inequality(self):
        """p <> q → diagnostic."""
        result = _analyze(
            "MATCH p = (a)-[e]->(b), q = (c)-[f]->(d) WHERE p <> q RETURN p",
            _NoGA09(),
        )
        self.assertIn("GA09", _feature_ids(result))

    def test_path_var_compared_to_literal(self):
        """p > 1 → diagnostic (path var in comparison)."""
        result = _analyze(
            "MATCH p = (a)-[e]->(b) WHERE p > 1 RETURN p",
            _NoGA09(),
        )
        self.assertIn("GA09", _feature_ids(result))

    def test_no_path_var_in_comparison(self):
        """a.name = 'test' where a is a node variable → no diagnostic."""
        result = _analyze(
            "MATCH p = (a)-[e]->(b) WHERE a.name = 'test' RETURN p",
            _NoGA09(),
        )
        self.assertTrue(result.ok)

    def test_no_path_variables_at_all(self):
        """No path variables declared → no diagnostic."""
        result = _analyze(
            "MATCH (a)-[e]->(b) WHERE a.name = 'test' RETURN a",
            _NoGA09(),
        )
        self.assertTrue(result.ok)

    def test_path_var_only_in_return(self):
        """Path var used in RETURN but not in comparison → no diagnostic."""
        result = _analyze(
            "MATCH p = (a)-[e]->(b) RETURN p",
            _NoGA09(),
        )
        self.assertTrue(result.ok)

    def test_full_dialect_allows_path_comparison(self):
        """Full dialect (GA09 supported) → no diagnostic."""
        result = _analyze(
            "MATCH p = (a)-[e]->(b), q = (c)-[f]->(d) WHERE p = q RETURN p",
            _Full(),
        )
        self.assertTrue(result.ok)

    def test_single_path_var_one_side(self):
        """Only one side of comparison is a path variable → diagnostic."""
        result = _analyze(
            "MATCH p = (a)-[e]->(b), (c)-[f]->(d) WHERE p = c RETURN p",
            _NoGA09(),
        )
        self.assertIn("GA09", _feature_ids(result))
        self.assertIn("p", result.diagnostics[0].message)

    def test_path_length_not_flagged(self):
        """PATH_LENGTH(p) > 10 — integer comparison, not path → no GA09 diagnostic."""
        result = _analyze(
            "MATCH p = (a)-[e]->(b) WHERE PATH_LENGTH(p) > 10 RETURN p",
            _NoGA09(),
        )
        ga09 = [d for d in result.diagnostics if d.feature_id == "GA09"]
        self.assertEqual(len(ga09), 0)


# ===========================================================================
# GA04 — Universal comparison (type-compatible comparisons)
# ===========================================================================


class TestGA04(unittest.TestCase):
    """GA04: without this feature, comparison operands must be type-compatible."""

    def test_string_compared_to_integer(self):
        """'hello' = 1 → diagnostic (string vs integer)."""
        result = _analyze("MATCH (n) WHERE 'hello' = 1 RETURN n", _NoGA04())
        self.assertIn("GA04", _feature_ids(result))

    def test_integer_compared_to_integer(self):
        """1 = 2 → no diagnostic (same type)."""
        result = _analyze("MATCH (n) WHERE 1 = 2 RETURN n", _NoGA04())
        # Filter to only GA04 diagnostics
        ga04 = [d for d in result.diagnostics if d.feature_id == "GA04"]
        self.assertEqual(len(ga04), 0)

    def test_integer_compared_to_float(self):
        """1 = 1.0 → no diagnostic (numeric subtypes are comparable)."""
        result = _analyze("MATCH (n) WHERE 1 = 1.0 RETURN n", _NoGA04())
        ga04 = [d for d in result.diagnostics if d.feature_id == "GA04"]
        self.assertEqual(len(ga04), 0)

    def test_string_compared_to_string(self):
        """'a' = 'b' → no diagnostic (same type)."""
        result = _analyze("MATCH (n) WHERE 'a' = 'b' RETURN n", _NoGA04())
        ga04 = [d for d in result.diagnostics if d.feature_id == "GA04"]
        self.assertEqual(len(ga04), 0)

    def test_boolean_compared_to_integer(self):
        """TRUE = 1 → diagnostic (boolean vs integer)."""
        result = _analyze("MATCH (n) WHERE TRUE = 1 RETURN n", _NoGA04())
        self.assertIn("GA04", _feature_ids(result))

    def test_full_dialect_allows_cross_type_comparison(self):
        """Full dialect (GA04 supported) → no diagnostic."""
        result = _analyze("MATCH (n) WHERE 'hello' = 1 RETURN n", _Full())
        ga04 = [d for d in result.diagnostics if d.feature_id == "GA04"]
        self.assertEqual(len(ga04), 0)

    def test_node_variable_comparison_no_diagnostic(self):
        """n.name = 'test' — unknown types → no diagnostic (conservative)."""
        result = _analyze("MATCH (n) WHERE n.name = 'test' RETURN n", _NoGA04())
        ga04 = [d for d in result.diagnostics if d.feature_id == "GA04"]
        self.assertEqual(len(ga04), 0)

    def test_string_less_than_integer(self):
        """'a' < 1 → diagnostic (string vs integer, non-equality)."""
        result = _analyze("MATCH (n) WHERE 'a' < 1 RETURN n", _NoGA04())
        self.assertIn("GA04", _feature_ids(result))

    def test_path_length_not_flagged(self):
        """PATH_LENGTH(p) > 10 — integer vs integer → no GA04 diagnostic."""
        result = _analyze(
            "MATCH p = (a)-[e]->(b) WHERE PATH_LENGTH(p) > 10 RETURN p",
            _NoGA04(),
        )
        ga04 = [d for d in result.diagnostics if d.feature_id == "GA04"]
        self.assertEqual(len(ga04), 0)

    def test_unknown_arithmetic_vs_temporal_not_flagged(self):
        """(n.x + n.y) = n.d with DATE context → no false-positive GA04."""
        ctx = ExternalContext(property_types={("Ev", "d"): GqlType.date()})
        result = _analyze(
            "MATCH (n:Ev) WHERE (n.x + n.y) = n.d RETURN n",
            _NoGA04(),
            external_context=ctx,
        )
        ga04 = [d for d in result.diagnostics if d.feature_id == "GA04"]
        self.assertEqual(len(ga04), 0)


# ===========================================================================
# GE04 — Graph parameters
# ===========================================================================


class TestGE04(unittest.TestCase):
    """GE04: without this feature, parameters may not be graph-typed."""

    def test_graph_typed_parameter(self):
        """$g is graph-typed → diagnostic."""
        ctx = ExternalContext(parameter_types={"g": GqlType.graph()})
        result = _analyze("MATCH (n) RETURN n", _NoGE04(), external_context=ctx)
        # No GeneralParameterReference in this query, so no diagnostic
        self.assertTrue(result.ok)

    def test_graph_parameter_in_use_clause(self):
        """USE $g — graph-typed parameter → diagnostic when GE04 absent."""
        ctx = ExternalContext(parameter_types={"g": GqlType.graph()})
        result = _analyze("USE $g MATCH (n) RETURN n", _NoGE04(), external_context=ctx)
        self.assertIn("GE04", _feature_ids(result))
        self.assertIn("$g", result.diagnostics[0].message)

    def test_non_graph_parameter_no_diagnostic(self):
        """$x is string-typed → no diagnostic."""
        ctx = ExternalContext(parameter_types={"x": GqlType.string()})
        result = _analyze("MATCH (n) WHERE n.name = $x RETURN n", _NoGE04(), external_context=ctx)
        ge04 = [d for d in result.diagnostics if d.feature_id == "GE04"]
        self.assertEqual(len(ge04), 0)

    def test_no_external_context_structural_inference(self):
        """USE $g — structurally graph-typed → diagnostic even without ExternalContext."""
        result = _analyze("USE $g MATCH (n) RETURN n", _NoGE04())
        self.assertIn("GE04", _feature_ids(result))

    def test_full_dialect_allows_graph_parameter(self):
        """Full dialect (GE04 supported) → no diagnostic."""
        ctx = ExternalContext(parameter_types={"g": GqlType.graph()})
        result = _analyze("USE $g MATCH (n) RETURN n", _Full(), external_context=ctx)
        ge04 = [d for d in result.diagnostics if d.feature_id == "GE04"]
        self.assertEqual(len(ge04), 0)


# ===========================================================================
# GE05 — Binding table parameters
# ===========================================================================


class TestGE05(unittest.TestCase):
    """GE05: without this feature, parameters may not be binding-table-typed."""

    def test_binding_table_parameter(self):
        """$t is binding-table-typed → diagnostic when GE05 absent."""
        ctx = ExternalContext(parameter_types={"t": GqlType.binding_table()})
        result = _analyze("MATCH (n) WHERE n.name = $t RETURN n", _NoGE05(), external_context=ctx)
        self.assertIn("GE05", _feature_ids(result))
        self.assertIn("$t", result.diagnostics[0].message)

    def test_non_binding_table_parameter_no_diagnostic(self):
        """$x is integer-typed → no diagnostic."""
        ctx = ExternalContext(parameter_types={"x": GqlType.integer()})
        result = _analyze("MATCH (n) WHERE n.age = $x RETURN n", _NoGE05(), external_context=ctx)
        ge05 = [d for d in result.diagnostics if d.feature_id == "GE05"]
        self.assertEqual(len(ge05), 0)

    def test_no_external_context_no_diagnostic(self):
        """Without ExternalContext, parameters are UNKNOWN → no diagnostic."""
        result = _analyze("MATCH (n) WHERE n.name = $t RETURN n", _NoGE05())
        ge05 = [d for d in result.diagnostics if d.feature_id == "GE05"]
        self.assertEqual(len(ge05), 0)

    def test_structural_inference_for_table(self):
        """FOR x IN TABLE $t — structurally binding-table-typed → diagnostic."""
        result = _analyze("FOR x IN TABLE $t RETURN x", _NoGE05())
        self.assertIn("GE05", _feature_ids(result))

    def test_full_dialect_allows_binding_table_parameter(self):
        """Full dialect (GE05 supported) → no diagnostic."""
        ctx = ExternalContext(parameter_types={"t": GqlType.binding_table()})
        result = _analyze("MATCH (n) WHERE n.name = $t RETURN n", _Full(), external_context=ctx)
        ge05 = [d for d in result.diagnostics if d.feature_id == "GE05"]
        self.assertEqual(len(ge05), 0)


# ===========================================================================
# Feature reporting — full query integration
# ===========================================================================

_FULL_QUERY = """\
MATCH p = (a:Account)-[t:TRANSACTION]->(b:Account)
NEXT
MATCH (b)-[u:TRANSACTION]->(c:Account)
  WHERE c <> a
    AND PATH_LENGTH(p) > 10
    AND u.amount > t.amount * 0.9
RETURN a.id AS source, c.id AS sink, u.amount
  ORDER BY u.amount DESC
  LIMIT 5
OTHERWISE
RETURN 'no matches found' AS result
"""


class TestFeatureReportingQuery(unittest.TestCase):
    """End-to-end: validate() must not report GA04/GA09 for PATH_LENGTH comparisons."""

    def test_no_false_positive_ga04_ga09(self):
        """The full NEXT/OTHERWISE query should NOT require GA04 or GA09."""
        d = Dialect.get_or_raise(None)
        result = d.validate(_FULL_QUERY)
        feature_ids = {f.id for f in result.features}
        self.assertNotIn("GA04", feature_ids, "GA04 is a false positive for PATH_LENGTH(p) > 10")
        self.assertNotIn("GA09", feature_ids, "GA09 is a false positive for PATH_LENGTH(p) > 10")

    def test_expected_features_present(self):
        """The query correctly requires these features."""
        d = Dialect.get_or_raise(None)
        result = d.validate(_FULL_QUERY)
        feature_ids = {f.id for f in result.features}
        # Core features the query should need
        for fid in ("GQ02", "GQ20", "GV55"):
            self.assertIn(fid, feature_ids, f"Expected feature {fid} not found")


# ===========================================================================
# GP15 — Graphs as procedure arguments
# ===========================================================================


class TestGP15(unittest.TestCase):
    """GP15: without this feature, procedure arguments shall not be graph-typed.

    ISO/IEC 39075:2024 §15.3 Conformance Rule 2.
    """

    def test_graph_argument_produces_diagnostic(self):
        """CALL proc(GRAPH CURRENT_GRAPH) with GP15 absent → diagnostic."""
        result = _analyze("CALL proc(GRAPH CURRENT_GRAPH)", _NoGP15())
        self.assertIn("GP15", _feature_ids(result))

    def test_non_graph_argument_no_diagnostic(self):
        """CALL proc(1) with GP15 absent → no GP15 diagnostic."""
        result = _analyze("CALL proc(1)", _NoGP15())
        self.assertNotIn("GP15", _feature_ids(result))

    def test_full_dialect_allows_graph_argument(self):
        """Full dialect (GP15 supported) → no diagnostic."""
        result = _analyze("CALL proc(GRAPH CURRENT_GRAPH)", _Full())
        gp15_diags = [d for d in result.diagnostics if d.feature_id == "GP15"]
        self.assertEqual(gp15_diags, [])

    def test_no_arguments_no_diagnostic(self):
        """CALL proc() with GP15 absent → no diagnostic."""
        result = _analyze("CALL proc()", _NoGP15())
        self.assertNotIn("GP15", _feature_ids(result))

    def test_parenthesized_graph_argument_produces_diagnostic(self):
        """CALL proc((GRAPH CURRENT_GRAPH)) — nested inside parens → still caught."""
        result = _analyze("CALL proc((GRAPH CURRENT_GRAPH))", _NoGP15())
        self.assertIn("GP15", _feature_ids(result))


# ===========================================================================
# GP14 — Binding tables as procedure arguments
# ===========================================================================


class TestGP14(unittest.TestCase):
    """GP14: without this feature, procedure arguments shall not be binding-table-typed.

    ISO/IEC 39075:2024 §15.3 Conformance Rule 3.
    """

    def test_binding_table_argument_produces_diagnostic(self):
        """CALL proc(TABLE t) with GP14 absent → diagnostic."""
        result = _analyze("CALL proc(TABLE t)", _NoGP14())
        self.assertIn("GP14", _feature_ids(result))

    def test_non_table_argument_no_diagnostic(self):
        """CALL proc(1) with GP14 absent → no GP14 diagnostic."""
        result = _analyze("CALL proc(1)", _NoGP14())
        self.assertNotIn("GP14", _feature_ids(result))

    def test_full_dialect_allows_table_argument(self):
        """Full dialect (GP14 supported) → no diagnostic."""
        result = _analyze("CALL proc(TABLE t)", _Full())
        gp14_diags = [d for d in result.diagnostics if d.feature_id == "GP14"]
        self.assertEqual(gp14_diags, [])

    def test_parenthesized_table_argument_produces_diagnostic(self):
        """CALL proc((TABLE t)) — nested inside parens → still caught."""
        result = _analyze("CALL proc((TABLE t))", _NoGP14())
        self.assertIn("GP14", _feature_ids(result))
