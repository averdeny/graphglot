"""Tests for the Cypher extension layer (Plan 030, Phases 1-3).

Covers:
- CypherDialect class hierarchy and feature system
- Cypher-specific token types (STARTS, ENDS, CONTAINS, UNWIND, MERGE, =~, etc.)
- AST nodes: StringMatchPredicate, InPredicate, MergeClause,
  RegexMatchPredicate, ListComprehension, ListPredicateFunction
- Parser functions for string ops, IN, UNWIND, WITH→RETURN NEXT, MERGE, regex, list comp, list preds
- Parse → generate round-trip tests
- Feature gating: Cypher syntax raises FeatureError under base GQL dialect
- Neo4j inheritance from CypherDialect
"""

import typing as t
import unittest

from graphglot import ast, features as F
from graphglot.ast.cypher import (
    CypherWithStatement,
    InPredicate,
    StringMatchPredicate,
    TemporalBaseType,
)
from graphglot.ast.expressions import Predicate
from graphglot.dialect.base import Dialect
from graphglot.dialect.cypher import CypherDialect
from graphglot.dialect.cypher_features import CYPHER_FEATURES
from graphglot.dialect.neo4j import Neo4j
from graphglot.error import FeatureError, ParseError
from graphglot.features import Feature, get_feature
from graphglot.lexer import TokenType


def _ve(expr: ast.Expression) -> ast.ValueExpression:
    """Wrap a bare Expression in a ValueExpression for tests."""
    if isinstance(expr, ast.Identifier):
        expr = ast.BindingVariableReference(binding_variable=expr)
    return ast.ArithmeticValueExpression(
        base=ast.ArithmeticTerm(base=ast.ArithmeticFactor(arithmetic_primary=expr))
    )


# =============================================================================
# Dialect hierarchy tests
# =============================================================================


class TestCypherDialectHierarchy(unittest.TestCase):
    """Test CypherDialect class hierarchy and registration."""

    def test_cypher_dialect_exists(self):
        cls = Dialect.get("cypherdialect")
        self.assertIs(cls, CypherDialect)

    def test_neo4j_inherits_cypher(self):
        self.assertTrue(issubclass(Neo4j, CypherDialect))
        self.assertTrue(issubclass(Neo4j, Dialect))

    def test_neo4j_lexer_inherits_cypher(self):
        self.assertTrue(issubclass(Neo4j.Lexer, CypherDialect.Lexer))

    def test_neo4j_parser_inherits_cypher(self):
        self.assertTrue(issubclass(Neo4j.Parser, CypherDialect.Parser))

    def test_neo4j_generator_inherits_cypher(self):
        self.assertTrue(issubclass(Neo4j.Generator, CypherDialect.Generator))

    def test_neo4j_still_registered(self):
        cls = Dialect.get("neo4j")
        self.assertIs(cls, Neo4j)

    def test_cypher_dialect_not_in_dialects_enum(self):
        from graphglot.dialect.base import Dialects

        names = [d.value for d in Dialects]
        self.assertNotIn("cypherdialect", names)


# =============================================================================
# Feature system tests
# =============================================================================


class TestCypherFeatures(unittest.TestCase):
    """Test CY: feature definitions and integration."""

    def test_cypher_features_exist(self):
        self.assertGreater(len(CYPHER_FEATURES), 0)
        self.assertIn("CY:OP01", CYPHER_FEATURES)
        self.assertIn("CY:OP02", CYPHER_FEATURES)
        self.assertIn("CY:CL02", CYPHER_FEATURES)

    def test_get_feature_cypher(self):
        f = F.CY_OP01
        self.assertIsInstance(f, Feature)
        self.assertEqual(f.id, "CY:OP01")
        self.assertIn("STARTS WITH", f.description)

    def test_get_feature_gql_still_works(self):
        f = F.G002
        self.assertEqual(f.id, "G002")

    def test_get_feature_invalid(self):
        with self.assertRaises(ValueError):
            get_feature("INVALID_001")

    def test_cypher_feature_category(self):
        f = F.CY_OP01
        self.assertEqual(f.category(), "Cypher operators")
        f = F.CY_CL01
        self.assertEqual(f.category(), "Cypher clauses")

    def test_cypher_dialect_has_cypher_features(self):
        d = CypherDialect()
        for fid in ["CY:OP01", "CY:OP02", "CY:CL02"]:
            self.assertTrue(d.is_feature_supported(fid), f"{fid} should be supported")

    def test_neo4j_has_cypher_features(self):
        d = Neo4j()
        for fid in ["CY:OP01", "CY:OP02", "CY:CL02"]:
            self.assertTrue(d.is_feature_supported(fid), f"{fid} should be supported by Neo4j")

    def test_base_dialect_lacks_cypher_features(self):
        d = Dialect()
        for fid in ["CY:OP01", "CY:OP02", "CY:CL02"]:
            self.assertFalse(d.is_feature_supported(fid), f"{fid} should NOT be in base GQL")


# =============================================================================
# Tokenization tests
# =============================================================================


class TestCypherTokenization(unittest.TestCase):
    """Test Cypher-specific keyword tokenization."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _token_types(self, query):
        tokens = self.neo4j.tokenize(query)
        return [(t.text, t.token_type) for t in tokens]

    def test_starts_with(self):
        tokens = self._token_types("n STARTS WITH 'x'")
        self.assertEqual(tokens[1][1], TokenType.STARTS)
        self.assertEqual(tokens[2][1], TokenType.WITH)

    def test_ends_with(self):
        tokens = self._token_types("n ENDS WITH 'x'")
        self.assertEqual(tokens[1][1], TokenType.ENDS)

    def test_contains(self):
        tokens = self._token_types("n CONTAINS 'x'")
        self.assertEqual(tokens[1][1], TokenType.CONTAINS)

    def test_unwind(self):
        tokens = self._token_types("UNWIND [1] AS x")
        self.assertEqual(tokens[0][1], TokenType.UNWIND)

    def test_merge(self):
        tokens = self._token_types("MERGE (n)")
        self.assertEqual(tokens[0][1], TokenType.MERGE)


# =============================================================================
# AST node tests
# =============================================================================


class TestCypherAST(unittest.TestCase):
    """Test Cypher-specific AST nodes."""

    def test_string_match_predicate_creation(self):
        sp = StringMatchPredicate(
            lhs=_ve(ast.Identifier(name="x")),
            kind=StringMatchPredicate.MatchKind.STARTS_WITH,
            rhs=_ve(ast.CharacterStringLiteral(value="test")),
        )
        self.assertEqual(sp.kind, StringMatchPredicate.MatchKind.STARTS_WITH)
        self.assertTrue(ast.is_nonstandard(sp))

    def test_string_match_requires_feature(self):
        sp = StringMatchPredicate(
            lhs=_ve(ast.Identifier(name="x")),
            kind=StringMatchPredicate.MatchKind.CONTAINS,
            rhs=_ve(ast.CharacterStringLiteral(value="test")),
        )
        features = sp.get_required_features()
        feature_ids = {f.id for f in features}
        self.assertIn("CY:OP01", feature_ids)

    def test_in_predicate_creation(self):
        ip = InPredicate(
            value=_ve(ast.Identifier(name="x")),
            list_expression=_ve(ast.Identifier(name="items")),
        )
        self.assertIsInstance(ip, InPredicate)
        self.assertTrue(ast.is_nonstandard(ip))

    def test_in_predicate_requires_feature(self):
        ip = InPredicate(
            value=_ve(ast.Identifier(name="x")),
            list_expression=_ve(ast.Identifier(name="items")),
        )
        features = ip.get_required_features()
        feature_ids = {f.id for f in features}
        self.assertIn("CY:OP02", feature_ids)

    def test_predicates_inherit_from_predicate(self):
        """Cypher predicates should inherit from the Predicate base class."""
        self.assertTrue(issubclass(StringMatchPredicate, Predicate))
        self.assertTrue(issubclass(InPredicate, Predicate))


# =============================================================================
# Parser tests
# =============================================================================


class TestCypherParsing(unittest.TestCase):
    """Test Cypher-specific parsing under Neo4j dialect."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        return self.neo4j.parse(query)

    # --- String match predicates ---

    def test_parse_starts_with(self):
        results = self._parse("MATCH (n) WHERE n.name STARTS WITH 'Al' RETURN n")
        matches = list(results[0].find_all(StringMatchPredicate))
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].kind, StringMatchPredicate.MatchKind.STARTS_WITH)

    def test_parse_ends_with(self):
        results = self._parse("MATCH (n) WHERE n.name ENDS WITH 'ce' RETURN n")
        matches = list(results[0].find_all(StringMatchPredicate))
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].kind, StringMatchPredicate.MatchKind.ENDS_WITH)

    def test_parse_contains(self):
        results = self._parse("MATCH (n) WHERE n.name CONTAINS 'li' RETURN n")
        matches = list(results[0].find_all(StringMatchPredicate))
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].kind, StringMatchPredicate.MatchKind.CONTAINS)

    def test_parse_string_match_with_string_literal_rhs(self):
        results = self._parse("MATCH (n) WHERE n.name STARTS WITH 'prefix' RETURN n")
        matches = list(results[0].find_all(StringMatchPredicate))
        self.assertEqual(len(matches), 1)

    # --- IN predicate ---

    def test_parse_in_predicate(self):
        results = self._parse("MATCH (n) WHERE n.age IN [25, 30] RETURN n")
        matches = list(results[0].find_all(InPredicate))
        self.assertEqual(len(matches), 1)

    def test_parse_in_with_parameter(self):
        results = self._parse("MATCH (n) WHERE n.id IN $ids RETURN n")
        matches = list(results[0].find_all(InPredicate))
        self.assertEqual(len(matches), 1)

    # --- UNWIND ---

    def test_parse_unwind(self):
        results = self._parse("UNWIND [1, 2, 3] AS x RETURN x")
        # UNWIND is rewritten to ForStatement
        for_stmts = list(results[0].find_all(ast.ForStatement))
        self.assertEqual(len(for_stmts), 1)
        var = for_stmts[0].for_item.for_item_alias.binding_variable
        self.assertEqual(var.name, "x")

    def test_parse_unwind_with_variable(self):
        """WITH + UNWIND chain: WITH now parsed as RETURN...NEXT."""
        results = self._parse("MATCH (n) WITH COLLECT(n) AS nodes UNWIND nodes AS node RETURN node")
        for_stmts = list(results[0].find_all(ast.ForStatement))
        self.assertEqual(len(for_stmts), 1)
        self.assertEqual(for_stmts[0].for_item.for_item_alias.binding_variable.name, "node")

    # --- WITH clause (parsed as CypherWithStatement) ---

    def test_parse_with_basic(self):
        """WITH n.name AS name → CypherWithStatement."""
        results = self._parse("MATCH (n) WITH n.name AS name RETURN name")
        with_stmts = list(results[0].find_all(CypherWithStatement))
        self.assertEqual(len(with_stmts), 1)
        # RETURN still produces a ReturnStatement
        returns = list(results[0].find_all(ast.ReturnStatement))
        self.assertEqual(len(returns), 1)

    def test_parse_with_distinct(self):
        """WITH DISTINCT → ReturnStatementBody with SetQuantifier."""
        results = self._parse("MATCH (n) WITH DISTINCT n.name AS name RETURN name")
        quantifiers = list(results[0].find_all(ast.SetQuantifier))
        self.assertGreaterEqual(len(quantifiers), 1)

    def test_parse_with_where(self):
        """WITH ... WHERE → CypherWithStatement owns the WhereClause."""
        results = self._parse(
            "MATCH (n) WITH n.name AS name WHERE name STARTS WITH 'A' RETURN name"
        )
        from graphglot.ast.cypher import CypherWithStatement

        withs = list(results[0].find_all(CypherWithStatement))
        self.assertEqual(len(withs), 1)
        self.assertIsNotNone(withs[0].where_clause)

    def test_parse_with_order_by_and_limit(self):
        """WITH n ORDER BY n.name LIMIT 10 → PRS with OrderByAndPageStatement."""
        results = self._parse("MATCH (n) WITH n ORDER BY n.name LIMIT 10 RETURN n")
        obps = list(results[0].find_all(ast.OrderByAndPageStatement))
        self.assertGreaterEqual(len(obps), 1)

    def test_parse_with_skip(self):
        """WITH n SKIP 5 → PRS with OrderByAndPageStatement containing offset."""
        results = self._parse("MATCH (n) WITH n SKIP 5 RETURN n")
        offsets = list(results[0].find_all(ast.OffsetClause))
        self.assertGreaterEqual(len(offsets), 1)

    def test_parse_with_skip_and_limit(self):
        results = self._parse("MATCH (n) WITH n SKIP 5 LIMIT 10 RETURN n")
        offsets = list(results[0].find_all(ast.OffsetClause))
        limits = list(results[0].find_all(ast.LimitClause))
        self.assertGreaterEqual(len(offsets), 1)
        self.assertGreaterEqual(len(limits), 1)

    def test_parse_with_multiple_items(self):
        results = self._parse("MATCH (n) WITH n.name AS name, n.age AS age RETURN name, age")
        item_lists = list(results[0].find_all(ast.ReturnItemList))
        # At least one ReturnItemList with 2 items (from the WITH)
        has_two_items = any(len(il.list_return_item) == 2 for il in item_lists)
        self.assertTrue(has_two_items)

    def test_parse_chained_with(self):
        """Chained WITH produces multiple CypherWithStatements."""
        results = self._parse(
            "MATCH (n) WITH n.name AS name WITH name WHERE name STARTS WITH 'A' RETURN name"
        )
        with_stmts = list(results[0].find_all(CypherWithStatement))
        self.assertEqual(len(with_stmts), 2)

    # --- Combined predicates ---

    def test_parse_string_match_with_and(self):
        results = self._parse(
            "MATCH (n) WHERE n.name STARTS WITH 'A' AND n.name ENDS WITH 'z' RETURN n"
        )
        matches = list(results[0].find_all(StringMatchPredicate))
        self.assertEqual(len(matches), 2)
        kinds = {m.kind for m in matches}
        self.assertEqual(
            kinds,
            {StringMatchPredicate.MatchKind.STARTS_WITH, StringMatchPredicate.MatchKind.ENDS_WITH},
        )

    def test_parse_in_and_string_match_combined(self):
        results = self._parse("MATCH (n) WHERE n.age IN [25, 30] AND n.name CONTAINS 'x' RETURN n")
        in_preds = list(results[0].find_all(InPredicate))
        str_preds = list(results[0].find_all(StringMatchPredicate))
        self.assertEqual(len(in_preds), 1)
        self.assertEqual(len(str_preds), 1)

    # --- Standard GQL still works under Cypher ---

    def test_parse_standard_comparison_still_works(self):
        """Standard GQL comparisons must not be broken by Cypher predicate override."""
        results = self._parse("MATCH (n) WHERE n.age > 25 RETURN n")
        self.assertEqual(len(results), 1)
        comps = list(results[0].find_all(ast.ComparisonPredicate))
        self.assertEqual(len(comps), 1)

    def test_parse_standard_null_check_still_works(self):
        results = self._parse("MATCH (n) WHERE n.name IS NOT NULL RETURN n")
        self.assertEqual(len(results), 1)
        nulls = list(results[0].find_all(ast.NullPredicate))
        self.assertEqual(len(nulls), 1)

    def test_parse_standard_exists_still_works(self):
        results = self._parse("MATCH (n) WHERE EXISTS { MATCH (n)-[]->(m) } RETURN n")
        self.assertEqual(len(results), 1)
        exists = list(results[0].find_all(ast.ExistsPredicate))
        self.assertEqual(len(exists), 1)


# =============================================================================
# Round-trip tests (parse → generate → verify)
# =============================================================================


