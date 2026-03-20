"""Parser coverage tests for AST types not exercised by other test suites.

Covers simplified path patterns, focused queries, temporal functions, procedures,
path variables, binding tables, ISO8601 duration components, numeric intermediaries,
and stub/unreachable parsers.
"""

import unittest

import pytest

from graphglot import ast

from .helpers import ParserTestHelper


class TestSimplifiedPatternVariants(unittest.TestCase):
    """Simplified path pattern types: conjunction, concatenation, quantified, overrides."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_simplified_conjunction(self):
        """SimplifiedConjunction via & operator between label names."""
        expr = self.helper.parse_single("KNOWS & FRIEND", ast.SimplifiedConjunction)
        self.assertIsInstance(expr, ast.SimplifiedConjunction)

    def test_simplified_concatenation(self):
        """SimplifiedConcatenation via juxtaposition of label names."""
        expr = self.helper.parse_single("KNOWS FRIEND", ast.SimplifiedConcatenation)
        self.assertIsInstance(expr, ast.SimplifiedConcatenation)

    def test_simplified_quantified(self):
        """SimplifiedQuantified via label name with graph pattern quantifier."""
        expr = self.helper.parse_single("KNOWS{1,5}", ast.SimplifiedQuantified)
        self.assertIsInstance(expr, ast.SimplifiedQuantified)
        self.assertIsInstance(expr.graph_pattern_quantifier, ast.GeneralQuantifier)

    def test_simplified_questioned(self):
        """SimplifiedQuestioned via label name with ? quantifier."""
        expr = self.helper.parse_single("KNOWS?", ast.SimplifiedQuestioned)
        self.assertIsInstance(expr, ast.SimplifiedQuestioned)

    def test_simplified_defaulting_left_or_right(self):
        """SimplifiedDefaultingLeftOrRight via -/ ... /-> syntax."""
        expr = self.helper.parse_single("-/ KNOWS /->", ast.SimplifiedDefaultingLeftOrRight)
        self.assertIsInstance(expr, ast.SimplifiedDefaultingLeftOrRight)

    def test_simplified_override_right(self):
        """SimplifiedOverrideRight via label name with > bracket."""
        expr = self.helper.parse_single("KNOWS >", ast.SimplifiedOverrideRight)
        self.assertIsInstance(expr, ast.SimplifiedOverrideRight)

    def test_simplified_override_left_or_right(self):
        """SimplifiedOverrideLeftOrRight via < label > brackets."""
        expr = self.helper.parse_single("< KNOWS >", ast.SimplifiedOverrideLeftOrRight)
        self.assertIsInstance(expr, ast.SimplifiedOverrideLeftOrRight)


class TestFocusedQueries(unittest.TestCase):
    """Focused query statement types using USE graph clause."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_focused_primitive_result_statement(self):
        """USE graph RETURN — produces FocusedPrimitiveResultStatement."""
        expr = self.helper.parse_single("USE myGraph RETURN 1", ast.GqlProgram)
        self.assertIsInstance(expr, ast.GqlProgram)

    def test_focused_primitive_result_statement_direct(self):
        """Direct parse of FocusedPrimitiveResultStatement."""
        expr = self.helper.parse_single("USE g RETURN 1", ast.FocusedPrimitiveResultStatement)
        self.assertIsInstance(expr, ast.FocusedPrimitiveResultStatement)
        self.assertIsNotNone(expr.use_graph_clause)
        self.assertIsNotNone(expr.primitive_result_statement)

    def test_focused_linear_query_and_primitive_result_statement_part(self):
        """Direct parse of FocusedLinearQueryAndPrimitiveResultStatementPart."""
        expr = self.helper.parse_single(
            "USE g MATCH (n) RETURN n",
            ast.FocusedLinearQueryAndPrimitiveResultStatementPart,
        )
        self.assertIsInstance(expr, ast.FocusedLinearQueryAndPrimitiveResultStatementPart)
        self.assertIsNotNone(expr.use_graph_clause)
        self.assertIsNotNone(expr.simple_linear_query_statement)
        self.assertIsNotNone(expr.primitive_result_statement)

    def test_focused_nested_query_specification(self):
        """USE graph { query } — produces FocusedNestedQuerySpecification."""
        expr = self.helper.parse_single("USE myGraph { MATCH (n) RETURN n }", ast.GqlProgram)
        self.assertIsInstance(expr, ast.GqlProgram)

    def test_focused_nested_query_specification_direct(self):
        """Direct parse of FocusedNestedQuerySpecification."""
        expr = self.helper.parse_single(
            "USE g { MATCH (n) RETURN n }", ast.FocusedNestedQuerySpecification
        )
        self.assertIsInstance(expr, ast.FocusedNestedQuerySpecification)
        self.assertIsNotNone(expr.use_graph_clause)
        self.assertIsNotNone(expr.nested_query_specification)

    def test_focused_nested_data_modifying_procedure_specification(self):
        """Direct parse of FocusedNestedDataModifyingProcedureSpecification."""
        expr = self.helper.parse_single(
            "USE g { INSERT (:Person) }",
            ast.FocusedNestedDataModifyingProcedureSpecification,
        )
        self.assertIsInstance(expr, ast.FocusedNestedDataModifyingProcedureSpecification)
        self.assertIsNotNone(expr.use_graph_clause)
        self.assertIsNotNone(expr.nested_data_modifying_procedure_specification)


