"""Tests for data-modifying statement parsing functionality."""

import unittest

from graphglot import ast

from .helpers import ParserTestHelper


class TestInsertStatement(unittest.TestCase):
    """Test suite for INSERT statement parser."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_insert_empty_node(self):
        """INSERT with an empty node pattern."""
        query = "INSERT ()"
        expr = self.helper.parse_single(query, ast.InsertStatement)

        self.assertIsInstance(expr, ast.InsertStatement)
        self.assertIsInstance(expr.insert_graph_pattern, ast.InsertGraphPattern)

    def test_insert_single_node(self):
        """INSERT with a single node pattern."""
        query = "INSERT (n)"
        expr = self.helper.parse_single(query, ast.InsertStatement)

        self.assertIsInstance(expr, ast.InsertStatement)
        self.assertIsInstance(expr.insert_graph_pattern, ast.InsertGraphPattern)

    def test_insert_single_node_with_property_specifications(self):
        """INSERT with a single node pattern with property specifications."""
        query = "INSERT (n {name: 'Alice', age: 30})"
        expr = self.helper.parse_single(query, ast.InsertStatement)

        self.assertIsInstance(expr, ast.InsertStatement)
        self.assertIsInstance(expr.insert_graph_pattern, ast.InsertGraphPattern)

    def test_insert_node_list(self):
        """INSERT with a node list pattern."""
        query = "INSERT (a), (b), (c)"
        expr = self.helper.parse_single(query, ast.InsertStatement)

        self.assertIsInstance(expr, ast.InsertStatement)

    def test_insert_single_node_with_label(self):
        """INSERT with a single node pattern."""
        query = "INSERT (n:Person)"
        expr = self.helper.parse_single(query, ast.InsertStatement)

        self.assertIsInstance(expr, ast.InsertStatement)
        self.assertIsInstance(expr.insert_graph_pattern, ast.InsertGraphPattern)

    def test_insert_empty_node_with_label(self):
        """INSERT with a single node pattern."""
        query = "INSERT (:Person)"
        expr = self.helper.parse_single(query, ast.InsertStatement)

        self.assertIsInstance(expr, ast.InsertStatement)
        self.assertIsInstance(expr.insert_graph_pattern, ast.InsertGraphPattern)

    def test_insert_simple_edge(self):
        """INSERT with a node-edge-node pattern."""
        query = "INSERT (n)-[r]->(m)"
        expr = self.helper.parse_single(query, ast.InsertStatement)

        self.assertIsInstance(expr, ast.InsertStatement)
        self.assertIsInstance(expr.insert_graph_pattern, ast.InsertGraphPattern)


class TestSetStatement(unittest.TestCase):
    """Test suite for SET statement parser."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_set_single_property(self):
        """SET with a single property assignment."""
        query = "SET n.age = 30"
        expr = self.helper.parse_single(query, ast.SetStatement)

        self.assertIsInstance(expr, ast.SetStatement)
        self.assertIsInstance(expr.set_item_list, ast.SetItemList)
        self.assertGreaterEqual(len(expr.set_item_list.list_set_item), 1)
        self.assertIsInstance(
            expr.set_item_list.list_set_item[0],
            (ast.SetPropertyItem, ast.SetAllPropertiesItem, ast.SetLabelItem),
        )

    def test_set_single_all_properties(self):
        """SET with a single all properties assignment."""
        query = "SET n = {name: 'Alice', age: 30}"
        expr = self.helper.parse_single(query, ast.SetStatement)

        self.assertIsInstance(expr, ast.SetStatement)
        self.assertIsInstance(expr.set_item_list, ast.SetItemList)

    def test_set_single_label(self):
        """SET with a single label assignment."""
        query = "SET n:Person"
        expr = self.helper.parse_single(query, ast.SetStatement)

        self.assertIsInstance(expr, ast.SetStatement)
        self.assertIsInstance(expr.set_item_list, ast.SetItemList)

    def test_set_multiple_items(self):
        """SET with multiple items separated by commas."""
        query = "SET n.age = 30, n:Person"
        expr = self.helper.parse_single(query, ast.SetStatement)

        self.assertIsInstance(expr, ast.SetStatement)
        self.assertIsInstance(expr.set_item_list, ast.SetItemList)
        self.assertGreaterEqual(len(expr.set_item_list.list_set_item), 2)


class TestRemoveStatement(unittest.TestCase):
    """Test suite for REMOVE statement parser."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_remove_single_property(self):
        """REMOVE with a single property."""
        query = "REMOVE n.age"
        expr = self.helper.parse_single(query, ast.RemoveStatement)

        self.assertIsInstance(expr, ast.RemoveStatement)
        self.assertIsInstance(expr.remove_item_list, ast.RemoveItemList)
        self.assertGreaterEqual(len(expr.remove_item_list.list_remove_item), 1)
        self.assertIsInstance(
            expr.remove_item_list.list_remove_item[0],
            (ast.RemovePropertyItem, ast.RemoveLabelItem),
        )

    def test_remove_single_label(self):
        """REMOVE with a single label."""
        query = "REMOVE n:Person"
        expr = self.helper.parse_single(query, ast.RemoveStatement)

        self.assertIsInstance(expr, ast.RemoveStatement)
        self.assertIsInstance(expr.remove_item_list, ast.RemoveItemList)
        self.assertGreaterEqual(len(expr.remove_item_list.list_remove_item), 1)


class TestDeleteStatement(unittest.TestCase):
    """Test suite for DELETE statement parser."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_delete_default_mode(self):
        """DELETE without explicit mode should default to NODETACH."""
        query = "DELETE n"
        expr = self.helper.parse_single(query, ast.DeleteStatement)

        self.assertIsInstance(expr, ast.DeleteStatement)
        self.assertEqual(expr.mode, ast.DeleteStatement.Mode.NODETACH)
        self.assertIsInstance(expr.delete_item_list, ast.DeleteItemList)
        self.assertGreaterEqual(len(expr.delete_item_list.list_delete_item), 1)

    def test_delete_with_detach(self):
        """DELETE with DETACH mode."""
        query = "DETACH DELETE n"
        expr = self.helper.parse_single(query, ast.DeleteStatement)

        self.assertIsInstance(expr, ast.DeleteStatement)
        self.assertEqual(expr.mode, ast.DeleteStatement.Mode.DETACH)

    def test_delete_with_nodetach(self):
        """DELETE with NODETACH mode."""
        query = "NODETACH DELETE n"
        expr = self.helper.parse_single(query, ast.DeleteStatement)

        self.assertIsInstance(expr, ast.DeleteStatement)
        self.assertEqual(expr.mode, ast.DeleteStatement.Mode.NODETACH)