class TestCypherRoundTrip(unittest.TestCase):
    """Parse → generate round-trip tests for Cypher syntax."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _round_trip(self, query):
        """Parse then generate, return the generated string."""
        results = self.neo4j.parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return self.neo4j.generate(results[0])

    # --- String match predicates ---

    def test_round_trip_starts_with(self):
        result = self._round_trip("MATCH (n) WHERE n.name STARTS WITH 'Al' RETURN n")
        self.assertIn("STARTS WITH", result)
        self.assertIn("'Al'", result)

    def test_round_trip_ends_with(self):
        result = self._round_trip("MATCH (n) WHERE n.name ENDS WITH 'ce' RETURN n")
        self.assertIn("ENDS WITH", result)

    def test_round_trip_contains(self):
        result = self._round_trip("MATCH (n) WHERE n.name CONTAINS 'li' RETURN n")
        self.assertIn("CONTAINS", result)

    # --- IN predicate ---

    def test_round_trip_in_with_list(self):
        result = self._round_trip("MATCH (n) WHERE n.age IN [25, 30] RETURN n")
        self.assertIn("IN", result)
        self.assertIn("25", result)
        self.assertIn("30", result)

    def test_round_trip_in_with_parameter(self):
        result = self._round_trip("MATCH (n) WHERE n.id IN $ids RETURN n")
        self.assertIn("IN", result)

    # --- UNWIND ---

    def test_round_trip_unwind(self):
        result = self._round_trip("UNWIND [1, 2, 3] AS x RETURN x")
        self.assertIn("UNWIND", result)
        self.assertIn("AS", result)
        self.assertIn("x", result)
        self.assertNotIn("FOR", result)

    # --- WITH clause (now generates as RETURN...NEXT) ---

    def test_round_trip_with_basic(self):
        """WITH becomes RETURN ... NEXT in generated output."""
        result = self._round_trip("MATCH (n) WITH n.name AS name RETURN name")
        self.assertIn("RETURN", result)
        self.assertIn("AS", result)
        self.assertIn("name", result)

    def test_round_trip_with_distinct(self):
        result = self._round_trip("MATCH (n) WITH DISTINCT n.name AS name RETURN name")
        self.assertIn("RETURN", result)
        self.assertIn("DISTINCT", result)

    def test_round_trip_with_order_limit(self):
        result = self._round_trip("MATCH (n) WITH n ORDER BY n.name LIMIT 10 RETURN n")
        self.assertIn("RETURN", result)
        self.assertIn("ORDER BY", result)
        self.assertIn("LIMIT", result)

    def test_round_trip_with_skip_limit(self):
        result = self._round_trip("MATCH (n) WITH n SKIP 5 LIMIT 10 RETURN n")
        self.assertIn("OFFSET", result)  # GQL uses OFFSET not SKIP
        self.assertIn("LIMIT", result)

    def test_round_trip_with_where(self):
        """WITH ... WHERE becomes RETURN ... NEXT FILTER WHERE ... in output."""
        result = self._round_trip(
            "MATCH (n) WITH n.name AS name WHERE name STARTS WITH 'A' RETURN name"
        )
        self.assertIn("RETURN", result)
        self.assertIn("WHERE", result)
        self.assertIn("STARTS WITH", result)

    # --- Combined ---

    def test_round_trip_combined_predicates(self):
        result = self._round_trip(
            "MATCH (n) WHERE n.name STARTS WITH 'A' AND n.age IN [25, 30] RETURN n"
        )
        self.assertIn("STARTS WITH", result)
        self.assertIn("IN", result)


# =============================================================================
# Generator unit tests
# =============================================================================


class TestCypherGeneration(unittest.TestCase):
    """Test Cypher-specific code generation from manually constructed AST."""

    def setUp(self):
        self.neo4j = Neo4j()

    def test_generate_starts_with(self):
        sp = StringMatchPredicate(
            lhs=_ve(ast.Identifier(name="x")),
            kind=StringMatchPredicate.MatchKind.STARTS_WITH,
            rhs=_ve(ast.CharacterStringLiteral(value="test")),
        )
        gen = self.neo4j.generator()
        result = gen.dispatch(sp).render()
        self.assertIn("STARTS WITH", result)

    def test_generate_ends_with(self):
        sp = StringMatchPredicate(
            lhs=_ve(ast.Identifier(name="x")),
            kind=StringMatchPredicate.MatchKind.ENDS_WITH,
            rhs=_ve(ast.CharacterStringLiteral(value="test")),
        )
        gen = self.neo4j.generator()
        result = gen.dispatch(sp).render()
        self.assertIn("ENDS WITH", result)

    def test_generate_contains(self):
        sp = StringMatchPredicate(
            lhs=_ve(ast.Identifier(name="x")),
            kind=StringMatchPredicate.MatchKind.CONTAINS,
            rhs=_ve(ast.CharacterStringLiteral(value="test")),
        )
        gen = self.neo4j.generator()
        result = gen.dispatch(sp).render()
        self.assertIn("CONTAINS", result)

    def test_generate_in_predicate(self):
        ip = InPredicate(
            value=_ve(ast.Identifier(name="x")),
            list_expression=_ve(ast.Identifier(name="items")),
        )
        gen = self.neo4j.generator()
        result = gen.dispatch(ip).render()
        self.assertIn("IN", result)


# =============================================================================
# Feature gating tests
# =============================================================================


class TestFeatureGating(unittest.TestCase):
    """Test that Cypher syntax is rejected under base GQL dialect."""

    def test_gql_rejects_starts_with(self):
        """Base GQL dialect should reject STARTS WITH (not a GQL keyword)."""
        d = Dialect()
        with self.assertRaises((ParseError, FeatureError)):
            d.parse("MATCH (n) WHERE n.name STARTS WITH 'Al' RETURN n")

    def test_gql_rejects_ends_with(self):
        d = Dialect()
        with self.assertRaises((ParseError, FeatureError)):
            d.parse("MATCH (n) WHERE n.name ENDS WITH 'ce' RETURN n")

    def test_gql_rejects_contains(self):
        d = Dialect()
        with self.assertRaises((ParseError, FeatureError)):
            d.parse("MATCH (n) WHERE n.name CONTAINS 'li' RETURN n")

    def test_gql_rejects_in(self):
        """Base GQL dialect should reject Cypher IN syntax."""
        d = Dialect()
        with self.assertRaises((ParseError, FeatureError)):
            d.parse("MATCH (n) WHERE n.age IN [25, 30] RETURN n")

    def test_gql_rejects_unwind(self):
        """Base GQL dialect should reject UNWIND (not a GQL keyword)."""
        d = Dialect()
        with self.assertRaises((ParseError, FeatureError)):
            d.parse("UNWIND [1, 2, 3] AS x RETURN x")

    def test_gql_rejects_with_clause(self):
        """Base GQL dialect should reject Cypher WITH as pipeline operator.

        WITH is not the RETURN keyword, so it fails to parse as a
        PrimitiveResultStatement under the standard GQL parser.
        """
        d = Dialect()
        with self.assertRaises((ParseError, FeatureError)):
            d.parse("MATCH (n) WITH n.name AS name RETURN name")


# =============================================================================
# Neo4j backward compatibility tests
# =============================================================================


class TestNeo4jBackwardCompat(unittest.TestCase):
    """Verify Neo4j dialect still works after CypherDialect refactoring."""

    def setUp(self):
        self.neo4j = Neo4j()

    def test_neo4j_parse_basic(self):
        results = self.neo4j.parse("MATCH (n) RETURN n")
        self.assertEqual(len(results), 1)

    def test_neo4j_parse_where(self):
        results = self.neo4j.parse("MATCH (n) WHERE n.age > 25 RETURN n.name")
        self.assertEqual(len(results), 1)

    def test_neo4j_generate_basic(self):
        results = self.neo4j.parse("MATCH (n) RETURN n")
        generated = self.neo4j.generate(results[0])
        self.assertIn("MATCH", generated)
        self.assertIn("RETURN", generated)

    def test_neo4j_exponential(self):
        """Neo4j's e() -> EXP(1) still works."""
        results = self.neo4j.parse("RETURN EXP(2)")
        self.assertEqual(len(results), 1)

    def test_neo4j_keyword_overrides(self):
        self.assertIn("COLLECT_LIST", self.neo4j.KEYWORD_OVERRIDES)
        self.assertEqual(self.neo4j.KEYWORD_OVERRIDES["COLLECT_LIST"], "COLLECT")

    def test_neo4j_comments(self):
        """Neo4j uses // comments, not --."""
        results = self.neo4j.parse("// comment\nMATCH (n) RETURN n")
        self.assertEqual(len(results), 1)

    def test_neo4j_round_trip_basic(self):
        """Basic GQL round-trip still works under Neo4j."""
        results = self.neo4j.parse("MATCH (n)-[r]->(m) RETURN n, r, m")
        generated = self.neo4j.generate(results[0])
        self.assertIn("MATCH", generated)
        self.assertIn("RETURN", generated)

    def test_neo4j_round_trip_where(self):
        results = self.neo4j.parse("MATCH (n) WHERE n.age > 25 RETURN n.name")
        generated = self.neo4j.generate(results[0])
        self.assertIn("WHERE", generated)


# =============================================================================
# MERGE clause tests
# =============================================================================


class TestCypherMerge(unittest.TestCase):
    """Test MERGE clause parsing, generation, and feature gating."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        return self.neo4j.parse(query)

    def _round_trip(self, query):
        results = self.neo4j.parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return self.neo4j.generate(results[0])

    # --- Parsing tests ---

    def test_merge_simple_node(self):
        results = self._parse("MERGE (n:Person)")
        from graphglot.ast.cypher import MergeClause

        merges = list(results[0].find_all(MergeClause))
        self.assertEqual(len(merges), 1)
        self.assertIsNone(merges[0].on_create_set)
        self.assertIsNone(merges[0].on_match_set)

    def test_merge_node_with_properties(self):
        results = self._parse("MERGE (n:Person {name: 'Alice'})")
        from graphglot.ast.cypher import MergeClause

        merges = list(results[0].find_all(MergeClause))
        self.assertEqual(len(merges), 1)
        # The path pattern should contain property specification
        props = list(merges[0].find_all(ast.ElementPropertySpecification))
        self.assertGreater(len(props), 0)

    def test_merge_with_on_create_set(self):
        results = self._parse("MERGE (n:Person) ON CREATE SET n.created = 1")
        from graphglot.ast.cypher import MergeClause

        merges = list(results[0].find_all(MergeClause))
        self.assertEqual(len(merges), 1)
        self.assertIsNotNone(merges[0].on_create_set)
        self.assertIsNone(merges[0].on_match_set)

    def test_merge_with_on_match_set(self):
        results = self._parse("MERGE (n:Person) ON MATCH SET n.updated = 1")
        from graphglot.ast.cypher import MergeClause

        merges = list(results[0].find_all(MergeClause))
        self.assertEqual(len(merges), 1)
        self.assertIsNone(merges[0].on_create_set)
        self.assertIsNotNone(merges[0].on_match_set)

    def test_merge_with_both_on_clauses(self):
        results = self._parse("MERGE (n:Person) ON CREATE SET n.a = 1 ON MATCH SET n.b = 2")
        from graphglot.ast.cypher import MergeClause

        merges = list(results[0].find_all(MergeClause))
        self.assertEqual(len(merges), 1)
        self.assertIsNotNone(merges[0].on_create_set)
        self.assertIsNotNone(merges[0].on_match_set)

    def test_merge_relationship(self):
        results = self._parse("MERGE (a)-[r:KNOWS]->(b)")
        from graphglot.ast.cypher import MergeClause

        merges = list(results[0].find_all(MergeClause))
        self.assertEqual(len(merges), 1)
        # Should have an edge pattern in the path
        edges = list(merges[0].find_all(ast.EdgePattern))
        self.assertGreater(len(edges), 0)

    # --- Round-trip tests ---

    def test_merge_round_trip_simple(self):
        result = self._round_trip("MERGE (n:Person)")
        self.assertIn("MERGE", result)
        self.assertIn("Person", result)

    def test_merge_round_trip_with_on_clauses(self):
        result = self._round_trip("MERGE (n:Person) ON CREATE SET n.a = 1 ON MATCH SET n.b = 2")
        self.assertIn("MERGE", result)
        self.assertIn("ON CREATE SET", result)
        self.assertIn("ON MATCH SET", result)

    def test_merge_round_trip_relationship(self):
        result = self._round_trip("MERGE (a)-[r:KNOWS]->(b)")
        self.assertIn("MERGE", result)
        self.assertIn("KNOWS", result)

    # --- Combined query tests ---

    def test_match_then_merge(self):
        results = self._parse("MATCH (a:Person) MERGE (a)-[:KNOWS]->(:Person {name: 'Bob'})")
        from graphglot.ast.cypher import MergeClause

        self.assertEqual(len(results), 1)
        merges = list(results[0].find_all(MergeClause))
        self.assertEqual(len(merges), 1)
        matches = list(results[0].find_all(ast.MatchStatement))
        self.assertEqual(len(matches), 1)

    def test_merge_then_return(self):
        results = self._parse("MERGE (n:Person {name: 'Alice'}) RETURN n")
        from graphglot.ast.cypher import MergeClause

        self.assertEqual(len(results), 1)
        merges = list(results[0].find_all(MergeClause))
        self.assertEqual(len(merges), 1)

    # --- Feature gating test ---

    def test_merge_feature_gating(self):
        """MergeClause should raise FeatureError or ParseError under base GQL dialect."""
        d = Dialect()
        with self.assertRaises((ParseError, FeatureError)):
            d.parse("MERGE (n:Person)")


# =============================================================================
# Regex match operator tests (Phase 3)
# =============================================================================


class TestCypherRegexMatch(unittest.TestCase):
    """Test regex match operator (=~) parsing, generation, and feature gating."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        return self.neo4j.parse(query)

    def _round_trip(self, query):
        results = self.neo4j.parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return self.neo4j.generate(results[0])

    def test_regex_simple(self):
        from graphglot.ast.cypher import RegexMatchPredicate

        results = self._parse("MATCH (n) WHERE n.name =~ 'Al.*' RETURN n")
        matches = list(results[0].find_all(RegexMatchPredicate))
        self.assertEqual(len(matches), 1)

    def test_regex_case_insensitive(self):
        from graphglot.ast.cypher import RegexMatchPredicate

        results = self._parse("MATCH (n) WHERE n.name =~ '(?i)alice' RETURN n")
        matches = list(results[0].find_all(RegexMatchPredicate))
        self.assertEqual(len(matches), 1)

    def test_regex_round_trip(self):
        result = self._round_trip("MATCH (n) WHERE n.name =~ 'Al.*' RETURN n")
        self.assertIn("=~", result)
        self.assertIn("'Al.*'", result)

    def test_regex_in_and_clause(self):
        from graphglot.ast.cypher import RegexMatchPredicate

        results = self._parse("MATCH (n) WHERE n.name =~ 'A.*' AND n.age > 20 RETURN n")
        regex_preds = list(results[0].find_all(RegexMatchPredicate))
        self.assertEqual(len(regex_preds), 1)
        comp_preds = list(results[0].find_all(ast.ComparisonPredicate))
        self.assertEqual(len(comp_preds), 1)

    def test_regex_feature_gating(self):
        """Base GQL dialect should reject =~ syntax."""
        d = Dialect()
        with self.assertRaises((ParseError, FeatureError)):
            d.parse("MATCH (n) WHERE n.name =~ 'Al.*' RETURN n")


# =============================================================================
# List comprehension tests (Phase 3)
# =============================================================================


class TestCypherListComprehension(unittest.TestCase):
    """Test list comprehension parsing, generation, and feature gating."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        return self.neo4j.parse(query)

    def _round_trip(self, query):
        results = self.neo4j.parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return self.neo4j.generate(results[0])

    def test_list_comp_full(self):
        from graphglot.ast.cypher import ListComprehension

        results = self._parse("RETURN [x IN [1, 2, 3] WHERE x > 1 | x * 2]")
        comps = list(results[0].find_all(ListComprehension))
        self.assertEqual(len(comps), 1)
        self.assertIsNotNone(comps[0].where_clause)
        self.assertIsNotNone(comps[0].projection)

    def test_list_comp_no_where(self):
        from graphglot.ast.cypher import ListComprehension

        results = self._parse("RETURN [x IN [1, 2, 3] | x * 2]")
        comps = list(results[0].find_all(ListComprehension))
        self.assertEqual(len(comps), 1)
        self.assertIsNone(comps[0].where_clause)
        self.assertIsNotNone(comps[0].projection)

    def test_list_comp_no_projection(self):
        from graphglot.ast.cypher import ListComprehension

        results = self._parse("RETURN [x IN [1, 2, 3] WHERE x > 1]")
        comps = list(results[0].find_all(ListComprehension))
        self.assertEqual(len(comps), 1)
        self.assertIsNotNone(comps[0].where_clause)
        self.assertIsNone(comps[0].projection)

    def test_list_comp_identity(self):
        from graphglot.ast.cypher import ListComprehension

        results = self._parse("RETURN [x IN [1, 2, 3]]")
        comps = list(results[0].find_all(ListComprehension))
        self.assertEqual(len(comps), 1)
        self.assertIsNone(comps[0].where_clause)
        self.assertIsNone(comps[0].projection)

    def test_list_comp_round_trip(self):
        result = self._round_trip("RETURN [x IN [1, 2, 3] WHERE x > 1 | x * 2]")
        self.assertIn("[", result)
        self.assertIn("IN", result)
        self.assertIn("WHERE", result)
        self.assertIn("|", result)

    def test_list_literal_still_works(self):
        """Standard list literals must not be broken by list comprehension override."""
        results = self._parse("RETURN [1, 2, 3]")
        self.assertEqual(len(results), 1)
        lists = list(results[0].find_all(ast.ListValueConstructorByEnumeration))
        self.assertGreater(len(lists), 0)

    def test_list_comp_in_return(self):
        from graphglot.ast.cypher import ListComprehension

        results = self._parse("MATCH (n) RETURN [x IN [1, 2, 3] | x * 2]")
        comps = list(results[0].find_all(ListComprehension))
        self.assertEqual(len(comps), 1)

    def test_list_comp_feature_gating(self):
        """Base GQL dialect should reject list comprehension syntax."""
        d = Dialect()
        # This would parse [x ...] as list literal and fail, or if it somehow
        # creates a ListComprehension, the feature check should reject it
        with self.assertRaises((ParseError, FeatureError)):
            d.parse("RETURN [x IN [1, 2, 3] | x * 2]")

    def test_list_comp_with_label_check_and_projection(self):
        """Pipe after label check is projection separator, not label disjunction."""
        from graphglot.ast.cypher import ListComprehension

        results = self._parse("RETURN [x IN nodes(p) WHERE x:Concept | x.name]")
        comps = list(results[0].find_all(ListComprehension))
        self.assertEqual(len(comps), 1)
        self.assertIsNotNone(comps[0].where_clause)
        self.assertIsNotNone(comps[0].projection)

    def test_list_comp_label_check_projection_round_trip(self):
        """Round-trip preserves label + projection with pipe separator."""
        result = self._round_trip("RETURN [x IN nodes(p) WHERE x:Concept | x.name]")
        self.assertIn(":Concept", result)
        self.assertIn("| x.name", result)

    def test_list_comp_label_disjunction_without_projection(self):
        """Pipe IS label disjunction when followed by a label name."""
        from graphglot.ast.cypher import ListComprehension

        results = self._parse("RETURN [x IN nodes(p) WHERE x:A|B]")
        comps = list(results[0].find_all(ListComprehension))
        self.assertEqual(len(comps), 1)
        self.assertIsNotNone(comps[0].where_clause)
        # No projection — | was consumed as label disjunction
        self.assertIsNone(comps[0].projection)

    def test_list_comp_complex_label_and_projection(self):
        """Original failing query: coalesce() after pipe is projection."""
        from graphglot.ast.cypher import ListComprehension

        results = self._parse(
            'RETURN [x IN nodes(path) WHERE x:Concept | coalesce(x.prefLabel, "")]'
        )
        comps = list(results[0].find_all(ListComprehension))
        self.assertEqual(len(comps), 1)
        self.assertIsNotNone(comps[0].where_clause)
        self.assertIsNotNone(comps[0].projection)

    def test_list_comp_label_disjunction_then_projection(self):
        """Label disjunction followed by projection: first | is label, second is projection."""
        from graphglot.ast.cypher import ListComprehension

        results = self._parse("RETURN [x IN nodes(p) WHERE x:Concept|NewConcept | x.name]")
        comps = list(results[0].find_all(ListComprehension))
        self.assertEqual(len(comps), 1)
        self.assertIsNotNone(comps[0].where_clause)
        self.assertIsNotNone(comps[0].projection)
        # Verify label disjunction has two terms
        label_exprs = list(results[0].find_all(ast.LabelExpression))
        self.assertTrue(
            any(len(le.label_terms) == 2 for le in label_exprs),
            "Expected a LabelExpression with 2 terms (Concept|NewConcept)",
        )


# =============================================================================
# List predicate function tests (Phase 3)
# =============================================================================


class TestCypherListPredicateFunction(unittest.TestCase):
    """Test list predicate functions (all/any/none/single) parsing, generation, feature gating."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        return self.neo4j.parse(query)

    def _round_trip(self, query):
        results = self.neo4j.parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return self.neo4j.generate(results[0])

    def test_all_predicate(self):
        from graphglot.ast.cypher import ListPredicateFunction

        results = self._parse("MATCH (n) WHERE all(x IN [1, 2, 3] WHERE x > 1) RETURN n")
        preds = list(results[0].find_all(ListPredicateFunction))
        self.assertEqual(len(preds), 1)
        self.assertEqual(preds[0].kind, ListPredicateFunction.Kind.ALL)

    def test_any_predicate(self):
        from graphglot.ast.cypher import ListPredicateFunction

        results = self._parse("MATCH (n) WHERE any(x IN [1, 2, 3] WHERE x > 5) RETURN n")
        preds = list(results[0].find_all(ListPredicateFunction))
        self.assertEqual(len(preds), 1)
        self.assertEqual(preds[0].kind, ListPredicateFunction.Kind.ANY)

    def test_none_predicate(self):
        from graphglot.ast.cypher import ListPredicateFunction

        results = self._parse("MATCH (n) WHERE none(x IN [1, 2, 3] WHERE x < 1) RETURN n")
        preds = list(results[0].find_all(ListPredicateFunction))
        self.assertEqual(len(preds), 1)
        self.assertEqual(preds[0].kind, ListPredicateFunction.Kind.NONE)

    def test_single_predicate(self):
        from graphglot.ast.cypher import ListPredicateFunction

        results = self._parse("MATCH (n) WHERE single(x IN [1, 2, 3] WHERE x = 1) RETURN n")
        preds = list(results[0].find_all(ListPredicateFunction))
        self.assertEqual(len(preds), 1)
        self.assertEqual(preds[0].kind, ListPredicateFunction.Kind.SINGLE)

    def test_all_round_trip(self):
        result = self._round_trip("MATCH (n) WHERE all(x IN [1, 2, 3] WHERE x > 1) RETURN n")
        self.assertIn("all", result)
        self.assertIn("IN", result)
        self.assertIn("WHERE", result)

    def test_any_round_trip(self):
        result = self._round_trip("MATCH (n) WHERE any(x IN [1, 2, 3] WHERE x > 5) RETURN n")
        self.assertIn("any", result)
        self.assertIn("IN", result)
        self.assertIn("WHERE", result)

    def test_list_pred_with_property_access(self):
        from graphglot.ast.cypher import ListPredicateFunction

        results = self._parse("MATCH (n) WHERE all(x IN [n.age] WHERE x > 1) RETURN n")
        preds = list(results[0].find_all(ListPredicateFunction))
        self.assertEqual(len(preds), 1)

    def test_all_does_not_break_path_search(self):
        """MATCH ALL SHORTEST ... must still work (ALL followed by SHORTEST, not ALL()."""
        results = self._parse("MATCH ALL SHORTEST (a:Person)-[]->{1,5}(b:Person) RETURN a")
        self.assertEqual(len(results), 1)
        # Should have AllShortestPathSearch, not ListPredicateFunction
        from graphglot.ast.cypher import ListPredicateFunction

        preds = list(results[0].find_all(ListPredicateFunction))
        self.assertEqual(len(preds), 0)

    def test_any_does_not_break_path_search(self):
        """MATCH ANY SHORTEST ... must still work."""
        results = self._parse("MATCH ANY SHORTEST (a:Person)-[]->{1,5}(b:Person) RETURN a")
        self.assertEqual(len(results), 1)
        from graphglot.ast.cypher import ListPredicateFunction

        preds = list(results[0].find_all(ListPredicateFunction))
        self.assertEqual(len(preds), 0)

    # --- Expression-context tests (RETURN) ---

    def test_none_in_return_context(self):
        """none() must work in RETURN, not just WHERE."""
        from graphglot.ast.cypher import ListPredicateFunction

        results = self._parse("RETURN none(x IN [1, 2, 3] WHERE x = 2) AS result")
        self.assertEqual(len(results), 1)
        preds = list(results[0].find_all(ListPredicateFunction))
        self.assertEqual(len(preds), 1)
        self.assertEqual(preds[0].kind, ListPredicateFunction.Kind.NONE)

    def test_all_in_return_context(self):
        """all() must work in RETURN, not just WHERE."""
        from graphglot.ast.cypher import ListPredicateFunction

        results = self._parse("RETURN all(x IN [1, 2, 3] WHERE x > 0) AS result")
        self.assertEqual(len(results), 1)
        preds = list(results[0].find_all(ListPredicateFunction))
        self.assertEqual(len(preds), 1)
        self.assertEqual(preds[0].kind, ListPredicateFunction.Kind.ALL)

    def test_single_in_return_context(self):
        """single() must work in RETURN, not just WHERE."""
        from graphglot.ast.cypher import ListPredicateFunction

        results = self._parse("RETURN single(x IN [1, 2, 3] WHERE x = 2) AS result")
        self.assertEqual(len(results), 1)
        preds = list(results[0].find_all(ListPredicateFunction))
        self.assertEqual(len(preds), 1)
        self.assertEqual(preds[0].kind, ListPredicateFunction.Kind.SINGLE)

    def test_nested_quantifiers_in_return(self):
        """Nested quantifier predicates in RETURN context."""
        results = self._parse(
            "RETURN none(x IN [['a'], ['a', 'b']] WHERE none(y IN x WHERE y = 'a')) AS r"
        )
        self.assertEqual(len(results), 1)

    def test_quantifier_after_comma_in_return(self):
        """Quantifier after comma: RETURN 1 AS a, all(...) AS b."""
        results = self._parse("RETURN 1 AS a, all(x IN [1, 2] WHERE x > 0) AS b")
        self.assertEqual(len(results), 1)

    def test_round_trip_quantifier_return(self):
        """Round-trip for quantifier predicates in expression context."""
        for query in [
            "RETURN all(x IN [1, 2, 3] WHERE x > 0) AS r",
            "RETURN none(x IN [1, 2] WHERE x < 0) AS r",
            "RETURN single(x IN [1, 2, 3] WHERE x = 2) AS r",
        ]:
            with self.subTest(query=query):
                generated = self._round_trip(query)
                results2 = self._parse(generated)
                self.assertEqual(len(results2), 1)

    def test_none_as_identifier_still_works(self):
        """RETURN none AS x — none used as identifier must still work."""
        results = self._parse("MATCH (none) RETURN none")
        self.assertEqual(len(results), 1)

    def test_single_as_identifier_still_works(self):
        """RETURN single AS x — single used as identifier must still work."""
        results = self._parse("MATCH (single) RETURN single")
        self.assertEqual(len(results), 1)

    def test_list_pred_feature_gating(self):
        """Base GQL dialect should reject list predicate functions."""
        d = Dialect()
        with self.assertRaises((ParseError, FeatureError)):
            d.parse("MATCH (n) WHERE all(x IN [1] WHERE x > 0) RETURN n")


