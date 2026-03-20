"""Tests for structural validation rules.

duplicate-alias, union-column-mismatch, mixed-query-conjunction,
nested-aggregation, aggregation-in-non-return-context, same-pattern-node-edge-conflict,
boolean-operand-type, orderby-aggregate-without-groupby, non-constant-skip-limit,
invalid-delete-target, invalid-merge-pattern, exists-no-update, type-mismatch.
These rules fire unconditionally — they are not gated on dialect features.
"""

from __future__ import annotations

import unittest

from graphglot.analysis import AnalysisResult, SemanticAnalyzer
from graphglot.dialect.fullgql import FullGQL
from graphglot.dialect.neo4j import Neo4j
from graphglot.typing.annotator import ExternalContext
from graphglot.typing.types import GqlType

_neo4j = Neo4j()
_gql = FullGQL()


def _analyze(query: str) -> AnalysisResult:
    analyzer = SemanticAnalyzer()
    ast_nodes = _neo4j.parse(query)
    return analyzer.analyze(ast_nodes[0], _neo4j)


def _analyze_gql(query: str) -> AnalysisResult:
    analyzer = SemanticAnalyzer()
    ast_nodes = _gql.parse(query)
    return analyzer.analyze(ast_nodes[0], _gql)


def _analyze_cypher_as_gql(query: str) -> AnalysisResult:
    """Parse with Neo4j (Cypher extensions), analyze with FullGQL."""
    analyzer = SemanticAnalyzer()
    ast_nodes = _neo4j.parse(query)
    return analyzer.analyze(ast_nodes[0], _gql)


def _feature_ids(result: AnalysisResult) -> set[str]:
    return {d.feature_id for d in result.diagnostics}


# ===========================================================================
# duplicate-alias — Duplicate column aliases
# ===========================================================================


class TestDuplicateColumnAliases(unittest.TestCase):
    """duplicate-alias: duplicate aliases in RETURN/WITH clause."""

    def test_duplicate_alias_return(self):
        """RETURN 1 AS a, 2 AS a → diagnostic."""
        result = _analyze("RETURN 1 AS a, 2 AS a")
        self.assertIn("duplicate-alias", _feature_ids(result))
        self.assertIn("a", result.diagnostics[0].message)

    def test_duplicate_alias_with(self):
        """WITH 1 AS a, 2 AS a RETURN a → diagnostic."""
        result = _analyze("WITH 1 AS a, 2 AS a RETURN a")
        self.assertIn("duplicate-alias", _feature_ids(result))

    def test_distinct_aliases_ok(self):
        """RETURN 1 AS a, 2 AS b → no diagnostic."""
        result = _analyze("RETURN 1 AS a, 2 AS b")
        self.assertNotIn("duplicate-alias", _feature_ids(result))

    def test_return_star_ok(self):
        """MATCH (n) RETURN * → no diagnostic."""
        result = _analyze("MATCH (n) RETURN *")
        self.assertNotIn("duplicate-alias", _feature_ids(result))


# ===========================================================================
# union-column-mismatch — UNION column mismatch
# ===========================================================================


class TestUnionColumnMismatch(unittest.TestCase):
    """union-column-mismatch: UNION branches must have the same column names."""

    def test_different_aliases(self):
        """RETURN 1 AS a UNION RETURN 2 AS b → diagnostic."""
        result = _analyze("RETURN 1 AS a UNION RETURN 2 AS b")
        self.assertIn("union-column-mismatch", _feature_ids(result))

    def test_different_aliases_union_all(self):
        """RETURN 1 AS a UNION ALL RETURN 2 AS b → diagnostic."""
        result = _analyze("RETURN 1 AS a UNION ALL RETURN 2 AS b")
        self.assertIn("union-column-mismatch", _feature_ids(result))

    def test_same_aliases_ok(self):
        """RETURN 1 AS a UNION RETURN 2 AS a → no diagnostic."""
        result = _analyze("RETURN 1 AS a UNION RETURN 2 AS a")
        self.assertNotIn("union-column-mismatch", _feature_ids(result))


