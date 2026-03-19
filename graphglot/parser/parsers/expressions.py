from __future__ import annotations

import typing as t

from graphglot import ast
from graphglot.error import ParseError, ValidationError
from graphglot.lexer import TokenType
from graphglot.parser.functions import parse_dotted_function, parse_function_call
from graphglot.parser.registry import parses

if t.TYPE_CHECKING:
    from graphglot.parser import Parser


# Function prefix lookup tables for routing to the correct parser
# These help identify the type of expression from definitive keywords

NUMERIC_FUNCTION_TOKENS: set[TokenType] = {
    # NOTE: ABS is intentionally excluded - it's ambiguous (could return numeric or duration)
    # and is handled by ArithmeticAbsoluteValueFunction via AmbiguousValueExpression
    TokenType.ACOS,
    TokenType.ASIN,
    TokenType.ATAN,
    TokenType.CEIL,
    TokenType.COS,
    TokenType.COSH,
    TokenType.COT,
    TokenType.DEGREES,
    TokenType.EXP,
    TokenType.E,  # Neo4j's e() — no-op for base dialect (token never produced)
    TokenType.FLOOR,
    TokenType.ROUND,  # Cypher ROUND() — no-op for base dialect (token never produced)
    TokenType.LN,
    TokenType.LOG,
    TokenType.LOG10,
    TokenType.MOD,
    TokenType.POWER,
    TokenType.RADIANS,
    TokenType.SIN,
    TokenType.SINH,
    TokenType.SQRT,
    TokenType.TAN,
    TokenType.TANH,
    TokenType.CHAR_LENGTH,
    TokenType.CHARACTER_LENGTH,
    TokenType.BYTE_LENGTH,
    TokenType.OCTET_LENGTH,
    TokenType.PATH_LENGTH,
    TokenType.CARDINALITY,
}

DATETIME_FUNCTION_TOKENS: set[TokenType] = {
    TokenType.DATE,
    TokenType.TIME,
    TokenType.DATETIME,
    TokenType.TIMESTAMP,
    TokenType.CURRENT_DATE,
    TokenType.CURRENT_TIME,
    TokenType.CURRENT_TIMESTAMP,
    TokenType.LOCAL_DATETIME,
    TokenType.LOCAL_TIME,
    TokenType.LOCAL_TIMESTAMP,
    TokenType.ZONED_DATETIME,
    TokenType.ZONED_TIME,
}

DURATION_FUNCTION_TOKENS: set[TokenType] = {
    TokenType.DURATION,
    TokenType.DURATION_BETWEEN,
}

STRING_FUNCTION_TOKENS: set[TokenType] = {
    TokenType.LOWER,
    TokenType.UPPER,
    TokenType.TRIM,
    TokenType.LTRIM,
    TokenType.RTRIM,
    TokenType.BTRIM,
    TokenType.SUBSTRING,
    TokenType.NORMALIZE,
    TokenType.LEFT,
    TokenType.RIGHT,
}

LIST_FUNCTION_TOKENS: set[TokenType] = {
    TokenType.ELEMENTS,
}

PATH_TOKENS: set[TokenType] = {
    TokenType.PATH,
}

REFERENCE_TOKENS: set[TokenType] = {
    TokenType.TABLE,
    TokenType.GRAPH,
}

ARITHMETIC_OPERATOR_TOKENS: set[TokenType] = {
    TokenType.PLUS_SIGN,
    TokenType.MINUS_SIGN,
    TokenType.ASTERISK,
    TokenType.SOLIDUS,
}


@parses(ast.GraphExpression)
def parse_graph_expression(parser: Parser) -> ast.GraphExpression:
    candidates_graph_expression = (
        parser.get_parser(ast.ObjectExpressionPrimary),
        parser.get_parser(ast.GraphReference),
        parser.get_parser(ast.ObjectNameOrBindingVariable),
        parser.get_parser(ast.CurrentGraph),
    )
    (result,) = parser.seq(candidates_graph_expression)
    return result


@parses(ast.BindingTableExpression)
def parse_binding_table_expression(parser: Parser) -> ast.BindingTableExpression:
    candidates_binding_table_expression = (
        parser.get_parser(ast.NestedBindingTableQuerySpecification),
        parser.get_parser(ast.ObjectExpressionPrimary),
        parser.get_parser(ast.BindingTableReference),
        parser.get_parser(ast.ObjectNameOrBindingVariable),
    )
    (result,) = parser.seq(candidates_binding_table_expression)
    return result


