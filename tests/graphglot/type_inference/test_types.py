"""Tests for GqlType data structure."""

import pytest

from graphglot.typing.types import GqlType, TypeKind


class TestGqlTypeConstructors:
    def test_unknown(self):
        t = GqlType.unknown()
        assert t.kind == TypeKind.UNKNOWN
        assert t.is_unknown

    def test_error(self):
        t = GqlType.error()
        assert t.kind == TypeKind.ERROR
        assert t.is_error
        assert not t.nullable

    def test_boolean(self):
        t = GqlType.boolean()
        assert t.kind == TypeKind.BOOLEAN

    def test_string(self):
        t = GqlType.string()
        assert t.kind == TypeKind.STRING
        assert t.is_string

    def test_byte_string(self):
        t = GqlType.byte_string()
        assert t.kind == TypeKind.BYTE_STRING
        assert t.is_string

    def test_integer(self):
        t = GqlType.integer()
        assert t.kind == TypeKind.INT
        assert t.is_numeric

    def test_decimal(self):
        t = GqlType.decimal()
        assert t.kind == TypeKind.DECIMAL
        assert t.is_numeric

    def test_float(self):
        t = GqlType.float_()
        assert t.kind == TypeKind.FLOAT
        assert t.is_numeric

    def test_numeric(self):
        t = GqlType.numeric()
        assert t.kind == TypeKind.NUMERIC
        assert t.is_numeric

    def test_date(self):
        t = GqlType.date()
        assert t.kind == TypeKind.DATE
        assert t.is_temporal

    def test_time(self):
        t = GqlType.time()
        assert t.kind == TypeKind.TIME
        assert t.is_temporal

    def test_datetime(self):
        t = GqlType.datetime_()
        assert t.kind == TypeKind.DATETIME
        assert t.is_temporal

    def test_local_datetime(self):
        t = GqlType.local_datetime()
        assert t.kind == TypeKind.LOCAL_DATETIME
        assert t.is_temporal

    def test_local_time(self):
        t = GqlType.local_time()
        assert t.kind == TypeKind.LOCAL_TIME
        assert t.is_temporal

    def test_duration(self):
        t = GqlType.duration()
        assert t.kind == TypeKind.DURATION
        assert not t.is_temporal  # Duration is not a temporal instant

    def test_null(self):
        t = GqlType.null()
        assert t.kind == TypeKind.NULL

    def test_node(self):
        t = GqlType.node()
        assert t.kind == TypeKind.NODE
        assert t.labels == frozenset()

    def test_node_with_labels(self):
        t = GqlType.node(frozenset({"Person", "Employee"}))
        assert t.kind == TypeKind.NODE
        assert t.labels == frozenset({"Person", "Employee"})

    def test_edge(self):
        t = GqlType.edge()
        assert t.kind == TypeKind.EDGE

    def test_path(self):
        t = GqlType.path()
        assert t.kind == TypeKind.PATH

    def test_list_no_element(self):
        t = GqlType.list_()
        assert t.kind == TypeKind.LIST
        assert t.element_type is None

    def test_list_with_element(self):
        t = GqlType.list_(GqlType.integer())
        assert t.kind == TypeKind.LIST
        assert t.element_type == GqlType.integer()

    def test_record(self):
        t = GqlType.record()
        assert t.kind == TypeKind.RECORD


class TestGqlTypeUnion:
    def test_single_member_returns_member(self):
        t = GqlType.union(GqlType.string())
        assert t == GqlType.string()

    def test_two_members(self):
        t = GqlType.union(GqlType.string(), GqlType.integer())
        assert t.is_union
        assert t.union_members == (GqlType.string(), GqlType.integer())

    def test_flattens_nested(self):
        inner = GqlType.union(GqlType.string(), GqlType.integer())
        outer = GqlType.union(inner, GqlType.boolean())
        assert outer.union_members == (GqlType.string(), GqlType.integer(), GqlType.boolean())

    def test_deduplicates(self):
        t = GqlType.union(GqlType.string(), GqlType.string(), GqlType.integer())
        assert t.union_members == (GqlType.string(), GqlType.integer())


class TestGqlTypeEquality:
    def test_same_kind_equal(self):
        assert GqlType.string() == GqlType.string()

    def test_different_kind_not_equal(self):
        assert GqlType.string() != GqlType.integer()

    def test_frozen(self):
        t = GqlType.string()
        with pytest.raises(AttributeError):
            t.kind = TypeKind.INT  # type: ignore[misc]

    def test_hashable(self):
        s = {GqlType.string(), GqlType.integer(), GqlType.string()}
        assert len(s) == 2


class TestGqlTypeComparability:
    """Tests for is_comparable_with method."""

    def test_same_kind_comparable(self):
        assert GqlType.string().is_comparable_with(GqlType.string())

    def test_numeric_subtypes_comparable(self):
        assert GqlType.integer().is_comparable_with(GqlType.float_())
        assert GqlType.decimal().is_comparable_with(GqlType.numeric())
        assert GqlType.float_().is_comparable_with(GqlType.integer())

    def test_temporal_types_comparable(self):
        assert GqlType.date().is_comparable_with(GqlType.datetime_())
        assert GqlType.time().is_comparable_with(GqlType.local_time())

    def test_string_subtypes_comparable(self):
        assert GqlType.string().is_comparable_with(GqlType.byte_string())

    def test_incompatible_types(self):
        assert not GqlType.string().is_comparable_with(GqlType.integer())
        assert not GqlType.boolean().is_comparable_with(GqlType.float_())
        assert not GqlType.node().is_comparable_with(GqlType.string())
        assert not GqlType.path().is_comparable_with(GqlType.integer())

    def test_unknown_is_conservative(self):
        assert GqlType.unknown().is_comparable_with(GqlType.string())
        assert GqlType.integer().is_comparable_with(GqlType.unknown())

    def test_null_is_universally_comparable(self):
        assert GqlType.null().is_comparable_with(GqlType.string())
        assert GqlType.integer().is_comparable_with(GqlType.null())

    def test_any_is_universally_comparable(self):
        assert GqlType.any_().is_comparable_with(GqlType.string())
        assert GqlType.integer().is_comparable_with(GqlType.any_())

    def test_error_is_conservative(self):
        assert GqlType.error().is_comparable_with(GqlType.string())

    def test_duration_not_comparable_to_temporal(self):
        """Duration is NOT a temporal instant — not comparable to DATE/TIME."""
        assert not GqlType.duration().is_comparable_with(GqlType.date())
        assert GqlType.duration().is_comparable_with(GqlType.duration())

    def test_union_comparable_if_any_member_matches(self):
        union = GqlType.union(GqlType.string(), GqlType.integer())
        assert union.is_comparable_with(GqlType.string())
        assert union.is_comparable_with(GqlType.integer())
        assert not union.is_comparable_with(GqlType.boolean())

    def test_graph_not_comparable_to_node(self):
        assert not GqlType.graph().is_comparable_with(GqlType.node())

    def test_element_types_not_cross_comparable(self):
        """NODE, EDGE, PATH are not mutually comparable."""
        assert not GqlType.node().is_comparable_with(GqlType.edge())
        assert not GqlType.node().is_comparable_with(GqlType.path())
        assert not GqlType.edge().is_comparable_with(GqlType.path())


class TestGqlTypeRepr:
    def test_simple(self):
        assert "string" in repr(GqlType.string())

    def test_list_element(self):
        assert "int" in repr(GqlType.list_(GqlType.integer()))

    def test_union(self):
        t = GqlType.union(GqlType.string(), GqlType.integer())
        r = repr(t)
        assert "string" in r
        assert "int" in r