# =============================================================================
# EXPLAIN / PROFILE query prefix tests (Plan 031 Phase 1)
# =============================================================================


class TestCypherQueryPrefix(unittest.TestCase):
    """Test EXPLAIN/PROFILE query prefix parsing, generation, and feature gating."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        return self.neo4j.parse(query)

    def _round_trip(self, query):
        results = self.neo4j.parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return self.neo4j.generate(results[0])

    def test_explain_match(self):
        from graphglot.ast.cypher import QueryPrefix

        results = self._parse("EXPLAIN MATCH (n) RETURN n")
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], QueryPrefix)
        self.assertEqual(results[0].kind, QueryPrefix.Kind.EXPLAIN)

    def test_profile_match(self):
        from graphglot.ast.cypher import QueryPrefix

        results = self._parse("PROFILE MATCH (n) RETURN n")
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], QueryPrefix)
        self.assertEqual(results[0].kind, QueryPrefix.Kind.PROFILE)

    def test_explain_round_trip(self):
        result = self._round_trip("EXPLAIN MATCH (n) RETURN n")
        self.assertIn("EXPLAIN", result)
        self.assertIn("MATCH", result)
        self.assertIn("RETURN", result)

    def test_profile_round_trip(self):
        result = self._round_trip("PROFILE MATCH (n) RETURN n")
        self.assertIn("PROFILE", result)
        self.assertIn("MATCH", result)
        self.assertIn("RETURN", result)

    def test_explain_complex(self):
        from graphglot.ast.cypher import QueryPrefix

        results = self._parse("EXPLAIN MATCH (n)-[r]->(m) WHERE n.name = 'Alice' RETURN m")
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], QueryPrefix)
        self.assertEqual(results[0].kind, QueryPrefix.Kind.EXPLAIN)

    def test_query_prefix_feature_gating(self):
        """Base GQL dialect should reject EXPLAIN/PROFILE (not GQL keywords)."""
        d = Dialect()
        with self.assertRaises((ParseError, FeatureError)):
            d.parse("EXPLAIN MATCH (n) RETURN n")


# =============================================================================
# CREATE / DROP INDEX tests (Plan 031 Phase 2)
# =============================================================================


class TestCypherIndex(unittest.TestCase):
    """Test CREATE/DROP INDEX parsing, generation, and feature gating."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        return self.neo4j.parse(query)

    def _round_trip(self, query):
        results = self.neo4j.parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return self.neo4j.generate(results[0])

    def _find_one(self, query, cls):
        results = self._parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        found = list(results[0].find_all(cls))
        self.assertEqual(len(found), 1, f"Expected 1 {cls.__name__} in: {query}")
        return found[0]

    def test_create_index_simple(self):
        from graphglot.ast.cypher import CreateIndex

        idx = self._find_one("CREATE INDEX FOR (n:Person) ON (n.name)", CreateIndex)
        self.assertIsNone(idx.name)
        self.assertFalse(idx.if_not_exists)
        self.assertFalse(idx.is_relationship)
        self.assertEqual(len(idx.properties), 1)

    def test_create_index_named(self):
        from graphglot.ast.cypher import CreateIndex

        idx = self._find_one("CREATE INDEX my_idx FOR (n:Person) ON (n.name)", CreateIndex)
        self.assertEqual(idx.name.name, "my_idx")

    def test_create_index_if_not_exists(self):
        from graphglot.ast.cypher import CreateIndex

        idx = self._find_one(
            "CREATE INDEX my_idx IF NOT EXISTS FOR (n:Person) ON (n.name)",
            CreateIndex,
        )
        self.assertTrue(idx.if_not_exists)

    def test_create_index_multi_property(self):
        from graphglot.ast.cypher import CreateIndex

        idx = self._find_one("CREATE INDEX FOR (n:Person) ON (n.first, n.last)", CreateIndex)
        self.assertEqual(len(idx.properties), 2)

    def test_create_index_relationship(self):
        from graphglot.ast.cypher import CreateIndex

        idx = self._find_one("CREATE INDEX FOR ()-[r:KNOWS]-() ON (r.since)", CreateIndex)
        self.assertTrue(idx.is_relationship)
        self.assertEqual(idx.label.name, "KNOWS")

    def test_drop_index(self):
        from graphglot.ast.cypher import DropIndex

        idx = self._find_one("DROP INDEX my_idx", DropIndex)
        self.assertEqual(idx.name.name, "my_idx")
        self.assertFalse(idx.if_exists)

    def test_drop_index_if_exists(self):
        from graphglot.ast.cypher import DropIndex

        idx = self._find_one("DROP INDEX my_idx IF EXISTS", DropIndex)
        self.assertTrue(idx.if_exists)

    def test_create_index_round_trip(self):
        result = self._round_trip("CREATE INDEX FOR (n:Person) ON (n.name)")
        self.assertIn("CREATE", result)
        self.assertIn("INDEX", result)
        self.assertIn("Person", result)
        self.assertIn("ON", result)


# =============================================================================
# CREATE / DROP CONSTRAINT tests (Plan 031 Phase 3)
# =============================================================================


class TestCypherConstraint(unittest.TestCase):
    """Test CREATE/DROP CONSTRAINT parsing, generation, and feature gating."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        return self.neo4j.parse(query)

    def _round_trip(self, query):
        results = self.neo4j.parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return self.neo4j.generate(results[0])

    def _find_one(self, query, cls):
        results = self._parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        found = list(results[0].find_all(cls))
        self.assertEqual(len(found), 1, f"Expected 1 {cls.__name__} in: {query}")
        return found[0]

    def test_create_constraint_unique(self):
        from graphglot.ast.cypher import ConstraintKind, CreateConstraint

        con = self._find_one(
            "CREATE CONSTRAINT FOR (n:Person) REQUIRE n.email IS UNIQUE",
            CreateConstraint,
        )
        self.assertEqual(con.constraint_kind, ConstraintKind.UNIQUE)
        self.assertIsNone(con.name)
        self.assertFalse(con.if_not_exists)

    def test_create_constraint_not_null(self):
        from graphglot.ast.cypher import ConstraintKind, CreateConstraint

        con = self._find_one(
            "CREATE CONSTRAINT FOR (n:Person) REQUIRE n.name IS NOT NULL",
            CreateConstraint,
        )
        self.assertEqual(con.constraint_kind, ConstraintKind.NOT_NULL)

    def test_create_constraint_node_key(self):
        from graphglot.ast.cypher import ConstraintKind, CreateConstraint

        con = self._find_one(
            "CREATE CONSTRAINT FOR (n:Person) REQUIRE (n.first, n.last) IS NODE KEY",
            CreateConstraint,
        )
        self.assertEqual(con.constraint_kind, ConstraintKind.NODE_KEY)
        self.assertEqual(len(con.properties), 2)

    def test_create_constraint_named(self):
        from graphglot.ast.cypher import CreateConstraint

        con = self._find_one(
            "CREATE CONSTRAINT my_con FOR (n:Person) REQUIRE n.email IS UNIQUE",
            CreateConstraint,
        )
        self.assertEqual(con.name.name, "my_con")

    def test_create_constraint_if_not_exists(self):
        from graphglot.ast.cypher import CreateConstraint

        con = self._find_one(
            "CREATE CONSTRAINT my_con IF NOT EXISTS FOR (n:Person) REQUIRE n.email IS UNIQUE",
            CreateConstraint,
        )
        self.assertTrue(con.if_not_exists)

    def test_drop_constraint(self):
        from graphglot.ast.cypher import DropConstraint

        con = self._find_one("DROP CONSTRAINT my_con", DropConstraint)
        self.assertEqual(con.name.name, "my_con")
        self.assertFalse(con.if_exists)

    def test_drop_constraint_if_exists(self):
        from graphglot.ast.cypher import DropConstraint

        con = self._find_one("DROP CONSTRAINT my_con IF EXISTS", DropConstraint)
        self.assertTrue(con.if_exists)

    def test_constraint_unique_round_trip(self):
        result = self._round_trip("CREATE CONSTRAINT FOR (n:Person) REQUIRE n.email IS UNIQUE")
        self.assertIn("CREATE", result)
        self.assertIn("CONSTRAINT", result)
        self.assertIn("REQUIRE", result)
        self.assertIn("UNIQUE", result)

    def test_constraint_not_null_round_trip(self):
        result = self._round_trip("CREATE CONSTRAINT FOR (n:Person) REQUIRE n.name IS NOT NULL")
        self.assertIn("CONSTRAINT", result)
        self.assertIn("NOT", result)
        self.assertIn("NULL", result)

    def test_constraint_node_key_round_trip(self):
        result = self._round_trip(
            "CREATE CONSTRAINT FOR (n:Person) REQUIRE (n.first, n.last) IS NODE KEY"
        )
        self.assertIn("CONSTRAINT", result)
        self.assertIn("NODE", result)
        self.assertIn("KEY", result)


# =============================================================================
# Cypher utility functions tests
# =============================================================================


class TestCypherUtilityFunctions(unittest.TestCase):
    """Test ROUND, SUBSTRING, LABELS parsing and generation."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        return self.neo4j.parse(query)

    def _round_trip(self, query):
        results = self.neo4j.parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return self.neo4j.generate(results[0])

    # --- ROUND ---

    def test_round_basic(self):
        from graphglot.ast.functions import Round

        results = self._parse("RETURN ROUND(3.7) AS result")
        rounds = list(results[0].find_all(Round))
        self.assertEqual(len(rounds), 1)

    def test_round_round_trip(self):
        result = self._round_trip("RETURN ROUND(3.7) AS result")
        self.assertIn("ROUND", result)
        self.assertIn("3.7", result)

    # --- SUBSTRING ---

    def test_substring_with_length(self):
        from graphglot.ast.functions import Substring

        results = self._parse("RETURN SUBSTRING('hello', 1, 3) AS result")
        subs = list(results[0].find_all(Substring))
        self.assertEqual(len(subs), 1)
        self.assertEqual(len(subs[0].arguments), 3)

    def test_substring_without_length(self):
        from graphglot.ast.functions import Substring

        results = self._parse("RETURN SUBSTRING('hello', 1) AS result")
        subs = list(results[0].find_all(Substring))
        self.assertEqual(len(subs), 1)
        self.assertEqual(len(subs[0].arguments), 2)

    def test_substring_round_trip_with_length(self):
        result = self._round_trip("RETURN SUBSTRING('hello', 1, 3) AS result")
        self.assertIn("SUBSTRING", result)
        self.assertIn("'hello'", result)

    def test_substring_round_trip_without_length(self):
        result = self._round_trip("RETURN SUBSTRING('hello', 1) AS result")
        self.assertIn("SUBSTRING", result)

    # --- LABELS ---

    def test_labels_basic(self):
        from graphglot.ast.functions import Labels

        results = self._parse("MATCH (n) RETURN LABELS(n) AS l")
        labels = list(results[0].find_all(Labels))
        self.assertEqual(len(labels), 1)

    def test_labels_round_trip(self):
        result = self._round_trip("MATCH (n) RETURN LABELS(n) AS l")
        self.assertIn("LABELS", result)

    # --- Temporal function gating ---

    def test_temporal_current_date_unsupported_neo4j(self):
        """Neo4j should reject CURRENT_DATE via GG:TF01 feature gate."""
        with self.assertRaises(FeatureError):
            self.neo4j.parse("RETURN CURRENT_DATE AS result")

    def test_temporal_current_timestamp_unsupported_neo4j(self):
        """Neo4j should reject CURRENT_TIMESTAMP via GG:TF01 feature gate."""
        with self.assertRaises(FeatureError):
            self.neo4j.parse("RETURN CURRENT_TIMESTAMP AS result")


# =============================================================================
# CREATE clause tests
# =============================================================================