@parses(ast.CompositeQueryExpression)
def parse_composite_query_expression(parser: Parser) -> ast.CompositeQueryExpression:
    def _parse_query_conjunction_element(
        parser: Parser,
    ) -> ast.CompositeQueryExpression._QueryConjunctionElement:
        (query_conjunction, composite_query_primary) = parser.seq(
            parser.get_parser(ast.QueryConjunction),
            parser.get_parser(ast.CompositeQueryPrimary),
        )
        return ast.CompositeQueryExpression._QueryConjunctionElement(
            query_conjunction=query_conjunction,
            composite_query_primary=composite_query_primary,
        )

    (
        composite_query_primary,
        query_conjunction_elements,
    ) = parser.seq(
        parser.get_parser(ast.CompositeQueryPrimary),
        parser.opt(
            lambda parser: parser.seq(parser.list_(_parse_query_conjunction_element, None))[0],
        ),
    )
    return ast.CompositeQueryExpression(
        left_composite_query_primary=composite_query_primary,
        query_conjunction_elements=query_conjunction_elements,
    )


@parses(ast.PathPatternExpression)
def parse_path_pattern_expression(parser: Parser) -> ast.PathPatternExpression:
    (first_term,) = parser.seq(parser.get_parser(ast.PathTerm))

    if parser._match(TokenType.MULTISET_ALTERNATION_OPERATOR):
        (
            _,
            remaining_list_path_term,
        ) = parser.seq(
            TokenType.MULTISET_ALTERNATION_OPERATOR,
            parser.list_(parser.get_parser(ast.PathTerm), TokenType.MULTISET_ALTERNATION_OPERATOR),
        )
        return ast.PathMultisetAlternation(list_path_term=[first_term, *remaining_list_path_term])
    if parser._match(TokenType.VERTICAL_BAR):
        (
            _,
            remaining_list_path_term,
        ) = parser.seq(
            TokenType.VERTICAL_BAR,
            parser.list_(parser.get_parser(ast.PathTerm), TokenType.VERTICAL_BAR),
        )
        return ast.PathPatternUnion(list_path_term=[first_term, *remaining_list_path_term])

    return first_term


@parses(ast.IsLabelExpression)
def parse_is_label_expression(parser: Parser) -> ast.IsLabelExpression:
    (
        _,
        label_expression,
    ) = parser.seq(
        {TokenType.IS, TokenType.COLON},
        parser.get_parser(ast.LabelExpression),
    )
    return ast.IsLabelExpression(
        label_expression=label_expression,
    )


@parses(ast.LabelExpression)
def parse_label_expression(parser: Parser) -> ast.LabelExpression:
    (label_terms,) = parser.seq(
        parser.list_(parser.get_parser(ast.LabelTerm), TokenType.VERTICAL_BAR),
    )
    return ast.LabelExpression(label_terms=label_terms)


@parses(ast.LetValueExpression)
def parse_let_value_expression(parser: Parser) -> ast.LetValueExpression:
    (_, let_variable_definition_list, _, value_expression, _) = parser.seq(
        TokenType.LET,
        parser.get_parser(ast.LetVariableDefinitionList),
        TokenType.IN,
        parser.get_parser(ast.ValueExpression),
        TokenType.END,
    )
    return ast.LetValueExpression(
        let_variable_definition_list=let_variable_definition_list,
        value_expression=value_expression,
    )


@parses(ast.ValueQueryExpression)
def parse_value_query_expression(parser: Parser) -> ast.ValueQueryExpression:
    (
        _,
        nested_query_specification,
    ) = parser.seq(
        TokenType.VALUE,
        parser.get_parser(ast.NestedQuerySpecification),
    )
    return ast.ValueQueryExpression(
        nested_query_specification=nested_query_specification,
    )


@parses(ast.CaseExpression)
def parse_case_expression(parser: Parser) -> ast.CaseExpression:
    candidates_case_expression = (
        parser.get_parser(ast.CaseAbbreviation),
        parser.get_parser(ast.CaseSpecification),
    )
    (result,) = parser.seq(candidates_case_expression)
    return result


@parses(ast.DependentValueExpression)
def parse_dependent_value_expression(parser: Parser) -> ast.DependentValueExpression:
    (
        set_quantifier,
        numeric_value_expression,
    ) = parser.seq(
        parser.opt(parser.get_parser(ast.SetQuantifier)),
        parser.get_parser(ast.NumericValueExpression),
    )
    return ast.DependentValueExpression(
        set_quantifier=set_quantifier,
        numeric_value_expression=numeric_value_expression,
    )


@parses(ast.ParenthesizedValueExpression)
def parse_parenthesized_value_expression(parser: Parser) -> ast.ParenthesizedValueExpression:
    (
        _,
        value_expression,
        _,
    ) = parser.seq(
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.ValueExpression),
        TokenType.RIGHT_PAREN,
    )
    return ast.ParenthesizedValueExpression(
        value_expression=value_expression,
    )


@parses(ast.ValueExpression)
def parse_value_expression(parser: Parser) -> ast.ValueExpression:
    candidates_value_expression = (
        parser.get_parser(ast.CommonValueExpression),
        parser.get_parser(ast.BooleanValueExpression),
    )
    (result,) = parser.seq(candidates_value_expression)
    return result


