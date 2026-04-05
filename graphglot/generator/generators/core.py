"""Generator functions for core expressions (GqlProgram, Statement, Identifier, etc.)."""

from __future__ import annotations

import functools
import typing as t

from graphglot import ast
from graphglot.generator.fragment import Fragment
from graphglot.generator.registry import generates

if t.TYPE_CHECKING:
    from graphglot.dialect.base import Dialect
    from graphglot.generator.base import Generator


@generates(ast.GqlProgram)
def generate_gql_program(gen: Generator, expr: ast.GqlProgram) -> Fragment:
    inner = expr.gql_program
    if isinstance(inner, ast.GqlProgram._ProgramActivitySessionCloseCommand):
        parts = [gen.dispatch(inner.program_activity)]
        if inner.session_close_command:
            parts.append(gen.dispatch(inner.session_close_command))
        return gen.seq(*parts)
    else:
        # SessionCloseCommand
        return gen.dispatch(inner)


@generates(ast.SessionActivity)
def generate_session_activity(gen: Generator, expr: ast.SessionActivity) -> Fragment:
    inner = expr.session_activity
    if isinstance(inner, list):
        # list[SessionResetCommand]
        return gen.join([gen.dispatch(cmd) for cmd in inner], sep=" ")
    else:
        # _ListSessionSetCommandListSessionResetCommand
        parts = [gen.dispatch(cmd) for cmd in inner.list_session_set_command]
        if inner.list_session_reset_command:
            parts.extend([gen.dispatch(cmd) for cmd in inner.list_session_reset_command])
        return gen.join(parts, sep=" ")


@generates(ast.TransactionActivity)
def generate_transaction_activity(gen: Generator, expr: ast.TransactionActivity) -> Fragment:
    inner = expr.transaction_activity
    if isinstance(
        inner,
        ast.TransactionActivity._StartTransactionCommandProcedureSpecificationEndTransactionCommand,
    ):
        parts = [gen.dispatch(inner.start_transaction_command)]
        if inner.procedure_specification_end_transaction_command:
            ps_etc = inner.procedure_specification_end_transaction_command
            parts.append(gen.dispatch(ps_etc.procedure_specification))
            if ps_etc.end_transaction_command:
                parts.append(gen.dispatch(ps_etc.end_transaction_command))
        return gen.seq(*parts)
    elif isinstance(inner, ast.TransactionActivity._ProcedureSpecificationEndTransactionCommand):
        parts = [gen.dispatch(inner.procedure_specification)]
        if inner.end_transaction_command:
            parts.append(gen.dispatch(inner.end_transaction_command))
        return gen.seq(*parts)
    else:
        # EndTransactionCommand
        return gen.dispatch(inner)


@generates(ast.Identifier)
def generate_identifier(gen: Generator, expr: ast.Identifier) -> Fragment:
    name = expr.name
    # Quote all identifiers unconditionally when option is set
    if gen.opts.get("quote_identifiers"):
        escaped = name.replace("`", "``")
        return Fragment(f"`{escaped}`")
    # Check if identifier needs to be quoted (contains special chars or is a keyword)
    if name and name.isidentifier() and not _is_reserved_word(name, gen.dialect):
        return Fragment(name)
    # Otherwise quote it with backticks
    escaped = name.replace("`", "``")
    return Fragment(f"`{escaped}`")


@generates(ast.BindingVariableReference)
def generate_binding_variable_reference(
    gen: Generator, expr: ast.BindingVariableReference
) -> Fragment:
    return gen.dispatch(expr.binding_variable)


@generates(ast.PropertyName)
def generate_property_name(gen: Generator, expr: ast.PropertyName) -> Fragment:
    return gen.dispatch(expr.identifier)


@functools.cache
def _get_reserved_words(dialect_class: type[Dialect] | None) -> frozenset[str]:
    """Compute the set of reserved keyword strings for a dialect.

    Reserved = lexer keywords minus dialect NON_RESERVED_WORDS, filtered to
    single-word identifier strings (excludes operators like ``||``, ``->``).
    """
    from graphglot.dialect.base import Dialect as _Dialect

    cls: type[Dialect] = dialect_class if dialect_class is not None else _Dialect

    lexer_class = cls.lexer_class
    non_reserved = cls.NON_RESERVED_WORDS

    return frozenset(
        word.upper()
        for word, tt in lexer_class.KEYWORDS.items()
        if tt not in non_reserved and word.isidentifier()
    )


