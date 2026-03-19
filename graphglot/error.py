from __future__ import annotations

import typing as t

from dataclasses import dataclass, field
from enum import Enum, auto

from graphglot.utils.helper import AutoName

# ---------------------------------------------------------------------------
# Span & Severity — canonical definitions, re-exported by lineage.models
# ---------------------------------------------------------------------------


class Severity(Enum):
    """Severity of a diagnostic."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    HINT = "hint"


@dataclass
class Span:
    """Source location range."""

    start_line: int
    start_column: int
    end_line: int
    end_column: int
    start_offset: int | None = None
    end_offset: int | None = None

    def __str__(self) -> str:
        return f"{self.start_line}:{self.start_column}-{self.end_line}:{self.end_column}"


# ---------------------------------------------------------------------------
# Unified Diagnostic
# ---------------------------------------------------------------------------


@dataclass
class Diagnostic:
    """Unified diagnostic from any pipeline phase."""

    code: str  # "GL01", "duplicate-alias", "parse-error", "token-error"
    message: str  # Human-readable, no ANSI, no baked-in position
    severity: Severity = Severity.ERROR
    phase: str = ""  # "lexer", "parser", "analysis"
    span: Span | None = None
    start_context: str = ""
    highlight: str = ""
    end_context: str = ""
    node: t.Any | None = None
    related: list[Span] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


def populate_highlight(diag: Diagnostic, query: str, context_chars: int = 100) -> None:
    """Fill start_context/highlight/end_context from span offsets + query text."""
    if not diag.span or diag.span.start_offset is None or diag.span.end_offset is None:
        return
    if diag.highlight:  # already populated (parser case)
        return
    start, end = diag.span.start_offset, diag.span.end_offset
    diag.start_context = query[max(0, start - context_chars) : start]
    diag.highlight = query[start:end]
    diag.end_context = query[end : end + context_chars]


def format_diagnostic(diag: Diagnostic, query: str = "", ansi: bool = True) -> str:
    """Format a Diagnostic for display.  Populates highlight from query if needed."""
    if query:
        populate_highlight(diag, query)
    pos = f" (line {diag.span.start_line}, col {diag.span.start_column})" if diag.span else ""
    header = f"[{diag.code}] {diag.message}{pos}"
    if diag.highlight:
        if ansi:
            snippet = f"{diag.start_context}\033[4m{diag.highlight}\033[0m{diag.end_context}"
        else:
            snippet = f"{diag.start_context}{diag.highlight}{diag.end_context}"
        return f"{header}\n{snippet}"
    return header


# ---------------------------------------------------------------------------
# Base exception
# ---------------------------------------------------------------------------


class GraphGlotError(Exception):
    pass


# ---------------------------------------------------------------------------
# TokenError
# ---------------------------------------------------------------------------


class TokenError(GraphGlotError):
    def __init__(
        self,
        message: str,
        line: int | None = None,
        col: int | None = None,
        start_offset: int | None = None,
        end_offset: int | None = None,
    ):
        super().__init__(message)
        self.line = line
        self.col = col
        self.start_offset = start_offset
        self.end_offset = end_offset

    def to_diagnostic(self) -> Diagnostic:
        span = (
            Span(
                start_line=self.line or 0,
                start_column=self.col or 0,
                end_line=self.line or 0,
                end_column=self.col or 0,
                start_offset=self.start_offset,
                end_offset=self.end_offset,
            )
            if self.line is not None
            else None
        )
        return Diagnostic(
            code="token-error",
            message=str(self),
            severity=Severity.ERROR,
            phase="lexer",
            span=span,
        )


# ---------------------------------------------------------------------------
# FeatureError
# ---------------------------------------------------------------------------


class FeatureError(GraphGlotError):
    """Raised when a required GQL feature is not supported by the dialect."""

    def __init__(
        self,
        message: str,
        feature_id: str | None = None,
        expression_type: str | None = None,
        line: int | None = None,
        col: int | None = None,
        start_offset: int | None = None,
        end_offset: int | None = None,
    ):
        super().__init__(message)
        self.feature_id = feature_id
        self.expression_type = expression_type
        self.line = line
        self.col = col
        self.start_offset = start_offset
        self.end_offset = end_offset

    def to_diagnostic(self) -> Diagnostic:
        span = (
            Span(
                start_line=self.line or 0,
                start_column=self.col or 0,
                end_line=self.line or 0,
                end_column=self.col or 0,
                start_offset=self.start_offset,
                end_offset=self.end_offset,
            )
            if self.line is not None
            else None
        )
        return Diagnostic(
            code=self.feature_id or "feature-error",
            message=str(self),
            severity=Severity.ERROR,
            phase="lexer",
            span=span,
        )


# ---------------------------------------------------------------------------
# ErrorLevel
# ---------------------------------------------------------------------------


class ErrorLevel(AutoName):
    IGNORE = auto()
    """Ignore all errors."""

    WARN = auto()
    """Log all errors."""

    RAISE = auto()
    """Collect all errors and raise a single exception."""

    IMMEDIATE = auto()
    """Immediately raise an exception on the first error found."""


# ---------------------------------------------------------------------------
# ParseError
# ---------------------------------------------------------------------------


class ParseError(GraphGlotError):
    def __init__(
        self,
        message: str,
        errors: list[dict[str, t.Any]] | None = None,
    ):
        super().__init__(message)
        self.errors = errors or []

    @classmethod
    def new(
        cls,
        message: str,
        description: str | None = None,
        line: int | None = None,
        col: int | None = None,
        start_context: str | None = None,
        highlight: str | None = None,
        end_context: str | None = None,
        into_expression: str | None = None,
        start_offset: int | None = None,
        end_offset: int | None = None,
    ) -> ParseError:
        return cls(
            message,
            [
                {
                    "description": description,
                    "line": line,
                    "col": col,
                    "start_context": start_context,
                    "highlight": highlight,
                    "end_context": end_context,
                    "into_expression": into_expression,
                    "start_offset": start_offset,
                    "end_offset": end_offset,
                }
            ],
        )

    def to_diagnostics(self) -> list[Diagnostic]:
        result: list[Diagnostic] = []
        for e in self.errors:
            span = (
                Span(
                    start_line=e.get("line", 0),
                    start_column=e.get("col", 0),
                    end_line=e.get("line", 0),
                    end_column=e.get("col", 0),
                    start_offset=e.get("start_offset"),
                    end_offset=e.get("end_offset"),
                )
                if e.get("line")
                else None
            )
            result.append(
                Diagnostic(
                    code="parse-error",
                    message=e.get("description") or str(self),
                    severity=Severity.ERROR,
                    phase="parser",
                    span=span,
                    start_context=e.get("start_context", ""),
                    highlight=e.get("highlight", ""),
                    end_context=e.get("end_context", ""),
                )
            )
        return result or [
            Diagnostic(
                code="parse-error",
                message=str(self),
                severity=Severity.ERROR,
                phase="parser",
            )
        ]


class _LazyParseError(ParseError):
    """ParseError that defers expensive message formatting until accessed."""

    def __init__(
        self,
        description: str,
        tok_line: int,
        tok_col: int,
        tok_start: int,
        tok_end: int,
        query: str,
        ctx_size: int,
    ):
        Exception.__init__(self, description)
        self._errors_list: list[dict[str, t.Any]] = []
        self._desc = description
        self._tok_line = tok_line
        self._tok_col = tok_col
        self._tok_start = tok_start
        self._tok_end = tok_end
        self._query = query
        self._ctx_size = ctx_size
        self._ready = False

    def _materialize(self) -> None:
        if self._ready:
            return
        self._ready = True
        s, e = self._tok_start, self._tok_end
        c = self._ctx_size
        start_ctx = self._query[max(s - c, 0) : s]
        highlight = self._query[s:e]
        end_ctx = self._query[e : e + c]
        self.args = (
            f"{self._desc}. Line {self._tok_line}, Col: {self._tok_col}.\n"
            f"  {start_ctx}\033[4m{highlight}\033[0m{end_ctx}",
        )
        self._errors_list = [
            {
                "description": self._desc,
                "line": self._tok_line,
                "col": self._tok_col,
                "start_context": start_ctx,
                "highlight": highlight,
                "end_context": end_ctx,
                "into_expression": None,
                "start_offset": self._tok_start,
                "end_offset": self._tok_end,
            }
        ]

    @property  # type: ignore[override]
    def errors(self) -> list[dict[str, t.Any]]:
        self._materialize()
        return self._errors_list

    @errors.setter
    def errors(self, value: list[dict[str, t.Any]]) -> None:
        self._errors_list = value

    def __str__(self) -> str:
        self._materialize()
        return super().__str__()

    def to_diagnostics(self) -> list[Diagnostic]:
        self._materialize()
        return super().to_diagnostics()


class ParseNotImplementedError(ParseError):
    """Raised when a feature is not implemented in the parser."""

    pass


# ---------------------------------------------------------------------------
# ValidationError
# ---------------------------------------------------------------------------


def span_from_node(node: t.Any) -> Span | None:
    """Extract a Span from an AST node's source_span and token range."""
    if node is None:
        return None
    source_span = getattr(node, "source_span", None)
    if source_span is None:
        return None
    start_tok = getattr(node, "_start_token", None)
    end_tok = getattr(node, "_end_token", None)
    if start_tok is None:
        return None
    return Span(
        start_line=start_tok.line,
        start_column=start_tok.col,
        end_line=(end_tok.line if end_tok else start_tok.line),
        end_column=(end_tok.col if end_tok else start_tok.col),
        start_offset=source_span[0],
        end_offset=source_span[1],
    )