# ===========================================================================
# mixed-query-conjunction — Query conjunction consistency (§14.2 SR 3)
# ===========================================================================


class TestMixedQueryConjunction(unittest.TestCase):
    """mixed-query-conjunction: all conjunctions in a CQE must be identical."""

    def test_union_then_union_all(self):
        """UNION then UNION ALL → diagnostic."""
        result = _analyze("RETURN 1 AS a UNION RETURN 2 AS a UNION ALL RETURN 3 AS a")
        self.assertIn("mixed-query-conjunction", _feature_ids(result))

    def test_union_all_then_union(self):
        """UNION ALL then UNION → diagnostic."""
        result = _analyze("RETURN 1 AS a UNION ALL RETURN 2 AS a UNION RETURN 3 AS a")
        self.assertIn("mixed-query-conjunction", _feature_ids(result))

    def test_all_union_ok(self):
        """All UNION → no diagnostic."""
        result = _analyze("RETURN 1 AS a UNION RETURN 2 AS a UNION RETURN 3 AS a")
        self.assertNotIn("mixed-query-conjunction", _feature_ids(result))

    def test_all_union_all_ok(self):
        """All UNION ALL → no diagnostic."""
        result = _analyze("RETURN 1 AS a UNION ALL RETURN 2 AS a UNION ALL RETURN 3 AS a")
        self.assertNotIn("mixed-query-conjunction", _feature_ids(result))

    def test_union_then_except(self):
        """UNION then EXCEPT → diagnostic (different operator types)."""
        result = _analyze_gql("RETURN 1 AS a UNION RETURN 2 AS a EXCEPT RETURN 3 AS a")
        self.assertIn("mixed-query-conjunction", _feature_ids(result))

    def test_union_then_otherwise(self):
        """UNION then OTHERWISE → diagnostic (set operator vs OTHERWISE)."""
        result = _analyze_gql("RETURN 1 AS a UNION RETURN 2 AS a OTHERWISE RETURN 3 AS a")
        self.assertIn("mixed-query-conjunction", _feature_ids(result))


# ===========================================================================
# nested-aggregation — Nested aggregate functions (§20.9 SR 4)
# ===========================================================================


class TestNestedAggregation(unittest.TestCase):
    """nested-aggregation: aggregate shall not contain an aggregate."""

    def test_count_of_count(self):
        """count(count(*)) → diagnostic."""
        result = _analyze("MATCH (n) RETURN count(count(*)) AS c")
        self.assertIn("nested-aggregation", _feature_ids(result))

    def test_sum_of_count(self):
        """sum(count(*)) → diagnostic."""
        result = _analyze("MATCH (n) RETURN sum(count(*)) AS s")
        self.assertIn("nested-aggregation", _feature_ids(result))

    def test_single_aggregate_ok(self):
        """count(*) alone → no diagnostic."""
        result = _analyze("MATCH (n) RETURN count(*) AS c")
        self.assertNotIn("nested-aggregation", _feature_ids(result))


# ===========================================================================
# aggregation-in-non-return-context — Aggregates outside RETURN/SELECT/ORDER BY
# (§20.1 CR 4)
# ===========================================================================


class TestAggregationInNonReturnContext(unittest.TestCase):
    """aggregation-in-non-return-context: aggregates only in RETURN/SELECT/ORDER BY."""

    def test_aggregate_in_where(self):
        """Aggregate in WHERE → diagnostic."""
        result = _analyze("MATCH (n) WHERE count(*) > 1 RETURN n")
        self.assertIn("aggregation-in-non-return-context", _feature_ids(result))

    def test_aggregate_in_return_ok(self):
        """Aggregate in RETURN → no diagnostic."""
        result = _analyze("MATCH (n) RETURN count(*)")
        self.assertNotIn("aggregation-in-non-return-context", _feature_ids(result))

    def test_aggregate_in_order_by_ok(self):
        """Aggregate in ORDER BY → no diagnostic (GF20 allows at AST level)."""
        result = _analyze("MATCH (n) RETURN n.name AS name ORDER BY count(*)")
        self.assertNotIn("aggregation-in-non-return-context", _feature_ids(result))