class TestTemporalAndDurationFunctions(unittest.TestCase):
    """LocaltimeFunction, LocaldatetimeFunction, DurationAbsoluteValueFunction."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_localtime_function(self):
        """LocaltimeFunction parses with no arguments (optional parameters)."""
        expr = self.helper.parse_single("", ast.LocaltimeFunction)
        self.assertIsInstance(expr, ast.LocaltimeFunction)
        self.assertIsNone(expr.time_function_parameters)

    def test_localdatetime_function(self):
        """LocaldatetimeFunction should parse LOCAL_TIMESTAMP or LOCAL_DATETIME(...)."""
        expr = self.helper.parse_single("LOCAL_TIMESTAMP", ast.LocaldatetimeFunction)
        self.assertIsInstance(expr, ast.LocaldatetimeFunction)

    def test_duration_absolute_value_function(self):
        """DurationAbsoluteValueFunction via ABS(DURATION '...')."""
        expr = self.helper.parse_single("ABS(DURATION 'P1Y')", ast.DurationAbsoluteValueFunction)
        self.assertIsInstance(expr, ast.DurationAbsoluteValueFunction)
        self.assertIsNotNone(expr.duration_value_expression)


class TestProcedureAndYield(unittest.TestCase):
    """NestedDataModifyingProcedureSpecification and YieldItemAlias."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_nested_data_modifying_procedure_specification(self):
        """Direct parse of NestedDataModifyingProcedureSpecification."""
        expr = self.helper.parse_single(
            "{ INSERT (:Person) }", ast.NestedDataModifyingProcedureSpecification
        )
        self.assertIsInstance(expr, ast.NestedDataModifyingProcedureSpecification)

    def test_yield_item_alias(self):
        """CALL proc YIELD col AS alias — produces YieldItemAlias."""
        expr = self.helper.parse_single("CALL myProc() YIELD col1 AS x RETURN x", ast.GqlProgram)
        self.assertIsInstance(expr, ast.GqlProgram)

    def test_yield_item_alias_direct(self):
        """Direct parse of YieldItemAlias."""
        expr = self.helper.parse_single("AS x", ast.YieldItemAlias)
        self.assertIsInstance(expr, ast.YieldItemAlias)
        self.assertIsNotNone(expr.binding_variable)


class TestPathAndGraphVariables(unittest.TestCase):
    """PathOrSubpathVariable, GraphPatternVariable."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_path_or_subpath_variable(self):
        """PathOrSubpathVariable parses an identifier."""
        expr = self.helper.parse_single("p", ast.PathOrSubpathVariable)
        self.assertIsInstance(expr, ast.Identifier)

    def test_graph_pattern_variable(self):
        """GraphPatternVariable parses an identifier."""
        expr = self.helper.parse_single("x", ast.GraphPatternVariable)
        self.assertIsInstance(expr, ast.Identifier)

    def test_path_variable_in_match(self):
        """MATCH p = (a)-[e]->(b) RETURN p — path variable assignment."""
        expr = self.helper.parse_single("MATCH p = (a)-[e]->(b) RETURN p", ast.GqlProgram)
        self.assertIsInstance(expr, ast.GqlProgram)


class TestBindingTables(unittest.TestCase):
    """BindingTableName, BindingTableReference."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_binding_table_name(self):
        """BindingTableName parses a regular identifier."""
        expr = self.helper.parse_single("myTable", ast.BindingTableName)
        self.assertIsInstance(expr, ast.Identifier)

    def test_binding_table_in_for(self):
        """FOR t IN myTable — binding table in FOR statement context."""
        expr = self.helper.parse_single("FOR t IN myTable RETURN t", ast.GqlProgram)
        self.assertIsInstance(expr, ast.GqlProgram)

    @pytest.mark.xfail(
        reason="BindingTableReference requires catalog path or delimited name",
        raises=Exception,
    )
    def test_binding_table_reference_direct(self):
        """Direct parse of BindingTableReference with catalog path."""
        self.helper.parse_single("/ myTable", ast.BindingTableReference)


