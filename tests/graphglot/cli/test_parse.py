"""Tests for the `gg parse` CLI command."""

from __future__ import annotations

import json
import unittest

from click.testing import CliRunner

from graphglot.cli import cli


class TestParseCommand(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    def test_valid_query_exit_0(self):
        result = self.runner.invoke(cli, ["parse", "MATCH (n) RETURN n"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Valid", result.output)

    def test_invalid_query_exit_1(self):
        result = self.runner.invoke(cli, ["parse", "MATCH (n RETURN n"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Invalid", result.output)

    def test_valid_json(self):
        result = self.runner.invoke(cli, ["parse", "-o", "json", "MATCH (n) RETURN n"])
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.output)
        self.assertTrue(data["valid"])

    def test_invalid_json(self):
        result = self.runner.invoke(cli, ["parse", "-o", "json", "MATCH (n RETURN n"])
        self.assertNotEqual(result.exit_code, 0)
        data = json.loads(result.output)
        self.assertFalse(data["valid"])
        self.assertIn("stage", data)
        self.assertIn("errors", data)

    def test_dialect_aware(self):
        result = self.runner.invoke(cli, ["parse", "-d", "neo4j", "MATCH (n) RETURN n"])
        self.assertEqual(result.exit_code, 0)

    def test_alias_p(self):
        result = self.runner.invoke(cli, ["p", "MATCH (n) RETURN n"])
        self.assertEqual(result.exit_code, 0)
