"""Shared Cypher dialect layer.

``CypherDialect`` is an abstract intermediate class between :class:`Dialect`
(the GQL base) and vendor-specific Cypher dialects like Neo4j.
It provides the shared Cypher syntax extensions (``STARTS WITH``, ``IN``,
``UNWIND``, ``MERGE``, etc.) that all Cypher-compatible databases share.

``CypherDialect`` is **not** registered in the :class:`Dialects` enum -- users
must pick a specific vendor.  Each vendor inherits shared Cypher features and
may add/remove vendor-specific behaviour.
"""

from __future__ import annotations

import typing as t

from decimal import Decimal

import graphglot.ast.functions as f

from graphglot import ast, features as F
from graphglot.ast.cypher import (
    ConstraintKind,
    CreateClause,
    CreateConstraint,
    CreateIndex,
    CypherChainedComparison,
    CypherPatternComprehension,
    CypherPatternPredicate,
    CypherPredicateComparison,
    CypherReduce,
    CypherSetAllFromExprItem,
    CypherSetMapAppendItem,
    CypherSetPropertyFromExprItem,
    CypherSimpleCase,
    CypherSliceExpression,
    CypherSubscriptExpression,
    CypherTemporalCast,
    CypherTemporalMethod,
    CypherWhenClause,
    CypherWithStatement,
    DropConstraint,
    DropIndex,
    InPredicate,
    ListComprehension,
    ListPredicateFunction,
    MergeClause,
    QueryPrefix,
    RegexMatchPredicate,
    StringMatchPredicate,
    TemporalBaseType,
)
from graphglot.dialect.base import Dialect
from graphglot.dialect.cypher_features import ALL_CYPHER_FEATURES
from graphglot.error import ParseError
from graphglot.features import Feature
from graphglot.generator import Generator as BaseGenerator, func_generators
from graphglot.generator.fragment import Fragment
from graphglot.lexer import Lexer as BaseLexer, Token, TokenType
from graphglot.parser import Parser as BaseParser
from graphglot.parser.functions import parse_func_args
from graphglot.transformations import with_to_next

# =============================================================================
# Parser functions (plain functions -- NOT @parses-decorated)
# =============================================================================


def _parse_string_match_predicate(parser: BaseParser) -> StringMatchPredicate:
    """Parse ``lhs STARTS WITH | ENDS WITH | CONTAINS rhs``.

    Tries each keyword form in order. Uses backtracking via ``try_parse_any``.
    """
    lhs = parser.get_parser(ast.ValueExpressionPrimary)(parser)

    if parser._match(TokenType.STARTS):
        parser._expect(TokenType.STARTS)
        parser._expect(TokenType.WITH)
        kind = StringMatchPredicate.MatchKind.STARTS_WITH
    elif parser._match(TokenType.ENDS):
        parser._expect(TokenType.ENDS)
        parser._expect(TokenType.WITH)
        kind = StringMatchPredicate.MatchKind.ENDS_WITH
    elif parser._match(TokenType.CONTAINS):
        parser._expect(TokenType.CONTAINS)
        kind = StringMatchPredicate.MatchKind.CONTAINS
    else:
        parser.raise_error("Expected STARTS WITH, ENDS WITH, or CONTAINS")
        raise  # unreachable but keeps type checker happy

    rhs = parser.get_parser(ast.ValueExpressionPrimary)(parser)
    return StringMatchPredicate(lhs=lhs, kind=kind, rhs=rhs)


def _parse_in_predicate(parser: BaseParser) -> InPredicate:
    """Parse ``value IN list_expression``."""
    (value, _, list_expression) = parser.seq(
        parser.get_parser(ast.ValueExpressionPrimary),
        TokenType.IN,
        parser.get_parser(ast.ValueExpression),
    )
    return InPredicate(value=value, list_expression=list_expression)


def _parse_regex_match_predicate(parser: BaseParser) -> RegexMatchPredicate:
    """Parse ``lhs =~ rhs`` regex match."""
    (lhs, _, rhs) = parser.seq(
        parser.get_parser(ast.ValueExpressionPrimary),
        TokenType.TILDE_EQUALS,
        parser.get_parser(ast.ValueExpressionPrimary),
    )
    return RegexMatchPredicate(lhs=lhs, rhs=rhs)


def _parse_list_comprehension(parser: BaseParser) -> ListComprehension:
    """Parse ``[variable IN source [WHERE pred] [| expr]]``."""
    parser._expect(TokenType.LEFT_BRACKET)
    variable = parser.get_parser(ast.BindingVariable)(parser)
    parser._expect(TokenType.IN)
    source = parser.get_parser(ast.ValueExpression)(parser)

    where_clause = t.cast(
        ast.WhereClause | None, parser.try_parse(parser.get_parser(ast.WhereClause))
    )

    projection: ast.ValueExpression | None = None
    if parser._match(TokenType.VERTICAL_BAR):
        parser._expect(TokenType.VERTICAL_BAR)
        projection = parser.get_parser(ast.ValueExpression)(parser)

    parser._expect(TokenType.RIGHT_BRACKET)
    return ListComprehension(
        variable=variable,
        source=source,
        where_clause=where_clause,
        projection=projection,
    )


def _parse_pattern_comprehension(parser: BaseParser) -> CypherPatternComprehension:
    """Parse ``[p = (pattern) [WHERE pred] | projection]``.

    Uses ``PathTerm`` instead of ``PathPattern`` to avoid the
    ``PathPatternExpression`` parser consuming ``|`` as a path-pattern union.
    Optionally handles ``p = ...`` path variable declaration before the pattern.
    """
    parser._expect(TokenType.LEFT_BRACKET)
    # Optional path variable declaration: p = ...
    path_var_decl = t.cast(
        ast.PathVariableDeclaration | None,
        parser.try_parse(parser.get_parser(ast.PathVariableDeclaration)),
    )
    # Parse as PathTerm (node-edge chain) to avoid | being consumed as PathPatternUnion
    path_term = parser.get_parser(ast.PathTerm)(parser)
    pattern = ast.PathPattern(
        path_variable_declaration=path_var_decl,
        path_pattern_prefix=None,
        path_pattern_expression=path_term,
    )
    where_clause = t.cast(
        ast.WhereClause | None, parser.try_parse(parser.get_parser(ast.WhereClause))
    )
    parser._expect(TokenType.VERTICAL_BAR)
    projection = parser.get_parser(ast.ValueExpression)(parser)
    parser._expect(TokenType.RIGHT_BRACKET)
    return CypherPatternComprehension(
        pattern=pattern,
        where_clause=where_clause,
        projection=projection,
    )


def _parse_cypher_list_or_comprehension(
    parser: BaseParser,
) -> ast.Expression:
    """Parse list comprehension, pattern comprehension, or standard list literal.

    All start with ``[``.  List comprehension has ``[<identifier> IN ...]``,
    pattern comprehension has ``[(<pattern>) ... | ...]``,
    and list literals have ``[<value_expression>, ...]`` or ``[]``.
    """
    comp = parser.try_parse(_parse_list_comprehension)
    if comp:
        return comp
    pcomp = parser.try_parse(_parse_pattern_comprehension)
    if pcomp:
        return pcomp
    # Fall back to standard list literal parser
    return BaseParser.PARSERS[ast.ListValueConstructorByEnumeration](parser)


def _parse_list_predicate_function(parser: BaseParser) -> ListPredicateFunction:
    """Parse ``all/any/none/single(variable IN source WHERE predicate)``."""
    if parser._match(TokenType.ALL):
        parser._expect(TokenType.ALL)
        kind = ListPredicateFunction.Kind.ALL
    elif parser._match(TokenType.ANY):
        parser._expect(TokenType.ANY)
        kind = ListPredicateFunction.Kind.ANY
    elif parser._match(TokenType.NONE_KW):
        parser._expect(TokenType.NONE_KW)
        kind = ListPredicateFunction.Kind.NONE
    elif parser._match(TokenType.SINGLE):
        parser._expect(TokenType.SINGLE)
        kind = ListPredicateFunction.Kind.SINGLE
    else:
        parser.raise_error("Expected all, any, none, or single")
        raise  # unreachable but keeps type checker happy

    parser._expect(TokenType.LEFT_PAREN)
    variable = parser.get_parser(ast.BindingVariable)(parser)
    parser._expect(TokenType.IN)
    source = parser.get_parser(ast.ValueExpression)(parser)
    parser._expect(TokenType.WHERE)
    predicate = parser.get_parser(ast.BooleanValueExpression)(parser)
    parser._expect(TokenType.RIGHT_PAREN)

    return ListPredicateFunction(
        kind=kind,
        variable=variable,
        source=source,
        predicate=predicate,
    )


def _parse_unwind_statement(parser: BaseParser) -> ast.ForStatement:
    """Parse ``UNWIND expr AS var`` and rewrite to :class:`ForStatement`.

    Cypher ``UNWIND [1,2,3] AS x`` is semantically identical to GQL
    ``FOR x IN [1,2,3]``.  Uses ValueExpression to allow subscript
    access like ``UNWIND arr[0] AS x``.
    """
    parser._expect(TokenType.UNWIND)
    # Use ValueExpression to allow subscript (qrows[p]), function (split(...)),
    # and other non-ListValueExpression forms as UNWIND source.
    source = parser.get_parser(ast.ValueExpression)(parser)
    parser._expect(TokenType.AS)
    var = parser.get_parser(ast.BindingVariable)(parser)
    return ast.ForStatement._construct(
        for_item=ast.ForItem._construct(
            for_item_alias=ast.ForItemAlias(binding_variable=var),
            for_item_source=source,
        ),
        for_ordinality_or_offset=None,
    )


def _parse_cypher_with_statement(parser: BaseParser) -> CypherWithStatement:
    """Parse Cypher ``WITH <return_body> [ORDER BY / LIMIT] [WHERE ...]``.

    WITH is parsed as a ``CypherWithStatement`` (a ``PrimitiveQueryStatement``)
    so it appears inline in ``SimpleLinearQueryStatement.list_simple_query_statement``
    alongside MATCH, FOR, FILTER, etc.

    The optional WHERE clause is absorbed directly into the
    ``CypherWithStatement.where_clause`` field.  This ensures correct
    generation in both the non-transformed path (``WITH n WHERE ...``) and
    the transformed path (``RETURN n NEXT FILTER WHERE ...``).
    """
    parser._expect(TokenType.WITH)
    body = parser.get_parser(ast.ReturnStatementBody)(parser)
    obps = t.cast(
        ast.OrderByAndPageStatement | None,
        parser.try_parse(parser.get_parser(ast.OrderByAndPageStatement)),
    )
    where = t.cast(
        ast.WhereClause | None,
        parser.try_parse(parser.get_parser(ast.WhereClause)),
    )
    return CypherWithStatement(
        return_statement_body=body,
        order_by_and_page_statement=obps,
        where_clause=where,
    )


def _parse_merge_clause(parser: BaseParser) -> MergeClause:
    """Parse ``MERGE <pattern> [ON CREATE SET ...] [ON MATCH SET ...]``."""
    parser._expect(TokenType.MERGE)
    path_pattern = parser.get_parser(ast.PathPattern)(parser)

    on_create_set: ast.SetItemList | None = None
    on_match_set: ast.SetItemList | None = None

    # First ON — could be ON CREATE SET or ON MATCH SET
    if parser._match(TokenType.ON):
        parser._expect(TokenType.ON)
        if parser._match(TokenType.CREATE):
            parser._expect(TokenType.CREATE)
            parser._expect(TokenType.SET)
            on_create_set = t.cast(ast.SetItemList, parser.get_parser(ast.SetItemList)(parser))
        elif parser._match(TokenType.MATCH):
            parser._expect(TokenType.MATCH)
            parser._expect(TokenType.SET)
            on_match_set = t.cast(ast.SetItemList, parser.get_parser(ast.SetItemList)(parser))

    # Second ON — the other sub-clause
    if (on_create_set is not None or on_match_set is not None) and parser._match(TokenType.ON):
        parser._expect(TokenType.ON)
        if parser._match(TokenType.MATCH) and on_match_set is None:
            parser._expect(TokenType.MATCH)
            parser._expect(TokenType.SET)
            on_match_set = t.cast(ast.SetItemList, parser.get_parser(ast.SetItemList)(parser))
        elif parser._match(TokenType.CREATE) and on_create_set is None:
            parser._expect(TokenType.CREATE)
            parser._expect(TokenType.SET)
            on_create_set = t.cast(ast.SetItemList, parser.get_parser(ast.SetItemList)(parser))

    return MergeClause(
        path_pattern=path_pattern,
        on_create_set=on_create_set,
        on_match_set=on_match_set,
    )


def _parse_create_clause(parser: BaseParser) -> CreateClause:
    """Parse ``CREATE <insert_graph_pattern>``."""
    parser._expect(TokenType.CREATE)
    pattern = parser.get_parser(ast.InsertGraphPattern)(parser)
    return CreateClause(insert_graph_pattern=pattern)


def _parse_query_prefix(parser: BaseParser) -> QueryPrefix:
    """Parse ``EXPLAIN <query>`` or ``PROFILE <query>``."""
    if parser._match(TokenType.EXPLAIN):
        parser._expect(TokenType.EXPLAIN)
        kind = QueryPrefix.Kind.EXPLAIN
    elif parser._match(TokenType.PROFILE):
        parser._expect(TokenType.PROFILE)
        kind = QueryPrefix.Kind.PROFILE
    else:
        parser.raise_error("Expected EXPLAIN or PROFILE")
        raise  # unreachable but keeps type checker happy

    body_parser = BaseParser.PARSERS[ast.GqlProgram]
    body = body_parser(parser)
    return QueryPrefix(kind=kind, body=body)


def _parse_cypher_gql_program(parser: BaseParser) -> ast.Expression:
    """Override GqlProgram parser to support EXPLAIN/PROFILE prefix."""
    prefix = parser.try_parse(_parse_query_prefix)
    if prefix:
        return prefix
    return BaseParser.PARSERS[ast.GqlProgram](parser)


def _parse_create_index(parser: BaseParser) -> CreateIndex:
    """Parse ``CREATE INDEX [name] [IF NOT EXISTS] FOR (var:label) ON (var.prop, ...)``
    or ``CREATE INDEX [name] [IF NOT EXISTS] FOR ()-[var:label]-() ON (var.prop, ...)``.
    """
    parser._expect(TokenType.CREATE)
    parser._expect(TokenType.INDEX)

    # optional name
    name: ast.Identifier | None = None
    if not parser._match(TokenType.IF) and not parser._match(TokenType.FOR):
        name = parser.get_parser(ast.Identifier)(parser)

    # optional IF NOT EXISTS
    if_not_exists = False
    if parser._match(TokenType.IF):
        parser._expect(TokenType.IF)
        parser._expect(TokenType.NOT)
        parser._expect(TokenType.EXISTS)
        if_not_exists = True

    parser._expect(TokenType.FOR)

    # Determine node vs relationship pattern
    is_relationship = False
    if parser._match(TokenType.LEFT_PAREN):
        # Could be (var:label) or ()-[var:label]-()
        parser._expect(TokenType.LEFT_PAREN)
        if parser._match(TokenType.RIGHT_PAREN):
            # ()-[var:label]-()
            parser._expect(TokenType.RIGHT_PAREN)
            parser._expect(TokenType.MINUS_LEFT_BRACKET)
            variable = parser.get_parser(ast.BindingVariable)(parser)
            parser._expect(TokenType.COLON)
            label = parser.get_parser(ast.Identifier)(parser)
            parser._expect(TokenType.RIGHT_BRACKET_MINUS)
            parser._expect(TokenType.LEFT_PAREN)
            parser._expect(TokenType.RIGHT_PAREN)
            is_relationship = True
        else:
            # (var:label)
            variable = parser.get_parser(ast.BindingVariable)(parser)
            parser._expect(TokenType.COLON)
            label = parser.get_parser(ast.Identifier)(parser)
            parser._expect(TokenType.RIGHT_PAREN)
    else:
        parser.raise_error("Expected '('")
        raise  # unreachable

    parser._expect(TokenType.ON)
    parser._expect(TokenType.LEFT_PAREN)

    # Parse property references: var.prop1, var.prop2, ...
    properties: list[ast.PropertyReference] = []
    prop = parser.get_parser(ast.PropertyReference)(parser)
    properties.append(prop)
    while parser._match(TokenType.COMMA):
        parser._expect(TokenType.COMMA)
        prop = parser.get_parser(ast.PropertyReference)(parser)
        properties.append(prop)

    parser._expect(TokenType.RIGHT_PAREN)

    return CreateIndex(
        name=name,
        if_not_exists=if_not_exists,
        variable=variable,
        label=label,
        is_relationship=is_relationship,
        properties=properties,
    )


def _parse_drop_index(parser: BaseParser) -> DropIndex:
    """Parse ``DROP INDEX name [IF EXISTS]``."""
    parser._expect(TokenType.DROP)
    parser._expect(TokenType.INDEX)
    name = parser.get_parser(ast.Identifier)(parser)

    if_exists = False
    if parser._match(TokenType.IF):
        parser._expect(TokenType.IF)
        parser._expect(TokenType.EXISTS)
        if_exists = True

    return DropIndex(name=name, if_exists=if_exists)


def _parse_create_constraint(parser: BaseParser) -> CreateConstraint:
    """Parse ``CREATE CONSTRAINT [name] [IF NOT EXISTS] FOR (var:label) REQUIRE ... IS <kind>``."""
    parser._expect(TokenType.CREATE)
    parser._expect(TokenType.CONSTRAINT)

    # optional name
    name: ast.Identifier | None = None
    if not parser._match(TokenType.IF) and not parser._match(TokenType.FOR):
        name = parser.get_parser(ast.Identifier)(parser)

    # optional IF NOT EXISTS
    if_not_exists = False
    if parser._match(TokenType.IF):
        parser._expect(TokenType.IF)
        parser._expect(TokenType.NOT)
        parser._expect(TokenType.EXISTS)
        if_not_exists = True

    parser._expect(TokenType.FOR)
    parser._expect(TokenType.LEFT_PAREN)
    variable = parser.get_parser(ast.BindingVariable)(parser)
    parser._expect(TokenType.COLON)
    label = parser.get_parser(ast.Identifier)(parser)
    parser._expect(TokenType.RIGHT_PAREN)

    parser._expect(TokenType.REQUIRE)

    # Parse property or (prop1, prop2, ...) for NODE KEY
    properties: list[ast.PropertyReference] = []
    if parser._match(TokenType.LEFT_PAREN):
        # (prop1, prop2, ...) — NODE KEY
        parser._expect(TokenType.LEFT_PAREN)
        prop = parser.get_parser(ast.PropertyReference)(parser)
        properties.append(prop)
        while parser._match(TokenType.COMMA):
            parser._expect(TokenType.COMMA)
            prop = parser.get_parser(ast.PropertyReference)(parser)
            properties.append(prop)
        parser._expect(TokenType.RIGHT_PAREN)
    else:
        # Single property reference
        prop = parser.get_parser(ast.PropertyReference)(parser)
        properties.append(prop)

    parser._expect(TokenType.IS)

    # Determine constraint kind: UNIQUE, NOT NULL, NODE KEY
    if parser._match(TokenType.UNIQUE):
        parser._expect(TokenType.UNIQUE)
        constraint_kind = ConstraintKind.UNIQUE
    elif parser._match(TokenType.NOT):
        parser._expect(TokenType.NOT)
        parser._expect(TokenType.NULL)
        constraint_kind = ConstraintKind.NOT_NULL
    elif parser._match(TokenType.NODE):
        parser._expect(TokenType.NODE)
        parser._expect(TokenType.KEY)
        constraint_kind = ConstraintKind.NODE_KEY
    else:
        parser.raise_error("Expected UNIQUE, NOT NULL, or NODE KEY")
        raise  # unreachable

    return CreateConstraint(
        name=name,
        if_not_exists=if_not_exists,
        variable=variable,
        label=label,
        properties=properties,
        constraint_kind=constraint_kind,
    )


