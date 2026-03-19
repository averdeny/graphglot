"""Generators for macro AST nodes."""

from __future__ import annotations

import typing as t

from graphglot.ast.macros import MacroCall, MacroVar
from graphglot.generator.fragment import Fragment, parens, seq
from graphglot.generator.registry import generates

if t.TYPE_CHECKING:
    from graphglot.generator.base import Generator


@generates(MacroVar)
def generate_macro_var(gen: Generator, expr: MacroVar) -> Fragment:
    return Fragment(f"@{expr.name}")


@generates(MacroCall)
def generate_macro_call(gen: Generator, expr: MacroCall) -> Fragment:
    if expr.arguments:
        args = gen.join([gen.dispatch(a) for a in expr.arguments], sep=", ")
        return seq(f"@{expr.name}", parens(args), sep="")
    return Fragment(f"@{expr.name}()")
