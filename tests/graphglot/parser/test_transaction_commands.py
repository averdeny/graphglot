"""Tests for transaction command parsing functionality."""

import unittest

from graphglot import ast

from .helpers import ParserTestHelper


class TestTransactionCommands(unittest.TestCase):
    """Test suite for transaction command parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_commit_command(self):
        """Test that the parser can parse a commit command."""
        query = "COMMIT"
        expressions = self.helper.parse(query)

        expected_commit_command = expressions[0].leaf_list()[0]
        self.assertIsInstance(expected_commit_command, ast.EndTransactionCommand)
        self.assertEqual(expected_commit_command.mode, ast.EndTransactionCommand.Mode.COMMIT)

    def test_rollback_command(self):
        """Test that the parser can parse a rollback command."""
        query = "ROLLBACK"
        expressions = self.helper.parse(query)

        expected_rollback_command = expressions[0].leaf_list()[0]
        self.assertIsInstance(expected_rollback_command, ast.EndTransactionCommand)
        self.assertEqual(expected_rollback_command.mode, ast.EndTransactionCommand.Mode.ROLLBACK)

    def test_start_transaction_command(self):
        """Test that the parser can parse a start transaction command."""
        query = "START TRANSACTION"
        self.helper.parse(query)
