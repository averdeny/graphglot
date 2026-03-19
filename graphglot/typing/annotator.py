"""TypeAnnotator — bottom-up type inference for GQL ASTs."""

from __future__ import annotations

import typing as t

from dataclasses import dataclass, field

from graphglot.typing.errors import Severity, TypeDiagnostic
from graphglot.typing.scope import ScopeKind, TypeScope
from graphglot.typing.types import GqlType

if t.TYPE_CHECKING:
    from graphglot.ast.base import Expression


@dataclass
class ExternalContext:
    """User-provided type info for what can't be inferred from the AST alone."""

    parameter_types: dict[str, GqlType] = field(default_factory=dict)
    property_types: dict[tuple[str, str], GqlType] = field(default_factory=dict)


@dataclass
class AnnotationResult:
    """Result of running type annotation on an expression."""

    diagnostics: list[TypeDiagnostic] = field(default_factory=list)
    annotated_count: int = 0

    @property
    def ok(self) -> bool:
        return all(d.severity != Severity.ERROR for d in self.diagnostics)


class TypeAnnotator:
    """Bottom-up type inference for GQL ASTs.

    Walks the AST in post-order (leaves first), setting ``_resolved_type``
    on every visited node.
    """

    def __init__(
        self,
        external_context: ExternalContext | None = None,
        dialect: t.Any | None = None,
    ):
        self.external_context = external_context or ExternalContext()
        self.dialect = dialect
        self._diagnostics: list[TypeDiagnostic] = []
        self._count = 0
        self._scope_stack: list[TypeScope] = []

    @property
    def current_scope(self) -> TypeScope:
        return self._scope_stack[-1]

    def push_scope(self, kind: ScopeKind) -> TypeScope:
        scope = TypeScope(kind=kind, parent=self._scope_stack[-1] if self._scope_stack else None)
        self._scope_stack.append(scope)
        return scope

    def pop_scope(self) -> TypeScope:
        return self._scope_stack.pop()

    def add_diagnostic(
        self,
        message: str,
        severity: Severity = Severity.WARNING,
        node: Expression | None = None,
    ) -> None:
        self._diagnostics.append(TypeDiagnostic(message=message, severity=severity, node=node))

    def annotate(self, expression: Expression) -> AnnotationResult:
        """Run type inference. Sets ``_resolved_type`` on every visited node."""
        from graphglot.typing.rules import TYPE_RULE_REGISTRY

        self._registry = TYPE_RULE_REGISTRY
        self._diagnostics = []
        self._count = 0
        self._scope_stack = [TypeScope(kind=ScopeKind.ROOT)]
        self._annotate_node(expression)
        return AnnotationResult(diagnostics=self._diagnostics, annotated_count=self._count)

    def _annotate_node(self, node: Expression) -> GqlType:
        """Annotate a single node and its children. Returns the resolved type."""
        rule = self._registry.get(type(node))
        if rule:
            resolved = rule(self, node)
        else:
            # No specific rule — annotate children, resolve to UNKNOWN
            for child in node.children():
                self._annotate_node(child)
            resolved = GqlType.unknown()
        node._resolved_type = resolved
        self._count += 1
        return resolved

    def annotate_children(self, node: Expression) -> None:
        """Helper: annotate all children of a node without setting its own type."""
        for child in node.children():
            self._annotate_node(child)

    def annotate_child(self, child: Expression) -> GqlType:
        """Helper: annotate a single child and return its resolved type."""
        return self._annotate_node(child)
