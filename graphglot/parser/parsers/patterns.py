from __future__ import annotations

import typing as t

from graphglot import ast
from graphglot.lexer import TokenType
from graphglot.parser.registry import parses

if t.TYPE_CHECKING:
    from graphglot.parser import Parser


@parses(ast.GraphPattern)
def parse_graph_pattern(parser: Parser) -> ast.GraphPattern:
    (
        match_mode,
        path_pattern_list,
        keep_clause,
        graph_pattern_where_clause,
    ) = parser.seq(
        parser.opt(parser.get_parser(ast.MatchMode)),
        parser.get_parser(ast.PathPatternList),
        parser.opt(parser.get_parser(ast.KeepClause)),
        parser.opt(parser.get_parser(ast.GraphPatternWhereClause)),
    )
    return ast.GraphPattern(
        match_mode=match_mode,
        path_pattern_list=path_pattern_list,
        keep_clause=keep_clause,
        graph_pattern_where_clause=graph_pattern_where_clause,
    )


@parses(ast.PathPattern)
def parse_path_pattern(parser: Parser) -> ast.PathPattern:
    (
        path_variable_declaration,
        path_pattern_prefix,
        path_pattern_expression,
    ) = parser.seq(
        parser.opt(parser.get_parser(ast.PathVariableDeclaration)),
        parser.opt(parser.get_parser(ast.PathPatternPrefix)),
        parser.get_parser(ast.PathPatternExpression),
    )

    return ast.PathPattern(
        path_variable_declaration=path_variable_declaration,
        path_pattern_prefix=path_pattern_prefix,
        path_pattern_expression=path_pattern_expression,
    )


@parses(ast.InsertPathPattern)
def parse_insert_path_pattern(parser: Parser) -> ast.InsertPathPattern:
    def _parse__insert_edge_pattern_insert_node_pattern(
        parser: Parser,
    ) -> ast.InsertPathPattern._InsertEdgePatternInsertNodePattern:
        (
            insert_edge_pattern,
            insert_node_pattern,
        ) = parser.seq(
            parser.get_parser(ast.InsertEdgePattern),
            parser.get_parser(ast.InsertNodePattern),
        )
        return ast.InsertPathPattern._InsertEdgePatternInsertNodePattern(
            insert_edge_pattern=insert_edge_pattern,
            insert_node_pattern=insert_node_pattern,
        )

    (
        insert_node_pattern,
        list_insert_edge_pattern_insert_node_pattern,
    ) = parser.seq(
        parser.get_parser(ast.InsertNodePattern),
        parser.opt(
            lambda parser: parser.seq(
                parser.list_(_parse__insert_edge_pattern_insert_node_pattern, None)
            )[0]
        ),
    )
    return ast.InsertPathPattern(
        insert_node_pattern=insert_node_pattern,
        list_insert_edge_pattern_insert_node_pattern=list_insert_edge_pattern_insert_node_pattern,
    )


@parses(ast.InsertNodePattern)
def parse_insert_node_pattern(parser: Parser) -> ast.InsertNodePattern:
    (
        _,
        insert_element_pattern_filler,
        _,
    ) = parser.seq(
        TokenType.LEFT_PAREN,
        parser.opt(parser.get_parser(ast.InsertElementPatternFiller)),
        TokenType.RIGHT_PAREN,
    )
    return ast.InsertNodePattern(
        insert_element_pattern_filler=insert_element_pattern_filler,
    )


@parses(ast.InsertEdgePattern)
def parse_insert_edge_pattern(parser: Parser) -> ast.InsertEdgePattern:
    candidates_insert_edge_pattern = (
        parser.get_parser(ast.InsertEdgePointingLeft),
        parser.get_parser(ast.InsertEdgePointingRight),
        parser.get_parser(ast.InsertEdgeUndirected),
    )
    (result,) = parser.seq(candidates_insert_edge_pattern)
    return result


@parses(ast.NodeTypePattern)
def parse_node_type_pattern(parser: Parser) -> ast.NodeTypePattern:
    def _parse__node_synonym_type_node_type_name(
        parser: Parser,
    ) -> ast.NodeTypePattern._TypeNodeTypeName:
        (
            _,
            type,
            node_type_name,
        ) = parser.seq(
            TokenType.NODE,
            parser.opt(TokenType.TYPE),
            parser.get_parser(ast.NodeTypeName),
        )
        return ast.NodeTypePattern._TypeNodeTypeName(
            type=bool(type),
            node_type_name=node_type_name,
        )

    (
        node_synonym_type_node_type_name,
        _,
        local_node_type_alias,
        node_type_filler,
        _,
    ) = parser.seq(
        parser.opt(_parse__node_synonym_type_node_type_name),
        TokenType.LEFT_PAREN,
        parser.opt(parser.get_parser(ast.LocalNodeTypeAlias)),
        parser.opt(parser.get_parser(ast.NodeTypeFiller)),
        TokenType.RIGHT_PAREN,
    )
    return ast.NodeTypePattern(
        node_synonym_type_node_type_name=node_synonym_type_node_type_name,
        local_node_type_alias=local_node_type_alias,
        node_type_filler=node_type_filler,
    )


