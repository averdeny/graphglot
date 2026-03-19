"""Macro AST nodes for @-prefixed syntax.

These nodes represent macro variable references (@name) and macro invocations
(@name(args...)) that can appear in any expression position via the
macro-aware Expression.__init__ bypass.
"""

from __future__ import annotations

from .base import Expression, field, nonstandard


@nonstandard("Macro extension: @name variable reference")
class MacroVar(Expression):
    """A macro variable reference: @name (no parentheses)."""

    __is_macro__ = True
    name: str


@nonstandard("Macro extension: @name() function invocation")
class MacroCall(Expression):
    """A macro invocation: @name() or @name(arg1, arg2, ...)."""

    __is_macro__ = True
    name: str
    arguments: list[Expression] = field(default_factory=list)