def _parse_drop_constraint(parser: BaseParser) -> DropConstraint:
    """Parse ``DROP CONSTRAINT name [IF EXISTS]``."""
    parser._expect(TokenType.DROP)
    parser._expect(TokenType.CONSTRAINT)
    name = parser.get_parser(ast.Identifier)(parser)

    if_exists = False
    if parser._match(TokenType.IF):
        parser._expect(TokenType.IF)
        parser._expect(TokenType.EXISTS)
        if_exists = True

    return DropConstraint(name=name, if_exists=if_exists)


def _parse_cypher_catalog_statement(
    parser: BaseParser,
) -> ast.PrimitiveCatalogModifyingStatement:
    """Extended PrimitiveCatalogModifyingStatement parser with Cypher DDL.

    Tries Cypher DDL (CREATE/DROP INDEX, CREATE/DROP CONSTRAINT) first,
    then falls back to standard GQL catalog statements.
    """
    result = parser.try_parse_any(
        _parse_create_index,
        _parse_drop_index,
        _parse_create_constraint,
        _parse_drop_constraint,
    )
    if result:
        return t.cast(ast.PrimitiveCatalogModifyingStatement, result)
    return BaseParser.PARSERS[ast.PrimitiveCatalogModifyingStatement](parser)


# Token-based Func dispatch for keyword tokens that remain in the base GQL lexer.
# These can't become VAR tokens, so they need explicit routing.
_TOKEN_FUNCTIONS: dict[TokenType, type[f.Func]] = {
    TokenType.LABELS: f.Labels,
    TokenType.KEYS: f.Keys,
    TokenType.LAST: f.Last,
    TokenType.NODES: f.Nodes,
    TokenType.RELATIONSHIPS: f.Relationships,
    TokenType.SIZE: f.Size,
    TokenType.RANGE: f.RangeFunc,
    TokenType.TYPE: f.TypeFunc,
    TokenType.PROPERTIES: f.Properties,
    TokenType.ROUND: f.Round,
    TokenType.SUBSTRING: f.Substring,
}
_TOKEN_FUNCTION_TOKENS: set[TokenType] = set(_TOKEN_FUNCTIONS)

# Module-level FUNCTIONS dict — shared by Parser.FUNCTIONS and Generator via
# func_generators().  Hoisted here so both inner classes can reference it.
_CYPHER_FUNCTIONS: dict[str, type[f.Func]] = {
    "REPLACE": f.Replace,
    "PI": f.Pi,
    "ISEMPTY": f.IsEmpty,
    "ISNAN": f.IsNaN,
    "ATAN2": f.Atan2,
    "HAVERSIN": f.Haversin,
    "TAIL": f.Tail,
    "HEAD": f.Head,
    "REVERSE": f.ReverseFunc,
    "RAND": f.Rand,
    "SIGN": f.SignFunc,
    "STARTNODE": f.StartNode,
    "ENDNODE": f.EndNode,
    "SPLIT": f.Split,
    "TOLOWER": f.ToLower,
    "TOUPPER": f.ToUpper,
    # Token-dispatched functions (keyword tokens, not VAR).
    # Included here so FUNCTIONS is the single source of
    # "which Func types does this dialect support".
    "LABELS": f.Labels,
    "KEYS": f.Keys,
    "LAST": f.Last,
    "NODES": f.Nodes,
    "RELATIONSHIPS": f.Relationships,
    "SIZE": f.Size,
    "RANGE": f.RangeFunc,
    "TYPE": f.TypeFunc,
    "PROPERTIES": f.Properties,
    "ROUND": f.Round,
    "SUBSTRING": f.Substring,
}


def _parse_cypher_field(parser: BaseParser) -> ast.Field:
    """Parse a map field, accepting any keyword token as field name.

    In Cypher, any identifier-like token (including reserved words like
    ``existing``, ``null``, ``type``) can be used as a map field name.
    The standard GQL ``FieldName = Identifier`` parser only accepts
    ``VAR`` or ``NON_RESERVED_WORDS`` tokens, which is too restrictive.
    """
    token = parser._curr
    # Accept any token whose text looks like an identifier and is followed by ':'
    if token and token.text.isidentifier() and parser._match_next(TokenType.COLON):
        parser._advance()
        field_name = ast.Identifier(name=token.text)
    else:
        field_name = parser.get_parser(ast.FieldName)(parser)
    (_, value_expression) = parser.seq(
        TokenType.COLON,
        parser.get_parser(ast.ValueExpression),
    )
    return ast.Field(field_name=field_name, value_expression=value_expression)


def _parse_cypher_simple_case(
    parser: BaseParser,
) -> ast.SimpleCase | CypherSimpleCase:
    """Try standard GQL SimpleCase first; fall back to CypherSimpleCase for operands
    that don't fit the restricted CaseOperand/WhenOperand unions (e.g. ``CASE -1``).

    This ensures valid GQL CASE expressions produce standard AST nodes (transpilable
    to any dialect), while Cypher-only operands get the relaxed CypherSimpleCase.
    """
    standard = parser.try_parse(BaseParser.PARSERS[ast.SimpleCase])
    if standard is not None:
        return t.cast(ast.SimpleCase, standard)

    # Standard failed (operand outside CaseOperand union) — parse with relaxed types
    parser._expect(TokenType.CASE)
    case_operand = parser.get_parser(ast.ValueExpression)(parser)

    clauses: list[CypherWhenClause] = []
    while parser._match(TokenType.WHEN):
        parser._expect(TokenType.WHEN)
        operands: list[ast.ValueExpression] = []
        operands.append(parser.get_parser(ast.ValueExpression)(parser))
        while parser._match(TokenType.COMMA):
            parser._expect(TokenType.COMMA)
            operands.append(parser.get_parser(ast.ValueExpression)(parser))
        parser._expect(TokenType.THEN)
        result = parser.get_parser(ast.Result)(parser)
        clauses.append(CypherWhenClause(operands=operands, result=result))

    else_clause = t.cast(ast.ElseClause | None, parser.try_parse(parser.get_parser(ast.ElseClause)))
    parser._expect(TokenType.END)
    return CypherSimpleCase(
        case_operand=case_operand,
        when_clauses=clauses,
        else_clause=else_clause,
    )


# Type conversion function token set
_TYPE_CONV_TOKENS: set[TokenType] = {
    TokenType.TOBOOLEAN,
    TokenType.TOINTEGER,
    TokenType.TOFLOAT,
    TokenType.TOSTRING,
}


def _token_to_cast_target(token_type: TokenType) -> ast.ValueType:
    """Map a Cypher type-conversion token to its GQL CastTarget (ValueType)."""
    if token_type == TokenType.TOBOOLEAN:
        return ast.BooleanType(not_null=False)
    elif token_type == TokenType.TOINTEGER:
        return ast.SignedBinaryExactNumericType(
            signed_type=ast.SignedBinaryExactNumericType._Int(precision=None),
            not_null=False,
        )
    elif token_type == TokenType.TOFLOAT:
        return ast.ApproximateNumericType(
            approximate_numeric_type=ast.ApproximateNumericType._Float(precision_scale=None),
            not_null=False,
        )
    else:  # TOSTRING
        return ast.CharacterStringType(
            character_string_type=ast.CharacterStringType._String(min_length=None, max_length=None),
            not_null=False,
        )


_TEMPORAL_CAST_TARGETS: dict[TemporalBaseType, type[ast.ValueType]] = {
    TemporalBaseType.DATE: ast.DateType,
    TemporalBaseType.TIME: ast.TimeType,
    TemporalBaseType.DATETIME: ast.DatetimeType,
    TemporalBaseType.LOCALDATETIME: ast.LocaldatetimeType,
    TemporalBaseType.LOCALTIME: ast.LocaltimeType,
    # DURATION omitted — requires a qualifier not available in Cypher
}


def _cast_as_cve(arg: ast.ValueExpression, cast_target: ast.ValueType) -> ast.CommonValueExpression:
    """Wrap ``CAST(arg AS target)`` in the CVE hierarchy.

    CastSpecification is a NonParenthesizedValueExpressionPrimary, so it must
    be wrapped in ArithmeticFactor → ArithmeticTerm → ArithmeticValueExpression
    to produce a ``CommonValueExpression``.
    """
    cast_spec = ast.CastSpecification(cast_operand=arg, cast_target=cast_target)
    return ast.ArithmeticValueExpression(
        base=ast.ArithmeticTerm(
            base=ast.ArithmeticFactor(arithmetic_primary=cast_spec),
        ),
    )


def _parse_cypher_type_conversion(parser: BaseParser) -> ast.CommonValueExpression:
    """Parse ``toBoolean/toInteger/toFloat/toString ( expression )``.

    Creates a :class:`CastSpecification` and wraps it in the CVE hierarchy.
    """
    tok = parser._curr
    parser._advance()  # consume the function keyword
    parser._expect(TokenType.LEFT_PAREN)
    arg = parser.get_parser(ast.ValueExpression)(parser)
    parser._expect(TokenType.RIGHT_PAREN)
    return _cast_as_cve(arg, _token_to_cast_target(tok.token_type))


def _parse_cypher_pattern_predicate(parser: BaseParser) -> CypherPatternPredicate:
    """Parse a bare pattern as a predicate: ``(n)-[:T]->()``.

    Called from ``_parse_cypher_boolean_test`` when a ``(`` is found and the
    following tokens form a path pattern (not a parenthesized expression).
    """
    path_pattern = parser.get_parser(ast.PathPattern)(parser)
    return CypherPatternPredicate(pattern=path_pattern)


# Temporal keywords that are now non-reserved in Cypher.  These appear in the
# base parser's DATETIME/DURATION fast-path token sets, so we must guard
# against the fast-path firing when they are used as bare identifiers.
_CYPHER_TEMPORAL_IDENTIFIER_TOKENS: set[TokenType] = {
    TokenType.DATE,
    TokenType.TIME,
    TokenType.DATETIME,
    TokenType.DURATION,
    TokenType.TIMESTAMP,
}

# When a temporal keyword is followed by one of these, it is genuinely the
# start of a temporal expression (function call, method call, or literal).
_TEMPORAL_FUNCTION_NEXT: set[TokenType] = {
    TokenType.LEFT_PAREN,
    TokenType.PERIOD,
    TokenType.STRING,
}


def _to_nve(expr: ast.CommonValueExpression) -> ast.NumericValueExpression:
    """Convert a CommonValueExpression to NumericValueExpression.

    Used to wrap operands of Cypher's ``%`` and ``^`` operators so they fit
    into :class:`ModulusExpression` / :class:`PowerFunction` fields.

    Unwraps simple AVE trees (single factor, no steps) to extract the inner
    VEP/NumericValueFunction directly.  Complex expressions are wrapped via
    :class:`ParenthesizedValueExpression`.
    """
    if isinstance(expr, ast.NumericValueExpression):
        return expr

    if isinstance(expr, ast.ValueExpressionPrimary | ast.NumericValueFunction):
        return ast.NumericValueExpression(
            base=ast.Term(base=ast.Factor(numeric_primary=expr)),
        )

    # AVE(base=AT(...), steps=None) → convert AT→Term structure if possible
    if isinstance(expr, ast.ArithmeticValueExpression) and expr.steps is None:
        at = expr.base
        if isinstance(at, ast.ArithmeticTerm):
            _np = ast.ValueExpressionPrimary | ast.NumericValueFunction
            af = at.base
            if isinstance(af, ast.ArithmeticFactor) and isinstance(af.arithmetic_primary, _np):
                base_factor = ast.Factor(sign=af.sign, numeric_primary=af.arithmetic_primary)
                if at.steps is None:
                    return ast.NumericValueExpression(base=ast.Term(base=base_factor))
                # Convert multiplicative steps: AT._MF(op, AF) → Term._MF(op, Factor)
                mf_steps: list[ast.Term._MultiplicativeFactor] = []
                for mf in at.steps:
                    if isinstance(mf.factor, ast.ArithmeticFactor) and isinstance(
                        mf.factor.arithmetic_primary, _np
                    ):
                        mf_steps.append(
                            ast.Term._MultiplicativeFactor(
                                operator=mf.operator,
                                factor=ast.Factor(
                                    sign=mf.factor.sign,
                                    numeric_primary=mf.factor.arithmetic_primary,
                                ),
                            )
                        )
                    else:
                        break  # Can't convert this step — fall through to PVE
                else:
                    # All steps converted successfully
                    return ast.NumericValueExpression(
                        base=ast.Term(base=base_factor, steps=mf_steps or None),
                    )

    # General case: wrap in parentheses
    pve = ast.ParenthesizedValueExpression(value_expression=expr)
    return ast.NumericValueExpression(
        base=ast.Term(base=ast.Factor(numeric_primary=pve)),
    )


# Arithmetic operator token sets for the Cypher postfix handler.
# Precedence: ^ (power) > %, *, / (term) > +, - (additive).
_POWER_OPS: set[TokenType] = {TokenType.CARET}
_TERM_LEVEL_OPS: set[TokenType] = {TokenType.PERCENT, TokenType.ASTERISK, TokenType.SOLIDUS}
_ADD_LEVEL_OPS: set[TokenType] = {TokenType.PLUS_SIGN, TokenType.MINUS_SIGN}


def _to_arithmetic_primary(
    expr: ast.CommonValueExpression,
) -> ast.ArithmeticPrimary:
    """Extract ArithmeticPrimary from a CVE without unnecessary PVE wrapping.

    Unwraps simple expression trees (single unsigned factor, no steps) to find
    the inner VEP/NumericValueFunction.  Falls back to PVE wrapping for
    complex expressions.
    """
    if isinstance(expr, ast.ValueExpressionPrimary | ast.NumericValueFunction):
        return expr

    # AVE(base=AT(base=AF(+, primary), steps=None), steps=None) → extract primary
    if isinstance(expr, ast.ArithmeticValueExpression) and expr.steps is None:
        at = expr.base
        if isinstance(at, ast.ArithmeticTerm) and at.steps is None:
            af = at.base
            if isinstance(af, ast.ArithmeticFactor) and af.sign == ast.Sign.PLUS_SIGN:
                return af.arithmetic_primary

    # NVE(base=Term(base=Factor(+, primary), steps=None), steps=None) → extract primary
    if isinstance(expr, ast.NumericValueExpression) and expr.steps is None:
        term = expr.base
        if isinstance(term, ast.Term) and term.steps is None:
            factor = term.base
            if isinstance(factor, ast.Factor) and factor.sign == ast.Sign.PLUS_SIGN:
                return factor.numeric_primary

    return ast.ParenthesizedValueExpression(value_expression=expr)


_Rebuilder = t.Callable[[ast.NumericValueExpression], ast.ArithmeticValueExpression]


def _split_rightmost_factor(
    lhs: ast.CommonValueExpression,
) -> tuple[ast.CommonValueExpression, _Rebuilder | None]:
    """Extract the rightmost leaf factor from an AVE for ``^`` precedence.

    The GQL base parser may have already consumed ``*``/``/``/``+``/``-`` into
    an ArithmeticValueExpression.  Since ``^`` binds tighter, we need to
    "steal" the rightmost factor from that tree.

    Returns ``(leaf, rebuild)`` where *leaf* is the rightmost factor wrapped as
    an AVE and *rebuild* is a callable that puts the power result back into the
    original structure.  ``rebuild`` is ``None`` when the entire expression *is*
    the leaf.
    """
    if not isinstance(lhs, ast.ArithmeticValueExpression):
        return lhs, None

    ave = lhs

    # Locate the rightmost ArithmeticTerm
    if ave.steps:
        last_signed = ave.steps[-1]
        at = last_signed.term
    else:
        at = ave.base

    if not isinstance(at, ast.ArithmeticTerm):
        return lhs, None

    if at.steps:
        # Rightmost factor is in the last multiplicative step
        last_mf = at.steps[-1]
        leaf = ast.ArithmeticValueExpression(
            base=ast.ArithmeticTerm(base=last_mf.factor),
        )
        # Capture narrowed values for closure (avoids mypy Optional indexing)
        prior_mf_steps = at.steps[:-1]
        at_base = at.base
        prior_ave_steps = ave.steps[:-1] if ave.steps else None

        def _rebuild_mf(power_nve: ast.NumericValueExpression) -> ast.ArithmeticValueExpression:
            power_ap = _to_arithmetic_primary(power_nve)
            new_mf = ast.ArithmeticTerm._MultiplicativeFactor(
                operator=last_mf.operator,
                factor=ast.ArithmeticFactor(arithmetic_primary=power_ap),
            )
            new_at = ast.ArithmeticTerm(base=at_base, steps=[*prior_mf_steps, new_mf])
            if prior_ave_steps is not None:
                new_signed = ast.ArithmeticValueExpression._SignedTerm(
                    sign=last_signed.sign,
                    term=new_at,
                )
                return ast.ArithmeticValueExpression(
                    base=ave.base,
                    steps=[*prior_ave_steps, new_signed],
                )
            return ast.ArithmeticValueExpression(base=new_at)

        return leaf, _rebuild_mf

    if ave.steps:
        # No multiplicative steps — the base factor of the last signed term
        leaf = ast.ArithmeticValueExpression(
            base=ast.ArithmeticTerm(base=at.base),
        )

        # Capture narrowed value for closure
        prior_add_steps = ave.steps[:-1]

        def _rebuild_add(power_nve: ast.NumericValueExpression) -> ast.ArithmeticValueExpression:
            power_ap = _to_arithmetic_primary(power_nve)
            power_at = ast.ArithmeticTerm(
                base=ast.ArithmeticFactor(arithmetic_primary=power_ap),
            )
            new_signed = ast.ArithmeticValueExpression._SignedTerm(
                sign=last_signed.sign,
                term=power_at,
            )
            return ast.ArithmeticValueExpression(
                base=ave.base,
                steps=[*prior_add_steps, new_signed],
            )

        return leaf, _rebuild_add

    # Simple AVE (single factor, no steps) — entire expression is the leaf
    return lhs, None


