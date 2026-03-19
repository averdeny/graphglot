"""Tests for CAST type inference and from_ast_value_type."""

from graphglot.ast import expressions as ast
from graphglot.dialect.base import Dialect
from graphglot.typing import TypeAnnotator, TypeKind
from graphglot.typing.rules.cast import from_ast_value_type


def _annotate(query: str) -> ast.Expression:
    d = Dialect.get_or_raise("ir")
    exprs = d.parse(query)
    TypeAnnotator().annotate(exprs[0])
    return exprs[0]


class TestFromAstValueType:
    def test_path_type(self):
        t = from_ast_value_type(ast.PathValueType(not_null=False))
        assert t.kind == TypeKind.PATH

    def test_cast_to_list_via_query(self):
        """Test LIST type resolution through a CAST query."""
        root = _annotate("RETURN CAST(NULL AS LIST<STRING>)")
        cs = root.find_first(ast.CastSpecification)
        assert cs._resolved_type.kind == TypeKind.LIST


class TestCastExpression:
    def test_cast_to_string(self):
        root = _annotate("RETURN CAST(42 AS STRING)")
        cs = root.find_first(ast.CastSpecification)
        assert cs._resolved_type.kind == TypeKind.STRING

    def test_cast_to_boolean(self):
        root = _annotate("RETURN CAST('true' AS BOOLEAN)")
        cs = root.find_first(ast.CastSpecification)
        assert cs._resolved_type.kind == TypeKind.BOOLEAN

    def test_cast_to_int(self):
        root = _annotate("RETURN CAST('42' AS INT)")
        cs = root.find_first(ast.CastSpecification)
        assert cs._resolved_type.kind == TypeKind.INT

    def test_cast_to_float(self):
        root = _annotate("RETURN CAST(42 AS FLOAT64)")
        cs = root.find_first(ast.CastSpecification)
        assert cs._resolved_type.kind == TypeKind.FLOAT
