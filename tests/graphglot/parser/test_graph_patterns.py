"""Tests for graph pattern parsing functionality."""

import unittest

from graphglot import ast

from .helpers import ParserTestHelper


class TestGraphPatterns(unittest.TestCase):
    """Test suite for graph pattern parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_simple_graph_pattern_binding_table(self):
        """Test that the parser can parse a simple graph pattern binding table."""
        query = "(n:Person)"
        expr = self.helper.parse_single(query, ast.GraphPatternBindingTable)

        leaves = expr.leaf_list()
        self.assertEqual(len(leaves), 2)
        self.assertIsInstance(leaves[0], ast.BindingVariable)
        self.assertEqual(leaves[0].name, "n")
        self.assertIsInstance(leaves[1], ast.Identifier)
        self.assertEqual(leaves[1].name, "Person")

    def test_is_colon_equivalence(self):
        """Test that IS and colon syntax are equivalent."""
        query1 = "(n IS Person)"
        expr_1 = self.helper.parse_single(query1, ast.GraphPatternBindingTable)

        query2 = "(n:Person)"
        expr_2 = self.helper.parse_single(query2, ast.GraphPatternBindingTable)

        self.assertEqual(expr_1, expr_2)

    def test_is_not_labeled(self):
        """Test that the parser can parse label negation."""
        query = "(n IS !Person)"
        expr = self.helper.parse_single(query, ast.GraphPatternBindingTable)

        self.assertIsInstance(expr.find_first(ast.LabelNegation), ast.LabelNegation)

    def test_simple_graph_pattern_binding_table_with_label_disjunction(self):
        """Test that the parser can parse a graph pattern with label disjunction."""
        query = "(n:Person&Employee|Company)"
        expr = self.helper.parse_single(query, ast.GraphPatternBindingTable)

        self.assertIsNotNone(expr)
        # Verify the node pattern contains the expected labels
        leaves = expr.leaf_list()
        identifiers = [leaf for leaf in leaves if isinstance(leaf, ast.Identifier)]
        label_names = [id.name for id in identifiers]
        self.assertIn("Person", label_names)
        self.assertIn("Employee", label_names)
        self.assertIn("Company", label_names)

    def test_wildcard_label(self):
        """Test that the parser can parse a wildcard label."""
        query = "(n:%)"
        expr = self.helper.parse_single(query, ast.GraphPatternBindingTable)

        self.assertIsInstance(expr.find_first(ast.WildcardLabel), ast.WildcardLabel)

    def test_graph_pattern_binding_table_with_full_edge_pattern(self):
        """Test that the parser can parse a graph pattern with full edge pattern."""
        query = "p = (n:Person) -[r:KNOWS]-> (m:Person)"
        self.helper.parse(query, ast.GraphPatternBindingTable)

    def test_graph_pattern_binding_table_with_empty_filler(self):
        """Test that the parser can parse a graph pattern with empty edge filler."""
        query = "p = (n:Person) -[]-> (m:Person)"
        self.helper.parse(query, ast.GraphPatternBindingTable)

    def test_graph_pattern_binding_table_with_abbreviated_edge_pattern(self):
        """Test that the parser can parse a graph pattern with abbreviated edge pattern."""
        query = "p = (n:Person) -> (m:Person)"
        self.helper.parse(query, ast.GraphPatternBindingTable)

    def test_graph_pattern_binding_table_with_abbreviated_nondirectional_edge_pattern(self):
        """Test that the parser can parse a graph pattern with abbreviated nondirectional edge."""
        query = "(s)-(e)"  # using START and END wouldn't work because they are reserved keywords
        self.helper.parse(query, ast.GraphPatternBindingTable)

    def test_simple_graph_pattern_binding_table_with_path_prefix(self):
        """Test that the parser can parse a graph pattern with path prefix."""
        query = "p = (n:Person)"
        expr = self.helper.parse_single(query, ast.GraphPatternBindingTable)

        leaves = expr.leaf_list()
        self.assertEqual(len(leaves), 3)

    def test_node_with_where_clause(self):
        """Test that the parser can parse a node with a where clause."""
        query = "(p IS Person WHERE p.age > 30)"
        self.helper.parse(query, ast.GraphPatternBindingTable)

    def test_node_with_element_property_specification(self):
        """Test that the parser can parse a node with an element property specification."""
        query = "(p IS Person {name: 'John', age: 30})"
        self.helper.parse(query, ast.GraphPatternBindingTable)

    def test_edge_pattern(self):
        """Test that the parser can parse an edge pattern."""
        query = "-[r:KNOWS]->"
        self.helper.parse(query, ast.EdgePattern)

    def test_edge_abbreviated_pattern(self):
        """Test that the parser can parse an abbreviated edge pattern."""
        query = "->"
        self.helper.parse(query, ast.EdgePattern)
