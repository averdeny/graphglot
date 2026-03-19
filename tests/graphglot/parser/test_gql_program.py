import unittest

from graphglot import ast

from .helpers import ParserTestHelper


class TestCreateSchemaStatement(unittest.TestCase):
    def setUp(self) -> None:
        self.helper = ParserTestHelper()

    def assert_gql_program(self, query: str):
        expr = self.helper.parse_single(query, ast.GqlProgram)
        self.assertIsInstance(expr, ast.GqlProgram)
        return expr

    def test_session_close_only(self):
        self.assert_gql_program("SESSION CLOSE")

    def test_commit_command(self):
        self.assert_gql_program("COMMIT")

    def test_rollback_command(self):
        self.assert_gql_program("ROLLBACK")

    def test_create_schema(self):
        self.assert_gql_program("CREATE SCHEMA /my_schemas/foo")

    def test_create_schema_if_not_exists(self):
        self.assert_gql_program("CREATE SCHEMA IF NOT EXISTS /my_schemas/foo")

    def test_session_set_schema_command(self):
        self.assert_gql_program("SESSION SET SCHEMA /my_schemas/foo")

    def test_session_set_graph_command(self):
        self.assert_gql_program("SESSION SET GRAPH my_graph")

    def test_session_set_time_zone_command(self):
        self.assert_gql_program('SESSION SET TIME ZONE "utc"')

    def test_create_graph(self):
        query = """
        CREATE GRAPH my_graph {
            (n: Person {first_name STRING, last_name STRING, age INT})
        }
        """
        self.assert_gql_program(query)

    def test_create_or_replace_graph(self):
        query = """
        CREATE OR REPLACE GRAPH my_graph LIKE CURRENT_GRAPH
        """
        self.assert_gql_program(query)

    def test_insert_statement(self):
        query = """
        INSERT
            (n: Person {first_name: "Alice", last_name: "Smith", age: 30}),
            (n: Person {first_name: "Bob", last_name: "Jones", age: 25}),
            (n: Person {first_name: "Charlie", last_name: "Brown", age: 35})
        """
        self.assert_gql_program(query)

    def test_simple_match_statement(self):
        self.assert_gql_program("""
        MATCH (n: Person {first_name: "Alice", last_name: "Smith", age: 30})
        RETURN n.first_name, n.last_name, n.age
        """)

    def test_multiple_labels(self):
        self.assert_gql_program("MATCH (n: Person|Employee) RETURN n")

    def test_edge_direction_right(self):
        """Test that right-pointing edge -[r]-> is parsed correctly."""
        query = "MATCH (a)-[r]->(b) RETURN a, r, b"
        expr = self.assert_gql_program(query)
        # Verify it's actually FullEdgePointingRight, not FullEdgeUndirected
        from graphglot.ast import FullEdgePointingRight

        found = False
        for node in expr.dfs():
            if isinstance(node, FullEdgePointingRight):
                found = True
                break
        self.assertTrue(found, "Expected FullEdgePointingRight but got different edge type")

    def test_edge_direction_right_with_label(self):
        query = "MATCH (a)-[r:KNOWS]->(b) RETURN a, b"
        expr = self.assert_gql_program(query)
        # Verify it's actually FullEdgePointingRight, not FullEdgeUndirected
        from graphglot.ast import FullEdgePointingRight

        found = False
        for node in expr.dfs():
            if isinstance(node, FullEdgePointingRight):
                found = True
                break
        self.assertTrue(found, "Expected FullEdgePointingRight but got different edge type")

    def test_property_reference_is_null(self):
        # NOTE: n.value_ is a valid property reference because it is not a keyword.
        self.assert_gql_program("MATCH (n) WHERE n.value_ IS NULL RETURN n")

    def test_property_reference_is_not_null(self):
        self.assert_gql_program("MATCH (n) WHERE n.value_ IS NOT NULL RETURN n")

    def test_set_table_from_query(self):
        query = """
        SESSION SET TABLE $table1 = { MATCH (n:Person) RETURN n }
        """
        self.assert_gql_program(query)

    def test_group_shortest_path(self):
        self.assert_gql_program("""
        MATCH (a {_id: "a"}), (c {_id: "c"})
        MATCH p = SHORTEST 1 GROUP (a)->{1,5}(c)
        RETURN p
        """)

    def test_optional_match_statements(self):
        self.assert_gql_program("""
        MATCH (n {key: "value"})
        OPTIONAL MATCH (n)-[r]->(m)
        RETURN DISTINCT m
        """)

    def test_optional_match_statements_with_for_statement(self):
        self.assert_gql_program("""
        FOR id in ["a", "b", "c"]
        OPTIONAL {
            MATCH (n {key: id})
            MATCH (n)->(m)
        }
        RETURN m._id
        """)

    def test_anonymous_call_statement(self):
        self.assert_gql_program("""
        MATCH (n)
        CALL {
            MATCH (n)-(m)
            RETURN COUNT(m) as total
        }
        RETURN n._id as startNode, total
        """)

    def test_repeatable_elements_match_mode(self):
        self.assert_gql_program("MATCH REPEATABLE ELEMENTS (n)-[e]->(m) RETURN n")
