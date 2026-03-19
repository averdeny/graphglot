"""Tests for schema reference parsing functionality."""

import unittest

from graphglot import ast

from .helpers import ParserTestHelper


class TestSchemaReferences(unittest.TestCase):
    """Test suite for schema reference parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_at_schema_clause(self):
        """Test that the parser can parse an AT schema clause."""
        query = "AT HOME_SCHEMA"
        self.helper.parse(query, ast.AtSchemaClause)

    def test_relative_directory_path(self):
        """Test that the parser can parse a relative directory path."""
        query = "../../"
        expressions = self.helper.parse(query, ast.RelativeDirectoryPath)

        self.assertEqual(expressions[0].up_levels, 2)
        self.assertIsNone(expressions[0].simple_directory_path)

    def test_relative_directory_path_simple(self):
        """Test that the parser can parse a simple relative directory path."""
        query = ".."
        expressions = self.helper.parse(query, ast.RelativeDirectoryPath)

        self.assertEqual(expressions[0].up_levels, 1)
        self.assertIsNone(expressions[0].simple_directory_path)

    def test_schema_name(self):
        """Test that the parser can parse a schema name."""
        query = "my_schema"
        expressions = self.helper.parse(query, ast.SchemaName)

        self.assertIsInstance(expressions[0], ast.Identifier)
        self.assertEqual(expressions[0].name, "my_schema")

    def test_simple_directory_path_single_segment(self):
        """Test that the parser can parse a simple directory path with one segment."""
        query = "foo/"
        expr = self.helper.parse_single(query, ast.SimpleDirectoryPath)

        self.assertIsInstance(expr, ast.SimpleDirectoryPath)
        self.assertEqual(len(expr.items), 1)
        # DirectoryName is a type alias for Identifier
        self.assertIsInstance(expr.items[0], ast.DirectoryName)
        self.assertEqual(expr.items[0].name, "foo")

    def test_simple_directory_path_multiple_segments(self):
        """Test that the parser can parse a simple directory path with multiple segments."""
        query = "foo/bar/"
        expr = self.helper.parse_single(query, ast.SimpleDirectoryPath)

        self.assertIsInstance(expr, ast.SimpleDirectoryPath)
        self.assertEqual(len(expr.items), 2)
        self.assertIsInstance(expr.items[0], ast.DirectoryName)
        self.assertIsInstance(expr.items[1], ast.DirectoryName)
        self.assertEqual(expr.items[0].name, "foo")
        self.assertEqual(expr.items[1].name, "bar")
