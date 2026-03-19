"""Dialect-agnostic function infrastructure.

Provides :class:`Func` as the base class for generic ``name(arg1, arg2, ...)``
functions, :class:`Anonymous` as a catch-all for unknown function names, and
concrete subclasses for well-known functions.

The :data:`FUNC_REGISTRY` maps uppercase function names to their ``Func``
subclasses so that parsers can dispatch by name.

Existing GQL functions (43 keyword-based AST types) are **not** affected —
they stay as-is in ``expressions.py``.  This module covers functions that are
identified by name rather than by keyword token.
"""

from __future__ import annotations

from typing import ClassVar

from .expressions import CommonValueExpression, ValueExpression


class Func(CommonValueExpression):
    """Base class for generic functions: ``name(arg1, arg2, ...)``.

    Subclass with ``func_name`` ClassVar.  Optionally set ``min_args`` /
    ``max_args`` for arity validation at the parser level.

    The auto-registry (:data:`FUNC_REGISTRY`) maps uppercase names to
    subclasses.
    """

    func_name: ClassVar[str]
    min_args: ClassVar[int] = 0
    max_args: ClassVar[int | None] = None  # None = unlimited

    arguments: list[ValueExpression]


class Anonymous(Func):
    """Catch-all for unknown function names: ``name(arg1, arg2, ...)``.

    The *name* field stores the actual function name as it appeared in the
    source query.  ``func_name`` is left empty at the class level.
    """

    func_name: ClassVar[str] = ""
    name: str  # actual function name (instance field)


# =============================================================================
# Concrete subclasses — dialect-agnostic semantic concepts
# =============================================================================


class Replace(Func):
    """``replace(original, search, replacement)``"""

    func_name: ClassVar[str] = "replace"
    min_args: ClassVar[int] = 3
    max_args: ClassVar[int] = 3


class Pi(Func):
    """``pi()``"""

    func_name: ClassVar[str] = "pi"
    min_args: ClassVar[int] = 0
    max_args: ClassVar[int] = 0


class IsEmpty(Func):
    """``isEmpty(expr)``"""

    func_name: ClassVar[str] = "isEmpty"
    min_args: ClassVar[int] = 1
    max_args: ClassVar[int] = 1


class IsNaN(Func):
    """``isNaN(expr)``"""

    func_name: ClassVar[str] = "isNaN"
    min_args: ClassVar[int] = 1
    max_args: ClassVar[int] = 1


class Atan2(Func):
    """``atan2(y, x)``"""

    func_name: ClassVar[str] = "atan2"
    min_args: ClassVar[int] = 2
    max_args: ClassVar[int] = 2


class Haversin(Func):
    """``haversin(expr)``"""

    func_name: ClassVar[str] = "haversin"
    min_args: ClassVar[int] = 1
    max_args: ClassVar[int] = 1


# --- Neo4j utility functions ---


class RandomUUID(Func):
    """``randomUUID()``"""

    func_name: ClassVar[str] = "randomUUID"
    min_args: ClassVar[int] = 0
    max_args: ClassVar[int] = 0


class TimestampFunc(Func):
    """``timestamp()`` — returns epoch millis."""

    func_name: ClassVar[str] = "timestamp"
    min_args: ClassVar[int] = 0
    max_args: ClassVar[int] = 0


class ValueTypeFunc(Func):
    """``valueType(expr)``"""

    func_name: ClassVar[str] = "valueType"
    min_args: ClassVar[int] = 1
    max_args: ClassVar[int] = 1


class ElementId(Func):
    """``elementId(node_or_rel)``"""

    func_name: ClassVar[str] = "elementId"
    min_args: ClassVar[int] = 1
    max_args: ClassVar[int] = 1


class ToStringOrNull(Func):
    """``toStringOrNull(expr)``"""

    func_name: ClassVar[str] = "toStringOrNull"
    min_args: ClassVar[int] = 1
    max_args: ClassVar[int] = 1


class ToBooleanOrNull(Func):
    """``toBooleanOrNull(expr)``"""

    func_name: ClassVar[str] = "toBooleanOrNull"
    min_args: ClassVar[int] = 1
    max_args: ClassVar[int] = 1


class ToIntegerOrNull(Func):
    """``toIntegerOrNull(expr)``"""

    func_name: ClassVar[str] = "toIntegerOrNull"
    min_args: ClassVar[int] = 1
    max_args: ClassVar[int] = 1


class ToFloatOrNull(Func):
    """``toFloatOrNull(expr)``"""

    func_name: ClassVar[str] = "toFloatOrNull"
    min_args: ClassVar[int] = 1
    max_args: ClassVar[int] = 1


class ToBooleanList(Func):
    """``toBooleanList(list)``"""

    func_name: ClassVar[str] = "toBooleanList"
    min_args: ClassVar[int] = 1
    max_args: ClassVar[int] = 1


class ToIntegerList(Func):
    """``toIntegerList(list)``"""

    func_name: ClassVar[str] = "toIntegerList"
    min_args: ClassVar[int] = 1
    max_args: ClassVar[int] = 1


class ToFloatList(Func):
    """``toFloatList(list)``"""

    func_name: ClassVar[str] = "toFloatList"
    min_args: ClassVar[int] = 1
    max_args: ClassVar[int] = 1


class ToStringList(Func):
    """``toStringList(list)``"""

    func_name: ClassVar[str] = "toStringList"
    min_args: ClassVar[int] = 1
    max_args: ClassVar[int] = 1


# --- Neo4j spatial functions ---


