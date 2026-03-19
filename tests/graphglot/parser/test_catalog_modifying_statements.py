import unittest

from graphglot import ast

from .helpers import ParserTestHelper


class TestCreateSchemaStatement(unittest.TestCase):
    def setUp(self) -> None:
        self.helper = ParserTestHelper()

    def test_create_schema_simple_absolute(self):
        query = "CREATE SCHEMA /myschemas/foo"
        expr = self.helper.parse_single(query, ast.CreateSchemaStatement)

        self.assertIsInstance(expr, ast.CreateSchemaStatement)
        self.assertFalse(expr.if_not_exists)
        self.assertIsInstance(expr.catalog_schema_parent_and_name, ast.CatalogSchemaParentAndName)

    def test_create_schema_if_not_exists_relative(self):
        # Use an absolute directory path as required by <catalog schema parent and name>.
        query = "CREATE SCHEMA IF NOT EXISTS /myschemas/bar"
        expr = self.helper.parse_single(query, ast.CreateSchemaStatement)

        self.assertIsInstance(expr, ast.CreateSchemaStatement)
        self.assertTrue(expr.if_not_exists)
        self.assertIsInstance(expr.catalog_schema_parent_and_name, ast.CatalogSchemaParentAndName)


class TestDropSchemaStatement(unittest.TestCase):
    def setUp(self) -> None:
        self.helper = ParserTestHelper()

    def test_drop_schema_simple(self):
        query = "DROP SCHEMA /myschemas/foo"
        expr = self.helper.parse_single(query, ast.DropSchemaStatement)

        self.assertIsInstance(expr, ast.DropSchemaStatement)
        self.assertFalse(expr.if_exists)

    def test_drop_schema_if_exists(self):
        # Use an absolute directory path as required by <catalog schema parent and name>.
        query = "DROP SCHEMA IF EXISTS /myschemas/bar"
        expr = self.helper.parse_single(query, ast.DropSchemaStatement)

        self.assertIsInstance(expr, ast.DropSchemaStatement)
        self.assertTrue(expr.if_exists)


class TestCreateGraphStatement(unittest.TestCase):
    def setUp(self) -> None:
        self.helper = ParserTestHelper()

    def test_create_graph_simple(self):
        query = "CREATE PROPERTY GRAPH my_graph_of_type LIKE CURRENT_GRAPH"
        expr = self.helper.parse_single(query, ast.CreateGraphStatement)

        self.assertIsInstance(expr, ast.CreateGraphStatement)
        self.assertEqual(expr.create_mode, ast.CreateGraphStatement.CreateMode.CREATE_GRAPH)
        self.assertIsInstance(expr.catalog_graph_parent_and_name, ast.CatalogGraphParentAndName)
        self.assertIsInstance(expr.graph_type, ast.OfGraphType)

    def test_create_graph_if_not_exists_with_source(self):
        query = """
            CREATE PROPERTY GRAPH IF NOT EXISTS my_graph
            LIKE CURRENT_GRAPH AS COPY OF CURRENT_GRAPH
        """
        expr = self.helper.parse_single(query, ast.CreateGraphStatement)

        self.assertIsInstance(expr, ast.CreateGraphStatement)
        self.assertEqual(
            expr.create_mode,
            ast.CreateGraphStatement.CreateMode.CREATE_GRAPH_IF_NOT_EXISTS,
        )
        self.assertIsInstance(expr.graph_source, ast.GraphSource)


class TestDropGraphStatement(unittest.TestCase):
    def setUp(self) -> None:
        self.helper = ParserTestHelper()

    def test_drop_graph_simple(self):
        query = "DROP GRAPH my_graph"
        expr = self.helper.parse_single(query, ast.DropGraphStatement)

        self.assertIsInstance(expr, ast.DropGraphStatement)
        self.assertFalse(expr.if_exists)

    def test_drop_graph_if_exists_property_graph(self):
        query = "DROP PROPERTY GRAPH IF EXISTS my_graph"
        expr = self.helper.parse_single(query, ast.DropGraphStatement)

        self.assertIsInstance(expr, ast.DropGraphStatement)
        self.assertTrue(expr.if_exists)


class TestCreateGraphTypeStatement(unittest.TestCase):
    def setUp(self) -> None:
        self.helper = ParserTestHelper()

    def test_create_graph_type_simple(self):
        query = "CREATE PROPERTY GRAPH TYPE my_type LIKE CURRENT_GRAPH"
        expr = self.helper.parse_single(query, ast.CreateGraphTypeStatement)

        self.assertIsInstance(expr, ast.CreateGraphTypeStatement)
        self.assertEqual(
            expr.create_mode,
            ast.CreateGraphTypeStatement.CreateMode.CREATE_GRAPH_TYPE,
        )
        self.assertIsInstance(
            expr.catalog_graph_type_parent_and_name, ast.CatalogGraphTypeParentAndName
        )
        self.assertIsInstance(expr.graph_type_source, ast.GraphTypeSource)

    def test_create_graph_type_if_not_exists(self):
        query = "CREATE PROPERTY GRAPH TYPE IF NOT EXISTS my_type LIKE CURRENT_GRAPH"
        expr = self.helper.parse_single(query, ast.CreateGraphTypeStatement)

        self.assertIsInstance(expr, ast.CreateGraphTypeStatement)
        self.assertEqual(
            expr.create_mode,
            ast.CreateGraphTypeStatement.CreateMode.CREATE_GRAPH_TYPE_IF_NOT_EXISTS,
        )


class TestDropGraphTypeStatement(unittest.TestCase):
    def setUp(self) -> None:
        self.helper = ParserTestHelper()

    def test_drop_graph_type_simple(self):
        query = "DROP GRAPH TYPE my_type"
        expr = self.helper.parse_single(query, ast.DropGraphTypeStatement)

        self.assertIsInstance(expr, ast.DropGraphTypeStatement)
        self.assertFalse(expr.if_exists)

    def test_drop_graph_type_if_exists_property_graph_type(self):
        query = "DROP PROPERTY GRAPH TYPE IF EXISTS my_type"
        expr = self.helper.parse_single(query, ast.DropGraphTypeStatement)

        self.assertIsInstance(expr, ast.DropGraphTypeStatement)
        self.assertTrue(expr.if_exists)