def _absorb_power_ops(
    parser: BaseParser,
    lhs: ast.CommonValueExpression,
) -> ast.CommonValueExpression:
    """Consume any trailing ``^`` operators (highest arithmetic precedence).

    When the GQL parser has already consumed ``*``/``/``/``+``/``-`` into the
    *lhs*, this function extracts the rightmost factor so that ``^`` binds
    tighter (e.g. ``2 * 3 ^ 4`` → ``2 * (3 ^ 4)``).
    """
    if not parser._match(_POWER_OPS):
        return lhs

    leaf, rebuild = _split_rightmost_factor(lhs)
    nve = _to_nve(leaf)
    while parser._match(_POWER_OPS):
        parser._advance()  # consume ^
        rhs_vep = parser.get_parser(ast.ValueExpressionPrimary)(parser)
        rhs_nve = ast.NumericValueExpression(
            base=ast.Term(base=ast.Factor(numeric_primary=rhs_vep)),
        )
        power = ast.PowerFunction(
            numeric_value_expression_base=nve,
            numeric_value_expression_exponent=rhs_nve,
        )
        nve = ast.NumericValueExpression(
            base=ast.Term(base=ast.Factor(numeric_primary=power)),
        )

    if rebuild is None:
        return nve
    return rebuild(nve)


def _extract_at(result: ast.CommonValueExpression) -> ast.ArithmeticTerm:
    """Extract an ArithmeticTerm from a CVE, wrapping in PVE if needed."""
    if (
        isinstance(result, ast.ArithmeticValueExpression)
        and result.steps is None
        and isinstance(result.base, ast.ArithmeticTerm)
    ):
        return result.base
    ap = _to_arithmetic_primary(result)
    return ast.ArithmeticTerm(base=ast.ArithmeticFactor(arithmetic_primary=ap))


def _absorb_term_ops(
    parser: BaseParser,
    lhs: ast.CommonValueExpression,
) -> ast.CommonValueExpression:
    """Consume ``^``, ``%``, ``*``, ``/`` operators (used as RHS of additive ops)."""
    result = _absorb_power_ops(parser, lhs)

    if not parser._match(_TERM_LEVEL_OPS):
        return result

    # If _absorb_power_ops rebuilt an additive AVE (e.g. from ``1 + 2 ^ 3``),
    # term-level ops (``* 4``) should only apply to the rightmost additive
    # term — not to the entire expression.  Extract and work on that term alone.
    ave_prefix: ast.ArithmeticValueExpression | None = None
    add_sign: ast.Sign | None = None
    if isinstance(result, ast.ArithmeticValueExpression) and result.steps is not None:
        last_signed = result.steps[-1]
        ave_prefix = ast.ArithmeticValueExpression(
            base=result.base,
            steps=result.steps[:-1] if len(result.steps) > 1 else None,
        )
        add_sign = last_signed.sign
        result = ast.ArithmeticValueExpression(base=last_signed.term)

    while parser._match(_TERM_LEVEL_OPS):
        tok = parser._curr
        parser._advance()
        rhs_vep = parser.get_parser(ast.ValueExpressionPrimary)(parser)
        rhs = _absorb_power_ops(parser, rhs_vep)

        if tok.token_type == TokenType.PERCENT:
            nve_result = _to_nve(result)
            rhs_nve = rhs if isinstance(rhs, ast.NumericValueExpression) else _to_nve(rhs)
            mod = ast.ModulusExpression(
                numeric_value_expression_dividend=nve_result,
                numeric_value_expression_divisor=rhs_nve,
            )
            result = ast.NumericValueExpression(
                base=ast.Term(base=ast.Factor(numeric_primary=mod)),
            )
        else:
            # * or / — use ArithmeticTerm (matches GQL parser output)
            lhs_ap = _to_arithmetic_primary(result)
            rhs_ap = _to_arithmetic_primary(rhs)
            operator = (
                ast.MultiplicativeOperator.MULTIPLY
                if tok.token_type == TokenType.ASTERISK
                else ast.MultiplicativeOperator.DIVIDE
            )
            result = ast.ArithmeticValueExpression(
                base=ast.ArithmeticTerm(
                    base=ast.ArithmeticFactor(arithmetic_primary=lhs_ap),
                    steps=[
                        ast.ArithmeticTerm._MultiplicativeFactor(
                            operator=operator,
                            factor=ast.ArithmeticFactor(arithmetic_primary=rhs_ap),
                        )
                    ],
                ),
            )

    if ave_prefix is not None:
        new_at = _extract_at(result)
        new_signed = ast.ArithmeticValueExpression._SignedTerm(
            sign=add_sign or ast.Sign.PLUS_SIGN,
            term=new_at,
        )
        return ast.ArithmeticValueExpression(
            base=ave_prefix.base,
            steps=[*(ave_prefix.steps or []), new_signed],
        )

    return result


def _parse_cypher_arithmetic_postfix(
    parser: BaseParser,
    lhs_cve: ast.CommonValueExpression,
) -> ast.CommonValueExpression:
    """Handle arithmetic operators after a CVE that bypassed AmbiguousValueExpression.

    Called when ``^``, ``%``, ``*``, ``/``, ``+``, or ``-`` follows a CVE result
    from a fast-path (list literal, Cypher function, or a prior postfix result).

    Operator precedence: ``^`` > ``%``/``*``/``/`` > ``+``/``-``.
    Uses ArithmeticValueExpression/ArithmeticTerm/ArithmeticFactor (the same
    types the GQL parser produces) for ``*``, ``/``, ``+``, ``-`` so that
    round-trip parse→generate→re-parse produces identical ASTs.
    NVE/Term/Factor is only used for ``%``/``^`` where ModulusExpression/
    PowerFunction require NumericValueExpression fields.
    """
    # Phase 0 + Phase 1: ^, %, *, /
    result = _absorb_term_ops(parser, lhs_cve)

    # Phase 2: Additive ops (+, -) — lower precedence
    if not parser._match(_ADD_LEVEL_OPS):
        return result

    # Decompose the result into base AT + existing additive steps.
    # _absorb_term_ops may have returned an AVE that already has additive steps
    # (e.g. ``1 + 2 ^ 3 * 4``), in which case we extend rather than re-wrap.
    if isinstance(result, ast.ArithmeticValueExpression):
        lhs_at = result.base if isinstance(result.base, ast.ArithmeticTerm) else _extract_at(result)
        steps: list[ast.ArithmeticValueExpression._SignedTerm] = list(result.steps or [])
    else:
        lhs_at = _extract_at(result)
        steps = []

    while parser._match(_ADD_LEVEL_OPS):
        tok = parser._curr
        parser._advance()
        sign = ast.Sign.PLUS_SIGN if tok.token_type == TokenType.PLUS_SIGN else ast.Sign.MINUS_SIGN
        rhs_cve = BaseParser.PARSERS[ast.CommonValueExpression](parser)
        rhs_cve = _absorb_term_ops(parser, rhs_cve)
        rhs_at = _extract_at(rhs_cve)
        steps.append(ast.ArithmeticValueExpression._SignedTerm(sign=sign, term=rhs_at))
    return ast.ArithmeticValueExpression(base=lhs_at, steps=steps)


_COMPARISON_OPS: set[TokenType] = {
    TokenType.EQUALS_OPERATOR,
    TokenType.NOT_EQUALS_OPERATOR,
    TokenType.LEFT_ANGLE_BRACKET,
    TokenType.RIGHT_ANGLE_BRACKET,
    TokenType.LESS_THAN_OR_EQUALS_OPERATOR,
    TokenType.GREATER_THAN_OR_EQUALS_OPERATOR,
}

_TOKEN_TO_COMP_OP: dict[TokenType, ast.ComparisonPredicatePart2.CompOp] = {
    TokenType.EQUALS_OPERATOR: ast.ComparisonPredicatePart2.CompOp.EQUALS,
    TokenType.NOT_EQUALS_OPERATOR: ast.ComparisonPredicatePart2.CompOp.NOT_EQUALS,
    TokenType.LEFT_ANGLE_BRACKET: ast.ComparisonPredicatePart2.CompOp.LESS_THAN,
    TokenType.RIGHT_ANGLE_BRACKET: ast.ComparisonPredicatePart2.CompOp.GREATER_THAN,
    TokenType.LESS_THAN_OR_EQUALS_OPERATOR: (
        ast.ComparisonPredicatePart2.CompOp.LESS_THAN_OR_EQUALS
    ),
    TokenType.GREATER_THAN_OR_EQUALS_OPERATOR: (
        ast.ComparisonPredicatePart2.CompOp.GREATER_THAN_OR_EQUALS
    ),
}


_parse_func_args = parse_func_args


def _parse_cypher_reduce(parser: BaseParser) -> CypherReduce:
    """Parse ``reduce(acc = init, var IN list | expr)``."""
    parser._expect(TokenType.REDUCE)
    parser._expect(TokenType.LEFT_PAREN)
    acc = parser.get_parser(ast.Identifier)(parser)
    parser._expect(TokenType.EQUALS_OPERATOR)
    initial = parser.get_parser(ast.ValueExpression)(parser)
    parser._expect(TokenType.COMMA)
    var = parser.get_parser(ast.Identifier)(parser)
    parser._expect(TokenType.IN)
    list_expr = parser.get_parser(ast.ValueExpression)(parser)
    parser._expect(TokenType.VERTICAL_BAR)
    expression = parser.get_parser(ast.ValueExpression)(parser)
    parser._expect(TokenType.RIGHT_PAREN)
    return CypherReduce(
        accumulator=acc,
        initial=initial,
        variable=var,
        list_expr=list_expr,
        expression=expression,
    )


def _parse_cypher_core_cve(parser: BaseParser) -> ast.CommonValueExpression:
    """Parse the core CVE: base expression + arithmetic + subscript/slice postfix."""
    if parser._match({TokenType.NONE_KW, TokenType.SINGLE}) and parser._match_next(
        TokenType.LEFT_PAREN
    ):
        parser.raise_error("Expected common value expression")
        raise  # unreachable
    result: ast.CommonValueExpression
    if parser._match(_TOKEN_FUNCTION_TOKENS) and parser._match_next(TokenType.LEFT_PAREN):
        # Keyword-token functions: LABELS, KEYS, NODES, etc. — dispatch via dict
        func_cls = _TOKEN_FUNCTIONS[parser._curr.token_type]
        parser._advance()  # consume keyword token
        result = _parse_func_args(parser, func_cls)
    elif parser._match(_TYPE_CONV_TOKENS) and parser._match_next(TokenType.LEFT_PAREN):
        result = _parse_cypher_type_conversion(parser)
    elif parser._match(TokenType.PATH_LENGTH) and parser._match_next(TokenType.LEFT_PAREN):
        # Guard: PATH_LENGTH is in NON_RESERVED_WORDS (property access: n.length)
        # but length(x) must route to PathLengthExpression, not Identifier.
        # Route directly to avoid NRW identifier match inside NVE.
        ple = parser.get_parser(ast.PathLengthExpression)(parser)
        result = ast.NumericValueExpression(
            base=ast.Term(base=ast.Factor(numeric_primary=ple)),
        )
    elif parser._match(TokenType.REPLACE) and parser._match_next(TokenType.LEFT_PAREN):
        # Cypher replace(str, search, repl) — keyword token
        parser._advance()  # consume REPLACE
        result = _parse_func_args(parser, f.Replace)
    elif parser._match(TokenType.REDUCE) and parser._match_next(TokenType.LEFT_PAREN):
        # Cypher reduce(acc = init, var IN list | expr) — special syntax
        result = _parse_cypher_reduce(parser)
    elif parser._match(TokenType.TIMESTAMP) and parser._match_next(TokenType.LEFT_PAREN):
        # Neo4j timestamp() — 0-arg epoch millis function
        parser._advance()  # consume TIMESTAMP
        result = _parse_func_args(parser, f.TimestampFunc)
    elif parser._match(_CYPHER_TEMPORAL_IDENTIFIER_TOKENS) and not parser._match_next(
        _TEMPORAL_FUNCTION_NEXT
    ):
        result = parser.get_parser(ast.AmbiguousValueExpression)(parser)
    else:
        result = BaseParser.PARSERS[ast.CommonValueExpression](parser)

    # Postfix operators (chainable): arithmetic, subscript, slice
    while True:
        if parser._match(_POWER_OPS | _TERM_LEVEL_OPS | _ADD_LEVEL_OPS):
            result = _parse_cypher_arithmetic_postfix(parser, result)
        elif parser._match(TokenType.LEFT_BRACKET):
            parser._expect(TokenType.LEFT_BRACKET)
            if parser._match(TokenType.DOUBLE_PERIOD):
                # [..end]
                parser._expect(TokenType.DOUBLE_PERIOD)
                end = parser.get_parser(ast.ValueExpression)(parser)
                parser._expect(TokenType.RIGHT_BRACKET)
                result = CypherSliceExpression(base=result, end=end)
            else:
                start_or_index = parser.get_parser(ast.ValueExpression)(parser)
                if parser._match(TokenType.DOUBLE_PERIOD):
                    # [start..end] or [start..]
                    parser._expect(TokenType.DOUBLE_PERIOD)
                    end = None
                    if not parser._match(TokenType.RIGHT_BRACKET):
                        end = parser.get_parser(ast.ValueExpression)(parser)
                    parser._expect(TokenType.RIGHT_BRACKET)
                    result = CypherSliceExpression(base=result, start=start_or_index, end=end)
                else:
                    # [index] — existing subscript
                    parser._expect(TokenType.RIGHT_BRACKET)
                    result = CypherSubscriptExpression(base=result, index=start_or_index)
        elif parser._match(TokenType.PERIOD):
            # Property access on expression result: (expr).prop, expr[idx].prop, fn().prop
            parser._expect(TokenType.PERIOD)
            prop_ident = parser.get_parser(ast.Identifier)(parser)
            prop_ref = ast.PropertyReference._construct(
                property_source=result,
                property_name=[ast.PropertyName(identifier=prop_ident)],
            )
            # Wrap in arithmetic chain: PropertyReference → VEP → Factor → Term → NVE
            result = ast.NumericValueExpression(
                base=ast.Term(base=ast.Factor(numeric_primary=prop_ref)),
            )
        else:
            break

    return result


def _parse_cypher_common_value_expression(parser: BaseParser) -> ast.CommonValueExpression:
    """Extended CommonValueExpression with Cypher extensions.

    Comparison and boolean operators are handled by BooleanValueExpression
    (via BooleanTest → Predicate → ComparisonPredicate) at a higher level.
    This function handles: routing, arithmetic, subscript/slice.
    """
    return _parse_cypher_core_cve(parser)


# Tokens that indicate a boolean/comparison operator follows a CVE.
# When ValueExpression sees these after a successful CVE parse, it must
# re-parse as BVE so the standard predicate/boolean chain handles them.
_CVE_UPGRADE_TOKENS: set[TokenType] = _COMPARISON_OPS | {
    TokenType.AND,
    TokenType.OR,
    TokenType.XOR,
    TokenType.IS,
    # Cypher infix predicates — IN, STARTS WITH, ENDS WITH, CONTAINS
    TokenType.IN,
    TokenType.STARTS,
    TokenType.ENDS,
    TokenType.CONTAINS,
    # Cypher label test: var:Label triggers LabeledPredicate via BVE path
    TokenType.COLON,
}


def _parse_cypher_value_expression(parser: BaseParser) -> ast.ValueExpression:
    """Cypher ValueExpression: CVE first, upgrade to BVE if comparison/boolean follows.

    GQL's ``ValueExpression = CVE | BVE`` tries CVE first.  For ``RETURN 1 = 1``
    this consumes ``1`` as CVE and leaves ``= 1`` unparsed.  In Cypher, comparison
    and boolean operators can appear anywhere a value expression is expected.

    Strategy: save position, attempt CVE; if it succeeds AND the next token is a
    comparison/boolean operator, retreat and re-parse as BVE.
    """
    saved = parser._index
    cve = parser.try_parse(parser.get_parser(ast.CommonValueExpression))
    if cve is not None:
        if not parser._match(_CVE_UPGRADE_TOKENS):
            return t.cast(ast.ValueExpression, cve)
        # Comparison/boolean follows — retreat and re-parse as BVE
        parser._retreat(saved)
    return parser.get_parser(ast.BooleanValueExpression)(parser)


def _parse_cypher_date_function(
    parser: BaseParser,
) -> ast.DateFunction | ast.CommonValueExpression:
    """Parse Cypher ``date(...)`` — consumes DATE keyword + parens.

    Also handles ``CURRENT_DATE`` (gated by GG:TF01).
    Falls back to ``CAST(expr AS DATE)`` for expression arguments like ``date(null)``.
    """
    if parser._match(TokenType.CURRENT_DATE):
        parser._expect(TokenType.CURRENT_DATE)
        result = ast.DateFunction(date_function=ast.DateFunction._CurrentDate())
        result.require_feature(F.GG_TF01)
        return result
    parser._expect(TokenType.DATE)
    parser._expect(TokenType.LEFT_PAREN)
    saved = parser._index
    params = t.cast(
        ast.DateFunctionParameters | None,
        parser.try_parse(parser.get_parser(ast.DateFunctionParameters)),
    )
    if params is not None or parser._match(TokenType.RIGHT_PAREN):
        parser._expect(TokenType.RIGHT_PAREN)
        return ast.DateFunction(
            date_function=ast.DateFunction._DateLeftParenDateFunctionParametersRightParen(
                date_function_parameters=params,
            ),
        )
    # Expression fallback: date(null), date(var) → CAST(expr AS DATE)
    parser._retreat(saved)
    arg = parser.get_parser(ast.ValueExpression)(parser)
    parser._expect(TokenType.RIGHT_PAREN)
    return _cast_as_cve(arg, _TEMPORAL_CAST_TARGETS[TemporalBaseType.DATE](not_null=False))


def _parse_cypher_time_function(
    parser: BaseParser,
) -> ast.TimeFunction | ast.CommonValueExpression:
    """Parse Cypher ``time(...)`` — consumes TIME keyword + parens.

    The base GQL parser expects LEFT_PAREN directly (no TIME token), which
    breaks ``time('10:30:00')`` in Cypher.
    Falls back to ``CAST(expr AS ZONED TIME)`` for expression arguments.
    """
    if parser._match(TokenType.CURRENT_TIME):
        parser._expect(TokenType.CURRENT_TIME)
        return ast.TimeFunction(time_function=ast.TimeFunction._CurrentTime())
    parser._expect(TokenType.TIME)
    parser._expect(TokenType.LEFT_PAREN)
    saved = parser._index
    params = t.cast(
        ast.TimeFunctionParameters | None,
        parser.try_parse(parser.get_parser(ast.TimeFunctionParameters)),
    )
    if params is not None or parser._match(TokenType.RIGHT_PAREN):
        parser._expect(TokenType.RIGHT_PAREN)
        return ast.TimeFunction(
            time_function=ast.TimeFunction._ZonedTimeLeftParenTimeFunctionParametersRightParen(
                time_function_parameters=params,
            ),
        )
    parser._retreat(saved)
    arg = parser.get_parser(ast.ValueExpression)(parser)
    parser._expect(TokenType.RIGHT_PAREN)
    return _cast_as_cve(arg, _TEMPORAL_CAST_TARGETS[TemporalBaseType.TIME](not_null=False))


