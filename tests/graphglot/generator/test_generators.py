"""Unit tests for individual generator functions.

Tests construct AST nodes directly and verify the generated GQL output strings.
For complex AST nodes that require deep nesting, a parse-based helper is used.
"""

import unittest

from decimal import Decimal

from graphglot import ast
from graphglot.generator.base import Generator
from graphglot.lexer import Lexer
from graphglot.parser import Parser


def generate(expr: ast.Expression, dialect=None) -> str:
    gen = Generator(dialect=dialect)
    return gen.generate(expr)


def parse_and_generate(query: str) -> str:
    lexer = Lexer()
    parser = Parser()
    tokens = lexer.tokenize(query)
    parsed = parser.parse(tokens, query)[0]
    return parsed.to_gql()


def parse_and_find(query: str, expr_type: type) -> ast.Expression:
    lexer = Lexer()
    parser = Parser()
    tokens = lexer.tokenize(query)
    parsed = parser.parse(tokens, query)[0]
    found = list(parsed.find_all(expr_type))
    assert found, f"No {expr_type.__name__} found in parsed AST of: {query}"
    return found[0]


class TestLiteralGenerators(unittest.TestCase):
    """Tests for literal generator functions."""

    def test_boolean_literal_true(self):
        self.assertEqual(generate(ast.BooleanLiteral(value=True)), "TRUE")

    def test_boolean_literal_false(self):
        self.assertEqual(generate(ast.BooleanLiteral(value=False)), "FALSE")

    def test_boolean_literal_unknown(self):
        self.assertEqual(generate(ast.BooleanLiteral(value=None)), "UNKNOWN")

    def test_character_string_literal(self):
        self.assertEqual(generate(ast.CharacterStringLiteral(value="hello")), "'hello'")

    def test_character_string_literal_empty(self):
        self.assertEqual(generate(ast.CharacterStringLiteral(value="")), "''")

    def test_character_string_literal_escapes_quotes(self):
        self.assertEqual(generate(ast.CharacterStringLiteral(value="it's")), "'it''s'")

    def test_character_string_literal_none(self):
        self.assertEqual(generate(ast.CharacterStringLiteral(value=None)), "''")

    def test_unsigned_numeric_literal_integer(self):
        self.assertEqual(generate(ast.UnsignedNumericLiteral(value=42)), "42")

    def test_unsigned_numeric_literal_decimal(self):
        self.assertEqual(generate(ast.UnsignedNumericLiteral(value=Decimal("3.14"))), "3.14")

    def test_signed_numeric_literal_positive(self):
        expr = ast.SignedNumericLiteral(
            sign=ast.Sign.PLUS_SIGN,
            unsigned_numeric_literal=ast.UnsignedNumericLiteral(value=5),
        )
        self.assertEqual(generate(expr), "5")

    def test_signed_numeric_literal_negative(self):
        expr = ast.SignedNumericLiteral(
            sign=ast.Sign.MINUS_SIGN,
            unsigned_numeric_literal=ast.UnsignedNumericLiteral(value=5),
        )
        self.assertEqual(generate(expr), "-5")

    def test_null_literal(self):
        self.assertEqual(generate(ast.NullLiteral()), "NULL")

    def test_unsigned_integer(self):
        self.assertEqual(generate(ast.UnsignedInteger(value=10)), "10")

    def test_byte_string_literal(self):
        self.assertEqual(generate(ast.ByteStringLiteral(value="CAFE")), "X'CAFE'")

    def test_byte_string_literal_empty(self):
        self.assertEqual(generate(ast.ByteStringLiteral(value="")), "X''")


