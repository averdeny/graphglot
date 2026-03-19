import unittest

from graphglot import ast

from .helpers import ParserTestHelper


class TestPathSearch(unittest.TestCase):
    def setUp(self) -> None:
        self.helper = ParserTestHelper()

    def test_all_path_search_simple(self):
        query = "ALL"
        expr = self.helper.parse_single(query, ast.AllPathSearch)

        self.assertIsInstance(expr, ast.AllPathSearch)
        self.assertIsNone(expr.path_mode)
        self.assertFalse(expr.path_or_paths)

    def test_all_path_search_with_mode_and_paths(self):
        query = "ALL WALK PATHS"
        expr = self.helper.parse_single(query, ast.AllPathSearch)

        self.assertIsInstance(expr, ast.AllPathSearch)
        self.assertIsNotNone(expr.path_mode)
        self.assertTrue(expr.path_or_paths)

    def test_any_path_search_simple(self):
        query = "ANY"
        expr = self.helper.parse_single(query, ast.AnyPathSearch)

        self.assertIsInstance(expr, ast.AnyPathSearch)
        self.assertIsNone(expr.number_of_paths)
        self.assertIsNone(expr.path_mode)
        self.assertFalse(expr.path_or_paths)

    def test_any_path_search_with_number_mode_and_paths(self):
        query = "ANY 3 WALK PATHS"
        expr = self.helper.parse_single(query, ast.AnyPathSearch)

        self.assertIsInstance(expr, ast.AnyPathSearch)
        self.assertIsNotNone(expr.number_of_paths)
        self.assertIsNotNone(expr.path_mode)
        self.assertTrue(expr.path_or_paths)

    def test_all_shortest_path_search_with_mode_and_paths(self):
        query = "ALL SHORTEST WALK PATHS"
        expr = self.helper.parse_single(query, ast.AllShortestPathSearch)

        self.assertIsInstance(expr, ast.AllShortestPathSearch)
        self.assertIsInstance(expr.path_mode, ast.PathMode)
        self.assertTrue(expr.path_or_paths)

    def test_any_shortest_path_search_simple(self):
        query = "ANY SHORTEST"
        expr = self.helper.parse_single(query, ast.AnyShortestPathSearch)

        self.assertIsInstance(expr, ast.AnyShortestPathSearch)
        self.assertIsNone(expr.path_mode)
        self.assertFalse(expr.path_or_paths)

    def test_counted_shortest_path_search_with_number_mode_and_paths(self):
        query = "SHORTEST 5 WALK PATHS"
        expr = self.helper.parse_single(query, ast.CountedShortestPathSearch)

        self.assertIsInstance(expr, ast.CountedShortestPathSearch)
        self.assertIsNotNone(expr.number_of_paths)
        self.assertIsNotNone(expr.path_mode)
        self.assertTrue(expr.path_or_paths)