def _parse_cypher_datetime_function(
    parser: BaseParser,
) -> ast.DatetimeFunction | ast.CommonValueExpression:
    """Parse Cypher ``datetime(...)`` — consumes DATETIME keyword + parens.

    The base GQL parser expects LEFT_PAREN directly (no DATETIME token), which
    breaks ``datetime('2024-01-15T10:30:00')`` in Cypher.
    Falls back to ``CAST(expr AS ZONED DATETIME)`` for expression arguments.
    """
    if parser._match(TokenType.CURRENT_TIMESTAMP):
        parser._expect(TokenType.CURRENT_TIMESTAMP)
        result = ast.DatetimeFunction(datetime_function=ast.DatetimeFunction._CurrentTimestamp())
        result.require_feature(F.GG_TF01)
        return result
    parser._expect(TokenType.DATETIME)
    parser._expect(TokenType.LEFT_PAREN)
    saved = parser._index
    params = t.cast(
        ast.DatetimeFunctionParameters | None,
        parser.try_parse(parser.get_parser(ast.DatetimeFunctionParameters)),
    )
    if params is not None or parser._match(TokenType.RIGHT_PAREN):
        parser._expect(TokenType.RIGHT_PAREN)
        return ast.DatetimeFunction(
            datetime_function=ast.DatetimeFunction._ZonedDatetimeLeftParenDatetimeFunctionParametersRightParen(
                datetime_function_parameters=params,
            ),
        )
    parser._retreat(saved)
    arg = parser.get_parser(ast.ValueExpression)(parser)
    parser._expect(TokenType.RIGHT_PAREN)
    return _cast_as_cve(arg, _TEMPORAL_CAST_TARGETS[TemporalBaseType.DATETIME](not_null=False))


def _parse_cypher_localdatetime_function(
    parser: BaseParser,
) -> ast.LocaldatetimeFunction | ast.CommonValueExpression:
    """Parse Cypher ``localdatetime(...)`` or ``LOCAL_DATETIME(...)`` or ``LOCAL_TIMESTAMP``.

    Handles single-word ``localdatetime`` (Cypher) and multi-word ``LOCAL_DATETIME`` (GQL).
    Falls back to ``CAST(expr AS LOCAL DATETIME)`` for expression arguments.
    """
    if parser._match(TokenType.LOCAL_TIMESTAMP):
        parser._expect(TokenType.LOCAL_TIMESTAMP)
        return ast.LocaldatetimeFunction(
            localdatetime_function=ast.LocaldatetimeFunction._LocalTimestamp()
        )
    # LOCAL_DATETIME covers both "LOCAL_DATETIME" and "localdatetime" (Cypher lexer maps both)
    parser._expect(TokenType.LOCAL_DATETIME)
    parser._expect(TokenType.LEFT_PAREN)
    saved = parser._index
    params = t.cast(
        ast.DatetimeFunctionParameters | None,
        parser.try_parse(parser.get_parser(ast.DatetimeFunctionParameters)),
    )
    if params is not None or parser._match(TokenType.RIGHT_PAREN):
        parser._expect(TokenType.RIGHT_PAREN)
        return ast.LocaldatetimeFunction(
            localdatetime_function=ast.LocaldatetimeFunction._LocalDatetimeLeftParenDatetimeFunctionParametersRightParen(
                datetime_function_parameters=params,
            ),
        )
    parser._retreat(saved)
    arg = parser.get_parser(ast.ValueExpression)(parser)
    parser._expect(TokenType.RIGHT_PAREN)
    return _cast_as_cve(arg, _TEMPORAL_CAST_TARGETS[TemporalBaseType.LOCALDATETIME](not_null=False))


def _parse_cypher_localtime_function(
    parser: BaseParser,
) -> ast.LocaltimeFunction | ast.CommonValueExpression:
    """Parse Cypher ``localtime(...)`` or ``LOCAL_TIME(...)``.

    Handles single-word ``localtime`` (Cypher) and multi-word ``LOCAL_TIME`` (GQL).
    Falls back to ``CAST(expr AS LOCAL TIME)`` for expression arguments.
    """
    # LOCAL_TIME covers both "LOCAL_TIME" and "localtime" (Cypher lexer maps both)
    parser._expect(TokenType.LOCAL_TIME)
    parser._expect(TokenType.LEFT_PAREN)
    saved = parser._index
    params = t.cast(
        ast.TimeFunctionParameters | None,
        parser.try_parse(parser.get_parser(ast.TimeFunctionParameters)),
    )
    if params is not None or parser._match(TokenType.RIGHT_PAREN):
        parser._expect(TokenType.RIGHT_PAREN)
        return ast.LocaltimeFunction(time_function_parameters=params)
    parser._retreat(saved)
    arg = parser.get_parser(ast.ValueExpression)(parser)
    parser._expect(TokenType.RIGHT_PAREN)
    return _cast_as_cve(arg, _TEMPORAL_CAST_TARGETS[TemporalBaseType.LOCALTIME](not_null=False))


def _parse_cypher_duration_function(
    parser: BaseParser,
) -> ast.DurationFunction | CypherTemporalCast:
    """Parse Cypher ``duration(...)`` — consumes leading DURATION keyword.

    The base GQL parser doesn't consume the DURATION keyword; this override does.
    Falls back to CypherTemporalCast for expression arguments like ``duration(null)``.
    """
    parser._expect(TokenType.DURATION)
    parser._expect(TokenType.LEFT_PAREN)
    if parser._match(TokenType.RIGHT_PAREN):
        parser._expect(TokenType.RIGHT_PAREN)
        return ast.DurationFunction(duration_function_parameters=None)
    saved = parser._index
    params = t.cast(
        ast.DurationFunctionParameters | None,
        parser.try_parse(parser.get_parser(ast.DurationFunctionParameters)),
    )
    if params is not None:
        parser._expect(TokenType.RIGHT_PAREN)
        return ast.DurationFunction(duration_function_parameters=params)
    # Expression fallback: duration(null), duration(var), duration(toString(x))
    parser._retreat(saved)
    arg = parser.get_parser(ast.ValueExpression)(parser)
    parser._expect(TokenType.RIGHT_PAREN)
    return CypherTemporalCast(function_name=TemporalBaseType.DURATION, argument=arg)


# Mapping from Cypher lowercase temporal names to method enums
_TEMPORAL_BASE_TYPES: dict[TokenType, TemporalBaseType] = {
    TokenType.DATE: TemporalBaseType.DATE,
    TokenType.TIME: TemporalBaseType.TIME,
    TokenType.DATETIME: TemporalBaseType.DATETIME,
    TokenType.LOCAL_DATETIME: TemporalBaseType.LOCALDATETIME,
    TokenType.LOCAL_TIME: TemporalBaseType.LOCALTIME,
    TokenType.DURATION: TemporalBaseType.DURATION,
}

_TEMPORAL_METHODS: dict[str, CypherTemporalMethod.Method] = {
    "truncate": CypherTemporalMethod.Method.TRUNCATE,
    "between": CypherTemporalMethod.Method.BETWEEN,
    "transaction": CypherTemporalMethod.Method.TRANSACTION,
    "statement": CypherTemporalMethod.Method.STATEMENT,
    "realtime": CypherTemporalMethod.Method.REALTIME,
    "inmonths": CypherTemporalMethod.Method.INMONTHS,
    "indays": CypherTemporalMethod.Method.INDAYS,
    "inseconds": CypherTemporalMethod.Method.INSECONDS,
    "fromepoch": CypherTemporalMethod.Method.FROMEPOCH,
    "fromepochmillis": CypherTemporalMethod.Method.FROMEPOCHMILLIS,
}


def _parse_cypher_temporal_method(
    parser: BaseParser,
) -> CypherTemporalMethod | ast.DatetimeSubtraction:
    """Parse ``base.method(args)`` — e.g., ``date.truncate('year', d)``.

    ``duration.between(d1, d2)`` is parsed directly into
    :class:`DatetimeSubtraction` (GQL ``DURATION_BETWEEN``).
    """
    # Current token is a temporal keyword; consume it
    base_type: TemporalBaseType | None = None
    for tok_type, bt in _TEMPORAL_BASE_TYPES.items():
        if parser._match(tok_type):
            parser._expect(tok_type)
            base_type = bt
            break
    if base_type is None:
        parser.raise_error("Expected temporal type keyword")
        raise  # unreachable

    parser._expect(TokenType.PERIOD)
    method_id = parser.get_parser(ast.Identifier)(parser)
    method_name = method_id.name.lower()
    if method_name not in _TEMPORAL_METHODS:
        parser.raise_error(f"Unknown temporal method: {method_name}")
        raise  # unreachable
    method = _TEMPORAL_METHODS[method_name]

    parser._expect(TokenType.LEFT_PAREN)
    arguments: list[ast.ValueExpression] = []
    if not parser._match(TokenType.RIGHT_PAREN):
        arg = parser.get_parser(ast.ValueExpression)(parser)
        arguments.append(arg)
        while parser._match(TokenType.COMMA):
            parser._expect(TokenType.COMMA)
            arg = parser.get_parser(ast.ValueExpression)(parser)
            arguments.append(arg)
    parser._expect(TokenType.RIGHT_PAREN)

    # duration.between(d1, d2) → DURATION_BETWEEN(d1, d2)
    if method == CypherTemporalMethod.Method.BETWEEN:
        if len(arguments) != 2:
            parser.raise_error(
                f"duration.between() requires exactly 2 arguments, got {len(arguments)}"
            )
        params = ast.DatetimeSubtractionParameters(
            datetime_value_expression_1=arguments[0],
            datetime_value_expression_2=arguments[1],
        )
        return ast.DatetimeSubtraction(
            datetime_subtraction_parameters=params,
            temporal_duration_qualifier=None,
        )

    return CypherTemporalMethod(base_type=base_type, method=method, arguments=arguments)


def _parse_cypher_datetime_primary(parser: BaseParser) -> ast.DatetimePrimary:
    """Try DatetimeValueFunction before VEP.

    Temporal keywords (DATE, TIME, etc.) are non-reserved in Cypher, so
    ``parse_identifier`` now accepts them.  The base GQL grammar tries VEP
    *before* DatetimeValueFunction, which means ``date('...')`` would be
    greedily consumed as an identifier.  Swapping the order fixes this:
    DatetimeValueFunction is tried first and only falls through to VEP when
    it doesn't match.
    """
    candidates = (
        parser.get_parser(ast.DatetimeValueFunction),
        parser.get_parser(ast.ValueExpressionPrimary),
    )
    (result,) = parser.seq(candidates)
    return result


def _parse_cypher_duration_primary(parser: BaseParser) -> ast.DurationPrimary:
    """Try DurationValueFunction before VEP — same rationale as datetime."""
    candidates = (
        parser.get_parser(ast.DurationValueFunction),
        parser.get_parser(ast.ValueExpressionPrimary),
    )
    (result,) = parser.seq(candidates)
    return result


def _parse_cypher_duration_value_function(parser: BaseParser) -> ast.DurationValueFunction:
    """Override DurationValueFunction to handle Cypher ``duration.between(...)`` etc."""
    if parser._match(TokenType.DURATION):
        method_result = parser.try_parse(_parse_cypher_temporal_method)
        if method_result:
            return t.cast(ast.DurationValueFunction, method_result)
    candidates = (
        parser.get_parser(ast.DurationFunction),
        parser.get_parser(ast.DurationAbsoluteValueFunction),
    )
    (result,) = parser.seq(candidates)
    return result


def _parse_cypher_datetime_value_function(parser: BaseParser) -> ast.DatetimeValueFunction:
    """Override DatetimeValueFunction to handle Cypher temporal syntax.

    Checks for static method calls (``date.truncate(...)``), then falls through
    to the individual Cypher temporal function parsers.
    """
    # Check for static method pattern: temporal_keyword PERIOD identifier LEFT_PAREN
    if any(parser._match(tok) for tok in _TEMPORAL_BASE_TYPES):
        # Peek ahead: if next token after the keyword is PERIOD, it's a static method
        method_result = parser.try_parse(_parse_cypher_temporal_method)
        if method_result:
            return t.cast(ast.DatetimeValueFunction, method_result)

    # Fall through to individual function parsers
    candidates = (
        parser.get_parser(ast.DateFunction),
        parser.get_parser(ast.TimeFunction),
        parser.get_parser(ast.DatetimeFunction),
        parser.get_parser(ast.LocaltimeFunction),
        parser.get_parser(ast.LocaldatetimeFunction),
    )
    (result,) = parser.seq(candidates)
    return result


def _parse_cypher_label_set_specification(parser: BaseParser) -> ast.LabelSetSpecification:
    """Parse colon-separated labels: ``A:B:C`` (Cypher) or ``A&B&C`` (GQL).

    Used in INSERT/CREATE patterns via ``LabelAndPropertySetSpecification``.
    The leading ``:`` has already been consumed by the caller.
    """
    label = parser.get_parser(ast.LabelName)(parser)
    labels = [label]
    while parser._match({TokenType.COLON, TokenType.AMPERSAND}):
        parser._advance()
        labels.append(parser.get_parser(ast.LabelName)(parser))
    return ast.LabelSetSpecification(list_label_name=labels)


def _is_label_factor_after_pipe(parser: BaseParser) -> bool:
    """Check whether the token after ``|`` starts a label factor.

    Returns ``True`` when ``|`` is followed by a valid label-factor start:
    - ``VAR`` not followed by ``(`` (function call) or ``.`` (property ref)
    - ``!`` (negation), ``%`` (wildcard), ``(`` (parenthesized label expr)
    - ``:`` (legacy ``|:Label`` syntax)

    Returns ``False`` for anything else (keywords like COALESCE, function
    calls like ``coalesce(...)``, property references like ``x.name``).
    This disambiguates ``|`` as label disjunction vs. list-comprehension
    projection separator.
    """
    nxt = parser._peek_at(1)
    if nxt is None:
        return False
    tt = nxt.token_type
    if tt in {
        TokenType.EXCLAMATION_MARK,
        TokenType.PERCENT,
        TokenType.COLON,
    }:
        return True
    if tt == TokenType.LEFT_PAREN:
        # ``(`` starts a parenthesized label expression
        return True
    if tt == TokenType.VAR:
        # VAR + ( → function call, VAR + . → property ref → NOT label
        after_var = parser._peek_at(2)
        if after_var and after_var.token_type in {
            TokenType.LEFT_PAREN,
            TokenType.PERIOD,
        }:
            return False
        return True
    return False


def _parse_cypher_label_expression(parser: BaseParser) -> ast.LabelExpression:
    """Parse LabelExpression with lookahead to avoid consuming ``|`` greedily.

    The standard GQL parser uses ``list_(LabelTerm, VERTICAL_BAR)`` which
    greedily consumes every ``|`` as label disjunction.  In Cypher, ``|`` also
    serves as the list-comprehension projection separator, e.g.::

        [x IN nodes(p) WHERE x:Concept | coalesce(x.prefLabel, "")]

    This override checks :func:`_is_label_factor_after_pipe` before consuming
    each ``|`` to decide if it is a label disjunction or something else.
    """
    first_term = parser.get_parser(ast.LabelTerm)(parser)
    terms: list[ast.LabelTerm] = [first_term]
    while parser._match(TokenType.VERTICAL_BAR) and _is_label_factor_after_pipe(parser):
        parser._advance()  # consume |
        # Consume optional redundant colon: |:T (legacy Cypher syntax)
        if parser._match(TokenType.COLON):
            parser._advance()
        terms.append(parser.get_parser(ast.LabelTerm)(parser))
    return ast.LabelExpression(label_terms=terms)


def _parse_cypher_is_label_expression(parser: BaseParser) -> ast.IsLabelExpression:
    """Parse label expressions with colon, ampersand, and pipe separators.

    Supports Cypher ``:A:B`` (conjunction), GQL ``IS A&B`` (conjunction),
    ``IS A|B`` / ``:A|B`` (disjunction), negation ``!A``, wildcard ``%``,
    and parenthesized label expressions ``(A|B)``.

    - ``:`` and ``&`` create a conjunction within a single :class:`LabelTerm`
    - ``|`` creates a disjunction — starts a new :class:`LabelTerm`

    Uses :func:`_is_label_factor_after_pipe` to avoid consuming ``|`` that
    serves as a list-comprehension projection separator.
    """
    # Consume leading : or IS
    (_,) = parser.seq({TokenType.IS, TokenType.COLON})

    # Use LabelFactor parser to handle LabelName, !negation, %wildcard, (parens)
    factor = parser.get_parser(ast.LabelFactor)(parser)
    factors: list[ast.LabelFactor] = [factor]
    terms: list[ast.LabelTerm] = []

    while parser._match({TokenType.COLON, TokenType.AMPERSAND, TokenType.VERTICAL_BAR}):
        if parser._curr.token_type == TokenType.VERTICAL_BAR and not _is_label_factor_after_pipe(
            parser
        ):
            break
        tok = parser._curr
        parser._advance()
        if tok.token_type == TokenType.VERTICAL_BAR:
            # Disjunction — close current term, start new one
            terms.append(ast.LabelTerm(label_factors=factors))
            # Consume optional redundant colon: [:T|:T] (legacy Cypher syntax)
            if parser._match(TokenType.COLON):
                parser._advance()
            factors = [parser.get_parser(ast.LabelFactor)(parser)]
        else:
            # Conjunction (:  or &) — add to current term
            factors.append(parser.get_parser(ast.LabelFactor)(parser))

    terms.append(ast.LabelTerm(label_factors=factors))
    label_expr = ast.LabelExpression(label_terms=terms)
    return ast.IsLabelExpression(label_expression=label_expr)


def _parse_cypher_set_quantifier(parser: BaseParser) -> ast.SetQuantifier:
    """SetQuantifier override: ALL + LEFT_PAREN is a quantifier predicate, not RETURN ALL.

    In Cypher, ``RETURN all(x IN ...)`` uses ``all()`` as a list predicate
    function.  The base GQL parser would greedily match ``ALL`` as a
    ``SetQuantifier`` (for ``RETURN ALL ...``), leaving ``(x IN ...)``
    unparseable.  This override rejects ``ALL`` when followed by ``(`` so
    the predicate function gets a chance.
    """
    if parser._match(TokenType.ALL) and parser._match_next(TokenType.LEFT_PAREN):
        parser.raise_error("Expected DISTINCT or ALL (not followed by '(')")
        raise  # unreachable
    return BaseParser.PARSERS[ast.SetQuantifier](parser)


