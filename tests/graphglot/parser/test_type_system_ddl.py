"""Tests for node/edge type and graph-type DDL (type system side) parsing functionality."""

import unittest

from graphglot import ast

from .helpers import ParserTestHelper


class TestNodeTypePattern(unittest.TestCase):
    """Test suite for NodeTypePattern parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_node_type_pattern_simple(self):
        """Test that the parser can parse a simple node type pattern."""
        query = "NODE TYPE Person ()"
        expr = self.helper.parse_single(query, ast.NodeTypePattern)

        self.assertIsInstance(expr, ast.NodeTypePattern)
        self.assertIsNotNone(expr.node_synonym_type_node_type_name)
        self.assertIsNone(expr.local_node_type_alias)
        self.assertIsNone(expr.node_type_filler)

    def test_node_type_pattern_with_alias(self):
        """Test that the parser can parse a node type pattern with local alias."""
        query = "NODE TYPE Person (p)"
        expr = self.helper.parse_single(query, ast.NodeTypePattern)

        self.assertIsInstance(expr, ast.NodeTypePattern)
        self.assertIsNotNone(expr.local_node_type_alias)

    def test_node_type_pattern_without_type_keyword(self):
        """Test that the parser can parse a node type pattern without TYPE keyword."""
        query = "NODE Person ()"
        expr = self.helper.parse_single(query, ast.NodeTypePattern)

        self.assertIsInstance(expr, ast.NodeTypePattern)
        self.assertIsNotNone(expr.node_synonym_type_node_type_name)
        self.assertFalse(expr.node_synonym_type_node_type_name.type)

    def test_node_type_pattern_as_node_type_specification(self):
        """Test that the parser can parse a node type pattern as NodeTypeSpecification."""
        query = "NODE TYPE Person ()"
        expr = self.helper.parse_single(query, ast.NodeTypeSpecification)

        self.assertIsInstance(expr, ast.NodeTypePattern)


class TestNodeTypePhrase(unittest.TestCase):
    """Test suite for NodeTypePhrase parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_node_type_phrase_with_label(self):
        """Test that the parser can parse a node type phrase with label."""
        query = "NODE TYPE Person LABEL Person"
        expr = self.helper.parse_single(query, ast.NodeTypePhrase)

        self.assertIsInstance(expr, ast.NodeTypePhrase)

    def test_node_type_phrase_with_alias(self):
        """Test that the parser can parse a node type phrase with alias."""
        query = "NODE TYPE Person LABEL Person AS p"
        expr = self.helper.parse_single(query, ast.NodeTypePhrase)

        self.assertIsInstance(expr, ast.NodeTypePhrase)
        self.assertIsNotNone(expr.local_node_type_alias)


class TestEdgeTypePattern(unittest.TestCase):
    """Test suite for EdgeTypePattern parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_edge_type_pattern_pointing_right(self):
        """Test that the parser can parse an edge type pattern pointing right."""
        query = "EDGE TYPE Rel (A)-[IS Rel]->(B)"
        expr = self.helper.parse_single(query, ast.EdgeTypePattern)

        self.assertIsInstance(expr, ast.EdgeTypePattern)
        self.assertIsInstance(expr.edge_type_pattern, ast.EdgeTypePatternDirected)

    def test_edge_type_pattern_pointing_left(self):
        """Test that the parser can parse an edge type pattern pointing left."""
        query = "EDGE TYPE Rel (A)<-[IS Rel]-(B)"
        expr = self.helper.parse_single(query, ast.EdgeTypePattern)

        self.assertIsInstance(expr, ast.EdgeTypePattern)
        self.assertIsInstance(expr.edge_type_pattern, ast.EdgeTypePatternDirected)

    def test_edge_type_pattern_undirected(self):
        """Test that the parser can parse an undirected edge type pattern."""
        query = "EDGE TYPE Rel (A)~[IS Rel]~(B)"
        expr = self.helper.parse_single(query, ast.EdgeTypePattern)

        self.assertIsInstance(expr, ast.EdgeTypePattern)
        self.assertIsInstance(expr.edge_type_pattern, ast.EdgeTypePatternUndirected)


class TestEdgeTypePhrase(unittest.TestCase):
    """Test suite for EdgeTypePhrase parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_edge_type_phrase_directed(self):
        """Test that the parser can parse a directed edge type phrase."""
        query = "DIRECTED EDGE TYPE Rel CONNECTING (A TO B)"
        expr = self.helper.parse_single(query, ast.EdgeTypePhrase)

        self.assertIsInstance(expr, ast.EdgeTypePhrase)
        self.assertEqual(expr.edge_kind, ast.EdgeKind.DIRECTED)

    def test_edge_type_phrase_undirected(self):
        """Test that the parser can parse an undirected edge type phrase."""
        query = "UNDIRECTED EDGE TYPE Rel CONNECTING (A TO B)"
        expr = self.helper.parse_single(query, ast.EdgeTypePhrase)

        self.assertIsInstance(expr, ast.EdgeTypePhrase)
        self.assertEqual(expr.edge_kind, ast.EdgeKind.UNDIRECTED)


class TestGraphTypeSource(unittest.TestCase):
    """Test suite for GraphTypeSource parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_graph_type_source_like_graph(self):
        """Test that the parser can parse a graph type source with LIKE."""
        query = "LIKE CURRENT_GRAPH"
        expr = self.helper.parse_single(query, ast.GraphTypeSource)

        self.assertIsInstance(expr, ast.GraphTypeSource)
        self.assertIsInstance(expr.graph_type_source, ast.GraphTypeLikeGraph)

    def test_graph_type_source_copy_of(self):
        """Test that the parser can parse a graph type source with COPY OF."""
        # COPY OF requires a GraphTypeReference (graph type name),
        # not a GraphExpression like CURRENT_GRAPH
        query = "COPY OF my_graph_type"
        expr = self.helper.parse_single(query, ast.GraphTypeSource)

        self.assertIsInstance(expr, ast.GraphTypeSource)
        self.assertIsInstance(expr.graph_type_source, ast.GraphTypeSource._AsCopyOfGraphType)

    def test_graph_type_source_as_copy_of(self):
        """Test that the parser can parse a graph type source with AS COPY OF."""
        # COPY OF requires a GraphTypeReference (graph type name),
        # not a GraphExpression like CURRENT_GRAPH
        query = "AS COPY OF my_graph_type"
        expr = self.helper.parse_single(query, ast.GraphTypeSource)

        self.assertIsInstance(expr, ast.GraphTypeSource)
        self.assertIsInstance(expr.graph_type_source, ast.GraphTypeSource._AsCopyOfGraphType)
        self.assertTrue(expr.graph_type_source.as_)
