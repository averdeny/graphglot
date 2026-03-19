"""Generator functions for pattern expressions (node, edge, path patterns)."""

from __future__ import annotations

import typing as t

from graphglot import ast
from graphglot.generator.fragment import Fragment
from graphglot.generator.registry import generates

if t.TYPE_CHECKING:
    from graphglot.generator.base import Generator


@generates(ast.GraphPatternBindingTable)
def generate_graph_pattern_binding_table(
    gen: Generator, expr: ast.GraphPatternBindingTable
) -> Fragment:
    parts = [gen.dispatch(expr.graph_pattern)]
    if expr.graph_pattern_yield_clause:
        parts.append(gen.dispatch(expr.graph_pattern_yield_clause))
    return gen.seq(*parts)


@generates(ast.GraphPattern)
def generate_graph_pattern(gen: Generator, expr: ast.GraphPattern) -> Fragment:
    inner_parts = []
    if expr.match_mode:
        inner_parts.append(gen.dispatch(expr.match_mode))
    inner_parts.append(gen.dispatch(expr.path_pattern_list))
    if expr.keep_clause:
        inner_parts.append(gen.dispatch(expr.keep_clause))
    parts = [gen.seq(*inner_parts)]
    if expr.graph_pattern_where_clause:
        parts.append(gen.dispatch(expr.graph_pattern_where_clause))
    return gen.seq(*parts, sep=gen.sep())


@generates(ast.RepeatableElementsMatchMode)
def generate_repeatable_elements_match_mode(
    gen: Generator, expr: ast.RepeatableElementsMatchMode
) -> Fragment:
    return Fragment("REPEATABLE ELEMENTS")


@generates(ast.DifferentEdgesMatchMode)
def generate_different_edges_match_mode(
    gen: Generator, expr: ast.DifferentEdgesMatchMode
) -> Fragment:
    return Fragment("DIFFERENT EDGES")


@generates(ast.PathPatternList)
def generate_path_pattern_list(gen: Generator, expr: ast.PathPatternList) -> Fragment:
    return gen.join([gen.dispatch(p) for p in expr.list_path_pattern], sep=", ")


@generates(ast.PathPattern)
def generate_path_pattern(gen: Generator, expr: ast.PathPattern) -> Fragment:
    parts = []
    if expr.path_variable_declaration:
        parts.append(gen.dispatch(expr.path_variable_declaration))
    if expr.path_pattern_prefix:
        parts.append(gen.dispatch(expr.path_pattern_prefix))
    parts.append(gen.dispatch(expr.path_pattern_expression))
    return gen.seq(*parts)


@generates(ast.PathVariableDeclaration)
def generate_path_variable_declaration(
    gen: Generator, expr: ast.PathVariableDeclaration
) -> Fragment:
    return gen.seq(gen.dispatch(expr.path_variable), "=")


@generates(ast.PathModePrefix)
def generate_path_mode_prefix(gen: Generator, expr: ast.PathModePrefix) -> Fragment:
    parts: list[str | Fragment] = [gen.dispatch(expr.path_mode)]
    if expr.path_or_paths:
        parts.append("PATH")
    return gen.seq(*parts)


@generates(ast.PathMode)
def generate_path_mode(gen: Generator, expr: ast.PathMode) -> Fragment:
    return Fragment(expr.mode.name)


@generates(ast.AllPathSearch)
def generate_all_path_search(gen: Generator, expr: ast.AllPathSearch) -> Fragment:
    parts: list[str | Fragment] = ["ALL"]
    if expr.path_mode:
        parts.append(gen.dispatch(expr.path_mode))
    if expr.path_or_paths:
        parts.append(gen.dispatch(expr.path_or_paths))
    return gen.seq(*parts)


