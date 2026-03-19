import unittest

from graphglot import ast

from .helpers import ParserTestHelper


class TestCreateSchemaStatement(unittest.TestCase):
    def setUp(self) -> None:
        self.helper = ParserTestHelper()

    def test_numeric_value_expression(self):
        query = "1"
        expr = self.helper.parse_single(query, ast.CommonValueExpression)
        self.assertIsInstance(expr, ast.CommonValueExpression)

    def test_numeric_value_function(self):
        query = "CHAR_LENGTH(n)"
        expr = self.helper.parse_single(query, ast.CommonValueExpression)
        self.assertIsInstance(expr, ast.CommonValueExpression)

    def test_string_value_expression(self):
        query = '"Hello, World!"'
        expr = self.helper.parse_single(query, ast.CommonValueExpression)
        self.assertIsInstance(expr, ast.CommonValueExpression)

    def test_string_value_function(self):
        query = 'LEFT("Hello, World!", 5)'
        expr = self.helper.parse_single(query, ast.CommonValueExpression)
        self.assertIsInstance(expr, ast.CommonValueExpression)

    def test_datetime_value_expression(self):
        query = "DATE '2026-01-01'"
        expr = self.helper.parse_single(query, ast.CommonValueExpression)
        self.assertIsInstance(expr, ast.CommonValueExpression)

    def test_datetime_value_function(self):
        query = "CURRENT_TIMESTAMP"
        expr = self.helper.parse_single(query, ast.CommonValueExpression)
        self.assertIsInstance(expr, ast.CommonValueExpression)

    def test_duration_value_expression(self):
        query = "DURATION 'PT1H'"
        expr = self.helper.parse_single(query, ast.CommonValueExpression)
        self.assertIsInstance(expr, ast.CommonValueExpression)

    def test_duration_addition(self):
        query = "DURATION 'PT1H' + DURATION 'PT2H'"
        expr = self.helper.parse_single(query, ast.DurationValueExpression)
        self.assertIsInstance(expr, ast.DurationValueExpression)
        # Verify it has the expected structure with steps
        self.assertIsNotNone(expr.steps)
        self.assertEqual(len(expr.steps), 1)
        self.assertEqual(expr.steps[0].sign, ast.Sign.PLUS_SIGN)

    def test_duration_subtraction(self):
        query = "DURATION 'PT1H' - DURATION 'PT2H'"
        expr = self.helper.parse_single(query, ast.DurationValueExpression)
        self.assertIsInstance(expr, ast.DurationValueExpression)
        # Verify it has the expected structure with steps
        self.assertIsNotNone(expr.steps)
        self.assertEqual(len(expr.steps), 1)
        self.assertEqual(expr.steps[0].sign, ast.Sign.MINUS_SIGN)

    def test_duration_between(self):
        query = "DURATION_BETWEEN(a, b)"
        expr = self.helper.parse_single(query, ast.DurationValueExpression)
        self.assertIsInstance(expr, ast.DurationValueExpression)
        self.assertIsInstance(expr.base, ast.DatetimeSubtraction)

    def test_abs_with_duration_is_not_numeric(self):
        """ABS with duration argument should parse as ArithmeticAbsoluteValueFunction,
        not as AbsoluteValueExpression (which is a NumericValueFunction).

        At parse time, we can't determine if ABS(x) returns numeric or duration,
        so it should use the ambiguous ArithmeticAbsoluteValueFunction type.
        """
        query = "ABS(DURATION 'PT1H')"
        # Parse via CommonValueExpression to verify the fast-path doesn't
        # route to NumericValueExpression
        expr = self.helper.parse_single(query, ast.CommonValueExpression)
        self.assertIsInstance(expr, ast.ArithmeticValueExpression)
        # Navigate to the ArithmeticAbsoluteValueFunction
        arithmetic_primary = expr.base.base.arithmetic_primary
        self.assertIsInstance(arithmetic_primary, ast.ArithmeticAbsoluteValueFunction)
        # Verify it's NOT an AbsoluteValueExpression (which is NumericValueFunction)
        self.assertNotIsInstance(arithmetic_primary, ast.AbsoluteValueExpression)

    def test_duration_value_function(self):
        query = "DURATION( { d: 'PT1H' } )"
        # expr = self.helper.parse_single(query, ast.DurationValueExpression) # This works
        expr = self.helper.parse_single(query, ast.CommonValueExpression)
        self.assertIsInstance(expr, ast.CommonValueExpression)

    def test_list_value_expression(self):
        query = "[1, 2, 3]"
        expr = self.helper.parse_single(query, ast.ListValueExpression)
        self.assertIsInstance(expr, ast.ListValueExpression)

    def test_list_value_function(self):
        query = "TRIM([1, 2, 3], 2)"
        expr = self.helper.parse_single(query, ast.ListValueFunction)
        self.assertIsInstance(expr, ast.ListValueFunction)

    def test_graph_reference_value_expression(self):
        query = "GRAPH my_graph"
        expr = self.helper.parse_single(query, ast.CommonValueExpression)
        self.assertIsInstance(expr, ast.GraphReferenceValueExpression)

    def test_binding_table_reference_value_expression(self):
        query = "TABLE { MATCH (n) RETURN n }"
        expr = self.helper.parse_single(query, ast.CommonValueExpression)
        self.assertIsInstance(expr, ast.BindingTableReferenceValueExpression)

    def test_let_value_expression(self):
        query = "LET x = 1 IN x + 1 END"
        expr = self.helper.parse_single(query, ast.CommonValueExpression)
        self.assertIsInstance(expr, ast.CommonValueExpression)

    def test_arithmetic_value_expression(self):
        query = "a + b"
        expr = self.helper.parse_single(query, ast.CommonValueExpression)
        self.assertIsInstance(expr, ast.ArithmeticValueExpression)

    def test_single_identifier(self):
        query = "a"
        expr = self.helper.parse_single(query, ast.CommonValueExpression)
        self.assertIsInstance(expr, ast.ArithmeticValueExpression)

    def test_string_concatenation(self):
        """String concatenation with || operator."""
        query = "'hello' || 'world'"
        expr = self.helper.parse_single(query, ast.CommonValueExpression)
        self.assertIsInstance(expr, ast.CharacterStringValueExpression)
        self.assertEqual(len(expr.list_character_string_value_expression), 2)

    def test_list_concatenation(self):
        """List concatenation with || operator."""
        query = "[1, 2] || [3, 4]"
        expr = self.helper.parse_single(query, ast.CommonValueExpression)
        self.assertIsInstance(expr, ast.ListValueExpression)
        self.assertEqual(len(expr.list_list_primary), 2)

    def test_path_concatenation_with_constructor(self):
        """Path concatenation with || operator using PATH constructor."""
        query = "PATH [a] || PATH [b]"
        expr = self.helper.parse_single(query, ast.CommonValueExpression)
        self.assertIsInstance(expr, ast.PathValueExpression)
        self.assertEqual(len(expr.list_path_value_primary), 2)

    def test_identifier_concatenation(self):
        """Identifier concatenation with || operator.

        When parsing `a || b`, the parser detects the || operator after
        the first operand and parses as ConcatenationValueExpression (generic).
        """
        query = "a || b"
        expr = self.helper.parse_single(query, ast.CommonValueExpression)
        self.assertIsInstance(expr, ast.ConcatenationValueExpression)
        self.assertEqual(len(expr.operands), 2)
        self.assertIsInstance(expr.operands[0], ast.BindingVariableReference)
        self.assertIsInstance(expr.operands[1], ast.BindingVariableReference)