class TestCoreGenerators(unittest.TestCase):
    """Tests for core generator functions."""

    def test_identifier_simple(self):
        self.assertEqual(generate(ast.Identifier(name="myVar")), "myVar")

    def test_identifier_reserved_word_quoted(self):
        self.assertEqual(generate(ast.Identifier(name="MATCH")), "`MATCH`")

    def test_identifier_reserved_word_return(self):
        self.assertEqual(generate(ast.Identifier(name="RETURN")), "`RETURN`")

    def test_identifier_with_special_chars(self):
        result = generate(ast.Identifier(name="my-var"))
        self.assertEqual(result, "`my-var`")

    def test_identifier_reserved_word_quoted_with_dialect(self):
        """MATCH is reserved in all dialects — always backtick-quoted."""
        from graphglot.dialect.neo4j import Neo4j

        result = generate(ast.Identifier(name="MATCH"), dialect=Neo4j())
        self.assertEqual(result, "`MATCH`")

    def test_identifier_non_reserved_unquoted_with_cypher_dialect(self):
        """PRODUCT is non-reserved in Cypher — should NOT be quoted."""
        from graphglot.dialect.neo4j import Neo4j

        result = generate(ast.Identifier(name="PRODUCT"), dialect=Neo4j())
        self.assertEqual(result, "PRODUCT")

    def test_identifier_edge_unquoted_with_cypher_dialect(self):
        """EDGE is non-reserved in Cypher — should NOT be quoted."""
        from graphglot.dialect.neo4j import Neo4j

        result = generate(ast.Identifier(name="EDGE"), dialect=Neo4j())
        self.assertEqual(result, "EDGE")

    def test_identifier_no_dialect_keywords_reserved(self):
        """Without a dialect, lexer keywords should be treated as reserved."""
        # PRODUCT is a GQL keyword → reserved by default
        result = generate(ast.Identifier(name="PRODUCT"))
        self.assertEqual(result, "`PRODUCT`")

    def test_session_close_command(self):
        self.assertEqual(generate(ast.SessionCloseCommand()), "SESSION CLOSE")

    def test_end_transaction_commit(self):
        self.assertEqual(
            generate(ast.EndTransactionCommand(mode=ast.EndTransactionCommand.Mode.COMMIT)),
            "COMMIT",
        )

    def test_end_transaction_rollback(self):
        self.assertEqual(
            generate(ast.EndTransactionCommand(mode=ast.EndTransactionCommand.Mode.ROLLBACK)),
            "ROLLBACK",
        )

    def test_start_transaction(self):
        self.assertEqual(
            generate(ast.StartTransactionCommand(transaction_characteristics=None)),
            "START TRANSACTION",
        )

    def test_set_operator_union(self):
        expr = ast.SetOperator(
            set_operator_type=ast.SetOperator.SetOperatorType.UNION,
            set_quantifier=None,
        )
        self.assertEqual(generate(expr), "UNION")

    def test_set_operator_union_all(self):
        expr = ast.SetOperator(
            set_operator_type=ast.SetOperator.SetOperatorType.UNION,
            set_quantifier=ast.SetQuantifier(set_quantifier=ast.SetQuantifier.Quantifier.ALL),
        )
        self.assertEqual(generate(expr), "UNION ALL")

    def test_set_operator_except(self):
        expr = ast.SetOperator(
            set_operator_type=ast.SetOperator.SetOperatorType.EXCEPT,
            set_quantifier=None,
        )
        self.assertEqual(generate(expr), "EXCEPT")

    def test_set_operator_intersect(self):
        expr = ast.SetOperator(
            set_operator_type=ast.SetOperator.SetOperatorType.INTERSECT,
            set_quantifier=None,
        )
        self.assertEqual(generate(expr), "INTERSECT")


