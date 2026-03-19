from __future__ import annotations

import typing as t

from graphglot import ast
from graphglot.lexer import TokenType
from graphglot.parser.registry import parses

if t.TYPE_CHECKING:
    from graphglot.parser import Parser


@parses(ast.ElementPatternPredicate)
def parse_element_pattern_predicate(parser: Parser) -> ast.ElementPatternPredicate:
    candidates_element_pattern_predicate = (
        parser.get_parser(ast.ElementPatternWhereClause),
        parser.get_parser(ast.ElementPropertySpecification),
    )
    (result,) = parser.seq(candidates_element_pattern_predicate)
    return result


@parses(ast.Predicate)
def parse_predicate(parser: Parser) -> ast.Predicate:
    candidates_predicate = (
        parser.get_parser(ast.ComparisonPredicate),
        parser.get_parser(ast.ExistsPredicate),
        parser.get_parser(ast.NullPredicate),
        parser.get_parser(ast.NormalizedPredicate),
        parser.get_parser(ast.ValueTypePredicate),
        parser.get_parser(ast.DirectedPredicate),
        parser.get_parser(ast.LabeledPredicate),
        parser.get_parser(ast.SourceDestinationPredicate),
        parser.get_parser(ast.AllDifferentPredicate),
        parser.get_parser(ast.SamePredicate),
        parser.get_parser(ast.PropertyExistsPredicate),
    )
    (result,) = parser.seq(candidates_predicate)
    return result


@parses(ast.ComparisonPredicate)
def parse_comparison_predicate(parser: Parser) -> ast.ComparisonPredicate:
    (
        comparison_predicand,
        comparison_predicate_part_2,
    ) = parser.seq(
        parser.get_parser(ast.ComparisonPredicand),
        parser.get_parser(ast.ComparisonPredicatePart2),
    )
    return ast.ComparisonPredicate(
        comparison_predicand=comparison_predicand,
        comparison_predicate_part_2=comparison_predicate_part_2,
    )


@parses(ast.ExistsPredicate)
def parse_exists_predicate(parser: Parser) -> ast.ExistsPredicate:
    def _parse__exists_graph_pattern(
        parser: Parser,
    ) -> ast.ExistsPredicate._ExistsGraphPattern:
        candidates = (
            lambda parser: parser.seq(
                TokenType.LEFT_BRACE,
                parser.get_parser(ast.GraphPattern),
                TokenType.RIGHT_BRACE,
            )[1],
            lambda parser: parser.seq(
                TokenType.LEFT_PAREN,
                parser.get_parser(ast.GraphPattern),
                TokenType.RIGHT_PAREN,
            )[1],
        )

        (graph_pattern,) = parser.seq(candidates)
        return ast.ExistsPredicate._ExistsGraphPattern(
            graph_pattern=graph_pattern,
        )

    def _parse__exists_match_statement_block(
        parser: Parser,
    ) -> ast.ExistsPredicate._ExistsMatchStatementBlock:
        candidates = (
            lambda parser: parser.seq(
                TokenType.LEFT_BRACE,
                parser.get_parser(ast.MatchStatementBlock),
                TokenType.RIGHT_BRACE,
            )[1],
            lambda parser: parser.seq(
                TokenType.LEFT_PAREN,
                parser.get_parser(ast.MatchStatementBlock),
                TokenType.RIGHT_PAREN,
            )[1],
        )
        (match_statement_block,) = parser.seq(candidates)
        return ast.ExistsPredicate._ExistsMatchStatementBlock(
            match_statement_block=match_statement_block,
        )

    candidates_exists_predicate = (
        _parse__exists_graph_pattern,
        _parse__exists_match_statement_block,
        parser.get_parser(ast.NestedQuerySpecification),
    )
    (
        _,
        exists_predicate,
    ) = parser.seq(
        TokenType.EXISTS,
        candidates_exists_predicate,
    )
    return ast.ExistsPredicate(
        exists_predicate=exists_predicate,
    )


@parses(ast.NullPredicate)
def parse_null_predicate(parser: Parser) -> ast.NullPredicate:
    (
        value_expression_primary,
        null_predicate_part_2,
    ) = parser.seq(
        parser.get_parser(ast.ValueExpressionPrimary),
        parser.get_parser(ast.NullPredicatePart2),
    )
    return ast.NullPredicate(
        value_expression_primary=value_expression_primary,
        null_predicate_part_2=null_predicate_part_2,
    )