@generates(ast.AnyPathSearch)
def generate_any_path_search(gen: Generator, expr: ast.AnyPathSearch) -> Fragment:
    parts: list[str | Fragment] = ["ANY"]
    if expr.number_of_paths:
        parts.append(gen.dispatch(expr.number_of_paths))
    if expr.path_mode:
        parts.append(gen.dispatch(expr.path_mode))
    if expr.path_or_paths:
        parts.append(gen.dispatch(expr.path_or_paths))
    return gen.seq(*parts)


@generates(ast.AllShortestPathSearch)
def generate_all_shortest_path_search(gen: Generator, expr: ast.AllShortestPathSearch) -> Fragment:
    parts: list[str | Fragment] = ["ALL SHORTEST"]
    if expr.path_mode:
        parts.append(gen.dispatch(expr.path_mode))
    if expr.path_or_paths:
        parts.append(gen.dispatch(expr.path_or_paths))
    return gen.seq(*parts)


@generates(ast.AnyShortestPathSearch)
def generate_any_shortest_path_search(gen: Generator, expr: ast.AnyShortestPathSearch) -> Fragment:
    parts: list[str | Fragment] = ["ANY SHORTEST"]
    if expr.path_mode:
        parts.append(gen.dispatch(expr.path_mode))
    if expr.path_or_paths:
        parts.append(gen.dispatch(expr.path_or_paths))
    return gen.seq(*parts)


@generates(ast.CountedShortestPathSearch)
def generate_counted_shortest_path_search(
    gen: Generator, expr: ast.CountedShortestPathSearch
) -> Fragment:
    parts: list[str | Fragment] = ["SHORTEST", gen.dispatch(expr.number_of_paths)]
    if expr.path_mode:
        parts.append(gen.dispatch(expr.path_mode))
    if expr.path_or_paths:
        parts.append(gen.dispatch(expr.path_or_paths))
    return gen.seq(*parts)


@generates(ast.CountedShortestGroupSearch)
def generate_counted_shortest_group_search(
    gen: Generator, expr: ast.CountedShortestGroupSearch
) -> Fragment:
    parts: list[str | Fragment] = ["SHORTEST"]
    if expr.number_of_groups:
        parts.append(gen.dispatch(expr.number_of_groups))
    if expr.path_mode:
        parts.append(gen.dispatch(expr.path_mode))
    if expr.path_or_paths:
        parts.append(gen.dispatch(expr.path_or_paths))
    parts.append("GROUPS")
    return gen.seq(*parts)


@generates(ast.PathOrPaths)
def generate_path_or_paths(gen: Generator, expr: ast.PathOrPaths) -> Fragment:
    return Fragment(expr.mode.name)


@generates(ast.PathTerm)
def generate_path_term(gen: Generator, expr: ast.PathTerm) -> Fragment:
    return gen.join([gen.dispatch(f) for f in expr.factors], sep=" ")


@generates(ast.QuantifiedPathPrimary)
def generate_quantified_path_primary(gen: Generator, expr: ast.QuantifiedPathPrimary) -> Fragment:
    return gen.seq(gen.dispatch(expr.path_primary), gen.dispatch(expr.graph_pattern_quantifier))


@generates(ast.QuestionedPathPrimary)
def generate_questioned_path_primary(gen: Generator, expr: ast.QuestionedPathPrimary) -> Fragment:
    return Fragment(f"{gen.dispatch(expr.path_primary)}?")


@generates(ast.FixedQuantifier)
def generate_fixed_quantifier(gen: Generator, expr: ast.FixedQuantifier) -> Fragment:
    return gen.braces(gen.dispatch(expr.unsigned_integer))


@generates(ast.GeneralQuantifier)
def generate_general_quantifier(gen: Generator, expr: ast.GeneralQuantifier) -> Fragment:
    parts = [str(gen.dispatch(expr.lower_bound)), ","]
    if expr.upper_bound:
        parts.append(str(gen.dispatch(expr.upper_bound)))
    return gen.braces(gen.seq(*parts, sep=""))


@generates(ast.Asterisk)
def generate_asterisk(gen: Generator, expr: ast.Asterisk) -> Fragment:
    return Fragment("*")