class TestClauseGenerators(unittest.TestCase):
    """Tests for clause generator functions."""

    def test_set_quantifier_distinct(self):
        expr = ast.SetQuantifier(set_quantifier=ast.SetQuantifier.Quantifier.DISTINCT)
        self.assertEqual(generate(expr), "DISTINCT")

    def test_set_quantifier_all(self):
        expr = ast.SetQuantifier(set_quantifier=ast.SetQuantifier.Quantifier.ALL)
        self.assertEqual(generate(expr), "ALL")

    def test_ordering_specification_asc(self):
        expr = ast.OrderingSpecification(ordering_specification=ast.OrderingSpecification.Order.ASC)
        self.assertEqual(generate(expr), "ASC")

    def test_ordering_specification_desc(self):
        expr = ast.OrderingSpecification(
            ordering_specification=ast.OrderingSpecification.Order.DESC
        )
        self.assertEqual(generate(expr), "DESC")

    def test_null_ordering_first(self):
        expr = ast.NullOrdering(null_ordering=ast.NullOrdering.Order.NULLS_FIRST)
        self.assertEqual(generate(expr), "NULLS FIRST")

    def test_null_ordering_last(self):
        expr = ast.NullOrdering(null_ordering=ast.NullOrdering.Order.NULLS_LAST)
        self.assertEqual(generate(expr), "NULLS LAST")

    def test_empty_grouping_set(self):
        self.assertEqual(generate(ast.EmptyGroupingSet()), "()")

    def test_where_clause_via_parse(self):
        wc = parse_and_find("MATCH (n) WHERE n.age > 21 RETURN n", ast.GraphPatternWhereClause)
        result = generate(wc)
        self.assertIn("WHERE", result)
        self.assertIn("n.age", result)
        self.assertIn(">", result)
        self.assertIn("21", result)

    def test_order_by_clause_via_parse(self):
        result = parse_and_generate("MATCH (n) RETURN n ORDER BY n.name ASC")
        self.assertIn("ORDER BY", result)
        self.assertIn("n.name", result)
        self.assertIn("ASC", result)

    def test_order_by_desc_nulls_last_via_parse(self):
        result = parse_and_generate("MATCH (n) RETURN n ORDER BY n.age DESC NULLS LAST")
        self.assertIn("ORDER BY", result)
        self.assertIn("DESC", result)
        self.assertIn("NULLS LAST", result)

    def test_limit_clause_via_parse(self):
        result = parse_and_generate("MATCH (n) RETURN n LIMIT 10")
        self.assertIn("LIMIT", result)
        self.assertIn("10", result)

    def test_offset_clause_via_parse(self):
        result = parse_and_generate("MATCH (n) RETURN n OFFSET 5 LIMIT 10")
        self.assertIn("OFFSET", result)
        self.assertIn("5", result)
        self.assertIn("LIMIT", result)
        self.assertIn("10", result)

    def test_variable_scope_clause_empty(self):
        expr = ast.VariableScopeClause(binding_variable_reference_list=None)
        self.assertEqual(generate(expr), "()")


