"""Tests for --version flag."""

from __future__ import annotations

import unittest

from click.testing import CliRunner

from graphglot import __version__
from graphglot.cli import cli


class TestVersion(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    def test_version_flag(self):
        result = self.runner.invoke(cli, ["--version"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn(__version__, result.output)
        self.assertIn("graphglot", result.output)

    def test_version_flag_short(self):
        result = self.runner.invoke(cli, ["--version"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("version", result.output.lower())
