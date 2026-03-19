"""Tests for the `gg type` CLI command."""

from __future__ import annotations

import json
import unittest

from click.testing import CliRunner

from graphglot.cli import cli


class TestTypeCommand(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    def test_basic_type_output(self):
        result = self.runner.invoke(cli, ["type", "MATCH (n) RETURN n"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Inferred Types", result.output)
        self.assertIn("n", result.output)

    def test_json_format(self):
        result = self.runner.invoke(cli, ["type", "-o", "json", "MATCH (n) RETURN n"])
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.output)
        self.assertIn("ok", data)
        self.assertIn("fields", data)
        self.assertIsInstance(data["fields"], list)
        self.assertGreater(len(data["fields"]), 0)
        field = data["fields"][0]
        self.assertIn("position", field)
        self.assertIn("expression", field)
        self.assertIn("type", field)

    def test_invalid_query_exit_1(self):
        result = self.runner.invoke(cli, ["type", "MATCH (n RETURN n"])
        self.assertNotEqual(result.exit_code, 0)

    def test_invalid_query_json(self):
        result = self.runner.invoke(cli, ["type", "-o", "json", "MATCH (n RETURN n"])
        self.assertNotEqual(result.exit_code, 0)
        data = json.loads(result.output)
        self.assertFalse(data["ok"])

    def test_dialect_option(self):
        result = self.runner.invoke(cli, ["type", "-d", "neo4j", "MATCH (n) RETURN n"])
        self.assertEqual(result.exit_code, 0)

    def test_alias_ty(self):
        result = self.runner.invoke(cli, ["ty", "MATCH (n) RETURN n"])
        self.assertEqual(result.exit_code, 0)

    def test_return_star(self):
        result = self.runner.invoke(cli, ["type", "MATCH (n) RETURN *"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("star projection", result.output.lower())

    def test_annotated_count_shown(self):
        result = self.runner.invoke(cli, ["type", "MATCH (n) RETURN n"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Annotated", result.output)