class TestCypherCreate(unittest.TestCase):
    """Test Cypher CREATE clause parsing, generation, and round-trip."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        results = self.neo4j.parse(query)
        self.assertEqual(len(results), 1)
        return results[0]

    def _round_trip(self, query):
        return self.neo4j.generate(self._parse(query))

    def test_create_simple_node(self):
        """CREATE (n:Person) parses and has a CreateClause."""
        tree = self._parse("CREATE (n:Person)")
        creates = list(tree.find_all(ast.CreateClause))
        self.assertEqual(len(creates), 1)

    def test_create_node_with_properties(self):
        """CREATE (n:Person {name: 'Alice'}) includes properties."""
        tree = self._parse("CREATE (n:Person {name: 'Alice'})")
        creates = list(tree.find_all(ast.CreateClause))
        self.assertEqual(len(creates), 1)

    def test_create_relationship(self):
        """CREATE (a)-[r:KNOWS]->(b) parses edge pattern."""
        tree = self._parse("CREATE (a)-[r:KNOWS]->(b)")
        creates = list(tree.find_all(ast.CreateClause))
        self.assertEqual(len(creates), 1)

    def test_match_create(self):
        """MATCH (a:Person) CREATE (a)-[:KNOWS]->(b:Person)."""
        tree = self._parse("MATCH (a:Person) CREATE (a)-[:KNOWS]->(b:Person)")
        matches = list(tree.find_all(ast.MatchStatement))
        creates = list(tree.find_all(ast.CreateClause))
        self.assertGreaterEqual(len(matches), 1)
        self.assertGreaterEqual(len(creates), 1)

    def test_create_return(self):
        """CREATE (n:Person) RETURN n."""
        tree = self._parse("CREATE (n:Person {name: 'Alice'}) RETURN n")
        creates = list(tree.find_all(ast.CreateClause))
        self.assertGreaterEqual(len(creates), 1)

    def test_match_create_return(self):
        """MATCH (a) CREATE (a)-[r:KNOWS]->(b:Person) RETURN r."""
        tree = self._parse("MATCH (a:Person) CREATE (a)-[r:KNOWS]->(b:Person) RETURN r")
        matches = list(tree.find_all(ast.MatchStatement))
        creates = list(tree.find_all(ast.CreateClause))
        self.assertGreaterEqual(len(matches), 1)
        self.assertGreaterEqual(len(creates), 1)

    def test_create_round_trip(self):
        """Round-trip preserves CREATE keyword."""
        result = self._round_trip("CREATE (n:Person {name: 'Alice'})")
        self.assertIn("CREATE", result)
        self.assertIn("Person", result)
        self.assertNotIn("INSERT", result)

    def test_create_relationship_round_trip(self):
        result = self._round_trip("CREATE (a)-[r:KNOWS]->(b)")
        self.assertIn("CREATE", result)
        self.assertIn("KNOWS", result)

    def test_match_create_no_next(self):
        """Round-trip should not insert NEXT between MATCH and CREATE."""
        result = self._round_trip("MATCH (a:Person) CREATE (a)-[:KNOWS]->(b:Person)")
        self.assertNotIn("NEXT", result)
        self.assertIn("MATCH", result)
        self.assertIn("CREATE", result)

    def test_create_feature_gating(self):
        """CreateClause requires CY:CL04 feature."""
        feature_ids = set()
        tree = self._parse("CREATE (n:Person)")
        for node in tree.find_all(ast.CreateClause):
            feature_ids.update(f.id for f in node.get_required_features())
        self.assertIn("CY:CL04", feature_ids)


# =============================================================================
# Cypher temporal function tests
# =============================================================================


class TestCypherTemporalFunctions(unittest.TestCase):
    """Test Cypher temporal function parsing, generation, and round-trip."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        return self.neo4j.parse(query)

    def _round_trip(self, query):
        results = self.neo4j.parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return self.neo4j.generate(results[0])

    # --- String constructor parsing ---

    def test_parse_date_string(self):
        """date('2024-01-15') — already works via base GQL parser."""
        results = self._parse("RETURN date('2024-01-15') AS d")
        self.assertEqual(len(results), 1)
        dates = list(results[0].find_all(ast.DateFunction))
        self.assertEqual(len(dates), 1)

    def test_parse_time_string(self):
        """time('10:30:00') — requires Cypher parser override (TIME token not consumed)."""
        results = self._parse("RETURN time('10:30:00') AS t")
        self.assertEqual(len(results), 1)
        times = list(results[0].find_all(ast.TimeFunction))
        self.assertEqual(len(times), 1)

    def test_parse_datetime_string(self):
        """datetime('2024-01-15T10:30:00') — requires Cypher parser override."""
        results = self._parse("RETURN datetime('2024-01-15T10:30:00') AS dt")
        self.assertEqual(len(results), 1)
        dts = list(results[0].find_all(ast.DatetimeFunction))
        self.assertEqual(len(dts), 1)

    def test_parse_localdatetime_string(self):
        """localdatetime('2024-01-15T10:30:00') — requires lexer + parser."""
        results = self._parse("RETURN localdatetime('2024-01-15T10:30:00') AS ldt")
        self.assertEqual(len(results), 1)
        ldts = list(results[0].find_all(ast.LocaldatetimeFunction))
        self.assertEqual(len(ldts), 1)

    def test_parse_localtime_string(self):
        """localtime('10:30:00') — requires lexer + parser."""
        results = self._parse("RETURN localtime('10:30:00') AS lt")
        self.assertEqual(len(results), 1)
        lts = list(results[0].find_all(ast.LocaltimeFunction))
        self.assertEqual(len(lts), 1)

    def test_parse_duration_string(self):
        """duration('P1Y2M3D') — already works via base GQL parser."""
        results = self._parse("RETURN duration('P1Y2M3D') AS dur")
        self.assertEqual(len(results), 1)
        durs = list(results[0].find_all(ast.DurationFunction))
        self.assertEqual(len(durs), 1)

    # --- No-arg constructors (Cypher: current value) ---

    def test_parse_date_no_arg(self):
        """date() — Cypher for current date."""
        results = self._parse("RETURN date() AS d")
        self.assertEqual(len(results), 1)
        dates = list(results[0].find_all(ast.DateFunction))
        self.assertEqual(len(dates), 1)

    def test_parse_time_no_arg(self):
        """time() — Cypher for current time."""
        results = self._parse("RETURN time() AS t")
        self.assertEqual(len(results), 1)
        times = list(results[0].find_all(ast.TimeFunction))
        self.assertEqual(len(times), 1)

    def test_parse_datetime_no_arg(self):
        """datetime() — Cypher for current datetime."""
        results = self._parse("RETURN datetime() AS dt")
        self.assertEqual(len(results), 1)
        dts = list(results[0].find_all(ast.DatetimeFunction))
        self.assertEqual(len(dts), 1)

    def test_parse_localdatetime_no_arg(self):
        """localdatetime() — Cypher for current local datetime."""
        results = self._parse("RETURN localdatetime() AS ldt")
        self.assertEqual(len(results), 1)
        ldts = list(results[0].find_all(ast.LocaldatetimeFunction))
        self.assertEqual(len(ldts), 1)

    def test_parse_localtime_no_arg(self):
        """localtime() — Cypher for current local time."""
        results = self._parse("RETURN localtime() AS lt")
        self.assertEqual(len(results), 1)
        lts = list(results[0].find_all(ast.LocaltimeFunction))
        self.assertEqual(len(lts), 1)

    # --- Static method calls ---

    def test_parse_date_truncate(self):
        """date.truncate('year', date('2024-06-15'))."""
        from graphglot.ast.cypher import CypherTemporalMethod

        results = self._parse("RETURN date.truncate('year', date('2024-06-15')) AS d")
        self.assertEqual(len(results), 1)
        methods = list(results[0].find_all(CypherTemporalMethod))
        self.assertEqual(len(methods), 1)
        self.assertEqual(methods[0].base_type, TemporalBaseType.DATE)
        self.assertEqual(methods[0].method, CypherTemporalMethod.Method.TRUNCATE)

    def test_parse_duration_between(self):
        """duration.between(date('2024-01-01'), date('2024-06-15'))."""
        from graphglot.ast.cypher import CypherTemporalMethod

        results = self._parse(
            "RETURN duration.between(date('2024-01-01'), date('2024-06-15')) AS d"
        )
        self.assertEqual(len(results), 1)
        methods = list(results[0].find_all(CypherTemporalMethod))
        self.assertEqual(len(methods), 1)
        self.assertEqual(methods[0].base_type, TemporalBaseType.DURATION)
        self.assertEqual(methods[0].method, CypherTemporalMethod.Method.BETWEEN)

    def test_parse_datetime_realtime(self):
        """datetime.realtime()."""
        from graphglot.ast.cypher import CypherTemporalMethod

        results = self._parse("RETURN datetime.realtime() AS dt")
        self.assertEqual(len(results), 1)
        methods = list(results[0].find_all(CypherTemporalMethod))
        self.assertEqual(len(methods), 1)
        self.assertEqual(methods[0].base_type, TemporalBaseType.DATETIME)
        self.assertEqual(methods[0].method, CypherTemporalMethod.Method.REALTIME)

    def test_parse_datetime_transaction(self):
        """datetime.transaction()."""
        from graphglot.ast.cypher import CypherTemporalMethod

        results = self._parse("RETURN datetime.transaction() AS dt")
        self.assertEqual(len(results), 1)
        methods = list(results[0].find_all(CypherTemporalMethod))
        self.assertEqual(len(methods), 1)
        self.assertEqual(methods[0].method, CypherTemporalMethod.Method.TRANSACTION)

    def test_parse_datetime_statement(self):
        """datetime.statement()."""
        from graphglot.ast.cypher import CypherTemporalMethod

        results = self._parse("RETURN datetime.statement() AS dt")
        self.assertEqual(len(results), 1)
        methods = list(results[0].find_all(CypherTemporalMethod))
        self.assertEqual(len(methods), 1)
        self.assertEqual(methods[0].method, CypherTemporalMethod.Method.STATEMENT)

    def test_parse_duration_inmonths(self):
        """duration.inMonths(d1, d2)."""
        from graphglot.ast.cypher import CypherTemporalMethod

        results = self._parse(
            "RETURN duration.inMonths(date('2024-01-01'), date('2024-06-15')) AS m"
        )
        self.assertEqual(len(results), 1)
        methods = list(results[0].find_all(CypherTemporalMethod))
        self.assertEqual(len(methods), 1)
        self.assertEqual(methods[0].base_type, TemporalBaseType.DURATION)
        self.assertEqual(methods[0].method, CypherTemporalMethod.Method.INMONTHS)
        self.assertEqual(len(methods[0].arguments), 2)

    def test_parse_duration_indays(self):
        """duration.inDays(d1, d2)."""
        from graphglot.ast.cypher import CypherTemporalMethod

        results = self._parse("RETURN duration.inDays(date('2024-01-01'), date('2024-06-15')) AS d")
        self.assertEqual(len(results), 1)
        methods = list(results[0].find_all(CypherTemporalMethod))
        self.assertEqual(len(methods), 1)
        self.assertEqual(methods[0].base_type, TemporalBaseType.DURATION)
        self.assertEqual(methods[0].method, CypherTemporalMethod.Method.INDAYS)
        self.assertEqual(len(methods[0].arguments), 2)

    def test_parse_duration_inseconds(self):
        """duration.inSeconds(d1, d2)."""
        from graphglot.ast.cypher import CypherTemporalMethod

        results = self._parse("RETURN duration.inSeconds(time('10:00:00'), time('12:30:00')) AS s")
        self.assertEqual(len(results), 1)
        methods = list(results[0].find_all(CypherTemporalMethod))
        self.assertEqual(len(methods), 1)
        self.assertEqual(methods[0].base_type, TemporalBaseType.DURATION)
        self.assertEqual(methods[0].method, CypherTemporalMethod.Method.INSECONDS)
        self.assertEqual(len(methods[0].arguments), 2)

    # --- Round-trip tests (Cypher generates lowercase) ---

    def test_round_trip_date_string(self):
        result = self._round_trip("RETURN date('2024-01-15') AS d")
        self.assertIn("date(", result)
        self.assertIn("2024-01-15", result)

    def test_round_trip_time_string(self):
        result = self._round_trip("RETURN time('10:30:00') AS t")
        self.assertIn("time(", result)
        self.assertIn("10:30:00", result)

    def test_round_trip_datetime_string(self):
        result = self._round_trip("RETURN datetime('2024-01-15T10:30:00') AS dt")
        self.assertIn("datetime(", result)

    def test_round_trip_localdatetime_string(self):
        result = self._round_trip("RETURN localdatetime('2024-01-15T10:30:00') AS ldt")
        self.assertIn("localdatetime(", result)

    def test_round_trip_localtime_string(self):
        result = self._round_trip("RETURN localtime('10:30:00') AS lt")
        self.assertIn("localtime(", result)

    def test_round_trip_duration_string(self):
        result = self._round_trip("RETURN duration('P1Y2M3D') AS dur")
        self.assertIn("duration(", result)

    def test_round_trip_date_no_arg(self):
        result = self._round_trip("RETURN date() AS d")
        self.assertIn("date()", result)

    def test_round_trip_datetime_no_arg(self):
        result = self._round_trip("RETURN datetime() AS dt")
        self.assertIn("datetime()", result)

    def test_round_trip_date_truncate(self):
        result = self._round_trip("RETURN date.truncate('year', date('2024-06-15')) AS d")
        self.assertIn("date.truncate(", result)

    def test_round_trip_duration_between(self):
        result = self._round_trip(
            "RETURN duration.between(date('2024-01-01'), date('2024-06-15')) AS d"
        )
        self.assertIn("duration.between(", result)

    def test_round_trip_datetime_realtime(self):
        result = self._round_trip("RETURN datetime.realtime() AS dt")
        self.assertIn("datetime.realtime()", result)

    def test_round_trip_duration_inmonths(self):
        result = self._round_trip(
            "RETURN duration.inMonths(date('2024-01-01'), date('2024-06-15')) AS m"
        )
        self.assertIn("duration.inMonths(", result)

    def test_round_trip_duration_indays(self):
        result = self._round_trip(
            "RETURN duration.inDays(date('2024-01-01'), date('2024-06-15')) AS d"
        )
        self.assertIn("duration.inDays(", result)

    def test_round_trip_duration_inseconds(self):
        result = self._round_trip(
            "RETURN duration.inSeconds(time('10:00:00'), time('12:30:00')) AS s"
        )
        self.assertIn("duration.inSeconds(", result)

    # --- Map constructors (temporal keywords as field names) ---

    def test_date_map_constructor(self):
        """date({year: 2024, month: 1, day: 15}) — keywords as record field names."""
        results = self._parse("RETURN date({year: 2024, month: 1, day: 15}) AS d")
        self.assertEqual(len(results), 1)
        dates = list(results[0].find_all(ast.DateFunction))
        self.assertEqual(len(dates), 1)

    def test_time_map_constructor(self):
        """time({hour: 10, minute: 30, second: 0}) — keywords as record field names."""
        results = self._parse("RETURN time({hour: 10, minute: 30, second: 0}) AS t")
        self.assertEqual(len(results), 1)
        times = list(results[0].find_all(ast.TimeFunction))
        self.assertEqual(len(times), 1)

    def test_datetime_map_constructor(self):
        """datetime({year: 2024, month: 1, day: 15, hour: 10, minute: 30}) — mixed fields."""
        results = self._parse(
            "RETURN datetime({year: 2024, month: 1, day: 15, hour: 10, minute: 30}) AS dt"
        )
        self.assertEqual(len(results), 1)
        dts = list(results[0].find_all(ast.DatetimeFunction))
        self.assertEqual(len(dts), 1)

    def test_localdatetime_map_constructor(self):
        """localdatetime({year: 2024, month: 1, day: 15, hour: 10})."""
        results = self._parse(
            "RETURN localdatetime({year: 2024, month: 1, day: 15, hour: 10}) AS ldt"
        )
        self.assertEqual(len(results), 1)
        ldts = list(results[0].find_all(ast.LocaldatetimeFunction))
        self.assertEqual(len(ldts), 1)

    def test_localtime_map_constructor(self):
        """localtime({hour: 12, minute: 0, second: 0})."""
        results = self._parse("RETURN localtime({hour: 12, minute: 0, second: 0}) AS lt")
        self.assertEqual(len(results), 1)
        lts = list(results[0].find_all(ast.LocaltimeFunction))
        self.assertEqual(len(lts), 1)

    def test_duration_map_constructor(self):
        """duration({years: 1, months: 2, days: 3}) — plural keys, should already work."""
        results = self._parse("RETURN duration({years: 1, months: 2, days: 3}) AS dur")
        self.assertEqual(len(results), 1)
        durs = list(results[0].find_all(ast.DurationFunction))
        self.assertEqual(len(durs), 1)

    def test_temporal_property_access(self):
        """Property access with temporal keywords: d.year, d.month, d.day."""
        results = self._parse(
            "WITH date('2024-06-15') AS d RETURN d.year AS y, d.month AS m, d.day AS dy"
        )
        self.assertEqual(len(results), 1)

    def test_round_trip_temporal_map(self):
        """Parse → generate → re-parse for temporal map constructors."""
        queries = [
            "RETURN date({year: 2024, month: 1, day: 15}) AS d",
            "RETURN time({hour: 10, minute: 30, second: 0}) AS t",
            "RETURN datetime({year: 2024, month: 6, day: 15, hour: 12}) AS dt",
        ]
        for query in queries:
            with self.subTest(query=query):
                generated = self._round_trip(query)
                # Re-parse the generated output to verify it's valid
                results2 = self._parse(generated)
                self.assertEqual(len(results2), 1, f"Round-trip failed for: {query}")

    # --- Feature gating ---

    def test_temporal_method_requires_feature(self):
        """CypherTemporalMethod should require CY:TF01 feature."""
        from graphglot.ast.cypher import CypherTemporalMethod

        results = self._parse("RETURN date.truncate('year', date('2024-06-15')) AS d")
        methods = list(results[0].find_all(CypherTemporalMethod))
        self.assertEqual(len(methods), 1)
        feature_ids = {f.id for f in methods[0].get_required_features()}
        self.assertIn("CY:TF01", feature_ids)


# =============================================================================
# Cypher map literals tests (Plan 035)
# =============================================================================


class TestCypherMapLiterals(unittest.TestCase):
    """Test map literal extensions: nested maps, keyword field names, subscript, keys()."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        return self.neo4j.parse(query)

    def _round_trip(self, query):
        results = self.neo4j.parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return self.neo4j.generate(results[0])

    # --- GV48: Nested maps ---

    def test_nested_map_simple(self):
        """RETURN {a: {b: 1}} — nested record constructor requires GV48."""
        results = self._parse("RETURN {a: {b: 1}} AS m")
        self.assertEqual(len(results), 1)
        rcs = list(results[0].find_all(ast.RecordConstructor))
        self.assertGreaterEqual(len(rcs), 2)  # outer + inner

    def test_nested_map_round_trip(self):
        """Round-trip for nested maps."""
        result = self._round_trip("RETURN {a: {b: 1}} AS m")
        # Re-parse to verify
        results2 = self._parse(result)
        self.assertEqual(len(results2), 1)

    def test_deeply_nested_map(self):
        """RETURN {a: {b: {c: 1}}} — three-level nesting."""
        results = self._parse("RETURN {a: {b: {c: 1}}} AS m")
        self.assertEqual(len(results), 1)
        rcs = list(results[0].find_all(ast.RecordConstructor))
        self.assertGreaterEqual(len(rcs), 3)  # outer + middle + inner

    # --- Keyword field names ---

    def test_keyword_field_existing(self):
        """RETURN {existing: 42} — 'existing' is a reserved word in GQL."""
        results = self._parse("RETURN {existing: 42} AS m")
        self.assertEqual(len(results), 1)
        fields = list(results[0].find_all(ast.Field))
        self.assertEqual(len(fields), 1)
        self.assertEqual(fields[0].field_name.name, "existing")

    def test_keyword_field_null(self):
        """RETURN {null: 'x'} — 'null' is a reserved word."""
        results = self._parse("RETURN {null: 'x'} AS m")
        self.assertEqual(len(results), 1)
        fields = list(results[0].find_all(ast.Field))
        self.assertEqual(len(fields), 1)

    def test_keyword_field_type(self):
        """RETURN {type: 'Person'} — 'type' is a non-reserved word."""
        results = self._parse("RETURN {type: 'Person'} AS m")
        self.assertEqual(len(results), 1)

    def test_keyword_field_mixed(self):
        """RETURN {name: 'Alice', existing: true} — mix of normal + keyword fields."""
        results = self._parse("RETURN {name: 'Alice', existing: true} AS m")
        self.assertEqual(len(results), 1)
        fields = list(results[0].find_all(ast.Field))
        self.assertEqual(len(fields), 2)

    def test_keyword_field_round_trip(self):
        result = self._round_trip("RETURN {existing: 42} AS m")
        self.assertIn("existing", result)
        self.assertIn("42", result)

    # --- Subscript expression expr[idx] ---

    def test_subscript_map_string_key(self):
        """RETURN {a: 1, b: 2}['a'] — map subscript with string key."""
        from graphglot.ast.cypher import CypherSubscriptExpression

        results = self._parse("RETURN {a: 1, b: 2}['a'] AS v")
        self.assertEqual(len(results), 1)
        subs = list(results[0].find_all(CypherSubscriptExpression))
        self.assertEqual(len(subs), 1)

    def test_subscript_list_integer_index(self):
        """RETURN [1, 2, 3][0] — list subscript with integer index."""
        from graphglot.ast.cypher import CypherSubscriptExpression

        results = self._parse("RETURN [1, 2, 3][0] AS v")
        self.assertEqual(len(results), 1)
        subs = list(results[0].find_all(CypherSubscriptExpression))
        self.assertEqual(len(subs), 1)

    def test_subscript_variable(self):
        """RETURN m['key'] — subscript on a variable."""
        from graphglot.ast.cypher import CypherSubscriptExpression

        results = self._parse("WITH {a: 1} AS m RETURN m['a'] AS v")
        self.assertEqual(len(results), 1)
        subs = list(results[0].find_all(CypherSubscriptExpression))
        self.assertEqual(len(subs), 1)

    def test_subscript_chained(self):
        """RETURN {a: {b: 1}}['a']['b'] — chained subscript."""
        from graphglot.ast.cypher import CypherSubscriptExpression

        results = self._parse("RETURN {a: {b: 1}}['a']['b'] AS v")
        self.assertEqual(len(results), 1)
        subs = list(results[0].find_all(CypherSubscriptExpression))
        self.assertGreaterEqual(len(subs), 2)

    def test_subscript_round_trip(self):
        """Round-trip for subscript expression."""

        result = self._round_trip("WITH {a: 1} AS m RETURN m['a'] AS v")
        # Should contain bracket notation
        self.assertIn("[", result)
        self.assertIn("]", result)

    def test_subscript_feature_gating(self):
        """CypherSubscriptExpression requires CY:OP04."""
        from graphglot.ast.cypher import CypherSubscriptExpression

        sub = CypherSubscriptExpression(
            base=_ve(ast.Identifier(name="m")),
            index=_ve(ast.CharacterStringLiteral(value="a")),
        )
        feature_ids = {f.id for f in sub.get_required_features()}
        self.assertIn("CY:OP04", feature_ids)

    # --- keys() function ---

    def test_keys_map_literal(self):
        """RETURN keys({a: 1, b: 2}) — keys() on map literal."""
        from graphglot.ast.functions import Keys

        results = self._parse("RETURN keys({a: 1, b: 2}) AS k")
        self.assertEqual(len(results), 1)
        keys_fns = list(results[0].find_all(Keys))
        self.assertEqual(len(keys_fns), 1)

    def test_keys_variable(self):
        """RETURN keys(n) — keys() on a node variable."""
        from graphglot.ast.functions import Keys

        results = self._parse("MATCH (n) RETURN keys(n) AS k")
        self.assertEqual(len(results), 1)
        keys_fns = list(results[0].find_all(Keys))
        self.assertEqual(len(keys_fns), 1)

    def test_keys_round_trip(self):
        """Round-trip for keys() function."""
        result = self._round_trip("MATCH (n) RETURN keys(n) AS k")
        self.assertIn("keys(", result.lower())


# =============================================================================
# Cypher graph function tests (size, nodes, relationships)
# =============================================================================


class TestCypherGraphFunctions(unittest.TestCase):
    """Test size(), nodes(), relationships() parsing and generation."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        return self.neo4j.parse(query)

    def _round_trip(self, query):
        results = self.neo4j.parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return self.neo4j.generate(results[0])

    # --- size() ---

    def test_size_list_literal(self):
        """size([1, 2, 3]) — list cardinality."""
        from graphglot.ast.functions import Size

        results = self._parse("RETURN size([1, 2, 3]) AS n")
        self.assertEqual(len(results), 1)
        fns = list(results[0].find_all(Size))
        self.assertEqual(len(fns), 1)

    def test_size_string(self):
        """size('hello') — string length."""
        from graphglot.ast.functions import Size

        results = self._parse("RETURN size('hello') AS n")
        fns = list(results[0].find_all(Size))
        self.assertEqual(len(fns), 1)

    def test_size_property(self):
        """size(n.name) — property string length."""
        from graphglot.ast.functions import Size

        results = self._parse("MATCH (n) RETURN size(n.name) AS n")
        fns = list(results[0].find_all(Size))
        self.assertEqual(len(fns), 1)

    def test_size_round_trip(self):
        result = self._round_trip("RETURN size([1, 2, 3]) AS n")
        self.assertIn("size(", result.lower())

    # --- nodes() ---

    def test_nodes_path(self):
        """nodes(p) — extract nodes from path variable."""
        from graphglot.ast.functions import Nodes

        results = self._parse("MATCH p = (a)-[r]->(b) RETURN nodes(p) AS ns")
        self.assertEqual(len(results), 1)
        fns = list(results[0].find_all(Nodes))
        self.assertEqual(len(fns), 1)

    def test_nodes_round_trip(self):
        result = self._round_trip("MATCH p = (a)-[r]->(b) RETURN nodes(p) AS ns")
        self.assertIn("nodes(", result.lower())

    # --- relationships() ---

    def test_relationships_path(self):
        """relationships(p) — extract relationships from path variable."""
        from graphglot.ast.functions import Relationships

        results = self._parse("MATCH p = (a)-[r]->(b) RETURN relationships(p) AS rels")
        self.assertEqual(len(results), 1)
        fns = list(results[0].find_all(Relationships))
        self.assertEqual(len(fns), 1)

    def test_relationships_round_trip(self):
        result = self._round_trip("MATCH p = (a)-[r]->(b) RETURN relationships(p) AS rels")
        self.assertIn("relationships(", result.lower())

    # --- Combined usage ---

    def test_combined_graph_functions(self):
        """Combined: nodes(p), relationships(p), size(nodes(p))."""
        results = self._parse(
            "MATCH p = (a)-[r]->(b) "
            "RETURN nodes(p) AS ns, relationships(p) AS rs, "
            "size(nodes(p)) AS cnt"
        )
        self.assertEqual(len(results), 1)

    def test_size_in_quantifier(self):
        """size() inside a quantifier predicate — TCK pattern."""
        results = self._parse("RETURN none(x IN [] WHERE size(x) = 3) AS result")
        self.assertEqual(len(results), 1)


