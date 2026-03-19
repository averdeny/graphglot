"""Data models for semantic analysis."""

from __future__ import annotations

import typing as t

from dataclasses import dataclass, field

from graphglot.error import Diagnostic, Severity, Span

if t.TYPE_CHECKING:
    from graphglot.ast.base import Expression
    from graphglot.dialect.base import Dialect
    from graphglot.lineage.models import LineageGraph


@dataclass
class AnalysisContext:
    """Context passed to each analysis rule."""

    expression: Expression
    dialect: Dialect
    lineage: LineageGraph | None = None


@dataclass
class SemanticDiagnostic:
    """A single diagnostic emitted by a semantic analysis rule."""

    feature_id: str
    message: str
    node: Expression | None = None
    line: int | None = field(default=None, init=False)
    col: int | None = field(default=None, init=False)
    span: Span | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        cur = self.node
        while cur is not None:
            start_tok = getattr(cur, "_start_token", None)
            if start_tok is not None:
                self.line = start_tok.line
                self.col = start_tok.col
                end_tok = getattr(cur, "_end_token", None) or start_tok
                self.span = Span(
                    start_line=start_tok.line,
                    start_column=start_tok.col,
                    end_line=end_tok.line,
                    end_column=end_tok.col,
                    start_offset=start_tok.start,
                    end_offset=end_tok.end + 1,
                )
                return
            cur = getattr(cur, "_parent", None)

    def __str__(self) -> str:
        pos = f" (line {self.line}, col {self.col})" if self.line is not None else ""
        return f"[{self.feature_id}] {self.message}{pos}"

    def to_diagnostic(self) -> Diagnostic:
        return Diagnostic(
            code=self.feature_id,
            message=self.message,
            severity=Severity.ERROR,
            phase="analysis",
            span=self.span,
            node=self.node,
        )


@dataclass
class AnalysisResult:
    """Result of running semantic analysis on an expression."""

    diagnostics: list[SemanticDiagnostic] = field(default_factory=list)
    features: set[str] = field(default_factory=set)

    @property
    def ok(self) -> bool:
        """True when no diagnostics were emitted."""
        return len(self.diagnostics) == 0
