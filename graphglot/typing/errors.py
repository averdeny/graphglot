"""Type diagnostics for type inference."""

from __future__ import annotations

import typing as t

from dataclasses import dataclass
from enum import StrEnum

if t.TYPE_CHECKING:
    from graphglot.ast.base import Expression


class Severity(StrEnum):
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"


@dataclass
class TypeDiagnostic:
    """A single diagnostic emitted during type annotation."""

    message: str
    severity: Severity = Severity.WARNING
    node: Expression | None = None

    def __repr__(self) -> str:
        return f"TypeDiagnostic({self.severity.value}: {self.message})"
