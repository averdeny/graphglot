"""Tests for dynamic union types and reference value types parsing functionality."""

import unittest

from graphglot import ast

from .helpers import ParserTestHelper


class TestOpenDynamicUnionType(unittest.TestCase):
    """Test suite for OpenDynamicUnionType parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_open_dynamic_union_type_value(self):
        """Test that the parser can parse VALUE type."""
        query = "ANY VALUE"
        expr = self.helper.parse_single(query, ast.OpenDynamicUnionType)

        self.assertIsInstance(expr, ast.OpenDynamicUnionType)
        self.assertFalse(expr.not_null)

    def test_open_dynamic_union_type_value_not_null(self):
        """Test that the parser can parse VALUE NOT NULL type."""
        query = "ANY VALUE NOT NULL"
        expr = self.helper.parse_single(query, ast.OpenDynamicUnionType)

        self.assertIsInstance(expr, ast.OpenDynamicUnionType)
        self.assertTrue(expr.not_null)

    def test_open_dynamic_union_type_any_value(self):
        """Test that the parser can parse ANY VALUE type."""
        query = "ANY VALUE"
        expr = self.helper.parse_single(query, ast.OpenDynamicUnionType)

        self.assertIsInstance(expr, ast.OpenDynamicUnionType)
        self.assertFalse(expr.not_null)

    def test_open_dynamic_union_type_as_value_type(self):
        query = "ANY VALUE NOT NULL"
        expr = self.helper.parse_single(query, ast.ValueType)

        self.assertIsInstance(expr, ast.ValueType)
        self.assertIsInstance(expr, ast.OpenDynamicUnionType)
        self.assertTrue(expr.not_null)


class TestDynamicPropertyValueType(unittest.TestCase):
    """Test suite for DynamicPropertyValueType parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_dynamic_property_value_type_property_value(self):
        """Test that the parser can parse PROPERTY VALUE type."""
        query = "PROPERTY VALUE"
        expr = self.helper.parse_single(query, ast.DynamicPropertyValueType)

        self.assertIsInstance(expr, ast.DynamicPropertyValueType)
        self.assertFalse(expr.any)
        self.assertFalse(expr.not_null)

    def test_dynamic_property_value_type_any_property_value(self):
        """Test that the parser can parse ANY PROPERTY VALUE type."""
        query = "ANY PROPERTY VALUE"
        expr = self.helper.parse_single(query, ast.DynamicPropertyValueType)

        self.assertIsInstance(expr, ast.DynamicPropertyValueType)
        self.assertTrue(expr.any)
        self.assertFalse(expr.not_null)

    def test_dynamic_property_value_type_property_value_not_null(self):
        """Test that the parser can parse PROPERTY VALUE NOT NULL type."""
        query = "PROPERTY VALUE NOT NULL"
        expr = self.helper.parse_single(query, ast.DynamicPropertyValueType)

        self.assertIsInstance(expr, ast.DynamicPropertyValueType)
        self.assertFalse(expr.any)
        self.assertTrue(expr.not_null)

    def test_dynamic_property_value_type_any_property_value_not_null(self):
        """Test that the parser can parse ANY PROPERTY VALUE NOT NULL type."""
        query = "ANY PROPERTY VALUE NOT NULL"
        expr = self.helper.parse_single(query, ast.DynamicPropertyValueType)

        self.assertIsInstance(expr, ast.DynamicPropertyValueType)
        self.assertTrue(expr.any)
        self.assertTrue(expr.not_null)

    def test_dynamic_property_value_type_as_value_type(self):
        """Test that the parser can parse PROPERTY VALUE as a ValueType."""
        query = "PROPERTY VALUE"
        expr = self.helper.parse_single(query, ast.ValueType)

        self.assertIsInstance(expr, ast.DynamicUnionType)
        self.assertIsInstance(expr, ast.DynamicPropertyValueType)


class TestClosedDynamicUnionType(unittest.TestCase):
    """Test suite for ClosedDynamicUnionType parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_closed_dynamic_union_type_component_list(self):
        """Test that the parser can parse a closed dynamic union type with component list."""
        query = "<INTEGER | STRING>"
        expr = self.helper.parse_single(query, ast.ClosedDynamicUnionType)

        self.assertIsInstance(expr, ast.ClosedDynamicUnionType)

    def test_closed_dynamic_union_type_any_value_with_components(self):
        """Test that the parser can parse ANY VALUE <component type list>."""
        query = "ANY VALUE <INTEGER | STRING>"
        expr = self.helper.parse_single(query, ast.ClosedDynamicUnionType)

        self.assertIsInstance(expr, ast.ClosedDynamicUnionType)


class TestOpenGraphReferenceValueType(unittest.TestCase):
    """Test suite for OpenGraphReferenceValueType parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_open_graph_reference_value_type_graph(self):
        """Test that the parser can parse GRAPH type."""
        query = "GRAPH"
        expr = self.helper.parse_single(query, ast.OpenGraphReferenceValueType)

        self.assertIsInstance(expr, ast.OpenGraphReferenceValueType)
        self.assertFalse(expr.any)
        self.assertFalse(expr.not_null)

    def test_open_graph_reference_value_type_any_graph(self):
        """Test that the parser can parse ANY GRAPH type."""
        query = "ANY GRAPH"
        expr = self.helper.parse_single(query, ast.OpenGraphReferenceValueType)

        self.assertIsInstance(expr, ast.OpenGraphReferenceValueType)
        self.assertTrue(expr.any)
        self.assertFalse(expr.not_null)

    def test_open_graph_reference_value_type_graph_not_null(self):
        """Test that the parser can parse GRAPH NOT NULL type."""
        query = "GRAPH NOT NULL"
        expr = self.helper.parse_single(query, ast.OpenGraphReferenceValueType)

        self.assertIsInstance(expr, ast.OpenGraphReferenceValueType)
        self.assertFalse(expr.any)
        self.assertTrue(expr.not_null)

    def test_open_graph_reference_value_type_any_graph_not_null(self):
        """Test that the parser can parse ANY GRAPH NOT NULL type."""
        query = "ANY GRAPH NOT NULL"
        expr = self.helper.parse_single(query, ast.OpenGraphReferenceValueType)

        self.assertIsInstance(expr, ast.OpenGraphReferenceValueType)
        self.assertTrue(expr.any)
        self.assertTrue(expr.not_null)

    def test_open_graph_reference_value_type_as_predefined_type(self):
        """Test that the parser can parse GRAPH as a PredefinedType."""
        query = "GRAPH"
        expr = self.helper.parse_single(query, ast.PredefinedType)

        self.assertIsInstance(expr, ast.ReferenceValueType)
        self.assertIsInstance(expr, ast.GraphReferenceValueType)
        self.assertIsInstance(expr, ast.OpenGraphReferenceValueType)


