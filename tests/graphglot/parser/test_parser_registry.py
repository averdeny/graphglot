"""Smoke tests for the @parses decorator-based parser registry."""

from __future__ import annotations

import enum
import typing as t
import unittest

from graphglot.ast.base import Expression
from graphglot.parser.base import Parser
from graphglot.parser.registry import get_registry


class TestParserRegistry(unittest.TestCase):
    def test_registry_has_entries(self):
        registry = get_registry()
        self.assertGreater(len(registry), 500)

    def test_registry_values_are_callable(self):
        registry = get_registry()
        for expr_type, func in registry.items():
            name = getattr(expr_type, "__name__", str(expr_type))
            self.assertTrue(callable(func), f"Value for {name} is not callable")

    def test_registry_keys_are_expression_types(self):
        registry = get_registry()
        for key in registry:
            # Concrete classes should be subclasses of Expression or Enum
            if isinstance(key, type):
                self.assertTrue(
                    issubclass(key, Expression | enum.Enum),
                    f"{key} is not an Expression subclass or Enum",
                )
            else:
                # Union TypeAliases (typing._UnionGenericAlias) are also valid keys
                self.assertIsNotNone(
                    t.get_args(key),
                    f"{key} is neither a type nor a Union TypeAlias",
                )

    def test_default_parsers_matches_registry(self):
        self.assertEqual(Parser.PARSERS, get_registry())

    def test_arithmetic_primary_registered(self):
        """parse_arithmetic_primary was previously missing from the PARSERS dict."""
        from graphglot import ast

        registry = get_registry()
        self.assertIn(ast.ArithmeticPrimary, registry)