def _try_cypher_infix_predicate(
    parser: BaseParser,
) -> StringMatchPredicate | InPredicate | RegexMatchPredicate:
    """Parse CVE once, then dispatch to the correct Cypher infix predicate.

    Uses ``CommonValueExpression`` for LHS so arithmetic like ``[1]+2 IN [3]+4``
    parses the full ``[1]+2`` before checking for the infix keyword.
    """
    lhs = parser.get_parser(ast.CommonValueExpression)(parser)

    if parser._match(TokenType.STARTS):
        parser._expect(TokenType.STARTS)
        parser._expect(TokenType.WITH)
        rhs = parser.get_parser(ast.CommonValueExpression)(parser)
        return StringMatchPredicate(
            lhs=lhs, kind=StringMatchPredicate.MatchKind.STARTS_WITH, rhs=rhs
        )
    elif parser._match(TokenType.ENDS):
        parser._expect(TokenType.ENDS)
        parser._expect(TokenType.WITH)
        rhs = parser.get_parser(ast.CommonValueExpression)(parser)
        return StringMatchPredicate(lhs=lhs, kind=StringMatchPredicate.MatchKind.ENDS_WITH, rhs=rhs)
    elif parser._match(TokenType.CONTAINS):
        parser._expect(TokenType.CONTAINS)
        rhs = parser.get_parser(ast.CommonValueExpression)(parser)
        return StringMatchPredicate(lhs=lhs, kind=StringMatchPredicate.MatchKind.CONTAINS, rhs=rhs)
    elif parser._match(TokenType.IN):
        parser._expect(TokenType.IN)
        list_expr = parser.get_parser(ast.ValueExpression)(parser)
        return InPredicate(value=lhs, list_expression=list_expr)
    elif parser._match(TokenType.TILDE_EQUALS):
        parser._expect(TokenType.TILDE_EQUALS)
        rhs = parser.get_parser(ast.CommonValueExpression)(parser)
        return RegexMatchPredicate(lhs=lhs, rhs=rhs)

    parser.raise_error("Expected STARTS WITH, ENDS WITH, CONTAINS, IN, or =~")
    raise  # unreachable


def _parse_cypher_general_parameter_reference(
    parser: BaseParser,
) -> ast.GeneralParameterReference:
    """Parse ``$name`` or ``$123`` (Cypher allows numeric parameter names)."""
    parser._expect(TokenType.DOLLAR_SIGN)
    # Try standard identifier first
    param_name = parser.try_parse(parser.get_parser(ast.ParameterName))
    if param_name is not None:
        return ast.GeneralParameterReference(parameter_name=t.cast(ast.Identifier, param_name))
    # Numeric parameter: $1, $2, etc.
    if parser._match(TokenType.NUMBER):
        num_text = parser._curr.text
        parser._advance()
        ident = ast.Identifier(name=num_text)
        return ast.GeneralParameterReference._construct(
            parameter_name=ident,
        )
    parser.raise_error("Expected parameter name or number after $")
    raise  # unreachable


def _parse_cypher_boolean_factor(parser: BaseParser) -> ast.BooleanFactor:
    """Extended BooleanFactor: support ``NOT NOT expr`` (nested negation).

    Cypher allows: ``NOT NOT NOT ... expr`` — recursively nested.
    """
    if not parser._match(TokenType.NOT):
        # No NOT — plain BooleanTest
        boolean_test = parser.get_parser(ast.BooleanTest)(parser)
        return ast.BooleanFactor(not_=False, boolean_test=boolean_test)
    # Consume NOT
    parser._advance()
    if parser._match(TokenType.NOT):
        # Nested NOT — recurse to handle NOT NOT NOT ...
        inner = _parse_cypher_boolean_factor(parser)
        # Wrap inner BooleanFactor → BooleanTerm → BVE → BooleanTest
        # Use _construct to bypass strict BooleanPrimary validation
        # (BVE is not literally a BooleanPrimary but generators handle it)
        inner_bve = ast.BooleanValueExpression(
            boolean_term=ast.BooleanTerm(list_boolean_factor=[inner]),
            ops=None,
        )
        inner_test = ast.BooleanTest._construct(
            boolean_primary=inner_bve,
            truth_value=None,
        )
        return ast.BooleanFactor(not_=True, boolean_test=inner_test)
    boolean_test = parser.get_parser(ast.BooleanTest)(parser)
    return ast.BooleanFactor(not_=True, boolean_test=boolean_test)


def _parse_cypher_boolean_test(parser: BaseParser) -> ast.BooleanTest:
    """Extended BooleanTest parser that handles Cypher predicates.

    Tries Cypher-specific predicates first.  If one matches it is wrapped in a
    ``BooleanTest``.  Otherwise falls through to the standard GQL path.

    Performance: infix predicates (STARTS WITH, IN, =~) share a single VEP
    parse via ``_try_cypher_infix_predicate`` instead of each trying separately.
    """
    # List predicate functions: fail fast on keyword check (O(1))
    if parser._match(
        {TokenType.ALL, TokenType.ANY, TokenType.NONE_KW, TokenType.SINGLE}
    ) and parser._match_next(TokenType.LEFT_PAREN):
        pred_result = parser.try_parse(parser.PARSERS[ListPredicateFunction])
        if pred_result:
            # Check for comparison operator after quantifier predicate:
            # none(...) = true, any(...) <> false, etc.
            if parser._match(_COMPARISON_OPS):
                op_token = parser._curr
                parser._advance()
                comp_op = _TOKEN_TO_COMP_OP[op_token.token_type]
                rhs = parser.get_parser(ast.ValueExpression)(parser)
                comparison = CypherPredicateComparison(left=pred_result, op=comp_op, right=rhs)
                return ast.BooleanTest(
                    boolean_primary=t.cast(ast.BooleanPrimary, comparison),
                    truth_value=None,
                )
            return ast.BooleanTest(
                boolean_primary=t.cast(ast.BooleanPrimary, pred_result), truth_value=None
            )

    # Pattern predicate: bare pattern (n)-[:T]->() as boolean in WHERE
    if parser._match(TokenType.LEFT_PAREN):
        pattern_result = parser.try_parse(_parse_cypher_pattern_predicate)
        if pattern_result:
            return ast.BooleanTest(
                boolean_primary=t.cast(ast.BooleanPrimary, pattern_result), truth_value=None
            )

    # Infix predicates: parse VEP once, then check operator token
    infix_result = parser.try_parse(_try_cypher_infix_predicate)
    if infix_result:
        return ast.BooleanTest(
            boolean_primary=t.cast(ast.BooleanPrimary, infix_result), truth_value=None
        )

    # Standard GQL path — parse BooleanPrimary + optional IS [NOT] truth_value
    def _parse__is_not_truth_value(p: BaseParser) -> ast.BooleanTest._IsNotTruthValue:
        (_, not_, truth_value) = p.seq(
            TokenType.IS,
            p.opt(TokenType.NOT),
            p.get_parser(ast.TruthValue),
        )
        return ast.BooleanTest._IsNotTruthValue(not_=bool(not_), truth_value=truth_value)

    (boolean_primary, truth_value) = parser.seq(
        parser.get_parser(ast.BooleanPrimary),
        parser.opt(_parse__is_not_truth_value),
    )

    # Cypher extension: comparison with non-CVE RHS (e.g. quantifier predicate).
    # Handles: (single(...) OR all(...)) <= any(...),
    #          n.prop IS NULL = (m.prop IS NULL), etc.
    # Only triggers when BooleanPrimary is NOT already a ComparisonPredicate
    # (to avoid double-parsing chained comparisons like 1 = 2 = 3).
    if (
        truth_value is None
        and not isinstance(boolean_primary, ast.ComparisonPredicate)
        and parser._match(_COMPARISON_OPS)
    ):
        op_token = parser._curr
        parser._advance()
        comp_op = _TOKEN_TO_COMP_OP[op_token.token_type]
        rhs = parser.get_parser(ast.ValueExpression)(parser)
        comparison = CypherPredicateComparison(left=boolean_primary, op=comp_op, right=rhs)
        return ast.BooleanTest(
            boolean_primary=t.cast(ast.BooleanPrimary, comparison), truth_value=None
        )

    # Cypher precedence: IS [NOT] NULL / IN bind tighter than comparison operators.
    # e.g. `false = true IS NULL` → `false = (true IS NULL)`
    #       `false = true IN [true, false]` → `false = (true IN [true, false])`
    if truth_value is None and isinstance(boolean_primary, ast.ComparisonPredicate):
        rhs_expr = boolean_primary.comparison_predicate_part_2.comparison_predicand
        comp_op = boolean_primary.comparison_predicate_part_2.comp_op
        lhs_expr = boolean_primary.comparison_predicand
        rhs_wrapped: ast.Expression | None = None

        # IS [NOT] NULL after comparison RHS
        if parser._match(TokenType.IS) and parser._match_next({TokenType.NULL, TokenType.NOT}):
            parser._expect(TokenType.IS)
            not_ = False
            if parser._match(TokenType.NOT):
                parser._advance()
                not_ = True
            parser._expect(TokenType.NULL)
            rhs_wrapped = ast.NullPredicate._construct(
                value_expression_primary=rhs_expr,
                null_predicate_part_2=ast.NullPredicatePart2(not_=not_),
            )

        # IN list after comparison RHS
        if rhs_wrapped is None and parser._match(TokenType.IN):
            parser._expect(TokenType.IN)
            list_expr = parser.get_parser(ast.ValueExpression)(parser)
            rhs_wrapped = InPredicate(
                value=t.cast(ast.ValueExpression, rhs_expr), list_expression=list_expr
            )

        if rhs_wrapped is not None:
            comparison = CypherPredicateComparison(left=lhs_expr, op=comp_op, right=rhs_wrapped)
            return ast.BooleanTest(
                boolean_primary=t.cast(ast.BooleanPrimary, comparison), truth_value=None
            )

        # Chained comparison: a < b < c → ComparisonPredicate(a<b), ComparisonPredicate(b<c)
        if parser._match(_COMPARISON_OPS):
            comparisons: list[ast.ComparisonPredicate] = [boolean_primary]
            prev_rhs = boolean_primary.comparison_predicate_part_2.comparison_predicand
            while parser._match(_COMPARISON_OPS):
                op_token = parser._curr
                parser._advance()
                chain_op = _TOKEN_TO_COMP_OP[op_token.token_type]
                rhs = parser.get_parser(ast.CommonValueExpression)(parser)
                comparisons.append(
                    ast.ComparisonPredicate(
                        comparison_predicand=prev_rhs,
                        comparison_predicate_part_2=ast.ComparisonPredicatePart2(
                            comp_op=chain_op, comparison_predicand=rhs
                        ),
                    )
                )
                prev_rhs = rhs
            chained = CypherChainedComparison(comparisons=comparisons)
            return ast.BooleanTest(
                boolean_primary=t.cast(ast.BooleanPrimary, chained), truth_value=None
            )

    return ast.BooleanTest(boolean_primary=boolean_primary, truth_value=truth_value)


def _parse_cypher_primitive_query_statement(
    parser: BaseParser,
) -> ast.PrimitiveQueryStatement:
    """Extended PrimitiveQueryStatement parser with Cypher clauses.

    Adds UNWIND (rewritten to ForStatement), MERGE, CREATE, and bare WHERE
    (for WITH...WHERE patterns) to the candidate list.
    """
    candidates = (
        parser.get_parser(ast.MatchStatement),
        parser.get_parser(ast.LetStatement),
        parser.get_parser(ast.ForStatement),
        parser.get_parser(ast.FilterStatement),
        parser.get_parser(ast.OrderByAndPageStatement),
        # Cypher extensions
        _parse_cypher_with_statement,
        parser.PARSERS[MergeClause],
        parser.PARSERS[CreateClause],
        _parse_unwind_statement,
        parser.get_parser(ast.MacroCall),
    )
    (result,) = parser.seq(candidates)
    # WITH always requires a continuation clause — it's not a terminal statement.
    if isinstance(result, CypherWithStatement) and (
        parser._curr is None or parser._curr.token_type in (TokenType.EOF, TokenType.SEMICOLON)
    ):
        parser.raise_error(
            "Query cannot conclude with WITH (must be followed by a RETURN clause, "
            "an update clause, a subquery call, or a procedure call)"
        )
    return result


# =============================================================================
# Generator functions (plain functions -- NOT @generates-decorated)
# =============================================================================


def _generate_string_match_predicate(gen: BaseGenerator, expr: StringMatchPredicate) -> Fragment:
    lhs = gen.dispatch(expr.lhs)
    rhs = gen.dispatch(expr.rhs)
    kw = {
        StringMatchPredicate.MatchKind.STARTS_WITH: "STARTS WITH",
        StringMatchPredicate.MatchKind.ENDS_WITH: "ENDS WITH",
        StringMatchPredicate.MatchKind.CONTAINS: "CONTAINS",
    }[expr.kind]
    return gen.seq(lhs, kw, rhs)


def _generate_in_predicate(gen: BaseGenerator, expr: InPredicate) -> Fragment:
    return gen.seq(gen.dispatch(expr.value), "IN", gen.dispatch(expr.list_expression))


def _generate_merge_clause(gen: BaseGenerator, expr: MergeClause) -> Fragment:
    parts: list[str | Fragment] = [gen.seq("MERGE", gen.dispatch(expr.path_pattern))]
    if expr.on_create_set:
        parts.append(gen.seq("ON", "CREATE", "SET", gen.dispatch(expr.on_create_set)))
    if expr.on_match_set:
        parts.append(gen.seq("ON", "MATCH", "SET", gen.dispatch(expr.on_match_set)))
    return gen.seq(*parts, sep=gen.sep())


def _generate_create_clause(gen: BaseGenerator, expr: CreateClause) -> Fragment:
    return gen.seq("CREATE", gen.dispatch(expr.insert_graph_pattern))


def _generate_regex_match_predicate(gen: BaseGenerator, expr: RegexMatchPredicate) -> Fragment:
    return gen.seq(gen.dispatch(expr.lhs), "=~", gen.dispatch(expr.rhs))


def _generate_list_comprehension(gen: BaseGenerator, expr: ListComprehension) -> Fragment:
    parts: list[str | Fragment] = [
        "[",
        gen.dispatch(expr.variable),
        "IN",
        gen.dispatch(expr.source),
    ]
    if expr.where_clause:
        parts.append(gen.dispatch(expr.where_clause))
    if expr.projection:
        parts.extend(["|", gen.dispatch(expr.projection)])
    parts.append("]")
    return gen.seq(*parts)


def _generate_list_predicate_function(gen: BaseGenerator, expr: ListPredicateFunction) -> Fragment:
    kw = {
        ListPredicateFunction.Kind.ALL: "all",
        ListPredicateFunction.Kind.ANY: "any",
        ListPredicateFunction.Kind.NONE: "none",
        ListPredicateFunction.Kind.SINGLE: "single",
    }[expr.kind]
    return gen.seq(
        kw,
        "(",
        gen.dispatch(expr.variable),
        "IN",
        gen.dispatch(expr.source),
        "WHERE",
        gen.dispatch(expr.predicate),
        ")",
    )


def _generate_query_prefix(gen: BaseGenerator, expr: QueryPrefix) -> Fragment:
    kw = "EXPLAIN" if expr.kind == QueryPrefix.Kind.EXPLAIN else "PROFILE"
    return gen.seq(kw, gen.dispatch(expr.body))


def _generate_create_index(gen: BaseGenerator, expr: CreateIndex) -> Fragment:
    parts: list[str | Fragment] = ["CREATE", "INDEX"]
    if expr.name:
        parts.append(gen.dispatch(expr.name))
    if expr.if_not_exists:
        parts.extend(["IF", "NOT", "EXISTS"])
    parts.append("FOR")
    if expr.is_relationship:
        parts.append("(")
        parts.append(")")
        parts.append("-")
        parts.append("[")
        parts.append(gen.dispatch(expr.variable))
        parts.append(":")
        parts.append(gen.dispatch(expr.label))
        parts.append("]")
        parts.append("-")
        parts.append("(")
        parts.append(")")
    else:
        parts.append("(")
        parts.append(gen.dispatch(expr.variable))
        parts.append(":")
        parts.append(gen.dispatch(expr.label))
        parts.append(")")
    parts.append("ON")
    parts.append("(")
    for i, prop in enumerate(expr.properties):
        if i > 0:
            parts.append(",")
        parts.append(gen.dispatch(prop))
    parts.append(")")
    return gen.seq(*parts)


def _generate_drop_index(gen: BaseGenerator, expr: DropIndex) -> Fragment:
    parts: list[str | Fragment] = ["DROP", "INDEX", gen.dispatch(expr.name)]
    if expr.if_exists:
        parts.extend(["IF", "EXISTS"])
    return gen.seq(*parts)


def _generate_create_constraint(gen: BaseGenerator, expr: CreateConstraint) -> Fragment:
    parts: list[str | Fragment] = ["CREATE", "CONSTRAINT"]
    if expr.name:
        parts.append(gen.dispatch(expr.name))
    if expr.if_not_exists:
        parts.extend(["IF", "NOT", "EXISTS"])
    parts.append("FOR")
    parts.append("(")
    parts.append(gen.dispatch(expr.variable))
    parts.append(":")
    parts.append(gen.dispatch(expr.label))
    parts.append(")")
    parts.append("REQUIRE")

    if expr.constraint_kind == ConstraintKind.NODE_KEY:
        parts.append("(")
        for i, prop in enumerate(expr.properties):
            if i > 0:
                parts.append(",")
            parts.append(gen.dispatch(prop))
        parts.append(")")
    else:
        for prop in expr.properties:
            parts.append(gen.dispatch(prop))

    parts.append("IS")
    if expr.constraint_kind == ConstraintKind.UNIQUE:
        parts.append("UNIQUE")
    elif expr.constraint_kind == ConstraintKind.NOT_NULL:
        parts.extend(["NOT", "NULL"])
    elif expr.constraint_kind == ConstraintKind.NODE_KEY:
        parts.extend(["NODE", "KEY"])
    return gen.seq(*parts)


def _generate_drop_constraint(gen: BaseGenerator, expr: DropConstraint) -> Fragment:
    parts: list[str | Fragment] = ["DROP", "CONSTRAINT", gen.dispatch(expr.name)]
    if expr.if_exists:
        parts.extend(["IF", "EXISTS"])
    return gen.seq(*parts)


def _generate_unwind_statement(gen: BaseGenerator, expr: ast.ForStatement) -> Fragment:
    """Generate ``UNWIND expr AS var`` from a ForStatement.

    Only used by the Cypher generator -- the GQL generator emits ``FOR var IN expr``.
    """
    return gen.seq(
        "UNWIND",
        gen.dispatch(expr.for_item.for_item_source),
        "AS",
        gen.dispatch(expr.for_item.for_item_alias.binding_variable),
    )


def _nve_is_complex(
    nve: ast.NumericValueExpression,
    exclude: tuple[type, ...] = (),
    *,
    allow_term_steps: bool = False,
) -> bool:
    """True if an NVE will render with infix operators."""
    if nve.steps is not None:
        return True
    if isinstance(nve.base, ast.Term):
        if nve.base.steps is not None and not allow_term_steps:
            return True
        np = nve.base.base.numeric_primary
        check = tuple(t for t in (ast.ModulusExpression, ast.PowerFunction) if t not in exclude)
        if check and isinstance(np, check):
            return True
    return False


def _paren_nve(
    gen: BaseGenerator,
    nve: ast.NumericValueExpression,
    exclude: tuple[type, ...] = (),
    *,
    allow_term_steps: bool = False,
) -> Fragment:
    """Dispatch an NVE, wrapping in parens if it has multiple terms/factors."""
    inner = gen.dispatch(nve)
    if _nve_is_complex(nve, exclude=exclude, allow_term_steps=allow_term_steps):
        return gen.parens(inner)
    return inner


