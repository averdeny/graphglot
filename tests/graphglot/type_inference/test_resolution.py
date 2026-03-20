"""Tests for ambiguous expression resolution."""

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