class TestExpressionGenerators(unittest.TestCase):
    """Tests for expression generator functions."""

    def test_aggregate_count_star(self):
        expr = ast.AggregateFunction(aggregate_function=ast.AggregateFunction._CountAsterisk())
        self.assertEqual(generate(expr), "COUNT(*)")

    def test_truth_value_true(self):
        self.assertEqual(generate(ast.TruthValue(truth_value=ast.TruthValue._True())), "TRUE")

    def test_truth_value_false(self):
        self.assertEqual(generate(ast.TruthValue(truth_value=ast.TruthValue._False())), "FALSE")

    def test_truth_value_unknown(self):
        self.assertEqual(generate(ast.TruthValue(truth_value=ast.TruthValue._Unknown())), "UNKNOWN")

    def test_else_clause(self):
        expr = ast.ElseClause(
            result=ast.CharacterStringValueExpression(
                list_character_string_value_expression=[
                    ast.CharacterStringLiteral(value="fallback")
                ]
            )
        )
        self.assertEqual(generate(expr), "ELSE 'fallback'")

    def test_home_graph(self):
        self.assertEqual(generate(ast.HomeGraph()), "HOME_GRAPH")

    def test_current_graph(self):
        self.assertEqual(generate(ast.CurrentGraph()), "CURRENT_GRAPH")

    def test_asterisk(self):
        self.assertEqual(generate(ast.Asterisk()), "*")

    def test_parenthesized_value_expression_via_parse(self):
        result = parse_and_generate("MATCH (n) WHERE (n.age > 21 AND n.active = TRUE) RETURN n")
        self.assertIn("(", result)
        self.assertIn(")", result)
        self.assertIn("AND", result)

    def test_numeric_addition_via_parse(self):
        result = parse_and_generate("MATCH (n) RETURN n.age + 1")
        self.assertIn("+", result)

    def test_numeric_subtraction_via_parse(self):
        result = parse_and_generate("MATCH (n) RETURN n.age - 1")
        self.assertIn("-", result)

    def test_numeric_multiplication_via_parse(self):
        result = parse_and_generate("MATCH (n) RETURN n.age * 2")
        self.assertIn("*", result)

    def test_unary_minus_via_parse(self):
        result = parse_and_generate("MATCH (n) RETURN -n.age")
        self.assertIn("-", result)

    def test_property_reference_via_parse(self):
        result = parse_and_generate("MATCH (n) RETURN n.name")
        self.assertIn("n.name", result)

    def test_nested_property_reference_via_parse(self):
        result = parse_and_generate("MATCH (n) RETURN n.address.city")
        self.assertIn("n.address.city", result)

    def test_return_item_alias_via_parse(self):
        result = parse_and_generate("MATCH (n) RETURN n.name AS personName")
        self.assertIn("AS", result)
        self.assertIn("personName", result)

    def test_case_searched_via_parse(self):
        result = parse_and_generate(
            "MATCH (n) RETURN CASE WHEN n.age > 21 THEN 'adult' ELSE 'minor' END"
        )
        self.assertIn("CASE", result)
        self.assertIn("WHEN", result)
        self.assertIn("THEN", result)
        self.assertIn("ELSE", result)
        self.assertIn("END", result)

    def test_case_searched_no_else_via_parse(self):
        result = parse_and_generate("MATCH (n) RETURN CASE WHEN n.age > 21 THEN 'adult' END")
        self.assertIn("CASE", result)
        self.assertIn("WHEN", result)
        self.assertIn("THEN", result)
        self.assertNotIn("ELSE", result)
        self.assertIn("END", result)

    def test_case_multiple_when_via_parse(self):
        result = parse_and_generate(
            "MATCH (n) RETURN CASE WHEN n.age < 13 THEN 'child' "
            "WHEN n.age < 18 THEN 'teen' ELSE 'adult' END"
        )
        self.assertEqual(result.count("WHEN"), 2)
        self.assertEqual(result.count("THEN"), 2)

    def test_boolean_or_via_parse(self):
        result = parse_and_generate("MATCH (n) WHERE n.a = TRUE OR n.b = FALSE RETURN n")
        self.assertIn("OR", result)

    def test_boolean_and_via_parse(self):
        result = parse_and_generate("MATCH (n) WHERE n.age >= 18 AND n.age <= 65 RETURN n")
        self.assertIn("AND", result)

    def test_boolean_not_via_parse(self):
        result = parse_and_generate("MATCH (n) WHERE NOT n.active = TRUE RETURN n")
        self.assertIn("NOT", result)

    def test_list_value_constructor_empty(self):
        expr = ast.ListValueConstructorByEnumeration(
            list_value_type_name=None, list_element_list=None
        )
        self.assertEqual(generate(expr), "[]")

    def test_fields_specification_empty(self):
        self.assertEqual(generate(ast.FieldsSpecification(field_list=None)), "{}")

    def test_record_constructor_with_keyword(self):
        expr = ast.RecordConstructor(
            record=True,
            fields_specification=ast.FieldsSpecification(field_list=None),
        )
        self.assertEqual(generate(expr), "RECORD {}")

    def test_record_constructor_without_keyword(self):
        expr = ast.RecordConstructor(
            record=False,
            fields_specification=ast.FieldsSpecification(field_list=None),
        )
        self.assertEqual(generate(expr), "{}")

    def test_general_parameter_reference(self):
        expr = ast.GeneralParameterReference(parameter_name=ast.Identifier(name="x"))
        self.assertEqual(generate(expr), "$x")

    def test_substituted_parameter_reference(self):
        expr = ast.SubstitutedParameterReference(parameter_name=ast.Identifier(name="param"))
        self.assertEqual(generate(expr), "$$param")

    def test_absolute_value_expression(self):
        expr = ast.AbsoluteValueExpression(
            numeric_value_expression=ast.UnsignedNumericLiteral(value=42)
        )
        self.assertEqual(generate(expr), "ABS (42)")

    def test_duration_absolute_value_function(self):
        expr = ast.DurationAbsoluteValueFunction(
            duration_value_expression=ast.GeneralParameterReference(
                parameter_name=ast.Identifier(name="d")
            )
        )
        self.assertEqual(generate(expr), "ABS ($d)")