def _generate_cypher_modulus(gen: BaseGenerator, expr: ast.ModulusExpression) -> Fragment:
    """Generate ``dividend % divisor`` for Cypher infix modulus."""
    # Left operand: don't paren for Mod (left-assoc) or Power (higher prec).
    # allow_term_steps: * / are same precedence as %, no parens needed.
    dividend = _paren_nve(
        gen,
        expr.numeric_value_expression_dividend,
        exclude=(ast.ModulusExpression, ast.PowerFunction),
        allow_term_steps=True,
    )
    # Right operand: paren for Mod (override left-assoc), not Power (higher prec)
    divisor = _paren_nve(
        gen,
        expr.numeric_value_expression_divisor,
        exclude=(ast.PowerFunction,),
    )
    return Fragment(f"{dividend} % {divisor}")


def _generate_cypher_power(gen: BaseGenerator, expr: ast.PowerFunction) -> Fragment:
    """Generate ``base ^ exponent`` for Cypher infix exponentiation."""
    # Left operand: don't paren for Power (left-assoc), paren for Mod (lower prec)
    base = _paren_nve(
        gen,
        expr.numeric_value_expression_base,
        exclude=(ast.PowerFunction,),
    )
    # Right operand: paren for both Mod and Power (override left-assoc)
    exp = _paren_nve(gen, expr.numeric_value_expression_exponent)
    return Fragment(f"{base} ^ {exp}")


def _generate_cypher_with_statement(gen: BaseGenerator, expr: CypherWithStatement) -> Fragment:
    """Generate ``WITH <body> [ORDER BY / LIMIT] [WHERE ...]`` for Cypher."""
    parts: list[str | Fragment] = [gen.seq("WITH", gen.dispatch(expr.return_statement_body))]
    if expr.order_by_and_page_statement:
        parts.append(gen.dispatch(expr.order_by_and_page_statement))
    if expr.where_clause:
        parts.append(gen.dispatch(expr.where_clause))
    return gen.seq(*parts, sep=gen.sep())


def _generate_cypher_is_label_expression(
    gen: BaseGenerator, expr: ast.IsLabelExpression
) -> Fragment:
    """Generate ``:A:B:C`` (colon-separated labels) for Cypher."""
    return gen.seq(":", gen.dispatch(expr.label_expression), sep="")


def _generate_cypher_label_term(gen: BaseGenerator, expr: ast.LabelTerm) -> Fragment:
    """Generate colon-separated label conjunction for Cypher (instead of ``&``)."""
    return gen.join([gen.dispatch(f) for f in expr.label_factors], sep=":")


def _generate_cypher_subscript(gen: BaseGenerator, expr: CypherSubscriptExpression) -> Fragment:
    return gen.seq(gen.dispatch(expr.base), "[", gen.dispatch(expr.index), "]", sep="")


def _generate_cypher_simple_case(gen: BaseGenerator, expr: CypherSimpleCase) -> Fragment:
    parts: list[str | Fragment] = ["CASE", gen.dispatch(expr.case_operand)]
    for clause in expr.when_clauses:
        parts.append(_generate_cypher_when_clause(gen, clause))
    if expr.else_clause:
        parts.append(gen.dispatch(expr.else_clause))
    parts.append("END")
    return gen.seq(*parts)


def _generate_cypher_when_clause(gen: BaseGenerator, expr: CypherWhenClause) -> Fragment:
    operands = gen.join([gen.dispatch(o) for o in expr.operands], sep=", ")
    return gen.seq("WHEN", operands, "THEN", gen.dispatch(expr.result))


def _generate_cypher_slice(gen: BaseGenerator, expr: CypherSliceExpression) -> Fragment:
    base = gen.dispatch(expr.base)
    start = gen.dispatch(expr.start) if expr.start is not None else Fragment("")
    end = gen.dispatch(expr.end) if expr.end is not None else Fragment("")
    return Fragment(f"{base}[{start}..{end}]")


def _generate_cypher_pattern_comprehension(
    gen: BaseGenerator, expr: CypherPatternComprehension
) -> Fragment:
    parts: list[str | Fragment] = ["[", gen.dispatch(expr.pattern)]
    if expr.where_clause:
        parts.append(gen.dispatch(expr.where_clause))
    parts.extend(["|", gen.dispatch(expr.projection), "]"])
    return gen.seq(*parts)


_CYPHER_ESCAPE_MAP = {
    "\\": "\\\\",
    "'": "\\'",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
    "\b": "\\b",
    "\f": "\\f",
    "\0": "\\0",
}


def _escape_cypher_char(c: str) -> str:
    """Escape a single character for a Cypher string literal."""
    mapped = _CYPHER_ESCAPE_MAP.get(c)
    if mapped is not None:
        return mapped
    if not c.isprintable():
        cp = ord(c)
        if cp <= 0xFFFF:
            return f"\\u{cp:04x}"
        return f"\\U{cp:08x}"
    return c


def _generate_cypher_string_literal(
    gen: BaseGenerator, expr: ast.CharacterStringLiteral
) -> Fragment:
    """Generate Cypher string literal with backslash escaping."""
    value = expr.value or ""
    escaped = "".join(_escape_cypher_char(c) for c in value)
    return Fragment(f"'{escaped}'")


def _generate_cypher_cast_specification(
    gen: BaseGenerator, expr: ast.CastSpecification
) -> Fragment:
    """Generate Cypher type-conversion syntax from CastSpecification.

    Maps GQL ``CAST(x AS TYPE)`` to Cypher function syntax for supported target
    types, falling back to standard ``CAST(...)`` for others.
    """
    target = expr.cast_target
    operand = gen.dispatch(expr.cast_operand)
    if isinstance(target, ast.BooleanType):
        return gen.seq("toBoolean(", operand, ")", sep="")
    elif isinstance(target, ast.CharacterStringType):
        return gen.seq("toString(", operand, ")", sep="")
    elif isinstance(target, ast.ApproximateNumericType):
        return gen.seq("toFloat(", operand, ")", sep="")
    elif isinstance(
        target,
        ast.SignedBinaryExactNumericType
        | ast.UnsignedBinaryExactNumericType
        | ast.DecimalExactNumericType,
    ):
        return gen.seq("toInteger(", operand, ")", sep="")
    # Temporal types: CAST(x AS DATE) → date(x)
    for base_type, type_cls in _TEMPORAL_CAST_TARGETS.items():
        if isinstance(target, type_cls):
            name = base_type.name.lower()
            return gen.seq(f"{name}(", operand, ")", sep="")
    # Fallback to standard CAST for other types
    return Fragment(f"CAST({operand} AS {gen.dispatch(target)})")


def _generate_cypher_reduce(gen: BaseGenerator, expr: CypherReduce) -> Fragment:
    """Generate ``reduce(acc = init, var IN list | expr)``."""
    return gen.seq(
        "reduce(",
        gen.dispatch(expr.accumulator),
        "=",
        gen.dispatch(expr.initial),
        ",",
        gen.dispatch(expr.variable),
        "IN",
        gen.dispatch(expr.list_expr),
        "|",
        gen.dispatch(expr.expression),
        ")",
    )


_COMP_OP_TO_STR: dict[ast.ComparisonPredicatePart2.CompOp, str] = {
    ast.ComparisonPredicatePart2.CompOp.EQUALS: "=",
    ast.ComparisonPredicatePart2.CompOp.NOT_EQUALS: "<>",
    ast.ComparisonPredicatePart2.CompOp.LESS_THAN: "<",
    ast.ComparisonPredicatePart2.CompOp.GREATER_THAN: ">",
    ast.ComparisonPredicatePart2.CompOp.LESS_THAN_OR_EQUALS: "<=",
    ast.ComparisonPredicatePart2.CompOp.GREATER_THAN_OR_EQUALS: ">=",
}


def _generate_cypher_predicate_comparison(
    gen: BaseGenerator, expr: CypherPredicateComparison
) -> Fragment:
    return gen.seq(gen.dispatch(expr.left), _COMP_OP_TO_STR[expr.op], gen.dispatch(expr.right))


def _generate_cypher_chained_comparison(
    gen: BaseGenerator, expr: CypherChainedComparison
) -> Fragment:
    """Generate chained comparison: ``a < b < c`` (not expanded to AND)."""
    parts: list[str | Fragment] = []
    for i, cmp in enumerate(expr.comparisons):
        if i == 0:
            parts.append(gen.dispatch(cmp.comparison_predicand))
        parts.append(_COMP_OP_TO_STR[cmp.comparison_predicate_part_2.comp_op])
        parts.append(gen.dispatch(cmp.comparison_predicate_part_2.comparison_predicand))
    return gen.seq(*parts)


def _generate_cypher_pattern_predicate(
    gen: BaseGenerator, expr: CypherPatternPredicate
) -> Fragment:
    return gen.dispatch(expr.pattern)


def _generate_cypher_abbreviated_edge(
    gen: BaseGenerator, expr: ast.AbbreviatedEdgePattern
) -> Fragment:
    """Generate Cypher-style double-dash arrows: ``-->``, ``<--``, ``--``, ``<-->``."""
    pattern_map = {
        ast.AbbreviatedEdgePattern.PatternType.LEFT_ARROW: "<--",
        ast.AbbreviatedEdgePattern.PatternType.RIGHT_ARROW: "-->",
        ast.AbbreviatedEdgePattern.PatternType.MINUS_SIGN: "--",
        ast.AbbreviatedEdgePattern.PatternType.LEFT_MINUS_RIGHT: "<-->",
    }
    return Fragment(pattern_map[expr.pattern])


# --- Cypher temporal generators (lowercase output) ---


def _generate_cypher_date_function(gen: BaseGenerator, expr: ast.DateFunction) -> Fragment:
    if isinstance(expr.date_function, ast.DateFunction._CurrentDate):
        return Fragment("date()")
    inner = expr.date_function
    if inner.date_function_parameters:
        return Fragment(f"date({gen.dispatch(inner.date_function_parameters)})")
    return Fragment("date()")


def _generate_cypher_time_function(gen: BaseGenerator, expr: ast.TimeFunction) -> Fragment:
    if isinstance(expr.time_function, ast.TimeFunction._CurrentTime):
        return Fragment("time()")
    inner = expr.time_function
    if inner.time_function_parameters:
        return Fragment(f"time({gen.dispatch(inner.time_function_parameters)})")
    return Fragment("time()")


def _generate_cypher_datetime_function(gen: BaseGenerator, expr: ast.DatetimeFunction) -> Fragment:
    if isinstance(expr.datetime_function, ast.DatetimeFunction._CurrentTimestamp):
        return Fragment("datetime()")
    inner = expr.datetime_function
    if inner.datetime_function_parameters:
        return Fragment(f"datetime({gen.dispatch(inner.datetime_function_parameters)})")
    return Fragment("datetime()")


def _generate_cypher_localdatetime_function(
    gen: BaseGenerator, expr: ast.LocaldatetimeFunction
) -> Fragment:
    if isinstance(expr.localdatetime_function, ast.LocaldatetimeFunction._LocalTimestamp):
        return Fragment("localdatetime()")
    inner = expr.localdatetime_function
    if inner.datetime_function_parameters:
        return Fragment(f"localdatetime({gen.dispatch(inner.datetime_function_parameters)})")
    return Fragment("localdatetime()")


def _generate_cypher_localtime_function(
    gen: BaseGenerator, expr: ast.LocaltimeFunction
) -> Fragment:
    if expr.time_function_parameters:
        return Fragment(f"localtime({gen.dispatch(expr.time_function_parameters)})")
    return Fragment("localtime()")


def _generate_cypher_duration_function(gen: BaseGenerator, expr: ast.DurationFunction) -> Fragment:
    return Fragment(f"duration({gen.dispatch(expr.duration_function_parameters)})")


def _generate_cypher_temporal_cast(gen: BaseGenerator, expr: CypherTemporalCast) -> Fragment:
    arg_str = str(gen.dispatch(expr.argument))
    name = expr.function_name.name.lower()
    return Fragment(f"{name}({arg_str})")


def _generate_cypher_datetime_subtraction(
    gen: BaseGenerator, expr: ast.DatetimeSubtraction
) -> Fragment:
    """Generate ``duration.between(d1, d2)`` from DatetimeSubtraction.

    Unqualified DatetimeSubtraction (no temporal_duration_qualifier) maps to
    Cypher ``duration.between()``. Qualified forms fall back to GQL
    ``DURATION_BETWEEN(d1, d2) YEAR TO MONTH``.
    """
    params = expr.datetime_subtraction_parameters
    d1 = gen.dispatch(params.datetime_value_expression_1)
    d2 = gen.dispatch(params.datetime_value_expression_2)
    if expr.temporal_duration_qualifier is None:
        return Fragment(f"duration.between({d1}, {d2})")
    qualifier = gen.dispatch(expr.temporal_duration_qualifier)
    return gen.seq("DURATION_BETWEEN", gen.parens(gen.seq(d1, ",", d2)), qualifier)


def _generate_cypher_temporal_method(gen: BaseGenerator, expr: CypherTemporalMethod) -> Fragment:
    base_names = {
        TemporalBaseType.DATE: "date",
        TemporalBaseType.TIME: "time",
        TemporalBaseType.DATETIME: "datetime",
        TemporalBaseType.LOCALDATETIME: "localdatetime",
        TemporalBaseType.LOCALTIME: "localtime",
        TemporalBaseType.DURATION: "duration",
    }
    method_names = {
        CypherTemporalMethod.Method.TRUNCATE: "truncate",
        # BETWEEN is parsed directly into DatetimeSubtraction (not CypherTemporalMethod)
        CypherTemporalMethod.Method.TRANSACTION: "transaction",
        CypherTemporalMethod.Method.STATEMENT: "statement",
        CypherTemporalMethod.Method.REALTIME: "realtime",
        CypherTemporalMethod.Method.INMONTHS: "inMonths",
        CypherTemporalMethod.Method.INDAYS: "inDays",
        CypherTemporalMethod.Method.INSECONDS: "inSeconds",
        CypherTemporalMethod.Method.FROMEPOCH: "fromepoch",
        CypherTemporalMethod.Method.FROMEPOCHMILLIS: "fromepochmillis",
    }
    base = base_names[expr.base_type]
    method = method_names[expr.method]
    if expr.arguments:
        arg_strs = ", ".join(str(gen.dispatch(a)) for a in expr.arguments)
        return Fragment(f"{base}.{method}({arg_strs})")
    return Fragment(f"{base}.{method}()")


# =============================================================================
# Variable-length path support
# =============================================================================


def _parse_varlen_quantifier(
    parser: BaseParser,
) -> ast.FixedQuantifier | ast.GeneralQuantifier:
    """Parse ``*N..M``, ``*N``, ``*..M``, ``*N..``, or bare ``*``.

    The ``*`` has already been consumed by the caller.
    """
    if parser._match(TokenType.NUMBER):
        val = int(t.cast(Token, parser._expect(TokenType.NUMBER)).text)
        if parser._match(TokenType.DOUBLE_PERIOD):
            parser._expect(TokenType.DOUBLE_PERIOD)
            upper = None
            if parser._match(TokenType.NUMBER):
                upper = ast.UnsignedInteger(
                    value=int(t.cast(Token, parser._expect(TokenType.NUMBER)).text)
                )
            return ast.GeneralQuantifier(
                lower_bound=ast.UnsignedInteger(value=val), upper_bound=upper
            )
        return ast.FixedQuantifier(unsigned_integer=ast.UnsignedInteger(value=val))
    elif parser._match(TokenType.DOUBLE_PERIOD):
        parser._expect(TokenType.DOUBLE_PERIOD)
        upper = None
        if parser._match(TokenType.NUMBER):
            upper = ast.UnsignedInteger(
                value=int(t.cast(Token, parser._expect(TokenType.NUMBER)).text)
            )
        return ast.GeneralQuantifier(lower_bound=None, upper_bound=upper)
    # Bare *: unbounded
    return ast.GeneralQuantifier(lower_bound=None, upper_bound=None)


def _parse_cypher_element_pattern_filler(parser: BaseParser) -> ast.ElementPatternFiller:
    """Parse element pattern filler with optional Cypher variable-length quantifier.

    In Cypher, ``[r:TYPE*1..5 {prop: val}]`` places the quantifier inside the
    brackets after the label and before the property predicate.  We store the
    parsed quantifier on a side-channel attribute so that the PathFactor
    override can wrap the result in a ``QuantifiedPathPrimary``.
    """
    var = t.cast(
        "ast.ElementVariableDeclaration | None",
        parser.try_parse(parser.get_parser(ast.ElementVariableDeclaration)),
    )
    label = t.cast(
        "ast.IsLabelExpression | None",
        parser.try_parse(parser.get_parser(ast.IsLabelExpression)),
    )

    # Variable-length quantifier: * [int] [.. [int]]
    quantifier = None
    if parser._match(TokenType.ASTERISK):
        parser._expect(TokenType.ASTERISK)
        quantifier = _parse_varlen_quantifier(parser)
    parser._pending_varlen_quantifier = quantifier  # type: ignore[attr-defined]

    pred = t.cast(
        "ast.ElementPatternPredicate | None",
        parser.try_parse(parser.get_parser(ast.ElementPatternPredicate)),
    )
    return ast.ElementPatternFiller(
        element_variable_declaration=var,
        is_label_expression=label,
        element_pattern_predicate=pred,
    )


def _parse_cypher_path_factor(parser: BaseParser) -> ast.PathFactor:
    """Parse a path factor, wrapping in QuantifiedPathPrimary if a variable-length
    quantifier was set by the element pattern filler override."""
    # Standard PathFactor candidates: QPP → QuestionedPP → PathPrimary
    candidates = (
        parser.get_parser(ast.QuantifiedPathPrimary),
        parser.get_parser(ast.QuestionedPathPrimary),
        parser.get_parser(ast.PathPrimary),
    )
    (result,) = parser.seq(candidates)

    quantifier = getattr(parser, "_pending_varlen_quantifier", None)
    if quantifier is not None:
        parser._pending_varlen_quantifier = None  # type: ignore[attr-defined]
        result = ast.QuantifiedPathPrimary(
            path_primary=result,
            graph_pattern_quantifier=quantifier,
        )
    return result


# =============================================================================
# Variable-length path generator
# =============================================================================

_EDGE_TYPES_WITH_FILLER = (
    ast.FullEdgePointingRight,
    ast.FullEdgePointingLeft,
    ast.FullEdgeAnyDirection,
    ast.FullEdgeUndirected,
    ast.FullEdgeLeftOrUndirected,
    ast.FullEdgeUndirectedOrRight,
    ast.FullEdgeLeftOrRight,
)


def _format_cypher_quantifier(q: ast.GraphPatternQuantifier) -> str:
    """Format a GQL quantifier as Cypher ``*N..M`` syntax."""
    if isinstance(q, ast.FixedQuantifier):
        return f"*{q.unsigned_integer.value}"
    if isinstance(q, ast.GeneralQuantifier):
        lower = str(q.lower_bound.value) if q.lower_bound else ""
        upper = str(q.upper_bound.value) if q.upper_bound else ""
        if not lower and not upper:
            return "*"
        return f"*{lower}..{upper}"
    return "*"


