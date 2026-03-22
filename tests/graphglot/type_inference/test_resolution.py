"""Tests for ambiguous expression resolution."""

import pytest

from graphglot.ast import expressions as ast
from graphglot.dialect.base import Dialect
from graphglot.typing import ExternalContext, GqlType, TypeAnnotator, TypeKind


def _annotate(query: str, **kwargs) -> ast.Expression:
    d = Dialect.get_or_raise("ir")
    exprs = d.parse(query)
    TypeAnnotator(**kwargs).annotate(exprs[0])
    return exprs[0]


class TestConcatenationResolution:
    def test_string_concat_known(self):
        """'a' || 'b' should resolve to STRING."""
        root = _annotate("RETURN 'a' || 'b'")
        # May parse as CharacterStringValueExpression directly if both are strings
        # or as ConcatenationValueExpression if ambiguous
        csve = root.find_first(ast.CharacterStringValueExpression)
        cve = root.find_first(ast.ConcatenationValueExpression)
        if csve:
            assert csve._resolved_type.kind == TypeKind.STRING
        elif cve:
            assert cve._resolved_type.kind == TypeKind.STRING

    def test_ambiguous_concat(self):
        """a || b with unknown operands produces a union type."""
        root = _annotate("MATCH (n) RETURN n.x || n.y")
        cve = root.find_first(ast.ConcatenationValueExpression)
        if cve:
            t = cve._resolved_type
            # Should be a union of STRING, LIST, PATH
            assert t.is_union or t.kind in (TypeKind.STRING, TypeKind.LIST, TypeKind.PATH)

    def test_path_concat_resolved(self):
        """p || q with PATH operands should resolve to PATH."""
        root = _annotate("MATCH p = (a)-[r]->(b), q = (c)-[s]->(d) RETURN p || q")
        cve = root.find_first(ast.ConcatenationValueExpression)
        assert cve is not None
        assert cve._resolved_type.kind == TypeKind.PATH

    def test_string_concat_with_context(self):
        """n.name || n.name with STRING property context should resolve to STRING."""
        ctx = ExternalContext(property_types={("Person", "name"): GqlType.string()})
        root = _annotate("MATCH (n:Person) RETURN n.name || n.name", external_context=ctx)
        cve = root.find_first(ast.ConcatenationValueExpression)
        assert cve is not None
        assert cve._resolved_type.kind == TypeKind.STRING

    def test_byte_string_concat_with_context(self):
        """BYTE_STRING property context should resolve to BYTE_STRING."""
        ctx = ExternalContext(property_types={("Blob", "payload"): GqlType.byte_string()})
        root = _annotate("MATCH (n:Blob) RETURN n.payload || n.payload", external_context=ctx)
        cve = root.find_first(ast.ConcatenationValueExpression)
        assert cve is not None
        assert cve._resolved_type.kind == TypeKind.BYTE_STRING

    def test_mixed_types_stay_unknown(self):
        """path || string should stay unknown (operands disagree)."""
        ctx = ExternalContext(
            property_types={
                ("A", "p"): GqlType.path(),
                ("A", "s"): GqlType.string(),
            }
        )
        root = _annotate("MATCH (n:A) RETURN n.p || n.s", external_context=ctx)
        cve = root.find_first(ast.ConcatenationValueExpression)
        assert cve is not None
        assert cve._resolved_type.is_unknown, (
            f"mixed path||string should be unknown, got {cve._resolved_type!r}"
        )

    def test_path_concat_node_returns_unknown(self):
        """p || n where n is a NODE should return unknown (NODE not concat-compatible)."""
        root = _annotate("MATCH p = (a)-[r]->(b), (n) RETURN p || n")
        cve = root.find_first(ast.ConcatenationValueExpression)
        assert cve is not None
        assert cve._resolved_type.is_unknown, (
            f"PATH || NODE should be unknown, got {cve._resolved_type!r}"
        )

    def test_node_concat_node_returns_unknown(self):
        """n || m where both are NODEs should return unknown (NODE not concat-compatible)."""
        root = _annotate("MATCH (n), (m) RETURN n || m")
        cve = root.find_first(ast.ConcatenationValueExpression)
        assert cve is not None
        assert cve._resolved_type.is_unknown, (
            f"NODE || NODE should be unknown, got {cve._resolved_type!r}"
        )