@parses(ast.EdgeTypePattern)
def parse_edge_type_pattern(parser: Parser) -> ast.EdgeTypePattern:
    def _parse__edge_type_pattern_prefix(
        parser: Parser,
    ) -> ast.EdgeTypePattern._EdgeTypePatternPrefix:
        (
            edge_kind_token,
            _,
            type_,
            edge_type_name,
        ) = parser.seq(
            parser.opt({TokenType.DIRECTED, TokenType.UNDIRECTED}),
            TokenType.EDGE,
            parser.opt(TokenType.TYPE),
            parser.get_parser(ast.EdgeTypeName),
        )
        edge_kind = None
        if edge_kind_token:
            edge_kind = (
                ast.EdgeKind.DIRECTED
                if edge_kind_token.token_type == TokenType.DIRECTED
                else ast.EdgeKind.UNDIRECTED
            )
        return ast.EdgeTypePattern._EdgeTypePatternPrefix(
            edge_kind=edge_kind,
            type_=bool(type_),
            edge_type_name=edge_type_name,
        )

    (
        prefix,
        edge_type_pattern,
    ) = parser.seq(
        parser.opt(_parse__edge_type_pattern_prefix),
        (
            parser.get_parser(ast.EdgeTypePatternDirected),
            parser.get_parser(ast.EdgeTypePatternUndirected),
        ),
    )
    return ast.EdgeTypePattern(
        prefix=prefix,
        edge_type_pattern=edge_type_pattern,
    )


@parses(ast.ElementPattern)
def parse_element_pattern(parser: Parser) -> ast.ElementPattern:
    candidates_element_pattern = (
        parser.get_parser(ast.NodePattern),
        parser.get_parser(ast.EdgePattern),
    )
    (result,) = parser.seq(candidates_element_pattern)
    return result


@parses(ast.NodePattern)
def parse_node_pattern(parser: Parser) -> ast.NodePattern:
    (
        _,
        element_pattern_filler,
        _,
    ) = parser.seq(
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.ElementPatternFiller),
        TokenType.RIGHT_PAREN,
    )
    return ast.NodePattern(
        element_pattern_filler=element_pattern_filler,
    )


@parses(ast.EdgePattern)
def parse_edge_pattern(parser: Parser) -> ast.EdgePattern:
    candidates_edge_pattern = (
        parser.get_parser(ast.FullEdgePattern),
        parser.get_parser(ast.AbbreviatedEdgePattern),
    )
    (result,) = parser.seq(candidates_edge_pattern)
    return result


@parses(ast.FullEdgePattern)
def parse_full_edge_pattern(parser: Parser) -> ast.FullEdgePattern:
    candidates_full_edge_pattern = (
        parser.get_parser(ast.FullEdgePointingLeft),
        parser.get_parser(ast.FullEdgeUndirected),
        parser.get_parser(ast.FullEdgePointingRight),
        parser.get_parser(ast.FullEdgeLeftOrUndirected),
        parser.get_parser(ast.FullEdgeUndirectedOrRight),
        parser.get_parser(ast.FullEdgeLeftOrRight),
        parser.get_parser(ast.FullEdgeAnyDirection),
    )
    (result,) = parser.seq(candidates_full_edge_pattern)
    return result


@parses(ast.AbbreviatedEdgePattern)
def parse_abbreviated_edge_pattern(parser: Parser) -> ast.AbbreviatedEdgePattern:
    token_set = {
        TokenType.LEFT_ARROW,
        TokenType.TILDE,
        TokenType.RIGHT_ARROW,
        TokenType.LEFT_ARROW_TILDE,
        TokenType.TILDE_RIGHT_ARROW,
        TokenType.LEFT_MINUS_RIGHT,
        TokenType.MINUS_SIGN,
    }
    (pattern_token,) = parser.seq(token_set)

    match pattern_token.token_type:
        case TokenType.LEFT_ARROW:
            pattern = ast.AbbreviatedEdgePattern.PatternType.LEFT_ARROW
        case TokenType.TILDE:
            pattern = ast.AbbreviatedEdgePattern.PatternType.TILDE
        case TokenType.RIGHT_ARROW:
            pattern = ast.AbbreviatedEdgePattern.PatternType.RIGHT_ARROW
        case TokenType.LEFT_ARROW_TILDE:
            pattern = ast.AbbreviatedEdgePattern.PatternType.LEFT_ARROW_TILDE
        case TokenType.TILDE_RIGHT_ARROW:
            pattern = ast.AbbreviatedEdgePattern.PatternType.TILDE_RIGHT_ARROW
        case TokenType.LEFT_MINUS_RIGHT:
            pattern = ast.AbbreviatedEdgePattern.PatternType.LEFT_MINUS_RIGHT
        case TokenType.MINUS_SIGN:
            pattern = ast.AbbreviatedEdgePattern.PatternType.MINUS_SIGN

    return ast.AbbreviatedEdgePattern(pattern=pattern)