@parses(ast.LengthExpression)
def parse_length_expression(parser: Parser) -> ast.LengthExpression:
    candidates_length_expression = (
        parser.get_parser(ast.CharLengthExpression),
        parser.get_parser(ast.ByteLengthExpression),
        parser.get_parser(ast.PathLengthExpression),
    )
    (result,) = parser.seq(candidates_length_expression)
    return result


@parses(ast.CardinalityExpression)
def parse_cardinality_expression(parser: Parser) -> ast.CardinalityExpression:
    def _parse__cardinality_left_paren_cardinality_expression_argument_right_paren(
        parser: Parser,
    ) -> ast.CardinalityExpression._CardinalityLeftParenCardinalityExpressionArgumentRightParen:
        (
            _,
            _,
            cardinality_expression_argument,
            _,
        ) = parser.seq(
            TokenType.CARDINALITY,
            TokenType.LEFT_PAREN,
            parser.get_parser(ast.CardinalityExpressionArgument),
            TokenType.RIGHT_PAREN,
        )
        return (
            ast.CardinalityExpression._CardinalityLeftParenCardinalityExpressionArgumentRightParen(
                cardinality_expression_argument=cardinality_expression_argument,
            )
        )

    def _parse__size_left_paren_list_value_expression_right_paren(
        parser: Parser,
    ) -> ast.CardinalityExpression._SizeLeftParenListValueExpressionRightParen:
        (
            _,
            _,
            list_value_expression,
            _,
        ) = parser.seq(
            TokenType.SIZE,
            TokenType.LEFT_PAREN,
            parser.get_parser(ast.ListValueExpression),
            TokenType.RIGHT_PAREN,
        )
        return ast.CardinalityExpression._SizeLeftParenListValueExpressionRightParen(
            list_value_expression=list_value_expression,
        )

    candidates_cardinality_expression = (
        _parse__cardinality_left_paren_cardinality_expression_argument_right_paren,
        _parse__size_left_paren_list_value_expression_right_paren,
    )
    (cardinality_expression,) = parser.seq(candidates_cardinality_expression)
    return ast.CardinalityExpression(
        cardinality_expression=cardinality_expression,
    )


@parses(ast.AbsoluteValueExpression)
def parse_absolute_value_expression(parser: Parser) -> ast.AbsoluteValueExpression:
    (
        _,
        _,
        numeric_value_expression,
        _,
    ) = parser.seq(
        TokenType.ABS,
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.NumericValueExpression),
        TokenType.RIGHT_PAREN,
    )
    return ast.AbsoluteValueExpression(
        numeric_value_expression=numeric_value_expression,
    )


@parses(ast.ModulusExpression)
def parse_modulus_expression(parser: Parser) -> ast.ModulusExpression:
    (
        _,
        _,
        numeric_value_expression_dividend,
        _,
        numeric_value_expression_divisor,
        _,
    ) = parser.seq(
        TokenType.MOD,
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.NumericValueExpressionDividend),
        TokenType.COMMA,
        parser.get_parser(ast.NumericValueExpressionDivisor),
        TokenType.RIGHT_PAREN,
    )
    return ast.ModulusExpression(
        numeric_value_expression_dividend=numeric_value_expression_dividend,
        numeric_value_expression_divisor=numeric_value_expression_divisor,
    )


_BOOL_LITERAL_TOKENS = {TokenType.TRUE, TokenType.FALSE, TokenType.UNKNOWN}
_BOOL_OP_TOKENS = {TokenType.AND, TokenType.OR, TokenType.XOR}


