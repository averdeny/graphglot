"""Generator functions for session and transaction commands."""

from __future__ import annotations

import typing as t

from graphglot import ast
from graphglot.generator.fragment import Fragment
from graphglot.generator.registry import generates

if t.TYPE_CHECKING:
    from graphglot.generator.base import Generator


@generates(ast.SessionSetCommand)
def generate_session_set_command(gen: Generator, expr: ast.SessionSetCommand) -> Fragment:
    return gen.seq("SESSION SET", gen.dispatch(expr.session_set_command))


@generates(ast.SessionSetSchemaClause)
def generate_session_set_schema_clause(
    gen: Generator, expr: ast.SessionSetSchemaClause
) -> Fragment:
    return gen.seq("SCHEMA", gen.dispatch(expr.schema_reference))


@generates(ast.SessionSetGraphClause)
def generate_session_set_graph_clause(gen: Generator, expr: ast.SessionSetGraphClause) -> Fragment:
    return gen.seq("GRAPH", gen.dispatch(expr.graph_expression))


@generates(ast.SessionSetTimeZoneClause)
def generate_session_set_time_zone_clause(
    gen: Generator, expr: ast.SessionSetTimeZoneClause
) -> Fragment:
    return gen.seq("TIME ZONE", gen.dispatch(expr.set_time_zone_value))


@generates(ast.SessionSetGraphParameterClause)
def generate_session_set_graph_parameter_clause(
    gen: Generator, expr: ast.SessionSetGraphParameterClause
) -> Fragment:
    return gen.seq(
        "GRAPH",
        gen.dispatch(expr.session_set_parameter_name),
        "=",
        gen.dispatch(expr.opt_typed_graph_initializer),
    )


@generates(ast.SessionSetBindingTableParameterClause)
def generate_session_set_binding_table_parameter_clause(
    gen: Generator, expr: ast.SessionSetBindingTableParameterClause
) -> Fragment:
    return gen.seq(
        "TABLE",
        gen.dispatch(expr.session_set_parameter_name),
        "=",
        gen.dispatch(expr.opt_typed_binding_table_initializer),
    )


@generates(ast.SessionSetValueParameterClause)
def generate_session_set_value_parameter_clause(
    gen: Generator, expr: ast.SessionSetValueParameterClause
) -> Fragment:
    return gen.seq(
        "VALUE",
        gen.dispatch(expr.session_set_parameter_name),
        "=",
        gen.dispatch(expr.opt_typed_value_initializer),
    )


@generates(ast.OptTypedGraphInitializer)
def generate_opt_typed_graph_initializer(
    gen: Generator, expr: ast.OptTypedGraphInitializer
) -> Fragment:
    return gen.dispatch(expr.graph_initializer)


@generates(ast.GraphInitializer)
def generate_graph_initializer(gen: Generator, expr: ast.GraphInitializer) -> Fragment:
    return gen.dispatch(expr.graph_expression)


@generates(ast.OptTypedBindingTableInitializer)
def generate_opt_typed_binding_table_initializer(
    gen: Generator, expr: ast.OptTypedBindingTableInitializer
) -> Fragment:
    return gen.dispatch(expr.binding_table_initializer)


@generates(ast.BindingTableInitializer)
def generate_binding_table_initializer(
    gen: Generator, expr: ast.BindingTableInitializer
) -> Fragment:
    return gen.dispatch(expr.binding_table_expression)


@generates(ast.OptTypedValueInitializer)
def generate_opt_typed_value_initializer(
    gen: Generator, expr: ast.OptTypedValueInitializer
) -> Fragment:
    return gen.dispatch(expr.value_initializer)


@generates(ast.ValueInitializer)
def generate_value_initializer(gen: Generator, expr: ast.ValueInitializer) -> Fragment:
    return gen.dispatch(expr.value_expression)


@generates(ast.SessionSetParameterName)
def generate_session_set_parameter_name(
    gen: Generator, expr: ast.SessionSetParameterName
) -> Fragment:
    parts: list[str | Fragment] = []
    if expr.if_not_exists:
        parts.append("IF NOT EXISTS")
    parts.append(gen.dispatch(expr.session_parameter_specification))
    return gen.seq(*parts)


@generates(ast.GeneralParameterReference)
def generate_general_parameter_reference(
    gen: Generator, expr: ast.GeneralParameterReference
) -> Fragment:
    return Fragment(f"${gen.dispatch(expr.parameter_name)}")