class TestOpenNodeReferenceValueType(unittest.TestCase):
    """Test suite for OpenNodeReferenceValueType parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_open_node_reference_value_type_node(self):
        """Test that the parser can parse NODE type."""
        query = "NODE"
        expr = self.helper.parse_single(query, ast.OpenNodeReferenceValueType)

        self.assertIsInstance(expr, ast.OpenNodeReferenceValueType)
        self.assertFalse(expr.any)
        self.assertFalse(expr.not_null)

    def test_open_node_reference_value_type_any_node(self):
        """Test that the parser can parse ANY NODE type."""
        query = "ANY NODE"
        expr = self.helper.parse_single(query, ast.OpenNodeReferenceValueType)

        self.assertIsInstance(expr, ast.OpenNodeReferenceValueType)
        self.assertTrue(expr.any)
        self.assertFalse(expr.not_null)

    def test_open_node_reference_value_type_node_not_null(self):
        """Test that the parser can parse NODE NOT NULL type."""
        query = "NODE NOT NULL"
        expr = self.helper.parse_single(query, ast.OpenNodeReferenceValueType)

        self.assertIsInstance(expr, ast.OpenNodeReferenceValueType)
        self.assertFalse(expr.any)
        self.assertTrue(expr.not_null)

    def test_open_node_reference_value_type_any_node_not_null(self):
        """Test that the parser can parse ANY NODE NOT NULL type."""
        query = "ANY NODE NOT NULL"
        expr = self.helper.parse_single(query, ast.OpenNodeReferenceValueType)

        self.assertIsInstance(expr, ast.OpenNodeReferenceValueType)
        self.assertTrue(expr.any)
        self.assertTrue(expr.not_null)


class TestOpenEdgeReferenceValueType(unittest.TestCase):
    """Test suite for OpenEdgeReferenceValueType parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_open_edge_reference_value_type_edge(self):
        """Test that the parser can parse EDGE type."""
        query = "EDGE"
        expr = self.helper.parse_single(query, ast.OpenEdgeReferenceValueType)

        self.assertIsInstance(expr, ast.OpenEdgeReferenceValueType)
        self.assertFalse(expr.any)
        self.assertFalse(expr.not_null)

    def test_open_edge_reference_value_type_any_edge(self):
        """Test that the parser can parse ANY EDGE type."""
        query = "ANY EDGE"
        expr = self.helper.parse_single(query, ast.OpenEdgeReferenceValueType)

        self.assertIsInstance(expr, ast.OpenEdgeReferenceValueType)
        self.assertTrue(expr.any)
        self.assertFalse(expr.not_null)

    def test_open_edge_reference_value_type_edge_not_null(self):
        """Test that the parser can parse EDGE NOT NULL type."""
        query = "EDGE NOT NULL"
        expr = self.helper.parse_single(query, ast.OpenEdgeReferenceValueType)

        self.assertIsInstance(expr, ast.OpenEdgeReferenceValueType)
        self.assertFalse(expr.any)
        self.assertTrue(expr.not_null)

    def test_open_edge_reference_value_type_any_edge_not_null(self):
        """Test that the parser can parse ANY EDGE NOT NULL type."""
        query = "ANY EDGE NOT NULL"
        expr = self.helper.parse_single(query, ast.OpenEdgeReferenceValueType)

        self.assertIsInstance(expr, ast.OpenEdgeReferenceValueType)
        self.assertTrue(expr.any)
        self.assertTrue(expr.not_null)


class TestClosedReferenceValueTypes(unittest.TestCase):
    """Test suite for closed reference value types parser."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = ParserTestHelper()

    def test_closed_node_reference_value_type(self):
        """Test that the parser can parse a closed node reference value type."""
        # Requires a node type specification
        query = "NODE TYPE Person () NOT NULL"
        expr = self.helper.parse_single(query, ast.ClosedNodeReferenceValueType)

        self.assertIsInstance(expr, ast.ClosedNodeReferenceValueType)
        self.assertTrue(expr.not_null)

    def test_closed_edge_reference_value_type(self):
        """Test that the parser can parse a closed edge reference value type."""
        query = "EDGE TYPE Rel (A)-[:Rel]->(B) NOT NULL"
        expr = self.helper.parse_single(query, ast.ClosedEdgeReferenceValueType)

        self.assertIsInstance(expr, ast.ClosedEdgeReferenceValueType)
        self.assertTrue(expr.not_null)
