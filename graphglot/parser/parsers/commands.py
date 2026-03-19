from __future__ import annotations

import typing as t

from graphglot import ast
from graphglot.lexer import TokenType
from graphglot.parser.registry import parses, token_parser

if t.TYPE_CHECKING:
    from graphglot.parser import Parser


@parses(ast.EndTransactionCommand)
def parse_end_transaction_command(parser: Parser) -> ast.EndTransactionCommand:
    (mode_token,) = parser.seq(
        {
            TokenType.ROLLBACK,
            TokenType.COMMIT,
        }
    )
    match mode_token.token_type:
        case TokenType.ROLLBACK:
            mode = ast.EndTransactionCommand.Mode.ROLLBACK
        case TokenType.COMMIT:
            mode = ast.EndTransactionCommand.Mode.COMMIT

    return ast.EndTransactionCommand(
        mode=mode,
    )


@parses(ast.SessionSetCommand)
def parse_session_set_command(parser: Parser) -> ast.SessionSetCommand:
    candidates_session_set_command = (
        parser.get_parser(ast.SessionSetSchemaClause),
        parser.get_parser(ast.SessionSetTimeZoneClause),
        parser.get_parser(ast.SessionSetParameterClause),
        parser.get_parser(ast.SessionSetGraphClause),
    )
    (
        _,
        session_set_command,
    ) = parser.seq(
        TokenType.SESSION_SET,
        candidates_session_set_command,
    )
    return ast.SessionSetCommand(
        session_set_command=session_set_command,
    )


@parses(ast.SessionResetCommand)
def parse_session_reset_command(parser: Parser) -> ast.SessionResetCommand:
    (
        _,
        session_reset_arguments,
    ) = parser.seq(
        TokenType.SESSION_RESET,
        parser.opt(parser.get_parser(ast.SessionResetArguments)),
    )
    return ast.SessionResetCommand(
        session_reset_arguments=session_reset_arguments,
    )


parse_session_close_command = parses(ast.SessionCloseCommand)(
    token_parser(TokenType.SESSION_CLOSE, ast_type=ast.SessionCloseCommand)
)


@parses(ast.StartTransactionCommand)
def parse_start_transaction_command(parser: Parser) -> ast.StartTransactionCommand:
    (
        _,
        transaction_characteristics,
    ) = parser.seq(
        TokenType.START_TRANSACTION,
        parser.opt(parser.get_parser(ast.TransactionCharacteristics)),
    )
    return ast.StartTransactionCommand(
        transaction_characteristics=transaction_characteristics,
    )