@generates(ast.NodePattern)
def generate_node_pattern(gen: Generator, expr: ast.NodePattern) -> Fragment:
    return gen.parens(gen.dispatch(expr.element_pattern_filler))


@generates(ast.ElementPatternFiller)
def generate_element_pattern_filler(gen: Generator, expr: ast.ElementPatternFiller) -> Fragment:
    parts = []
    if expr.element_variable_declaration:
        parts.append(gen.dispatch(expr.element_variable_declaration))
    if expr.is_label_expression:
        parts.append(gen.dispatch(expr.is_label_expression))
    if expr.element_pattern_predicate:
        parts.append(gen.dispatch(expr.element_pattern_predicate))
    return gen.seq(*parts)


@generates(ast.ElementVariableDeclaration)
def generate_element_variable_declaration(
    gen: Generator, expr: ast.ElementVariableDeclaration
) -> Fragment:
    return gen.dispatch(expr.element_variable)


@generates(ast.IsLabelExpression)
def generate_is_label_expression(gen: Generator, expr: ast.IsLabelExpression) -> Fragment:
    # Use colon for conciseness (Cypher-style)
    return gen.seq(":", gen.dispatch(expr.label_expression), sep="")


@generates(ast.ElementPatternWhereClause)
def generate_element_pattern_where_clause(
    gen: Generator, expr: ast.ElementPatternWhereClause
) -> Fragment:
    return gen.seq(gen.keyword("WHERE"), gen.dispatch(expr.search_condition))


@generates(ast.ElementPropertySpecification)
def generate_element_property_specification(
    gen: Generator, expr: ast.ElementPropertySpecification
) -> Fragment:
    return gen.braces(gen.dispatch(expr.property_key_value_pair_list))


@generates(ast.PropertyKeyValuePairList)
def generate_property_key_value_pair_list(
    gen: Generator, expr: ast.PropertyKeyValuePairList
) -> Fragment:
    return gen.join([gen.dispatch(p) for p in expr.list_property_key_value_pair], sep=", ")


@generates(ast.PropertyKeyValuePair)
def generate_property_key_value_pair(gen: Generator, expr: ast.PropertyKeyValuePair) -> Fragment:
    return gen.seq(
        gen.dispatch(expr.property_name), ":", gen.dispatch(expr.value_expression), sep=" "
    )


@generates(ast.LabelExpression)
def generate_label_expression(gen: Generator, expr: ast.LabelExpression) -> Fragment:
    return gen.join([gen.dispatch(t) for t in expr.label_terms], sep="|")


@generates(ast.LabelTerm)
def generate_label_term(gen: Generator, expr: ast.LabelTerm) -> Fragment:
    return gen.join([gen.dispatch(f) for f in expr.label_factors], sep="&")


@generates(ast.LabelNegation)
def generate_label_negation(gen: Generator, expr: ast.LabelNegation) -> Fragment:
    return Fragment(f"!{gen.dispatch(expr.label_primary)}")


@generates(ast.LabelName)
def generate_label_name(gen: Generator, expr: ast.LabelName) -> Fragment:
    return gen.dispatch(expr.identifier)


@generates(ast.LabelSetSpecification)
def generate_label_set_specification(gen: Generator, expr: ast.LabelSetSpecification) -> Fragment:
    # Labels are separated by colons, with colon prefix
    return Fragment(":" + ":".join(str(gen.dispatch(name)) for name in expr.list_label_name))


@generates(ast.WildcardLabel)
def generate_wildcard_label(gen: Generator, expr: ast.WildcardLabel) -> Fragment:
    return Fragment("%")


@generates(ast.ParenthesizedLabelExpression)
def generate_parenthesized_label_expression(
    gen: Generator, expr: ast.ParenthesizedLabelExpression
) -> Fragment:
    return gen.parens(gen.dispatch(expr.label_expression))


# Full Edge Patterns