@parses(ast.ValueTypePredicate)
def parse_value_type_predicate(parser: Parser) -> ast.ValueTypePredicate:
    (
        value_expression_primary,
        value_type_predicate_part_2,
    ) = parser.seq(
        parser.get_parser(ast.ValueExpressionPrimary),
        parser.get_parser(ast.ValueTypePredicatePart2),
    )
    return ast.ValueTypePredicate(
        value_expression_primary=value_expression_primary,
        value_type_predicate_part_2=value_type_predicate_part_2,
    )


@parses(ast.NormalizedPredicate)
def parse_normalized_predicate(parser: Parser) -> ast.NormalizedPredicate:
    (
        string_value_expression,
        normalized_predicate_part_2,
    ) = parser.seq(
        parser.get_parser(ast.StringValueExpression),
        parser.get_parser(ast.NormalizedPredicatePart2),
    )
    return ast.NormalizedPredicate(
        string_value_expression=string_value_expression,
        normalized_predicate_part_2=normalized_predicate_part_2,
    )


@parses(ast.DirectedPredicate)
def parse_directed_predicate(parser: Parser) -> ast.DirectedPredicate:
    (
        element_variable_reference,
        directed_predicate_part_2,
    ) = parser.seq(
        parser.get_parser(ast.ElementVariableReference),
        parser.get_parser(ast.DirectedPredicatePart2),
    )
    return ast.DirectedPredicate(
        element_variable_reference=element_variable_reference,
        directed_predicate_part_2=directed_predicate_part_2,
    )


@parses(ast.LabeledPredicate)
def parse_labeled_predicate(parser: Parser) -> ast.LabeledPredicate:
    (
        element_variable_reference,
        labeled_predicate_part_2,
    ) = parser.seq(
        parser.get_parser(ast.ElementVariableReference),
        parser.get_parser(ast.LabeledPredicatePart2),
    )
    return ast.LabeledPredicate(
        element_variable_reference=element_variable_reference,
        labeled_predicate_part_2=labeled_predicate_part_2,
    )


@parses(ast.SourceDestinationPredicate)
def parse_source_destination_predicate(parser: Parser) -> ast.SourceDestinationPredicate:
    candidates = (
        parser.get_parser(ast.SourcePredicatePart2),
        parser.get_parser(ast.DestinationPredicatePart2),
    )
    (
        node_reference,
        predicate_part_2,
    ) = parser.seq(
        parser.get_parser(ast.NodeReference),
        candidates,
    )
    return ast.SourceDestinationPredicate(
        node_reference=node_reference,
        predicate_part_2=predicate_part_2,
    )


@parses(ast.AllDifferentPredicate)
def parse_all_different_predicate(parser: Parser) -> ast.AllDifferentPredicate:
    (
        _,
        _,
        list_element_variable_reference,
        _,
    ) = parser.seq(
        TokenType.ALL_DIFFERENT,
        TokenType.LEFT_PAREN,
        parser.list_(
            parser.get_parser(ast.ElementVariableReference),
            TokenType.COMMA,
            min_items=2,
        ),
        TokenType.RIGHT_PAREN,
    )
    return ast.AllDifferentPredicate(
        list_element_variable_reference=list_element_variable_reference,
    )


@parses(ast.SamePredicate)
def parse_same_predicate(parser: Parser) -> ast.SamePredicate:
    (
        _,
        _,
        list_element_variable_reference,
        _,
    ) = parser.seq(
        TokenType.SAME,
        TokenType.LEFT_PAREN,
        parser.list_(
            parser.get_parser(ast.ElementVariableReference),
            TokenType.COMMA,
            min_items=2,
        ),
        TokenType.RIGHT_PAREN,
    )
    return ast.SamePredicate(
        list_element_variable_reference=list_element_variable_reference,
    )


@parses(ast.PropertyExistsPredicate)
def parse_property_exists_predicate(parser: Parser) -> ast.PropertyExistsPredicate:
    (
        _,
        _,
        element_variable_reference,
        _,
        property_name,
        _,
    ) = parser.seq(
        TokenType.PROPERTY_EXISTS,
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.ElementVariableReference),
        TokenType.COMMA,
        parser.get_parser(ast.PropertyName),
        TokenType.RIGHT_PAREN,
    )
    return ast.PropertyExistsPredicate(
        element_variable_reference=element_variable_reference,
        property_name=property_name,
    )