def _render_filler_with_quantifier(
    gen: BaseGenerator,
    filler: ast.ElementPatternFiller,
    quantifier: ast.GraphPatternQuantifier,
) -> str:
    """Render filler parts with quantifier between label and property predicate.

    Cypher order: ``var :LABEL *quantifier {property}``
    """
    parts: list[str] = []
    if filler.element_variable_declaration:
        parts.append(str(gen.dispatch(filler.element_variable_declaration)))
    if filler.is_label_expression:
        parts.append(str(gen.dispatch(filler.is_label_expression)))
    parts.append(_format_cypher_quantifier(quantifier))
    if filler.element_pattern_predicate:
        parts.append(str(gen.dispatch(filler.element_pattern_predicate)))
    return " ".join(parts)


def _generate_cypher_quantified_path_primary(
    gen: BaseGenerator, expr: ast.QuantifiedPathPrimary
) -> Fragment:
    """Generate a QuantifiedPathPrimary, rendering quantifier inside brackets for edges."""
    edge = expr.path_primary
    if not isinstance(edge, _EDGE_TYPES_WITH_FILLER):
        # Non-edge (e.g. parenthesized path pattern): use standard GQL rendering
        return gen.seq(gen.dispatch(edge), gen.dispatch(expr.graph_pattern_quantifier))

    inner = _render_filler_with_quantifier(
        gen, edge.element_pattern_filler, expr.graph_pattern_quantifier
    )

    if isinstance(edge, ast.FullEdgePointingRight):
        return Fragment(f"-[{inner}]->")
    elif isinstance(edge, ast.FullEdgePointingLeft):
        return Fragment(f"<-[{inner}]-")
    elif isinstance(edge, ast.FullEdgeAnyDirection):
        return Fragment(f"-[{inner}]-")
    elif isinstance(edge, ast.FullEdgeUndirected):
        return Fragment(f"~[{inner}]~")
    elif isinstance(edge, ast.FullEdgeLeftOrUndirected):
        return Fragment(f"<~[{inner}]~")
    elif isinstance(edge, ast.FullEdgeUndirectedOrRight):
        return Fragment(f"~[{inner}]~>")
    elif isinstance(edge, ast.FullEdgeLeftOrRight):
        return Fragment(f"<-[{inner}]->")
    # Fallback
    return gen.seq(gen.dispatch(edge), gen.dispatch(expr.graph_pattern_quantifier))


# =============================================================================
# CALL procedure overrides (Plan 041, Feature 3)
# =============================================================================


def _parse_cypher_yield_clause(parser: BaseParser) -> ast.YieldClause:
    """Parse YIELD clause, supporting ``YIELD *`` (Cypher extension)."""
    parser._expect(TokenType.YIELD)
    if parser._match(TokenType.ASTERISK):
        parser._expect(TokenType.ASTERISK)
        # YIELD * — return a YieldClause with an empty item list
        return ast.YieldClause._construct(
            yield_item_list=ast.YieldItemList._construct(list_yield_item=[]),
        )
    yield_item_list = parser.get_parser(ast.YieldItemList)(parser)
    return ast.YieldClause(yield_item_list=yield_item_list)


def _parse_cypher_named_procedure_call(parser: BaseParser) -> ast.NamedProcedureCall:
    """Parse CALL with or without parentheses (Cypher allows both)."""
    # Try GQL path first (with parens)
    result = parser.try_parse(BaseParser.PARSERS[ast.NamedProcedureCall])
    if result:
        return t.cast(ast.NamedProcedureCall, result)
    # No-parens path: just procedure reference + optional YIELD
    proc_ref = parser.get_parser(ast.ProcedureReference)(parser)
    yield_clause = t.cast(
        "ast.YieldClause | None",
        parser.try_parse(parser.get_parser(ast.YieldClause)),
    )
    return ast.NamedProcedureCall(
        procedure_reference=proc_ref,
        procedure_argument_list=None,
        yield_clause=yield_clause,
    )


def _generate_cypher_named_procedure_call(
    gen: BaseGenerator, expr: ast.NamedProcedureCall
) -> Fragment:
    """Generate CALL, always emitting parentheses even when no args."""
    parts: list[str | Fragment] = [gen.dispatch(expr.procedure_reference)]
    if expr.procedure_argument_list is not None:
        args = gen.dispatch(expr.procedure_argument_list)
        parts.append(gen.parens(args))
    else:
        parts.append(gen.parens(""))  # Always emit ()
    # proc_name(...) has no space, but YIELD needs a space
    call_part = gen.seq(*parts, sep="")
    if expr.yield_clause:
        return gen.seq(call_part, gen.dispatch(expr.yield_clause))
    return call_part


def _generate_cypher_yield_clause(gen: BaseGenerator, expr: ast.YieldClause) -> Fragment:
    """Generate YIELD clause, emitting ``YIELD *`` for empty item lists."""
    if not expr.yield_item_list.list_yield_item:
        return gen.seq("YIELD", "*")
    return gen.seq(gen.keyword("YIELD"), gen.dispatch(expr.yield_item_list))


_BINARY_SET_FUNC_NAMES = {
    ast.BinarySetFunction.BinarySetFunctionType.PERCENTILE_CONT: "percentileCont",
    ast.BinarySetFunction.BinarySetFunctionType.PERCENTILE_DISC: "percentileDisc",
}


def _generate_cypher_binary_set_function(
    gen: BaseGenerator, expr: ast.BinarySetFunction
) -> Fragment:
    """Generate percentileDisc/percentileCont in Cypher camelCase form."""
    func_name = _BINARY_SET_FUNC_NAMES[expr.binary_set_function_type]
    dep = gen.dispatch(expr.dependent_value_expression)
    ind = gen.dispatch(expr.independent_value_expression)
    return Fragment(f"{func_name}({dep}, {ind})")


# =============================================================================
# Label predicate generator override (Plan 041, Feature 4)
# =============================================================================


def _generate_cypher_labeled_predicate(gen: BaseGenerator, expr: ast.LabeledPredicate) -> Fragment:
    """Generate label predicate as ``var:Label`` (Cypher colon syntax)."""
    var = gen.dispatch(expr.element_variable_reference)
    label = gen.dispatch(expr.labeled_predicate_part_2.label_expression)
    return Fragment(f"{var}:{label}")


# =============================================================================
# Multi-label REMOVE/SET parser overrides (Plan 041, Feature 2)
# =============================================================================


def _parse_cypher_remove_item_list(parser: BaseParser) -> ast.RemoveItemList:
    """Parse RemoveItemList with support for multi-label REMOVE n:L1:L2."""
    items: list[ast.RemoveItem] = []
    while True:
        item_or_items = _parse_cypher_remove_item(parser)
        if isinstance(item_or_items, list):
            items.extend(item_or_items)
        else:
            items.append(item_or_items)
        if not parser._match(TokenType.COMMA):
            break
        parser._advance()
    return ast.RemoveItemList(list_remove_item=items)


def _parse_cypher_remove_item(
    parser: BaseParser,
) -> ast.RemoveItem | list[ast.RemoveLabelItem]:
    """Parse a single RemoveItem, expanding multi-label to a list."""
    # Try RemovePropertyItem first (n.prop)
    result = parser.try_parse(parser.get_parser(ast.RemovePropertyItem))
    if result:
        return t.cast(ast.RemoveItem, result)
    # Label path: n:L1:L2
    var = parser.get_parser(ast.BindingVariableReference)(parser)
    parser._expect({TokenType.IS, TokenType.COLON})
    labels = [parser.get_parser(ast.LabelName)(parser)]
    while parser._match(TokenType.COLON):
        parser._advance()
        labels.append(parser.get_parser(ast.LabelName)(parser))
    if len(labels) == 1:
        return ast.RemoveLabelItem(binding_variable_reference=var, label_name=labels[0])
    return [
        ast.RemoveLabelItem(binding_variable_reference=var, label_name=label) for label in labels
    ]


def _parse_cypher_set_item_list(parser: BaseParser) -> ast.SetItemList:
    """Parse SetItemList with support for multi-label SET n:L1:L2."""
    items: list[ast.SetItem] = []
    while True:
        item_or_items = _parse_cypher_set_item(parser)
        if isinstance(item_or_items, list):
            items.extend(item_or_items)
        else:
            items.append(item_or_items)
        if not parser._match(TokenType.COMMA):
            break
        parser._advance()
    return ast.SetItemList(list_set_item=items)


def _parse_cypher_set_item(
    parser: BaseParser,
) -> ast.SetItem | list[ast.SetLabelItem]:
    """Parse a single SetItem, expanding multi-label to a list.

    Handles standard GQL SET items plus Cypher extensions:
    - ``n += {map}`` — map append
    - ``(expr).prop = val`` — parenthesized SET target
    - ``n = other`` — set all properties from another node
    """
    # (expr).prop = val  — parenthesized SET target
    if parser._match(TokenType.LEFT_PAREN):
        result = parser.try_parse(_parse_cypher_set_property_from_expr)
        if result:
            return t.cast(ast.SetItem, result)

    # Try SetPropertyItem first (n.prop = val)
    result = parser.try_parse(parser.get_parser(ast.SetPropertyItem))
    if result:
        return t.cast(ast.SetItem, result)

    # n += {map}  or  n = {map}  or  n = other  or  n:Label
    # All start with BindingVariableReference, so parse it once
    saved = parser._index
    var_expr = parser.try_parse(parser.get_parser(ast.BindingVariableReference))
    if var_expr is not None:
        var = t.cast(ast.BindingVariableReference, var_expr)
        # n += {map}
        if parser._match(TokenType.PLUS_SIGN):
            parser._expect(TokenType.PLUS_SIGN)
            parser._expect(TokenType.EQUALS_OPERATOR)
            map_expr = parser.get_parser(ast.ValueExpression)(parser)
            return t.cast(
                ast.SetItem,
                CypherSetMapAppendItem(binding_variable_reference=var, map_expression=map_expr),
            )

        # n = expr (copy all properties)
        if parser._match(TokenType.EQUALS_OPERATOR):
            parser._expect(TokenType.EQUALS_OPERATOR)
            val = parser.get_parser(ast.ValueExpression)(parser)
            return t.cast(
                ast.SetItem,
                CypherSetAllFromExprItem(
                    binding_variable_reference=var,
                    value=val,
                ),
            )

        # Label path: n:L1:L2
        if parser._match({TokenType.IS, TokenType.COLON}):
            parser._expect({TokenType.IS, TokenType.COLON})
            labels = [parser.get_parser(ast.LabelName)(parser)]
            while parser._match(TokenType.COLON):
                parser._advance()
                labels.append(parser.get_parser(ast.LabelName)(parser))
            if len(labels) == 1:
                return ast.SetLabelItem(binding_variable_reference=var, label_name=labels[0])
            return [
                ast.SetLabelItem(binding_variable_reference=var, label_name=label)
                for label in labels
            ]

    parser._retreat(saved)
    parser.raise_error("Expected SET item (property, map, label, or +=)")
    raise  # unreachable


def _parse_cypher_set_property_from_expr(
    parser: BaseParser,
) -> CypherSetPropertyFromExprItem:
    """Parse ``(expr).prop = val``."""
    parser._expect(TokenType.LEFT_PAREN)
    expr = parser.get_parser(ast.ValueExpression)(parser)
    parser._expect(TokenType.RIGHT_PAREN)
    parser._expect(TokenType.PERIOD)
    prop_name = parser.get_parser(ast.PropertyName)(parser)
    parser._expect(TokenType.EQUALS_OPERATOR)
    val = parser.get_parser(ast.ValueExpression)(parser)
    return CypherSetPropertyFromExprItem(target_expression=expr, property_name=prop_name, value=val)


def _generate_cypher_remove_statement(gen: BaseGenerator, expr: ast.RemoveStatement) -> Fragment:
    """Generate REMOVE, merging consecutive same-variable labels into n:L1:L2."""
    items = expr.remove_item_list.list_remove_item
    parts: list[str | Fragment] = ["REMOVE"]
    rendered: list[str | Fragment] = []
    i = 0
    while i < len(items):
        item = items[i]
        if isinstance(item, ast.RemoveLabelItem):
            # Collect consecutive label items for the same variable
            var_name = item.binding_variable_reference.binding_variable.name
            label_names = [str(gen.dispatch(item.label_name))]
            j = i + 1
            while j < len(items):
                next_item = items[j]
                if (
                    isinstance(next_item, ast.RemoveLabelItem)
                    and next_item.binding_variable_reference.binding_variable.name == var_name
                ):
                    label_names.append(str(gen.dispatch(next_item.label_name)))
                    j += 1
                else:
                    break
            var = gen.dispatch(item.binding_variable_reference)
            rendered.append(Fragment(f"{var}:{':'.join(label_names)}"))
            i = j
        else:
            rendered.append(gen.dispatch(item))
            i += 1
    parts.append(gen.join(rendered, sep=", "))
    return gen.seq(*parts)


def _generate_cypher_set_statement(gen: BaseGenerator, expr: ast.SetStatement) -> Fragment:
    """Generate SET, merging consecutive same-variable labels into n:L1:L2."""
    items = expr.set_item_list.list_set_item
    parts: list[str | Fragment] = ["SET"]
    rendered: list[str | Fragment] = []
    i = 0
    while i < len(items):
        item = items[i]
        if isinstance(item, ast.SetLabelItem):
            # Collect consecutive label items for the same variable
            var_name = item.binding_variable_reference.binding_variable.name
            label_names = [str(gen.dispatch(item.label_name))]
            j = i + 1
            while j < len(items):
                next_item = items[j]
                if (
                    isinstance(next_item, ast.SetLabelItem)
                    and next_item.binding_variable_reference.binding_variable.name == var_name
                ):
                    label_names.append(str(gen.dispatch(next_item.label_name)))
                    j += 1
                else:
                    break
            var = gen.dispatch(item.binding_variable_reference)
            rendered.append(Fragment(f"{var}:{':'.join(label_names)}"))
            i = j
        else:
            rendered.append(gen.dispatch(item))
            i += 1
    parts.append(gen.join(rendered, sep=", "))
    return gen.seq(*parts)


def _generate_cypher_set_all_from_expr_item(
    gen: BaseGenerator, expr: CypherSetAllFromExprItem
) -> Fragment:
    """Generate ``n = expr``."""
    var = gen.dispatch(expr.binding_variable_reference)
    val = gen.dispatch(expr.value)
    return Fragment(f"{var} = {val}")


def _generate_cypher_set_map_append_item(
    gen: BaseGenerator, expr: CypherSetMapAppendItem
) -> Fragment:
    """Generate ``n += {map}``."""
    var = gen.dispatch(expr.binding_variable_reference)
    val = gen.dispatch(expr.map_expression)
    return Fragment(f"{var} += {val}")


def _generate_cypher_set_property_from_expr_item(
    gen: BaseGenerator, expr: CypherSetPropertyFromExprItem
) -> Fragment:
    """Generate ``(expr).prop = val``."""
    target = gen.dispatch(expr.target_expression)
    prop = gen.dispatch(expr.property_name)
    val = gen.dispatch(expr.value)
    return Fragment(f"({target}).{prop} = {val}")


def _parse_cypher_label_term(parser: BaseParser) -> ast.LabelTerm:
    """Parse LabelTerm with ``:`` as conjunction (in addition to GQL ``&``).

    Cypher uses ``a:A:B`` to mean "has both labels A and B", where ``:`` acts
    as conjunction.  GQL uses ``&`` for the same purpose.
    """
    factors = [parser.get_parser(ast.LabelFactor)(parser)]
    while parser._match({TokenType.AMPERSAND, TokenType.COLON}):
        parser._advance()
        factors.append(parser.get_parser(ast.LabelFactor)(parser))
    return ast.LabelTerm(label_factors=factors)


def _reject_negative_literal(expr: ast.Expression, clause: str) -> None:
    """Reject negative numeric literal in SKIP/LIMIT."""
    cur = expr
    while True:
        if isinstance(cur, ast.Factor | ast.ArithmeticFactor) and cur.sign == ast.Sign.MINUS_SIGN:
            raise ParseError(f"Negative value not allowed in {clause} clause")
        children = list(cur.children())
        if len(children) != 1:
            break
        cur = children[0]


def _reject_float_literal(expr: ast.Expression, clause: str) -> None:
    """Reject float literal in SKIP/LIMIT."""
    cur = expr
    while True:
        children = list(cur.children())
        if len(children) != 1:
            break
        cur = children[0]
    if isinstance(cur, ast.UnsignedNumericLiteral) and isinstance(cur.value, Decimal):
        raise ParseError(f"Floating point value not allowed in {clause} clause")


def _parse_cypher_offset_clause(parser: BaseParser) -> ast.OffsetClause:
    """Parse SKIP/OFFSET with expression (not just integer literal).

    Cypher allows ``SKIP $param`` and ``SKIP toInteger(expr)`` in addition
    to the GQL-standard ``OFFSET <integer>``.
    """
    parser._expect({TokenType.SKIP, TokenType.OFFSET})
    expr = parser.get_parser(ast.ValueExpression)(parser)
    _reject_negative_literal(expr, "SKIP")
    _reject_float_literal(expr, "SKIP")
    # _construct bypasses validation to allow any expression
    return ast.OffsetClause._construct(non_negative_integer_specification=expr)


def _parse_cypher_limit_clause(parser: BaseParser) -> ast.LimitClause:
    """Parse LIMIT with expression (not just integer literal).

    Cypher allows ``LIMIT $param`` and ``LIMIT toInteger(expr)`` in addition
    to the GQL-standard ``LIMIT <integer>``.
    """
    parser._expect(TokenType.LIMIT)
    expr = parser.get_parser(ast.ValueExpression)(parser)
    _reject_negative_literal(expr, "LIMIT")
    _reject_float_literal(expr, "LIMIT")
    # _construct bypasses validation to allow any expression
    return ast.LimitClause._construct(non_negative_integer_specification=expr)


# =============================================================================
# CypherDialect class
# =============================================================================