# =============================================================================
# Reserved keywords as identifiers (Plan 036)
# =============================================================================


class TestReservedKeywordsAsIdentifiers(unittest.TestCase):
    """GQL reserved keywords usable as property names, aliases, and variables in Cypher."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        return self.neo4j.parse(query)

    def _round_trip(self, query):
        results = self.neo4j.parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return self.neo4j.generate(results[0])

    # --- Property access with reserved keywords ---

    def test_property_access_bool(self):
        results = self._parse("MATCH (a) RETURN a.bool")
        self.assertEqual(len(results), 1)

    def test_property_access_list(self):
        results = self._parse("MATCH (a) RETURN a.list")
        self.assertEqual(len(results), 1)

    def test_property_access_date(self):
        results = self._parse("MATCH (a) RETURN a.date")
        self.assertEqual(len(results), 1)

    def test_property_access_time(self):
        results = self._parse("MATCH (a) RETURN a.time")
        self.assertEqual(len(results), 1)

    def test_property_access_datetime(self):
        results = self._parse("MATCH (a) RETURN a.datetime")
        self.assertEqual(len(results), 1)

    def test_property_access_duration(self):
        results = self._parse("MATCH (a) RETURN a.duration")
        self.assertEqual(len(results), 1)

    def test_property_access_value(self):
        results = self._parse("MATCH (a) RETURN a.value")
        self.assertEqual(len(results), 1)

    def test_property_access_float(self):
        results = self._parse("MATCH (a) RETURN a.float")
        self.assertEqual(len(results), 1)

    def test_property_access_int(self):
        results = self._parse("MATCH (a) RETURN a.int")
        self.assertEqual(len(results), 1)

    def test_property_access_real(self):
        results = self._parse("MATCH (a) RETURN a.real")
        self.assertEqual(len(results), 1)

    def test_property_access_timestamp(self):
        results = self._parse("MATCH (a) RETURN a.timestamp")
        self.assertEqual(len(results), 1)

    # --- Aliases with reserved keywords ---

    def test_alias_bool(self):
        results = self._parse("RETURN 1 AS bool")
        self.assertEqual(len(results), 1)

    def test_alias_sum(self):
        results = self._parse("RETURN 1 AS sum")
        self.assertEqual(len(results), 1)

    def test_alias_count(self):
        results = self._parse("RETURN 1 AS count")
        self.assertEqual(len(results), 1)

    def test_alias_avg(self):
        results = self._parse("RETURN 1 AS avg")
        self.assertEqual(len(results), 1)

    def test_alias_min(self):
        results = self._parse("RETURN 1 AS min")
        self.assertEqual(len(results), 1)

    def test_alias_max(self):
        results = self._parse("RETURN 1 AS max")
        self.assertEqual(len(results), 1)

    def test_alias_date(self):
        results = self._parse("RETURN 1 AS date")
        self.assertEqual(len(results), 1)

    def test_alias_value(self):
        results = self._parse("RETURN 1 AS value")
        self.assertEqual(len(results), 1)

    def test_alias_list(self):
        results = self._parse("RETURN 1 AS list")
        self.assertEqual(len(results), 1)

    def test_alias_float(self):
        results = self._parse("RETURN 1 AS float")
        self.assertEqual(len(results), 1)

    def test_alias_int(self):
        results = self._parse("RETURN 1 AS int")
        self.assertEqual(len(results), 1)

    # --- WITH + ORDER BY with reserved keyword properties ---

    def test_with_order_by_bool_property(self):
        results = self._parse("MATCH (a) WITH a ORDER BY a.bool RETURN a")
        self.assertEqual(len(results), 1)

    def test_with_order_by_date_property(self):
        results = self._parse("MATCH (a) WITH a ORDER BY a.date RETURN a")
        self.assertEqual(len(results), 1)

    def test_with_order_by_list_property(self):
        results = self._parse("MATCH (a) WITH a ORDER BY a.list RETURN a")
        self.assertEqual(len(results), 1)

    def test_with_alias_sum(self):
        results = self._parse("MATCH (a) WITH a.num + a.num2 AS sum RETURN sum")
        self.assertEqual(len(results), 1)

    # --- Verify temporal/aggregate functions still work ---

    def test_date_function_still_works(self):
        results = self._parse("RETURN date('2024-01-15') AS d")
        self.assertEqual(len(results), 1)

    def test_datetime_function_still_works(self):
        results = self._parse("RETURN datetime('2024-01-15T10:30:00') AS dt")
        self.assertEqual(len(results), 1)

    def test_time_function_still_works(self):
        results = self._parse("RETURN time('10:30:00') AS t")
        self.assertEqual(len(results), 1)

    def test_duration_function_still_works(self):
        results = self._parse("RETURN duration('P1Y2M3D') AS d")
        self.assertEqual(len(results), 1)

    def test_count_function_still_works(self):
        results = self._parse("MATCH (n) RETURN count(*) AS cnt")
        self.assertEqual(len(results), 1)

    def test_sum_function_still_works(self):
        results = self._parse("MATCH (n) RETURN sum(n.x) AS total")
        self.assertEqual(len(results), 1)

    def test_avg_function_still_works(self):
        results = self._parse("MATCH (n) RETURN avg(n.x) AS average")
        self.assertEqual(len(results), 1)

    def test_min_max_functions_still_work(self):
        results = self._parse("MATCH (n) RETURN min(n.x) AS lo, max(n.x) AS hi")
        self.assertEqual(len(results), 1)

    # --- Round-trip tests ---

    def test_round_trip_property_bool(self):
        result = self._round_trip("MATCH (a) RETURN a.bool")
        self.assertIn("bool", result.lower())

    def test_round_trip_alias_sum(self):
        result = self._round_trip("RETURN 1 AS sum")
        self.assertIn("sum", result.lower())

    def test_round_trip_with_order_by_date(self):
        result = self._round_trip("MATCH (a) WITH a ORDER BY a.date RETURN a")
        self.assertIn("date", result.lower())


# =============================================================================
# Modulus operator tests
# =============================================================================


class TestModulusOperator(unittest.TestCase):
    """Cypher ``%`` infix modulus operator using standard ModulusExpression."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _round_trip(self, query):
        results = self.neo4j.parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return self.neo4j.generate(results[0])

    def test_simple_modulus(self):
        result = self._round_trip("RETURN 10 % 3")
        self.assertIn("%", result)

    def test_modulus_in_where(self):
        result = self._round_trip("MATCH (n) WHERE n.age % 2 = 0 RETURN n")
        self.assertIn("%", result)

    def test_modulus_with_parens(self):
        result = self._round_trip("RETURN (10 + 3) % 4")
        self.assertIn("%", result)

    def test_modulus_chained(self):
        result = self._round_trip("RETURN 100 % 7 % 3")
        self.assertIn("%", result)

    def test_modulus_with_multiply(self):
        """Precedence: % and * are same level (term-level)."""
        result = self._round_trip("RETURN 10 % 3 * 2")
        self.assertIn("%", result)
        self.assertIn("*", result)

    def test_modulus_with_addition(self):
        """Precedence: % binds tighter than +."""
        result = self._round_trip("RETURN 10 % 3 + 1")
        self.assertIn("%", result)
        self.assertIn("+", result)

    def test_modulus_ast_type(self):
        """Parser produces standard ModulusExpression, not a Cypher-specific node."""
        results = self.neo4j.parse("RETURN 10 % 3")
        program = results[0]
        # Walk the AST to find ModulusExpression
        found = False

        def walk(node):
            nonlocal found
            if isinstance(node, ast.ModulusExpression):
                found = True
                return
            if isinstance(node, ast.Expression):
                for child in node.ast_fields:
                    val = getattr(node, child, None)
                    if val is not None:
                        if isinstance(val, list):
                            for item in val:
                                walk(item)
                        else:
                            walk(val)

        walk(program)
        self.assertTrue(found, "Expected ModulusExpression in AST")


# =============================================================================
# List concatenation tests
# =============================================================================


class TestListConcatenation(unittest.TestCase):
    """Cypher list concatenation via ``+`` using standard ArithmeticValueExpression."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _round_trip(self, query):
        results = self.neo4j.parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return self.neo4j.generate(results[0])

    def test_list_plus_list(self):
        result = self._round_trip("RETURN [1, 2] + [3, 4]")
        self.assertIn("+", result)

    def test_list_minus(self):
        """List difference via ``-``."""
        result = self._round_trip("RETURN [1, 2, 3] - [2]")
        self.assertIn("-", result)

    def test_list_concat_in_where(self):
        result = self._round_trip("MATCH (n) WHERE size([1] + [2]) = 2 RETURN n")
        self.assertIn("+", result)

    def test_list_concat_with_variable(self):
        result = self._round_trip("MATCH (n) RETURN n.tags + ['extra']")
        self.assertIn("+", result)

    def test_list_multiply(self):
        """Arithmetic after list literal — multiply."""
        result = self._round_trip("RETURN size([1, 2, 3]) * 2")
        self.assertIn("*", result)

    def test_list_divide(self):
        """Arithmetic after list literal — divide."""
        result = self._round_trip("RETURN size([1, 2, 3]) / 2")
        self.assertIn("/", result)

    def test_size_modulus(self):
        """Modulus on a Cypher function result."""
        result = self._round_trip("RETURN size([1, 2, 3]) % 2")
        self.assertIn("%", result)


# =============================================================================
# Cypher directed arrows (-->, <--, --) tests
# =============================================================================


class TestCypherDirectedArrows(unittest.TestCase):
    """Test Cypher double-dash arrows: -->, <--, --."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _round_trip(self, query):
        results = self.neo4j.parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return self.neo4j.generate(results[0])

    def test_right_arrow(self):
        """``-->`` parses as a right-directed abbreviated edge."""
        result = self._round_trip("MATCH (a)-->(b) RETURN a, b")
        self.assertIn("-->", result)

    def test_left_arrow(self):
        """``<--`` parses as a left-directed abbreviated edge."""
        result = self._round_trip("MATCH (a)<--(b) RETURN a, b")
        self.assertIn("<--", result)

    def test_undirected(self):
        """``--`` parses as an undirected abbreviated edge."""
        result = self._round_trip("MATCH (a)--(b) RETURN a, b")
        self.assertIn("--", result)

    def test_mixed_arrows(self):
        """Mixed arrow styles in the same query."""
        result = self._round_trip("MATCH (a)-->(b)<--(c) RETURN a, b, c")
        self.assertIn("-->", result)
        self.assertIn("<--", result)

    def test_full_edge_still_works(self):
        """Single-dash full edge patterns ``-[r:KNOWS]->`` still work."""
        result = self._round_trip("MATCH (a)-[r:KNOWS]->(b) RETURN a, r, b")
        self.assertIn("KNOWS", result)
        # Full edge patterns use single-dash: -[...]->, not --[...]-->
        self.assertIn("->", result)

    def test_single_dash_arrows_generate_double(self):
        """GQL-style single-dash ``->`` input generates Cypher ``-->``."""
        result = self._round_trip("MATCH (a)->(b) RETURN a, b")
        self.assertIn("-->", result)

    def test_undirected_full_edge(self):
        """Single-dash undirected full edge ``-[r]-`` still works."""
        result = self._round_trip("MATCH (a)-[r]-(b) RETURN a, r, b")
        self.assertIn("MATCH", result)


# =============================================================================
# Hex / Octal integer literal tests (Plan 038, Feature 1)
# =============================================================================


class TestCypherHexOctalLiterals(unittest.TestCase):
    """Test that hex and octal integer literals parse under Neo4j dialect."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _round_trip(self, query):
        results = self.neo4j.parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return self.neo4j.generate(results[0])

    def test_hex_literal(self):
        """RETURN 0xFF parses as integer literal."""
        results = self.neo4j.parse("RETURN 0xFF")
        self.assertEqual(len(results), 1)

    def test_octal_literal(self):
        """RETURN 0o77 parses as integer literal."""
        results = self.neo4j.parse("RETURN 0o77")
        self.assertEqual(len(results), 1)

    def test_hex_round_trip(self):
        """Hex literal round-trips (converted to decimal)."""
        result = self._round_trip("RETURN 0xFF")
        self.assertIn("255", result)

    def test_octal_round_trip(self):
        """Octal literal round-trips (converted to decimal)."""
        result = self._round_trip("RETURN 0o77")
        self.assertIn("63", result)


# =============================================================================
# CASE expression tests (Plan 038, Feature 2)
# =============================================================================


class TestCypherCaseExpression(unittest.TestCase):
    """Test that CASE expressions parse and round-trip under Neo4j dialect."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _round_trip(self, query):
        results = self.neo4j.parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return self.neo4j.generate(results[0])

    def test_simple_case(self):
        """Simple CASE expression parses."""
        results = self.neo4j.parse("RETURN CASE 1 WHEN 1 THEN 'one' ELSE 'other' END")
        self.assertEqual(len(results), 1)

    def test_searched_case(self):
        """Searched CASE expression parses."""
        results = self.neo4j.parse(
            "MATCH (n) RETURN CASE WHEN n.age > 18 THEN 'adult' ELSE 'minor' END"
        )
        self.assertEqual(len(results), 1)

    def test_case_round_trip(self):
        """CASE expression survives round-trip."""
        result = self._round_trip("RETURN CASE 1 WHEN 1 THEN 'one' ELSE 'other' END")
        self.assertIn("CASE", result)
        self.assertIn("WHEN", result)
        self.assertIn("END", result)


# =============================================================================
# Power ^ operator tests (Plan 038, Feature 3)
# =============================================================================


class TestCypherPowerOperator(unittest.TestCase):
    """Test Cypher power operator ``^`` parsing and generation."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _round_trip(self, query):
        results = self.neo4j.parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return self.neo4j.generate(results[0])

    def test_simple_power(self):
        """RETURN 2 ^ 3 parses as PowerFunction."""
        results = self.neo4j.parse("RETURN 2 ^ 3")
        self.assertEqual(len(results), 1)
        powers = list(results[0].find_all(ast.PowerFunction))
        self.assertEqual(len(powers), 1)

    def test_power_round_trip(self):
        """Power expression round-trips with ^."""
        result = self._round_trip("RETURN 2 ^ 3")
        self.assertIn("^", result)

    def test_power_precedence_over_multiply(self):
        """RETURN 2 * 3 ^ 4 -- ^ binds tighter than *."""
        results = self.neo4j.parse("RETURN 2 * 3 ^ 4")
        self.assertEqual(len(results), 1)
        powers = list(results[0].find_all(ast.PowerFunction))
        self.assertEqual(len(powers), 1)

    def test_power_precedence_over_addition(self):
        """RETURN 1 + 2 ^ 3 -- ^ binds tighter than +."""
        results = self.neo4j.parse("RETURN 1 + 2 ^ 3")
        self.assertEqual(len(results), 1)
        powers = list(results[0].find_all(ast.PowerFunction))
        self.assertEqual(len(powers), 1)

    def test_power_in_where(self):
        """Power op works in WHERE clause."""
        results = self.neo4j.parse("MATCH (n) WHERE n.x ^ 2 > 10 RETURN n")
        self.assertEqual(len(results), 1)


# =============================================================================
# Multi-label :A:B:C tests (Plan 038, Feature 4)
# =============================================================================


class TestCypherMultiLabel(unittest.TestCase):
    """Test multi-label colon syntax ``(:A:B:C)``."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _round_trip(self, query):
        results = self.neo4j.parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return self.neo4j.generate(results[0])

    def test_two_labels(self):
        """MATCH (n:A:B) RETURN n parses both labels via LabelTerm."""
        results = self.neo4j.parse("MATCH (n:A:B) RETURN n")
        self.assertEqual(len(results), 1)
        terms = list(results[0].find_all(ast.LabelTerm))
        self.assertTrue(any(len(lt.label_factors) == 2 for lt in terms))

    def test_three_labels(self):
        """MATCH (n:A:B:C) RETURN n parses three labels via LabelTerm."""
        results = self.neo4j.parse("MATCH (n:A:B:C) RETURN n")
        self.assertEqual(len(results), 1)
        terms = list(results[0].find_all(ast.LabelTerm))
        self.assertTrue(any(len(lt.label_factors) == 3 for lt in terms))

    def test_multi_label_round_trip(self):
        """Multi-label round-trips with colon separation."""
        result = self._round_trip("MATCH (n:A:B:C) RETURN n")
        self.assertIn(":A", result)
        self.assertIn(":B", result)
        self.assertIn(":C", result)

    def test_create_multi_label(self):
        """CREATE (n:A:B) parses with multi-labels."""
        results = self.neo4j.parse("CREATE (n:A:B)")
        self.assertEqual(len(results), 1)
        labels = list(results[0].find_all(ast.LabelSetSpecification))
        self.assertTrue(any(len(ls.list_label_name) == 2 for ls in labels))


# =============================================================================
# WITH chaining tests (Plan 038, Feature 5)
# =============================================================================