def _is_reserved_word(name: str, dialect: Dialect | None = None) -> bool:
    """Check if a name is a reserved keyword in the given dialect."""
    dialect_class = type(dialect) if dialect is not None else None
    return name.upper() in _get_reserved_words(dialect_class)


@generates(ast.NextStatement)
def generate_next_statement(gen: Generator, expr: ast.NextStatement) -> Fragment:
    parts: list[str | Fragment] = ["NEXT"]
    if expr.yield_clause:
        parts.append(gen.dispatch(expr.yield_clause))
    parts.append(gen.dispatch(expr.statement))
    return gen.seq(*parts, sep=gen.sep())


@generates(ast.CompositeQueryExpression)
def generate_composite_query_expression(
    gen: Generator, expr: ast.CompositeQueryExpression
) -> Fragment:
    parts = [gen.dispatch(expr.left_composite_query_primary)]
    if expr.query_conjunction_elements:
        for elem in expr.query_conjunction_elements:
            parts.append(gen.dispatch(elem.query_conjunction))
            parts.append(gen.dispatch(elem.composite_query_primary))
    return gen.seq(*parts, sep=gen.sep())


@generates(ast.QueryConjunction)
def generate_query_conjunction(gen: Generator, expr: ast.QueryConjunction) -> Fragment:
    inner = expr.query_conjunction
    if isinstance(inner, ast.SetOperator):
        return gen.dispatch(inner)
    else:
        return Fragment("OTHERWISE")


@generates(ast.SetOperator)
def generate_set_operator(gen: Generator, expr: ast.SetOperator) -> Fragment:
    keyword = expr.set_operator_type.name  # UNION, INTERSECT, EXCEPT
    if expr.set_quantifier:
        sq = gen.dispatch(expr.set_quantifier)
        return gen.seq(keyword, sq)
    return Fragment(keyword)


@generates(ast.FocusedLinearQueryStatement)
def generate_focused_linear_query_statement(
    gen: Generator, expr: ast.FocusedLinearQueryStatement
) -> Fragment:
    inner = expr.focused_linear_query_statement
    if isinstance(
        inner,
        ast.FocusedLinearQueryStatement._ListFocusedLinearQueryStatementPartFocusedLinearQueryAndPrimitiveResultStatementPart,
    ):
        parts = []
        if inner.list_focused_linear_query_statement_part:
            for part in inner.list_focused_linear_query_statement_part:
                parts.append(gen.dispatch(part))
        parts.append(gen.dispatch(inner.focused_linear_query_and_primitive_result_statement_part))
        return gen.seq(*parts, sep=gen.sep())
    elif isinstance(inner, ast.FocusedPrimitiveResultStatement):
        return gen.seq(
            gen.dispatch(inner.use_graph_clause),
            gen.dispatch(inner.primitive_result_statement),
            sep=gen.sep(),
        )
    elif isinstance(inner, ast.FocusedNestedQuerySpecification):
        return gen.seq(
            gen.dispatch(inner.use_graph_clause),
            gen.dispatch(inner.nested_query_specification),
            sep=gen.sep(),
        )
    else:
        # SelectStatement
        return gen.dispatch(inner)


@generates(ast.FocusedLinearQueryStatementPart)
def generate_focused_linear_query_statement_part(
    gen: Generator, expr: ast.FocusedLinearQueryStatementPart
) -> Fragment:
    return gen.seq(
        gen.dispatch(expr.use_graph_clause),
        gen.dispatch(expr.simple_linear_query_statement),
        sep=gen.sep(),
    )


@generates(ast.FocusedLinearQueryAndPrimitiveResultStatementPart)
def generate_focused_linear_query_and_primitive_result_statement_part(
    gen: Generator, expr: ast.FocusedLinearQueryAndPrimitiveResultStatementPart
) -> Fragment:
    return gen.seq(
        gen.dispatch(expr.use_graph_clause),
        gen.dispatch(expr.simple_linear_query_statement),
        gen.dispatch(expr.primitive_result_statement),
        sep=gen.sep(),
    )