@generates(ast.SessionResetCommand)
def generate_session_reset_command(gen: Generator, expr: ast.SessionResetCommand) -> Fragment:
    return gen.seq("SESSION RESET", gen.dispatch(expr.session_reset_arguments))


@generates(ast.SessionResetArguments)
def generate_session_reset_arguments(gen: Generator, expr: ast.SessionResetArguments) -> Fragment:
    inner = expr.session_reset_arguments
    if isinstance(inner, ast.SessionResetArguments._AllParameters):
        if inner.all:
            return Fragment("ALL PARAMETERS")
        return Fragment("PARAMETERS")
    elif isinstance(inner, ast.SessionResetArguments._AllCharacteristics):
        if inner.all:
            return Fragment("ALL CHARACTERISTICS")
        return Fragment("CHARACTERISTICS")
    elif isinstance(inner, ast.SessionResetArguments._Schema):
        return Fragment("SCHEMA")
    elif isinstance(inner, ast.SessionResetArguments._Graph):
        return Fragment("GRAPH")
    elif isinstance(inner, ast.SessionResetArguments._TimeZone):
        return Fragment("TIME ZONE")
    elif isinstance(inner, ast.SessionResetArguments._ParameterSessionParameterSpecification):
        if inner.parameter:
            return gen.seq("PARAMETER", gen.dispatch(inner.session_parameter_specification))
        return gen.dispatch(inner.session_parameter_specification)
    else:
        return gen.dispatch(inner)


@generates(ast.SessionCloseCommand)
def generate_session_close_command(gen: Generator, expr: ast.SessionCloseCommand) -> Fragment:
    return Fragment("SESSION CLOSE")


@generates(ast.StartTransactionCommand)
def generate_start_transaction_command(
    gen: Generator, expr: ast.StartTransactionCommand
) -> Fragment:
    parts: list[str | Fragment] = ["START TRANSACTION"]
    if expr.transaction_characteristics:
        parts.append(gen.dispatch(expr.transaction_characteristics))
    return gen.seq(*parts)


@generates(ast.TransactionCharacteristics)
def generate_transaction_characteristics(
    gen: Generator, expr: ast.TransactionCharacteristics
) -> Fragment:
    return gen.join(
        [generate_transaction_mode(gen, c) for c in expr.list_transaction_mode], sep=", "
    )


@generates(ast.TransactionCharacteristics.TransactionMode)
def generate_transaction_mode(
    gen: Generator, expr: ast.TransactionCharacteristics.TransactionMode
) -> Fragment:
    if expr == ast.TransactionCharacteristics.TransactionMode.READ_ONLY:
        return Fragment("READ ONLY")
    return Fragment("READ WRITE")


@generates(ast.EndTransactionCommand)
def generate_end_transaction_command(gen: Generator, expr: ast.EndTransactionCommand) -> Fragment:
    if expr.mode == ast.EndTransactionCommand.Mode.ROLLBACK:
        return Fragment("ROLLBACK")
    return Fragment("COMMIT")


@generates(ast.LinearCatalogModifyingStatement)
def generate_linear_catalog_modifying_statement(
    gen: Generator, expr: ast.LinearCatalogModifyingStatement
) -> Fragment:
    parts = [gen.dispatch(s) for s in expr.list_simple_catalog_modifying_statement]
    return gen.seq(*parts)


@generates(ast.CreateSchemaStatement)
def generate_create_schema_statement(gen: Generator, expr: ast.CreateSchemaStatement) -> Fragment:
    parts: list[str | Fragment] = ["CREATE SCHEMA"]
    if expr.if_not_exists:
        parts.append("IF NOT EXISTS")
    parts.append(gen.dispatch(expr.catalog_schema_parent_and_name))
    return gen.seq(*parts)


@generates(ast.DropSchemaStatement)
def generate_drop_schema_statement(gen: Generator, expr: ast.DropSchemaStatement) -> Fragment:
    parts: list[str | Fragment] = ["DROP SCHEMA"]
    if expr.if_exists:
        parts.append("IF EXISTS")
    parts.append(gen.dispatch(expr.catalog_schema_parent_and_name))
    return gen.seq(*parts)


@generates(ast.CatalogSchemaParentAndName)
def generate_catalog_schema_parent_and_name(
    gen: Generator, expr: ast.CatalogSchemaParentAndName
) -> Fragment:
    path = gen.dispatch(expr.absolute_directory_path)
    name = gen.dispatch(expr.schema_name)
    return Fragment(f"{path}/{name}")


