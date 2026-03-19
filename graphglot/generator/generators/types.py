"""Generator functions for type expressions."""

from __future__ import annotations

import typing as t

from graphglot import ast
from graphglot.generator.fragment import Fragment
from graphglot.generator.registry import generates

if t.TYPE_CHECKING:
    from graphglot.generator.base import Generator


@generates(ast.BooleanType)
def generate_boolean_type(gen: Generator, expr: ast.BooleanType) -> Fragment:
    not_null = " NOT NULL" if expr.not_null else ""
    return Fragment(f"BOOLEAN{not_null}")


@generates(ast.CharacterStringType)
def generate_character_string_type(gen: Generator, expr: ast.CharacterStringType) -> Fragment:
    inner = expr.character_string_type
    not_null = " NOT NULL" if expr.not_null else ""
    if isinstance(inner, ast.CharacterStringType._String):
        if inner.min_length and inner.max_length:
            return Fragment(
                f"STRING({gen.dispatch(inner.min_length)}, "
                f"{gen.dispatch(inner.max_length)}){not_null}"
            )
        elif inner.max_length:
            return Fragment(f"STRING({gen.dispatch(inner.max_length)}){not_null}")
        return Fragment(f"STRING{not_null}")
    elif isinstance(inner, ast.CharacterStringType._Char):
        if inner.fixed_length:
            return Fragment(f"CHAR({gen.dispatch(inner.fixed_length)}){not_null}")
        return Fragment(f"CHAR{not_null}")
    else:  # _Varchar
        if inner.max_length:
            return Fragment(f"VARCHAR({gen.dispatch(inner.max_length)}){not_null}")
        return Fragment(f"VARCHAR{not_null}")


@generates(ast.ByteStringType)
def generate_byte_string_type(gen: Generator, expr: ast.ByteStringType) -> Fragment:
    inner = expr.byte_string_type
    not_null = " NOT NULL" if expr.not_null else ""
    if isinstance(inner, ast.ByteStringType._Bytes):
        if inner.min_length and inner.max_length:
            return Fragment(
                f"BYTES({gen.dispatch(inner.min_length)}, "
                f"{gen.dispatch(inner.max_length)}){not_null}"
            )
        elif inner.max_length:
            return Fragment(f"BYTES({gen.dispatch(inner.max_length)}){not_null}")
        return Fragment(f"BYTES{not_null}")
    elif isinstance(inner, ast.ByteStringType._Binary):
        if inner.fixed_length:
            return Fragment(f"BINARY({gen.dispatch(inner.fixed_length)}){not_null}")
        return Fragment(f"BINARY{not_null}")
    else:  # _Varbinary
        if inner.max_length:
            return Fragment(f"VARBINARY({gen.dispatch(inner.max_length)}){not_null}")
        return Fragment(f"VARBINARY{not_null}")


@generates(ast.DecimalExactNumericType)
def generate_decimal_exact_numeric_type(
    gen: Generator, expr: ast.DecimalExactNumericType
) -> Fragment:
    not_null = " NOT NULL" if expr.not_null else ""
    if expr.precision_scale:
        ps = expr.precision_scale
        if ps.scale:
            return Fragment(
                f"DECIMAL({gen.dispatch(ps.precision)}, {gen.dispatch(ps.scale)}){not_null}"
            )
        return Fragment(f"DECIMAL({gen.dispatch(ps.precision)}){not_null}")
    return Fragment(f"DECIMAL{not_null}")


@generates(ast.SignedBinaryExactNumericType)
def generate_signed_binary_exact_numeric_type(
    gen: Generator, expr: ast.SignedBinaryExactNumericType
) -> Fragment:
    not_null = " NOT NULL" if expr.not_null else ""
    type_map = {
        ast.SignedBinaryExactNumericType._Int8: "INT8",
        ast.SignedBinaryExactNumericType._Int16: "INT16",
        ast.SignedBinaryExactNumericType._Int32: "INT32",
        ast.SignedBinaryExactNumericType._Int64: "INT64",
        ast.SignedBinaryExactNumericType._Int128: "INT128",
        ast.SignedBinaryExactNumericType._Int256: "INT256",
        ast.SignedBinaryExactNumericType._Smallint: "SMALLINT",
        ast.SignedBinaryExactNumericType._Bigint: "BIGINT",
    }
    for cls, name in type_map.items():
        if isinstance(expr.signed_type, cls):
            return Fragment(f"{name}{not_null}")
    # _Int with optional precision
    if isinstance(expr.signed_type, ast.SignedBinaryExactNumericType._Int):
        if expr.signed_type.precision:
            return Fragment(f"INT({gen.dispatch(expr.signed_type.precision)}){not_null}")
        return Fragment(f"INT{not_null}")
    return Fragment(f"INT{not_null}")


