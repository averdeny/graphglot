"""Cypher-specific AST nodes.

These nodes represent syntax that is not part of the ISO/IEC 39075:2024 GQL
standard but is shared across Cypher-compatible databases (Neo4j, Neptune, etc.).

All classes are decorated with :func:`nonstandard` and gate on ``CY:``
features via :meth:`~Expression.require_feature`.

Cypher predicates inherit from :class:`Predicate` so they can appear in
``BooleanTest.boolean_primary`` alongside the standard GQL predicates
via the ``BooleanPrimary = Predicate | BooleanPredicand`` type alias.
"""

from __future__ import annotations

from enum import Enum, auto

from graphglot import features as F

from .base import Expression, model_validator, nonstandard
from .expressions import (
    BindingVariable,
    BindingVariableReference,
    BooleanValueExpression,
    CaseSpecification,
    CommonValueExpression,
    ComparisonPredicate,
    ComparisonPredicatePart2,
    DatetimeValueFunction,
    DurationValueFunction,
    ElseClause,
    GqlProgram,
    Identifier,
    InsertGraphPattern,
    ListValueConstructorByEnumeration,
    OrderByAndPageStatement,
    PathPattern,
    Predicate,
    PrimitiveCatalogModifyingStatement,
    PrimitiveQueryStatement,
    PropertyName,
    PropertyReference,
    Result,
    ReturnStatementBody,
    SetItem,
    SetItemList,
    ValueExpression,
    WhereClause,
)

# =============================================================================
# Operators / predicates
# =============================================================================


@nonstandard("Cypher extension: string match predicates (STARTS WITH, ENDS WITH, CONTAINS)")
class StringMatchPredicate(Predicate):
    """Cypher ``lhs STARTS WITH | ENDS WITH | CONTAINS rhs``.

    Example::

        n.name STARTS WITH 'Al'
        n.name ENDS WITH 'ice'
        n.name CONTAINS 'li'
    """

    class MatchKind(Enum):
        STARTS_WITH = auto()
        ENDS_WITH = auto()
        CONTAINS = auto()

    lhs: ValueExpression
    kind: MatchKind
    rhs: ValueExpression

    @model_validator(mode="after")
    def _check_feature(self):
        self.require_feature(F.CY_OP01)
        return self


@nonstandard("Cypher extension: IN predicate (expr IN list)")
class InPredicate(Predicate):
    """Cypher ``value IN list_expression``.

    Example::

        n.age IN [25, 30, 35]
        x IN $ids
    """

    value: ValueExpression
    list_expression: ValueExpression

    @model_validator(mode="after")
    def _check_feature(self):
        self.require_feature(F.CY_OP02)
        return self


@nonstandard("Cypher extension: subscript/index access (expr[idx])")
class CypherSubscriptExpression(CommonValueExpression):
    """Cypher ``expr[idx]`` subscript access.

    Used for both map key access (``map['key']``) and list index
    access (``list[0]``).  Chainable: ``expr[a][b]``.

    Example::

        {a: 1}['a']
        [1, 2, 3][0]
        map['key']
    """

    base: ValueExpression
    index: ValueExpression

    @model_validator(mode="after")
    def _check_feature(self):
        self.require_feature(F.CY_OP04)
        return self


@nonstandard("Cypher extension: list slice expression")
class CypherSliceExpression(CommonValueExpression):
    """Cypher ``expr[start..end]`` list slice.

    One of ``start`` or ``end`` may be omitted (but not both).

    Example::

        [1, 2, 3][0..2]
        list[1..]
        list[..3]
    """

    base: ValueExpression
    start: ValueExpression | None = None
    end: ValueExpression | None = None

    @model_validator(mode="after")
    def _check_feature(self):
        self.require_feature(F.CY_OP04)
        return self


class CypherWhenClause(Expression):
    """A single ``WHEN operand_list THEN result`` inside :class:`CypherSimpleCase`."""

    operands: list[ValueExpression]
    result: Result