class TestByteStringSubstringFunction(unittest.TestCase):
    """ByteStringSubstringFunction via LEFT/RIGHT byte string operations."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_byte_string_substring_left(self):
        """LEFT(X'DEADBEEF', 2) — produces SubstringFunction via GQL."""
        expr = self.helper.parse_single("RETURN LEFT(X'DEADBEEF', 2)", ast.GqlProgram)
        self.assertIsInstance(expr, ast.GqlProgram)

    def test_byte_string_substring_direct(self):
        """Direct parse of ByteStringSubstringFunction."""
        expr = self.helper.parse_single("LEFT(X'DEAD', 2)", ast.ByteStringSubstringFunction)
        self.assertIsInstance(expr, ast.ByteStringSubstringFunction)
        self.assertEqual(expr.mode, ast.ByteStringSubstringFunction.Mode.LEFT)


class TestEndpointPairPointingLeft(unittest.TestCase):
    """EndpointPairPointingLeft for graph type DDL."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_endpoint_pair_pointing_left(self):
        """(dest <- src) — endpoint pair pointing left in graph DDL."""
        expr = self.helper.parse_single("( a <- b )", ast.EndpointPairPointingLeft)
        self.assertIsInstance(expr, ast.EndpointPairPointingLeft)


class TestIso8601Parsers(unittest.TestCase):
    """ISO8601 duration component parsers (dead code — never called by grammar chain)."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_iso8601_sint_positive(self):
        """Iso8601Sint parses an unsigned integer."""
        expr = self.helper.parse_single("5", ast.Iso8601Sint)
        self.assertIsInstance(expr, ast.Iso8601Sint)
        self.assertFalse(expr.minus_sign)

    def test_iso8601_sint_negative(self):
        """Iso8601Sint parses a negative integer."""
        expr = self.helper.parse_single("-3", ast.Iso8601Sint)
        self.assertIsInstance(expr, ast.Iso8601Sint)
        self.assertTrue(expr.minus_sign)

    def test_iso8601_years(self):
        """Iso8601Years wraps Iso8601Sint (Y token not consumed by parser)."""
        expr = self.helper.parse_single("5", ast.Iso8601Years)
        self.assertIsInstance(expr, ast.Iso8601Years)
        self.assertIsNotNone(expr.iso8601_sint)

    def test_iso8601_months(self):
        """Iso8601Months wraps Iso8601Sint (M token not consumed by parser)."""
        expr = self.helper.parse_single("5", ast.Iso8601Months)
        self.assertIsInstance(expr, ast.Iso8601Months)

    def test_iso8601_days(self):
        """Iso8601Days wraps Iso8601Sint (D token not consumed by parser)."""
        expr = self.helper.parse_single("5", ast.Iso8601Days)
        self.assertIsInstance(expr, ast.Iso8601Days)

    def test_iso8601_hours(self):
        """Iso8601Hours wraps Iso8601Sint (H token not consumed by parser)."""
        expr = self.helper.parse_single("5", ast.Iso8601Hours)
        self.assertIsInstance(expr, ast.Iso8601Hours)

    def test_iso8601_minutes(self):
        """Iso8601Minutes wraps Iso8601Sint (M token not consumed by parser)."""
        expr = self.helper.parse_single("5", ast.Iso8601Minutes)
        self.assertIsInstance(expr, ast.Iso8601Minutes)

    def test_iso8601_seconds(self):
        """Iso8601Seconds wraps Iso8601Sint with optional fractional part."""
        expr = self.helper.parse_single("5", ast.Iso8601Seconds)
        self.assertIsInstance(expr, ast.Iso8601Seconds)
        self.assertIsNone(expr.iso8601_uint)

    def test_iso8601_years_and_months(self):
        """Iso8601YearsAndMonths combines optional years and months."""
        expr = self.helper.parse_single("5 5", ast.Iso8601YearsAndMonths)
        self.assertIsInstance(expr, ast.Iso8601YearsAndMonths)
        self.assertIsNotNone(expr.iso8601_years)
        self.assertIsNotNone(expr.iso8601_months)

    def test_iso8601_days_and_time(self):
        """Iso8601DaysAndTime combines optional days, hours, minutes, seconds."""
        expr = self.helper.parse_single("5 5 5 5", ast.Iso8601DaysAndTime)
        self.assertIsInstance(expr, ast.Iso8601DaysAndTime)
        self.assertIsNotNone(expr.iso8601_days)


class TestNumericIntermediaries(unittest.TestCase):
    """Mantissa, SignedDecimalInteger — numeric parser intermediaries."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_mantissa(self):
        """Mantissa should parse an unsigned decimal."""
        self.helper.parse_single("42", ast.Mantissa)

    def test_signed_decimal_integer_positive(self):
        """SignedDecimalInteger parses an unsigned integer (positive by default)."""
        expr = self.helper.parse_single("5", ast.SignedDecimalInteger)
        self.assertIsInstance(expr, ast.SignedDecimalInteger)
        self.assertEqual(expr.sign, ast.Sign.PLUS_SIGN)

    def test_signed_decimal_integer_negative(self):
        """SignedDecimalInteger parses a negative integer."""
        expr = self.helper.parse_single("-5", ast.SignedDecimalInteger)
        self.assertIsInstance(expr, ast.SignedDecimalInteger)
        self.assertEqual(expr.sign, ast.Sign.MINUS_SIGN)