@generates(ast.UnsignedBinaryExactNumericType)
def generate_unsigned_binary_exact_numeric_type(
    gen: Generator, expr: ast.UnsignedBinaryExactNumericType
) -> Fragment:
    not_null = " NOT NULL" if expr.not_null else ""
    type_map = {
        ast.UnsignedBinaryExactNumericType._Uint8: "UINT8",
        ast.UnsignedBinaryExactNumericType._Uint16: "UINT16",
        ast.UnsignedBinaryExactNumericType._Uint32: "UINT32",
        ast.UnsignedBinaryExactNumericType._Uint64: "UINT64",
        ast.UnsignedBinaryExactNumericType._Uint128: "UINT128",
        ast.UnsignedBinaryExactNumericType._Uint256: "UINT256",
        ast.UnsignedBinaryExactNumericType._Usmallint: "USMALLINT",
        ast.UnsignedBinaryExactNumericType._Ubigint: "UBIGINT",
    }
    for cls, name in type_map.items():
        if isinstance(expr.unsigned_type, cls):
            return Fragment(f"{name}{not_null}")
    # _Uint with optional precision
    if isinstance(expr.unsigned_type, ast.UnsignedBinaryExactNumericType._Uint):
        if expr.unsigned_type.precision:
            return Fragment(f"UINT({gen.dispatch(expr.unsigned_type.precision)}){not_null}")
        return Fragment(f"UINT{not_null}")
    return Fragment(f"UINT{not_null}")


@generates(ast.ApproximateNumericType)
def generate_approximate_numeric_type(gen: Generator, expr: ast.ApproximateNumericType) -> Fragment:
    not_null = " NOT NULL" if expr.not_null else ""
    type_map = {
        ast.ApproximateNumericType._Float16: "FLOAT16",
        ast.ApproximateNumericType._Float32: "FLOAT32",
        ast.ApproximateNumericType._Float64: "FLOAT64",
        ast.ApproximateNumericType._Float128: "FLOAT128",
        ast.ApproximateNumericType._Float256: "FLOAT256",
        ast.ApproximateNumericType._Real: "REAL",
        ast.ApproximateNumericType._DoublePrecision: "DOUBLE PRECISION",
    }
    for cls, name in type_map.items():
        if isinstance(expr.approximate_numeric_type, cls):
            return Fragment(f"{name}{not_null}")
    # _Float with optional precision/scale
    if isinstance(expr.approximate_numeric_type, ast.ApproximateNumericType._Float):
        ps = expr.approximate_numeric_type.precision_scale
        if ps:
            if ps.scale:
                return Fragment(
                    f"FLOAT({gen.dispatch(ps.precision)}, {gen.dispatch(ps.scale)}){not_null}"
                )
            return Fragment(f"FLOAT({gen.dispatch(ps.precision)}){not_null}")
        return Fragment(f"FLOAT{not_null}")
    return Fragment(f"FLOAT{not_null}")


@generates(ast.DateType)
def generate_date_type(gen: Generator, expr: ast.DateType) -> Fragment:
    not_null = " NOT NULL" if expr.not_null else ""
    return Fragment(f"DATE{not_null}")


@generates(ast.TimeType)
def generate_time_type(gen: Generator, expr: ast.TimeType) -> Fragment:
    parts = ["ZONED TIME"]
    if expr.not_null:
        parts.append("NOT NULL")
    return gen.seq(*parts)


@generates(ast.LocaltimeType)
def generate_localtime_type(gen: Generator, expr: ast.LocaltimeType) -> Fragment:
    not_null = " NOT NULL" if expr.not_null else ""
    return Fragment(f"LOCAL TIME{not_null}")


@generates(ast.DatetimeType)
def generate_datetime_type(gen: Generator, expr: ast.DatetimeType) -> Fragment:
    parts = ["ZONED DATETIME"]
    if expr.not_null:
        parts.append("NOT NULL")
    return gen.seq(*parts)


@generates(ast.LocaldatetimeType)
def generate_localdatetime_type(gen: Generator, expr: ast.LocaldatetimeType) -> Fragment:
    not_null = " NOT NULL" if expr.not_null else ""
    return Fragment(f"LOCAL DATETIME{not_null}")


@generates(ast.TemporalDurationType)
def generate_temporal_duration_type(gen: Generator, expr: ast.TemporalDurationType) -> Fragment:
    qualifier = gen.dispatch(expr.temporal_duration_qualifier)
    parts: list[str | Fragment] = [gen.seq("DURATION", gen.parens(qualifier), sep="")]
    if expr.not_null:
        parts.append("NOT NULL")
    return gen.seq(*parts)


@generates(ast.OpenNodeReferenceValueType)
def generate_open_node_reference_value_type(
    gen: Generator, expr: ast.OpenNodeReferenceValueType
) -> Fragment:
    not_null = " NOT NULL" if expr.not_null else ""
    return Fragment(f"NODE{not_null}")


