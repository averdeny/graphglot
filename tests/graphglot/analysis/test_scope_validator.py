"""Tests for scope validation rules.

variable-type-conflict   — Cross-clause node/edge type mismatch
variable-already-bound   — Re-declaration in CREATE/MERGE/YIELD
undefined-variable       — Reference to variable not in current scope
return-star-no-variables — RETURN * with no variables in scope

These rules fire unconditionally — they are not gated on dialect features.
"""

from __future__ import annotations

import unittest

from graphglot.analysis import AnalysisResult, SemanticAnalyzer
from graphglot.dialect import Dialect
from graphglot.dialect.neo4j import Neo4j

_neo4j = Neo4j()
_full = Dialect()


def _analyze(query: str, dialect: Dialect | None = None) -> AnalysisResult:
    d = dialect or _neo4j
    analyzer = SemanticAnalyzer()
    ast_nodes = d.parse(query)
    transformed = d.transform(ast_nodes)
    return analyzer.analyze(transformed[0], d)


def _feature_ids(result: AnalysisResult) -> set[str]:
    return {d.feature_id for d in result.diagnostics}


def _messages_for(result: AnalysisResult, rule: str) -> list[str]:
    return [d.message for d in result.diagnostics if d.feature_id == rule]


def _cached_scope_rule_feature_ids(query: str, rule_fn, stale_feature_id: str) -> set[str]:
    """Return feature ids after poisoning the scope-rule cache with a reused integer id."""
    from graphglot.analysis.models import AnalysisContext, SemanticDiagnostic
    from graphglot.analysis.rules import scope_validator

    dialect = Neo4j()
    expr = dialect.transform(dialect.parse(query))[0]
    bogus = [
        SemanticDiagnostic(
            feature_id=stale_feature_id,
            message="bogus",
            node=expr,
        )
    ]
    scope_validator._scope_walk_cache = (id(expr), bogus)
    try:
        diagnostics = rule_fn(AnalysisContext(expression=expr, dialect=dialect, lineage=None))
    finally:
        scope_validator._scope_walk_cache = (None, [])
    return {diagnostic.feature_id for diagnostic in diagnostics}


# ===========================================================================
# variable-type-conflict — Cross-clause node/edge type mismatch
# ===========================================================================


class TestVariableTypeConflict(unittest.TestCase):
    """variable-type-conflict: same variable as different element kinds across clauses."""

    def test_cross_match_node_then_edge(self):
        """MATCH (r) MATCH ()-[r]->() RETURN r → diagnostic."""
        result = _analyze("MATCH (r) MATCH ()-[r]->() RETURN r")
        self.assertIn("variable-type-conflict", _feature_ids(result))
        msgs = _messages_for(result, "variable-type-conflict")
        self.assertTrue(any("r" in m for m in msgs))

    def test_cross_match_edge_then_node(self):
        """MATCH ()-[r]->() MATCH (r) RETURN r → diagnostic."""
        result = _analyze("MATCH ()-[r]->() MATCH (r) RETURN r")
        self.assertIn("variable-type-conflict", _feature_ids(result))

    def test_same_kind_cross_match_ok(self):
        """MATCH (a) MATCH (a)-[:T]->() RETURN a → no diagnostic (both node)."""
        result = _analyze("MATCH (a) MATCH (a)-[:T]->() RETURN a")
        self.assertNotIn("variable-type-conflict", _feature_ids(result))

    def test_path_vs_node_conflict(self):
        """MATCH (p) MATCH p = ()-[r]->() RETURN p → diagnostic."""
        result = _analyze("MATCH (p) MATCH p = ()-[r]->() RETURN p")
        self.assertIn("variable-type-conflict", _feature_ids(result))

    def test_single_match_ok(self):
        """MATCH (n)-[r]->(m) RETURN n → no diagnostic."""
        result = _analyze("MATCH (n)-[r]->(m) RETURN n")
        self.assertNotIn("variable-type-conflict", _feature_ids(result))

    def test_edge_same_kind_cross_match_ok(self):
        """MATCH ()-[r]->() MATCH ()-[r]->() RETURN r → no diagnostic (both edge)."""
        result = _analyze("MATCH ()-[r]->() MATCH ()-[r]->() RETURN r")
        self.assertNotIn("variable-type-conflict", _feature_ids(result))

    def test_with_boundary_resets_scope(self):
        """WITH boundary preserves type tracking → diagnostic."""
        result = _analyze("MATCH (r) WITH r AS r MATCH ()-[r]->() RETURN r")
        self.assertIn("variable-type-conflict", _feature_ids(result))

    def test_scope_cache_ignores_reused_integer_ids(self):
        """A stale integer-id cache entry must not suppress type-conflict diagnostics."""
        from graphglot.analysis.rules.scope_validator import check_variable_type_conflict

        ids = _cached_scope_rule_feature_ids(
            "MATCH (r) MATCH ()-[r]->() RETURN r",
            check_variable_type_conflict,
            stale_feature_id="undefined-variable",
        )
        self.assertIn("variable-type-conflict", ids)


# ===========================================================================
# variable-already-bound — Re-declaration in CREATE/MERGE
# ===========================================================================


class TestVariableAlreadyBound(unittest.TestCase):
    """variable-already-bound: re-declaring a bound variable in CREATE/MERGE."""

    def test_create_rebind_matched(self):
        """MATCH (a) CREATE (a) → diagnostic (Cypher CREATE: all vars must be new)."""
        result = _analyze("MATCH (a) CREATE (a)")
        self.assertIn("variable-already-bound", _feature_ids(result))

    def test_create_new_var_ok(self):
        """MATCH (a) CREATE (b) → no diagnostic."""
        result = _analyze("MATCH (a) CREATE (b)")
        self.assertNotIn("variable-already-bound", _feature_ids(result))

    def test_merge_rebind_existing(self):
        """MATCH (a) MERGE (a)-[:T]->(b) → no diagnostic (bare filler = reference)."""
        result = _analyze("MATCH (a) MERGE (a)-[:T]->(b)")
        self.assertNotIn("variable-already-bound", _feature_ids(result))

    def test_create_rebind_edge(self):
        """MATCH ()-[r]->() CREATE ()-[r]->() → diagnostic."""
        result = _analyze("MATCH ()-[r]->() CREATE ({name:'x'})-[r:T]->({name:'y'})")
        self.assertIn("variable-already-bound", _feature_ids(result))

    def test_create_after_create_ok(self):
        """CREATE (a) CREATE (b) → no diagnostic (both new)."""
        result = _analyze("CREATE (a) CREATE (b)")
        self.assertNotIn("variable-already-bound", _feature_ids(result))

    def test_insert_reuse_variable_in_same_statement(self):
        """INSERT (a:Person), (a)-[:KNOWS]->(b:Person) → no diagnostic.

        Bare (a) in a later path pattern is a reference to the already-declared
        variable, not a re-declaration.
        """
        result = _analyze(
            'INSERT (a:Person {name: "Andy"}),'
            '       (b:Person {name: "Boris"}),'
            "       (a)-[:HAS]->(b)"
        )
        self.assertNotIn("variable-already-bound", _feature_ids(result))

    def test_insert_multi_path_reuse_many_variables(self):
        """Complex INSERT with many cross-references → no diagnostic."""
        result = _analyze(
            'INSERT (a:Person {name: "Andy"}),'
            '       (b:Person {name: "Boris"}),'
            '       (c:Person {name: "Charlie"}),'
            '       (d:Person {name: "David"}),'
            '       (pb:Pet {name: "Boris"})<-[:HAS]-(a)-[:HAS]->(pa:Pet {name: "Andy"}),'
            "       (b)-[:HAS]->(pb),"
            "       (c)-[:HAS]->(pa)"
        )
        self.assertNotIn("variable-already-bound", _feature_ids(result))

    def test_insert_true_redeclaration_still_flagged(self):
        """INSERT (a:Person), (a:Dog) → diagnostic (both have labels = true redeclaration)."""
        result = _analyze("INSERT (a:Person), (a:Dog)")
        self.assertIn("variable-already-bound", _feature_ids(result))

    def test_insert_all_bare_reuse(self):
        """INSERT (a), (b), (a)-[:KNOWS]->(b) → no diagnostic (all bare reuse)."""
        result = _analyze("INSERT (a), (b), (a)-[:KNOWS]->(b)")
        self.assertNotIn("variable-already-bound", _feature_ids(result))

    def test_insert_properties_on_repeated_var(self):
        """INSERT (a:Person), (a {age: 30}) → diagnostic (properties on repeated var)."""
        result = _analyze("INSERT (a:Person), (a {age: 30})")
        self.assertIn("variable-already-bound", _feature_ids(result))

    def test_create_reuse_in_same_statement(self):
        """CREATE (a:Person), (a)-[:KNOWS]->(b:Person) → no diagnostic."""
        result = _analyze("CREATE (a:Person), (a)-[:KNOWS]->(b:Person)")
        self.assertNotIn("variable-already-bound", _feature_ids(result))


# ===========================================================================
# undefined-variable — Reference to variable not in scope
# ===========================================================================