# ===========================================================================
# same-pattern-node-edge-conflict — Node/edge variable conflict (§16.4 SR 5)
# ===========================================================================


class TestSamePatternNodeEdgeConflict(unittest.TestCase):
    """same-pattern-node-edge-conflict: same name as node and edge in one pattern."""

    def test_same_var_node_and_edge(self):
        """MATCH (r)-[r]->(m) → diagnostic."""
        result = _analyze("MATCH (r)-[r]->(m) RETURN r")
        self.assertIn("same-pattern-node-edge-conflict", _feature_ids(result))

    def test_different_vars_ok(self):
        """MATCH (n)-[e]->(m) → no diagnostic."""
        result = _analyze("MATCH (n)-[r]->(m) RETURN n")
        self.assertNotIn("same-pattern-node-edge-conflict", _feature_ids(result))

    def test_cross_match_not_flagged(self):
        """Same name across different MATCH clauses → no diagnostic."""
        result = _analyze("MATCH (r) MATCH ()-[r]->() RETURN r")
        self.assertNotIn("same-pattern-node-edge-conflict", _feature_ids(result))

    def test_nested_subquery_not_flagged(self):
        """Same name as edge in nested EXISTS subquery → no diagnostic (different depth)."""
        result = _analyze("MATCH (n WHERE EXISTS { MATCH ()-[n]->() }) RETURN n")
        self.assertNotIn("same-pattern-node-edge-conflict", _feature_ids(result))


# ===========================================================================
# boolean-operand-type — Boolean operator operand type validation (§20.20 SR 3)
# ===========================================================================


class TestBooleanOperandType(unittest.TestCase):
    """boolean-operand-type: boolean operators require boolean-typed operands."""

    def test_not_integer(self):
        """RETURN NOT 0 → diagnostic (integer is not boolean)."""
        result = _analyze("RETURN NOT 0")
        self.assertIn("boolean-operand-type", _feature_ids(result))

    def test_not_string(self):
        """RETURN NOT 'foo' → diagnostic (string is not boolean)."""
        result = _analyze("RETURN NOT 'foo'")
        self.assertIn("boolean-operand-type", _feature_ids(result))

    def test_not_list(self):
        """RETURN NOT [] → diagnostic (list is not boolean)."""
        result = _analyze("RETURN NOT []")
        self.assertIn("boolean-operand-type", _feature_ids(result))

    def test_not_true_ok(self):
        """RETURN NOT true → no diagnostic (boolean is boolean)."""
        result = _analyze("RETURN NOT true")
        self.assertNotIn("boolean-operand-type", _feature_ids(result))

    def test_and_integer_boolean(self):
        """RETURN 123 AND true → diagnostic (integer operand)."""
        result = _analyze("RETURN 123 AND true")
        self.assertIn("boolean-operand-type", _feature_ids(result))

    def test_and_string_boolean(self):
        """RETURN 'foo' AND true → diagnostic (string operand)."""
        result = _analyze("RETURN 'foo' AND true")
        self.assertIn("boolean-operand-type", _feature_ids(result))

    def test_and_booleans_ok(self):
        """RETURN true AND false → no diagnostic."""
        result = _analyze("RETURN true AND false")
        self.assertNotIn("boolean-operand-type", _feature_ids(result))

    def test_or_integer_boolean(self):
        """RETURN 123 OR true → diagnostic (integer operand)."""
        result = _analyze("RETURN 123 OR true")
        self.assertIn("boolean-operand-type", _feature_ids(result))

    def test_or_booleans_ok(self):
        """RETURN true OR false → no diagnostic."""
        result = _analyze("RETURN true OR false")
        self.assertNotIn("boolean-operand-type", _feature_ids(result))

    def test_xor_integer_boolean(self):
        """RETURN 123 XOR true → diagnostic (integer operand)."""
        result = _analyze("RETURN 123 XOR true")
        self.assertIn("boolean-operand-type", _feature_ids(result))

    def test_variable_operand_ok(self):
        """MATCH (n) RETURN NOT n.active → no diagnostic (property is UNKNOWN)."""
        result = _analyze("MATCH (n) RETURN NOT n.active")
        self.assertNotIn("boolean-operand-type", _feature_ids(result))


