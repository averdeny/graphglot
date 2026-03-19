"""Tests for scope.py — is_variable_reference with promoted AST wrappers."""

from __future__ import annotations

import typing as t
import unittest

from graphglot import ast
from graphglot.scope import extract_variable_references, is_variable_reference


class TestIsVariableReference(unittest.TestCase):
    """Test the simplified is_variable_reference based on isinstance check."""

    @staticmethod
    def _make_ident(name: str = "x") -> ast.Identifier:
        return ast.Identifier(name=name)

    def test_positive_inside_binding_variable_reference(self):
        """Identifier inside BindingVariableReference → True."""
        ident = self._make_ident()
        bvr = ast.BindingVariableReference(binding_variable=ident)
        # _parent is set by Pydantic during construction
        assert bvr.binding_variable is ident
        self.assertTrue(is_variable_reference(ident))

    def test_negative_inside_property_name(self):
        """Identifier inside PropertyName → False."""
        ident = self._make_ident()
        ast.PropertyName(identifier=ident)
        self.assertFalse(is_variable_reference(ident))

    def test_negative_inside_label_name(self):
        """Identifier inside LabelName → False."""
        ident = self._make_ident()
        ast.LabelName(identifier=ident)
        self.assertFalse(is_variable_reference(ident))

    def test_negative_inside_element_variable_declaration(self):
        """Identifier inside ElementVariableDeclaration → False."""
        ident = self._make_ident()
        ast.ElementVariableDeclaration(temp=False, element_variable=ident)
        self.assertFalse(is_variable_reference(ident))

    def test_negative_inside_return_item_alias(self):
        """Identifier inside ReturnItemAlias → False."""
        ident = self._make_ident()
        ast.ReturnItemAlias(identifier=ident)
        self.assertFalse(is_variable_reference(ident))

    def test_negative_standalone(self):
        """Standalone Identifier (no parent) → False (safe default)."""
        ident = self._make_ident()
        self.assertFalse(is_variable_reference(ident))


class TestExtractVariableReferencesViaParser(unittest.TestCase):
    """Integration tests — extract references from parsed queries."""

    def _parse(self, query: str) -> ast.Expression:
        from graphglot.dialect import Dialect

        d = Dialect()
        return d.parse(query)[0]

    def test_match_return_references(self):
        """MATCH (n) RETURN n → n is both declared and referenced."""
        tree = self._parse("MATCH (n) RETURN n")
        refs = extract_variable_references(tree)
        self.assertIn("n", refs)

    def test_property_name_not_reference(self):
        """MATCH (n) RETURN n.name → 'name' is NOT a variable reference."""
        tree = self._parse("MATCH (n) RETURN n.name")
        refs = extract_variable_references(tree)
        self.assertNotIn("name", refs)
        self.assertIn("n", refs)

    def test_label_not_reference(self):
        """MATCH (n:Person) RETURN n → 'Person' is NOT a variable reference."""
        tree = self._parse("MATCH (n:Person) RETURN n")
        refs = extract_variable_references(tree)
        self.assertNotIn("Person", refs)
        self.assertIn("n", refs)

    def test_alias_not_reference(self):
        """MATCH (n) RETURN n.name AS alias → 'alias' is NOT a variable reference."""
        tree = self._parse("MATCH (n) RETURN n.name AS alias")
        refs = extract_variable_references(tree)
        self.assertNotIn("alias", refs)


class TestSubqueryBoundaryCompleteness(unittest.TestCase):
    """Structural test: every braced Nested* AST class must be a scope boundary."""

    # Nested* classes that are NOT subquery scope boundaries:
    # - NestedGraphTypeSpecification: DDL type definition, no variable scope
    _NON_BOUNDARY_NESTED: t.ClassVar[set[str]] = {
        "NestedGraphTypeSpecification",
    }

    def test_all_nested_braced_types_are_boundaries(self):
        """Every Nested* class wrapping { ... } should be in SUBQUERY_BOUNDARY_TYPES.

        Focused*Nested* wrappers (USE graph + nested spec) contain an inner
        Nested* type that the parent-chain walk hits first, so they are
        excluded.  Other Focused* classes (e.g. FocusedLinearQueryStatement)
        are graph-switching wrappers, not braced subquery boundaries.
        """
        import inspect

        from graphglot.scope import SUBQUERY_BOUNDARY_TYPES

        missing = []
        for name, _obj in inspect.getmembers(ast):
            if not name.startswith("Nested"):
                continue
            if name in self._NON_BOUNDARY_NESTED:
                continue
            raw = getattr(ast, name)
            if not inspect.isclass(raw):
                # TypeAlias — target is already covered
                continue
            if not issubclass(raw, ast.Expression):
                continue
            if raw in SUBQUERY_BOUNDARY_TYPES:
                continue
            missing.append(name)

        self.assertEqual(
            missing,
            [],
            f"Nested/Focused AST types not in SUBQUERY_BOUNDARY_TYPES: {missing}. "
            f"Add them to the tuple or to the exclusion sets in this test.",
        )

    def test_exists_predicate_is_boundary(self):
        """ExistsPredicate is a scope boundary (not Nested* but still braced)."""
        from graphglot.scope import SUBQUERY_BOUNDARY_TYPES

        self.assertIn(ast.ExistsPredicate, SUBQUERY_BOUNDARY_TYPES)


if __name__ == "__main__":
    unittest.main()
