"""Tests for operator type inference rules."""

from graphglot.ast import expressions as ast
from graphglot.dialect.base import Dialect
from graphglot.typing import TypeAnnotator, TypeKind


def _annotate(query: str) -> ast.Expression:
    d = Dialect.get_or_raise("ir")
    exprs = d.parse(query)
    TypeAnnotator().annotate(exprs[0])
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

    def test_predicate_types(self):
        """NullPredicate returns BOOLEAN."""
        root = _annotate("MATCH (n) WHERE n.name IS NOT NULL RETURN n")
        np = root.find_first(ast.NullPredicate)
        assert np._resolved_type.kind == TypeKind.BOOLEAN