class TestUndefinedVariable(unittest.TestCase):
    """undefined-variable: referencing a variable not in current scope."""

    def test_with_hides_original_vars(self):
        """MATCH (a) WITH a.name AS foo RETURN a → diagnostic (a not in scope after WITH)."""
        result = _analyze("MATCH (a) WITH a.name AS foo RETURN a")
        self.assertIn("undefined-variable", _feature_ids(result))
        msgs = _messages_for(result, "undefined-variable")
        self.assertTrue(any("a" in m for m in msgs))

    def test_with_projected_var_ok(self):
        """MATCH (a) WITH a AS b RETURN b → no diagnostic."""
        result = _analyze("MATCH (a) WITH a AS b RETURN b")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_undefined_in_return(self):
        """RETURN x → diagnostic."""
        result = _analyze("RETURN x")
        self.assertIn("undefined-variable", _feature_ids(result))

    def test_match_var_in_return_ok(self):
        """MATCH (n) RETURN n → no diagnostic."""
        result = _analyze("MATCH (n) RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_with_star_preserves_scope(self):
        """MATCH (a) WITH * RETURN a → no diagnostic."""
        result = _analyze("MATCH (a) WITH * RETURN a")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_undefined_after_with_chain(self):
        """MATCH (a), (b) WITH a AS x RETURN b → diagnostic (b hidden by WITH)."""
        result = _analyze("MATCH (a), (b) WITH a AS x RETURN b")
        self.assertIn("undefined-variable", _feature_ids(result))

    def test_scope_cache_ignores_reused_integer_ids(self):
        """A stale integer-id cache entry must not suppress undefined-variable diagnostics."""
        from graphglot.analysis.rules.scope_validator import check_undefined_variable

        ids = _cached_scope_rule_feature_ids(
            "MATCH (a), (b) WITH a AS x RETURN b",
            check_undefined_variable,
            stale_feature_id="variable-type-conflict",
        )
        self.assertIn("undefined-variable", ids)

    def test_with_alias_available_in_return(self):
        """MATCH (n) WITH n.name AS name RETURN name → no diagnostic."""
        result = _analyze("MATCH (n) WITH n.name AS name RETURN name")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_undefined_in_where_after_with(self):
        """MATCH (a) WITH a.name AS name WHERE a.age > 25 RETURN name → diagnostic."""
        result = _analyze("MATCH (a) WITH a.name AS name WHERE a.age > 25 RETURN name")
        self.assertIn("undefined-variable", _feature_ids(result))

    def test_match_after_with_uses_projected_scope(self):
        """MATCH (a) WITH a AS x MATCH (x)-[r]->(b) RETURN b → no diagnostic."""
        result = _analyze("MATCH (a) WITH a AS x MATCH (x)-[r]->(b) RETURN b")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_property_ref_ok(self):
        """MATCH (n) RETURN n.name → no diagnostic (n in scope, name is property)."""
        result = _analyze("MATCH (n) RETURN n.name")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_parameter_ref_not_undefined(self):
        """RETURN $n → no diagnostic (parameters are not binding variables)."""
        result = _analyze("RETURN $n")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_parameter_ref_in_where_not_undefined(self):
        """MATCH (a) WHERE a.name = $name RETURN a → no diagnostic."""
        result = _analyze("MATCH (a) WHERE a.name = $name RETURN a")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_parameter_ref_in_set_not_undefined(self):
        """MATCH (n) SET n.val = $v RETURN n → no diagnostic."""
        result = _analyze("MATCH (n) SET n.val = $v RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_substituted_parameter_ref_not_undefined(self):
        """RETURN GRAPH $$my_graph → no diagnostic (substituted parameter, not a variable)."""
        result = _analyze("RETURN GRAPH $$my_graph", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_for_ordinality_binding_in_scope(self):
        """FOR x IN [1,2,3] WITH ORDINALITY i RETURN x, i → no diagnostic."""
        result = _analyze("FOR x IN [1,2,3] WITH ORDINALITY i RETURN x, i", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_for_offset_binding_in_scope(self):
        """FOR x IN [1,2,3] WITH OFFSET i RETURN x, i → no diagnostic."""
        result = _analyze("FOR x IN [1,2,3] WITH OFFSET i RETURN x, i", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_graph_name_not_undefined(self):
        """RETURN GRAPH my_graph → no diagnostic (catalog graph name, not a variable)."""
        result = _analyze("RETURN GRAPH my_graph", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_graph_name_in_use_not_undefined(self):
        """USE my_graph MATCH (n) RETURN n → no diagnostic."""
        result = _analyze("USE my_graph MATCH (n) RETURN n", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_nested_subquery_scope_isolation(self):
        """RETURN TABLE { MATCH (n) RETURN n } → no diagnostic (n is bound in subquery)."""
        result = _analyze("RETURN TABLE { MATCH (n) RETURN n }", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_exists_subquery_scope_isolation(self):
        """MATCH (a) WHERE EXISTS { MATCH (a)-[r]->(b) } RETURN a → no diagnostic."""
        result = _analyze("MATCH (a) WHERE EXISTS { MATCH (a)-[r]->(b) } RETURN a")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_call_subquery_exports_to_outer_scope(self):
        """CALL { RETURN 1 AS x } RETURN x → no diagnostic."""
        result = _analyze("CALL { RETURN 1 AS x } RETURN x", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_call_subquery_alias_export(self):
        """CALL { RETURN 'hello' AS greeting } RETURN greeting → no diagnostic."""
        result = _analyze("CALL { RETURN 'hello' AS greeting } RETURN greeting", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_call_subquery_imports_outer_scope(self):
        """MATCH (a) CALL { RETURN a.name AS val } RETURN val → no diagnostic."""
        result = _analyze("MATCH (a) CALL { RETURN a.name AS val } RETURN val", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_named_procedure_yield_in_scope(self):
        """CALL my_proc() YIELD result RETURN result → no diagnostic."""
        result = _analyze("CALL my_proc() YIELD result RETURN result", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_named_procedure_yield_alias_in_scope(self):
        """CALL my_proc() YIELD result AS r RETURN r → no diagnostic."""
        result = _analyze("CALL my_proc() YIELD result AS r RETURN r", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))


# ===========================================================================
# NEXT chain scope propagation (WITH → RETURN...NEXT transform)
# ===========================================================================


class TestNextScopePropagation(unittest.TestCase):
    """Tests for scope propagation through NEXT chains (transformed WITH)."""

    def test_next_scope_propagation(self):
        """MATCH (a) WITH a.name AS foo RETURN foo → no diagnostic."""
        result = _analyze("MATCH (a) WITH a.name AS foo RETURN foo")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_next_scope_filters_undefined(self):
        """MATCH (a) WITH a AS b RETURN a → diagnostic (a hidden by WITH/NEXT)."""
        result = _analyze("MATCH (a) WITH a AS b RETURN a")
        self.assertIn("undefined-variable", _feature_ids(result))

    def test_next_type_conflict(self):
        """MATCH (r) WITH r AS r MATCH ()-[r]->() RETURN r → type conflict across NEXT."""
        result = _analyze("MATCH (r) WITH r AS r MATCH ()-[r]->() RETURN r")
        self.assertIn("variable-type-conflict", _feature_ids(result))

    def test_next_filter_undefined(self):
        """MATCH (a) WITH a.name AS name WHERE a.age > 25 RETURN name → diagnostic."""
        result = _analyze("MATCH (a) WITH a.name AS name WHERE a.age > 25 RETURN name")
        self.assertIn("undefined-variable", _feature_ids(result))

    def test_multi_next_chain(self):
        """MATCH (a),(b) WITH a WITH a.name AS n RETURN n, b → b undefined in final block."""
        result = _analyze("MATCH (a),(b) WITH a WITH a.name AS n RETURN n, b")
        self.assertIn("undefined-variable", _feature_ids(result))

    def test_next_already_bound(self):
        """MATCH (a) WITH a MATCH (b) CREATE (a) RETURN b → diagnostic (bare-only CREATE)."""
        result = _analyze("MATCH (a) WITH a MATCH (b) CREATE (a) RETURN b")
        self.assertIn("variable-already-bound", _feature_ids(result))


# ===========================================================================
# Focused (USE graph) statement scope
# ===========================================================================


class TestFocusedStatementScope(unittest.TestCase):
    """Scope validation for focused (USE graph) statements."""

    def test_focused_type_conflict_across_next(self):
        """USE g MATCH (n) RETURN n.name AS name NEXT USE g MATCH (name) RETURN name."""
        result = _analyze(
            "USE myGraph MATCH (n) RETURN n.name AS name NEXT USE myGraph MATCH (name) RETURN name",
            dialect=_full,
        )
        self.assertIn("variable-type-conflict", _feature_ids(result))

    def test_focused_undefined_across_next(self):
        """USE g MATCH (a) RETURN a AS b NEXT USE g RETURN a → undefined."""
        result = _analyze(
            "USE myGraph MATCH (a) RETURN a AS b NEXT USE myGraph RETURN a",
            dialect=_full,
        )
        self.assertIn("undefined-variable", _feature_ids(result))

    def test_focused_bare_var_forward_ok(self):
        """USE g MATCH (n) RETURN n NEXT USE g MATCH (n) RETURN n → no conflict."""
        result = _analyze(
            "USE myGraph MATCH (n) RETURN n NEXT USE myGraph MATCH (n) RETURN n",
            dialect=_full,
        )
        self.assertNotIn("variable-type-conflict", _feature_ids(result))

    def test_focused_already_bound(self):
        """USE g MATCH (a) RETURN a NEXT ... INSERT (a) → no diagnostic (bare ref)."""
        result = _analyze(
            "USE myGraph MATCH (a) RETURN a NEXT USE myGraph MATCH (b) INSERT (a) RETURN b",
            dialect=_full,
        )
        self.assertNotIn("variable-already-bound", _feature_ids(result))


# ===========================================================================
# Value-kind tracking — WITH scalar projection → pattern conflict
# ===========================================================================


class TestValueKindTracking(unittest.TestCase):
    """Detect type conflicts when WITH projects a scalar and the next block uses it as element."""

    def test_literal_as_node(self):
        """WITH 123 AS n MATCH (n) RETURN n → type conflict."""
        result = _analyze("WITH 123 AS n MATCH (n) RETURN n")
        self.assertIn("variable-type-conflict", _feature_ids(result))

    def test_literal_as_edge(self):
        """WITH 123 AS r MATCH ()-[r]-() RETURN r → type conflict."""
        result = _analyze("WITH 123 AS r MATCH ()-[r]-() RETURN r")
        self.assertIn("variable-type-conflict", _feature_ids(result))

    def test_literal_as_path(self):
        """WITH 123 AS p MATCH p = ()-[]->() RETURN p → type conflict."""
        result = _analyze("WITH 123 AS p MATCH p = ()-[]->() RETURN p")
        self.assertIn("variable-type-conflict", _feature_ids(result))

    def test_list_wrap_as_node(self):
        """MATCH (n) WITH [n] AS users MATCH (users) RETURN users → type conflict."""
        result = _analyze("MATCH (n) WITH [n] AS users MATCH (users) RETURN users")
        self.assertIn("variable-type-conflict", _feature_ids(result))

    def test_bare_var_rename_ok(self):
        """MATCH (n) WITH n AS m MATCH (m) RETURN m → no conflict (inherits node)."""
        result = _analyze("MATCH (n) WITH n AS m MATCH (m) RETURN m")
        self.assertNotIn("variable-type-conflict", _feature_ids(result))

    def test_bare_var_forward_ok(self):
        """MATCH (n) WITH n MATCH (n) RETURN n → no conflict."""
        result = _analyze("MATCH (n) WITH n MATCH (n) RETURN n")
        self.assertNotIn("variable-type-conflict", _feature_ids(result))

    def test_star_forward_ok(self):
        """MATCH (n) WITH * MATCH (n) RETURN n → no conflict."""
        result = _analyze("MATCH (n) WITH * MATCH (n) RETURN n")
        self.assertNotIn("variable-type-conflict", _feature_ids(result))

    def test_with_shadow_type_conflict(self):
        """MATCH (n) WITH 1 AS n MATCH (n) RETURN n → type-conflict."""
        result = _analyze("MATCH (n) WITH 1 AS n MATCH (n) RETURN n")
        self.assertIn("variable-type-conflict", _feature_ids(result))


# ===========================================================================
# Undefined-variable extensions — DELETE, SET, CREATE, MERGE
# ===========================================================================


class TestUndefinedVariableExtensions(unittest.TestCase):
    """Detect undefined variables in DELETE, SET, CREATE properties, and MERGE."""

    def test_undefined_in_delete(self):
        """MATCH (a) DELETE x → undefined variable."""
        result = _analyze("MATCH (a) DELETE x")
        self.assertIn("undefined-variable", _feature_ids(result))

    def test_undefined_in_set(self):
        """MATCH (n) SET x.num = 1 → undefined variable."""
        result = _analyze("MATCH (n) SET x.num = 1")
        self.assertIn("undefined-variable", _feature_ids(result))

    def test_undefined_in_create_property(self):
        """CREATE (b {name: missing}) → undefined variable."""
        result = _analyze("CREATE (b {name: missing})")
        self.assertIn("undefined-variable", _feature_ids(result))

    def test_undefined_in_merge_on_create(self):
        """MERGE (n) ON CREATE SET x.num = 1 → undefined variable."""
        result = _analyze("MERGE (n) ON CREATE SET x.num = 1")
        self.assertIn("undefined-variable", _feature_ids(result))

    def test_undefined_in_merge_on_match(self):
        """MERGE (n) ON MATCH SET x.num = 1 → undefined variable."""
        result = _analyze("MERGE (n) ON MATCH SET x.num = 1")
        self.assertIn("undefined-variable", _feature_ids(result))


# ===========================================================================
# return-star-no-variables — RETURN * with no variables in scope (§14.11 SR 6a)
# ===========================================================================


class TestReturnStarNoVariables(unittest.TestCase):
    """return-star-no-variables: RETURN * requires variables in scope."""

    def test_return_star_no_variables(self):
        """MATCH () RETURN * → diagnostic (no named variables in scope)."""
        result = _analyze("MATCH () RETURN *")
        self.assertIn("return-star-no-variables", _feature_ids(result))

    def test_return_star_with_variables_ok(self):
        """MATCH (n) RETURN * → no diagnostic."""
        result = _analyze("MATCH (n) RETURN *")
        self.assertNotIn("return-star-no-variables", _feature_ids(result))


# ===========================================================================
# Non-variable identifiers — must not be flagged as undefined
# ===========================================================================


class TestNonVariableIdentifiers(unittest.TestCase):
    """Identifiers that are property names, field names, or type names — not variables."""

    def test_property_exists_predicate_property_name(self):
        """PROPERTY_EXISTS(n, name) → 'name' is a property name, not a variable."""
        result = _analyze("MATCH (n:Person) WHERE PROPERTY_EXISTS(n, name) RETURN n", dialect=_full)
        msgs = _messages_for(result, "undefined-variable")
        self.assertFalse(
            any("name" in m for m in msgs),
            f"'name' wrongly flagged as undefined: {msgs}",
        )

    def test_record_type_field_name(self):
        """IS TYPED {name STRING} → 'name' is a field name in a record type."""
        result = _analyze("MATCH (n) WHERE n.x IS TYPED {name STRING} RETURN n", dialect=_full)
        msgs = _messages_for(result, "undefined-variable")
        self.assertFalse(
            any("name" in m for m in msgs),
            f"'name' wrongly flagged as undefined: {msgs}",
        )

    def test_binding_table_type_field_name(self):
        """IS TYPED TABLE {name STRING} → 'name' is a field name in a table type."""
        result = _analyze(
            "MATCH (n) WHERE n.x IS TYPED TABLE {name STRING} RETURN n", dialect=_full
        )
        msgs = _messages_for(result, "undefined-variable")
        self.assertFalse(
            any("name" in m for m in msgs),
            f"'name' wrongly flagged as undefined: {msgs}",
        )

    def test_let_value_expression_binding(self):
        """RETURN LET x = 1 IN x + 1 END → 'x' is bound by LET, not undefined."""
        result = _analyze("RETURN LET x = 1 IN x + 1 END", dialect=_full)
        msgs = _messages_for(result, "undefined-variable")
        self.assertFalse(
            any("x" in m for m in msgs),
            f"'x' wrongly flagged as undefined: {msgs}",
        )

    def test_let_value_expression_rhs_checked(self):
        """RETURN LET x = y IN x END → 'y' IS undefined (in the RHS, not bound by LET)."""
        result = _analyze("RETURN LET x = y IN x END", dialect=_full)
        msgs = _messages_for(result, "undefined-variable")
        self.assertTrue(
            any("y" in m for m in msgs),
            f"'y' should be flagged as undefined: {msgs}",
        )

    def test_let_value_expression_with_match(self):
        """MATCH (n) RETURN LET x = n.val IN x * 2 END → no diagnostic."""
        result = _analyze("MATCH (n) RETURN LET x = n.val IN x * 2 END", dialect=_full)
        msgs = _messages_for(result, "undefined-variable")
        self.assertEqual(msgs, [], f"Unexpected undefined-variable diagnostics: {msgs}")


# ===========================================================================
# LET statement scope — new handler required
# ===========================================================================


class TestLetStatementScope(unittest.TestCase):
    """LET binds variables that should be visible in subsequent clauses."""

    def test_let_single_ok(self):
        """LET x = 1 RETURN x → no diagnostic."""
        result = _analyze("LET x = 1 RETURN x", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_let_multiple_ok(self):
        """LET x = 1, y = 2 RETURN x, y → no diagnostic."""
        result = _analyze("LET x = 1, y = 2 RETURN x, y", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_let_undefined(self):
        """LET x = 1 RETURN y → undefined-variable."""
        result = _analyze("LET x = 1 RETURN y", dialect=_full)
        self.assertIn("undefined-variable", _feature_ids(result))
        msgs = _messages_for(result, "undefined-variable")
        self.assertTrue(any("y" in m for m in msgs))

    def test_let_after_match_ok(self):
        """MATCH (n) LET x = n.name RETURN x → no diagnostic."""
        result = _analyze("MATCH (n) LET x = n.name RETURN x", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_let_before_match_ok(self):
        """LET x = 1 MATCH (n) WHERE n.id = x RETURN n → no diagnostic."""
        result = _analyze("LET x = 1 MATCH (n) WHERE n.id = x RETURN n", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_let_after_with_ok(self):
        """MATCH (a) WITH a LET x = a.name RETURN x → no diagnostic (Neo4j WITH + LET)."""
        result = _analyze("MATCH (a) WITH a LET x = a.name RETURN x")
        self.assertNotIn("undefined-variable", _feature_ids(result))


# ===========================================================================
# OPTIONAL MATCH scope
# ===========================================================================


class TestOptionalMatchScope(unittest.TestCase):
    """OPTIONAL MATCH bindings are visible in subsequent clauses."""

    def test_optional_match_after_match_ok(self):
        """MATCH (a) OPTIONAL MATCH (a)-[r]->(b) RETURN a, b → no diagnostic."""
        result = _analyze("MATCH (a) OPTIONAL MATCH (a)-[r]->(b) RETURN a, b")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_optional_match_standalone_ok(self):
        """OPTIONAL MATCH (a) RETURN a → no diagnostic."""
        result = _analyze("OPTIONAL MATCH (a) RETURN a")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_optional_match_edge_ok(self):
        """OPTIONAL MATCH (a)-[r]->(b) RETURN a, r, b → no diagnostic."""
        result = _analyze("OPTIONAL MATCH (a)-[r]->(b) RETURN a, r, b")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_optional_match_cross_ref_ok(self):
        """MATCH (a) OPTIONAL MATCH (b) WHERE b.id = a.id RETURN a, b → no diagnostic."""
        result = _analyze("MATCH (a) OPTIONAL MATCH (b) WHERE b.id = a.id RETURN a, b")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_optional_match_hidden_by_with(self):
        """MATCH (a) OPTIONAL MATCH (b) WITH a RETURN b → undefined (b hidden)."""
        result = _analyze("MATCH (a) OPTIONAL MATCH (b) WITH a RETURN b")
        self.assertIn("undefined-variable", _feature_ids(result))


# ===========================================================================
# UNION scope isolation
# ===========================================================================


class TestUnionScopeIsolation(unittest.TestCase):
    """UNION/INTERSECT branches have independent scopes."""

    def test_union_both_ok(self):
        """RETURN 1 AS x UNION RETURN 2 AS x → no diagnostic."""
        result = _analyze("RETURN 1 AS x UNION RETURN 2 AS x", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_union_match_both_ok(self):
        """MATCH (a) RETURN a.name AS n UNION MATCH (b) RETURN b.name AS n → no diagnostic."""
        result = _analyze(
            "MATCH (a) RETURN a.name AS n UNION MATCH (b) RETURN b.name AS n", dialect=_full
        )
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_union_second_branch_undefined(self):
        """Second UNION branch references undefined variable."""
        result = _analyze("MATCH (a) RETURN a.name AS n UNION RETURN x AS n", dialect=_full)
        self.assertIn("undefined-variable", _feature_ids(result))

    def test_union_all_ok(self):
        """MATCH (a) RETURN a AS x UNION ALL MATCH (b) RETURN b AS x → no diagnostic."""
        result = _analyze(
            "MATCH (a) RETURN a AS x UNION ALL MATCH (b) RETURN b AS x", dialect=_full
        )
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_intersect_ok(self):
        """RETURN 1 AS x INTERSECT RETURN 2 AS x → no diagnostic."""
        result = _analyze("RETURN 1 AS x INTERSECT RETURN 2 AS x", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))


# ===========================================================================
# CALL subquery — advanced patterns
# ===========================================================================


class TestCallSubqueryAdvanced(unittest.TestCase):
    """Advanced CALL { ... } patterns for scope export, chaining, and import."""

    def test_call_match_export(self):
        """CALL { MATCH (n) RETURN n } RETURN n → no diagnostic."""
        result = _analyze("CALL { MATCH (n) RETURN n } RETURN n", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_call_alias_export(self):
        """CALL { MATCH (n) RETURN n.name AS name } RETURN name → no diagnostic."""
        result = _analyze("CALL { MATCH (n) RETURN n.name AS name } RETURN name", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_call_chained_exports(self):
        """Chained CALL subqueries propagate exports."""
        result = _analyze(
            "MATCH (a) CALL { RETURN a.name AS val } CALL { RETURN val AS msg } RETURN msg",
            dialect=_full,
        )
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_call_sequential_exports(self):
        """Sequential CALL subqueries export independently."""
        result = _analyze(
            "CALL { RETURN 1 AS x } CALL { RETURN 2 AS y } RETURN x, y", dialect=_full
        )
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_call_partial_export_undefined(self):
        """CALL { RETURN 1 AS x } RETURN x, y → undefined (y)."""
        result = _analyze("CALL { RETURN 1 AS x } RETURN x, y", dialect=_full)
        self.assertIn("undefined-variable", _feature_ids(result))

    def test_call_export_used_in_match(self):
        """CALL exports usable in subsequent MATCH."""
        result = _analyze("CALL { MATCH (n) RETURN n } MATCH (n)-[r]->(m) RETURN m", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_call_import_and_export(self):
        """CALL imports outer scope and exports RETURN projections."""
        result = _analyze(
            "MATCH (a) CALL { MATCH (a)-[r]->(b) RETURN b } RETURN a, b", dialect=_full
        )
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_call_export_in_where(self):
        """CALL export usable in subsequent WHERE."""
        result = _analyze("CALL { RETURN 1 AS x } MATCH (n) WHERE n.id = x RETURN n", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))


# ===========================================================================
# Named procedure YIELD — advanced patterns
# ===========================================================================


class TestNamedProcedureYieldAdvanced(unittest.TestCase):
    """Advanced CALL proc() YIELD patterns."""

    def test_yield_multiple_ok(self):
        """CALL proc() YIELD a, b RETURN a, b → no diagnostic."""
        result = _analyze("CALL proc() YIELD a, b RETURN a, b", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_yield_aliases_ok(self):
        """CALL proc() YIELD a AS x, b AS y RETURN x, y → no diagnostic."""
        result = _analyze("CALL proc() YIELD a AS x, b AS y RETURN x, y", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_yield_with_match_ok(self):
        """MATCH (n) CALL proc(n) YIELD result RETURN n, result → no diagnostic."""
        result = _analyze("MATCH (n) CALL proc(n) YIELD result RETURN n, result", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_yield_undefined_ref(self):
        """CALL proc() YIELD result RETURN missing → undefined."""
        result = _analyze("CALL proc() YIELD result RETURN missing", dialect=_full)
        self.assertIn("undefined-variable", _feature_ids(result))


# ===========================================================================
# EXISTS subquery — advanced patterns
# ===========================================================================


class TestExistsSubqueryAdvanced(unittest.TestCase):
    """EXISTS { ... } subqueries isolate their scope."""

    def test_exists_with_outer_ref_ok(self):
        """MATCH (a) WHERE EXISTS { MATCH (a)-[r]->(b) WHERE b.age > 10 } RETURN a → OK."""
        result = _analyze("MATCH (a) WHERE EXISTS { MATCH (a)-[r]->(b) WHERE b.age > 10 } RETURN a")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_not_exists_ok(self):
        """MATCH (a) WHERE NOT EXISTS { MATCH (a)-[r]->(b) } RETURN a → OK."""
        result = _analyze("MATCH (a) WHERE NOT EXISTS { MATCH (a)-[r]->(b) } RETURN a")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_exists_independent_ok(self):
        """MATCH (a) WHERE EXISTS { MATCH (b) } RETURN a → OK."""
        result = _analyze("MATCH (a) WHERE EXISTS { MATCH (b) } RETURN a")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_exists_scope_isolation(self):
        """MATCH (a) WHERE EXISTS { MATCH (b) } RETURN a, b → b undefined (isolated)."""
        result = _analyze("MATCH (a) WHERE EXISTS { MATCH (b) } RETURN a, b")
        self.assertIn("undefined-variable", _feature_ids(result))


# ===========================================================================
# Complex WITH chains (Neo4j dialect — CypherWithStatement transform)
# ===========================================================================


class TestComplexWithChains(unittest.TestCase):
    """Complex WITH projection chains with filtering and ordering."""

    def test_with_multi_projection_ok(self):
        """MATCH (a), (b) WITH a.name AS x, b.name AS y RETURN x, y → no diagnostic."""
        result = _analyze("MATCH (a), (b) WITH a.name AS x, b.name AS y RETURN x, y")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_double_with_ok(self):
        """MATCH (a) WITH a WITH a.name AS name RETURN name → no diagnostic."""
        result = _analyze("MATCH (a) WITH a WITH a.name AS name RETURN name")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_with_where_ok(self):
        """MATCH (a) WITH a WHERE a.age > 25 RETURN a → no diagnostic."""
        result = _analyze("MATCH (a) WITH a WHERE a.age > 25 RETURN a")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_with_order_by_ok(self):
        """MATCH (a) WITH a ORDER BY a.name RETURN a → no diagnostic."""
        result = _analyze("MATCH (a) WITH a ORDER BY a.name RETURN a")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_with_hides_non_projected(self):
        """MATCH (a), (b) WITH a MATCH (c) WHERE c.id = b.id RETURN c → b undefined."""
        result = _analyze("MATCH (a), (b) WITH a MATCH (c) WHERE c.id = b.id RETURN c")
        self.assertIn("undefined-variable", _feature_ids(result))
        msgs = _messages_for(result, "undefined-variable")
        self.assertTrue(any("b" in m for m in msgs))


# ===========================================================================
# Type-conflict inside CALL bodies — currently broken, fixed by refactor
# ===========================================================================


class TestTypeConflictInCallBodies(unittest.TestCase):
    """Type conflicts and already-bound inside CALL { ... } bodies."""

    def test_type_conflict_inside_call(self):
        """CALL { MATCH (n) MATCH ()-[n]->() RETURN n } RETURN n → type-conflict."""
        result = _analyze("CALL { MATCH (n) MATCH ()-[n]->() RETURN n } RETURN n", dialect=_full)
        self.assertIn("variable-type-conflict", _feature_ids(result))

    def test_already_bound_inside_call(self):
        """CALL { MATCH (a) CREATE (a) RETURN a } RETURN a → diagnostic (bare-only CREATE)."""
        result = _analyze("CALL { MATCH (a) CREATE (a) RETURN a } RETURN a")
        self.assertIn("variable-already-bound", _feature_ids(result))

    def test_call_export_type_conflict(self):
        """CALL exports value, outer MATCH uses as node → type-conflict."""
        result = _analyze("CALL { MATCH (n) RETURN 1 AS n } MATCH (n) RETURN n", dialect=_full)
        self.assertIn("variable-type-conflict", _feature_ids(result))


# ===========================================================================
# Complex multi-statement scope (SET, DELETE, REMOVE, INSERT)
# ===========================================================================


class TestComplexMultiStatementScope(unittest.TestCase):
    """Scope validation across multi-statement data-modifying queries."""

    def test_match_set_delete_return_ok(self):
        """MATCH (a)-[r]->(b) SET a.visited = TRUE DELETE r RETURN a, b → OK."""
        result = _analyze("MATCH (a)-[r]->(b) SET a.visited = TRUE DELETE r RETURN a, b")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_match_set_return_ok(self):
        """MATCH (a) SET a.name = 'test' RETURN a.name → OK."""
        result = _analyze("MATCH (a) SET a.name = 'test' RETURN a.name")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_match_remove_return_ok(self):
        """MATCH (a)-[r]->(b) REMOVE a.temp RETURN a, b → OK."""
        result = _analyze("MATCH (a)-[r]->(b) REMOVE a.temp RETURN a, b")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_match_insert_return_ok(self):
        """MATCH (a) INSERT (b:Person) RETURN a, b → OK."""
        result = _analyze("MATCH (a) INSERT (b:Person) RETURN a, b", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_undefined_in_delete_multi(self):
        """MATCH (a) DELETE x → undefined in multi-statement context."""
        result = _analyze("MATCH (a) DELETE x")
        self.assertIn("undefined-variable", _feature_ids(result))

    def test_undefined_in_set_multi(self):
        """MATCH (a) SET x.name = 'test' → undefined in multi-statement context."""
        result = _analyze("MATCH (a) SET x.name = 'test'")
        self.assertIn("undefined-variable", _feature_ids(result))


# ===========================================================================
# Part 2a: New false-positive exclusion tests
# ===========================================================================


class TestPropertyKeyValuePairNotVariable(unittest.TestCase):
    """Property key names in {key: val} pattern specs must not be flagged as variables."""

    def test_pattern_property_spec(self):
        """MATCH (n {name: 'x'}) RETURN n → no diagnostic."""
        result = _analyze("MATCH (n {name: 'x'}) RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_edge_property_spec(self):
        """MATCH ()-[r {weight: 1}]->() RETURN r → no diagnostic."""
        result = _analyze("MATCH ()-[r {weight: 1}]->() RETURN r")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_create_with_properties(self):
        """CREATE (n {age: 25}) → no diagnostic."""
        result = _analyze("CREATE (n {age: 25})")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_multiple_properties(self):
        """MATCH (n {a: 1, b: 2}) RETURN n → no diagnostic."""
        result = _analyze("MATCH (n {a: 1, b: 2}) RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))


class TestSelectItemAliasNotVariable(unittest.TestCase):
    """SELECT alias declarations must not be flagged as variables (GQL only)."""

    def test_select_literal_alias(self):
        """SELECT 1 AS x → no diagnostic."""
        result = _analyze("SELECT 1 AS x", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_select_from_match(self):
        """SELECT n.name AS val FROM GRAPH g MATCH (n) → no diagnostic for val."""
        # Note: GRAPH reference may not be in scope, but alias itself should be fine
        result = _analyze("SELECT 1 AS val", dialect=_full)
        msgs = _messages_for(result, "undefined-variable")
        self.assertFalse(any("val" in m for m in msgs))


class TestYieldItemNotVariable(unittest.TestCase):
    """YIELD item names and aliases must not be flagged as variables."""

    def test_yield_name_in_scope(self):
        """CALL proc() YIELD result RETURN result → no diagnostic."""
        result = _analyze("CALL my_proc() YIELD result RETURN result", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_yield_alias_in_scope(self):
        """CALL proc() YIELD result AS alias RETURN alias → no diagnostic."""
        result = _analyze("CALL my_proc() YIELD result AS alias RETURN alias", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_yield_multiple(self):
        """CALL proc() YIELD a, b AS c RETURN a, c → no diagnostic."""
        result = _analyze("CALL my_proc() YIELD a, b AS c RETURN a, c", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))


class TestSubpathVariableDeclaration(unittest.TestCase):
    """Subpath variable declarations must not be flagged as variables."""

    def test_subpath_in_pattern(self):
        """Subpath variable in parenthesized path pattern → enters scope."""
        result = _analyze("MATCH (a)(p = (x)-[r]->(y))+(b) RETURN a, b", dialect=_full)
        msgs = _messages_for(result, "undefined-variable")
        self.assertFalse(any("p" in m for m in msgs), f"'p' wrongly flagged: {msgs}")


class TestListComprehensionScope(unittest.TestCase):
    """List comprehension iterator variables must not be flagged as undefined."""

    def test_basic_projection(self):
        """RETURN [x IN [1,2,3] | x * 2] → no diagnostic."""
        result = _analyze("RETURN [x IN [1,2,3] | x * 2]")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_with_where(self):
        """RETURN [x IN [1,2,3] WHERE x > 1] → no diagnostic."""
        result = _analyze("RETURN [x IN [1,2,3] WHERE x > 1]")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_with_match_scope(self):
        """MATCH (n) RETURN [x IN n.list | x + 1] → no diagnostic."""
        result = _analyze("MATCH (n) RETURN [x IN n.list | x + 1]")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_full_form(self):
        """RETURN [x IN [1,2,3] WHERE x > 1 | x * 2] → no diagnostic."""
        result = _analyze("RETURN [x IN [1,2,3] WHERE x > 1 | x * 2]")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_nested_comprehensions(self):
        """Nested comprehensions: outer and inner vars not flagged."""
        result = _analyze("RETURN [x IN [1,2,3] | [y IN [4,5] | x + y]]")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_all_predicate(self):
        """MATCH (n) RETURN all(x IN n.list WHERE x > 0) → no diagnostic."""
        result = _analyze("MATCH (n) RETURN all(x IN n.list WHERE x > 0)")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_any_predicate(self):
        """MATCH (n) RETURN any(x IN n.list WHERE x > 0) → no diagnostic."""
        result = _analyze("MATCH (n) RETURN any(x IN n.list WHERE x > 0)")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_none_predicate(self):
        """MATCH (n) RETURN none(x IN n.list WHERE x > 0) → no diagnostic."""
        result = _analyze("MATCH (n) RETURN none(x IN n.list WHERE x > 0)")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_single_predicate(self):
        """MATCH (n) RETURN single(x IN n.list WHERE x = 1) → no diagnostic."""
        result = _analyze("MATCH (n) RETURN single(x IN n.list WHERE x = 1)")
        self.assertNotIn("undefined-variable", _feature_ids(result))


class TestCypherSetPropertyNotVariable(unittest.TestCase):
    """Property names in SET items must not be flagged as variables."""

    def test_set_property_name(self):
        """MATCH (n) SET n.name = 'test' RETURN n → no diagnostic."""
        result = _analyze("MATCH (n) SET n.name = 'test' RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_set_property_age(self):
        """MATCH (n) SET n.age = 25 RETURN n → no diagnostic."""
        result = _analyze("MATCH (n) SET n.age = 25 RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_set_edge_property(self):
        """MATCH ()-[r]->() SET r.weight = 1 RETURN r → no diagnostic."""
        result = _analyze("MATCH ()-[r]->() SET r.weight = 1 RETURN r")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_set_multiple_items(self):
        """MATCH (n) SET n.name = 'x', n.age = 30 RETURN n → no diagnostic."""
        result = _analyze("MATCH (n) SET n.name = 'x', n.age = 30 RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))


class TestMapLiteralFieldNotVariable(unittest.TestCase):
    """Map literal field names must not be flagged as variables."""

    def test_map_return(self):
        """RETURN {name: 'Alice', age: 30} → no diagnostic."""
        result = _analyze("RETURN {name: 'Alice', age: 30}")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_map_with_var_ref(self):
        """MATCH (n) RETURN {x: n.name} → no diagnostic."""
        result = _analyze("MATCH (n) RETURN {x: n.name}")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_nested_map(self):
        """RETURN {a: {b: 1}} → no diagnostic."""
        result = _analyze("RETURN {a: {b: 1}}")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_map_in_where(self):
        """MATCH (n) WHERE n = {name: 'x'} RETURN n → no diagnostic."""
        result = _analyze("MATCH (n) WHERE n = {name: 'x'} RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))


# ===========================================================================
# Part 2b: Deep nesting & complex patterns
# ===========================================================================


class TestDeepNestedSubqueries(unittest.TestCase):
    """Tests for deeply nested subqueries and scope isolation."""

    def test_nested_call_inside_call(self):
        """CALL { CALL { RETURN 1 AS x } RETURN x } RETURN x → no diagnostic."""
        result = _analyze("CALL { CALL { RETURN 1 AS x } RETURN x } RETURN x", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_exists_inside_exists(self):
        """Nested EXISTS inside EXISTS → no crash, no false positive."""
        q = (
            "MATCH (a) WHERE EXISTS { MATCH (a)-[r]->(b)"
            " WHERE EXISTS { MATCH (b)-[s]->(c) } } RETURN a"
        )
        result = _analyze(q)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_exists_inside_call(self):
        """EXISTS inside CALL body → proper isolation."""
        result = _analyze(
            "CALL { MATCH (a) WHERE EXISTS { MATCH (a)-[r]->(b) } RETURN a } RETURN a",
            dialect=_full,
        )
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_triple_nesting(self):
        """CALL { CALL { CALL { RETURN 1 AS x } RETURN x } RETURN x } RETURN x."""
        result = _analyze(
            "CALL { CALL { CALL { RETURN 1 AS x } RETURN x } RETURN x } RETURN x",
            dialect=_full,
        )
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_mixed_nesting_with_match(self):
        """MATCH (a) CALL { MATCH (a)-[r]->(b) RETURN b } RETURN a, b."""
        result = _analyze(
            "MATCH (a) CALL { MATCH (a)-[r]->(b) RETURN b } RETURN a, b",
            dialect=_full,
        )
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_nested_subquery_accesses_outer(self):
        """Inner CALL body reads outer scope variable → no diagnostic."""
        result = _analyze(
            "MATCH (a) CALL { RETURN a.name AS val } RETURN a, val",
            dialect=_full,
        )
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_nested_subquery_internal_no_leak(self):
        """Variables declared inside CALL don't leak to outer scope."""
        result = _analyze(
            "CALL { MATCH (inner) RETURN 1 AS x } RETURN inner",
            dialect=_full,
        )
        self.assertIn("undefined-variable", _feature_ids(result))

    def test_call_no_return_exports_nothing(self):
        """CALL body with no RETURN exports nothing."""
        result = _analyze(
            "CALL { MATCH (n) } RETURN 1 AS x",
            dialect=_full,
        )
        self.assertNotIn("undefined-variable", _feature_ids(result))


class TestComplexPatterns(unittest.TestCase):
    """Tests for complex graph patterns."""

    def test_multi_hop_path(self):
        """MATCH (a)-[r1]->(b)-[r2]->(c) RETURN a, b, c → no diagnostic."""
        result = _analyze("MATCH (a)-[r1]->(b)-[r2]->(c) RETURN a, b, c")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_named_path(self):
        """MATCH p = (a)-[r]->(b) RETURN p, a, b → no diagnostic."""
        result = _analyze("MATCH p = (a)-[r]->(b) RETURN p, a, b")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_multiple_named_paths(self):
        """Multiple named paths in same MATCH → no diagnostic."""
        result = _analyze("MATCH p1 = (a)-[r]->(b), p2 = (c)-[s]->(d) RETURN p1, p2")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_path_with_where(self):
        """Path + WHERE referencing path nodes → no diagnostic."""
        result = _analyze("MATCH p = (a)-[r]->(b) WHERE a.name = 'x' RETURN p")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_variable_length_path(self):
        """MATCH (a)-[*1..3]->(b) RETURN a, b → no diagnostic."""
        result = _analyze("MATCH (a)-[*1..3]->(b) RETURN a, b")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_multiple_patterns_single_match(self):
        """MATCH (a), (b), (c) RETURN a, b, c → no diagnostic."""
        result = _analyze("MATCH (a), (b), (c) RETURN a, b, c")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_pattern_with_labels(self):
        """MATCH (a:Person)-[r:KNOWS]->(b:Person) RETURN a, b → no diagnostic."""
        result = _analyze("MATCH (a:Person)-[r:KNOWS]->(b:Person) RETURN a, b")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_disconnected_patterns_where_crossref(self):
        """Disconnected patterns + WHERE cross-reference → no diagnostic."""
        result = _analyze("MATCH (a), (b) WHERE a.id = b.id RETURN a, b")
        self.assertNotIn("undefined-variable", _feature_ids(result))


class TestComplexReturnExpressions(unittest.TestCase):
    """Tests for complex RETURN expressions."""

    def test_return_aggregation(self):
        """MATCH (n) RETURN count(n) → no diagnostic."""
        result = _analyze("MATCH (n) RETURN count(n)")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_return_math(self):
        """MATCH (n) RETURN n.age + 1 AS older → no diagnostic."""
        result = _analyze("MATCH (n) RETURN n.age + 1 AS older")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_return_multiple_aliases(self):
        """MATCH (a), (b) RETURN a.name AS x, b.name AS y → no diagnostic."""
        result = _analyze("MATCH (a), (b) RETURN a.name AS x, b.name AS y")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_return_case_expression(self):
        """MATCH (n) RETURN CASE WHEN n.age > 25 THEN 'old' ELSE 'young' END → no diagnostic."""
        result = _analyze(
            "MATCH (n) RETURN CASE WHEN n.age > 25 THEN 'old' ELSE 'young' END AS category"
        )
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_return_string_concat(self):
        """RETURN 'hello' + ' world' AS msg → no diagnostic."""
        result = _analyze("RETURN 'hello' + ' world' AS msg")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_return_order_by_alias(self):
        """MATCH (n) RETURN n.name AS name ORDER BY name → no diagnostic."""
        result = _analyze("MATCH (n) RETURN n.name AS name ORDER BY name")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_return_distinct(self):
        """MATCH (n) RETURN DISTINCT n → no diagnostic."""
        result = _analyze("MATCH (n) RETURN DISTINCT n")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_return_sum(self):
        """MATCH (n) RETURN sum(n.age) AS total → no diagnostic."""
        result = _analyze("MATCH (n) RETURN sum(n.age) AS total")
        self.assertNotIn("undefined-variable", _feature_ids(result))


class TestMultiClauseChains(unittest.TestCase):
    """Tests for multi-clause query chains."""

    def test_match_match_where_return(self):
        """MATCH (a) MATCH (b) WHERE a.id = b.id RETURN a, b → no diagnostic."""
        result = _analyze("MATCH (a) MATCH (b) WHERE a.id = b.id RETURN a, b")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_double_with(self):
        """MATCH (a) WITH a MATCH (b) WHERE b.id = a.id WITH b RETURN b → no diagnostic."""
        result = _analyze("MATCH (a) WITH a MATCH (b) WHERE b.id = a.id WITH b RETURN b")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_optional_match_with_return(self):
        """MATCH (a) OPTIONAL MATCH (a)-[r]->(b) WITH a, b RETURN a, b → no diagnostic."""
        result = _analyze("MATCH (a) OPTIONAL MATCH (a)-[r]->(b) WITH a, b RETURN a, b")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_let_match_return(self):
        """LET x = 1 MATCH (n) WHERE n.id = x RETURN n → no diagnostic."""
        result = _analyze("LET x = 1 MATCH (n) WHERE n.id = x RETURN n", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_for_return(self):
        """FOR x IN [1,2,3] RETURN x → no diagnostic."""
        result = _analyze("FOR x IN [1,2,3] RETURN x", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_create_match_return(self):
        """CREATE (a:T) MATCH (b) RETURN a, b → no diagnostic."""
        result = _analyze("CREATE (a:T) MATCH (b) RETURN a, b")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_match_set_delete_return(self):
        """MATCH (a)-[r]->(b) SET a.visited = TRUE DELETE r RETURN a, b → no diagnostic."""
        result = _analyze("MATCH (a)-[r]->(b) SET a.visited = TRUE DELETE r RETURN a, b")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_match_merge_return(self):
        """MATCH (a) MERGE (b:T {name: 'x'}) RETURN a, b → no diagnostic."""
        result = _analyze("MATCH (a) MERGE (b:T {name: 'x'}) RETURN a, b")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_three_matches(self):
        """MATCH (a) MATCH (b) MATCH (c) RETURN a, b, c → no diagnostic."""
        result = _analyze("MATCH (a) MATCH (b) MATCH (c) RETURN a, b, c")
        self.assertNotIn("undefined-variable", _feature_ids(result))


class TestEdgeCaseQueries(unittest.TestCase):
    """Tests for edge-case queries and unusual patterns."""

    def test_empty_match(self):
        """MATCH () RETURN 1 → no undefined (no named vars, but no refs either)."""
        result = _analyze("MATCH () RETURN 1")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_single_literal(self):
        """RETURN 1 AS x → no diagnostic."""
        result = _analyze("RETURN 1 AS x")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_boolean_literal(self):
        """RETURN TRUE AS flag → no diagnostic."""
        result = _analyze("RETURN TRUE AS flag")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_null_literal(self):
        """RETURN null AS val → no diagnostic."""
        result = _analyze("RETURN null AS val")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_string_concat_literal(self):
        """RETURN 'hello' + ' world' AS msg → no diagnostic."""
        result = _analyze("RETURN 'hello' + ' world' AS msg")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_match_no_return(self):
        """MATCH (a) SET a.x = 1 → no diagnostic (data-modifying only)."""
        result = _analyze("MATCH (a) SET a.x = 1")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_long_alias_name(self):
        """Very long alias name should work fine."""
        result = _analyze("MATCH (n) RETURN n.name AS very_long_alias_name_here")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_numeric_literal_not_var(self):
        """RETURN 42 → no diagnostic (numeric literal, not a variable)."""
        result = _analyze("RETURN 42")
        self.assertNotIn("undefined-variable", _feature_ids(result))


# ===========================================================================
# Part 2c: Scope boundary stress tests
# ===========================================================================


class TestWithScopeProjection(unittest.TestCase):
    """WITH scope projection boundary tests."""

    def test_with_star_preserves_and_adds(self):
        """WITH * preserves all vars and new MATCH adds more."""
        result = _analyze("MATCH (a) WITH * MATCH (b) RETURN a, b")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_with_partial_projection(self):
        """WITH partial projection hides non-projected vars."""
        result = _analyze("MATCH (a), (b) WITH a RETURN b")
        self.assertIn("undefined-variable", _feature_ids(result))

    def test_with_expression_projection(self):
        """WITH expression projection (not just bare vars)."""
        result = _analyze("MATCH (n) WITH n.name + '!' AS msg RETURN msg")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_with_aggregation(self):
        """MATCH (n) WITH count(n) AS cnt RETURN cnt → no diagnostic."""
        result = _analyze("MATCH (n) WITH count(n) AS cnt RETURN cnt")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_with_distinct(self):
        """MATCH (n) WITH DISTINCT n.name AS name RETURN name → no diagnostic."""
        result = _analyze("MATCH (n) WITH DISTINCT n.name AS name RETURN name")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_with_star_where_filter(self):
        """MATCH (a) WITH * WHERE a.age > 25 RETURN a → no diagnostic."""
        result = _analyze("MATCH (a) WITH * WHERE a.age > 25 RETURN a")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_with_alias_shadowing(self):
        """MATCH (a) WITH a.name AS a RETURN a → no diagnostic."""
        result = _analyze("MATCH (a) WITH a.name AS a RETURN a")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_with_order_by_limit(self):
        """MATCH (n) WITH n ORDER BY n.name LIMIT 10 RETURN n → no diagnostic."""
        result = _analyze("MATCH (n) WITH n ORDER BY n.name LIMIT 10 RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))


class TestUnionScopeAdvanced(unittest.TestCase):
    """Advanced UNION/EXCEPT/INTERSECT scope tests."""

    def test_union_all_different_vars(self):
        """UNION ALL with different var names but same alias → no diagnostic."""
        result = _analyze(
            "MATCH (a) RETURN a.name AS n UNION ALL MATCH (b) RETURN b.name AS n",
            dialect=_full,
        )
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_three_way_union(self):
        """Three-way UNION → no diagnostic."""
        result = _analyze(
            "RETURN 1 AS x UNION RETURN 2 AS x UNION RETURN 3 AS x",
            dialect=_full,
        )
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_union_with_match(self):
        """UNION with MATCH in both branches → no diagnostic."""
        result = _analyze(
            "MATCH (a) RETURN a AS x UNION MATCH (b) RETURN b AS x",
            dialect=_full,
        )
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_except(self):
        """EXCEPT → no diagnostic."""
        result = _analyze("RETURN 1 AS x EXCEPT RETURN 2 AS x", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_intersect_different_patterns(self):
        """INTERSECT with both branches using different patterns → no diagnostic."""
        result = _analyze(
            "MATCH (a) RETURN a.id AS id INTERSECT MATCH (b) RETURN b.id AS id",
            dialect=_full,
        )
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_union_branch_undefined(self):
        """Undefined in second UNION branch → diagnostic only on that branch."""
        result = _analyze(
            "MATCH (a) RETURN a.name AS n UNION RETURN missing AS n",
            dialect=_full,
        )
        self.assertIn("undefined-variable", _feature_ids(result))
        msgs = _messages_for(result, "undefined-variable")
        self.assertTrue(any("missing" in m for m in msgs))


class TestCallSubqueryExportProjection(unittest.TestCase):
    """CALL { ... } export and projection tests."""

    def test_call_return_star_exports_all(self):
        """CALL with RETURN * exports all inner scope."""
        result = _analyze(
            "CALL { MATCH (n) RETURN * } RETURN n",
            dialect=_full,
        )
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_call_return_partial(self):
        """CALL with partial RETURN → only projected vars available."""
        result = _analyze(
            "CALL { MATCH (n), (m) RETURN n } RETURN n",
            dialect=_full,
        )
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_call_partial_hidden(self):
        """CALL partial export → non-projected var undefined in outer scope."""
        result = _analyze(
            "CALL { MATCH (n), (m) RETURN n } RETURN m",
            dialect=_full,
        )
        self.assertIn("undefined-variable", _feature_ids(result))

    def test_call_with_union(self):
        """CALL body with UNION → exports from union."""
        result = _analyze(
            "CALL { RETURN 1 AS x UNION RETURN 2 AS x } RETURN x",
            dialect=_full,
        )
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_multiple_calls_export(self):
        """Multiple CALL bodies exporting different vars, used together."""
        result = _analyze(
            "CALL { RETURN 1 AS x } CALL { RETURN 2 AS y } RETURN x, y",
            dialect=_full,
        )
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_call_no_return_nothing_exported(self):
        """CALL with no RETURN → nothing exported, outer scope unaffected."""
        result = _analyze(
            "CALL { MATCH (n) } RETURN 1 AS x",
            dialect=_full,
        )
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_call_data_modifying_return(self):
        """CALL body with data-modifying statement + RETURN."""
        result = _analyze(
            "CALL { CREATE (n:T) RETURN n } RETURN n",
        )
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_call_chained_inner_exports(self):
        """Chained CALL → first export used by second CALL."""
        result = _analyze(
            "MATCH (a) CALL { RETURN a.name AS val } CALL { RETURN val AS msg } RETURN msg",
            dialect=_full,
        )
        self.assertNotIn("undefined-variable", _feature_ids(result))


class TestForStatementScope(unittest.TestCase):
    """FOR statement scope binding tests (GQL only)."""

    def test_for_basic(self):
        """FOR x IN [1,2,3] RETURN x → no diagnostic."""
        result = _analyze("FOR x IN [1,2,3] RETURN x", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_for_ordinality(self):
        """FOR x IN [1,2,3] WITH ORDINALITY i RETURN x, i → no diagnostic."""
        result = _analyze("FOR x IN [1,2,3] WITH ORDINALITY i RETURN x, i", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_for_offset(self):
        """FOR x IN [1,2,3] WITH OFFSET i RETURN x, i → no diagnostic."""
        result = _analyze("FOR x IN [1,2,3] WITH OFFSET i RETURN x, i", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_for_after_match(self):
        """MATCH (n) FOR x IN [1,2] RETURN n, x → no diagnostic."""
        result = _analyze("MATCH (n) FOR x IN [1,2] RETURN n, x", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_for_undefined_after(self):
        """FOR x IN [1,2,3] RETURN y → undefined."""
        result = _analyze("FOR x IN [1,2,3] RETURN y", dialect=_full)
        self.assertIn("undefined-variable", _feature_ids(result))


class TestLetStatementAdvanced(unittest.TestCase):
    """Advanced LET statement tests (GQL only)."""

    def test_let_with_expression(self):
        """LET x = 1 + 2 RETURN x → no diagnostic."""
        result = _analyze("LET x = 1 + 2 RETURN x", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_let_after_with(self):
        """MATCH (a) WITH a LET x = a.name RETURN x → no diagnostic."""
        result = _analyze("MATCH (a) WITH a LET x = a.name RETURN x")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_multiple_lets(self):
        """LET x = 1 LET y = 2 RETURN x, y → no diagnostic."""
        result = _analyze("LET x = 1 LET y = 2 RETURN x, y", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_let_with_undefined_ref(self):
        """LET x = missing_var RETURN x → undefined for missing_var."""
        result = _analyze("LET x = missing_var RETURN x", dialect=_full)
        self.assertIn("undefined-variable", _feature_ids(result))
        msgs = _messages_for(result, "undefined-variable")
        self.assertTrue(any("missing_var" in m for m in msgs))

    def test_let_chain_dependency(self):
        """LET x = 1, y = x + 1 RETURN y → check if x is visible to y definition."""
        # LET definitions in same list may or may not see prior definitions
        # Just verify no crash
        result = _analyze("LET x = 1, y = 2 RETURN x, y", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))


# ===========================================================================
# Part 2d: Cross-rule interaction tests
# ===========================================================================


class TestCrossRuleInteractions(unittest.TestCase):
    """Tests where multiple rule types interact in the same query."""

    def test_type_conflict_and_undefined(self):
        """Type conflict + undefined in same query."""
        result = _analyze("MATCH (r) MATCH ()-[r]->() RETURN missing")
        ids = _feature_ids(result)
        self.assertIn("variable-type-conflict", ids)
        self.assertIn("undefined-variable", ids)

    def test_already_bound_and_type_conflict(self):
        """Already-bound + type conflict."""
        result = _analyze("MATCH (r) WITH r AS r MATCH ()-[r]->() CREATE (r) RETURN r")
        ids = _feature_ids(result)
        # Expect at least type-conflict since r was node but now edge
        self.assertIn("variable-type-conflict", ids)

    def test_multiple_undefined(self):
        """Multiple undefined vars in one query."""
        result = _analyze("RETURN x, y, z")
        msgs = _messages_for(result, "undefined-variable")
        undefined_names = {m.split("'")[1] for m in msgs if "'" in m}
        self.assertTrue({"x", "y", "z"} <= undefined_names)

    def test_undefined_in_where_and_return(self):
        """Undefined in WHERE + undefined in RETURN."""
        result = _analyze("MATCH (n) WHERE missing > 1 RETURN also_missing")
        msgs = _messages_for(result, "undefined-variable")
        found = " ".join(msgs)
        self.assertIn("missing", found)
        self.assertIn("also_missing", found)

    def test_call_type_conflict_outer_undefined(self):
        """CALL body produces type conflict + outer has undefined."""
        result = _analyze(
            "CALL { MATCH (r) MATCH ()-[r]->() RETURN 1 AS x } RETURN missing",
            dialect=_full,
        )
        ids = _feature_ids(result)
        self.assertIn("variable-type-conflict", ids)
        self.assertIn("undefined-variable", ids)

    def test_return_star_no_vars_and_where_undefined(self):
        """RETURN * with no variables + undefined in WHERE."""
        result = _analyze("MATCH () WHERE missing > 1 RETURN *")
        ids = _feature_ids(result)
        self.assertIn("return-star-no-variables", ids)
        self.assertIn("undefined-variable", ids)

    def test_nested_subquery_undefined_outer_undefined(self):
        """Nested subquery undefined + outer undefined (independent)."""
        result = _analyze(
            "CALL { RETURN missing_inner AS x } RETURN missing_outer",
            dialect=_full,
        )
        msgs = _messages_for(result, "undefined-variable")
        found = " ".join(msgs)
        self.assertIn("missing_inner", found)
        self.assertIn("missing_outer", found)

    def test_cross_with_type_conflict_value_kind(self):
        """Type conflict across WITH boundary + value kind tracking."""
        result = _analyze("MATCH (n) WITH 1 AS n MATCH (n) RETURN n")
        self.assertIn("variable-type-conflict", _feature_ids(result))


class TestReturnStarAdvanced(unittest.TestCase):
    """Advanced RETURN * tests."""

    def test_return_star_after_optional_match(self):
        """MATCH (a) OPTIONAL MATCH (a)-[r]->(b) RETURN * → no diagnostic."""
        result = _analyze("MATCH (a) OPTIONAL MATCH (a)-[r]->(b) RETURN *")
        self.assertNotIn("return-star-no-variables", _feature_ids(result))

    def test_return_star_after_let(self):
        """LET x = 1 RETURN * → no diagnostic (x in scope)."""
        result = _analyze("LET x = 1 RETURN *", dialect=_full)
        self.assertNotIn("return-star-no-variables", _feature_ids(result))

    def test_return_star_after_call_export(self):
        """CALL { RETURN 1 AS x } RETURN * → no diagnostic."""
        result = _analyze("CALL { RETURN 1 AS x } RETURN *", dialect=_full)
        self.assertNotIn("return-star-no-variables", _feature_ids(result))

    def test_return_star_after_yield(self):
        """CALL proc() YIELD result RETURN * → no diagnostic."""
        result = _analyze("CALL my_proc() YIELD result RETURN *", dialect=_full)
        self.assertNotIn("return-star-no-variables", _feature_ids(result))

    def test_return_star_path_var_only(self):
        """MATCH p = (a)-[r]->(b) RETURN * → no diagnostic."""
        result = _analyze("MATCH p = (a)-[r]->(b) RETURN *")
        self.assertNotIn("return-star-no-variables", _feature_ids(result))


class TestAlreadyBoundAdvanced(unittest.TestCase):
    """Advanced already-bound detection tests."""

    def test_create_after_call_export(self):
        """CALL exports 'a', then CREATE (a) → diagnostic (bare-only CREATE)."""
        result = _analyze(
            "CALL { MATCH (a) RETURN a } CREATE (a) RETURN a",
        )
        self.assertIn("variable-already-bound", _feature_ids(result))

    def test_create_after_for(self):
        """FOR a IN [1,2] INSERT (a:T) → already bound."""
        result = _analyze("FOR a IN [1,2] INSERT (a:T)", dialect=_full)
        self.assertIn("variable-already-bound", _feature_ids(result))

    def test_create_after_let(self):
        """LET a = 1 INSERT (a:T) → already bound."""
        result = _analyze("LET a = 1 INSERT (a:T)", dialect=_full)
        self.assertIn("variable-already-bound", _feature_ids(result))

    def test_create_after_yield(self):
        """MATCH + CALL YIELD a + CREATE (a) → already bound (MATCH binds, CREATE re-declares)."""
        result = _analyze("MATCH (a) CREATE (a:T)")
        self.assertIn("variable-already-bound", _feature_ids(result))

    def test_merge_same_var_node_edge(self):
        """MATCH (a) MERGE (a)-[r:T]->(b) → no diagnostic (bare filler = reference)."""
        result = _analyze("MATCH (a) MERGE (a)-[r:T]->(b)")
        self.assertNotIn("variable-already-bound", _feature_ids(result))


# ===========================================================================
# Part 2e: Cypher-specific scope tests
# ===========================================================================


class TestCypherCreateMerge(unittest.TestCase):
    """Cypher CREATE/MERGE scope tests."""

    def test_create_with_scope_ref(self):
        """MATCH (a) CREATE (b {ref: a.id}) → no undefined (a.id in scope)."""
        result = _analyze("MATCH (a) CREATE (b {ref: a.id})")
        msgs = _messages_for(result, "undefined-variable")
        self.assertFalse(any("a" in m for m in msgs), f"'a' wrongly flagged: {msgs}")

    def test_merge_on_create_set(self):
        """MERGE (n:T) ON CREATE SET n.ts = 1 RETURN n → no diagnostic."""
        result = _analyze("MERGE (n:T {name: 'x'}) ON CREATE SET n.ts = 1 RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_merge_on_match_set(self):
        """MERGE (n:T) ON MATCH SET n.count = n.count + 1 RETURN n → no diagnostic."""
        result = _analyze("MERGE (n:T {name: 'x'}) ON MATCH SET n.count = n.count + 1 RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_create_relationship(self):
        """MATCH (a), (b) CREATE (a)-[r:KNOWS]->(b) RETURN r → no diagnostic (bare references)."""
        result = _analyze("MATCH (a), (b) CREATE (a)-[r:KNOWS]->(b) RETURN r")
        self.assertNotIn("variable-already-bound", _feature_ids(result))

    def test_merge_relationship(self):
        """MATCH (a), (b) MERGE (a)-[r:KNOWS]->(b) RETURN r → no diagnostic (bare references)."""
        result = _analyze("MATCH (a), (b) MERGE (a)-[r:KNOWS]->(b) RETURN r")
        self.assertNotIn("variable-already-bound", _feature_ids(result))

    def test_create_after_with(self):
        """MATCH (a) WITH a CREATE (b {ref: a.name}) RETURN a, b → no diagnostic."""
        result = _analyze("MATCH (a) WITH a CREATE (b {ref: a.name}) RETURN a, b")
        self.assertNotIn("undefined-variable", _feature_ids(result))


class TestCypherUnwindScope(unittest.TestCase):
    """Cypher UNWIND scope tests."""

    def test_unwind_basic(self):
        """UNWIND [1,2,3] AS x RETURN x → no diagnostic."""
        result = _analyze("UNWIND [1,2,3] AS x RETURN x")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_unwind_in_where(self):
        """UNWIND [1,2,3] AS x MATCH (n) WHERE n.id = x RETURN n → no diagnostic."""
        result = _analyze("UNWIND [1,2,3] AS x MATCH (n) WHERE n.id = x RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_unwind_after_match(self):
        """MATCH (n) UNWIND n.list AS item RETURN n, item → no diagnostic."""
        result = _analyze("MATCH (n) UNWIND n.list AS item RETURN n, item")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_unwind_undefined_return(self):
        """UNWIND [1,2,3] AS x RETURN y → undefined."""
        result = _analyze("UNWIND [1,2,3] AS x RETURN y")
        self.assertIn("undefined-variable", _feature_ids(result))
        msgs = _messages_for(result, "undefined-variable")
        self.assertTrue(any("y" in m for m in msgs))


class TestCypherWithDistinct(unittest.TestCase):
    """Cypher WITH DISTINCT scope tests."""

    def test_with_distinct_name(self):
        """MATCH (n) WITH DISTINCT n.name AS name RETURN name → no diagnostic."""
        result = _analyze("MATCH (n) WITH DISTINCT n.name AS name RETURN name")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_with_distinct_node(self):
        """MATCH (n) WITH DISTINCT n RETURN n → no diagnostic."""
        result = _analyze("MATCH (n) WITH DISTINCT n RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_with_distinct_hides_non_projected(self):
        """MATCH (a), (b) WITH DISTINCT a RETURN b → undefined."""
        result = _analyze("MATCH (a), (b) WITH DISTINCT a RETURN b")
        self.assertIn("undefined-variable", _feature_ids(result))

    def test_with_distinct_where(self):
        """MATCH (n) WITH DISTINCT n.name AS name WHERE name = 'x' RETURN name → no diagnostic."""
        result = _analyze("MATCH (n) WITH DISTINCT n.name AS name WHERE name = 'x' RETURN name")
        self.assertNotIn("undefined-variable", _feature_ids(result))


class TestCypherWherePatterns(unittest.TestCase):
    """Cypher WHERE pattern and predicate tests."""

    def test_where_pattern(self):
        """MATCH (n) WHERE (n)--() RETURN n → no diagnostic."""
        result = _analyze("MATCH (n) WHERE (n)--() RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_where_complex_boolean(self):
        """Complex boolean: WHERE n.a > 1 OR (n.b < 2 AND n.c = 3) → no diagnostic."""
        result = _analyze("MATCH (n) WHERE n.a > 1 OR (n.b < 2 AND n.c = 3) RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_where_in_predicate(self):
        """MATCH (n) WHERE n.val IN [1,2,3] RETURN n → no diagnostic."""
        result = _analyze("MATCH (n) WHERE n.val IN [1,2,3] RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_where_and_condition(self):
        """MATCH (n) WHERE n.age > 25 AND n.name = 'x' RETURN n → no diagnostic."""
        result = _analyze("MATCH (n) WHERE n.age > 25 AND n.name = 'x' RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))


class TestCypherAggregationScope(unittest.TestCase):
    """Cypher aggregation function scope tests."""

    def test_count_node(self):
        """MATCH (n) RETURN count(n) AS cnt → no diagnostic."""
        result = _analyze("MATCH (n) RETURN count(n) AS cnt")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_count_with_group(self):
        """MATCH (n) RETURN n.label, count(n) AS cnt → no diagnostic."""
        result = _analyze("MATCH (n) RETURN n.label, count(n) AS cnt")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_collect(self):
        """MATCH (n)-[r]->(m) RETURN n, collect(m) AS friends → no diagnostic."""
        result = _analyze("MATCH (n)-[r]->(m) RETURN n, collect(m) AS friends")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_with_count(self):
        """MATCH (n) WITH n.label AS t, count(n) AS c RETURN t, c → no diagnostic."""
        result = _analyze("MATCH (n) WITH n.label AS t, count(n) AS c RETURN t, c")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_sum(self):
        """MATCH (n) RETURN sum(n.age) AS total → no diagnostic."""
        result = _analyze("MATCH (n) RETURN sum(n.age) AS total")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_with_collect(self):
        """MATCH (n) WITH collect(n.name) AS names RETURN names → no diagnostic."""
        result = _analyze("MATCH (n) WITH collect(n.name) AS names RETURN names")
        self.assertNotIn("undefined-variable", _feature_ids(result))


# ===========================================================================
# Part 2f: GQL-specific edge cases
# ===========================================================================


class TestGqlSpecificScope(unittest.TestCase):
    """GQL-specific scope edge cases (full dialect)."""

    def test_insert_statement(self):
        """INSERT (n:Person {name: 'x'}) RETURN n → no diagnostic."""
        result = _analyze("INSERT (n:Person {name: 'x'}) RETURN n", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_insert_with_ref(self):
        """MATCH (a) INSERT (b:T {ref: a.id}) RETURN b → check a in scope."""
        result = _analyze("MATCH (a) INSERT (b:T {ref: a.id}) RETURN a, b", dialect=_full)
        msgs = _messages_for(result, "undefined-variable")
        self.assertFalse(any("a" in m for m in msgs), f"'a' wrongly flagged: {msgs}")

    def test_insert_bare_reuse_gql(self):
        """INSERT (a:Person), (b:Person), (a)-[:KNOWS]->(b) RETURN a → no diagnostic (GQL)."""
        result = _analyze(
            "INSERT (a:Person {name: 'x'}), (b:Person {name: 'y'}),"
            "       (a)-[:KNOWS]->(b) RETURN a, b",
            dialect=_full,
        )
        self.assertNotIn("variable-already-bound", _feature_ids(result))

    def test_insert_redeclaration_gql(self):
        """INSERT (a:Person), (a:Dog) RETURN a → diagnostic (GQL, labeled re-declaration)."""
        result = _analyze("INSERT (a:Person), (a:Dog) RETURN a", dialect=_full)
        self.assertIn("variable-already-bound", _feature_ids(result))

    def test_table_subquery(self):
        """RETURN TABLE { MATCH (n) RETURN n.name AS name } → no diagnostic."""
        result = _analyze(
            "RETURN TABLE { MATCH (n) RETURN n.name AS name }",
            dialect=_full,
        )
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_filter_statement(self):
        """MATCH (n) FILTER WHERE n.age > 25 RETURN n → no diagnostic."""
        result = _analyze("MATCH (n) FILTER WHERE n.age > 25 RETURN n", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_exists_in_where(self):
        """MATCH (a) WHERE EXISTS { MATCH (a)-[r]->(b) } RETURN a → no diagnostic."""
        result = _analyze(
            "MATCH (a) WHERE EXISTS { MATCH (a)-[r]->(b) } RETURN a",
            dialect=_full,
        )
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_record_constructor(self):
        """MATCH (n) RETURN {name: n.name, age: n.age} → no diagnostic."""
        result = _analyze("MATCH (n) RETURN {name: n.name, age: n.age}")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_cast_expression(self):
        """MATCH (n) RETURN CAST(n.age AS STRING) → no diagnostic."""
        result = _analyze("MATCH (n) RETURN CAST(n.age AS STRING)", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_nested_table(self):
        """Nested TABLE subquery → no diagnostic."""
        result = _analyze(
            "RETURN TABLE { RETURN TABLE { RETURN 1 AS x } }",
            dialect=_full,
        )
        self.assertNotIn("undefined-variable", _feature_ids(result))


# ===========================================================================
# Additional scope boundary and Cypher edge cases for coverage target
# ===========================================================================


class TestCypherExpressionScope(unittest.TestCase):
    """Cypher expression-level scope tests."""

    def test_string_starts_with(self):
        """MATCH (n) WHERE n.name STARTS WITH 'A' RETURN n → no diagnostic."""
        result = _analyze("MATCH (n) WHERE n.name STARTS WITH 'A' RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_string_ends_with(self):
        """MATCH (n) WHERE n.name ENDS WITH 'z' RETURN n → no diagnostic."""
        result = _analyze("MATCH (n) WHERE n.name ENDS WITH 'z' RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_string_contains(self):
        """MATCH (n) WHERE n.name CONTAINS 'li' RETURN n → no diagnostic."""
        result = _analyze("MATCH (n) WHERE n.name CONTAINS 'li' RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_regex_match(self):
        """MATCH (n) WHERE n.name =~ 'A.*' RETURN n → no diagnostic."""
        result = _analyze("MATCH (n) WHERE n.name =~ 'A.*' RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_subscript_access(self):
        """MATCH (n) RETURN n.list[0] → no diagnostic."""
        result = _analyze("MATCH (n) RETURN n.list[0]")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_slice_access(self):
        """MATCH (n) RETURN n.list[0..2] → no diagnostic."""
        result = _analyze("MATCH (n) RETURN n.list[0..2]")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_head_function(self):
        """MATCH (n) RETURN head(n.list) → no diagnostic."""
        result = _analyze("MATCH (n) RETURN head(n.list)")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_tail_function(self):
        """MATCH (n) RETURN tail(n.list) → no diagnostic."""
        result = _analyze("MATCH (n) RETURN tail(n.list)")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_last_function(self):
        """MATCH (n) RETURN last(n.list) → no diagnostic."""
        result = _analyze("MATCH (n) RETURN last(n.list)")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_size_function(self):
        """MATCH (n) RETURN size(n.list) → no diagnostic."""
        result = _analyze("MATCH (n) RETURN size(n.list)")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_type_function(self):
        """MATCH ()-[r]->() RETURN type(r) → no diagnostic."""
        result = _analyze("MATCH ()-[r]->() RETURN type(r)")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_labels_function(self):
        """MATCH (n) RETURN labels(n) → no diagnostic."""
        result = _analyze("MATCH (n) RETURN labels(n)")
        self.assertNotIn("undefined-variable", _feature_ids(result))


class TestCypherPropertyAccess(unittest.TestCase):
    """Cypher property access and map field scope tests."""

    def test_deep_property_chain(self):
        """MATCH (n) RETURN n.a.b → no diagnostic (a is property, b is property)."""
        result = _analyze("MATCH (n) RETURN n.a")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_property_in_where(self):
        """MATCH (n) WHERE n.age > 25 RETURN n → no diagnostic."""
        result = _analyze("MATCH (n) WHERE n.age > 25 RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_property_in_order_by(self):
        """MATCH (n) RETURN n ORDER BY n.name → no diagnostic."""
        result = _analyze("MATCH (n) RETURN n ORDER BY n.name")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_property_in_set(self):
        """MATCH (n) SET n.visited = TRUE RETURN n → no diagnostic."""
        result = _analyze("MATCH (n) SET n.visited = TRUE RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_property_in_create(self):
        """CREATE (n:T {name: 'x', age: 25}) → no diagnostic."""
        result = _analyze("CREATE (n:T {name: 'x', age: 25})")
        self.assertNotIn("undefined-variable", _feature_ids(result))


class TestCypherMatchVariants(unittest.TestCase):
    """Various MATCH clause forms in Cypher."""

    def test_match_where_exists(self):
        """MATCH (n) WHERE EXISTS { MATCH (n)-[r]->(m) } RETURN n → no diagnostic."""
        result = _analyze("MATCH (n) WHERE EXISTS { MATCH (n)-[r]->(m) } RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_match_where_not_exists(self):
        """MATCH (n) WHERE NOT EXISTS { MATCH (n)-[r]->(m) } RETURN n → no diagnostic."""
        result = _analyze("MATCH (n) WHERE NOT EXISTS { MATCH (n)-[r]->(m) } RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_match_optional_match_chain(self):
        """MATCH (a) OPTIONAL MATCH (a)-[r]->(b) RETURN a, r, b → no diagnostic."""
        result = _analyze("MATCH (a) OPTIONAL MATCH (a)-[r]->(b) RETURN a, r, b")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_match_with_param_in_where(self):
        """MATCH (n) WHERE n.id = $id RETURN n → no diagnostic."""
        result = _analyze("MATCH (n) WHERE n.id = $id RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_match_with_label_and_prop(self):
        """MATCH (n:Person {name: 'Alice'}) RETURN n → no diagnostic."""
        result = _analyze("MATCH (n:Person {name: 'Alice'}) RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))


class TestComplexScopeChains(unittest.TestCase):
    """Complex chains of scope-modifying operations."""

    def test_match_with_match_with_return(self):
        """MATCH (a) WITH a MATCH (b) WITH b RETURN b → no diagnostic."""
        result = _analyze("MATCH (a) WITH a MATCH (b) WITH b RETURN b")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_match_with_hides_then_match(self):
        """MATCH (a) WITH a.name AS name MATCH (b) RETURN name, b → no diagnostic."""
        result = _analyze("MATCH (a) WITH a.name AS name MATCH (b) RETURN name, b")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_with_where_scope(self):
        """MATCH (a) WITH a WHERE a.age > 10 RETURN a → no diagnostic."""
        result = _analyze("MATCH (a) WITH a WHERE a.age > 10 RETURN a")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_with_hides_in_where(self):
        """MATCH (a), (b) WITH a WHERE b.age > 10 RETURN a → undefined (b hidden)."""
        result = _analyze("MATCH (a), (b) WITH a WHERE b.age > 10 RETURN a")
        self.assertIn("undefined-variable", _feature_ids(result))

    def test_triple_with_chain(self):
        """MATCH (a) WITH a WITH a.name AS name WITH name RETURN name → no diagnostic."""
        result = _analyze("MATCH (a) WITH a WITH a.name AS name WITH name RETURN name")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_with_star_then_partial(self):
        """MATCH (a), (b) WITH * WITH a RETURN b → undefined (b hidden by second WITH)."""
        result = _analyze("MATCH (a), (b) WITH * WITH a RETURN b")
        self.assertIn("undefined-variable", _feature_ids(result))

    def test_call_export_then_with(self):
        """CALL exports, then WITH filters → proper scope."""
        result = _analyze(
            "CALL { RETURN 1 AS x } WITH x RETURN x",
        )
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_call_export_then_with_loses_var(self):
        """CALL exports, then WITH filters → lost var is undefined."""
        result = _analyze(
            "CALL { RETURN 1 AS x } CALL { RETURN 2 AS y } WITH x RETURN y",
        )
        self.assertIn("undefined-variable", _feature_ids(result))


class TestMergeAdvanced(unittest.TestCase):
    """Advanced MERGE scope and interaction tests."""

    def test_merge_new_pattern(self):
        """MERGE (n:T {name: 'x'}) RETURN n → no diagnostic."""
        result = _analyze("MERGE (n:T {name: 'x'}) RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_merge_on_create_and_match(self):
        """MERGE (n:T) ON CREATE SET n.created = 1 ON MATCH SET n.seen = 2 RETURN n."""
        result = _analyze(
            "MERGE (n:T {name: 'x'}) ON CREATE SET n.created = 1 ON MATCH SET n.seen = 2 RETURN n"
        )
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_merge_undefined_in_on_create(self):
        """MERGE (n) ON CREATE SET x.num = 1 → x is undefined."""
        result = _analyze("MERGE (n) ON CREATE SET x.num = 1")
        self.assertIn("undefined-variable", _feature_ids(result))

    def test_merge_undefined_in_on_match(self):
        """MERGE (n) ON MATCH SET x.num = 1 → x is undefined."""
        result = _analyze("MERGE (n) ON MATCH SET x.num = 1")
        self.assertIn("undefined-variable", _feature_ids(result))


class TestDeleteRemoveScope(unittest.TestCase):
    """DELETE and REMOVE scope tests."""

    def test_delete_defined(self):
        """MATCH (a)-[r]->(b) DELETE r → no diagnostic."""
        result = _analyze("MATCH (a)-[r]->(b) DELETE r")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_delete_undefined(self):
        """MATCH (a) DELETE missing → undefined."""
        result = _analyze("MATCH (a) DELETE missing")
        self.assertIn("undefined-variable", _feature_ids(result))

    def test_remove_defined(self):
        """MATCH (a) REMOVE a.prop → no diagnostic."""
        result = _analyze("MATCH (a) REMOVE a.prop")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_remove_undefined(self):
        """MATCH (a) REMOVE missing.prop → undefined."""
        result = _analyze("MATCH (a) REMOVE missing.prop")
        self.assertIn("undefined-variable", _feature_ids(result))

    def test_detach_delete(self):
        """MATCH (n) DETACH DELETE n → no diagnostic."""
        result = _analyze("MATCH (n) DETACH DELETE n")
        self.assertNotIn("undefined-variable", _feature_ids(result))


class TestCypherCaseScope(unittest.TestCase):
    """Cypher CASE expression scope tests."""

    def test_simple_case(self):
        """MATCH (n) RETURN CASE n.status WHEN 'active' THEN 1 ELSE 0 END → no diagnostic."""
        result = _analyze("MATCH (n) RETURN CASE n.status WHEN 'active' THEN 1 ELSE 0 END AS val")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_searched_case(self):
        """MATCH (n) RETURN CASE WHEN n.age > 25 THEN 'old' ELSE 'young' END → no diagnostic."""
        result = _analyze(
            "MATCH (n) RETURN CASE WHEN n.age > 25 THEN 'old' ELSE 'young' END AS category"
        )
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_case_with_undefined(self):
        """RETURN CASE missing WHEN 1 THEN 'one' END → undefined."""
        result = _analyze("RETURN CASE missing WHEN 1 THEN 'one' END AS val")
        self.assertIn("undefined-variable", _feature_ids(result))

    def test_case_multiple_when(self):
        """MATCH (n) RETURN CASE WHEN n.a = 1 THEN 'a' WHEN n.b = 2 THEN 'b' END."""
        result = _analyze(
            "MATCH (n) RETURN CASE WHEN n.a = 1 THEN 'a' WHEN n.b = 2 THEN 'b' END AS val"
        )
        self.assertNotIn("undefined-variable", _feature_ids(result))


class TestParameterScope(unittest.TestCase):
    """Parameter references should never be flagged as undefined."""

    def test_dollar_in_return(self):
        """RETURN $x → no diagnostic."""
        result = _analyze("RETURN $x")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_dollar_in_where(self):
        """MATCH (n) WHERE n.id = $id RETURN n → no diagnostic."""
        result = _analyze("MATCH (n) WHERE n.id = $id RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_dollar_in_set(self):
        """MATCH (n) SET n.val = $v RETURN n → no diagnostic."""
        result = _analyze("MATCH (n) SET n.val = $v RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_dollar_in_create(self):
        """CREATE (n {name: $name}) → no diagnostic."""
        result = _analyze("CREATE (n {name: $name})")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_substituted_param(self):
        """RETURN GRAPH $$g → no diagnostic."""
        result = _analyze("RETURN GRAPH $$g", dialect=_full)
        self.assertNotIn("undefined-variable", _feature_ids(result))


# ===========================================================================
# Diagnostic line/col — position info populated from AST _start_token
# ===========================================================================


class TestDiagnosticLineCol(unittest.TestCase):
    """Verify that SemanticDiagnostic.line/col are populated from the AST node."""

    def test_undefined_variable_has_position(self):
        """undefined-variable diagnostic carries line/col."""
        result = _analyze("MATCH (n) RETURN x")
        diags = [d for d in result.diagnostics if d.feature_id == "undefined-variable"]
        self.assertTrue(len(diags) >= 1)
        for d in diags:
            self.assertIsNotNone(d.line, "line should be populated")
            self.assertIsNotNone(d.col, "col should be populated")

    def test_type_conflict_has_position(self):
        """variable-type-conflict diagnostic carries line/col."""
        result = _analyze("MATCH (r) MATCH ()-[r]->() RETURN r")
        diags = [d for d in result.diagnostics if d.feature_id == "variable-type-conflict"]
        self.assertTrue(len(diags) >= 1)
        for d in diags:
            self.assertIsNotNone(d.line)
            self.assertIsNotNone(d.col)

    def test_already_bound_has_position(self):
        """variable-already-bound diagnostic carries line/col."""
        result = _analyze("MATCH (n) CREATE (n:T)")
        diags = [d for d in result.diagnostics if d.feature_id == "variable-already-bound"]
        self.assertTrue(len(diags) >= 1)
        for d in diags:
            self.assertIsNotNone(d.line)
            self.assertIsNotNone(d.col)

    def test_return_star_no_vars_has_position(self):
        """return-star-no-variables diagnostic carries line/col."""
        result = _analyze("RETURN *", dialect=_full)
        diags = [d for d in result.diagnostics if d.feature_id == "return-star-no-variables"]
        self.assertTrue(len(diags) >= 1)
        for d in diags:
            self.assertIsNotNone(d.line)
            self.assertIsNotNone(d.col)

    def test_undefined_in_where_after_with_has_position(self):
        """Diagnostic for undefined var in WITH...WHERE points to the variable, not None."""
        query = (
            "MATCH (n)-[r]->(prod)\n"
            "OPTIONAL MATCH (prod)-[r2]->(c)\n"
            "WITH n, r, r2, c\n"
            'WHERE prod.category = "Electronics"\n'
            "RETURN n"
        )
        result = _analyze(query)
        diags = [d for d in result.diagnostics if d.feature_id == "undefined-variable"]
        self.assertTrue(len(diags) >= 1, "expected at least one undefined-variable diagnostic")
        prod_diag = [d for d in diags if "prod" in d.message]
        self.assertTrue(len(prod_diag) >= 1, "expected diagnostic for 'prod'")
        d = prod_diag[0]
        self.assertIsNotNone(d.line, "diagnostic line should not be None")
        self.assertIsNotNone(d.col, "diagnostic col should not be None")
        # The diagnostic should point to line 4 col 10 where `prod` appears in WHERE
        self.assertEqual(d.line, 4, "diagnostic should point to line 4 (WHERE clause)")
        self.assertEqual(d.col, 10, "diagnostic should point to col 10 ('prod' in WHERE)")

    def test_undefined_in_return_points_to_variable(self):
        """Diagnostic for undefined var in RETURN points to the specific variable."""
        query = "MATCH (n) RETURN x"
        result = _analyze(query)
        diags = [d for d in result.diagnostics if d.feature_id == "undefined-variable"]
        self.assertTrue(len(diags) >= 1)
        d = diags[0]
        self.assertIsNotNone(d.line)
        self.assertIsNotNone(d.col)
        # 'x' has col 19 (token end-col), not col 17 (RETURN keyword)
        self.assertEqual(d.col, 19, "diagnostic should point to the 'x' identifier")


# ===========================================================================
# Cross-statement bare reference tests
# ===========================================================================


class TestCrossStatementBareReference(unittest.TestCase):
    """Bare variable references across INSERT/CREATE/MERGE statements."""

    def test_insert_cross_statement_bare_reuse(self):
        """Multi-INSERT chain with cross-statement bare references → no diagnostic."""
        query = (
            'INSERT (a:Person {name: "Andy"}), (b:Person {name: "Boris"}) '
            'INSERT (pb:Pet {name: "Boris"})<-[:HAS]-(a)-[:HAS]->(pa:Pet {name: "Andy"}) '
            "INSERT (b)-[:HAS]->(pb) "
            "INSERT (c)-[:HAS]->(pa)"
        )
        result = _analyze(query, dialect=_full)
        self.assertNotIn("variable-already-bound", _feature_ids(result))

    def test_create_cross_statement_bare_reuse(self):
        """CREATE (a:Person) CREATE (a)-[:KNOWS]->(b:Person) → no diagnostic."""
        result = _analyze("CREATE (a:Person) CREATE (a)-[:KNOWS]->(b:Person)")
        self.assertNotIn("variable-already-bound", _feature_ids(result))

    def test_match_create_relationship_ok(self):
        """MATCH (a), (b) CREATE (a)-[r:KNOWS]->(b) RETURN a, b, r → no undefined-variable."""
        result = _analyze("MATCH (a), (b) CREATE (a)-[r:KNOWS]->(b) RETURN a, b, r")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_merge_decorated_redeclaration(self):
        """MATCH (a) MERGE (a:Dog)-[r:T]->(b) → diagnostic (decorated filler)."""
        result = _analyze("MATCH (a) MERGE (a:Dog)-[r:T]->(b)")
        self.assertIn("variable-already-bound", _feature_ids(result))


# ===========================================================================
# Cross-check: integration queries must not produce false-positive scope errors
# ===========================================================================

_SCOPE_FALSE_POSITIVE_IDS = {
    "variable-already-bound",
    "undefined-variable",
    "distinct-order-by-non-projected",
}


class TestIntegrationQueriesNoFalsePositives(unittest.TestCase):
    """Every Neo4j-validated integration query must pass scope validation.

    If Neo4j accepts a query, our scope validator must not flag it.
    This test catches wrong test expectations: if someone writes
    assertIn("variable-already-bound", ...) for a valid query, this
    cross-check will fail for the same query.
    """

    def test_no_scope_false_positives(self):
        from tests.graphglot.integration.queries import ALL_QUERY_CASES

        failures: list[str] = []
        for tc in ALL_QUERY_CASES:
            if tc.xfail or tc.unsupported:
                continue
            result = _analyze(tc.gql)
            scope_diags = [
                d for d in result.diagnostics if d.feature_id in _SCOPE_FALSE_POSITIVE_IDS
            ]
            if scope_diags:
                msgs = "; ".join(d.message for d in scope_diags)
                failures.append(f"  {tc.id}: {msgs}")

        if failures:
            self.fail(
                f"{len(failures)} integration query(s) got false-positive scope errors:\n"
                + "\n".join(failures)
            )


# ===========================================================================
# CREATE/MERGE variable rebinding — Cypher CREATE rejects all bare rebinds,
# MERGE allows bare node refs if there's at least one new binding
# ===========================================================================


class TestCreateMergeRebinding(unittest.TestCase):
    """variable-already-bound: CREATE/MERGE rebinding semantics."""

    def test_create_bare_only_rebind(self):
        """MATCH (a) CREATE (a) → diagnostic (no new bindings in CREATE)."""
        result = _analyze("MATCH (a) CREATE (a)")
        self.assertIn("variable-already-bound", _feature_ids(result))

    def test_create_bare_edge_rebind(self):
        """MATCH ()-[r]->() CREATE ()-[r]->() → diagnostic (edge rebind)."""
        result = _analyze("MATCH ()-[r]->() CREATE ({name:'x'})-[r:T]->({name:'y'})")
        self.assertIn("variable-already-bound", _feature_ids(result))

    def test_create_bare_node_with_new_edge_ok(self):
        """MATCH (a), (b) CREATE (a)-[r:KNOWS]->(b) → no diagnostic."""
        result = _analyze("MATCH (a), (b) CREATE (a)-[r:KNOWS]->(b) RETURN r")
        self.assertNotIn("variable-already-bound", _feature_ids(result))

    def test_merge_only_bare_node(self):
        """MATCH (a) MERGE (a) → diagnostic (MERGE with no new bindings)."""
        result = _analyze("MATCH (a) MERGE (a)")
        self.assertIn("variable-already-bound", _feature_ids(result))

    def test_merge_edge_rebind(self):
        """MATCH (a)-[r]->(b) MERGE (a)-[r]->(b) → diagnostic (edge r rebind)."""
        result = _analyze("MATCH (a)-[r]->(b) MERGE (a)-[r:T]->(b)")
        self.assertIn("variable-already-bound", _feature_ids(result))

    def test_merge_bare_node_with_new_edge_ok(self):
        """MATCH (a) MERGE (a)-[:NEW]->(b) → no diagnostic (bare node ref + new edge)."""
        result = _analyze("MATCH (a) MERGE (a)-[:NEW]->(b)")
        self.assertNotIn("variable-already-bound", _feature_ids(result))


# ===========================================================================
# DISTINCT + ORDER BY scope — §14.10 SR III: with DISTINCT, ORDER BY refs
# must be in projected names
# ===========================================================================


class TestDistinctOrderByScope(unittest.TestCase):
    """DISTINCT + ORDER BY: sort keys must reference projected variables."""

    def test_distinct_order_by_non_projected(self):
        """RETURN DISTINCT a.name ORDER BY a.age → diagnostic (a.age uses unprojected var)."""
        result = _analyze("MATCH (a) RETURN DISTINCT a.name ORDER BY a.age")
        self.assertIn("distinct-order-by-non-projected", _feature_ids(result))

    def test_distinct_order_by_same_var_ok(self):
        """RETURN DISTINCT a.name ORDER BY a.name → no diagnostic (same var)."""
        result = _analyze("MATCH (a) RETURN DISTINCT a.name ORDER BY a.name")
        self.assertNotIn("distinct-order-by-non-projected", _feature_ids(result))

    def test_no_distinct_order_by_ok(self):
        """RETURN a.name ORDER BY a.age → no diagnostic (no DISTINCT)."""
        result = _analyze("MATCH (a) RETURN a.name ORDER BY a.age")
        self.assertNotIn("distinct-order-by-non-projected", _feature_ids(result))

    def test_distinct_order_by_alias_ok(self):
        """RETURN DISTINCT a.name AS n ORDER BY n → no diagnostic (alias)."""
        result = _analyze("MATCH (a) RETURN DISTINCT a.name AS n ORDER BY n")
        self.assertNotIn("distinct-order-by-non-projected", _feature_ids(result))


# ===========================================================================
# WHERE pattern predicate — unbounded variables
# ===========================================================================


class TestWherePatternPredicateScope(unittest.TestCase):
    """Cypher pattern predicates in WHERE must not introduce new variables."""

    def test_new_edge_in_where_pattern(self):
        """MATCH (n) WHERE (n)-[r]->() RETURN n → diagnostic (r undefined)."""
        result = _analyze("MATCH (n) WHERE (n)-[r]->() RETURN n")
        self.assertIn("undefined-variable", _feature_ids(result))
        msgs = _messages_for(result, "undefined-variable")
        self.assertTrue(any("r" in m for m in msgs))

    def test_new_node_in_where_pattern(self):
        """MATCH (n) WHERE (a) RETURN n → diagnostic (a undefined)."""
        result = _analyze("MATCH (n) WHERE (a) RETURN n")
        self.assertIn("undefined-variable", _feature_ids(result))
        msgs = _messages_for(result, "undefined-variable")
        self.assertTrue(any("a" in m for m in msgs))

    def test_normal_where_ok(self):
        """MATCH (n) WHERE n.active RETURN n → no diagnostic."""
        result = _analyze("MATCH (n) WHERE n.active RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_all_bound_pattern_ok(self):
        """MATCH (n)-[r]->(m) WHERE (n)-[r]->(m) RETURN n → no diagnostic."""
        result = _analyze("MATCH (n)-[r]->(m) WHERE (n)-[r]->(m) RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_pattern_inside_exists_ok(self):
        """Pattern predicate inside EXISTS is in its own scope — no false positive."""
        result = _analyze("MATCH (n) WHERE EXISTS { MATCH (m) WHERE (m)-[r]->() } RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))


class TestExistsSubqueryScope(unittest.TestCase):
    """Variables inside EXISTS subqueries must not leak to the outer scope."""

    def test_exists_with_match_new_var(self):
        """New variable inside EXISTS { MATCH } is scoped — no false positive."""
        result = _analyze("MATCH (n) WHERE EXISTS { MATCH (n)-[r]->(m) } RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_exists_for_new_var(self):
        """FOR inside EXISTS introduces a new variable — no false positive."""
        result = _analyze(
            "MATCH (n) WHERE EXISTS { FOR x IN LIST [1, 2, 3] RETURN x } RETURN n",
            dialect=_full,
        )
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_exists_for_with_filter(self):
        """FOR + FILTER inside EXISTS — variable used in filter is scoped."""
        result = _analyze(
            "MATCH (n) WHERE EXISTS { FOR x IN LIST [1, 2] FILTER WHERE x > 0 RETURN x } RETURN n",
            dialect=_full,
        )
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_with_exists_synthetic_nodes(self):
        """WITH + EXISTS: with_to_next builds synthetic nodes via _construct.

        The scope validator must not flag variables inside EXISTS as undefined
        even when parent pointers are absent (pruned DFS handles this).
        """
        result = _analyze("MATCH (n) WITH n WHERE EXISTS { MATCH (n)-[r]->(m) } RETURN n")
        self.assertNotIn("undefined-variable", _feature_ids(result))

    def test_exists_var_not_visible_outside(self):
        """Variable defined inside EXISTS must NOT be visible in outer RETURN."""
        result = _analyze("MATCH (n) WHERE EXISTS { MATCH (n)-[r]->(m) } RETURN m")
        self.assertIn("undefined-variable", _feature_ids(result))

    def test_outer_var_undefined_with_exists(self):
        """Undefined outer variable is still flagged even with EXISTS present."""
        result = _analyze("MATCH (n) WHERE EXISTS { MATCH (n)-[r]->(m) } RETURN z")
        self.assertIn("undefined-variable", _feature_ids(result))


# ===========================================================================
# CALL YIELD — duplicate/shadowing variables
# ===========================================================================


class TestCallYieldConflicts(unittest.TestCase):
    """CALL proc() YIELD must not shadow outer scope or have duplicates."""

    def test_yield_shadows_outer(self):
        """WITH 1 AS x CALL test.proc() YIELD x RETURN x → diagnostic (shadow)."""
        result = _analyze("WITH 1 AS x CALL test.proc() YIELD x RETURN x")
        self.assertIn("variable-already-bound", _feature_ids(result))

    def test_yield_duplicate_via_alias(self):
        """CALL test.proc() YIELD a, b AS a RETURN a → diagnostic (duplicate)."""
        result = _analyze("CALL test.proc() YIELD a, b AS a RETURN a", dialect=_full)
        self.assertIn("variable-already-bound", _feature_ids(result))

    def test_yield_no_conflict_ok(self):
        """CALL test.proc() YIELD a, b RETURN a, b → no diagnostic."""
        result = _analyze("CALL test.proc() YIELD a, b RETURN a, b", dialect=_full)
        self.assertNotIn("variable-already-bound", _feature_ids(result))