class ValidationError(GraphGlotError):
    """Raised when AST-level semantic or structural validation fails."""

    def __init__(self, message: str, node: t.Any | None = None):
        super().__init__(message)
        self.node = node

    def to_diagnostic(self) -> Diagnostic:
        return Diagnostic(
            code="validation-error",
            message=str(self),
            severity=Severity.ERROR,
            phase="parser",
            span=span_from_node(self.node),
            node=self.node,
        )


# ---------------------------------------------------------------------------
# UnsupportedLineageError
# ---------------------------------------------------------------------------


class UnsupportedLineageError(GraphGlotError):
    """Raised when lineage analysis encounters an unsupported statement type."""

    def __init__(self, message: str, node: t.Any | None = None):
        super().__init__(message)
        self.node = node

    def to_diagnostic(self) -> Diagnostic:
        return Diagnostic(
            code="unsupported-lineage",
            message=str(self),
            severity=Severity.ERROR,
            phase="lineage",
            span=span_from_node(self.node),
            node=self.node,
        )


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


def concat_messages(errors: t.Sequence[t.Any], maximum: int) -> str:
    msg = [str(e) for e in errors[:maximum]]
    remaining = len(errors) - maximum
    if remaining > 0:
        msg.append(f"... and {remaining} more")
    return "\n\n".join(msg)


def merge_errors(errors: t.Sequence[ParseError]) -> list[dict[str, t.Any]]:
    return [e_dict for error in errors for e_dict in error.errors]
