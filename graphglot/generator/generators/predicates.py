"""Generator functions for predicate expressions (comparison, exists, etc.)."""

from __future__ import annotations

import typing as t

from graphglot import ast
from graphglot.generator.fragment import Fragment
from graphglot.generator.registry import generates

if t.TYPE_CHECKING:
    from graphglot.generator.base import Generator


@generates(ast.ComparisonPredicate)
def generate_comparison_predicate(gen: Generator, expr: ast.ComparisonPredicate) -> Fragment:
    return gen.seq(
        gen.dispatch(expr.comparison_predicand), gen.dispatch(expr.comparison_predicate_part_2)
    )


@generates(ast.ComparisonPredicatePart2)
def generate_comparison_predicate_part_2(
    gen: Generator, expr: ast.ComparisonPredicatePart2
) -> Fragment:
    # Get the operator
    op_map = {
        "EQUALS": "=",
        "NOT_EQUALS": "<>",
        "LESS_THAN": "<",
        "GREATER_THAN": ">",
        "LESS_THAN_OR_EQUALS": "<=",
        "GREATER_THAN_OR_EQUALS": ">=",
    }
    op = op_map.get(expr.comp_op.name, str(expr.comp_op.name))
    return gen.seq(op, gen.dispatch(expr.comparison_predicand))


@generates(ast.ExistsPredicate)
def generate_exists_predicate(gen: Generator, expr: ast.ExistsPredicate) -> Fragment:
    inner = expr.exists_predicate
    if isinstance(inner, ast.ExistsPredicate._ExistsGraphPattern):
        return gen.seq("EXISTS", gen.braces(gen.dispatch(inner.graph_pattern)))
    elif isinstance(inner, ast.ExistsPredicate._ExistsMatchStatementBlock):
        return gen.seq("EXISTS", gen.braces(gen.dispatch(inner.match_statement_block)))
    elif isinstance(inner, ast.NestedQuerySpecification):
        return gen.seq("EXISTS", gen.dispatch(inner))
    else:
        return gen.seq("EXISTS", gen.dispatch(inner))


@generates(ast.NullPredicate)
def generate_null_predicate(gen: Generator, expr: ast.NullPredicate) -> Fragment:
    return gen.seq(
        gen.dispatch(expr.value_expression_primary), gen.dispatch(expr.null_predicate_part_2)
    )


@generates(ast.NullPredicatePart2)
def generate_null_predicate_part_2(gen: Generator, expr: ast.NullPredicatePart2) -> Fragment:
    if expr.not_:
        return Fragment("IS NOT NULL")
    return Fragment("IS NULL")


@generates(ast.ValueTypePredicate)
def generate_value_type_predicate(gen: Generator, expr: ast.ValueTypePredicate) -> Fragment:
    return gen.seq(
        gen.dispatch(expr.value_expression_primary), gen.dispatch(expr.value_type_predicate_part_2)
    )


@generates(ast.ValueTypePredicatePart2)
def generate_value_type_predicate_part_2(
    gen: Generator, expr: ast.ValueTypePredicatePart2
) -> Fragment:
    parts: list[str | Fragment] = ["IS"]
    if expr.not_:
        parts.append("NOT")
    parts.append("TYPED")
    parts.append(gen.dispatch(expr.value_type))
    return gen.seq(*parts)


@generates(ast.NormalizedPredicate)
def generate_normalized_predicate(gen: Generator, expr: ast.NormalizedPredicate) -> Fragment:
    return gen.seq(
        gen.dispatch(expr.string_value_expression),
        gen.dispatch(expr.normalized_predicate_part_2),
    )


@generates(ast.NormalizedPredicatePart2)
def generate_normalized_predicate_part_2(
    gen: Generator, expr: ast.NormalizedPredicatePart2
) -> Fragment:
    parts: list[str | Fragment] = ["IS"]
    if expr.not_:
        parts.append("NOT")
    if expr.normal_form:
        parts.append(gen.dispatch(expr.normal_form))
    parts.append("NORMALIZED")
    return gen.seq(*parts)


@generates(ast.DirectedPredicate)
def generate_directed_predicate(gen: Generator, expr: ast.DirectedPredicate) -> Fragment:
    return gen.seq(
        gen.dispatch(expr.element_variable_reference), gen.dispatch(expr.directed_predicate_part_2)
    )


@generates(ast.DirectedPredicatePart2)
def generate_directed_predicate_part_2(
    gen: Generator, expr: ast.DirectedPredicatePart2
) -> Fragment:
    if expr.not_:
        return Fragment("IS NOT DIRECTED")
    return Fragment("IS DIRECTED")


@generates(ast.LabeledPredicate)
def generate_labeled_predicate(gen: Generator, expr: ast.LabeledPredicate) -> Fragment:
    return gen.seq(
        gen.dispatch(expr.element_variable_reference), gen.dispatch(expr.labeled_predicate_part_2)
    )


@generates(ast.LabeledPredicatePart2)
def generate_labeled_predicate_part_2(gen: Generator, expr: ast.LabeledPredicatePart2) -> Fragment:
    inner = expr.is_labeled_or_colon
    if isinstance(inner, ast.IsLabeledOrColon._IsNotLabeled):
        parts: list[str | Fragment] = ["IS"]
        if inner.not_:
            parts.append("NOT")
        parts.append("LABELED")
        parts.append(gen.dispatch(expr.label_expression))
        return gen.seq(*parts)
    else:
        # _Colon variant: :<label expression>
        return Fragment(f":{gen.dispatch(expr.label_expression)}")


@generates(ast.SourceDestinationPredicate)
def generate_source_destination_predicate(
    gen: Generator, expr: ast.SourceDestinationPredicate
) -> Fragment:
    return gen.seq(gen.dispatch(expr.node_reference), gen.dispatch(expr.predicate_part_2))


@generates(ast.SourcePredicatePart2)
def generate_source_predicate_part_2(gen: Generator, expr: ast.SourcePredicatePart2) -> Fragment:
    parts: list[str | Fragment] = ["IS"]
    if expr.not_:
        parts.append("NOT")
    parts.append("SOURCE OF")
    parts.append(gen.dispatch(expr.edge_reference))
    return gen.seq(*parts)


@generates(ast.DestinationPredicatePart2)
def generate_destination_predicate_part_2(
    gen: Generator, expr: ast.DestinationPredicatePart2
) -> Fragment:
    parts: list[str | Fragment] = ["IS"]
    if expr.not_:
        parts.append("NOT")
    parts.append("DESTINATION OF")
    parts.append(gen.dispatch(expr.edge_reference))
    return gen.seq(*parts)


@generates(ast.AllDifferentPredicate)
def generate_all_different_predicate(gen: Generator, expr: ast.AllDifferentPredicate) -> Fragment:
    refs = gen.join([gen.dispatch(r) for r in expr.list_element_variable_reference], sep=", ")
    return Fragment(f"ALL_DIFFERENT({refs})")


@generates(ast.SamePredicate)
def generate_same_predicate(gen: Generator, expr: ast.SamePredicate) -> Fragment:
    refs = gen.join([gen.dispatch(r) for r in expr.list_element_variable_reference], sep=", ")
    return Fragment(f"SAME({refs})")


@generates(ast.PropertyExistsPredicate)
def generate_property_exists_predicate(
    gen: Generator, expr: ast.PropertyExistsPredicate
) -> Fragment:
    ref = gen.dispatch(expr.element_variable_reference)
    name = gen.dispatch(expr.property_name)
    return Fragment(f"PROPERTY_EXISTS({ref}, {name})")