# ===========================================================================
# orderby-aggregate-without-groupby — Aggregates in ORDER BY (§14.10 SR 4)
# ===========================================================================


class TestOrderByAggregateWithoutGroupBy(unittest.TestCase):
    """orderby-aggregate-without-groupby: aggregate in ORDER BY requires GROUP BY."""

    def test_aggregate_in_orderby_no_groupby(self):
        """MATCH (n) RETURN n.num1 ORDER BY max(n.num2) → diagnostic."""
        result = _analyze("MATCH (n) RETURN n.num1 ORDER BY max(n.num2)")
        self.assertIn("orderby-aggregate-without-groupby", _feature_ids(result))

    def test_aggregate_in_orderby_with_groupby_ok(self):
        """GQL: RETURN with GROUP BY and aggregate → ORDER BY aggregate OK."""
        result = _analyze_gql(
            "MATCH (n) RETURN n.name AS name, count(*) AS cnt GROUP BY name ORDER BY count(*)"
        )
        self.assertNotIn("orderby-aggregate-without-groupby", _feature_ids(result))

    def test_no_aggregate_in_orderby_ok(self):
        """MATCH (n) RETURN n.num ORDER BY n.num → no diagnostic."""
        result = _analyze("MATCH (n) RETURN n.num ORDER BY n.num")
        self.assertNotIn("orderby-aggregate-without-groupby", _feature_ids(result))

    def test_agg_in_return_no_groupby_still_flags(self):
        """ORDER BY aggregate requires BOTH GROUP BY AND aggregate in RETURN items."""
        result = _analyze("MATCH (n) RETURN count(*) AS c ORDER BY count(*)")
        self.assertIn("orderby-aggregate-without-groupby", _feature_ids(result))


# ===========================================================================
# non-constant-skip-limit — SKIP/LIMIT require constant expressions (§16.18-19)
# Always enforced. $param is allowed, but arbitrary variable expressions
# like n.count are never valid per §16.18-19.
# ===========================================================================


class TestNonConstantSkipLimit(unittest.TestCase):
    """non-constant-skip-limit: SKIP/LIMIT require integer literal or parameter."""

    def test_variable_in_skip(self):
        """MATCH (n) RETURN n SKIP n.num → diagnostic."""
        result = _analyze("MATCH (n) RETURN n SKIP n.num")
        self.assertIn("non-constant-skip-limit", _feature_ids(result))

    def test_variable_in_limit(self):
        """MATCH (n) RETURN n LIMIT n.num → diagnostic."""
        result = _analyze("MATCH (n) RETURN n LIMIT n.num")
        self.assertIn("non-constant-skip-limit", _feature_ids(result))

    def test_literal_skip_ok(self):
        """MATCH (n) RETURN n SKIP 5 → no diagnostic."""
        result = _analyze("MATCH (n) RETURN n SKIP 5")
        self.assertNotIn("non-constant-skip-limit", _feature_ids(result))

    def test_literal_limit_ok(self):
        """MATCH (n) RETURN n LIMIT 10 → no diagnostic."""
        result = _analyze("MATCH (n) RETURN n LIMIT 10")
        self.assertNotIn("non-constant-skip-limit", _feature_ids(result))

    def test_param_in_limit_ok(self):
        """MATCH (n) RETURN n LIMIT $num → no diagnostic."""
        result = _analyze("MATCH (n) RETURN n LIMIT $num")
        self.assertNotIn("non-constant-skip-limit", _feature_ids(result))

    def test_aggregate_in_skip(self):
        """MATCH (n) RETURN n SKIP count(*) → diagnostic."""
        result = _analyze("MATCH (n) RETURN n SKIP count(*)")
        self.assertIn("non-constant-skip-limit", _feature_ids(result))


