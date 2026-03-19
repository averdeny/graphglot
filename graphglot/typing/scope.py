"""Type scope — variable-to-type binding tracking."""

from __future__ import annotations

import typing as t

from dataclasses import dataclass
from enum import StrEnum

from graphglot.typing.types import GqlType

if t.TYPE_CHECKING:
    from graphglot.ast.base import Expression


class ScopeKind(StrEnum):
    ROOT = "root"
    QUERY = "query"
    PATTERN = "pattern"
    SUBQUERY = "subquery"


@dataclass
class TypeBinding:
    """A variable name bound to a type."""

    name: str
    type: GqlType
    node: Expression | None = None


class TypeScope:
    """Hierarchical scope for tracking variable-to-type bindings."""

    def __init__(self, kind: ScopeKind, parent: TypeScope | None = None):
        self.kind = kind
        self.parent = parent
        self._bindings: dict[str, TypeBinding] = {}

    def bind(self, name: str, typ: GqlType, node: Expression | None = None) -> None:
        """Bind a variable name to a type in this scope."""
        self._bindings[name] = TypeBinding(name=name, type=typ, node=node)

    def lookup(self, name: str) -> TypeBinding | None:
        """Look up a variable name, walking the parent chain."""
        binding = self._bindings.get(name)
        if binding is not None:
            return binding
        if self.parent is not None:
            return self.parent.lookup(name)
        return None

    def bindings(self) -> dict[str, TypeBinding]:
        """Return all bindings in this scope (not including parents)."""
        return dict(self._bindings)

    def __repr__(self) -> str:
        names = list(self._bindings.keys())
        return f"TypeScope({self.kind.value}, bindings={names})"