@parses(ast.CommonValueExpression)
def parse_common_value_expression(parser: Parser) -> ast.CommonValueExpression:
    """
    Uses function prefix lookups to route to the correct parser when possible.
    AmbiguousValueExpression is used as the default for ambiguous cases (e.g., `a + b`
    or `a || b`) where the type cannot be determined at parse time.
    """
    # Guard: boolean literals followed by boolean operators belong in
    # BooleanValueExpression, not here.  Without this check, `true AND false`
    # would be consumed as a bare `true` (ArithmeticValueExpression) and the
    # AND token left unconsumed, causing a parse error.
    if parser._match(_BOOL_LITERAL_TOKENS) and parser._match_next(_BOOL_OP_TOKENS):
        raise ParseError("Boolean literal followed by boolean operator")

    # Fast-path: definitive type indicators based on function keywords.
    if parser._match(DURATION_FUNCTION_TOKENS):
        return parser.get_parser(ast.DurationValueExpression)(parser)

    if parser._match(DATETIME_FUNCTION_TOKENS):
        return parser.get_parser(ast.DatetimeValueExpression)(parser)

    if parser._match(STRING_FUNCTION_TOKENS):
        return parser.get_parser(ast.StringValueExpression)(parser)

    if parser._match(NUMERIC_FUNCTION_TOKENS):
        return parser.get_parser(ast.NumericValueExpression)(parser)

    if parser._match(LIST_FUNCTION_TOKENS):
        return parser.get_parser(ast.ListValueExpression)(parser)

    if parser._match(REFERENCE_TOKENS):
        return parser.get_parser(ast.ReferenceValueExpression)(parser)

    # Fast-path for string literals - they can have || concatenation
    if parser._match(TokenType.STRING):
        return parser.get_parser(ast.StringValueExpression)(parser)

    # Fast-path for byte string literals
    if parser._match(TokenType.BYTE_STRING):
        return parser.get_parser(ast.ByteStringValueExpression)(parser)

    # Fast-path for list literals - they can have || concatenation
    if parser._match(TokenType.LEFT_BRACKET):
        return parser.get_parser(ast.ListValueExpression)(parser)

    # Fast-path for path value constructors - they can have || concatenation
    if parser._match(PATH_TOKENS):
        return parser.get_parser(ast.PathValueExpression)(parser)

    # Function calls: name(args) — FUNCTIONS → FUNC_REGISTRY → Anonymous (GG:FN01)
    if parser._match(TokenType.VAR) and parser._match_next(TokenType.LEFT_PAREN):
        return parse_function_call(parser)

    # Dotted namespace functions: ns.func(args) — try parse, fall through on failure
    if parser._match(TokenType.VAR) and parser._match_next(TokenType.PERIOD):
        dotted_result = parser.try_parse(parse_dotted_function)
        if dotted_result is not None:
            return t.cast(ast.CommonValueExpression, dotted_result)
        # Fall through to AmbiguousValueExpression (property access)

    # For ambiguous cases (no definitive keyword), delegate to AmbiguousValueExpression
    # This handles cases like `a || b` (concatenation) and `a + b` (arithmetic)
    return parser.get_parser(ast.AmbiguousValueExpression)(parser)


@parses(ast.BooleanValueExpression)
def parse_boolean_value_expression(parser: Parser) -> ast.BooleanValueExpression:
    def _parse__op_boolean_term(parser: Parser) -> ast.BooleanValueExpression._OpBooleanTerm:
        (
            operator_token,
            boolean_term,
        ) = parser.seq(
            {TokenType.OR, TokenType.XOR},
            parser.get_parser(ast.BooleanTerm),
        )

        match operator_token.token_type:
            case TokenType.OR:
                operator = ast.BooleanValueExpression.Operator.OR
            case TokenType.XOR:
                operator = ast.BooleanValueExpression.Operator.XOR

        return ast.BooleanValueExpression._OpBooleanTerm(
            operator=operator,
            boolean_term=boolean_term,
        )

    (
        boolean_term,
        ops,
    ) = parser.seq(
        parser.get_parser(ast.BooleanTerm),
        parser.opt(
            lambda parser: parser.seq(
                parser.list_(
                    _parse__op_boolean_term,
                    None,
                ),
            )[0],
        ),
    )
    return ast.BooleanValueExpression(
        boolean_term=boolean_term,
        ops=ops,
    )


@parses(ast.ParenthesizedBooleanValueExpression)
def parse_parenthesized_boolean_value_expression(
    parser: Parser,
) -> ast.ParenthesizedBooleanValueExpression:
    (
        _,
        boolean_value_expression,
        _,
    ) = parser.seq(
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.BooleanValueExpression),
        TokenType.RIGHT_PAREN,
    )
    return ast.ParenthesizedBooleanValueExpression(
        boolean_value_expression=boolean_value_expression,
    )


@parses(ast.CharLengthExpression)
def parse_char_length_expression(parser: Parser) -> ast.CharLengthExpression:
    (
        _,
        _,
        character_string_value_expression,
        _,
    ) = parser.seq(
        TokenType.CHAR_LENGTH,
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.CharacterStringValueExpression),
        TokenType.RIGHT_PAREN,
    )
    return ast.CharLengthExpression(
        character_string_value_expression=character_string_value_expression,
    )


@parses(ast.ByteLengthExpression)
def parse_byte_length_expression(parser: Parser) -> ast.ByteLengthExpression:
    (
        _,
        _,
        byte_string_value_expression,
        _,
    ) = parser.seq(
        TokenType.BYTE_LENGTH,
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.ByteStringValueExpression),
        TokenType.RIGHT_PAREN,
    )
    return ast.ByteLengthExpression(
        byte_string_value_expression=byte_string_value_expression,
    )


@parses(ast.PathLengthExpression)
def parse_path_length_expression(parser: Parser) -> ast.PathLengthExpression:
    (
        _,
        _,
        path_value_expression,
        _,
    ) = parser.seq(
        TokenType.PATH_LENGTH,
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.PathValueExpression),
        TokenType.RIGHT_PAREN,
    )
    return ast.PathLengthExpression(
        path_value_expression=path_value_expression,
    )