# ===========================================================================
# mixed-focused-ambient — Mixed focused/ambient statements (§9.2 SR 5, §14.2 SR 4)
# ===========================================================================


class TestMixedFocusedAmbient(unittest.TestCase):
    """mixed-focused-ambient: cannot mix focused (USE) and ambient statements."""

    def test_focused_then_ambient_next(self):
        """USE $g MATCH (n) RETURN n NEXT MATCH (n) RETURN n → diagnostic."""
        result = _analyze_gql("USE $g MATCH (n) RETURN n NEXT MATCH (n) RETURN n")
        self.assertIn("mixed-focused-ambient", _feature_ids(result))

    def test_ambient_then_focused_next(self):
        """MATCH (n) RETURN n NEXT USE $g MATCH (n) RETURN n → diagnostic."""
        result = _analyze_gql("MATCH (n) RETURN n NEXT USE $g MATCH (n) RETURN n")
        self.assertIn("mixed-focused-ambient", _feature_ids(result))

    def test_all_focused_next_ok(self):
        """USE $g MATCH (n) RETURN n NEXT USE $g MATCH (m) RETURN m → no diagnostic."""
        result = _analyze_gql("USE $g MATCH (n) RETURN n NEXT USE $g MATCH (m) RETURN m")
        self.assertNotIn("mixed-focused-ambient", _feature_ids(result))

    def test_all_ambient_next_ok(self):
        """MATCH (n) RETURN n NEXT MATCH (m) RETURN m → no diagnostic."""
        result = _analyze_gql("MATCH (n) RETURN n NEXT MATCH (m) RETURN m")
        self.assertNotIn("mixed-focused-ambient", _feature_ids(result))

    def test_three_way_mixed_next(self):
        """Focused, focused, then ambient across three NEXT → diagnostic."""
        result = _analyze_gql(
            "USE $g MATCH (n) RETURN n NEXT USE $g MATCH (m) RETURN m NEXT MATCH (o) RETURN o"
        )
        self.assertIn("mixed-focused-ambient", _feature_ids(result))

    def test_single_statement_ok(self):
        """USE $g MATCH (n) RETURN n → no diagnostic (single statement)."""
        result = _analyze_gql("USE $g MATCH (n) RETURN n")
        self.assertNotIn("mixed-focused-ambient", _feature_ids(result))


# ===========================================================================
# invalid-delete-target — DELETE argument validation (§13.5 SR 5, CR 2)
# ===========================================================================


class TestInvalidDeleteTarget(unittest.TestCase):
    """invalid-delete-target: DELETE requires bare variable references."""

    def test_delete_variable_ok(self):
        """MATCH (n) DELETE n → no diagnostic."""
        result = _analyze("MATCH (n) DELETE n")
        self.assertNotIn("invalid-delete-target", _feature_ids(result))

    def test_detach_delete_variable_ok(self):
        """MATCH (n) DETACH DELETE n → no diagnostic."""
        result = _analyze("MATCH (n) DETACH DELETE n")
        self.assertNotIn("invalid-delete-target", _feature_ids(result))

    def test_delete_labeled_predicate(self):
        """MATCH (n) DELETE n:Person → diagnostic."""
        result = _analyze("MATCH (n) DELETE n:Person")
        self.assertIn("invalid-delete-target", _feature_ids(result))

    def test_delete_arithmetic(self):
        """MATCH (n) DELETE 1 + 1 → diagnostic."""
        result = _analyze("MATCH () DELETE 1 + 1")
        self.assertIn("invalid-delete-target", _feature_ids(result))

    def test_delete_multiple_vars_ok(self):
        """MATCH (n), (m) DELETE n, m → no diagnostic."""
        result = _analyze("MATCH (n), (m) DELETE n, m")
        self.assertNotIn("invalid-delete-target", _feature_ids(result))


