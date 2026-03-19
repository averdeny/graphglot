"""Tests for the `gg features` CLI command."""

from __future__ import annotations

import json
import unittest

from click.testing import CliRunner

from graphglot.cli import cli


class TestFeaturesCommand(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    def test_list_all(self):
        result = self.runner.invoke(cli, ["features"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("features", result.output.lower())

    def test_json_format(self):
        result = self.runner.invoke(cli, ["features", "-o", "json"])
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.output)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        self.assertIn("id", data[0])
        self.assertIn("kind", data[0])
        self.assertIn("category", data[0])
        self.assertIn("description", data[0])

    def test_filter_by_dialect(self):
        all_result = self.runner.invoke(cli, ["features", "-o", "json"])
        all_data = json.loads(all_result.output)
        neo4j_result = self.runner.invoke(cli, ["features", "-d", "neo4j", "-o", "json"])
        neo4j_data = json.loads(neo4j_result.output)
        # Neo4j supports a subset
        self.assertLessEqual(len(neo4j_data), len(all_data))
        self.assertGreater(len(neo4j_data), 0)

    def test_filter_by_kind_optional(self):
        result = self.runner.invoke(cli, ["features", "-k", "optional", "-o", "json"])
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.output)
        for f in data:
            self.assertEqual(f["kind"], "optional")

    def test_filter_by_kind_extension(self):
        result = self.runner.invoke(cli, ["features", "-k", "extension", "-o", "json"])
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.output)
        for f in data:
            self.assertEqual(f["kind"], "extension")

    def test_filter_by_category(self):
        result = self.runner.invoke(cli, ["features", "-c", "Graph pattern", "-o", "json"])
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.output)
        self.assertGreater(len(data), 0)
        for f in data:
            self.assertIn("graph pattern", f["category"].lower())

    def test_search(self):
        result = self.runner.invoke(cli, ["features", "-s", "path", "-o", "json"])
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.output)
        self.assertGreater(len(data), 0)
        for f in data:
            self.assertTrue("path" in f["id"].lower() or "path" in f["description"].lower())

    def test_combined_filters(self):
        result = self.runner.invoke(
            cli, ["features", "-d", "neo4j", "-k", "optional", "-o", "json"]
        )
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.output)
        for f in data:
            self.assertEqual(f["kind"], "optional")

    def test_empty_results(self):
        result = self.runner.invoke(cli, ["features", "-s", "zzz_nonexistent_zzz", "-o", "json"])
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.output)
        self.assertEqual(len(data), 0)

    def test_alias_f(self):
        result = self.runner.invoke(cli, ["f"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("features", result.output.lower())