class TestCypherWithChaining(unittest.TestCase):
    """Test Cypher WITH multi-part query chaining."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        results = self.neo4j.parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return results[0]

    def _round_trip(self, query):
        return self.neo4j.generate(self._parse(query))

    def test_match_with_return(self):
        """MATCH (n) WITH n RETURN n parses as multi-part query."""
        tree = self._parse("MATCH (n) WITH n RETURN n")
        self.assertIsNotNone(tree)

    def test_match_with_where_return(self):
        """MATCH (n) WITH n.name AS name WHERE name = 'A' RETURN name."""
        tree = self._parse("MATCH (n) WITH n.name AS name WHERE name = 'A' RETURN name")
        self.assertIsNotNone(tree)

    def test_with_list_return(self):
        """WITH [1,2,3] AS list RETURN list."""
        tree = self._parse("WITH [1,2,3] AS list RETURN list")
        self.assertIsNotNone(tree)

    def test_match_with_order_limit_return(self):
        """MATCH (n) WITH n ORDER BY n.name LIMIT 10 RETURN n."""
        tree = self._parse("MATCH (n) WITH n ORDER BY n.name LIMIT 10 RETURN n")
        self.assertIsNotNone(tree)

    def test_with_round_trip(self):
        """WITH chained query round-trips."""
        result = self._round_trip("MATCH (n) WITH n RETURN n")
        self.assertIn("WITH", result)
        self.assertIn("RETURN", result)

    def test_multiple_with(self):
        """Multiple WITH clauses chain correctly."""
        tree = self._parse("MATCH (n) WITH n WITH n.name AS name RETURN name")
        self.assertIsNotNone(tree)

    def test_with_aggregation(self):
        """WITH supports aggregation: MATCH (n) WITH count(n) AS cnt RETURN cnt."""
        tree = self._parse("MATCH (n) WITH count(n) AS cnt RETURN cnt")
        self.assertIsNotNone(tree)

    def test_with_distinct(self):
        """WITH DISTINCT works."""
        tree = self._parse("MATCH (n) WITH DISTINCT n.name AS name RETURN name")
        self.assertIsNotNone(tree)

    def test_unwind_with_return(self):
        """UNWIND chains naturally: UNWIND [1,2,3] AS x WITH x RETURN x."""
        tree = self._parse("UNWIND [1,2,3] AS x RETURN x")
        self.assertIsNotNone(tree)


# =============================================================================
# CASE expression operands tests (Plan 038b, Feature 1)
# =============================================================================


class TestCypherCaseOperands(unittest.TestCase):
    """Test CASE expression with full value expressions as operands."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        results = self.neo4j.parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return results[0]

    def _round_trip(self, query):
        return self.neo4j.generate(self._parse(query))

    def test_case_negative_operand(self):
        """CASE -1 WHEN -1 THEN 'neg' ELSE 'other' END."""
        tree = self._parse("RETURN CASE -1 WHEN -1 THEN 'neg' ELSE 'other' END")
        self.assertIsNotNone(tree)

    def test_case_expression_operand(self):
        """CASE 1 + 1 WHEN 2 THEN 'two' ELSE 'other' END."""
        tree = self._parse("RETURN CASE 1 + 1 WHEN 2 THEN 'two' ELSE 'other' END")
        self.assertIsNotNone(tree)

    def test_case_when_expression(self):
        """CASE x WHEN 1 + 1 THEN 'two' END — expression in WHEN."""
        tree = self._parse("WITH 2 AS x RETURN CASE x WHEN 1 + 1 THEN 'two' ELSE 'other' END")
        self.assertIsNotNone(tree)

    def test_case_negative_round_trip(self):
        result = self._round_trip("RETURN CASE -1 WHEN -1 THEN 'neg' ELSE 'other' END")
        self.assertIn("CASE", result)
        self.assertIn("WHEN", result)
        self.assertIn("END", result)


# =============================================================================
# Comparison operators in value expressions tests (Plan 038b, Feature 2)
# =============================================================================


class TestCypherComparisonExpression(unittest.TestCase):
    """Test comparison operators (=, <>, <, >, <=, >=) in RETURN position.

    These use standard GQL ComparisonPredicate via the ValueExpression upgrade
    mechanism (_parse_cypher_value_expression) — NOT custom AST nodes.
    """

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        results = self.neo4j.parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return results[0]

    def _round_trip(self, query):
        return self.neo4j.generate(self._parse(query))

    def test_equals(self):
        """RETURN 1 = 1 AS eq — uses standard ComparisonPredicate."""
        tree = self._parse("RETURN 1 = 1 AS eq")
        comps = list(tree.find_all(ast.ComparisonPredicatePart2))
        self.assertEqual(len(comps), 1)
        self.assertEqual(comps[0].comp_op, ast.ComparisonPredicatePart2.CompOp.EQUALS)

    def test_not_equals(self):
        """RETURN 1 <> 2 AS neq."""
        tree = self._parse("RETURN 1 <> 2 AS neq")
        comps = list(tree.find_all(ast.ComparisonPredicatePart2))
        self.assertEqual(len(comps), 1)
        self.assertEqual(comps[0].comp_op, ast.ComparisonPredicatePart2.CompOp.NOT_EQUALS)

    def test_less_than(self):
        """RETURN 1 < 2 AS lt."""
        tree = self._parse("RETURN 1 < 2 AS lt")
        self.assertIsNotNone(tree)

    def test_greater_than(self):
        """RETURN 2 > 1 AS gt."""
        tree = self._parse("RETURN 2 > 1 AS gt")
        self.assertIsNotNone(tree)

    def test_less_than_or_equals(self):
        """RETURN 1 <= 2 AS lte."""
        tree = self._parse("RETURN 1 <= 2 AS lte")
        self.assertIsNotNone(tree)

    def test_greater_than_or_equals(self):
        """RETURN 2 >= 1 AS gte."""
        tree = self._parse("RETURN 2 >= 1 AS gte")
        self.assertIsNotNone(tree)

    def test_equals_round_trip(self):
        result = self._round_trip("RETURN 1 = 1 AS eq")
        self.assertIn("=", result)

    def test_not_equals_round_trip(self):
        result = self._round_trip("RETURN 1 <> 2 AS neq")
        self.assertIn("<>", result)

    def test_comparison_with_property(self):
        """MATCH (n) RETURN n.age > 18 AS adult."""
        tree = self._parse("MATCH (n) RETURN n.age > 18 AS adult")
        self.assertIsNotNone(tree)

    def test_where_comparison_still_works(self):
        """Ensure WHERE comparisons don't regress."""
        tree = self._parse("MATCH (n) WHERE n.age > 25 RETURN n")
        self.assertIsNotNone(tree)


# =============================================================================
# Boolean operators in value expressions tests (Plan 038b, Feature 3)
# =============================================================================


class TestCypherBooleanExpression(unittest.TestCase):
    """Test boolean operators (AND, OR, XOR) at the CVE level."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        results = self.neo4j.parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return results[0]

    def _round_trip(self, query):
        return self.neo4j.generate(self._parse(query))

    def test_and(self):
        """RETURN true AND false AS r — uses standard BooleanValueExpression."""
        tree = self._parse("RETURN true AND false AS r")
        bves = list(tree.find_all(ast.BooleanValueExpression))
        self.assertGreaterEqual(len(bves), 1)

    def test_or(self):
        """RETURN true OR false AS r."""
        tree = self._parse("RETURN true OR false AS r")
        bves = list(tree.find_all(ast.BooleanValueExpression))
        self.assertGreaterEqual(len(bves), 1)

    def test_and_with_comparison(self):
        """RETURN 1 = 1 AND 2 = 2 AS r."""
        tree = self._parse("RETURN 1 = 1 AND 2 = 2 AS r")
        self.assertIsNotNone(tree)

    def test_or_with_comparison(self):
        """RETURN 1 = 2 OR 2 = 2 AS r."""
        tree = self._parse("RETURN 1 = 2 OR 2 = 2 AS r")
        self.assertIsNotNone(tree)

    def test_and_round_trip(self):
        result = self._round_trip("RETURN true AND false AS r")
        self.assertIn("AND", result)

    def test_or_round_trip(self):
        result = self._round_trip("RETURN true OR false AS r")
        self.assertIn("OR", result)

    def test_and_precedence_over_or(self):
        """RETURN true OR false AND false — AND binds tighter."""
        tree = self._parse("RETURN true OR false AND false AS r")
        bves = list(tree.find_all(ast.BooleanValueExpression))
        self.assertGreaterEqual(len(bves), 1)

    def test_in_and_contains_combined(self):
        """Ensure WHERE with IN + AND + CONTAINS still works."""
        tree = self._parse("MATCH (n) WHERE n.age IN [25, 30] AND n.name CONTAINS 'x' RETURN n")
        self.assertIsNotNone(tree)


# =============================================================================
# range() function tests (Plan 038b, Feature 4)
# =============================================================================


class TestRangeFunc(unittest.TestCase):
    """Test range(start, end [, step]) function."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        results = self.neo4j.parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return results[0]

    def _round_trip(self, query):
        return self.neo4j.generate(self._parse(query))

    def test_range_two_args(self):
        """RETURN range(0, 10) AS r."""
        from graphglot.ast.functions import RangeFunc

        tree = self._parse("RETURN range(0, 10) AS r")
        fns = list(tree.find_all(RangeFunc))
        self.assertEqual(len(fns), 1)
        self.assertEqual(len(fns[0].arguments), 2)

    def test_range_three_args(self):
        """RETURN range(0, 10, 2) AS r."""
        from graphglot.ast.functions import RangeFunc

        tree = self._parse("RETURN range(0, 10, 2) AS r")
        fns = list(tree.find_all(RangeFunc))
        self.assertEqual(len(fns), 1)
        self.assertEqual(len(fns[0].arguments), 3)

    def test_range_round_trip(self):
        result = self._round_trip("RETURN range(0, 10) AS r")
        self.assertIn("range(", result.lower())
        self.assertIn("10", result)

    def test_range_with_step_round_trip(self):
        result = self._round_trip("RETURN range(0, 10, 2) AS r")
        self.assertIn("range(", result.lower())

    def test_range_in_unwind(self):
        """UNWIND range(1, 3) AS x RETURN x."""
        tree = self._parse("UNWIND range(1, 3) AS x RETURN x")
        self.assertIsNotNone(tree)


# =============================================================================
# List slicing tests (Plan 038b, Feature 5)
# =============================================================================


class TestCypherListSlicing(unittest.TestCase):
    """Test list slicing expr[start..end]."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        results = self.neo4j.parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return results[0]

    def _round_trip(self, query):
        return self.neo4j.generate(self._parse(query))

    def test_full_slice(self):
        """RETURN [1, 2, 3][0..2] AS r."""
        from graphglot.ast.cypher import CypherSliceExpression

        tree = self._parse("RETURN [1, 2, 3][0..2] AS r")
        slices = list(tree.find_all(CypherSliceExpression))
        self.assertEqual(len(slices), 1)
        self.assertIsNotNone(slices[0].start)
        self.assertIsNotNone(slices[0].end)

    def test_slice_from_start(self):
        """RETURN [1, 2, 3][..2] AS r."""
        from graphglot.ast.cypher import CypherSliceExpression

        tree = self._parse("RETURN [1, 2, 3][..2] AS r")
        slices = list(tree.find_all(CypherSliceExpression))
        self.assertEqual(len(slices), 1)
        self.assertIsNone(slices[0].start)
        self.assertIsNotNone(slices[0].end)

    def test_slice_to_end(self):
        """RETURN [1, 2, 3][1..] AS r."""
        from graphglot.ast.cypher import CypherSliceExpression

        tree = self._parse("RETURN [1, 2, 3][1..] AS r")
        slices = list(tree.find_all(CypherSliceExpression))
        self.assertEqual(len(slices), 1)
        self.assertIsNotNone(slices[0].start)
        self.assertIsNone(slices[0].end)

    def test_slice_round_trip(self):
        result = self._round_trip("RETURN [1, 2, 3][0..2] AS r")
        self.assertIn("[0..2]", result)

    def test_slice_from_start_round_trip(self):
        result = self._round_trip("RETURN [1, 2, 3][..2] AS r")
        self.assertIn("[..2]", result)

    def test_slice_to_end_round_trip(self):
        result = self._round_trip("RETURN [1, 2, 3][1..] AS r")
        self.assertIn("[1..]", result)

    def test_subscript_still_works(self):
        """Regular subscript [0] still works."""
        from graphglot.ast.cypher import CypherSubscriptExpression

        tree = self._parse("RETURN [1, 2, 3][0] AS r")
        subs = list(tree.find_all(CypherSubscriptExpression))
        self.assertEqual(len(subs), 1)

    def test_slice_on_variable(self):
        """WITH [1, 2, 3] AS l RETURN l[0..2] AS r."""
        tree = self._parse("WITH [1, 2, 3] AS l RETURN l[0..2] AS r")
        self.assertIsNotNone(tree)


# =============================================================================
# Pattern comprehension tests (Plan 038b, Feature 6)
# =============================================================================


class TestCypherPatternComprehension(unittest.TestCase):
    """Test pattern comprehension [(pattern) [WHERE ...] | projection]."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        results = self.neo4j.parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return results[0]

    def _round_trip(self, query):
        return self.neo4j.generate(self._parse(query))

    def test_simple_pattern_comprehension(self):
        """RETURN [(a)-->(b) | b.name] AS names."""
        from graphglot.ast.cypher import CypherPatternComprehension

        tree = self._parse("MATCH (a) RETURN [(a)-->(b) | b.name] AS names")
        pcs = list(tree.find_all(CypherPatternComprehension))
        self.assertEqual(len(pcs), 1)
        self.assertIsNone(pcs[0].where_clause)

    def test_pattern_comprehension_with_where(self):
        """RETURN [(a)-->(b) WHERE b.age > 18 | b.name] AS names."""
        from graphglot.ast.cypher import CypherPatternComprehension

        tree = self._parse("MATCH (a) RETURN [(a)-->(b) WHERE b.age > 18 | b.name] AS names")
        pcs = list(tree.find_all(CypherPatternComprehension))
        self.assertEqual(len(pcs), 1)
        self.assertIsNotNone(pcs[0].where_clause)

    def test_pattern_comprehension_round_trip(self):
        result = self._round_trip("MATCH (a) RETURN [(a)-->(b) | b.name] AS names")
        self.assertIn("[", result)
        self.assertIn("|", result)
        self.assertIn("]", result)

    def test_pattern_comprehension_feature_gating(self):
        """CypherPatternComprehension requires CY:EX01."""
        from graphglot.ast.cypher import CypherPatternComprehension

        tree = self._parse("MATCH (a) RETURN [(a)-->(b) | b.name] AS names")
        pcs = list(tree.find_all(CypherPatternComprehension))
        self.assertEqual(len(pcs), 1)
        feature_ids = {f.id for f in pcs[0].get_required_features()}
        self.assertIn("CY:EX01", feature_ids)


# =============================================================================
# Variable-length path tests (Plan 039)
# =============================================================================


class TestCypherVariableLengthPaths(unittest.TestCase):
    """Test Cypher variable-length relationship patterns ``[*N..M]``."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        results = self.neo4j.parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return results[0]

    def _round_trip(self, query):
        tree = self._parse(query)
        return self.neo4j.generate(tree)

    def _get_qpp(self, query):
        """Parse query and return the first QuantifiedPathPrimary."""
        tree = self._parse(query)
        qpps = list(tree.find_all(ast.QuantifiedPathPrimary))
        self.assertEqual(len(qpps), 1, f"Expected 1 QuantifiedPathPrimary for: {query}")
        return qpps[0]

    # --- Directed right: quantifier forms ---

    def test_unbounded_star(self):
        """MATCH (a)-[*]->(b) RETURN a — GeneralQuantifier(None, None)."""
        qpp = self._get_qpp("MATCH (a)-[*]->(b) RETURN a")
        self.assertIsInstance(qpp.path_primary, ast.FullEdgePointingRight)
        q = qpp.graph_pattern_quantifier
        self.assertIsInstance(q, ast.GeneralQuantifier)
        self.assertIsNone(q.lower_bound)
        self.assertIsNone(q.upper_bound)

    def test_fixed_quantifier(self):
        """MATCH (a)-[*2]->(b) RETURN a — FixedQuantifier(2)."""
        qpp = self._get_qpp("MATCH (a)-[*2]->(b) RETURN a")
        self.assertIsInstance(qpp.path_primary, ast.FullEdgePointingRight)
        q = qpp.graph_pattern_quantifier
        self.assertIsInstance(q, ast.FixedQuantifier)
        self.assertEqual(q.unsigned_integer.value, 2)

    def test_bounded_range(self):
        """MATCH (a)-[*1..3]->(b) RETURN a — GeneralQuantifier(1, 3)."""
        qpp = self._get_qpp("MATCH (a)-[*1..3]->(b) RETURN a")
        q = qpp.graph_pattern_quantifier
        self.assertIsInstance(q, ast.GeneralQuantifier)
        self.assertEqual(q.lower_bound.value, 1)
        self.assertEqual(q.upper_bound.value, 3)

    def test_upper_only(self):
        """MATCH (a)-[*..5]->(b) RETURN a — GeneralQuantifier(None, 5)."""
        qpp = self._get_qpp("MATCH (a)-[*..5]->(b) RETURN a")
        q = qpp.graph_pattern_quantifier
        self.assertIsInstance(q, ast.GeneralQuantifier)
        self.assertIsNone(q.lower_bound)
        self.assertEqual(q.upper_bound.value, 5)

    def test_lower_only(self):
        """MATCH (a)-[*3..]->(b) RETURN a — GeneralQuantifier(3, None)."""
        qpp = self._get_qpp("MATCH (a)-[*3..]->(b) RETURN a")
        q = qpp.graph_pattern_quantifier
        self.assertIsInstance(q, ast.GeneralQuantifier)
        self.assertEqual(q.lower_bound.value, 3)
        self.assertIsNone(q.upper_bound)

    # --- Decorations: type, variable, property ---

    def test_type_and_unbounded(self):
        """MATCH (a)-[:KNOWS*]->(b) RETURN a — type + unbounded."""
        qpp = self._get_qpp("MATCH (a)-[:KNOWS*]->(b) RETURN a")
        self.assertIsInstance(qpp.path_primary, ast.FullEdgePointingRight)
        filler = qpp.path_primary.element_pattern_filler
        self.assertIsNotNone(filler.is_label_expression)
        q = qpp.graph_pattern_quantifier
        self.assertIsInstance(q, ast.GeneralQuantifier)
        self.assertIsNone(q.lower_bound)
        self.assertIsNone(q.upper_bound)

    def test_var_type_and_bounded(self):
        """MATCH (a)-[r:KNOWS*1..2]->(b) RETURN a — variable + type + bounded."""
        qpp = self._get_qpp("MATCH (a)-[r:KNOWS*1..2]->(b) RETURN a")
        filler = qpp.path_primary.element_pattern_filler
        self.assertIsNotNone(filler.element_variable_declaration)
        self.assertIsNotNone(filler.is_label_expression)
        q = qpp.graph_pattern_quantifier
        self.assertIsInstance(q, ast.GeneralQuantifier)
        self.assertEqual(q.lower_bound.value, 1)
        self.assertEqual(q.upper_bound.value, 2)

    def test_type_quantifier_and_property(self):
        """MATCH (a)-[:KNOWS* {year: 1988}]->(b) RETURN a — type + quantifier + property."""
        qpp = self._get_qpp("MATCH (a)-[:KNOWS* {year: 1988}]->(b) RETURN a")
        filler = qpp.path_primary.element_pattern_filler
        self.assertIsNotNone(filler.is_label_expression)
        self.assertIsNotNone(filler.element_pattern_predicate)
        q = qpp.graph_pattern_quantifier
        self.assertIsInstance(q, ast.GeneralQuantifier)

    # --- Other edge directions ---

    def test_left_pointing(self):
        """MATCH (a)<-[*1..3]-(b) RETURN a — FullEdgePointingLeft."""
        qpp = self._get_qpp("MATCH (a)<-[*1..3]-(b) RETURN a")
        self.assertIsInstance(qpp.path_primary, ast.FullEdgePointingLeft)

    def test_undirected(self):
        """MATCH (a)-[*]-(b) RETURN a — FullEdgeAnyDirection."""
        qpp = self._get_qpp("MATCH (a)-[*]-(b) RETURN a")
        self.assertIsInstance(qpp.path_primary, ast.FullEdgeAnyDirection)

    def test_undirected_type_bounded(self):
        """MATCH (a)-[:KNOWS*1..5]-(b) RETURN a — undirected + type + bounded."""
        qpp = self._get_qpp("MATCH (a)-[:KNOWS*1..5]-(b) RETURN a")
        self.assertIsInstance(qpp.path_primary, ast.FullEdgeAnyDirection)
        filler = qpp.path_primary.element_pattern_filler
        self.assertIsNotNone(filler.is_label_expression)
        q = qpp.graph_pattern_quantifier
        self.assertIsInstance(q, ast.GeneralQuantifier)
        self.assertEqual(q.lower_bound.value, 1)
        self.assertEqual(q.upper_bound.value, 5)

    # --- Round-trip tests ---

    def test_round_trip_unbounded(self):
        result = self._round_trip("MATCH (a)-[*]->(b) RETURN a")
        self.assertIn("{,}", result)

    def test_round_trip_fixed(self):
        result = self._round_trip("MATCH (a)-[*2]->(b) RETURN a")
        self.assertIn("{2}", result)

    def test_round_trip_bounded(self):
        result = self._round_trip("MATCH (a)-[*1..3]->(b) RETURN a")
        self.assertIn("{1,3}", result)

    def test_round_trip_type_bounded(self):
        result = self._round_trip("MATCH (a)-[:KNOWS*1..5]->(b) RETURN a")
        self.assertIn(":KNOWS", result)
        self.assertIn("{1,5}", result)

    def test_round_trip_var_type_bounded(self):
        result = self._round_trip("MATCH (a)-[r:KNOWS*1..2]->(b) RETURN a")
        self.assertIn(":KNOWS", result)
        self.assertIn("{1,2}", result)

    def test_round_trip_left_pointing(self):
        result = self._round_trip("MATCH (a)<-[*1..3]-(b) RETURN a")
        self.assertIn("{1,3}", result)

    def test_round_trip_undirected(self):
        result = self._round_trip("MATCH (a)-[*]-(b) RETURN a")
        self.assertIn("{,}", result)


# =============================================================================
# Type conversion functions (Plan 040)
# =============================================================================


class TestTypeConversionFunctions(unittest.TestCase):
    """Test toBoolean(), toInteger(), toFloat(), toString() parsing and generation."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        return self.neo4j.parse(query)

    def _round_trip(self, query):
        results = self._parse(query)
        return self.neo4j.generate(results[0])

    def test_parse_to_boolean(self):
        results = self._parse("RETURN toBoolean('true')")
        matches = list(results[0].find_all(ast.CastSpecification))
        self.assertEqual(len(matches), 1)
        self.assertIsInstance(matches[0].cast_target, ast.BooleanType)

    def test_parse_to_integer(self):
        results = self._parse("RETURN toInteger('42')")
        matches = list(results[0].find_all(ast.CastSpecification))
        self.assertEqual(len(matches), 1)
        self.assertIsInstance(matches[0].cast_target, ast.SignedBinaryExactNumericType)

    def test_parse_to_float(self):
        results = self._parse("RETURN toFloat('3.14')")
        matches = list(results[0].find_all(ast.CastSpecification))
        self.assertEqual(len(matches), 1)
        self.assertIsInstance(matches[0].cast_target, ast.ApproximateNumericType)

    def test_parse_to_string(self):
        results = self._parse("RETURN toString(42)")
        matches = list(results[0].find_all(ast.CastSpecification))
        self.assertEqual(len(matches), 1)
        self.assertIsInstance(matches[0].cast_target, ast.CharacterStringType)

    def test_round_trip_to_boolean(self):
        result = self._round_trip("RETURN toBoolean('true')")
        self.assertIn("toBoolean(", result)

    def test_round_trip_to_integer(self):
        result = self._round_trip("RETURN toInteger('42')")
        self.assertIn("toInteger(", result)

    def test_round_trip_to_float(self):
        result = self._round_trip("RETURN toFloat('3.14')")
        self.assertIn("toFloat(", result)

    def test_round_trip_to_string(self):
        result = self._round_trip("RETURN toString(42)")
        self.assertIn("toString(", result)

    def test_to_integer_in_return_expression(self):
        results = self._parse("MATCH (n) RETURN toInteger(n.age)")
        matches = list(results[0].find_all(ast.CastSpecification))
        self.assertEqual(len(matches), 1)
        self.assertIsInstance(matches[0].cast_target, ast.SignedBinaryExactNumericType)

    def test_gql_cast_transpiles_to_cypher(self):
        """GQL CAST(x AS TYPE) should generate as toXYZ() in Cypher."""
        result = self._round_trip("RETURN CAST('true' AS BOOLEAN)")
        self.assertIn("toBoolean(", result)
        result = self._round_trip("RETURN CAST('42' AS INTEGER)")
        self.assertIn("toInteger(", result)
        result = self._round_trip("RETURN CAST('3.14' AS FLOAT)")
        self.assertIn("toFloat(", result)
        result = self._round_trip("RETURN CAST(42 AS STRING)")
        self.assertIn("toString(", result)


