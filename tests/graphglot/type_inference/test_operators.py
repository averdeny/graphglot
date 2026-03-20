"""Tests for operator type inference rules."""

from graphglot.ast import expressions as ast
from graphglot.dialect.base import Dialect
from graphglot.typing import ExternalContext, GqlType, TypeAnnotator, TypeKind


def _annotate(query: str, **kwargs) -> ast.Expression:
    d = Dialect.get_or_raise("ir")
    exprs = d.parse(query)
    TypeAnnotator(**kwargs).annotate(exprs[0])
    return exprs[0]


class TestBooleanExpressions:
    def test_boolean_not(self):
        root = _annotate("RETURN NOT TRUE")
        bf = root.find_first(ast.BooleanFactor)
        assert bf._resolved_type.kind == TypeKind.BOOLEAN

    def test_boolean_test(self):
        root = _annotate("MATCH (n) WHERE TRUE RETURN n")
        bt = root.find_first(ast.BooleanTest)
        assert bt._resolved_type.kind == TypeKind.BOOLEAN


class TestComparisonPredicate:
    def test_equals(self):
        root = _annotate("MATCH (n) WHERE n.age = 30 RETURN n")
        cp = root.find_first(ast.ComparisonPredicate)
        assert cp._resolved_type.kind == TypeKind.BOOLEAN


class TestNumericExpressions:
    def test_addition(self):
        """1 + 2 parses as ArithmeticValueExpression (ambiguous at parse time)."""
        root = _annotate("RETURN 1 + 2")
        ave = root.find_first(ast.ArithmeticValueExpression)
        assert ave is not None
        assert ave._resolved_type.is_numeric

    def test_multiplication(self):
        """3 * 4 parses as ArithmeticValueExpression (ambiguous at parse time)."""
        root = _annotate("RETURN 3 * 4")
        ave = root.find_first(ast.ArithmeticValueExpression)
        assert ave is not None
        assert ave._resolved_type.is_numeric


class TestStringExpressions:
    def test_string_concat(self):
        root = _annotate("RETURN 'a' || 'b'")
        csve = root.find_first(ast.CharacterStringValueExpression)
        if csve:
            assert csve._resolved_type.kind == TypeKind.STRING


class TestPathExpressions:
    def test_path_value_expression(self):
        root = _annotate("MATCH p = (a)-[]->(b) RETURN p")
        pvd = root.find_first(ast.PathVariableDeclaration)
        assert pvd._resolved_type.kind == TypeKind.PATH


class TestParenthesizedExpression:
    def test_parenthesized_preserves_type(self):
        root = _annotate("RETURN (42)")
        pve = root.find_first(ast.ParenthesizedValueExpression)
        if pve:
            assert pve._resolved_type.is_numeric


class TestPropertyReference:
    def test_unknown_property(self):
        root = _annotate("MATCH (n) RETURN n.name")
        pr = root.find_first(ast.PropertyReference)
        assert pr._resolved_type.is_unknown

    def test_property_with_external_context(self):
        ctx = ExternalContext(property_types={("Person", "name"): GqlType.string()})
        root = _annotate("MATCH (n:Person) RETURN n.name", external_context=ctx)
        pr = root.find_first(ast.PropertyReference)
        assert pr._resolved_type.kind == TypeKind.STRING

    def test_multiple_properties_with_context(self):
        ctx = ExternalContext(
            property_types={
                ("Person", "name"): GqlType.string(),
                ("Person", "age"): GqlType.integer(),
            }
        )
        root = _annotate("MATCH (n:Person) RETURN n.name, n.age", external_context=ctx)
        prs = list(root.find_all(ast.PropertyReference))
        types_by_name = {pr.property_name[0].identifier.name: pr._resolved_type for pr in prs}
        assert types_by_name["name"].kind == TypeKind.STRING
        assert types_by_name["age"].kind == TypeKind.INT

    def test_edge_property_with_context(self):
        ctx = ExternalContext(property_types={("KNOWS", "since"): GqlType.integer()})
        root = _annotate("MATCH ()-[r:KNOWS]->() RETURN r.since", external_context=ctx)
        pr = root.find_first(ast.PropertyReference)
        assert pr._resolved_type.kind == TypeKind.INT

    def test_property_source_has_node_type(self):
        """BVR propagation: property source should have NODE type even without ExternalContext."""
        root = _annotate("MATCH (n:Person) RETURN n.name")
        pr = root.find_first(ast.PropertyReference)
        assert pr._resolved_type.is_unknown  # no external context
        assert pr.property_source._resolved_type.kind == TypeKind.NODE

    def test_predicate_types(self):
        """NullPredicate returns BOOLEAN."""
        root = _annotate("MATCH (n) WHERE n.name IS NOT NULL RETURN n")
        np = root.find_first(ast.NullPredicate)
        assert np._resolved_type.kind == TypeKind.BOOLEAN
