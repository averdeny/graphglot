import unittest

from graphglot import ast

from .helpers import ParserTestHelper


class TestSelectStatement(unittest.TestCase):
    def setUp(self) -> None:
        self.helper = ParserTestHelper()

    def test_select_asterisk_from_current_graph_match(self):
        """
        Basic SELECT * with a FROM <select graph match list> body.
        """
        query = "SELECT * FROM CURRENT_GRAPH MATCH (n)"

        expr = self.helper.parse_single(query, ast.SelectStatement)

        self.assertIsInstance(expr, ast.SelectStatement)
        # Projection is a bare asterisk
        self.assertIsInstance(expr.projection, ast.Asterisk)
        # Body is populated and uses a SelectGraphMatchList
        body = expr.body
        self.assertIsInstance(body, ast.SelectStatement._SelectStatementBodyWithClauses)
        self.assertIsInstance(
            body.select_statement_body.select_statement_body, ast.SelectGraphMatchList
        )

    def test_select_item_list_from_current_graph_match(self):
        """
        Select statement with a simple item list and FROM <select graph match list>.
        """
        query = "SELECT n.name FROM CURRENT_GRAPH MATCH (n)"

        expr = self.helper.parse_single(query, ast.SelectStatement)

        self.assertIsInstance(expr, ast.SelectStatement)
        self.assertIsInstance(expr.projection, ast.SelectItemList)
        item_list = expr.projection
        self.assertGreaterEqual(len(item_list.list_select_item), 1)

        body = expr.body
        self.assertIsInstance(body, ast.SelectStatement._SelectStatementBodyWithClauses)
        self.assertIsInstance(
            body.select_statement_body.select_statement_body, ast.SelectGraphMatchList
        )

    def test_select_with_where_group_by_having_order_by_offset_limit(self):
        """
        Select with most optional body clauses present to exercise plumbing.x
        """
        # The grammar here is a bit weird because:
        # - the first WHERE is parsed as part of <graph pattern where clause>.
        # - the second WHERE belongs to the SelectStatement.
        query = """
            SELECT n, COUNT(*) AS c
            FROM CURRENT_GRAPH MATCH (n)
            WHERE n.age > 30
            WHERE n.name = 'John'
            GROUP BY n
            HAVING COUNT(*) > 1
            ORDER BY n
            OFFSET 5
            LIMIT 10
        """

        expr = self.helper.parse_single(query, ast.SelectStatement)

        self.assertIsInstance(expr, ast.SelectStatement)
        body = expr.body
        self.assertIsInstance(body, ast.SelectStatement._SelectStatementBodyWithClauses)

        # Check that all the optional clauses were wired through
        self.assertIsInstance(body.where_clause, ast.WhereClause)
        self.assertIsInstance(body.group_by_clause, ast.GroupByClause)
        self.assertIsInstance(body.having_clause, ast.HavingClause)
        self.assertIsInstance(body.order_by_clause, ast.OrderByClause)
        self.assertIsInstance(body.offset_clause, ast.OffsetClause)
        self.assertIsInstance(body.limit_clause, ast.LimitClause)

    def test_select_from_nested_query_specification(self):
        """
        SELECT using FROM <select query specification> with a nested query specification.

        FROM { SELECT ... } form exercises the SelectQuerySpecification branch.
        """
        query = """
            SELECT * FROM {
                SELECT n
                FROM CURRENT_GRAPH MATCH (n)
            }
        """

        expr = self.helper.parse_single(query, ast.SelectStatement)

        self.assertIsInstance(expr, ast.SelectStatement)
        body = expr.body
        self.assertIsInstance(body, ast.SelectStatement._SelectStatementBodyWithClauses)
        self.assertIsInstance(
            body.select_statement_body.select_statement_body,
            ast.SelectQuerySpecification,
        )

    def test_select_from_graph_expression_and_nested_query_specification(self):
        """
        SELECT using FROM <graph expression> <nested query specification>.
        """
        query = """
            SELECT * FROM CURRENT_GRAPH {
                SELECT n
                FROM CURRENT_GRAPH MATCH (n)
            }
        """

        expr = self.helper.parse_single(query, ast.SelectStatement)

        self.assertIsInstance(expr, ast.SelectStatement)
        body = expr.body
        self.assertIsInstance(body, ast.SelectStatement._SelectStatementBodyWithClauses)
        self.assertIsInstance(
            body.select_statement_body.select_statement_body,
            ast.SelectQuerySpecification,
        )