@generates(ast.ClosedNodeReferenceValueType)
def generate_closed_node_reference_value_type(
    gen: Generator, expr: ast.ClosedNodeReferenceValueType
) -> Fragment:
    base = gen.seq("NODE", "::", gen.dispatch(expr.node_type_specification))
    if expr.not_null:
        return gen.seq(base, "NOT NULL")
    return base


@generates(ast.OpenEdgeReferenceValueType)
def generate_open_edge_reference_value_type(
    gen: Generator, expr: ast.OpenEdgeReferenceValueType
) -> Fragment:
    not_null = " NOT NULL" if expr.not_null else ""
    return Fragment(f"EDGE{not_null}")


@generates(ast.ClosedEdgeReferenceValueType)
def generate_closed_edge_reference_value_type(
    gen: Generator, expr: ast.ClosedEdgeReferenceValueType
) -> Fragment:
    base = gen.seq("EDGE", "::", gen.dispatch(expr.edge_type_specification))
    if expr.not_null:
        return gen.seq(base, "NOT NULL")
    return base


@generates(ast.ListValueType)
def generate_list_value_type(gen: Generator, expr: ast.ListValueType) -> Fragment:
    not_null = " NOT NULL" if expr.not_null else ""
    inner = expr.body
    if isinstance(inner, ast.ListValueType._ListValueTypeNameValueType):
        # LIST<type> form
        vt = gen.dispatch(inner.value_type)
        name = "GROUP LIST" if inner.list_value_type_name.group else "LIST"
        base = f"{name}<{vt}>"
    else:
        # [type] LIST form
        name = "GROUP LIST" if inner.list_value_type_name.group else "LIST"
        if inner.value_type:
            vt = gen.dispatch(inner.value_type)
            base = f"{vt} {name}"
        else:
            base = name
    if expr.max_length:
        return Fragment(f"{base}[{gen.dispatch(expr.max_length)}]{not_null}")
    return Fragment(f"{base}{not_null}")


@generates(ast.ListValueTypeName)
def generate_list_value_type_name(gen: Generator, expr: ast.ListValueTypeName) -> Fragment:
    if expr.group:
        return Fragment("GROUP LIST")
    return Fragment("LIST")


@generates(ast.PathValueType)
def generate_path_value_type(gen: Generator, expr: ast.PathValueType) -> Fragment:
    not_null = " NOT NULL" if expr.not_null else ""
    return Fragment(f"PATH{not_null}")


@generates(ast.RecordType)
def generate_record_type(gen: Generator, expr: ast.RecordType) -> Fragment:
    inner = expr.record_type
    if isinstance(inner, ast.RecordType._AnyRecordNotNull):
        not_null = " NOT NULL" if inner.not_null else ""
        if inner.any:
            return Fragment(f"ANY RECORD{not_null}")
        return Fragment(f"RECORD{not_null}")
    else:
        # _RecordFieldTypesSpecificationNotNull
        not_null = " NOT NULL" if inner.not_null else ""
        fields = gen.dispatch(inner.field_types_specification)
        if inner.record:
            return Fragment(f"RECORD {{{fields}}}{not_null}")
        return Fragment(f"{{{fields}}}{not_null}")


@generates(ast.FieldTypesSpecification)
def generate_field_types_specification(
    gen: Generator, expr: ast.FieldTypesSpecification
) -> Fragment:
    return gen.dispatch(expr.field_type_list)


@generates(ast.FieldTypeList)
def generate_field_type_list(gen: Generator, expr: ast.FieldTypeList) -> Fragment:
    return gen.join([gen.dispatch(f) for f in expr.list_field_type], sep=", ")


@generates(ast.FieldType)
def generate_field_type(gen: Generator, expr: ast.FieldType) -> Fragment:
    parts: list[str | Fragment] = [gen.dispatch(expr.field_name)]
    if expr.typed:
        parts.append("::")
    parts.append(gen.dispatch(expr.value_type))
    return gen.seq(*parts)


@generates(ast.NullType)
def generate_null_type(gen: Generator, expr: ast.NullType) -> Fragment:
    return Fragment("NULL")


@generates(ast.EmptyType)
def generate_empty_type(gen: Generator, expr: ast.EmptyType) -> Fragment:
    return Fragment("NOTHING")


@generates(ast.OpenDynamicUnionType)
def generate_open_dynamic_union_type(gen: Generator, expr: ast.OpenDynamicUnionType) -> Fragment:
    not_null = " NOT NULL" if expr.not_null else ""
    return Fragment(f"ANY{not_null}")


@generates(ast.ClosedDynamicUnionType)
def generate_closed_dynamic_union_type(
    gen: Generator, expr: ast.ClosedDynamicUnionType
) -> Fragment:
    ctl = expr.component_type_list
    types = gen.join([gen.dispatch(ct) for ct in ctl.list_component_type], sep=" | ")
    if expr.any_value:
        return Fragment(f"ANY<{types}>")
    return Fragment(f"<{types}>")