class TestPatternGenerators(unittest.TestCase):
    """Tests for pattern generator functions."""

    def _make_filler(self, name="r", label=None):
        filler_args = {
            "element_variable_declaration": ast.ElementVariableDeclaration(
                temp=False, element_variable=ast.Identifier(name=name)
            ),
            "is_label_expression": None,
            "element_pattern_predicate": None,
        }
        if label:
            filler_args["is_label_expression"] = ast.IsLabelExpression(
                label_expression=ast.LabelExpression(
                    label_terms=[
                        ast.LabelTerm(
                            label_factors=[ast.LabelName(identifier=ast.Identifier(name=label))]
                        )
                    ]
                )
            )
        return ast.ElementPatternFiller(**filler_args)

    def test_node_pattern_with_label(self):
        np = ast.NodePattern(element_pattern_filler=self._make_filler("n", "Person"))
        result = generate(np)
        self.assertIn("n", result)
        self.assertIn("Person", result)
        self.assertTrue(result.startswith("("))
        self.assertTrue(result.endswith(")"))

    def test_node_pattern_var_only(self):
        np = ast.NodePattern(element_pattern_filler=self._make_filler("x"))
        result = generate(np)
        self.assertEqual(result, "(x)")

    def test_node_pattern_empty(self):
        np = ast.NodePattern(
            element_pattern_filler=ast.ElementPatternFiller(
                element_variable_declaration=None,
                is_label_expression=None,
                element_pattern_predicate=None,
            )
        )
        self.assertEqual(generate(np), "()")

    def test_full_edge_pointing_right(self):
        expr = ast.FullEdgePointingRight(element_pattern_filler=self._make_filler("r"))
        self.assertEqual(generate(expr), "-[r]->")

    def test_full_edge_pointing_left(self):
        expr = ast.FullEdgePointingLeft(element_pattern_filler=self._make_filler("r"))
        self.assertEqual(generate(expr), "<-[r]-")

    def test_full_edge_undirected(self):
        expr = ast.FullEdgeUndirected(element_pattern_filler=self._make_filler("r"))
        self.assertEqual(generate(expr), "~[r]~")

    def test_full_edge_any_direction(self):
        expr = ast.FullEdgeAnyDirection(element_pattern_filler=self._make_filler("r"))
        self.assertEqual(generate(expr), "-[r]-")

    def test_full_edge_left_or_undirected(self):
        expr = ast.FullEdgeLeftOrUndirected(element_pattern_filler=self._make_filler("r"))
        self.assertEqual(generate(expr), "<~[r]~")

    def test_full_edge_undirected_or_right(self):
        expr = ast.FullEdgeUndirectedOrRight(element_pattern_filler=self._make_filler("r"))
        self.assertEqual(generate(expr), "~[r]~>")

    def test_full_edge_left_or_right(self):
        expr = ast.FullEdgeLeftOrRight(element_pattern_filler=self._make_filler("r"))
        self.assertEqual(generate(expr), "<-[r]->")

    def test_full_edge_with_label(self):
        expr = ast.FullEdgePointingRight(element_pattern_filler=self._make_filler("r", "KNOWS"))
        result = generate(expr)
        self.assertIn("KNOWS", result)
        self.assertTrue(result.startswith("-["))
        self.assertTrue(result.endswith("]->"))

    def test_abbreviated_edge_patterns(self):
        expected = {
            ast.AbbreviatedEdgePattern.PatternType.LEFT_ARROW: "<-",
            ast.AbbreviatedEdgePattern.PatternType.TILDE: "~",
            ast.AbbreviatedEdgePattern.PatternType.RIGHT_ARROW: "->",
            ast.AbbreviatedEdgePattern.PatternType.LEFT_ARROW_TILDE: "<~",
            ast.AbbreviatedEdgePattern.PatternType.TILDE_RIGHT_ARROW: "~>",
            ast.AbbreviatedEdgePattern.PatternType.LEFT_MINUS_RIGHT: "<->",
            ast.AbbreviatedEdgePattern.PatternType.MINUS_SIGN: "-",
        }
        for pattern_type, expected_str in expected.items():
            expr = ast.AbbreviatedEdgePattern(pattern=pattern_type)
            self.assertEqual(generate(expr), expected_str)

    def test_label_expression_single(self):
        expr = ast.LabelExpression(
            label_terms=[
                ast.LabelTerm(
                    label_factors=[ast.LabelName(identifier=ast.Identifier(name="Person"))]
                )
            ]
        )
        self.assertEqual(generate(expr), "Person")

    def test_label_expression_or(self):
        expr = ast.LabelExpression(
            label_terms=[
                ast.LabelTerm(
                    label_factors=[ast.LabelName(identifier=ast.Identifier(name="Person"))]
                ),
                ast.LabelTerm(
                    label_factors=[ast.LabelName(identifier=ast.Identifier(name="Employee"))]
                ),
            ]
        )
        self.assertEqual(generate(expr), "Person|Employee")

    def test_label_expression_and(self):
        expr = ast.LabelExpression(
            label_terms=[
                ast.LabelTerm(
                    label_factors=[
                        ast.LabelName(identifier=ast.Identifier(name="Person")),
                        ast.LabelName(identifier=ast.Identifier(name="Employee")),
                    ]
                )
            ]
        )
        self.assertEqual(generate(expr), "Person&Employee")

    def test_label_negation(self):
        expr = ast.LabelNegation(label_primary=ast.LabelName(identifier=ast.Identifier(name="Bot")))
        self.assertEqual(generate(expr), "!Bot")

    def test_wildcard_label(self):
        self.assertEqual(generate(ast.WildcardLabel()), "%")

    def test_label_set_specification(self):
        expr = ast.LabelSetSpecification(
            list_label_name=[
                ast.LabelName(identifier=ast.Identifier(name="Person")),
                ast.LabelName(identifier=ast.Identifier(name="Active")),
            ]
        )
        self.assertEqual(generate(expr), ":Person:Active")

    def test_fixed_quantifier(self):
        expr = ast.FixedQuantifier(unsigned_integer=ast.UnsignedInteger(value=3))
        self.assertEqual(generate(expr), "{3}")

    def test_general_quantifier(self):
        expr = ast.GeneralQuantifier(
            lower_bound=ast.UnsignedInteger(value=1),
            upper_bound=ast.UnsignedInteger(value=5),
        )
        self.assertEqual(generate(expr), "{1,5}")

    def test_general_quantifier_no_upper(self):
        expr = ast.GeneralQuantifier(
            lower_bound=ast.UnsignedInteger(value=0),
            upper_bound=None,
        )
        self.assertEqual(generate(expr), "{0,}")

    def test_path_mode_walk(self):
        self.assertEqual(generate(ast.PathMode(mode=ast.PathMode.Mode.WALK)), "WALK")

    def test_path_mode_trail(self):
        self.assertEqual(generate(ast.PathMode(mode=ast.PathMode.Mode.TRAIL)), "TRAIL")

    def test_path_mode_simple(self):
        self.assertEqual(generate(ast.PathMode(mode=ast.PathMode.Mode.SIMPLE)), "SIMPLE")

    def test_path_mode_acyclic(self):
        self.assertEqual(generate(ast.PathMode(mode=ast.PathMode.Mode.ACYCLIC)), "ACYCLIC")

    def test_different_edges_match_mode(self):
        expr = ast.DifferentEdgesMatchMode(mode=ast.DifferentEdgesMatchMode.Mode.EDGES)
        self.assertEqual(generate(expr), "DIFFERENT EDGES")

    def test_repeatable_elements_match_mode(self):
        expr = ast.RepeatableElementsMatchMode(mode=ast.RepeatableElementsMatchMode.Mode.ELEMENTS)
        self.assertEqual(generate(expr), "REPEATABLE ELEMENTS")

    def test_property_key_value_pair(self):
        expr = ast.PropertyKeyValuePair(
            property_name=ast.PropertyName(identifier=ast.Identifier(name="name")),
            value_expression=ast.CharacterStringValueExpression(
                list_character_string_value_expression=[ast.CharacterStringLiteral(value="Alice")]
            ),
        )
        result = generate(expr)
        self.assertIn("name", result)
        self.assertIn(":", result)
        self.assertIn("'Alice'", result)

    def test_insert_node_pattern_empty(self):
        expr = ast.InsertNodePattern(insert_element_pattern_filler=None)
        self.assertEqual(generate(expr), "()")

    def test_path_pattern_with_variable_via_parse(self):
        result = parse_and_generate("MATCH p = (a)-[]->(b) RETURN p")
        self.assertIn("p =", result)

    def test_quantified_path_via_parse(self):
        result = parse_and_generate("MATCH (a)-[]->{1,3}(b) RETURN a, b")
        self.assertIn("{1,3}", result)

    def test_quantified_path_plus_via_parse(self):
        result = parse_and_generate("MATCH (a)-[]->+(b) RETURN a, b")
        # + is parsed as {1,} quantifier
        self.assertIn("{1,}", result)

    def test_quantified_path_star_via_parse(self):
        result = parse_and_generate("MATCH (a)-[]->*(b) RETURN a, b")
        # * is parsed as {0,} quantifier
        self.assertIn("{0,}", result)

    def test_multiple_patterns_via_parse(self):
        result = parse_and_generate("MATCH (a)-[r1]->(b), (b)-[r2]->(c) RETURN a, c")
        self.assertIn(",", result)
        self.assertEqual(result.count("->"), 2)

    def test_label_with_where_via_parse(self):
        result = parse_and_generate("MATCH (n:Person WHERE n.age > 21) RETURN n")
        self.assertIn("Person", result)
        self.assertIn("WHERE", result)