@generates(ast.AmbientLinearQueryStatement)
def generate_ambient_linear_query_statement(
    gen: Generator, expr: ast.AmbientLinearQueryStatement
) -> Fragment:
    inner = expr.ambient_linear_query_statement
    if isinstance(
        inner, ast.AmbientLinearQueryStatement._SimpleLinearQueryStatementPrimitiveResultStatement
    ):
        parts = []
        if inner.simple_linear_query_statement:
            parts.append(gen.dispatch(inner.simple_linear_query_statement))
        parts.append(gen.dispatch(inner.primitive_result_statement))
        return gen.seq(*parts, sep=gen.sep())
    else:
        # NestedQuerySpecification
        return gen.dispatch(inner)


@generates(ast.SimpleLinearQueryStatement)
def generate_simple_linear_query_statement(
    gen: Generator, expr: ast.SimpleLinearQueryStatement
) -> Fragment:
    return gen.join(
        [gen.dispatch(stmt) for stmt in expr.list_simple_query_statement], sep=gen.sep()
    )


@generates(ast.PrimitiveResultStatement)
def generate_primitive_result_statement(
    gen: Generator, expr: ast.PrimitiveResultStatement
) -> Fragment:
    inner = expr.primitive_result_statement
    if isinstance(inner, ast.PrimitiveResultStatement._ReturnStatementOrderByAndPageStatement):
        parts = [gen.dispatch(inner.return_statement)]
        if inner.order_by_and_page_statement:
            parts.append(gen.dispatch(inner.order_by_and_page_statement))
        return gen.seq(*parts, sep=gen.sep())
    elif isinstance(inner, ast.PrimitiveResultStatement._Finish):
        return Fragment("FINISH")
    else:
        return gen.dispatch(inner)


@generates(ast.NestedProcedureSpecification)
def generate_nested_procedure_specification(
    gen: Generator, expr: ast.NestedProcedureSpecification
) -> Fragment:
    return gen.braces(gen.dispatch(expr.procedure_specification))


@generates(ast.ProcedureBody)
def generate_procedure_body(gen: Generator, expr: ast.ProcedureBody) -> Fragment:
    parts = []
    if expr.at_schema_clause:
        parts.append(gen.dispatch(expr.at_schema_clause))
    if expr.binding_variable_definition_block:
        parts.append(gen.dispatch(expr.binding_variable_definition_block))
    parts.append(gen.dispatch(expr.statement_block))
    return gen.seq(*parts)


@generates(ast.StatementBlock)
def generate_statement_block(gen: Generator, expr: ast.StatementBlock) -> Fragment:
    parts = [gen.dispatch(expr.statement)]
    if expr.list_next_statement:
        for next_stmt in expr.list_next_statement:
            parts.append(gen.dispatch(next_stmt))
    return gen.seq(*parts, sep=gen.sep())


@generates(ast.BindingVariableDefinitionBlock)
def generate_binding_variable_definition_block(
    gen: Generator, expr: ast.BindingVariableDefinitionBlock
) -> Fragment:
    return gen.join([gen.dispatch(defn) for defn in expr.list_binding_variable_definition], sep=" ")


@generates(ast.GraphVariableDefinition)
def generate_graph_variable_definition(
    gen: Generator, expr: ast.GraphVariableDefinition
) -> Fragment:
    parts: list[str | Fragment] = ["GRAPH", gen.dispatch(expr.binding_variable)]
    parts.append(gen.dispatch(expr.opt_typed_graph_initializer))
    return gen.seq(*parts)


@generates(ast.BindingTableVariableDefinition)
def generate_binding_table_variable_definition(
    gen: Generator, expr: ast.BindingTableVariableDefinition
) -> Fragment:
    return gen.seq(
        "BINDING",
        "TABLE",
        gen.dispatch(expr.binding_variable),
        gen.dispatch(expr.opt_typed_binding_table_initializer),
    )


@generates(ast.ValueVariableDefinition)
def generate_value_variable_definition(
    gen: Generator, expr: ast.ValueVariableDefinition
) -> Fragment:
    return gen.seq(
        "VALUE", gen.dispatch(expr.binding_variable), gen.dispatch(expr.opt_typed_value_initializer)
    )