@generates(ast.AbsoluteDirectoryPath)
def generate_absolute_directory_path(gen: Generator, expr: ast.AbsoluteDirectoryPath) -> Fragment:
    return gen.dispatch(expr.simple_directory_path)


@generates(ast.AbsoluteCatalogSchemaReference)
def generate_absolute_catalog_schema_reference(
    gen: Generator, expr: ast.AbsoluteCatalogSchemaReference
) -> Fragment:
    inner = expr.absolute_catalog_schema_reference
    if isinstance(inner, ast.Solidus):
        return Fragment("/")
    path = gen.dispatch(inner.absolute_directory_path)
    name = gen.dispatch(inner.schema_name)
    return Fragment(f"{path}/{name}")


@generates(ast.RelativeCatalogSchemaReference)
def generate_relative_catalog_schema_reference(
    gen: Generator, expr: ast.RelativeCatalogSchemaReference
) -> Fragment:
    inner = expr.relative_catalog_schema_reference
    if isinstance(inner, ast.PredefinedSchemaReference):
        return gen.dispatch(inner)
    path = gen.dispatch(inner.relative_directory_path)
    name = gen.dispatch(inner.schema_name)
    return gen.seq(path, name)


@generates(ast.PredefinedSchemaReference)
def generate_predefined_schema_reference(
    gen: Generator, expr: ast.PredefinedSchemaReference
) -> Fragment:
    inner = expr.predefined_schema_reference
    if isinstance(inner, ast.PredefinedSchemaReference._HomeSchema):
        return Fragment("HOME_SCHEMA")
    elif isinstance(inner, ast.PredefinedSchemaReference._CurrentSchema):
        return Fragment("CURRENT_SCHEMA")
    else:
        return Fragment(".")


@generates(ast.RelativeDirectoryPath)
def generate_relative_directory_path(gen: Generator, expr: ast.RelativeDirectoryPath) -> Fragment:
    parts = [".."] * expr.up_levels
    result = "/".join(parts)
    if expr.simple_directory_path:
        result += "/" + str(gen.dispatch(expr.simple_directory_path))
    return Fragment(result)


@generates(ast.SimpleDirectoryPath)
def generate_simple_directory_path(gen: Generator, expr: ast.SimpleDirectoryPath) -> Fragment:
    items = "/".join(str(gen.dispatch(item)) for item in expr.items)
    return Fragment(f"/{items}")


@generates(ast.CreateGraphStatement)
def generate_create_graph_statement(gen: Generator, expr: ast.CreateGraphStatement) -> Fragment:
    mode = expr.create_mode
    parts: list[str | Fragment]
    if mode == ast.CreateGraphStatement.CreateMode.CREATE_GRAPH_IF_NOT_EXISTS:
        parts = ["CREATE PROPERTY GRAPH IF NOT EXISTS"]
    elif mode == ast.CreateGraphStatement.CreateMode.CREATE_OR_REPLACE_GRAPH:
        parts = ["CREATE OR REPLACE PROPERTY GRAPH"]
    else:
        parts = ["CREATE PROPERTY GRAPH"]
    parts.append(gen.dispatch(expr.catalog_graph_parent_and_name))
    parts.append(gen.dispatch(expr.graph_type))
    if expr.graph_source:
        parts.append(gen.dispatch(expr.graph_source))
    return gen.seq(*parts)


@generates(ast.DropGraphStatement)
def generate_drop_graph_statement(gen: Generator, expr: ast.DropGraphStatement) -> Fragment:
    parts: list[str | Fragment] = ["DROP PROPERTY GRAPH"]
    if expr.if_exists:
        parts.append("IF EXISTS")
    parts.append(gen.dispatch(expr.catalog_graph_parent_and_name))
    return gen.seq(*parts)


@generates(ast.CatalogGraphParentAndName)
def generate_catalog_graph_parent_and_name(
    gen: Generator, expr: ast.CatalogGraphParentAndName
) -> Fragment:
    parts: list[Fragment] = []
    if expr.catalog_object_parent_reference:
        parts.append(gen.dispatch(expr.catalog_object_parent_reference))
    parts.append(gen.dispatch(expr.graph_name))
    return gen.seq(*parts)