# ===========================================================================
# invalid-merge-pattern — MERGE relationship constraints (Cypher-only)
# ===========================================================================


class TestInvalidMergePattern(unittest.TestCase):
    """invalid-merge-pattern: MERGE relationships need exactly one type."""

    def test_merge_with_type_ok(self):
        """MERGE (a)-[:T]->(b) → no diagnostic."""
        result = _analyze("MERGE (a)-[:T]->(b)")
        self.assertNotIn("invalid-merge-pattern", _feature_ids(result))

    def test_merge_no_type_abbreviated(self):
        """MERGE (a)-->(b) → diagnostic (no type on edge)."""
        result = _analyze("MERGE (a)-->(b)")
        self.assertIn("invalid-merge-pattern", _feature_ids(result))

    def test_merge_var_no_type(self):
        """MERGE (a)-[r]->(b) → diagnostic (variable but no type)."""
        result = _analyze("MERGE (a)-[r]->(b)")
        self.assertIn("invalid-merge-pattern", _feature_ids(result))

    def test_merge_multi_type(self):
        """MERGE (a)-[:A|:B]->(b) → diagnostic (multiple types)."""
        result = _analyze("MERGE (a)-[:A|:B]->(b)")
        self.assertIn("invalid-merge-pattern", _feature_ids(result))

    def test_merge_variable_length(self):
        """MERGE (a)-[:FOO*2]->(b) → diagnostic (variable-length)."""
        result = _analyze("MERGE (a)-[:FOO*2]->(b)")
        self.assertIn("invalid-merge-pattern", _feature_ids(result))

    def test_merge_node_only_ok(self):
        """MERGE (n:Person {name: 'x'}) → no diagnostic (node-only)."""
        result = _analyze("MERGE (n:Person {name: 'x'})")
        self.assertNotIn("invalid-merge-pattern", _feature_ids(result))


# ===========================================================================
# exists-no-update — No data-modifying statements inside EXISTS (§19.4)
# ===========================================================================


class TestExistsNoUpdate(unittest.TestCase):
    """exists-no-update: EXISTS cannot contain data-modifying statements."""

    def test_exists_with_set(self):
        """EXISTS { MATCH ... SET ... } → diagnostic."""
        result = _analyze("MATCH (n) WHERE exists { MATCH (n)-->(m) SET m.prop = 1 } RETURN n")
        self.assertIn("exists-no-update", _feature_ids(result))

    def test_exists_match_only_ok(self):
        """EXISTS { MATCH ... } → no diagnostic."""
        result = _analyze("MATCH (n) WHERE exists { MATCH (n)-->(m) } RETURN n")
        self.assertNotIn("exists-no-update", _feature_ids(result))

    def test_exists_with_delete(self):
        """EXISTS { MATCH ... DELETE ... } → diagnostic."""
        result = _analyze("MATCH (n) WHERE exists { MATCH (n)-->(m) DELETE m } RETURN n")
        self.assertIn("exists-no-update", _feature_ids(result))


# ===========================================================================
# type-mismatch — Incompatible operand types in concat/arithmetic
# ===========================================================================


def _analyze_with_ctx(
    query: str, external_context: ExternalContext | None = None
) -> AnalysisResult:
    analyzer = SemanticAnalyzer()
    return analyzer.analyze(_neo4j.parse(query)[0], _neo4j, external_context=external_context)