class TestCatalogBindingTable(unittest.TestCase):
    """CatalogBindingTableParentAndName parser."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_catalog_binding_table_parent_and_name(self):
        """CatalogBindingTableParentAndName with bare table name."""
        self.helper.parse_single("myTable", ast.CatalogBindingTableParentAndName)


class TestPathValueConcatenation(unittest.TestCase):
    """PathValueConcatenation parser."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_path_value_concatenation(self):
        """Path concatenation via || operator."""
        result = self.helper.parse_single("p || q", ast.PathValueConcatenation)
        assert len(result.list_path_value_primary) == 2
        assert isinstance(result.path_value_expression_1, ast.PathValueExpression)
        assert len(result.path_value_expression_1.list_path_value_primary) == 1

    def test_path_value_concatenation_three(self):
        """Three-way path concatenation: p || q || r."""
        result = self.helper.parse_single("p || q || r", ast.PathValueConcatenation)
        assert len(result.list_path_value_primary) == 3
        assert len(result.path_value_expression_1.list_path_value_primary) == 2

    def test_path_value_concatenation_round_trip(self):
        """Round-trip: parse then generate preserves p || q."""
        result = self.helper.parse_single("p || q", ast.PathValueConcatenation)
        assert result.to_gql() == "p || q"

    def test_path_value_concatenation_three_round_trip(self):
        """Round-trip: parse then generate preserves p || q || r."""
        result = self.helper.parse_single("p || q || r", ast.PathValueConcatenation)
        assert result.to_gql() == "p || q || r"


class TestStubParsers(unittest.TestCase):
    """Stub parsers with empty bodies or unreachable parsers."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_sql_datetime_literal_date(self):
        """SqlDatetimeLiteral DATE — parseable directly but unreachable via grammar."""
        expr = self.helper.parse_single("DATE '2023-01-01'", ast.SqlDatetimeLiteral)
        self.assertIsInstance(expr, ast.SqlDatetimeLiteral)
        self.assertEqual(expr.kind, ast.SqlDatetimeLiteral.Kind.DATE)

    def test_sql_datetime_literal_time(self):
        """SqlDatetimeLiteral TIME — parseable directly but unreachable via grammar."""
        expr = self.helper.parse_single("TIME '12:00:00'", ast.SqlDatetimeLiteral)
        self.assertIsInstance(expr, ast.SqlDatetimeLiteral)
        self.assertEqual(expr.kind, ast.SqlDatetimeLiteral.Kind.TIME)

    def test_sql_datetime_literal_timestamp(self):
        """SqlDatetimeLiteral TIMESTAMP — parseable directly but unreachable via grammar."""
        expr = self.helper.parse_single("TIMESTAMP '2023-01-01 12:00:00'", ast.SqlDatetimeLiteral)
        self.assertIsInstance(expr, ast.SqlDatetimeLiteral)
        self.assertEqual(expr.kind, ast.SqlDatetimeLiteral.Kind.TIMESTAMP)

    def test_token(self):
        """Token parser is intentionally not registered."""
        with self.assertRaises(KeyError):
            self.helper.parse_single("hello", ast.Token)

    @pytest.mark.xfail(
        reason="ClosedGraphReferenceValueType requires nested graph type spec",
        raises=Exception,
    )
    def test_closed_graph_reference_value_type(self):
        """ClosedGraphReferenceValueType requires complex graph type context."""
        self.helper.parse_single("GRAPH { }", ast.ClosedGraphReferenceValueType)

    def test_path_element_list_step(self):
        """PathElementListStep parses: , edge , node."""
        expr = self.helper.parse_single(", e , n", ast.PathElementListStep)
        self.assertIsInstance(expr, ast.PathElementListStep)