@generates(ast.CreateGraphTypeStatement)
def generate_create_graph_type_statement(
    gen: Generator, expr: ast.CreateGraphTypeStatement
) -> Fragment:
    mode = expr.create_mode
    parts: list[str | Fragment]
    if mode == ast.CreateGraphTypeStatement.CreateMode.CREATE_GRAPH_TYPE_IF_NOT_EXISTS:
        parts = ["CREATE PROPERTY GRAPH TYPE IF NOT EXISTS"]
    elif mode == ast.CreateGraphTypeStatement.CreateMode.CREATE_OR_REPLACE_GRAPH_TYPE:
        parts = ["CREATE OR REPLACE PROPERTY GRAPH TYPE"]
    else:
        parts = ["CREATE PROPERTY GRAPH TYPE"]
    parts.append(gen.dispatch(expr.catalog_graph_type_parent_and_name))
    parts.append(gen.dispatch(expr.graph_type_source))
    return gen.seq(*parts)


@generates(ast.DropGraphTypeStatement)
def generate_drop_graph_type_statement(
    gen: Generator, expr: ast.DropGraphTypeStatement
) -> Fragment:
    parts: list[str | Fragment] = ["DROP GRAPH TYPE"]
    if expr.if_exists:
        parts.append("IF EXISTS")
    parts.append(gen.dispatch(expr.catalog_graph_type_parent_and_name))
    return gen.seq(*parts)


@generates(ast.CatalogGraphTypeParentAndName)
def generate_catalog_graph_type_parent_and_name(
    gen: Generator, expr: ast.CatalogGraphTypeParentAndName
) -> Fragment:
    parts: list[Fragment] = []
    if expr.catalog_object_parent_reference:
        parts.append(gen.dispatch(expr.catalog_object_parent_reference))
    parts.append(gen.dispatch(expr.graph_type_name))
    return gen.seq(*parts)


@generates(ast.OpenGraphType)
def generate_open_graph_type(gen: Generator, expr: ast.OpenGraphType) -> Fragment:
    return Fragment("ANY PROPERTY GRAPH")


@generates(ast.OfGraphType)
def generate_of_graph_type(gen: Generator, expr: ast.OfGraphType) -> Fragment:
    return gen.dispatch(expr.of_graph_type)


@generates(ast.GraphTypeLikeGraph)
def generate_graph_type_like_graph(gen: Generator, expr: ast.GraphTypeLikeGraph) -> Fragment:
    return gen.seq("LIKE", gen.dispatch(expr.graph_expression))


@generates(ast.GraphSource)
def generate_graph_source(gen: Generator, expr: ast.GraphSource) -> Fragment:
    return gen.seq("AS COPY OF", gen.dispatch(expr.graph_expression))


@generates(ast.GraphTypeSource)
def generate_graph_type_source(gen: Generator, expr: ast.GraphTypeSource) -> Fragment:
    return gen.dispatch(expr.graph_type_source)


@generates(ast.FocusedLinearDataModifyingStatementBody)
def generate_focused_linear_data_modifying_statement_body(
    gen: Generator, expr: ast.FocusedLinearDataModifyingStatementBody
) -> Fragment:
    parts = [
        gen.dispatch(expr.use_graph_clause),
        gen.dispatch(expr.simple_linear_data_accessing_statement),
    ]
    if expr.primitive_result_statement:
        parts.append(gen.dispatch(expr.primitive_result_statement))
    return gen.seq(*parts)


@generates(ast.AmbientLinearDataModifyingStatement)
def generate_ambient_linear_data_modifying_statement(
    gen: Generator, expr: ast.AmbientLinearDataModifyingStatement
) -> Fragment:
    if isinstance(expr, ast.AmbientLinearDataModifyingStatementBody):
        return generate_ambient_linear_data_modifying_statement_body(gen, expr)
    if isinstance(expr, ast.NestedDataModifyingProcedureSpecification):
        return gen.braces(gen.dispatch(expr.data_modifying_procedure_specification))
    raise NotImplementedError(
        f"Unsupported ambient linear data-modifying statement: {type(expr).__name__}"
    )


@generates(ast.AmbientLinearDataModifyingStatementBody)
def generate_ambient_linear_data_modifying_statement_body(
    gen: Generator, expr: ast.AmbientLinearDataModifyingStatementBody
) -> Fragment:
    parts = [gen.dispatch(expr.simple_linear_data_accessing_statement)]
    if expr.primitive_result_statement:
        parts.append(gen.dispatch(expr.primitive_result_statement))
    return gen.seq(*parts)


@generates(ast.SimpleLinearDataAccessingStatement)
def generate_simple_linear_data_accessing_statement(
    gen: Generator, expr: ast.SimpleLinearDataAccessingStatement
) -> Fragment:
    return gen.join(
        [gen.dispatch(stmt) for stmt in expr.list_simple_data_accessing_statement], sep=" "
    )
