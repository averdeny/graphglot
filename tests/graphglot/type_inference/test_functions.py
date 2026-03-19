"""Tests for function type inference rules."""

from graphglot.ast import expressions as ast
from graphglot.dialect.base import Dialect
from graphglot.typing import TypeAnnotator, TypeKind


def _annotate(query: str) -> ast.Expression:
    d = Dialect.get_or_raise("ir")
    exprs = d.parse(query)
    TypeAnnotator().annotate(exprs[0])
    return exprs[0]


class TestAggregateFunctions:
    def test_count_star(self):
        root = _annotate("MATCH (n) RETURN COUNT(*)")
        agg = root.find_first(ast.AggregateFunction)
        assert agg._resolved_type.kind == TypeKind.INT

    def test_count_expr(self):
        root = _annotate("MATCH (n) RETURN COUNT(n)")
        agg = root.find_first(ast.AggregateFunction)
        assert agg._resolved_type.kind == TypeKind.INT

    def test_sum(self):
        root = _annotate("MATCH (n) RETURN SUM(n.age)")
        agg = root.find_first(ast.AggregateFunction)
        # SUM returns numeric (arg type unknown since n.age is UNKNOWN)
        assert agg._resolved_type.is_numeric or agg._resolved_type.is_unknown

    def test_avg(self):
        root = _annotate("MATCH (n) RETURN AVG(n.age)")
        agg = root.find_first(ast.AggregateFunction)
        assert agg._resolved_type.is_numeric or agg._resolved_type.is_unknown


class TestNumericFunctions:
    def test_floor(self):
        root = _annotate("RETURN FLOOR(3.7)")
        ff = root.find_first(ast.FloorFunction)
        assert ff._resolved_type.kind == TypeKind.INT

    def test_ceiling(self):
        root = _annotate("RETURN CEILING(3.2)")
        cf = root.find_first(ast.CeilingFunction)
        assert cf._resolved_type.kind == TypeKind.INT


class TestStringFunctions:
    def test_upper(self):
        root = _annotate("RETURN UPPER('hello')")
        fold = root.find_first(ast.Fold)
        assert fold._resolved_type.kind == TypeKind.STRING

    def test_lower(self):
        root = _annotate("RETURN LOWER('HELLO')")
        fold = root.find_first(ast.Fold)
        assert fold._resolved_type.kind == TypeKind.STRING


class TestTemporalFunctions:
    def test_current_date(self):
        root = _annotate("RETURN CURRENT_DATE")
        df = root.find_first(ast.DateFunction)
        assert df._resolved_type.kind == TypeKind.DATE
