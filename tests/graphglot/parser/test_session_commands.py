"""Tests for session command parsing functionality."""

import unittest

from graphglot import ast

from .helpers import ParserTestHelper


class TestSessionCommands(unittest.TestCase):
    """Test suite for session command parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_gql_program_close_only(self):
        """Test that the parser can parse a GQL program with only a session close command."""
        query = "SESSION CLOSE"
        expressions = self.helper.parse(query)

        expected_session_close_command = expressions[0].leaf_list()[0]
        self.assertIsInstance(expected_session_close_command, ast.SessionCloseCommand)

    def test_session_set_absolute_schema_command(self):
        """Test that the parser can parse a session set command with absolute schema."""
        query = "SESSION SET SCHEMA /"
        expressions = self.helper.parse(query, ast.SessionSetCommand)

        expected_session_set_command = expressions[0].leaf_list()[0]
        self.assertIsInstance(expected_session_set_command, ast.Solidus)

    def test_session_set_home_schema_command(self):
        """Test that the parser can parse a session set command with HOME_SCHEMA."""
        query = "SESSION SET SCHEMA HOME_SCHEMA"
        expressions = self.helper.parse(query, ast.SessionSetCommand)

        expected_session_set_command = expressions[0].leaf_list()[0]
        self.assertIsInstance(
            expected_session_set_command, ast.PredefinedSchemaReference._HomeSchema
        )

    def test_session_set_period_schema_command(self):
        """Test that the parser can parse a session set command with period schema."""
        query = "SESSION SET SCHEMA ."
        expressions = self.helper.parse(query, ast.SessionSetCommand)

        expected_session_set_command = expressions[0].leaf_list()[0]
        self.assertIsInstance(expected_session_set_command, ast.PredefinedSchemaReference._Period)

    def test_session_set_current_schema_command(self):
        """Test that the parser can parse a session set command with CURRENT_SCHEMA."""
        query = "SESSION SET SCHEMA CURRENT_SCHEMA"
        expressions = self.helper.parse(query, ast.SessionSetCommand)

        expected_session_set_command = expressions[0].leaf_list()[0]
        self.assertIsInstance(
            expected_session_set_command, ast.PredefinedSchemaReference._CurrentSchema
        )

    def test_session_set_schema_clause_relative_schema_reference(self):
        """Test that the parser can parse a session set schema clause with relative reference."""
        query = "SCHEMA .. my_schema"
        expressions = self.helper.parse(query, ast.SessionSetSchemaClause)

        self.assertIsInstance(expressions[0], ast.SessionSetSchemaClause)

    def test_session_set_graph(self):
        """Test that the parser can parse a session set graph clause."""
        query = "GRAPH my_graph"
        self.helper.parse(query, ast.SessionSetGraphClause)

    def test_session_reset_command(self):
        """Test that the parser can parse a session reset command."""
        query = "SESSION RESET"
        expressions = self.helper.parse(query, ast.SessionResetCommand)

        self.assertIsInstance(expressions[0], ast.SessionResetCommand)
        self.assertIsNone(expressions[0].session_reset_arguments)
