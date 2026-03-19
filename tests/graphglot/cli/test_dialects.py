"""Tests for the `gg dialects` CLI command."""

from __future__ import annotations

import json
import unittest

from click.testing import CliRunner

from graphglot.cli import cli


class TestDialectsCommand(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    def test_lists_dialects(self):
        result = self.runner.invoke(cli, ["dialects"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("fullgql", result.output.lower())
        self.assertIn("neo4j", result.output.lower())

    def test_json_format(self):
        result = self.runner.invoke(cli, ["dialects", "-o", "json"])
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.output)
        self.assertIsInstance(data, list)
        names = [d["name"] for d in data]
        self.assertIn("fullgql", names)
        self.assertIn("neo4j", names)

    def test_feature_counts_present(self):
        result = self.runner.invoke(cli, ["dialects", "-o", "json"])
        data = json.loads(result.output)
        for d in data:
            self.assertIn("features", d)
            self.assertIsInstance(d["features"], int)
            self.assertGreater(d["features"], 0)

    def test_ir_not_listed(self):
        """Internal IR dialect should not appear in user-facing output."""
        result = self.runner.invoke(cli, ["dialects", "-o", "json"])
        data = json.loads(result.output)
        names = [d["name"] for d in data]
        self.assertNotIn("ir", names)

    def test_alias_d(self):
        result = self.runner.invoke(cli, ["d"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("fullgql", result.output.lower())

    def test_descriptions_present(self):
        result = self.runner.invoke(cli, ["dialects", "-o", "json"])
        data = json.loads(result.output)
        for d in data:
            self.assertIn("description", d)
            self.assertIsInstance(d["description"], str)