@parses(ast.ReferenceValueExpression)
def parse_reference_value_expression(parser: Parser) -> ast.ReferenceValueExpression:
    candidates_reference_value_expression = (
        parser.get_parser(ast.GraphReferenceValueExpression),
        parser.get_parser(ast.BindingTableReferenceValueExpression),
        parser.get_parser(ast.NodeReferenceValueExpression),
        parser.get_parser(ast.EdgeReferenceValueExpression),
    )
    (result,) = parser.seq(candidates_reference_value_expression)
    return result


@parses(ast.PathValueExpression)
def parse_path_value_expression(parser: Parser) -> ast.PathValueExpression:
    (list_path_value_primary,) = parser.seq(
        parser.list_(
            parser.get_parser(ast.PathValuePrimary),
            TokenType.CONCATENATION_OPERATOR,
        ),
    )
    return ast.PathValueExpression(list_path_value_primary=list_path_value_primary)


@parses(ast.ListValueExpression)
def parse_list_value_expression(parser: Parser) -> ast.ListValueExpression:
    (list_list_primary,) = parser.seq(
        parser.list_(
            parser.get_parser(ast.ListPrimary),
            TokenType.CONCATENATION_OPERATOR,
        ),
    )
    return ast.ListValueExpression(list_list_primary=list_list_primary)


@parses(ast.NumericValueExpression)
def parse_numeric_value_expression(parser: Parser) -> ast.NumericValueExpression:
    def _parser__signed_term(parser: Parser) -> ast.NumericValueExpression._SignedTerm:
        (
            sign,
            term,
        ) = parser.seq(
            parser.get_parser(ast.Sign),
            parser.get_parser(ast.Term),
        )
        return ast.NumericValueExpression._SignedTerm(
            sign=sign,
            term=term,
        )

    (
        base,
        steps,
    ) = parser.seq(
        parser.get_parser(ast.Term),
        parser.list_(_parser__signed_term, None, min_items=0),
    )
    return ast.NumericValueExpression(
        base=base,
        steps=steps or None,
    )


@parses(ast.ArithmeticAbsoluteValueFunction)
def parse_arithmetic_absolute_value_function(
    parser: Parser,
) -> ast.ArithmeticAbsoluteValueFunction:
    """
    This handles the ambiguous case of ABS() where the inner expression
    could be either numeric or duration. Type resolution is deferred to
    semantic analysis.
    """
    (_, _, arithmetic_value_expression, _) = parser.seq(
        TokenType.ABS,
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.ArithmeticValueExpression),
        TokenType.RIGHT_PAREN,
    )
    return ast.ArithmeticAbsoluteValueFunction(
        arithmetic_value_expression=arithmetic_value_expression,
    )


@parses(ast.ArithmeticPrimary)
def parse_arithmetic_primary(parser: Parser) -> ast.ArithmeticPrimary:
    """
    Note: We expand the candidates to handle various constructs:
    - ArithmeticAbsoluteValueFunction: ABS(...) where type is ambiguous
    - DurationFunction: DURATION ( ... ) function calls
    - DatetimeSubtraction: DURATION_BETWEEN(...) function calls
    - NumericValueFunction: other numeric functions like FLOOR, CEILING, etc.
    - ValueExpressionPrimary: handles literals including DurationLiteral

    ABS is handled by ArithmeticAbsoluteValueFunction rather than the
    type-specific AbsoluteValueExpression or DurationAbsoluteValueFunction
    because at parse time we cannot determine if the inner expression is
    numeric or duration.
    """
    # Try ArithmeticAbsoluteValueFunction first for ABS token
    # This captures the ambiguous case where we don't know if it's
    # numeric ABS or duration ABS at parse time
    if parser._match({TokenType.ABS}):
        return parse_arithmetic_absolute_value_function(parser)

    candidates = (
        parser.get_parser(ast.DurationFunction),
        parser.get_parser(ast.DatetimeSubtraction),
        parser.get_parser(ast.NumericValueFunction),
        parser.get_parser(ast.ValueExpressionPrimary),
    )
    (result,) = parser.seq(candidates)
    return result


_INT64_MAX = 9223372036854775807  # 2^63 - 1


def _check_int64_positive_overflow(sign: ast.Sign, primary: ast.Expression) -> None:
    """Reject unsigned int > INT64_MAX when sign is not minus.

    The literal parser allows up to 2^63 so ``-2^63`` works, but
    positive 2^63 exceeds int64 max (2^63 - 1).
    """
    if (
        sign != ast.Sign.MINUS_SIGN
        and isinstance(primary, ast.UnsignedNumericLiteral)
        and isinstance(primary.value, int)
        and primary.value > _INT64_MAX
    ):
        raise ValidationError(f"Integer literal {primary.value} exceeds maximum value {_INT64_MAX}")