class TestPredicateGenerators(unittest.TestCase):
    """Tests for predicate generator functions."""

    def test_comparison_predicate_part2_all_ops(self):
        expected = {
            ast.ComparisonPredicatePart2.CompOp.EQUALS: "=",
            ast.ComparisonPredicatePart2.CompOp.NOT_EQUALS: "<>",
            ast.ComparisonPredicatePart2.CompOp.LESS_THAN: "<",
            ast.ComparisonPredicatePart2.CompOp.GREATER_THAN: ">",
            ast.ComparisonPredicatePart2.CompOp.LESS_THAN_OR_EQUALS: "<=",
            ast.ComparisonPredicatePart2.CompOp.GREATER_THAN_OR_EQUALS: ">=",
        }
        for op, op_str in expected.items():
            expr = ast.ComparisonPredicatePart2(
                comp_op=op,
                comparison_predicand=ast.UnsignedNumericLiteral(value=42),
            )
            result = generate(expr)
            self.assertIn(op_str, result)
            self.assertIn("42", result)

    def test_null_predicate_is_null(self):
        expr = ast.NullPredicatePart2(not_=False)
        self.assertEqual(generate(expr), "IS NULL")

    def test_null_predicate_is_not_null(self):
        expr = ast.NullPredicatePart2(not_=True)
        self.assertEqual(generate(expr), "IS NOT NULL")

    def test_directed_predicate_part2(self):
        expr = ast.DirectedPredicatePart2(not_=False)
        self.assertEqual(generate(expr), "IS DIRECTED")

    def test_directed_predicate_part2_not(self):
        expr = ast.DirectedPredicatePart2(not_=True)
        self.assertEqual(generate(expr), "IS NOT DIRECTED")

    def test_comparison_via_parse(self):
        result = parse_and_generate("MATCH (n) WHERE n.age > 21 RETURN n")
        self.assertIn(">", result)
        self.assertIn("21", result)

    def test_null_predicate_via_parse(self):
        result = parse_and_generate("MATCH (n) WHERE n.value_ IS NULL RETURN n")
        self.assertIn("IS NULL", result)

    def test_not_null_predicate_via_parse(self):
        result = parse_and_generate("MATCH (n) WHERE n.email IS NOT NULL RETURN n")
        self.assertIn("IS NOT NULL", result)