@nonstandard("Cypher extension: relaxed CASE expression operands")
class CypherSimpleCase(CaseSpecification):
    """Cypher ``CASE expr WHEN val THEN result ... END`` with relaxed operand types.

    GQL restricts ``CaseOperand`` to ``NPVEP | ElementVariableReference`` and
    ``WhenOperand`` to ``NPVEP | Part2 predicates``, but Cypher allows full
    expressions (e.g., ``CASE -1 WHEN -1 THEN 'neg' END``).

    Example::

        CASE n.status WHEN 'active' THEN 1 WHEN 'inactive' THEN 0 END
        CASE -1 WHEN -1 THEN 'neg' ELSE 'pos' END
    """

    case_operand: ValueExpression
    when_clauses: list[CypherWhenClause]
    else_clause: ElseClause | None = None


@nonstandard("Cypher extension: regex match operator (=~)")
class RegexMatchPredicate(Predicate):
    """Cypher ``lhs =~ rhs`` regex match.

    Example::

        n.name =~ 'Al.*'
        n.name =~ '(?i)alice'
    """

    lhs: ValueExpression
    rhs: ValueExpression

    @model_validator(mode="after")
    def _check_feature(self):
        self.require_feature(F.CY_OP03)
        return self


# =============================================================================
# Expressions
# =============================================================================


@nonstandard("Cypher extension: list comprehension")
class ListComprehension(ListValueConstructorByEnumeration):
    """Cypher ``[variable IN source WHERE pred | expr]``.

    Inherits from :class:`ListValueConstructorByEnumeration` so that it fits
    into the existing value-expression hierarchy.

    Example::

        [x IN [1,2,3] WHERE x > 1 | x * 2]
        [x IN list | x.name]
        [x IN list WHERE x > 0]
        [x IN list]
    """

    variable: BindingVariable
    source: ValueExpression
    where_clause: WhereClause | None
    projection: ValueExpression | None
    # Override inherited fields with defaults so they're not required
    list_value_type_name: None = None
    list_element_list: None = None

    @model_validator(mode="after")
    def _check_feature(self):
        self.require_feature(F.CY_EX01)
        return self


@nonstandard("Cypher extension: pattern comprehension")
class CypherPatternComprehension(ListValueConstructorByEnumeration):
    """Cypher ``[(pattern) [WHERE pred] | projection]``.

    A pattern comprehension evaluates a pattern, optionally filters with
    WHERE, and projects each match into a list.

    Example::

        [(a)-->(b) WHERE b.name = 'Alice' | b.age]
        [(a)-[r]->(b) | r.weight]
    """

    pattern: PathPattern
    where_clause: WhereClause | None = None
    projection: ValueExpression
    # Override inherited fields with defaults so they're not required
    list_value_type_name: None = None
    list_element_list: None = None

    @model_validator(mode="after")
    def _check_feature(self):
        self.require_feature(F.CY_EX01)
        return self


@nonstandard("Cypher extension: list predicate functions (all/any/none/single)")
class ListPredicateFunction(Predicate):
    """Cypher ``all/any/none/single(variable IN source WHERE predicate)``.

    Example::

        all(x IN nodes WHERE x.age > 0)
        any(x IN list WHERE x > 5)
        none(x IN list WHERE x < 0)
        single(x IN list WHERE x = 1)
    """

    class Kind(Enum):
        ALL = auto()
        ANY = auto()
        NONE = auto()
        SINGLE = auto()

    kind: Kind
    variable: BindingVariable
    source: ValueExpression
    predicate: BooleanValueExpression

    @model_validator(mode="after")
    def _check_feature(self):
        self.require_feature(F.CY_FN01)
        return self


@nonstandard("Cypher extension: predicate comparison (quantifier = expr)")
class CypherPredicateComparison(Predicate):
    """Comparison where one side is a predicate function (e.g. ``none(...) = true``).

    In Cypher, quantifier predicate functions return boolean values that can be
    compared with ``=``, ``<>``, etc.  GQL's ``ComparisonPredicate`` requires
    ``ComparisonPredicand`` (= ``CommonValueExpression``) on both sides, which
    excludes predicates.  This node bridges the gap.

    Example::

        none(x IN list WHERE x = 1) = true
        any(x IN list WHERE x > 0) <> false
    """

    left: Expression
    op: ComparisonPredicatePart2.CompOp
    right: Expression

    @model_validator(mode="after")
    def _check_feature(self):
        self.require_feature(F.CY_FN01)
        return self


