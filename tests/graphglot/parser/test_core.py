"""Tests for core parser functionality."""

import unittest

from graphglot import ast

from .helpers import ParserTestHelper


class TestProgramActivity(unittest.TestCase):
    """Test suite for program activity parsing."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_session_activity(self):
        expr = self.helper.parse_single("SESSION SET SCHEMA /my_schemas/foo", ast.ProgramActivity)
        self.assertIsInstance(expr, ast.SessionActivity)

    def test_transaction_activity(self):
        expr = self.helper.parse_single(
            "START TRANSACTION READ ONLY MATCH (n) RETURN n COMMIT",
            ast.ProgramActivity,
        )
        self.assertIsInstance(expr, ast.TransactionActivity)


class TestTransactionCharacteristics(unittest.TestCase):
    """Test suite for transaction characteristics parsing."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_read_only(self):
        expr = self.helper.parse_single("READ ONLY", ast.TransactionCharacteristics)
        self.assertIsInstance(expr, ast.TransactionCharacteristics)
        self.assertEqual(
            expr.list_transaction_mode[0],
            ast.TransactionCharacteristics.TransactionMode.READ_ONLY,
        )

    def test_read_write(self):
        expr = self.helper.parse_single("READ WRITE", ast.TransactionCharacteristics)
        self.assertIsInstance(expr, ast.TransactionCharacteristics)
        self.assertEqual(
            expr.list_transaction_mode[0],
            ast.TransactionCharacteristics.TransactionMode.READ_WRITE,
        )


class TestStatementBlock(unittest.TestCase):
    """Test suite for statement block parsing."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_single_statement(self):
        expr = self.helper.parse_single("MATCH (n) RETURN n", ast.StatementBlock)
        self.assertIsInstance(expr, ast.StatementBlock)
        self.assertIsNotNone(expr.statement)

    def test_multiple_statements_with_next(self):
        expr = self.helper.parse_single(
            "MATCH (n) RETURN n NEXT MATCH (m) RETURN m", ast.StatementBlock
        )
        self.assertIsInstance(expr, ast.StatementBlock)
        self.assertIsNotNone(expr.statement)
        self.assertIsNotNone(expr.list_next_statement)
        self.assertEqual(len(expr.list_next_statement), 1)


class TestProcedureSpecification(unittest.TestCase):
    """Test suite for procedure specification parsing."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_query_specification(self):
        expr = self.helper.parse_single("MATCH (n) RETURN n", ast.ProcedureSpecification)
        self.assertIsInstance(expr, ast.ProcedureSpecification)


class TestNestedQuerySpecification(unittest.TestCase):
    """Test suite for nested query specification parsing."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_nested_query(self):
        expr = self.helper.parse_single("{MATCH (n) RETURN n}", ast.NestedQuerySpecification)
        self.assertIsInstance(expr, ast.NestedQuerySpecification)
        self.assertIsNotNone(expr.query_specification)


class TestBindingVariableDefinition(unittest.TestCase):
    """Test suite for binding variable definition routing."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_value_variable_definition(self):
        expr = self.helper.parse_single("VALUE x = 1", ast.BindingVariableDefinition)
        self.assertIsInstance(expr, ast.ValueVariableDefinition)

    def test_graph_variable_definition(self):
        expr = self.helper.parse_single("GRAPH g = myGraph", ast.BindingVariableDefinition)
        self.assertIsInstance(expr, ast.GraphVariableDefinition)


class TestGraphInitializer(unittest.TestCase):
    """Test suite for graph initializer parsing."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_graph_initializer(self):
        expr = self.helper.parse_single("= myGraph", ast.GraphInitializer)
        self.assertIsInstance(expr, ast.GraphInitializer)
        self.assertIsNotNone(expr.graph_expression)


class TestOptTypedGraphInitializer(unittest.TestCase):
    """Test suite for opt typed graph initializer parsing."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_untyped(self):
        expr = self.helper.parse_single("= myGraph", ast.OptTypedGraphInitializer)
        self.assertIsInstance(expr, ast.OptTypedGraphInitializer)
        self.assertIsNotNone(expr.graph_initializer)
        self.assertIsNone(expr.typed_graph_reference_value_type)


class TestOptTypedBindingTableInitializer(unittest.TestCase):
    """Test suite for opt typed binding table initializer parsing."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_untyped(self):
        expr = self.helper.parse_single(
            "= {MATCH (n) RETURN n}", ast.OptTypedBindingTableInitializer
        )
        self.assertIsInstance(expr, ast.OptTypedBindingTableInitializer)
        self.assertIsNotNone(expr.binding_table_initializer)
        self.assertIsNone(expr.typed_binding_table_reference_value_type)


class TestOptTypedValueInitializer(unittest.TestCase):
    """Test suite for opt typed value initializer parsing."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_untyped(self):
        expr = self.helper.parse_single("= 42", ast.OptTypedValueInitializer)
        self.assertIsInstance(expr, ast.OptTypedValueInitializer)
        self.assertIsNotNone(expr.value_initializer)
        self.assertIsNone(expr.typed_value_type)


class TestSetQuantifier(unittest.TestCase):
    """Test suite for SetQuantifier parsing."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_distinct(self):
        expr = self.helper.parse_single("DISTINCT", ast.SetQuantifier)
        self.assertIsInstance(expr, ast.SetQuantifier)
        self.assertEqual(expr.set_quantifier, ast.SetQuantifier.Quantifier.DISTINCT)

    def test_all(self):
        expr = self.helper.parse_single("ALL", ast.SetQuantifier)
        self.assertIsInstance(expr, ast.SetQuantifier)
        self.assertEqual(expr.set_quantifier, ast.SetQuantifier.Quantifier.ALL)


class TestOrderingSpecification(unittest.TestCase):
    """Test suite for OrderingSpecification parsing."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_asc(self):
        expr = self.helper.parse_single("ASC", ast.OrderingSpecification)
        self.assertIsInstance(expr, ast.OrderingSpecification)
        self.assertEqual(expr.ordering_specification, ast.OrderingSpecification.Order.ASC)

    def test_desc(self):
        expr = self.helper.parse_single("DESC", ast.OrderingSpecification)
        self.assertIsInstance(expr, ast.OrderingSpecification)
        self.assertEqual(expr.ordering_specification, ast.OrderingSpecification.Order.DESC)


class TestBindingVariableDefinitionBlock(unittest.TestCase):
    """Test suite for binding variable definition block parsing."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_single_definition(self):
        expr = self.helper.parse_single("VALUE x = 1", ast.BindingVariableDefinitionBlock)
        self.assertIsInstance(expr, ast.BindingVariableDefinitionBlock)
        self.assertEqual(len(expr.list_binding_variable_definition), 1)

    def test_multiple_definitions(self):
        expr = self.helper.parse_single(
            "VALUE x = 1 VALUE y = 2", ast.BindingVariableDefinitionBlock
        )
        self.assertIsInstance(expr, ast.BindingVariableDefinitionBlock)
        self.assertEqual(len(expr.list_binding_variable_definition), 2)