@generates(ast.FullEdgePointingLeft)
def generate_full_edge_pointing_left(gen: Generator, expr: ast.FullEdgePointingLeft) -> Fragment:
    return Fragment(f"<-[{gen.dispatch(expr.element_pattern_filler)}]-")


@generates(ast.FullEdgePointingRight)
def generate_full_edge_pointing_right(gen: Generator, expr: ast.FullEdgePointingRight) -> Fragment:
    return Fragment(f"-[{gen.dispatch(expr.element_pattern_filler)}]->")


@generates(ast.FullEdgeUndirected)
def generate_full_edge_undirected(gen: Generator, expr: ast.FullEdgeUndirected) -> Fragment:
    return Fragment(f"~[{gen.dispatch(expr.element_pattern_filler)}]~")


@generates(ast.FullEdgeLeftOrUndirected)
def generate_full_edge_left_or_undirected(
    gen: Generator, expr: ast.FullEdgeLeftOrUndirected
) -> Fragment:
    return Fragment(f"<~[{gen.dispatch(expr.element_pattern_filler)}]~")


@generates(ast.FullEdgeUndirectedOrRight)
def generate_full_edge_undirected_or_right(
    gen: Generator, expr: ast.FullEdgeUndirectedOrRight
) -> Fragment:
    return Fragment(f"~[{gen.dispatch(expr.element_pattern_filler)}]~>")


@generates(ast.FullEdgeLeftOrRight)
def generate_full_edge_left_or_right(gen: Generator, expr: ast.FullEdgeLeftOrRight) -> Fragment:
    return Fragment(f"<-[{gen.dispatch(expr.element_pattern_filler)}]->")


@generates(ast.FullEdgeAnyDirection)
def generate_full_edge_any_direction(gen: Generator, expr: ast.FullEdgeAnyDirection) -> Fragment:
    return Fragment(f"-[{gen.dispatch(expr.element_pattern_filler)}]-")


# Abbreviated Edge Patterns


@generates(ast.AbbreviatedEdgePattern)
def generate_abbreviated_edge_pattern(gen: Generator, expr: ast.AbbreviatedEdgePattern) -> Fragment:
    pattern_map = {
        ast.AbbreviatedEdgePattern.PatternType.LEFT_ARROW: "<-",
        ast.AbbreviatedEdgePattern.PatternType.TILDE: "~",
        ast.AbbreviatedEdgePattern.PatternType.RIGHT_ARROW: "->",
        ast.AbbreviatedEdgePattern.PatternType.LEFT_ARROW_TILDE: "<~",
        ast.AbbreviatedEdgePattern.PatternType.TILDE_RIGHT_ARROW: "~>",
        ast.AbbreviatedEdgePattern.PatternType.LEFT_MINUS_RIGHT: "<->",
        ast.AbbreviatedEdgePattern.PatternType.MINUS_SIGN: "-",
    }
    return Fragment(pattern_map[expr.pattern])


# Insert Patterns


@generates(ast.InsertPathPattern)
def generate_insert_path_pattern(gen: Generator, expr: ast.InsertPathPattern) -> Fragment:
    parts = [gen.dispatch(expr.insert_node_pattern)]
    if expr.list_insert_edge_pattern_insert_node_pattern:
        for elem in expr.list_insert_edge_pattern_insert_node_pattern:
            parts.append(gen.dispatch(elem.insert_edge_pattern))
            parts.append(gen.dispatch(elem.insert_node_pattern))
    return gen.seq(*parts, sep="")


@generates(ast.InsertNodePattern)
def generate_insert_node_pattern(gen: Generator, expr: ast.InsertNodePattern) -> Fragment:
    if expr.insert_element_pattern_filler:
        return gen.parens(gen.dispatch(expr.insert_element_pattern_filler))
    return Fragment("()")


@generates(ast.InsertEdgePointingLeft)
def generate_insert_edge_pointing_left(
    gen: Generator, expr: ast.InsertEdgePointingLeft
) -> Fragment:
    if expr.insert_element_pattern_filler:
        return Fragment(f"<-[{gen.dispatch(expr.insert_element_pattern_filler)}]-")
    return Fragment("<-[]-")