# =============================================================================
# type() and properties() functions (Plan 040)
# =============================================================================


class TestGraphFunctions(unittest.TestCase):
    """Test type() and properties() parsing and generation."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        return self.neo4j.parse(query)

    def _round_trip(self, query):
        results = self._parse(query)
        return self.neo4j.generate(results[0])

    def test_parse_type_function(self):
        from graphglot.ast.functions import TypeFunc

        results = self._parse("MATCH ()-[r]->() RETURN type(r)")
        matches = list(results[0].find_all(TypeFunc))
        self.assertEqual(len(matches), 1)

    def test_round_trip_type(self):
        result = self._round_trip("MATCH ()-[r]->() RETURN type(r)")
        self.assertIn("type(", result.lower())

    def test_parse_properties(self):
        from graphglot.ast.functions import Properties

        results = self._parse("MATCH (n) RETURN properties(n)")
        matches = list(results[0].find_all(Properties))
        self.assertEqual(len(matches), 1)

    def test_round_trip_properties(self):
        result = self._round_trip("MATCH (n) RETURN properties(n)")
        self.assertIn("properties(", result.lower())

    def test_type_in_where(self):
        from graphglot.ast.functions import TypeFunc

        results = self._parse("MATCH ()-[r]->() WHERE type(r) = 'KNOWS' RETURN r")
        matches = list(results[0].find_all(TypeFunc))
        self.assertEqual(len(matches), 1)


# =============================================================================
# Pattern predicates (Plan 040)
# =============================================================================


class TestPatternPredicates(unittest.TestCase):
    """Test bare pattern predicates: WHERE (n)-[:T]->()."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        return self.neo4j.parse(query)

    def _round_trip(self, query):
        results = self._parse(query)
        return self.neo4j.generate(results[0])

    def test_parse_pattern_predicate_outgoing(self):
        from graphglot.ast.cypher import CypherPatternPredicate

        results = self._parse("MATCH (n) WHERE (n)-->() RETURN n")
        matches = list(results[0].find_all(CypherPatternPredicate))
        self.assertEqual(len(matches), 1)

    def test_parse_pattern_predicate_typed(self):
        from graphglot.ast.cypher import CypherPatternPredicate

        results = self._parse("MATCH (n) WHERE (n)-[:KNOWS]->() RETURN n")
        matches = list(results[0].find_all(CypherPatternPredicate))
        self.assertEqual(len(matches), 1)

    def test_parse_pattern_predicate_incoming(self):
        from graphglot.ast.cypher import CypherPatternPredicate

        results = self._parse("MATCH (n) WHERE (n)<--() RETURN n")
        matches = list(results[0].find_all(CypherPatternPredicate))
        self.assertEqual(len(matches), 1)

    def test_parse_pattern_predicate_undirected(self):
        from graphglot.ast.cypher import CypherPatternPredicate

        results = self._parse("MATCH (n) WHERE (n)--() RETURN n")
        matches = list(results[0].find_all(CypherPatternPredicate))
        self.assertEqual(len(matches), 1)

    def test_round_trip_pattern_predicate(self):
        result = self._round_trip("MATCH (n) WHERE (n)-[:KNOWS]->() RETURN n")
        self.assertIn("KNOWS", result)

    def test_negated_pattern_predicate(self):
        """NOT (n)-[:T]->() should parse with NOT as a boolean operator."""
        results = self._parse("MATCH (n) WHERE NOT (n)-->() RETURN n")
        from graphglot.ast.cypher import CypherPatternPredicate

        matches = list(results[0].find_all(CypherPatternPredicate))
        self.assertEqual(len(matches), 1)


# =============================================================================
# Data-modifying statement chaining (Plan 041, Feature 1)
# =============================================================================


class TestDataModifyingChaining(unittest.TestCase):
    """Test MATCH+DELETE/REMOVE/SET chaining via GQL data-modifying path."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        return self.neo4j.parse(query)

    def _round_trip(self, query):
        results = self._parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return self.neo4j.generate(results[0])

    def test_match_remove_property(self):
        """MATCH (n) REMOVE n.num RETURN n parses."""
        results = self._parse("MATCH (n) REMOVE n.num RETURN n")
        self.assertEqual(len(results), 1)
        removes = list(results[0].find_all(ast.RemoveStatement))
        self.assertEqual(len(removes), 1)

    def test_match_delete(self):
        """MATCH (n) DELETE n parses."""
        results = self._parse("MATCH (n) DELETE n")
        self.assertEqual(len(results), 1)
        deletes = list(results[0].find_all(ast.DeleteStatement))
        self.assertEqual(len(deletes), 1)

    def test_match_detach_delete(self):
        """MATCH (n) DETACH DELETE n parses."""
        results = self._parse("MATCH (n) DETACH DELETE n")
        self.assertEqual(len(results), 1)
        deletes = list(results[0].find_all(ast.DeleteStatement))
        self.assertEqual(len(deletes), 1)

    def test_match_set_property(self):
        """MATCH (n) SET n.name = 'x' RETURN n parses."""
        results = self._parse("MATCH (n) SET n.name = 'x' RETURN n")
        self.assertEqual(len(results), 1)
        sets = list(results[0].find_all(ast.SetStatement))
        self.assertEqual(len(sets), 1)

    def test_match_delete_relationship(self):
        """MATCH (n)-[r]->() DELETE r parses."""
        results = self._parse("MATCH (n)-[r]->() DELETE r")
        self.assertEqual(len(results), 1)

    def test_match_create(self):
        """MATCH (n) CREATE (m) RETURN n, m parses via data-modifying path."""
        results = self._parse("MATCH (n) CREATE (m) RETURN n, m")
        self.assertEqual(len(results), 1)

    def test_round_trip_match_delete(self):
        """MATCH+DELETE round-trips."""
        result = self._round_trip("MATCH (n) DELETE n")
        self.assertIn("MATCH", result)
        self.assertIn("DELETE", result)

    def test_round_trip_match_set(self):
        """MATCH+SET round-trips."""
        result = self._round_trip("MATCH (n) SET n.name = 'x' RETURN n")
        self.assertIn("SET", result)

    def test_round_trip_match_remove(self):
        """MATCH+REMOVE round-trips."""
        result = self._round_trip("MATCH (n) REMOVE n.num RETURN n")
        self.assertIn("REMOVE", result)

    def test_round_trip_match_detach_delete(self):
        """MATCH+DETACH DELETE round-trips."""
        result = self._round_trip("MATCH (n) DETACH DELETE n")
        self.assertIn("DETACH", result)
        self.assertIn("DELETE", result)


# =============================================================================
# Multi-label REMOVE and SET (Plan 041, Feature 2)
# =============================================================================


class TestMultiLabelRemoveSet(unittest.TestCase):
    """Test multi-label REMOVE n:L1:L2 and SET n:L1:L2."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        return self.neo4j.parse(query)

    def _round_trip(self, query):
        results = self._parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return self.neo4j.generate(results[0])

    def test_remove_two_labels(self):
        """REMOVE n:L1:L2 produces two RemoveLabelItem entries."""
        results = self._parse("MATCH (n) REMOVE n:L1:L2 RETURN n")
        self.assertEqual(len(results), 1)
        items = list(results[0].find_all(ast.RemoveLabelItem))
        self.assertEqual(len(items), 2)

    def test_set_two_labels(self):
        """SET n:L1:L2 produces two SetLabelItem entries."""
        results = self._parse("MATCH (n) SET n:L1:L2 RETURN n")
        self.assertEqual(len(results), 1)
        items = list(results[0].find_all(ast.SetLabelItem))
        self.assertEqual(len(items), 2)

    def test_round_trip_remove_multi_label(self):
        """REMOVE n:L1:L2 round-trips with colon syntax."""
        result = self._round_trip("MATCH (n) REMOVE n:L1:L2 RETURN n")
        self.assertIn("REMOVE", result)
        self.assertIn("L1", result)
        self.assertIn("L2", result)

    def test_round_trip_set_multi_label(self):
        """SET n:L1:L2 round-trips with colon syntax."""
        result = self._round_trip("MATCH (n) SET n:L1:L2 RETURN n")
        self.assertIn("SET", result)
        self.assertIn("L1", result)
        self.assertIn("L2", result)

    def test_remove_single_label(self):
        """Single-label REMOVE still works."""
        results = self._parse("MATCH (n) REMOVE n:Person RETURN n")
        self.assertEqual(len(results), 1)
        items = list(results[0].find_all(ast.RemoveLabelItem))
        self.assertEqual(len(items), 1)

    def test_set_single_label(self):
        """Single-label SET still works."""
        results = self._parse("MATCH (n) SET n:Person RETURN n")
        self.assertEqual(len(results), 1)
        items = list(results[0].find_all(ast.SetLabelItem))
        self.assertEqual(len(items), 1)


# =============================================================================
# CALL procedure fixes (Plan 041, Feature 3)
# =============================================================================


class TestCallProcedure(unittest.TestCase):
    """Test CALL procedure parsing and generation."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        return self.neo4j.parse(query)

    def _round_trip(self, query):
        results = self._parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return self.neo4j.generate(results[0])

    def test_call_with_parens_round_trip(self):
        """CALL db.labels() should keep parentheses after round-trip."""
        result = self._round_trip("CALL db.labels()")
        self.assertIn("()", result)

    def test_call_no_parens_parse(self):
        """CALL db.labels (no parens) should parse."""
        results = self._parse("CALL db.labels")
        self.assertEqual(len(results), 1)

    def test_call_no_parens_round_trip(self):
        """CALL db.labels (no parens) round-trips with parens added."""
        result = self._round_trip("CALL db.labels")
        self.assertIn("labels()", result)

    def test_call_with_yield(self):
        """CALL db.labels() YIELD label should parse and round-trip."""
        result = self._round_trip("CALL db.labels() YIELD label")
        self.assertIn("YIELD", result)
        self.assertIn("()", result)

    def test_call_with_args(self):
        """CALL db.index.fulltext.queryNodes('idx', 'search') round-trips."""
        result = self._round_trip("CALL db.index.fulltext.queryNodes('idx', 'search')")
        self.assertIn("queryNodes(", result)

    def test_call_no_parens_with_yield(self):
        """CALL db.labels YIELD label should parse."""
        results = self._parse("CALL db.labels YIELD label")
        self.assertEqual(len(results), 1)


# =============================================================================
# Label predicate in WHERE (Plan 041, Feature 4)
# =============================================================================


class TestLabelPredicate(unittest.TestCase):
    """Test WHERE n:Label parsing and generation."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        return self.neo4j.parse(query)

    def _round_trip(self, query):
        results = self._parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return self.neo4j.generate(results[0])

    def test_label_predicate_parse(self):
        """MATCH (n) WHERE n:Person RETURN n parses."""
        results = self._parse("MATCH (n) WHERE n:Person RETURN n")
        self.assertEqual(len(results), 1)
        preds = list(results[0].find_all(ast.LabeledPredicate))
        self.assertEqual(len(preds), 1)

    def test_label_predicate_round_trip(self):
        """Label predicate round-trips with colon syntax."""
        result = self._round_trip("MATCH (n) WHERE n:Person RETURN n")
        self.assertIn("n:Person", result)

    def test_multi_variable_label_predicate(self):
        """WHERE n:Person AND m:Dog parses two label predicates."""
        results = self._parse("MATCH (n), (m) WHERE n:Person AND m:Dog RETURN n, m")
        self.assertEqual(len(results), 1)
        preds = list(results[0].find_all(ast.LabeledPredicate))
        self.assertEqual(len(preds), 2)

    def test_label_predicate_in_optional_match(self):
        """OPTIONAL MATCH + WHERE label predicate."""
        results = self._parse("MATCH (n) OPTIONAL MATCH (n)-[r]->(m) WHERE m:Person RETURN n, m")
        self.assertEqual(len(results), 1)
        preds = list(results[0].find_all(ast.LabeledPredicate))
        self.assertEqual(len(preds), 1)

    def test_not_label_predicate(self):
        """WHERE NOT n:Person parses with negation."""
        results = self._parse("MATCH (n) WHERE NOT n:Person RETURN n")
        self.assertEqual(len(results), 1)


# =============================================================================
# OPTIONAL MATCH (Plan 041, Feature 5)
# =============================================================================


class TestOptionalMatch(unittest.TestCase):
    """Test OPTIONAL MATCH parsing and generation."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        return self.neo4j.parse(query)

    def _round_trip(self, query):
        results = self._parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return self.neo4j.generate(results[0])

    def test_optional_match_parse(self):
        """MATCH (n) OPTIONAL MATCH (n)-[r]->(m) RETURN n, r, m parses."""
        results = self._parse("MATCH (n) OPTIONAL MATCH (n)-[r]->(m) RETURN n, r, m")
        self.assertEqual(len(results), 1)

    def test_optional_match_round_trip(self):
        """OPTIONAL MATCH round-trips."""
        result = self._round_trip("MATCH (n) OPTIONAL MATCH (n)-[r]->(m) RETURN n, r, m")
        self.assertIn("OPTIONAL", result)
        self.assertIn("MATCH", result)

    def test_standalone_optional_match(self):
        """OPTIONAL MATCH as first clause."""
        results = self._parse("OPTIONAL MATCH (n) RETURN n")
        self.assertEqual(len(results), 1)


class TestCypherListFunctions(unittest.TestCase):
    """Test Cypher list utility functions: tail, head, last, reverse, rand."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        return self.neo4j.parse(query)

    def _round_trip(self, query):
        results = self._parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return self.neo4j.generate(results[0])

    def test_tail_function(self):
        """RETURN tail([1, 2, 3]) parses."""
        results = self._parse("RETURN tail([1, 2, 3])")
        self.assertEqual(len(results), 1)

    def test_tail_round_trip(self):
        """tail() round-trips."""
        result = self._round_trip("RETURN tail([1, 2, 3])")
        self.assertIn("tail(", result.lower())

    def test_head_function(self):
        """RETURN head([1, 2, 3]) parses."""
        results = self._parse("RETURN head([1, 2, 3])")
        self.assertEqual(len(results), 1)

    def test_head_round_trip(self):
        """head() round-trips."""
        result = self._round_trip("RETURN head([1, 2, 3])")
        self.assertIn("head(", result.lower())

    def test_last_function(self):
        """RETURN last([1, 2, 3]) parses."""
        results = self._parse("RETURN last([1, 2, 3])")
        self.assertEqual(len(results), 1)

    def test_last_round_trip(self):
        """last() round-trips."""
        result = self._round_trip("RETURN last([1, 2, 3])")
        self.assertIn("last(", result.lower())

    def test_reverse_function(self):
        """RETURN reverse([1, 2, 3]) parses."""
        results = self._parse("RETURN reverse([1, 2, 3])")
        self.assertEqual(len(results), 1)

    def test_reverse_round_trip(self):
        """reverse() round-trips."""
        result = self._round_trip("RETURN reverse([1, 2, 3])")
        self.assertIn("reverse(", result.lower())

    def test_rand_function(self):
        """RETURN rand() parses."""
        results = self._parse("RETURN rand()")
        self.assertEqual(len(results), 1)

    def test_rand_round_trip(self):
        """rand() round-trips."""
        result = self._round_trip("RETURN rand()")
        self.assertIn("rand()", result.lower())

    def test_tail_of_nodes(self):
        """tail(nodes(p)) composes with other functions."""
        results = self._parse("MATCH p = (n)-[*]->(m) RETURN tail(nodes(p))")
        self.assertEqual(len(results), 1)

    def test_reverse_in_case(self):
        """reverse() in CASE expression."""
        result = self._round_trip(
            "WITH [1] AS list RETURN CASE WHEN rand() < 0.5 THEN reverse(list) ELSE list END"
        )
        self.assertIn("reverse(", result.lower())
        self.assertIn("rand()", result.lower())

    def test_rand_in_list_comprehension(self):
        """rand() inside list comprehension."""
        results = self._parse("WITH [1, 2, 3] AS list RETURN [x IN list WHERE rand() > 0.5 | x]")
        self.assertEqual(len(results), 1)

    def test_reverse_string(self):
        """reverse() also works on strings."""
        result = self._round_trip("RETURN reverse('hello')")
        self.assertIn("reverse(", result.lower())