@parses(ast.ArithmeticFactor)
def parse_arithmetic_factor(parser: Parser) -> ast.ArithmeticFactor:
    (
        sign,
        arithmetic_primary,
    ) = parser.seq(
        parser.opt(parser.get_parser(ast.Sign)),
        parse_arithmetic_primary,
    )
    effective_sign = sign or ast.Sign.PLUS_SIGN
    _check_int64_positive_overflow(effective_sign, arithmetic_primary)
    return ast.ArithmeticFactor(
        sign=effective_sign,
        arithmetic_primary=arithmetic_primary,
    )


@parses(ast.ArithmeticTerm)
def parse_arithmetic_term(parser: Parser) -> ast.ArithmeticTerm:
    def _parse__multiplicative_factor(
        parser: Parser,
    ) -> ast.ArithmeticTerm._MultiplicativeFactor:
        (
            operator_token,
            factor,
        ) = parser.seq(
            {TokenType.ASTERISK, TokenType.SOLIDUS},
            parse_arithmetic_factor,
        )

        match operator_token.token_type:
            case TokenType.ASTERISK:
                operator = ast.MultiplicativeOperator.MULTIPLY
            case TokenType.SOLIDUS:
                operator = ast.MultiplicativeOperator.DIVIDE

        return ast.ArithmeticTerm._MultiplicativeFactor(
            operator=operator,
            factor=factor,
        )

    (
        base,
        steps,
    ) = parser.seq(
        parse_arithmetic_factor,
        parser.list_(_parse__multiplicative_factor, None, min_items=0),
    )
    return ast.ArithmeticTerm(
        base=base,
        steps=steps or None,
    )


@parses(ast.ArithmeticValueExpression)
def parse_arithmetic_value_expression(parser: Parser) -> ast.ArithmeticValueExpression:
    """
    This handles type-ambiguous arithmetic expressions where the actual type
    (numeric or duration) cannot be determined at parse time.
    """

    def _parse__signed_term(parser: Parser) -> ast.ArithmeticValueExpression._SignedTerm:
        (
            sign,
            term,
        ) = parser.seq(
            parser.get_parser(ast.Sign),
            parse_arithmetic_term,
        )
        return ast.ArithmeticValueExpression._SignedTerm(
            sign=sign,
            term=term,
        )

    (
        base,
        steps,
    ) = parser.seq(
        parse_arithmetic_term,
        parser.list_(_parse__signed_term, None, min_items=0),
    )
    return ast.ArithmeticValueExpression(
        base=base,
        steps=steps or None,
    )


@parses(ast.AmbiguousValueExpression)
def parse_ambiguous_value_expression(parser: Parser) -> ast.AmbiguousValueExpression:
    """Parse ambiguous value expressions (arithmetic or concatenation).

    This function handles cases where we can't determine expression type
    from initial tokens (e.g., plain identifiers like `a || b` or `a + b`).

    Strategy:
    1. Parse a ValueExpressionPrimary first
    2. Check what operator follows to determine expression type
    """
    start_pos = parser._index

    # Try to parse a ValueExpressionPrimary first
    first_primary = parser.try_parse(parser.get_parser(ast.ValueExpressionPrimary))

    if first_primary is not None:
        first_primary = t.cast(ast.ValueExpressionPrimary, first_primary)
        # Check what operator follows
        if parser._match(TokenType.CONCATENATION_OPERATOR):
            # Concatenation: collect all operands
            operands: list[ast.ValueExpressionPrimary] = [first_primary]
            while parser._match(TokenType.CONCATENATION_OPERATOR):
                parser._advance()  # consume ||
                (next_operand,) = parser.seq(parser.get_parser(ast.ValueExpressionPrimary))
                operands.append(t.cast(ast.ValueExpressionPrimary, next_operand))
            return ast.ConcatenationValueExpression(operands=operands)

        elif parser._match(ARITHMETIC_OPERATOR_TOKENS):
            # Arithmetic operator follows - backtrack and parse as ArithmeticValueExpression
            parser._retreat(start_pos)
            return parser.get_parser(ast.ArithmeticValueExpression)(parser)

        else:
            # No operator - wrap primary in ArithmeticValueExpression for type consistency
            return _wrap_primary_as_arithmetic(first_primary)

    # Fallback to ArithmeticValueExpression for complex cases
    return parser.get_parser(ast.ArithmeticValueExpression)(parser)


def _wrap_primary_as_arithmetic(
    primary: ast.ValueExpressionPrimary,
) -> ast.ArithmeticValueExpression:
    """Wrap a ValueExpressionPrimary in ArithmeticValueExpression structure."""
    _check_int64_positive_overflow(ast.Sign.PLUS_SIGN, primary)
    return ast.ArithmeticValueExpression(
        base=ast.ArithmeticTerm(
            base=ast.ArithmeticFactor(
                sign=ast.Sign.PLUS_SIGN,
                arithmetic_primary=primary,
            ),
            steps=None,
        ),
        steps=None,
    )


