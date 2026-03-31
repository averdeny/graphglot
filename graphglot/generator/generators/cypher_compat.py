"""GQL generators for Cypher-specific AST nodes.

These provide GQL-compatible output for Cypher-specific AST nodes.  Some are
direct keyword mappings (CREATE → INSERT), others are structural rewrites
(STARTS WITH → LEFT).  Every dialect inherits these via DEFAULT_GENERATORS, so
cross-dialect transpilation (e.g. Neo4j → FullGQL) works automatically.

CypherDialect.Generator overrides these with Cypher-native output (e.g.
``all(x IN list WHERE pred)`` instead of ``EXISTS { FOR x IN list ... }``).
"""

from __future__ import annotations

import typing as t

from graphglot.ast.cypher import (
    CreateClause,
    CypherChainedComparison,
    CypherPatternPredicate,
    CypherPredicateComparison,
    ListPredicateFunction,
    StringMatchPredicate,
)
from graphglot.ast.expressions import ComparisonPredicatePart2
from graphglot.generator.fragment import Fragment, parens, seq
from graphglot.generator.registry import generates

if t.TYPE_CHECKING:
    from graphglot.generator.base import Generator


@generates(CypherChainedComparison)
def generate_chained_comparison(gen: Generator, expr: CypherChainedComparison) -> Fragment:
    """``1 < n.num < 3`` → ``1 < n.num AND n.num < 3``."""
    parts: list[str | Fragment] = []
    for i, cmp in enumerate(expr.comparisons):
        if i > 0:
            parts.append("AND")
        parts.append(gen.dispatch(cmp))
    return parens(gen.seq(*parts))


@generates(StringMatchPredicate)
def generate_string_match_predicate(gen: Generator, expr: StringMatchPredicate) -> Fragment:
    """``x STARTS WITH 'A'`` → ``LEFT(x, CHAR_LENGTH('A')) = 'A'``.

    CONTAINS has no GQL equivalent — raises NotImplementedError.
    """
    if expr.kind == StringMatchPredicate.MatchKind.CONTAINS:
        raise NotImplementedError(
            "CONTAINS has no GQL equivalent. "
            "Use a Cypher-compatible dialect to generate this expression."
        )
    lhs = gen.dispatch(expr.lhs)
    rhs = gen.dispatch(expr.rhs)
    func = "LEFT" if expr.kind == StringMatchPredicate.MatchKind.STARTS_WITH else "RIGHT"
    return gen.seq(
        Fragment(f"{func}({lhs}, CHAR_LENGTH({rhs}))"),
        "=",
        rhs,
    )


@generates(CypherPatternPredicate)
def generate_pattern_predicate(gen: Generator, expr: CypherPatternPredicate) -> Fragment:
    """``(n)-[:KNOWS]->()`` → ``EXISTS {(n)-[:KNOWS]->()}``."""
    return gen.seq("EXISTS", gen.braces(gen.dispatch(expr.pattern)))


@generates(ListPredicateFunction)
def generate_list_predicate(gen: Generator, expr: ListPredicateFunction) -> Fragment:
    """``all/any/none(x IN L WHERE P)`` → EXISTS subquery.

    - ``any(x IN L WHERE P)``  → ``EXISTS {FOR x IN L FILTER WHERE P RETURN x}``
    - ``none(x IN L WHERE P)`` → ``(NOT EXISTS {FOR x IN L FILTER WHERE P RETURN x})``
    - ``all(x IN L WHERE P)``  → ``(NOT EXISTS {FOR x IN L FILTER WHERE NOT (P) RETURN x})``

    ``single()`` has no GQL equivalent — raises NotImplementedError.
    """
    if expr.kind == ListPredicateFunction.Kind.SINGLE:
        raise NotImplementedError(
            "single() has no GQL equivalent. "
            "Use a Cypher-compatible dialect to generate this expression."
        )
    var = gen.dispatch(expr.variable)
    source = gen.dispatch(expr.source)
    pred = gen.dispatch(expr.predicate)

    if expr.kind == ListPredicateFunction.Kind.ALL:
        where = gen.seq("NOT", parens(pred))
    else:
        where = pred

    body = gen.seq("FOR", var, "IN", source, "FILTER WHERE", where, "RETURN", var)
    exists = gen.seq("EXISTS", gen.braces(body))

    if expr.kind == ListPredicateFunction.Kind.ANY:
        return exists

    # none, all → (NOT EXISTS { ... })
    return parens(seq("NOT", exists))


_COMP_OP_STR = {
    ComparisonPredicatePart2.CompOp.EQUALS: "=",
    ComparisonPredicatePart2.CompOp.NOT_EQUALS: "<>",
    ComparisonPredicatePart2.CompOp.LESS_THAN: "<",
    ComparisonPredicatePart2.CompOp.GREATER_THAN: ">",
    ComparisonPredicatePart2.CompOp.LESS_THAN_OR_EQUALS: "<=",
    ComparisonPredicatePart2.CompOp.GREATER_THAN_OR_EQUALS: ">=",
}


@generates(CypherPredicateComparison)
def generate_predicate_comparison(gen: Generator, expr: CypherPredicateComparison) -> Fragment:
    """``none(...) = true`` → ``(NOT EXISTS {...}) = true``."""
    return gen.seq(gen.dispatch(expr.left), _COMP_OP_STR[expr.op], gen.dispatch(expr.right))


@generates(CreateClause)
def generate_create_clause(gen: Generator, expr: CreateClause) -> Fragment:
    """``CREATE <pattern>`` → ``INSERT <pattern>``."""
    return gen.seq(gen.keyword("INSERT"), gen.dispatch(expr.insert_graph_pattern))
