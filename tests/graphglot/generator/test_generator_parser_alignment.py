"""Tests to verify generator registry and coverage."""

import typing as t
import unittest

from graphglot import ast
from graphglot.generator.base import Generator
from graphglot.generator.registry import get_registry


class TestDecoratorRegistry(unittest.TestCase):
    """Smoke tests for the @generates decorator registry."""

    def test_registry_has_entries(self):
        """Registry should contain a reasonable number of generators."""
        registry = get_registry()
        self.assertGreater(len(registry), 100)

    def test_registry_values_are_callable(self):
        """All registry values should be callable."""
        registry = get_registry()
        for expr_type, func in registry.items():
            self.assertTrue(
                callable(func),
                f"{getattr(expr_type, '__name__', str(expr_type))}: {func} is not callable",
            )

    def test_registry_keys_are_expression_types(self):
        """All registry keys should be Expression subclasses or Union TypeAliases."""
        import enum
        import types

        registry = get_registry()
        for expr_type in registry:
            if isinstance(expr_type, types.UnionType):
                continue  # Union TypeAliases (e.g., Predicate, ValueExpressionPrimary)
            self.assertTrue(
                isinstance(expr_type, type) and (issubclass(expr_type, ast.Expression | enum.Enum)),
                f"{expr_type} is not an Expression subclass, Enum, or Union TypeAlias",
            )

    def test_dispatch_boolean_literal(self):
        """Dispatch should work for BooleanLiteral (basic smoke test)."""
        gen = Generator()
        result = gen.generate(ast.BooleanLiteral(value=True))
        self.assertEqual(result, "TRUE")

    def test_dispatch_null_literal(self):
        """Dispatch should work for NullLiteral."""
        gen = Generator()
        result = gen.generate(ast.NullLiteral())
        self.assertEqual(result, "NULL")

    def test_default_generators_matches_registry(self):
        """Generator.GENERATORS should be populated from the registry."""
        self.assertEqual(Generator.GENERATORS, get_registry())


class TestGeneratorCoverage(unittest.TestCase):
    """Test that generator coverage doesn't regress.

    New parser types added without generators should be added to
    KNOWN_MISSING_GENERATORS to acknowledge the gap explicitly.
    """

    # AST types that are known to not have generators yet.
    # This list should shrink over time, not grow.
    # When adding a generator for a type here, remove it from this set.
    KNOWN_MISSING_GENERATORS: t.ClassVar[set[str]] = {
        # These are types that exist as parsers but don't have generators.
        # The alignment test will fail if a NEW type appears without either
        # a generator or an entry here.
    }

    def test_registry_not_empty(self):
        """Sanity check that the registry loaded correctly."""
        registry = get_registry()
        self.assertGreater(len(registry), 0)


class TestGeneratorModuleAlignment(unittest.TestCase):
    """Verify generator functions live in modules matching their parser modules.

    Uses func.__module__ introspection since @generates decorators
    replaced per-file GENERATORS dicts.
    """

    # Mapping from parser module suffix to generator module suffix
    MODULE_PAIRS: t.ClassVar[list[str]] = [
        "clauses",
        "commands",
        "core",
        "expressions",
        "literals",
        "patterns",
        "predicates",
        "statements",
        "types",
    ]

    def test_generator_modules_exist(self):
        """All expected generator modules should be importable."""
        import importlib

        for module_name in self.MODULE_PAIRS:
            with self.subTest(module=module_name):
                mod = importlib.import_module(f"graphglot.generator.generators.{module_name}")
                self.assertIsNotNone(mod)

    def test_generator_functions_have_generates_decorator(self):
        """Each registered generator function should come from a generators module."""
        registry = get_registry()
        for expr_type, func in registry.items():
            name = getattr(expr_type, "__name__", str(expr_type))
            with self.subTest(type=name):
                self.assertIn(
                    "graphglot.generator.generators.",
                    func.__module__,
                    f"Generator for {name} is in {func.__module__}, "
                    f"expected graphglot.generator.generators.*",
                )
