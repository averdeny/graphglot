"""Tests for literal type inference rules."""

from graphglot.ast import expressions as ast
from graphglot.dialect.base import Dialect
from graphglot.typing import TypeAnnotator, TypeKind


def _annotate(query: str) -> ast.Expression:
    """Parse and annotate a query, return the first expression."""
    d = Dialect.get_or_raise("ir")
    exprs = d.parse(query)
    TypeAnnotator().annotate(exprs[0])
    return exprs[0]


def _find_type(root, ast_type):
    """Find the first node of ast_type and return its resolved type."""
    node = root.find_first(ast_type)
    assert node is not None, f"No {ast_type.__name__} found"
    return node._resolved_type


class TestIntegerLiteral:
    def test_integer(self):
        root = _annotate("RETURN 42")
        t = _find_type(root, ast.UnsignedNumericLiteral)
        assert t.kind == TypeKind.INT

    def test_large_integer(self):
        root = _annotate("RETURN 999999")
        t = _find_type(root, ast.UnsignedNumericLiteral)
        assert t.kind == TypeKind.INT


class TestDecimalLiteral:
    def test_decimal(self):
        root = _annotate("RETURN 3.14")
        t = _find_type(root, ast.UnsignedNumericLiteral)
        assert t.kind == TypeKind.DECIMAL


class TestStringLiteral:
    def test_string(self):
        root = _annotate("RETURN 'hello'")
        t = _find_type(root, ast.CharacterStringLiteral)
        assert t.kind == TypeKind.STRING


class TestBooleanLiteral:
    def test_boolean(self):
        root = _annotate("RETURN TRUE")
        t = _find_type(root, ast.BooleanLiteral)
        assert t.kind == TypeKind.BOOLEAN


class TestNullLiteral:
    def test_null(self):
        root = _annotate("RETURN NULL")
        t = _find_type(root, ast.NullLiteral)
        assert t.kind == TypeKind.NULL


class TestListLiteral:
    def test_empty_list(self):
        root = _annotate("RETURN []")
        t = _find_type(root, ast.ListValueConstructorByEnumeration)
        assert t.kind == TypeKind.LIST

    def test_integer_list(self):
        root = _annotate("RETURN [1, 2, 3]")
        t = _find_type(root, ast.ListValueConstructorByEnumeration)
        assert t.kind == TypeKind.LIST
        assert t.element_type is not None
        assert t.element_type.kind == TypeKind.INT

    def test_string_list(self):
        root = _annotate("RETURN ['a', 'b']")
        t = _find_type(root, ast.ListValueConstructorByEnumeration)
        assert t.kind == TypeKind.LIST
        assert t.element_type is not None
        assert t.element_type.kind == TypeKind.STRING


class TestDateLiteral:
    def test_date(self):
        root = _annotate("RETURN DATE '2024-01-15'")
        t = _find_type(root, ast.DateLiteral)
        assert t.kind == TypeKind.DATE


class TestDurationLiteral:
    def test_duration(self):
        root = _annotate("RETURN DURATION 'P1Y2M'")
        t = _find_type(root, ast.DurationLiteral)
        assert t.kind == TypeKind.DURATION