@parses(ast.StringValueExpression)
def parse_string_value_expression(parser: Parser) -> ast.StringValueExpression:
    """
    Note: We need to look ahead to determine if this is a byte string expression.
    Both ByteStringLiteral and CharacterStringLiteral can be parsed through
    GeneralLiteral, so we use a lookahead to detect BYTE_STRING tokens.
    """
    # Look ahead: if we see BYTE_STRING anywhere in the upcoming tokens
    # before a statement terminator, try ByteStringValueExpression first
    start_idx = parser._index
    has_byte_string = False
    paren_depth = 0

    # Scan ahead to check for BYTE_STRING tokens
    for i in range(start_idx, len(parser._tokens)):
        token = parser._tokens[i]
        if token.token_type == TokenType.BYTE_STRING:
            has_byte_string = True
            break
        # Stop at statement boundaries
        if token.token_type in (TokenType.SEMICOLON, TokenType.EOF):
            break
        # Track parentheses to limit scope
        if token.token_type == TokenType.LEFT_PAREN:
            paren_depth += 1
        elif token.token_type == TokenType.RIGHT_PAREN:
            paren_depth -= 1
            if paren_depth < 0:
                break

    if has_byte_string:
        candidates_string_value_expression = (
            parser.get_parser(ast.ByteStringValueExpression),
            parser.get_parser(ast.CharacterStringValueExpression),
        )
    else:
        candidates_string_value_expression = (
            parser.get_parser(ast.CharacterStringValueExpression),
            parser.get_parser(ast.ByteStringValueExpression),
        )
    (result,) = parser.seq(candidates_string_value_expression)
    return result


@parses(ast.DatetimeValueExpression)
def parse_datetime_value_expression(parser: Parser) -> ast.DatetimeValueExpression:
    def _parse__duration_value_expression_plus_datetime_primary(
        parser: Parser,
    ) -> ast.DatetimeValueExpression._DurationValueExpressionPlusDatetimePrimary:
        (
            duration_value_expression,
            _,
            datetime_primary,
        ) = parser.seq(
            parser.get_parser(ast.DurationValueExpression),
            TokenType.PLUS_SIGN,
            parser.get_parser(ast.DatetimePrimary),
        )
        return ast.DatetimeValueExpression._DurationValueExpressionPlusDatetimePrimary(
            duration_value_expression=duration_value_expression,
            datetime_primary=datetime_primary,
        )

    def _parse__signed_duration_term(
        parser: Parser,
    ) -> ast.DatetimeValueExpression._SignedDurationTerm:
        (
            sign,
            duration_term,
        ) = parser.seq(
            parser.get_parser(ast.Sign),
            parser.get_parser(ast.DurationTerm),
        )
        return ast.DatetimeValueExpression._SignedDurationTerm(
            sign=sign,
            duration_term=duration_term,
        )

    candidates_base = (
        parser.get_parser(ast.DatetimePrimary),
        _parse__duration_value_expression_plus_datetime_primary,
    )
    (base, steps) = parser.seq(
        candidates_base,
        parser.opt(
            lambda parser: parser.seq(
                parser.list_(_parse__signed_duration_term, None),
            )[0],
        ),
    )
    return ast.DatetimeValueExpression(
        base=base,
        steps=steps,
    )


@parses(ast.DurationValueExpression)
def parse_duration_value_expression(parser: Parser) -> ast.DurationValueExpression:
    """
    Uses a base-and-steps pattern to handle addition/subtraction naturally
    (similar to NumericValueExpression).
    """

    def _parse_signed_duration_term(
        parser: Parser,
    ) -> ast.DurationValueExpression._SignedDurationTerm:
        (sign, duration_term) = parser.seq(
            parser.get_parser(ast.Sign),
            parser.get_parser(ast.DurationTerm),
        )
        return ast.DurationValueExpression._SignedDurationTerm(
            sign=sign,
            duration_term=duration_term,
        )

    # Try DatetimeSubtraction first (DURATION_BETWEEN keyword is definitive)
    # Otherwise parse as duration term with optional +/- steps
    base_candidates = (
        parser.get_parser(ast.DatetimeSubtraction),
        parser.get_parser(ast.DurationTerm),
    )

    (base,) = parser.seq(base_candidates)

    # If base is DatetimeSubtraction, no steps are allowed
    if isinstance(base, ast.DatetimeSubtraction):
        return ast.DurationValueExpression(base=base, steps=None)

    # Otherwise, parse optional +/- duration term steps
    # Use parser.seq to properly resolve ListPart from parser.list_
    (steps,) = parser.seq(
        parser.list_(_parse_signed_duration_term, None, min_items=0),
    )

    return ast.DurationValueExpression(
        base=base,
        steps=steps or None,
    )