@nonstandard("Cypher extension: chained comparison (a < b < c)")
class CypherChainedComparison(Predicate):
    """Chained comparison: ``a < b < c`` expanded to ``a < b AND b < c``.

    Example::

        MATCH (n) WHERE 1 < n.num < 3 RETURN n
        -- equivalent to: WHERE 1 < n.num AND n.num < 3

    Stores the full list of comparisons for round-trip fidelity.
    """

    comparisons: list[ComparisonPredicate]

    @model_validator(mode="after")
    def _check_feature(self):
        self.require_feature(F.CY_FN01)
        return self


# =============================================================================
# CypherReduce — special syntax
# =============================================================================


@nonstandard("Cypher extension: reduce() accumulator function")
class CypherReduce(CommonValueExpression):
    """``reduce(accumulator = initial, variable IN list | expression)``.

    Example::

        reduce(s = 0, x IN [1, 2, 3] | s + x)
    """

    accumulator: Identifier
    initial: ValueExpression
    variable: Identifier
    list_expr: ValueExpression
    expression: ValueExpression

    @model_validator(mode="after")
    def _check_feature(self):
        self.require_feature(F.CY_FN04)
        return self


@nonstandard("Cypher extension: pattern expression predicate")
class CypherPatternPredicate(Predicate):
    """Bare pattern ``(n)-[:T]->()`` used as boolean predicate in WHERE.

    Example::

        WHERE (n)-[:KNOWS]->()
        WHERE NOT (n)-->()
    """

    pattern: PathPattern

    @model_validator(mode="after")
    def _check_feature(self):
        self.require_feature(F.CY_EX02)
        return self


class TemporalBaseType(Enum):
    """Temporal function base type shared by CypherTemporalCast and CypherTemporalMethod."""

    DATE = auto()
    TIME = auto()
    DATETIME = auto()
    LOCALDATETIME = auto()
    LOCALTIME = auto()
    DURATION = auto()


@nonstandard("Cypher extension: temporal function with expression argument")
class CypherTemporalCast(DatetimeValueFunction, DurationValueFunction):
    """Temporal function with expression argument: ``date(expr)``, ``datetime(var)``.

    Used when the temporal constructor receives an expression (variable, null,
    function call) instead of a string literal.  Cypher allows ``date(null)``,
    ``datetime(otherTemporal)``, ``date(toString(d))``, etc.

    Example::

        date(null)
        datetime(other)
        date(toString(d))
    """

    function_name: TemporalBaseType
    argument: ValueExpression

    @model_validator(mode="after")
    def _check_feature(self):
        self.require_feature(F.CY_TF01)
        return self


@nonstandard("Cypher extension: temporal static method calls")
class CypherTemporalMethod(DatetimeValueFunction, DurationValueFunction):
    """Cypher temporal static method calls.

    Example::

        date.truncate('year', d)
        duration.between(d1, d2)
        datetime.realtime()
        datetime.transaction()
        datetime.statement()
    """

    class Method(Enum):
        TRUNCATE = auto()
        BETWEEN = auto()
        TRANSACTION = auto()
        STATEMENT = auto()
        REALTIME = auto()
        INMONTHS = auto()
        INDAYS = auto()
        INSECONDS = auto()
        FROMEPOCH = auto()
        FROMEPOCHMILLIS = auto()

    base_type: TemporalBaseType
    method: Method
    arguments: list[ValueExpression]

    @model_validator(mode="after")
    def _check_feature(self):
        self.require_feature(F.CY_TF01)
        return self


# =============================================================================
# SET extensions
# =============================================================================