class CypherDialect(Dialect):
    """Abstract base for Cypher-compatible database dialects.

    Provides shared Cypher syntax extensions (string match operators, IN,
    UNWIND, MERGE, etc.) that vendors like Neo4j.

    **Not** registered in the :class:`Dialects` enum -- pick a vendor.
    """

    SUPPORTED_FEATURES: t.ClassVar[set[Feature]] = Dialect.SUPPORTED_FEATURES | ALL_CYPHER_FEATURES

    TRANSFORMATIONS: t.ClassVar[list] = [with_to_next, *Dialect.TRANSFORMATIONS]

    KEYWORD_OVERRIDES: t.ClassVar[dict[str, str]] = {
        "COLLECT_LIST": "COLLECT",
    }

    # Cypher-specific keywords are non-reserved — they can appear as identifiers
    # (variable names, parameter names, etc.).  This covers tokens added by the
    # Cypher lexer but NOT base GQL reserved words (MATCH, RETURN, WHERE, …).
    # In real Cypher those are also usable as identifiers / parameter names, but
    # adding them here would cause parse ambiguities with GQL grammar productions.
    NON_RESERVED_WORDS: t.ClassVar[set[TokenType]] = Dialect.NON_RESERVED_WORDS | {
        # --- GQL reserved keywords usable as Cypher identifiers ---
        # Predicate/existence keywords — Cypher allows n.exists, n.existing as props
        TokenType.EXISTS,
        TokenType.EXISTING,
        # Clause keywords — Cypher allows n.offset as property name
        TokenType.OFFSET,
        # Type keywords — used as property names (a.bool), aliases (AS bool)
        TokenType.BOOL,
        TokenType.FLOAT,
        TokenType.INT,
        TokenType.LIST,
        TokenType.REAL,
        TokenType.VALUE,
        # Aggregate function keywords — used as aliases (AS sum, AS count)
        TokenType.AVG,
        TokenType.COUNT,
        TokenType.MAX,
        TokenType.MIN,
        TokenType.SUM,
        # Temporal keywords — used as property names (a.date, a.time)
        # NOTE: These are also in the base parser's DATETIME/DURATION fast-path
        # token sets.  _parse_cypher_common_value_expression guards against the
        # fast-path firing when these tokens are bare identifiers (not followed
        # by '(', '.', or a string literal).
        TokenType.DATE,
        TokenType.TIME,
        TokenType.DATETIME,
        TokenType.DURATION,
        TokenType.TIMESTAMP,
        # --- Cypher-specific keywords (already non-reserved) ---
        TokenType.CONSTRAINT,
        TokenType.CONTAINS,
        TokenType.CSV,
        # Temporal field names — reserved in GQL for temporal duration qualifiers
        # (INTERVAL YEAR TO MONTH) but used as record field names and property
        # names in Cypher: date({year: 2024, month: 1, day: 15}), d.year, etc.
        TokenType.DAY,
        TokenType.ENDS,
        TokenType.EXPLAIN,
        TokenType.FIELDTERMINATOR,
        TokenType.FOREACH,
        TokenType.HEADERS,
        TokenType.HOUR,
        TokenType.INDEX,
        TokenType.KEY,
        TokenType.KEYS,
        TokenType.LOAD,
        TokenType.NODES,
        TokenType.MERGE,
        TokenType.MINUTE,
        TokenType.MONTH,
        TokenType.NONE_KW,
        TokenType.PROFILE,
        TokenType.PROPERTIES,
        TokenType.RANGE,
        TokenType.REDUCE,
        TokenType.REQUIRE,
        # NOT ROUND — it is used as a function keyword (ROUND(...)) and would
        # cause ambiguity in expression contexts.
        TokenType.ROWS,
        TokenType.SECOND,
        TokenType.SINGLE,
        TokenType.STARTS,
        TokenType.TOBOOLEAN,
        TokenType.TOFLOAT,
        TokenType.TOINTEGER,
        TokenType.TOSTRING,
        TokenType.TRANSACTIONS,
        TokenType.UNWIND,
        TokenType.YEAR,
        TokenType.REVERSE,
        # Relationship/label keywords — Cypher allows :TYPE, :End as labels
        TokenType.TYPE,
        TokenType.END,
        # Path/collection keywords — Cypher allows path/paths/values/start as identifiers
        TokenType.PATH,
        TokenType.PATHS,
        TokenType.VALUES,
        TokenType.START,
        TokenType.PATH_LENGTH,  # Neo4j maps LENGTH → PATH_LENGTH; _parse_cypher_core_cve guards fn
        # SQL keywords unused in Cypher — allows [like] as variable, AS from
        TokenType.LIKE,
        TokenType.FROM,
        TokenType.IN,
        # Neo4j-specific: E is Euler's number keyword but also common variable name
        TokenType.E,
        # --- GQL pre-reserved words (unused by any parser production) ---
        TokenType.ABSTRACT,
        TokenType.AGGREGATE,
        TokenType.AGGREGATES,
        TokenType.ALTER,
        TokenType.CATALOG,
        TokenType.CLEAR,
        TokenType.CLONE,
        TokenType.CURRENT_ROLE,
        TokenType.CURRENT_USER,
        TokenType.DATA,
        TokenType.DIRECTORY,
        TokenType.DRYRUN,
        TokenType.EXACT,
        TokenType.FUNCTION,
        TokenType.GQLSTATUS,
        TokenType.GRANT,
        TokenType.INSTANT,
        TokenType.INFINITY,
        TokenType.NUMBER,
        TokenType.NUMERIC,
        TokenType.ON,
        TokenType.OPEN,
        TokenType.PARTITION,
        TokenType.PROCEDURE,
        TokenType.PRODUCT,
        TokenType.PROJECT,
        TokenType.QUERY,
        TokenType.RECORDS,
        TokenType.REFERENCE,
        TokenType.RENAME,
        TokenType.REVOKE,
        # NOT SUBSTRING — it is used as a function keyword (SUBSTRING(...))
        # and would cause ambiguity in expression contexts.
        TokenType.SYSTEM_USER,
        TokenType.TEMPORAL,
        TokenType.UNIQUE,
        TokenType.UNIT,
        TokenType.WHITESPACE,
        # --- GQL reserved words (unused standalone — only consumed via compound tokens) ---
        TokenType.ASC,  # ASCENDING
        TokenType.BIG,
        TokenType.BY,
        TokenType.CLOSE,
        TokenType.CURRENT_GRAPH,  # CURRENT_PROPERTY_GRAPH
        TokenType.DESC,  # DESCENDING
        TokenType.HOME_GRAPH,  # HOME_PROPERTY_GRAPH
        TokenType.INT8,  # INTEGER8
        TokenType.INT16,  # INTEGER16
        TokenType.INT32,  # INTEGER32
        TokenType.INT64,  # INTEGER64
        TokenType.INT128,  # INTEGER128
        TokenType.INT256,  # INTEGER256
        TokenType.NULLS,
        TokenType.ORDER,
        TokenType.PRECISION,
        TokenType.RESET,
        TokenType.SESSION,
        TokenType.SIGNED,
        TokenType.SMALL,
        TokenType.UNSIGNED,
        TokenType.VARIABLE,
    }

    # Cypher uses backslash escapes: \', \", \\, \n, \t, etc.
    UNESCAPED_SEQUENCES: t.ClassVar[dict[str, str]] = {
        "\\'": "'",
        '\\"': '"',
    }

    class Lexer(BaseLexer):
        # Cypher uses // and /* */ comments (no -- comments)
        COMMENTS: t.ClassVar[list[str | tuple[str, str]]] = ["//", ("/*", "*/")]
        # Cypher strings use backslash as escape character (in addition to quote doubling)
        STRING_ESCAPES: t.ClassVar[list[str]] = ["'", "\\"]

        KEYWORDS: t.ClassVar[dict[str, t.Any]] = {
            **BaseLexer.KEYWORDS,
            # Cypher-specific keywords
            "CONSTRAINT": TokenType.CONSTRAINT,
            "CONTAINS": TokenType.CONTAINS,
            "CSV": TokenType.CSV,
            "ENDS": TokenType.ENDS,
            "EXPLAIN": TokenType.EXPLAIN,
            "FIELDTERMINATOR": TokenType.FIELDTERMINATOR,
            "FOREACH": TokenType.FOREACH,
            "HEADERS": TokenType.HEADERS,
            "INDEX": TokenType.INDEX,
            "KEY": TokenType.KEY,
            "KEYS": TokenType.KEYS,
            "NODES": TokenType.NODES,
            "RELATIONSHIPS": TokenType.RELATIONSHIPS,
            "LOAD": TokenType.LOAD,
            "MERGE": TokenType.MERGE,
            "NONE": TokenType.NONE_KW,
            "PROFILE": TokenType.PROFILE,
            "REDUCE": TokenType.REDUCE,
            "REQUIRE": TokenType.REQUIRE,
            "ROUND": TokenType.ROUND,
            "ROWS": TokenType.ROWS,
            "SINGLE": TokenType.SINGLE,
            "STARTS": TokenType.STARTS,
            "TRANSACTIONS": TokenType.TRANSACTIONS,
            "UNWIND": TokenType.UNWIND,
            # Single-word Cypher temporal keywords
            "LOCALDATETIME": TokenType.LOCAL_DATETIME,
            "LOCALTIME": TokenType.LOCAL_TIME,
            "DATETIME": TokenType.DATETIME,
            # Cypher functions
            "PROPERTIES": TokenType.PROPERTIES,
            "RANGE": TokenType.RANGE,
            "TOBOOLEAN": TokenType.TOBOOLEAN,
            "TOINTEGER": TokenType.TOINTEGER,
            "TOFLOAT": TokenType.TOFLOAT,
            "TOSTRING": TokenType.TOSTRING,
            "TYPE": TokenType.TYPE,
            # REVERSE is kept as keyword (base GQL lexer token)
            # Operators
            "=~": TokenType.TILDE_EQUALS,
            # Cypher double-dash arrows (abbreviated edge patterns)
            "<-->": TokenType.LEFT_MINUS_RIGHT,  # Cypher <--> = GQL <-> (bidirectional)
            "-->": TokenType.RIGHT_ARROW,  # Cypher --> = GQL ->
            "<--": TokenType.LEFT_ARROW,  # Cypher <-- = GQL <-
            "--": TokenType.MINUS_SIGN,  # Cypher -- = GQL - (undirected)
        }
        # Remove GQL COLLECT_LIST keyword, add Cypher COLLECT (openCypher grammar)
        KEYWORDS.pop("COLLECT_LIST")
        KEYWORDS["COLLECT"] = TokenType.COLLECT_LIST

        # Cypher uses ^ for exponentiation (openCypher grammar: <circumflex>)
        SINGLE_TOKENS: t.ClassVar[dict[str, t.Any]] = {
            **BaseLexer.SINGLE_TOKENS,
            "^": TokenType.CARET,
        }

        def _scan_number(self) -> None:
            """Override to handle double-period guard for slice syntax.

            When scanning a decimal point, if the next char is also ``.``,
            stop the number before the first ``.`` so that ``1..3`` scans
            as ``1`` + ``..`` + ``3`` instead of ``1.`` + ``.3``.
            """
            # Check for radix prefix (0x, 0o, 0b) — delegate to base
            if self._char == "0" and self._current < self.size:
                next_char = self._peek.lower()
                if next_char in ("x", "o", "b"):
                    super()._scan_number()
                    return

            # Decimal/float/scientific scanning with double-period guard
            decimal = self._char == "."
            scientific = 0

            while True:
                if self._peek.isdigit():
                    self._advance()
                elif self._peek == "." and not decimal:
                    # Guard: don't consume '.' if next is also '.' (slice syntax 1..3)
                    if self._current + 1 < self.size and self.query[self._current + 1] == ".":
                        break
                    decimal = True
                    self._advance()
                elif self._peek in ("-", "+") and scientific == 1:
                    scientific += 1
                    self._advance()
                elif self._peek.upper() == "E" and not scientific:
                    scientific += 1
                    self._advance()
                elif self._peek == "_" and self.dialect.NUMBERS_CAN_BE_UNDERSCORE_SEPARATED:
                    prev_is_digit = self._char.isdigit()
                    next_is_digit = (
                        self._current + 1 < self.size and self.query[self._current + 1].isdigit()
                    )
                    if prev_is_digit and next_is_digit:
                        self._advance()
                    else:
                        from graphglot.error import TokenError

                        raise TokenError(
                            f"Invalid number literal: '{self._text}' "
                            f"(line {self._line}, col {self._current})",
                            line=self._line,
                            col=self._current,
                        )
                else:
                    break

            # Check for numeric literal suffix
            if self._peek and self._peek.lower() in ("m", "f", "d"):
                suffix = self._peek.lower()
                if suffix == "m":
                    if scientific:
                        self.require_feature(F.GL06)
                    else:
                        self.require_feature(F.GL05)
                else:
                    if suffix == "f":
                        self.require_feature(F.GL09)
                    else:
                        self.require_feature(F.GL10)
                    if scientific:
                        self.require_feature(F.GL08)
                    else:
                        self.require_feature(F.GL07)
                self._advance()

            self._add(TokenType.NUMBER)

    class Parser(BaseParser):
        FUNCTIONS: t.ClassVar[dict[str, type[f.Func]]] = _CYPHER_FUNCTIONS

        PARSERS: t.ClassVar[dict[t.Any, t.Any]] = {
            **BaseParser.PARSERS,
            # Cypher AST types
            StringMatchPredicate: _parse_string_match_predicate,
            InPredicate: _parse_in_predicate,
            RegexMatchPredicate: _parse_regex_match_predicate,
            ListPredicateFunction: _parse_list_predicate_function,
            MergeClause: _parse_merge_clause,
            CreateClause: _parse_create_clause,
            QueryPrefix: _parse_query_prefix,
            CreateIndex: _parse_create_index,
            DropIndex: _parse_drop_index,
            CreateConstraint: _parse_create_constraint,
            DropConstraint: _parse_drop_constraint,
            CypherPatternComprehension: _parse_pattern_comprehension,
            CypherPatternPredicate: _parse_cypher_pattern_predicate,
            # Override GQL parsers to include Cypher extensions
            ast.ValueExpression: _parse_cypher_value_expression,
            ast.SimpleCase: _parse_cypher_simple_case,
            ast.Field: _parse_cypher_field,
            ast.LabelSetSpecification: _parse_cypher_label_set_specification,
            ast.IsLabelExpression: _parse_cypher_is_label_expression,
            ast.SetQuantifier: _parse_cypher_set_quantifier,
            ast.GqlProgram: _parse_cypher_gql_program,
            ast.GeneralParameterReference: _parse_cypher_general_parameter_reference,
            ast.YieldClause: _parse_cypher_yield_clause,
            ast.BooleanFactor: _parse_cypher_boolean_factor,
            ast.BooleanTest: _parse_cypher_boolean_test,
            ast.PrimitiveQueryStatement: _parse_cypher_primitive_query_statement,
            ast.PrimitiveCatalogModifyingStatement: _parse_cypher_catalog_statement,
            ast.ListValueConstructorByEnumeration: _parse_cypher_list_or_comprehension,
            ast.CommonValueExpression: _parse_cypher_common_value_expression,
            ast.DateFunction: _parse_cypher_date_function,
            ast.TimeFunction: _parse_cypher_time_function,
            ast.DatetimeFunction: _parse_cypher_datetime_function,
            ast.LocaldatetimeFunction: _parse_cypher_localdatetime_function,
            ast.LocaltimeFunction: _parse_cypher_localtime_function,
            ast.DurationFunction: _parse_cypher_duration_function,
            ast.DatetimeValueFunction: _parse_cypher_datetime_value_function,
            ast.DurationValueFunction: _parse_cypher_duration_value_function,
            # Swap VEP/function ordering so non-reserved temporal keywords
            # are not greedily consumed as identifiers (Plan 036).
            ast.DatetimePrimary: _parse_cypher_datetime_primary,
            ast.DurationPrimary: _parse_cypher_duration_primary,
            CypherTemporalMethod: _parse_cypher_temporal_method,
            # Variable-length path support (Plan 039)
            ast.ElementPatternFiller: _parse_cypher_element_pattern_filler,
            ast.PathFactor: _parse_cypher_path_factor,
            # CALL procedure override (Plan 041)
            ast.NamedProcedureCall: _parse_cypher_named_procedure_call,
            # Multi-label REMOVE/SET (Plan 041)
            ast.RemoveItemList: _parse_cypher_remove_item_list,
            ast.SetItemList: _parse_cypher_set_item_list,
            # Label expressions: colon as conjunction (a:A:B), pipe lookahead
            ast.LabelExpression: _parse_cypher_label_expression,
            ast.LabelTerm: _parse_cypher_label_term,
            # SKIP/LIMIT with expressions and parameters
            ast.OffsetClause: _parse_cypher_offset_clause,
            ast.LimitClause: _parse_cypher_limit_clause,
            # Special syntax parsers
            CypherReduce: _parse_cypher_reduce,
        }

    class Generator(BaseGenerator):
        GENERATORS: t.ClassVar[dict[t.Any, t.Any]] = {
            **BaseGenerator.GENERATORS,
            # AST overrides — GQL types with Cypher-specific generation
            ast.CharacterStringLiteral: _generate_cypher_string_literal,
            ast.CastSpecification: _generate_cypher_cast_specification,
            ast.IsLabelExpression: _generate_cypher_is_label_expression,
            ast.LabelTerm: _generate_cypher_label_term,
            ast.AbbreviatedEdgePattern: _generate_cypher_abbreviated_edge,
            ast.ModulusExpression: _generate_cypher_modulus,
            ast.PowerFunction: _generate_cypher_power,
            ast.ForStatement: _generate_unwind_statement,
            ast.DateFunction: _generate_cypher_date_function,
            ast.TimeFunction: _generate_cypher_time_function,
            ast.DatetimeFunction: _generate_cypher_datetime_function,
            ast.LocaldatetimeFunction: _generate_cypher_localdatetime_function,
            ast.LocaltimeFunction: _generate_cypher_localtime_function,
            ast.DurationFunction: _generate_cypher_duration_function,
            ast.QuantifiedPathPrimary: _generate_cypher_quantified_path_primary,
            ast.BinarySetFunction: _generate_cypher_binary_set_function,
            ast.NamedProcedureCall: _generate_cypher_named_procedure_call,
            ast.YieldClause: _generate_cypher_yield_clause,
            ast.LabeledPredicate: _generate_cypher_labeled_predicate,
            ast.RemoveStatement: _generate_cypher_remove_statement,
            ast.SetStatement: _generate_cypher_set_statement,
            # Cypher-specific expression types
            StringMatchPredicate: _generate_string_match_predicate,
            InPredicate: _generate_in_predicate,
            RegexMatchPredicate: _generate_regex_match_predicate,
            ListComprehension: _generate_list_comprehension,
            ListPredicateFunction: _generate_list_predicate_function,
            MergeClause: _generate_merge_clause,
            CreateClause: _generate_create_clause,
            QueryPrefix: _generate_query_prefix,
            CreateIndex: _generate_create_index,
            DropIndex: _generate_drop_index,
            CreateConstraint: _generate_create_constraint,
            DropConstraint: _generate_drop_constraint,
            CypherSubscriptExpression: _generate_cypher_subscript,
            CypherSimpleCase: _generate_cypher_simple_case,
            CypherWhenClause: _generate_cypher_when_clause,
            CypherSliceExpression: _generate_cypher_slice,
            CypherPatternComprehension: _generate_cypher_pattern_comprehension,
            CypherPatternPredicate: _generate_cypher_pattern_predicate,
            CypherPredicateComparison: _generate_cypher_predicate_comparison,
            CypherChainedComparison: _generate_cypher_chained_comparison,
            CypherWithStatement: _generate_cypher_with_statement,
            CypherTemporalCast: _generate_cypher_temporal_cast,
            CypherTemporalMethod: _generate_cypher_temporal_method,
            ast.DatetimeSubtraction: _generate_cypher_datetime_subtraction,
            CypherSetAllFromExprItem: _generate_cypher_set_all_from_expr_item,
            CypherSetMapAppendItem: _generate_cypher_set_map_append_item,
            CypherSetPropertyFromExprItem: _generate_cypher_set_property_from_expr_item,
            CypherReduce: _generate_cypher_reduce,
            # Per-subclass Func generators (auto-derived from FUNCTIONS)
            **func_generators(_CYPHER_FUNCTIONS),
        }