class PointConstructor(Func):
    """``point({x: v, y: v [, z: v] [, crs: s]})``"""

    func_name: ClassVar[str] = "point"
    min_args: ClassVar[int] = 1
    max_args: ClassVar[int] = 1


class PointDistance(Func):
    """``point.distance(p1, p2)``"""

    func_name: ClassVar[str] = "point.distance"
    min_args: ClassVar[int] = 2
    max_args: ClassVar[int] = 2


class PointWithinBBox(Func):
    """``point.withinBBox(point, lowerLeft, upperRight)``"""

    func_name: ClassVar[str] = "point.withinBBox"
    min_args: ClassVar[int] = 3
    max_args: ClassVar[int] = 3


# --- Cypher functions (migrated from CypherXxxFunction AST classes) ---


class Tail(Func):
    """``tail(list)`` — returns all elements except the first."""

    func_name: ClassVar[str] = "tail"
    min_args: ClassVar[int] = 1
    max_args: ClassVar[int] = 1


class Head(Func):
    """``head(list)`` — returns the first element."""

    func_name: ClassVar[str] = "head"
    min_args: ClassVar[int] = 1
    max_args: ClassVar[int] = 1


class Last(Func):
    """``last(list)`` — returns the last element."""

    func_name: ClassVar[str] = "last"
    min_args: ClassVar[int] = 1
    max_args: ClassVar[int] = 1


class ReverseFunc(Func):
    """``reverse(list_or_string)`` — returns reversed list or string."""

    func_name: ClassVar[str] = "reverse"
    min_args: ClassVar[int] = 1
    max_args: ClassVar[int] = 1


class Rand(Func):
    """``rand()`` — returns a random float in [0, 1)."""

    func_name: ClassVar[str] = "rand"
    min_args: ClassVar[int] = 0
    max_args: ClassVar[int] = 0


class Round(Func):
    """``ROUND(expr)``"""

    func_name: ClassVar[str] = "ROUND"
    min_args: ClassVar[int] = 1
    max_args: ClassVar[int] = 1


class SignFunc(Func):
    """``sign(expr)`` — returns the signum of a number."""

    func_name: ClassVar[str] = "sign"
    min_args: ClassVar[int] = 1
    max_args: ClassVar[int] = 1


class Substring(Func):
    """``SUBSTRING(string, start [, length])``"""

    func_name: ClassVar[str] = "SUBSTRING"
    min_args: ClassVar[int] = 2
    max_args: ClassVar[int] = 3


class Labels(Func):
    """``LABELS(node_expression)``"""

    func_name: ClassVar[str] = "LABELS"
    min_args: ClassVar[int] = 1
    max_args: ClassVar[int] = 1


class Keys(Func):
    """``keys(expression)``"""

    func_name: ClassVar[str] = "keys"
    min_args: ClassVar[int] = 1
    max_args: ClassVar[int] = 1


class RangeFunc(Func):
    """``range(start, end [, step])``"""

    func_name: ClassVar[str] = "range"
    min_args: ClassVar[int] = 2
    max_args: ClassVar[int] = 3


class Size(Func):
    """``size(expr)`` — list length or string length."""

    func_name: ClassVar[str] = "size"
    min_args: ClassVar[int] = 1
    max_args: ClassVar[int] = 1


class Nodes(Func):
    """``nodes(path)`` — extract nodes from a path."""

    func_name: ClassVar[str] = "nodes"
    min_args: ClassVar[int] = 1
    max_args: ClassVar[int] = 1


class Relationships(Func):
    """``relationships(path)`` — extract relationships from a path."""

    func_name: ClassVar[str] = "relationships"
    min_args: ClassVar[int] = 1
    max_args: ClassVar[int] = 1


class TypeFunc(Func):
    """``type(relationship)`` — return relationship type as string."""

    func_name: ClassVar[str] = "type"
    min_args: ClassVar[int] = 1
    max_args: ClassVar[int] = 1


class Properties(Func):
    """``properties(node_or_rel)`` — return map of all properties."""

    func_name: ClassVar[str] = "properties"
    min_args: ClassVar[int] = 1
    max_args: ClassVar[int] = 1


class StartNode(Func):
    """``startNode(relationship)`` — return start node of a relationship."""

    func_name: ClassVar[str] = "startNode"
    min_args: ClassVar[int] = 1
    max_args: ClassVar[int] = 1


class EndNode(Func):
    """``endNode(relationship)`` — return end node of a relationship."""

    func_name: ClassVar[str] = "endNode"
    min_args: ClassVar[int] = 1
    max_args: ClassVar[int] = 1


class Split(Func):
    """``split(string, delimiter)`` — split string into list."""

    func_name: ClassVar[str] = "split"
    min_args: ClassVar[int] = 2
    max_args: ClassVar[int] = 2


class ToLower(Func):
    """``toLower(string)`` — convert string to lowercase."""

    func_name: ClassVar[str] = "toLower"
    min_args: ClassVar[int] = 1
    max_args: ClassVar[int] = 1


class ToUpper(Func):
    """``toUpper(string)`` — convert string to uppercase."""

    func_name: ClassVar[str] = "toUpper"
    min_args: ClassVar[int] = 1
    max_args: ClassVar[int] = 1


# =============================================================================
# Auto-registry
# =============================================================================

FUNC_REGISTRY: dict[str, type[Func]] = {}


def _build_func_registry() -> None:
    """Populate :data:`FUNC_REGISTRY` from all :class:`Func` subclasses."""
    for cls in Func.__subclasses__():
        if cls is not Anonymous and cls.func_name:
            FUNC_REGISTRY[cls.func_name.upper()] = cls


_build_func_registry()