@nonstandard("Cypher extension: SET n += {map} (map append)")
class CypherSetMapAppendItem(SetItem):
    """Cypher ``SET var += map_expr`` — merge map into existing properties.

    Unlike ``SET var = map`` (which replaces all properties), ``+=`` merges
    the map into the existing properties, keeping unmentioned keys.

    Example::

        SET n += {name: 'Alice', age: 30}
        SET r += {weight: 1.5}
    """

    binding_variable_reference: BindingVariableReference
    map_expression: ValueExpression

    @model_validator(mode="after")
    def _check_feature(self):
        self.require_feature(F.CY_CL04)
        return self


@nonstandard("Cypher extension: SET n = expr (copy all properties from expression)")
class CypherSetAllFromExprItem(SetItem):
    """Cypher ``SET var = expr`` — replace all properties from an expression.

    Unlike ``SetAllPropertiesItem`` (which requires a ``{...}`` map literal),
    this allows any expression (e.g., another node/relationship variable).

    Example::

        SET r = a
        SET n = {name: 'Alice'}
    """

    binding_variable_reference: BindingVariableReference
    value: ValueExpression

    @model_validator(mode="after")
    def _check_feature(self):
        self.require_feature(F.CY_CL04)
        return self


@nonstandard("Cypher extension: SET (expr).prop = val")
class CypherSetPropertyFromExprItem(SetItem):
    """Cypher ``SET (expr).prop = val`` — set property on an expression result.

    Allows parenthesized expression as property source, e.g. ``(n).name``.

    Example::

        SET (n).name = 'neo4j'
        SET (r).weight = 1.5
    """

    target_expression: ValueExpression
    property_name: PropertyName
    value: ValueExpression

    @model_validator(mode="after")
    def _check_feature(self):
        self.require_feature(F.CY_CL04)
        return self


# =============================================================================
# Clauses
# =============================================================================


@nonstandard("Cypher extension: MERGE clause (match-or-create)")
class MergeClause(PrimitiveQueryStatement):
    """Cypher ``MERGE <pattern> [ON CREATE SET ...] [ON MATCH SET ...]``.

    MERGE is a "match-or-create" operation: it tries to MATCH the given
    pattern and, if no match is found, CREATEs it.  Optional ``ON CREATE
    SET`` and ``ON MATCH SET`` sub-clauses allow setting properties
    conditionally.

    Example::

        MERGE (n:Person {name: 'Alice'})
        MERGE (n:Person) ON CREATE SET n.created = datetime()
        MERGE (n:Person) ON CREATE SET n.created = 1 ON MATCH SET n.lastSeen = 2
    """

    path_pattern: PathPattern
    on_create_set: SetItemList | None
    on_match_set: SetItemList | None

    @model_validator(mode="after")
    def _check_feature(self):
        self.require_feature(F.CY_CL01)
        return self


@nonstandard("Cypher extension: WITH clause (variable projection)")
class CypherWithStatement(PrimitiveQueryStatement):
    """Cypher intermediate ``WITH`` in a multi-part query.

    WITH projects and optionally aggregates variables between query parts.
    GQL has no direct equivalent — ``RETURN`` terminates a query, while
    ``WITH`` acts as a pipeline stage within a single query.

    Example::

        MATCH (n) WITH n.name AS name RETURN name
        MATCH (n) WITH n ORDER BY n.age LIMIT 10 RETURN n
        MATCH (n) WITH DISTINCT n.label AS label RETURN label
        MATCH (n) WITH n WHERE n.age > 25 RETURN n
    """

    return_statement_body: ReturnStatementBody
    order_by_and_page_statement: OrderByAndPageStatement | None = None
    where_clause: WhereClause | None = None

    @model_validator(mode="after")
    def _check_feature(self):
        self.require_feature(F.CY_CL05)
        return self