@parses(ast.ParenthesizedPathPatternExpression)
def parse_parenthesized_path_pattern_expression(
    parser: Parser,
) -> ast.ParenthesizedPathPatternExpression:
    (
        _,
        subpath_variable_declaration,
        path_mode_prefix,
        path_pattern_expression,
        parenthesized_path_pattern_where_clause,
        _,
    ) = parser.seq(
        TokenType.LEFT_PAREN,
        parser.opt(parser.get_parser(ast.SubpathVariableDeclaration)),
        parser.opt(parser.get_parser(ast.PathModePrefix)),
        parser.get_parser(ast.PathPatternExpression),
        parser.opt(parser.get_parser(ast.ParenthesizedPathPatternWhereClause)),
        TokenType.RIGHT_PAREN,
    )
    return ast.ParenthesizedPathPatternExpression(
        subpath_variable_declaration=subpath_variable_declaration,
        path_mode_prefix=path_mode_prefix,
        path_pattern_expression=path_pattern_expression,
        parenthesized_path_pattern_where_clause=parenthesized_path_pattern_where_clause,
    )


@parses(ast.SimplifiedPathPatternExpression)
def parse_simplified_path_pattern_expression(parser: Parser) -> ast.SimplifiedPathPatternExpression:
    candidates_simplified_path_pattern_expression = (
        parser.get_parser(ast.SimplifiedDefaultingLeft),
        parser.get_parser(ast.SimplifiedDefaultingUndirected),
        parser.get_parser(ast.SimplifiedDefaultingRight),
        parser.get_parser(ast.SimplifiedDefaultingLeftOrUndirected),
        parser.get_parser(ast.SimplifiedDefaultingUndirectedOrRight),
        parser.get_parser(ast.SimplifiedDefaultingLeftOrRight),
        parser.get_parser(ast.SimplifiedDefaultingAnyDirection),
    )
    (result,) = parser.seq(candidates_simplified_path_pattern_expression)
    return result


@parses(ast.ParenthesizedLabelExpression)
def parse_parenthesized_label_expression(parser: Parser) -> ast.ParenthesizedLabelExpression:
    (
        _,
        label_expression,
        _,
    ) = parser.seq(
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.LabelExpression),
        TokenType.RIGHT_PAREN,
    )
    return ast.ParenthesizedLabelExpression(
        label_expression=label_expression,
    )


@parses(ast.GraphReferenceValueExpression)
def parse_graph_reference_value_expression(parser: Parser) -> ast.GraphReferenceValueExpression:
    def _parse__graph_graph_expression(
        parser: Parser,
    ) -> ast.GraphReferenceValueExpression._GraphGraphExpression:
        (
            _,
            graph_expression,
        ) = parser.seq(
            TokenType.GRAPH,
            parser.get_parser(ast.GraphExpression),
        )
        return ast.GraphReferenceValueExpression._GraphGraphExpression(
            graph_expression=graph_expression,
        )

    candidates_graph_reference_value_expression = (
        _parse__graph_graph_expression,
        parser.get_parser(ast.ValueExpressionPrimary),
    )
    (graph_reference_value_expression,) = parser.seq(candidates_graph_reference_value_expression)
    return ast.GraphReferenceValueExpression(
        graph_reference_value_expression=graph_reference_value_expression,
    )


@parses(ast.BindingTableReferenceValueExpression)
def parse_binding_table_reference_value_expression(
    parser: Parser,
) -> ast.BindingTableReferenceValueExpression:
    def _parse__table_binding_table_expression(
        parser: Parser,
    ) -> ast.BindingTableReferenceValueExpression._TableBindingTableExpression:
        (
            _,
            binding_table_expression,
        ) = parser.seq(
            TokenType.TABLE,
            parser.get_parser(ast.BindingTableExpression),
        )
        return ast.BindingTableReferenceValueExpression._TableBindingTableExpression(
            binding_table_expression=binding_table_expression,
        )

    candidates_binding_table_reference_value_expression = (
        _parse__table_binding_table_expression,
        parser.get_parser(ast.ValueExpressionPrimary),
    )
    (binding_table_reference_value_expression,) = parser.seq(
        candidates_binding_table_reference_value_expression
    )
    return ast.BindingTableReferenceValueExpression(
        binding_table_reference_value_expression=binding_table_reference_value_expression,
    )


@parses(ast.CharacterStringValueExpression)
def parse_character_string_value_expression(parser: Parser) -> ast.CharacterStringValueExpression:
    (list_character_string_value_expression,) = parser.seq(
        parser.list_(
            parser.get_parser(ast.CharacterStringPrimary),
            TokenType.CONCATENATION_OPERATOR,
        ),
    )
    return ast.CharacterStringValueExpression(
        list_character_string_value_expression=list_character_string_value_expression
    )


@parses(ast.ByteStringValueExpression)
def parse_byte_string_value_expression(parser: Parser) -> ast.ByteStringValueExpression:
    (list_byte_string_primary,) = parser.seq(
        parser.list_(
            parser.get_parser(ast.ByteStringPrimary),
            TokenType.CONCATENATION_OPERATOR,
        ),
    )
    return ast.ByteStringValueExpression(list_byte_string_primary=list_byte_string_primary)
