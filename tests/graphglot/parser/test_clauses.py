"""Tests for clause parsing functionality."""

import unittest

from graphglot import ast

from .helpers import ParserTestHelper


class TestUseGraphClause(unittest.TestCase):
    """Test suite for USE graph clause parsing."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_use_graph(self):
        expr = self.helper.parse_single("USE myGraph", ast.UseGraphClause)
        self.assertIsInstance(expr, ast.UseGraphClause)
        self.assertIsNotNone(expr.graph_expression)


class TestAtSchemaClause(unittest.TestCase):
    """Test suite for AT schema clause parsing."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_at_schema(self):
        expr = self.helper.parse_single("AT HOME_SCHEMA", ast.AtSchemaClause)
        self.assertIsInstance(expr, ast.AtSchemaClause)
        self.assertIsNotNone(expr.schema_reference)


class TestSessionSetTimeZoneClause(unittest.TestCase):
    """Test suite for session set time zone clause parsing."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_set_time_zone(self):
        expr = self.helper.parse_single("TIME ZONE '+05:00'", ast.SessionSetTimeZoneClause)
        self.assertIsInstance(expr, ast.SessionSetTimeZoneClause)
        self.assertIsNotNone(expr.set_time_zone_value)


class TestSessionSetParameterClause(unittest.TestCase):
    """Test suite for session set parameter clause routing."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_routes_to_graph_parameter(self):
        expr = self.helper.parse_single("GRAPH $g = myGraph", ast.SessionSetParameterClause)
        self.assertIsInstance(expr, ast.SessionSetGraphParameterClause)

    def test_routes_to_value_parameter(self):
        expr = self.helper.parse_single("VALUE $v = 42", ast.SessionSetParameterClause)
        self.assertIsInstance(expr, ast.SessionSetValueParameterClause)


class TestSessionSetGraphParameterClause(unittest.TestCase):
    """Test suite for session set graph parameter clause parsing."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_graph_parameter(self):
        expr = self.helper.parse_single("GRAPH $g = myGraph", ast.SessionSetGraphParameterClause)
        self.assertIsInstance(expr, ast.SessionSetGraphParameterClause)
        self.assertIsNotNone(expr.session_set_parameter_name)
        self.assertIsNotNone(expr.opt_typed_graph_initializer)


class TestSessionSetBindingTableParameterClause(unittest.TestCase):
    """Test suite for session set binding table parameter clause parsing."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_binding_table_parameter(self):
        expr = self.helper.parse_single(
            "TABLE $t = {MATCH (n) RETURN n}",
            ast.SessionSetBindingTableParameterClause,
        )
        self.assertIsInstance(expr, ast.SessionSetBindingTableParameterClause)
        self.assertIsNotNone(expr.session_set_parameter_name)
        self.assertIsNotNone(expr.opt_typed_binding_table_initializer)


class TestSessionSetValueParameterClause(unittest.TestCase):
    """Test suite for session set value parameter clause parsing."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_value_parameter(self):
        expr = self.helper.parse_single("VALUE $v = 42", ast.SessionSetValueParameterClause)
        self.assertIsInstance(expr, ast.SessionSetValueParameterClause)
        self.assertIsNotNone(expr.session_set_parameter_name)
        self.assertIsNotNone(expr.opt_typed_value_initializer)


class TestVariableScopeClause(unittest.TestCase):
    """Test suite for variable scope clause parsing."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_variable_scope_with_vars(self):
        expr = self.helper.parse_single("(x, y)", ast.VariableScopeClause)
        self.assertIsInstance(expr, ast.VariableScopeClause)
        self.assertIsNotNone(expr.binding_variable_reference_list)

    def test_variable_scope_empty(self):
        expr = self.helper.parse_single("()", ast.VariableScopeClause)
        self.assertIsInstance(expr, ast.VariableScopeClause)
        self.assertIsNone(expr.binding_variable_reference_list)


class TestParenthesizedPathPatternWhereClause(unittest.TestCase):
    """Test suite for parenthesized path pattern where clause parsing."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_where_clause(self):
        expr = self.helper.parse_single("WHERE n.age > 30", ast.ParenthesizedPathPatternWhereClause)
        self.assertIsInstance(expr, ast.ParenthesizedPathPatternWhereClause)
        self.assertIsNotNone(expr.search_condition)