@nonstandard("Cypher extension: CREATE clause (node/edge creation)")
class CreateClause(PrimitiveQueryStatement):
    """Cypher ``CREATE <insert_graph_pattern>``.

    CREATE is the primary way to create nodes and relationships in Cypher.
    Syntactically identical to GQL's INSERT — reuses :class:`InsertGraphPattern`.

    Example::

        CREATE (n:Person {name: 'Alice'})
        CREATE (a)-[r:KNOWS]->(b)
    """

    insert_graph_pattern: InsertGraphPattern

    @model_validator(mode="after")
    def _check_feature(self):
        self.require_feature(F.CY_CL04)
        return self


# =============================================================================
# Query prefixes
# =============================================================================


@nonstandard("Cypher extension: EXPLAIN / PROFILE query prefix")
class QueryPrefix(Expression):
    """Cypher ``EXPLAIN <query>`` or ``PROFILE <query>``.

    A prefix applied to an entire query to request execution plan information.

    Example::

        EXPLAIN MATCH (n) RETURN n
        PROFILE MATCH (n:Person) RETURN n.name
    """

    class Kind(Enum):
        EXPLAIN = auto()
        PROFILE = auto()

    kind: Kind
    body: GqlProgram

    @model_validator(mode="after")
    def _check_feature(self):
        self.require_feature(F.CY_QP01)
        return self


# =============================================================================
# DDL — Index management
# =============================================================================


@nonstandard("Cypher extension: CREATE INDEX")
class CreateIndex(PrimitiveCatalogModifyingStatement):
    """Cypher ``CREATE INDEX [name] [IF NOT EXISTS] FOR (n:Label) ON (n.prop, ...)``.

    Example::

        CREATE INDEX FOR (n:Person) ON (n.name)
        CREATE INDEX my_idx IF NOT EXISTS FOR ()-[r:KNOWS]-() ON (r.since)
    """

    name: Identifier | None
    if_not_exists: bool
    variable: BindingVariable
    label: Identifier
    is_relationship: bool
    properties: list[PropertyReference]

    @model_validator(mode="after")
    def _check_feature(self):
        self.require_feature(F.CY_DD01)
        return self


@nonstandard("Cypher extension: DROP INDEX")
class DropIndex(PrimitiveCatalogModifyingStatement):
    """Cypher ``DROP INDEX name [IF EXISTS]``.

    Example::

        DROP INDEX my_idx
        DROP INDEX my_idx IF EXISTS
    """

    name: Identifier
    if_exists: bool

    @model_validator(mode="after")
    def _check_feature(self):
        self.require_feature(F.CY_DD01)
        return self


# =============================================================================
# DDL — Constraint management
# =============================================================================


class ConstraintKind(Enum):
    """Kind of constraint in a CREATE CONSTRAINT statement."""

    UNIQUE = auto()
    NOT_NULL = auto()
    NODE_KEY = auto()


@nonstandard("Cypher extension: CREATE CONSTRAINT")
class CreateConstraint(PrimitiveCatalogModifyingStatement):
    """Cypher ``CREATE CONSTRAINT [name] [IF NOT EXISTS] FOR (n:Label) REQUIRE ... IS <kind>``.

    Example::

        CREATE CONSTRAINT FOR (n:Person) REQUIRE n.email IS UNIQUE
        CREATE CONSTRAINT FOR (n:Person) REQUIRE n.name IS NOT NULL
        CREATE CONSTRAINT FOR (n:Person) REQUIRE (n.first, n.last) IS NODE KEY
    """

    name: Identifier | None
    if_not_exists: bool
    variable: BindingVariable
    label: Identifier
    properties: list[PropertyReference]
    constraint_kind: ConstraintKind

    @model_validator(mode="after")
    def _check_feature(self):
        self.require_feature(F.CY_DD02)
        return self


@nonstandard("Cypher extension: DROP CONSTRAINT")
class DropConstraint(PrimitiveCatalogModifyingStatement):
    """Cypher ``DROP CONSTRAINT name [IF EXISTS]``.

    Example::

        DROP CONSTRAINT my_con
        DROP CONSTRAINT my_con IF EXISTS
    """

    name: Identifier
    if_exists: bool

    @model_validator(mode="after")
    def _check_feature(self):
        self.require_feature(F.CY_DD02)
        return self