class TestArithmeticResolution:
    def test_numeric_arithmetic_known(self):
        """1 + 2 should resolve to numeric."""
        root = _annotate("RETURN 1 + 2")
        nve = root.find_first(ast.NumericValueExpression)
        ave = root.find_first(ast.ArithmeticValueExpression)
        if nve:
            assert nve._resolved_type.is_numeric
        elif ave:
            assert ave._resolved_type.is_numeric

    def test_ambiguous_arithmetic(self):
        """n.x + n.y with unknown operands may produce union or unknown."""
        root = _annotate("MATCH (n) RETURN n.x + n.y")
        # Could be ArithmeticValueExpression if ambiguous
        ave = root.find_first(ast.ArithmeticValueExpression)
        if ave:
            t = ave._resolved_type
            assert t.is_union or t.is_numeric or t.is_unknown

    def test_bare_property_not_narrowed_to_arithmetic(self):
        """n.name with no operators should stay unknown, not become (numeric | duration)."""
        root = _annotate("MATCH (n) RETURN n.name")
        ri = next(root.find_all(ast.ReturnItem))
        t = ri.aggregating_value_expression._resolved_type
        assert t is not None
        assert t.is_unknown, f"expected unknown, got {t!r}"

    def test_temporal_propagates_through_arithmetic_term(self):
        """DATE property should propagate through ArithmeticTerm (not become UNKNOWN)."""
        ctx = ExternalContext(property_types={("Ev", "d"): GqlType.date()})
        root = _annotate("MATCH (n:Ev) RETURN n.d", external_context=ctx)
        at = root.find_first(ast.ArithmeticTerm)
        assert at is not None
        assert at._resolved_type.kind == TypeKind.DATE

    @pytest.mark.parametrize(
        "prop,gql_type,expected_kind",
        [
            ("d", GqlType.date(), TypeKind.DATE),
            ("t", GqlType.time(), TypeKind.TIME),
            ("ts", GqlType.datetime_(), TypeKind.DATETIME),
            ("ldt", GqlType.local_datetime(), TypeKind.LOCAL_DATETIME),
            ("lt", GqlType.local_time(), TypeKind.LOCAL_TIME),
        ],
        ids=["DATE", "TIME", "DATETIME", "LOCAL_DATETIME", "LOCAL_TIME"],
    )
    def test_temporal_base_propagates_through_addition(self, prop, gql_type, expected_kind):
        """Temporal base + unknown step should preserve the temporal type."""
        ctx = ExternalContext(property_types={("Ev", prop): gql_type})
        root = _annotate(f"MATCH (n:Ev) RETURN n.{prop} + n.x", external_context=ctx)
        ave = root.find_first(ast.ArithmeticValueExpression)
        assert ave is not None
        assert ave._resolved_type.kind == expected_kind

    def test_temporal_in_step_propagates(self):
        """UNKNOWN + DATE should resolve to DATE via step type extraction."""
        ctx = ExternalContext(property_types={("Ev", "d"): GqlType.date()})
        root = _annotate("MATCH (n:Ev) RETURN n.x + n.d", external_context=ctx)
        ave = root.find_first(ast.ArithmeticValueExpression)
        assert ave is not None
        assert ave._resolved_type.kind == TypeKind.DATE

    def test_numeric_in_step_propagates(self):
        """UNKNOWN + INT should resolve to numeric via step type extraction."""
        ctx = ExternalContext(property_types={("Ev", "x"): GqlType(kind=TypeKind.INT)})
        root = _annotate("MATCH (n:Ev) RETURN n.y + n.x", external_context=ctx)
        ave = root.find_first(ast.ArithmeticValueExpression)
        assert ave is not None
        assert ave._resolved_type.is_numeric

    def test_duration_in_step_propagates(self):
        """UNKNOWN + DURATION should resolve to duration via step type extraction."""
        ctx = ExternalContext(property_types={("Ev", "dur"): GqlType.duration()})
        root = _annotate("MATCH (n:Ev) RETURN n.y + n.dur", external_context=ctx)
        ave = root.find_first(ast.ArithmeticValueExpression)
        assert ave is not None
        assert ave._resolved_type.kind == TypeKind.DURATION

    def test_unknown_arithmetic_union_contains_all_temporal_kinds(self):
        """Unknown arithmetic union should contain all 5 temporal kinds."""
        root = _annotate("MATCH (n) RETURN n.x + n.y")
        ave = root.find_first(ast.ArithmeticValueExpression)
        assert ave is not None
        t = ave._resolved_type
        assert t.union_members is not None
        temporal_kinds = {m.kind for m in t.union_members if m.is_temporal}
        assert temporal_kinds == {
            TypeKind.DATE,
            TypeKind.TIME,
            TypeKind.DATETIME,
            TypeKind.LOCAL_DATETIME,
            TypeKind.LOCAL_TIME,
        }

    def test_unknown_arithmetic_comparable_with_numeric(self):
        """Unknown arithmetic should still be comparable with numeric."""
        root = _annotate("MATCH (n) RETURN n.x + n.y")
        ave = root.find_first(ast.ArithmeticValueExpression)
        assert ave is not None
        assert ave._resolved_type.is_comparable_with(GqlType.numeric())

    def test_unknown_arithmetic_comparable_with_duration(self):
        """Unknown arithmetic should still be comparable with duration."""
        root = _annotate("MATCH (n) RETURN n.x + n.y")
        ave = root.find_first(ast.ArithmeticValueExpression)
        assert ave is not None
        assert ave._resolved_type.is_comparable_with(GqlType.duration())

    def test_unknown_arithmetic_not_comparable_with_string(self):
        """Unknown arithmetic should NOT be comparable with string (union isn't too broad)."""
        root = _annotate("MATCH (n) RETURN n.x + n.y")
        ave = root.find_first(ast.ArithmeticValueExpression)
        assert ave is not None
        assert not ave._resolved_type.is_comparable_with(GqlType.string())

    def test_temporal_multiply_returns_unknown(self):
        """DATE * 2 should resolve to UNKNOWN (temporal types have no multiplicative semantics)."""
        ctx = ExternalContext(property_types={("Ev", "d"): GqlType.date()})
        root = _annotate("MATCH (n:Ev) RETURN n.d * 2", external_context=ctx)
        at = root.find_first(ast.ArithmeticTerm)
        assert at is not None
        assert at.steps, "expected multiplicative steps"
        assert at._resolved_type.is_unknown

    def test_duration_multiply_returns_duration(self):
        """DURATION * 2 should resolve to DURATION (scaling a duration is valid)."""
        ctx = ExternalContext(property_types={("Ev", "dur"): GqlType.duration()})
        root = _annotate("MATCH (n:Ev) RETURN n.dur * 2", external_context=ctx)
        at = root.find_first(ast.ArithmeticTerm)
        assert at is not None
        assert at.steps, "expected multiplicative steps"
        assert at._resolved_type.kind == TypeKind.DURATION

    def test_path_plus_int_returns_unknown(self):
        """MATCH p = ... RETURN p + 1 → AVE should be unknown (PATH not arithmetic)."""
        root = _annotate("MATCH p = (a)-[r]->(b) RETURN p + 1")
        ave = root.find_first(ast.ArithmeticValueExpression)
        assert ave is not None
        assert ave._resolved_type.is_unknown, (
            f"PATH + INT should be unknown, got {ave._resolved_type!r}"
        )

    def test_string_plus_int_returns_unknown(self):
        """STRING + INT → AVE should be unknown."""
        ctx = ExternalContext(
            property_types={("T", "s"): GqlType.string(), ("T", "x"): GqlType(kind=TypeKind.INT)}
        )
        root = _annotate("MATCH (n:T) RETURN n.s + n.x", external_context=ctx)
        ave = root.find_first(ast.ArithmeticValueExpression)
        assert ave is not None
        assert ave._resolved_type.is_unknown

    def test_int_plus_string_returns_unknown(self):
        """INT + STRING → AVE should be unknown (string step)."""
        ctx = ExternalContext(
            property_types={("T", "x"): GqlType(kind=TypeKind.INT), ("T", "s"): GqlType.string()}
        )
        root = _annotate("MATCH (n:T) RETURN n.x + n.s", external_context=ctx)
        ave = root.find_first(ast.ArithmeticValueExpression)
        assert ave is not None
        assert ave._resolved_type.is_unknown

    def test_int_times_string_returns_unknown(self):
        """INT * STRING → AT should be unknown."""
        ctx = ExternalContext(
            property_types={("T", "x"): GqlType(kind=TypeKind.INT), ("T", "s"): GqlType.string()}
        )
        root = _annotate("MATCH (n:T) RETURN n.x * n.s", external_context=ctx)
        at = root.find_first(ast.ArithmeticTerm)
        assert at is not None
        assert at.steps, "expected multiplicative steps"
        assert at._resolved_type.is_unknown

    def test_nested_numeric_times_string_returns_unknown(self):
        """(INT + INT) * STRING → outer AT should be unknown."""
        ctx = ExternalContext(
            property_types={
                ("T", "x"): GqlType(kind=TypeKind.INT),
                ("T", "y"): GqlType(kind=TypeKind.INT),
                ("T", "s"): GqlType.string(),
            }
        )
        root = _annotate("MATCH (n:T) RETURN (n.x + n.y) * n.s", external_context=ctx)
        at = root.find_first(ast.ArithmeticTerm)
        assert at is not None
        assert at.steps, "expected multiplicative steps"
        assert at._resolved_type.is_unknown

    def test_string_plus_nested_numeric_returns_unknown(self):
        """STRING + INT*INT → AVE should be unknown (string base)."""
        ctx = ExternalContext(
            property_types={
                ("T", "s"): GqlType.string(),
                ("T", "x"): GqlType(kind=TypeKind.INT),
                ("T", "y"): GqlType(kind=TypeKind.INT),
            }
        )
        root = _annotate("MATCH (n:T) RETURN n.s + n.x * n.y", external_context=ctx)
        ave = root.find_first(ast.ArithmeticValueExpression)
        assert ave is not None
        assert ave._resolved_type.is_unknown

    def test_unknown_plus_int_still_numeric(self):
        """UNKNOWN + INT → should still resolve to numeric (regression guard)."""
        ctx = ExternalContext(property_types={("T", "x"): GqlType(kind=TypeKind.INT)})
        root = _annotate("MATCH (n:T) RETURN n.y + n.x", external_context=ctx)
        ave = root.find_first(ast.ArithmeticValueExpression)
        assert ave is not None
        assert ave._resolved_type.is_numeric

    def test_date_plus_duration_still_temporal(self):
        """DATE + DURATION → should still resolve to DATE (regression guard)."""
        ctx = ExternalContext(
            property_types={("Ev", "d"): GqlType.date(), ("Ev", "dur"): GqlType.duration()}
        )
        root = _annotate("MATCH (n:Ev) RETURN n.d + n.dur", external_context=ctx)
        ave = root.find_first(ast.ArithmeticValueExpression)
        assert ave is not None
        assert ave._resolved_type.kind == TypeKind.DATE

    def test_temporal_bare_property_passthrough(self):
        """DATE property with no operators should resolve to DATE at ReturnItem level."""
        ctx = ExternalContext(property_types={("Ev", "d"): GqlType.date()})
        root = _annotate("MATCH (n:Ev) RETURN n.d", external_context=ctx)
        ri = next(root.find_all(ast.ReturnItem))
        t = ri.aggregating_value_expression._resolved_type
        assert t is not None
        assert t.kind == TypeKind.DATE