class TestQuantifierPredicateComparison(unittest.TestCase):
    """Test quantifier predicates in comparison contexts (none(...) = true, etc.)."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _parse(self, query):
        return self.neo4j.parse(query)

    def _round_trip(self, query):
        results = self._parse(query)
        self.assertEqual(len(results), 1, f"Expected 1 result for: {query}")
        return self.neo4j.generate(results[0])

    def test_none_equals_true(self):
        """none(x IN [1] WHERE x = 1) = true parses."""
        results = self._parse("RETURN none(x IN [1] WHERE x = 1) = true")
        self.assertEqual(len(results), 1)

    def test_none_equals_true_round_trip(self):
        """none(...) = true round-trips."""
        result = self._round_trip("RETURN none(x IN [1] WHERE x = 1) = true")
        self.assertIn("none", result.lower())
        self.assertIn("= true", result.lower())

    def test_any_not_equals_false(self):
        """any(...) <> false parses."""
        results = self._parse("RETURN any(x IN [1, 2] WHERE x > 0) <> false")
        self.assertEqual(len(results), 1)

    def test_none_equals_not_any(self):
        """none(...) = (NOT any(...)) — quantifier equivalence."""
        results = self._parse(
            "RETURN none(x IN [1, 2, 3] WHERE x = 1) = (NOT any(x IN [1, 2, 3] WHERE x = 1))"
        )
        self.assertEqual(len(results), 1)

    def test_single_equals_size(self):
        """single(x IN list WHERE pred) = (size([...]) = 1)."""
        results = self._parse(
            "RETURN single(x IN [1, 2] WHERE x > 0) = (size([x IN [1, 2] WHERE x > 0 | x]) = 1)"
        )
        self.assertEqual(len(results), 1)

    def test_all_equals_true_in_with(self):
        """all(...) = true in WITH clause."""
        results = self._parse("WITH all(x IN [1, 2, 3] WHERE x > 0) = true AS result RETURN result")
        self.assertEqual(len(results), 1)

    def test_none_comparison_less_than(self):
        """Quantifier with non-equality comparison."""
        results = self._parse("RETURN none(x IN [1] WHERE x = 1) = true")
        self.assertEqual(len(results), 1)

    def test_quantifier_combined_with_and(self):
        """Quantifier comparison combined with AND."""
        results = self._parse(
            "WITH [1, 2, 3] AS list "
            "RETURN none(x IN list WHERE false) = true AND any(x IN list WHERE x > 0) = true"
        )
        self.assertEqual(len(results), 1)


# =============================================================================
# Tier 4b: XOR, IS NULL in RETURN, quantifier RHS comparisons
# =============================================================================


class TestXorBooleanOperator(unittest.TestCase):
    """XOR boolean operator (GE07 feature gate)."""

    def _parse(self, query: str):
        d = Neo4j()
        return d.parse(query)

    def _roundtrip(self, query: str) -> str:
        d = Neo4j()
        results = d.parse(query)
        self.assertEqual(len(results), 1)
        return d.generate(results[0])

    def test_xor_basic(self):
        """RETURN true XOR false AS res."""
        results = self._parse("RETURN true XOR false AS res")
        self.assertEqual(len(results), 1)

    def test_xor_chained(self):
        """RETURN true XOR true XOR false AS res."""
        results = self._parse("RETURN true XOR true XOR false AS res")
        self.assertEqual(len(results), 1)

    def test_xor_with_null(self):
        """RETURN true XOR null AS res."""
        results = self._parse("RETURN true XOR null AS res")
        self.assertEqual(len(results), 1)

    def test_xor_round_trip(self):
        """XOR round-trip preserves XOR keyword."""
        result = self._roundtrip("RETURN true XOR false AS res")
        self.assertIn("XOR", result.upper())

    def test_xor_in_where(self):
        """WHERE clause with XOR."""
        results = self._parse(
            "UNWIND [true, false] AS a UNWIND [true, false] AS b "
            "RETURN a, b, (a XOR b) = (b XOR a) AS result"
        )
        self.assertEqual(len(results), 1)


class TestIsNullInReturn(unittest.TestCase):
    """IS NULL / IS NOT NULL in RETURN position."""

    def _parse(self, query: str):
        d = Neo4j()
        return d.parse(query)

    def _roundtrip(self, query: str) -> str:
        d = Neo4j()
        results = d.parse(query)
        self.assertEqual(len(results), 1)
        return d.generate(results[0])

    def test_null_is_null(self):
        """RETURN null IS NULL AS value."""
        results = self._parse("RETURN null IS NULL AS value")
        self.assertEqual(len(results), 1)

    def test_null_is_not_null(self):
        """RETURN null IS NOT NULL AS value."""
        results = self._parse("RETURN null IS NOT NULL AS value")
        self.assertEqual(len(results), 1)

    def test_variable_is_null(self):
        """WITH null AS n RETURN n IS NULL AS res."""
        results = self._parse("WITH null AS n RETURN n IS NULL AS res")
        self.assertEqual(len(results), 1)

    def test_property_is_null_in_return(self):
        """MATCH (n) RETURN n.prop IS NULL AS res."""
        results = self._parse("MATCH (n) RETURN n.prop IS NULL AS res")
        self.assertEqual(len(results), 1)

    def test_is_null_round_trip(self):
        """IS NULL round-trip."""
        result = self._roundtrip("RETURN null IS NULL AS value")
        self.assertIn("IS NULL", result.upper())

    def test_is_null_with_comma(self):
        """RETURN n.missing IS NULL, n.num IS NULL — comma-separated."""
        results = self._parse("MATCH (n) RETURN n.missing IS NULL, n.num IS NULL")
        self.assertEqual(len(results), 1)

    def test_is_null_in_comparison(self):
        """(a AND b) IS NULL = (b AND a) IS NULL — predicate comparison."""
        results = self._parse(
            "UNWIND [true, false, null] AS a "
            "UNWIND [true, false, null] AS b "
            "RETURN (a AND b) IS NULL = (b AND a) IS NULL AS result"
        )
        self.assertEqual(len(results), 1)

    def test_xor_is_null_comparison(self):
        """(a XOR b) IS NULL = (b XOR a) IS NULL — XOR + IS NULL + comparison."""
        results = self._parse(
            "UNWIND [true, false, null] AS a "
            "UNWIND [true, false, null] AS b "
            "WITH a, b WHERE a IS NULL OR b IS NULL "
            "RETURN a, b, (a XOR b) IS NULL = (b XOR a) IS NULL AS result"
        )
        self.assertEqual(len(results), 1)


class TestQuantifierRhsComparison(unittest.TestCase):
    """Quantifier predicate on RHS of comparison operator."""

    def _parse(self, query: str):
        d = Neo4j()
        return d.parse(query)

    def test_quantifier_rhs_lte(self):
        """(single(...) OR all(...)) <= any(...)."""
        results = self._parse(
            "RETURN (single(x IN [1, 2, 3] WHERE x = 2) "
            "OR all(x IN [1, 2, 3] WHERE x = 2)) "
            "<= any(x IN [1, 2, 3] WHERE x = 2) AS result"
        )
        self.assertEqual(len(results), 1)

    def test_quantifier_rhs_eq(self):
        """any(...) = (NOT none(...))."""
        results = self._parse(
            "RETURN any(x IN [1, 2, 3] WHERE x = 2) "
            "= (NOT none(x IN [1, 2, 3] WHERE x = 2)) AS result"
        )
        self.assertEqual(len(results), 1)


# =============================================================================
# GQL non-reserved word handling (Plan 040)
# =============================================================================


class TestGqlNonReservedWordLabels(unittest.TestCase):
    """GQL pre-reserved and reserved-unused words should be usable as labels in Cypher."""

    # 36 GQL pre-reserved + 24 GQL reserved-unused keywords
    _NON_RESERVED_LABEL_WORDS: t.ClassVar[list[str]] = [
        # 37 GQL pre-reserved words (unused by parser)
        "ABSTRACT",
        "AGGREGATE",
        "AGGREGATES",
        "ALTER",
        "CATALOG",
        "CLEAR",
        "CLONE",
        "CURRENT_ROLE",
        "CURRENT_USER",
        "DATA",
        "DIRECTORY",
        "DRYRUN",
        "EXACT",
        "FUNCTION",
        "GQLSTATUS",
        "GRANT",
        "INSTANT",
        "INFINITY",
        "NUMBER",
        "NUMERIC",
        "ON",
        "OPEN",
        "PARTITION",
        "PROCEDURE",
        "PRODUCT",
        "PROJECT",
        "QUERY",
        "RECORDS",
        "REFERENCE",
        "RENAME",
        "REVOKE",
        # NOT SUBSTRING — used as a function keyword (SUBSTRING(...))
        "SYSTEM_USER",
        "TEMPORAL",
        "UNIQUE",
        "UNIT",
        "WHITESPACE",
        # 24 GQL reserved words (only consumed via compound tokens, unused standalone)
        "ASCENDING",
        "BIG",
        "BOOLEAN",
        "BY",
        "CLOSE",
        "CURRENT_PROPERTY_GRAPH",
        "DESCENDING",
        "HOME_PROPERTY_GRAPH",
        "INTEGER",
        "INTEGER8",
        "INTEGER16",
        "INTEGER32",
        "INTEGER64",
        "INTEGER128",
        "INTEGER256",
        "NULLS",
        "ORDER",
        "PRECISION",
        "RESET",
        "SESSION",
        "SIGNED",
        "SMALL",
        "UNSIGNED",
        "VARIABLE",
    ]

    def setUp(self):
        self.neo4j = Neo4j()

    def test_non_reserved_word_as_label(self):
        """Each non-reserved word should parse as a label in MATCH (n:WORD) RETURN n."""
        for word in self._NON_RESERVED_LABEL_WORDS:
            with self.subTest(word=word):
                query = f"MATCH (n:{word}) RETURN n"
                results = self.neo4j.parse(query)
                self.assertEqual(len(results), 1, f"Failed to parse: {query}")

    def test_non_reserved_word_round_trip(self):
        """Parse -> generate -> re-parse for representative non-reserved words."""
        representative = ["PRODUCT", "PROJECT", "ABSTRACT", "CATALOG", "PROCEDURE"]
        for word in representative:
            with self.subTest(word=word):
                query = f"MATCH (n:{word}) RETURN n"
                results = self.neo4j.parse(query)
                self.assertEqual(len(results), 1)
                generated = self.neo4j.generate(results[0])
                # Re-parse the generated output
                results2 = self.neo4j.parse(generated)
                self.assertEqual(len(results2), 1, f"Re-parse failed for: {generated}")
                # Label name preserved without backtick-quoting
                self.assertIn(word, generated)


# =============================================================================
# Modulus/power precedence safety tests
# =============================================================================


class TestModulusPowerPrecedence(unittest.TestCase):
    """Verify modulus/power generators parenthesise complex operands."""

    def setUp(self):
        self.neo4j = Neo4j()

    def _rt(self, query):
        results = self.neo4j.parse(query)
        self.assertEqual(len(results), 1, f"Parse failed: {query}")
        generated = self.neo4j.generate(results[0])
        # Re-parse to verify round-trip correctness
        results2 = self.neo4j.parse(generated)
        self.assertEqual(len(results2), 1, f"Re-parse failed: {generated}")
        return generated

    def test_grouped_addition_modulus(self):
        """``(10 + 3) % 4`` must keep parens around the addition."""
        gen = self._rt("RETURN (10 + 3) % 4")
        self.assertIn("(", gen)
        self.assertIn("%", gen)

    def test_grouped_multiply_power(self):
        """``(2 * 3) ^ 4`` must keep parens around the multiplication."""
        gen = self._rt("RETURN (2 * 3) ^ 4")
        self.assertIn("(", gen)
        self.assertIn("^", gen)

    def test_power_rhs_complex(self):
        """``2 ^ (3 + 1)`` must keep parens around addition in exponent."""
        gen = self._rt("RETURN 2 ^ (3 + 1)")
        self.assertIn("(", gen)
        self.assertIn("^", gen)

    def test_modulus_idempotent_round_trip(self):
        """``(n.x + n.y) % 2`` — idempotent parse→gen→re-parse."""
        gen = self._rt("MATCH (n) RETURN (n.x + n.y) % 2")
        self.assertIn("%", gen)
        # Idempotent: second round-trip produces same output
        results = self.neo4j.parse(gen)
        gen2 = self.neo4j.generate(results[0])
        self.assertEqual(gen, gen2)

    def test_complex_nve_dividend_gets_parens(self):
        """Programmatic ModulusExpression with multi-term NVE gets parens."""
        gen = self.neo4j.generator()
        nve_complex = ast.NumericValueExpression(
            base=ast.Term(base=ast.Factor(numeric_primary=ast.UnsignedNumericLiteral(value=10))),
            steps=[
                ast.NumericValueExpression._SignedTerm(
                    sign=ast.Sign.PLUS_SIGN,
                    term=ast.Term(
                        base=ast.Factor(numeric_primary=ast.UnsignedNumericLiteral(value=3))
                    ),
                )
            ],
        )
        nve_simple = ast.NumericValueExpression(
            base=ast.Term(base=ast.Factor(numeric_primary=ast.UnsignedNumericLiteral(value=4))),
        )
        mod = ast.ModulusExpression(
            numeric_value_expression_dividend=nve_complex,
            numeric_value_expression_divisor=nve_simple,
        )
        result = gen.dispatch(mod).render()
        self.assertEqual(result, "(10 + 3) % 4")

    def test_complex_nve_power_gets_parens(self):
        """Programmatic PowerFunction with multi-term NVE gets parens."""
        gen = self.neo4j.generator()
        nve_complex = ast.NumericValueExpression(
            base=ast.Term(
                base=ast.Factor(numeric_primary=ast.UnsignedNumericLiteral(value=2)),
                steps=[
                    ast.Term._MultiplicativeFactor(
                        operator=ast.MultiplicativeOperator.MULTIPLY,
                        factor=ast.Factor(numeric_primary=ast.UnsignedNumericLiteral(value=3)),
                    )
                ],
            ),
        )
        nve_simple = ast.NumericValueExpression(
            base=ast.Term(base=ast.Factor(numeric_primary=ast.UnsignedNumericLiteral(value=4))),
        )
        power = ast.PowerFunction(
            numeric_value_expression_base=nve_complex,
            numeric_value_expression_exponent=nve_simple,
        )
        result = gen.dispatch(power).render()
        self.assertEqual(result, "(2 * 3) ^ 4")

    def test_modulus_inside_power_gets_parens(self):
        """Programmatic ModulusExpression inside Factor as PowerFunction base gets parens."""
        gen = self.neo4j.generator()
        mod = ast.ModulusExpression(
            numeric_value_expression_dividend=ast.NumericValueExpression(
                base=ast.Term(
                    base=ast.Factor(numeric_primary=ast.UnsignedNumericLiteral(value=10))
                ),
            ),
            numeric_value_expression_divisor=ast.NumericValueExpression(
                base=ast.Term(base=ast.Factor(numeric_primary=ast.UnsignedNumericLiteral(value=3))),
            ),
        )
        nve_mod = ast.NumericValueExpression(
            base=ast.Term(base=ast.Factor(numeric_primary=mod)),
        )
        nve_exp = ast.NumericValueExpression(
            base=ast.Term(base=ast.Factor(numeric_primary=ast.UnsignedNumericLiteral(value=2))),
        )
        power = ast.PowerFunction(
            numeric_value_expression_base=nve_mod,
            numeric_value_expression_exponent=nve_exp,
        )
        result = gen.dispatch(power).render()
        self.assertEqual(result, "(10 % 3) ^ 2")

    def test_power_inside_modulus_no_parens(self):
        """PowerFunction inside ModulusExpression dividend needs no parens (^ binds tighter)."""
        gen = self.neo4j.generator()
        power = ast.PowerFunction(
            numeric_value_expression_base=ast.NumericValueExpression(
                base=ast.Term(base=ast.Factor(numeric_primary=ast.UnsignedNumericLiteral(value=2))),
            ),
            numeric_value_expression_exponent=ast.NumericValueExpression(
                base=ast.Term(base=ast.Factor(numeric_primary=ast.UnsignedNumericLiteral(value=3))),
            ),
        )
        nve_power = ast.NumericValueExpression(
            base=ast.Term(base=ast.Factor(numeric_primary=power)),
        )
        nve_divisor = ast.NumericValueExpression(
            base=ast.Term(base=ast.Factor(numeric_primary=ast.UnsignedNumericLiteral(value=4))),
        )
        mod = ast.ModulusExpression(
            numeric_value_expression_dividend=nve_power,
            numeric_value_expression_divisor=nve_divisor,
        )
        result = gen.dispatch(mod).render()
        self.assertEqual(result, "2 ^ 3 % 4")

    def test_power_precedence_roundtrip(self):
        """Power binds tighter than * / % + - in roundtrip parse-generate."""
        cases = [
            # ^ on RHS of lower-precedence ops (no parens needed)
            "2 * 3 ^ 4",
            "2 / 3 ^ 4",
            "2 + 3 ^ 4",
            "2 - 3 ^ 4",
            # mixed chains
            "1 + 2 * 3 ^ 4",
            "1 ^ 2 * 3 + 4",
            "1 + 2 ^ 3 * 4 + 5",
            "1 * 2 ^ 3 % 4",
            # explicit parens overriding natural precedence (must be preserved)
            "(2 + 3) ^ 4",
            "(2 * 3) ^ 4",
            "2 ^ (3 + 4)",
            "2 ^ (3 * 4)",
            "(2 + 3) * 4 ^ 5",
            "2 * (3 + 4) ^ 5",
            "(2 + 3) ^ (4 - 1)",
            "(2 % 3) ^ 4",
            "2 % (3 % 4)",
        ]
        for expr in cases:
            with self.subTest(expr=expr):
                gen = self._rt(f"RETURN {expr}")
                result = gen.split("RETURN ", 1)[1] if "RETURN " in gen else gen
                self.assertEqual(result, expr)


# =============================================================================
# Cypher string escape tests
# =============================================================================


class TestCypherStringEscaping(unittest.TestCase):
    """Verify Cypher string literal generator escapes special characters."""

    def setUp(self):
        self.neo4j = Neo4j()
        self._gen = self.neo4j.generator()

    def _gen_string(self, value: str) -> str:
        """Generate a Cypher string literal from a CharacterStringLiteral."""
        node = ast.CharacterStringLiteral(value=value)
        return self._gen.dispatch(node).render()

    def test_backslash(self):
        self.assertEqual(self._gen_string("a\\b"), "'a\\\\b'")

    def test_single_quote(self):
        self.assertEqual(self._gen_string("it's"), "'it\\'s'")

    def test_newline(self):
        self.assertEqual(self._gen_string("a\nb"), "'a\\nb'")

    def test_tab(self):
        self.assertEqual(self._gen_string("a\tb"), "'a\\tb'")

    def test_null_char(self):
        self.assertEqual(self._gen_string("a\x00b"), "'a\\0b'")

    def test_double_quote(self):
        """Double quotes pass through unescaped inside single-quoted strings."""
        self.assertEqual(self._gen_string('say "hi"'), "'say \"hi\"'")

    def test_non_printable_unicode_escape(self):
        """Non-printable chars not in escape map get \\uXXXX."""
        self.assertEqual(self._gen_string("a\x01b"), "'a\\u0001b'")

    def test_printable_passthrough(self):
        """Regular printable characters pass through unchanged."""
        self.assertEqual(self._gen_string("hello world"), "'hello world'")