class TestTypeMismatch(unittest.TestCase):
    """type-mismatch: incompatible types in concatenation and arithmetic."""

    # --- Concatenation ---

    def test_concat_string_and_int(self):
        """STRING || INT → diagnostic (INT not concat-compatible)."""
        ctx = ExternalContext(
            property_types={("T", "s"): GqlType.string(), ("T", "x"): GqlType.integer()}
        )
        result = _analyze_with_ctx("MATCH (n:T) RETURN n.s || n.x", ctx)
        self.assertIn("type-mismatch", _feature_ids(result))
        msgs = [d.message for d in result.diagnostics if d.feature_id == "type-mismatch"]
        self.assertTrue(any("int" in m.lower() for m in msgs))

    def test_concat_string_and_path(self):
        """STRING || PATH → diagnostic (mixed concat kinds)."""
        ctx = ExternalContext(
            property_types={("T", "s"): GqlType.string(), ("T", "p"): GqlType.path()}
        )
        result = _analyze_with_ctx("MATCH (n:T) RETURN n.s || n.p", ctx)
        self.assertIn("type-mismatch", _feature_ids(result))

    def test_concat_strings_ok(self):
        """STRING || STRING → no diagnostic."""
        ctx = ExternalContext(
            property_types={("T", "s1"): GqlType.string(), ("T", "s2"): GqlType.string()}
        )
        result = _analyze_with_ctx("MATCH (n:T) RETURN n.s1 || n.s2", ctx)
        self.assertNotIn("type-mismatch", _feature_ids(result))

    def test_concat_paths_ok(self):
        """PATH || PATH → no diagnostic."""
        result = _analyze_with_ctx("MATCH p = (a)-->(b), q = (c)-->(d) RETURN p || q")
        self.assertNotIn("type-mismatch", _feature_ids(result))

    def test_concat_unknown_ok(self):
        """Unknown properties → no diagnostic (conservative)."""
        result = _analyze_with_ctx("MATCH (n:T) RETURN n.x || n.y")
        self.assertNotIn("type-mismatch", _feature_ids(result))

    def test_concat_one_known_ok(self):
        """Only one operand typed → no diagnostic (<2 concrete)."""
        ctx = ExternalContext(property_types={("T", "s"): GqlType.string()})
        result = _analyze_with_ctx("MATCH (n:T) RETURN n.s || n.y", ctx)
        self.assertNotIn("type-mismatch", _feature_ids(result))

    # --- Additive arithmetic ---

    def test_add_int_and_string(self):
        """INT + STRING → diagnostic (string is 'other')."""
        ctx = ExternalContext(
            property_types={("T", "x"): GqlType.integer(), ("T", "s"): GqlType.string()}
        )
        result = _analyze_with_ctx("MATCH (n:T) RETURN n.x + n.s", ctx)
        self.assertIn("type-mismatch", _feature_ids(result))

    def test_add_int_and_date(self):
        """INT + DATE → diagnostic (numeric + temporal)."""
        ctx = ExternalContext(
            property_types={("T", "x"): GqlType.integer(), ("T", "d"): GqlType.date()}
        )
        result = _analyze_with_ctx("MATCH (n:T) RETURN n.x + n.d", ctx)
        self.assertIn("type-mismatch", _feature_ids(result))

    def test_add_ints_ok(self):
        """INT + INT → no diagnostic."""
        ctx = ExternalContext(
            property_types={("T", "x"): GqlType.integer(), ("T", "y"): GqlType.integer()}
        )
        result = _analyze_with_ctx("MATCH (n:T) RETURN n.x + n.y", ctx)
        self.assertNotIn("type-mismatch", _feature_ids(result))

    def test_add_int_float_ok(self):
        """INT + FLOAT → no diagnostic (both numeric)."""
        ctx = ExternalContext(
            property_types={("T", "x"): GqlType.integer(), ("T", "f"): GqlType.float_()}
        )
        result = _analyze_with_ctx("MATCH (n:T) RETURN n.x + n.f", ctx)
        self.assertNotIn("type-mismatch", _feature_ids(result))

    def test_add_date_duration_ok(self):
        """DATE + DURATION → no diagnostic (temporal + duration)."""
        ctx = ExternalContext(
            property_types={("T", "d"): GqlType.date(), ("T", "dur"): GqlType.duration()}
        )
        result = _analyze_with_ctx("MATCH (n:T) RETURN n.d + n.dur", ctx)
        self.assertNotIn("type-mismatch", _feature_ids(result))

    def test_add_durations_ok(self):
        """DURATION + DURATION → no diagnostic."""
        ctx = ExternalContext(
            property_types={("T", "d1"): GqlType.duration(), ("T", "d2"): GqlType.duration()}
        )
        result = _analyze_with_ctx("MATCH (n:T) RETURN n.d1 + n.d2", ctx)
        self.assertNotIn("type-mismatch", _feature_ids(result))

    # --- Multiplicative arithmetic ---

    def test_mul_string_and_int(self):
        """STRING * INT → diagnostic (string not valid)."""
        ctx = ExternalContext(
            property_types={("T", "s"): GqlType.string(), ("T", "x"): GqlType.integer()}
        )
        result = _analyze_with_ctx("MATCH (n:T) RETURN n.s * n.x", ctx)
        self.assertIn("type-mismatch", _feature_ids(result))

    def test_mul_date_and_int(self):
        """DATE * INT → diagnostic (temporal not valid)."""
        ctx = ExternalContext(
            property_types={("T", "d"): GqlType.date(), ("T", "x"): GqlType.integer()}
        )
        result = _analyze_with_ctx("MATCH (n:T) RETURN n.d * n.x", ctx)
        self.assertIn("type-mismatch", _feature_ids(result))

    def test_mul_duration_and_duration(self):
        """DURATION * DURATION → diagnostic."""
        ctx = ExternalContext(
            property_types={("T", "d1"): GqlType.duration(), ("T", "d2"): GqlType.duration()}
        )
        result = _analyze_with_ctx("MATCH (n:T) RETURN n.d1 * n.d2", ctx)
        self.assertIn("type-mismatch", _feature_ids(result))

    def test_mul_ints_ok(self):
        """INT * INT → no diagnostic."""
        ctx = ExternalContext(
            property_types={("T", "x"): GqlType.integer(), ("T", "y"): GqlType.integer()}
        )
        result = _analyze_with_ctx("MATCH (n:T) RETURN n.x * n.y", ctx)
        self.assertNotIn("type-mismatch", _feature_ids(result))

    def test_mul_duration_and_int_ok(self):
        """DURATION * INT → no diagnostic (scaling)."""
        ctx = ExternalContext(
            property_types={("T", "dur"): GqlType.duration(), ("T", "x"): GqlType.integer()}
        )
        result = _analyze_with_ctx("MATCH (n:T) RETURN n.dur * n.x", ctx)
        self.assertNotIn("type-mismatch", _feature_ids(result))

    # --- Edge cases ---

    def test_literal_arithmetic_ok(self):
        """RETURN 1 + 2 → no diagnostic (both numeric literals)."""
        result = _analyze_with_ctx("RETURN 1 + 2")
        self.assertNotIn("type-mismatch", _feature_ids(result))

    def test_no_steps_no_diagnostic(self):
        """RETURN 42 → no diagnostic (no operations)."""
        result = _analyze_with_ctx("RETURN 42")
        self.assertNotIn("type-mismatch", _feature_ids(result))

    def test_concat_node_vars_via_validate(self):
        """End-to-end: NODE || NODE through Dialect.validate() pipeline."""
        result = _neo4j.validate("MATCH (n), (m) RETURN n || m")
        self.assertFalse(result.success)
        diag_codes = {d.code for d in result.all_diagnostics}
        self.assertIn("type-mismatch", diag_codes)