class TestStatementGenerators(unittest.TestCase):
    """Tests for statement generator functions."""

    def test_match_return_via_parse(self):
        result = parse_and_generate("MATCH (n) RETURN n")
        self.assertIn("MATCH", result)
        self.assertIn("RETURN", result)

    def test_match_with_label_via_parse(self):
        result = parse_and_generate("MATCH (n:Person) RETURN n")
        self.assertIn("Person", result)

    def test_optional_match_via_parse(self):
        result = parse_and_generate("OPTIONAL MATCH (n)-[r]->(m) RETURN n, m")
        self.assertIn("OPTIONAL", result)
        self.assertIn("MATCH", result)

    def test_return_distinct_via_parse(self):
        result = parse_and_generate("MATCH (n) RETURN DISTINCT n")
        self.assertIn("DISTINCT", result)

    def test_insert_via_parse(self):
        result = parse_and_generate("INSERT (n:Person {name: 'Bob'})")
        self.assertIn("INSERT", result)
        self.assertIn("Person", result)
        self.assertIn("Bob", result)

    def test_set_via_parse(self):
        result = parse_and_generate("MATCH (n) SET n.updated = TRUE")
        self.assertIn("SET", result)
        self.assertIn("n.updated", result)
        self.assertIn("TRUE", result)

    def test_delete_via_parse(self):
        result = parse_and_generate("MATCH (n) DELETE n")
        self.assertIn("DELETE", result)

    def test_detach_delete_via_parse(self):
        result = parse_and_generate("MATCH (n) DETACH DELETE n")
        self.assertIn("DETACH", result)
        self.assertIn("DELETE", result)

    def test_remove_label_via_parse(self):
        result = parse_and_generate("MATCH (n) REMOVE n:TempLabel")
        self.assertIn("REMOVE", result)
        self.assertIn("TempLabel", result)

    def test_filter_via_parse(self):
        result = parse_and_generate("MATCH (n) FILTER n.active = TRUE RETURN n")
        self.assertIn("FILTER", result)

    def test_union_all_via_parse(self):
        result = parse_and_generate("MATCH (n) RETURN n UNION ALL MATCH (m) RETURN m")
        self.assertIn("UNION", result)
        self.assertIn("ALL", result)

    def test_union_via_parse(self):
        result = parse_and_generate("MATCH (n) RETURN n UNION MATCH (m) RETURN m")
        self.assertIn("UNION", result)

    def test_multiple_return_items_via_parse(self):
        result = parse_and_generate("MATCH (n:Person) RETURN n.name, n.age, n.active")
        self.assertEqual(result.count(","), 2)

    def test_return_with_order_by_limit_offset(self):
        result = parse_and_generate(
            "MATCH (n) RETURN n ORDER BY n.age DESC, n.name ASC OFFSET 10 LIMIT 5"
        )
        self.assertIn("ORDER BY", result)
        self.assertIn("DESC", result)
        self.assertIn("ASC", result)
        self.assertIn("OFFSET", result)
        self.assertIn("LIMIT", result)