@generates(ast.InsertEdgePointingRight)
def generate_insert_edge_pointing_right(
    gen: Generator, expr: ast.InsertEdgePointingRight
) -> Fragment:
    if expr.insert_element_pattern_filler:
        return Fragment(f"-[{gen.dispatch(expr.insert_element_pattern_filler)}]->")
    return Fragment("-[]->")


@generates(ast.InsertEdgeUndirected)
def generate_insert_edge_undirected(gen: Generator, expr: ast.InsertEdgeUndirected) -> Fragment:
    if expr.insert_element_pattern_filler:
        return Fragment(f"~[{gen.dispatch(expr.insert_element_pattern_filler)}]~")
    return Fragment("~[]~")


@generates(ast.InsertElementPatternFiller)
def generate_insert_element_pattern_filler(
    gen: Generator, expr: ast.InsertElementPatternFiller
) -> Fragment:
    inner = expr.insert_element_pattern_filler
    if isinstance(
        inner,
        ast.InsertElementPatternFiller._ElementVariableDeclarationLabelAndPropertySetSpecification,
    ):
        parts = [gen.dispatch(inner.element_variable_declaration)]
        if inner.label_and_property_set_specification:
            parts.append(gen.dispatch(inner.label_and_property_set_specification))
        return gen.seq(*parts)
    elif isinstance(inner, ast.ElementVariableDeclaration):
        return gen.dispatch(inner)
    else:
        # LabelAndPropertySetSpecification
        return gen.dispatch(inner)


@generates(ast.LabelAndPropertySetSpecification)
def generate_label_and_property_set_specification(
    gen: Generator, expr: ast.LabelAndPropertySetSpecification
) -> Fragment:
    inner = expr.label_and_property_set_specification
    if isinstance(
        inner,
        ast.LabelAndPropertySetSpecification._LabelSetSpecificationElementPropertySpecification,
    ):
        # Both label set and property specification
        parts = [gen.dispatch(inner.label_set_specification)]
        if inner.element_property_specification:
            parts.append(gen.dispatch(inner.element_property_specification))
        return gen.seq(*parts)
    elif isinstance(inner, ast.LabelSetSpecification):
        # Just label set
        return gen.dispatch(inner)
    else:
        # Just element property specification
        return gen.dispatch(inner)


@generates(ast.ParenthesizedPathPatternExpression)
def generate_parenthesized_path_pattern_expression(
    gen: Generator, expr: ast.ParenthesizedPathPatternExpression
) -> Fragment:
    parts = []
    if expr.subpath_variable_declaration:
        parts.append(gen.dispatch(expr.subpath_variable_declaration))
    if expr.path_mode_prefix:
        parts.append(gen.dispatch(expr.path_mode_prefix))
    parts.append(gen.dispatch(expr.path_pattern_expression))
    if expr.parenthesized_path_pattern_where_clause:
        parts.append(gen.dispatch(expr.parenthesized_path_pattern_where_clause))
    return gen.parens(gen.seq(*parts))


@generates(ast.SubpathVariableDeclaration)
def generate_subpath_variable_declaration(
    gen: Generator, expr: ast.SubpathVariableDeclaration
) -> Fragment:
    return gen.seq(gen.dispatch(expr.subpath_variable), "=")


@generates(ast.ParenthesizedPathPatternWhereClause)
def generate_parenthesized_path_pattern_where_clause(
    gen: Generator, expr: ast.ParenthesizedPathPatternWhereClause
) -> Fragment:
    return gen.seq(gen.keyword("WHERE"), gen.dispatch(expr.search_condition))


@generates(ast.InsertPathPatternList)
def generate_insert_path_pattern_list(gen: Generator, expr: ast.InsertPathPatternList) -> Fragment:
    return gen.join([gen.dispatch(p) for p in expr.list_insert_path_pattern], sep=", ")