class TestCommandGenerators(unittest.TestCase):
    """Tests for command generator functions."""

    def test_session_close(self):
        self.assertEqual(generate(ast.SessionCloseCommand()), "SESSION CLOSE")

    def test_start_transaction(self):
        expr = ast.StartTransactionCommand(transaction_characteristics=None)
        self.assertEqual(generate(expr), "START TRANSACTION")

    def test_commit(self):
        expr = ast.EndTransactionCommand(mode=ast.EndTransactionCommand.Mode.COMMIT)
        self.assertEqual(generate(expr), "COMMIT")

    def test_rollback(self):
        expr = ast.EndTransactionCommand(mode=ast.EndTransactionCommand.Mode.ROLLBACK)
        self.assertEqual(generate(expr), "ROLLBACK")

    def test_session_close_via_parse(self):
        result = parse_and_generate("SESSION CLOSE")
        self.assertEqual(result, "SESSION CLOSE")

    def test_start_transaction_via_parse(self):
        result = parse_and_generate("START TRANSACTION")
        self.assertEqual(result, "START TRANSACTION")

    def test_commit_via_parse(self):
        result = parse_and_generate("COMMIT")
        self.assertEqual(result, "COMMIT")

    def test_rollback_via_parse(self):
        result = parse_and_generate("ROLLBACK")
        self.assertEqual(result, "ROLLBACK")
