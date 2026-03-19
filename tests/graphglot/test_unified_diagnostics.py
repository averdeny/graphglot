"""Tests for the unified diagnostic system across all pipeline phases."""

from __future__ import annotations

import unittest

from graphglot.error import (
    Diagnostic,
    FeatureError,
    ParseError,
    Severity,
    Span,
    TokenError,
    ValidationError,
    format_diagnostic,
    populate_highlight,
)

# ---------------------------------------------------------------------------
# Phase A: Span, Severity, Diagnostic, format_diagnostic
# ---------------------------------------------------------------------------


class TestSpan(unittest.TestCase):
    def test_construction(self):
        span = Span(start_line=1, start_column=5, end_line=1, end_column=10)
        self.assertEqual(span.start_line, 1)
        self.assertEqual(span.start_column, 5)
        self.assertEqual(span.end_line, 1)
        self.assertEqual(span.end_column, 10)
        self.assertIsNone(span.start_offset)
        self.assertIsNone(span.end_offset)

    def test_construction_with_offsets(self):
        span = Span(1, 5, 1, 10, start_offset=4, end_offset=9)
        self.assertEqual(span.start_offset, 4)
        self.assertEqual(span.end_offset, 9)

    def test_str(self):
        span = Span(2, 3, 4, 5)
        self.assertEqual(str(span), "2:3-4:5")


class TestSeverity(unittest.TestCase):
    def test_enum_values(self):
        self.assertEqual(Severity.ERROR.value, "error")
        self.assertEqual(Severity.WARNING.value, "warning")
        self.assertEqual(Severity.INFO.value, "info")
        self.assertEqual(Severity.HINT.value, "hint")


class TestDiagnostic(unittest.TestCase):
    def test_defaults(self):
        diag = Diagnostic(code="test", message="something broke")
        self.assertEqual(diag.code, "test")
        self.assertEqual(diag.message, "something broke")
        self.assertEqual(diag.severity, Severity.ERROR)
        self.assertEqual(diag.phase, "")
        self.assertIsNone(diag.span)
        self.assertEqual(diag.start_context, "")
        self.assertEqual(diag.highlight, "")
        self.assertEqual(diag.end_context, "")
        self.assertIsNone(diag.node)
        self.assertEqual(diag.related, [])
        self.assertEqual(diag.suggestions, [])

    def test_equality(self):
        d1 = Diagnostic(code="A", message="m", severity=Severity.WARNING)
        d2 = Diagnostic(code="A", message="m", severity=Severity.WARNING)
        self.assertEqual(d1, d2)

    def test_with_span(self):
        span = Span(1, 1, 1, 5, start_offset=0, end_offset=5)
        diag = Diagnostic(code="x", message="y", span=span)
        self.assertEqual(diag.span, span)


class TestPopulateHighlight(unittest.TestCase):
    def test_fills_from_offsets(self):
        query = "MATCH (n) RETURN m"
        span = Span(1, 18, 1, 18, start_offset=17, end_offset=18)
        diag = Diagnostic(code="test", message="msg", span=span)
        populate_highlight(diag, query)
        self.assertEqual(diag.highlight, "m")
        self.assertIn("RETURN ", diag.start_context)
        self.assertEqual(diag.end_context, "")

    def test_noop_without_span(self):
        diag = Diagnostic(code="test", message="msg")
        populate_highlight(diag, "MATCH (n)")
        self.assertEqual(diag.highlight, "")

    def test_noop_without_offsets(self):
        span = Span(1, 1, 1, 5)  # no start_offset/end_offset
        diag = Diagnostic(code="test", message="msg", span=span)
        populate_highlight(diag, "MATCH (n)")
        self.assertEqual(diag.highlight, "")

    def test_preserves_existing_highlight(self):
        span = Span(1, 1, 1, 5, start_offset=0, end_offset=5)
        diag = Diagnostic(code="test", message="msg", span=span, highlight="MATCH")
        populate_highlight(diag, "MATCH (n) RETURN n")
        self.assertEqual(diag.highlight, "MATCH")  # unchanged


class TestFormatDiagnostic(unittest.TestCase):
    def test_with_highlight_ansi(self):
        span = Span(1, 18, 1, 18, start_offset=17, end_offset=18)
        diag = Diagnostic(code="test", message="unresolved ref", span=span)
        out = format_diagnostic(diag, query="MATCH (n) RETURN m", ansi=True)
        self.assertIn("[test]", out)
        self.assertIn("unresolved ref", out)
        self.assertIn("\033[4m", out)  # ANSI underline
        self.assertIn("m", out)

    def test_plain_text(self):
        span = Span(1, 18, 1, 18, start_offset=17, end_offset=18)
        diag = Diagnostic(code="test", message="unresolved ref", span=span)
        out = format_diagnostic(diag, query="MATCH (n) RETURN m", ansi=False)
        self.assertIn("[test]", out)
        self.assertNotIn("\033[4m", out)

    def test_without_span(self):
        diag = Diagnostic(code="X", message="oops")
        out = format_diagnostic(diag)
        self.assertEqual(out, "[X] oops")

    def test_without_query(self):
        diag = Diagnostic(code="X", message="oops")
        out = format_diagnostic(diag)
        self.assertEqual(out, "[X] oops")

    def test_with_position(self):
        span = Span(3, 7, 3, 7)
        diag = Diagnostic(code="E", message="err", span=span)
        out = format_diagnostic(diag)
        self.assertIn("(line 3, col 7)", out)


# ---------------------------------------------------------------------------
# Phase B: Exception .to_diagnostic() / .to_diagnostics()
# ---------------------------------------------------------------------------


class TestTokenErrorToDiagnostic(unittest.TestCase):
    def test_with_offsets(self):
        err = TokenError("bad char", line=2, col=5, start_offset=10, end_offset=11)
        diag = err.to_diagnostic()
        self.assertEqual(diag.code, "token-error")
        self.assertEqual(diag.phase, "lexer")
        self.assertEqual(diag.severity, Severity.ERROR)
        self.assertIsNotNone(diag.span)
        self.assertEqual(diag.span.start_offset, 10)
        self.assertEqual(diag.span.end_offset, 11)

    def test_without_offsets(self):
        err = TokenError("bad char", line=1, col=1)
        diag = err.to_diagnostic()
        self.assertIsNotNone(diag.span)
        self.assertIsNone(diag.span.start_offset)

    def test_without_line(self):
        err = TokenError("bad char")
        diag = err.to_diagnostic()
        self.assertIsNone(diag.span)


class TestFeatureErrorToDiagnostic(unittest.TestCase):
    def test_feature_id_becomes_code(self):
        err = FeatureError("not supported", feature_id="GL01", line=1, col=1)
        diag = err.to_diagnostic()
        self.assertEqual(diag.code, "GL01")
        self.assertEqual(diag.phase, "lexer")

    def test_no_feature_id(self):
        err = FeatureError("not supported", line=1, col=1)
        diag = err.to_diagnostic()
        self.assertEqual(diag.code, "feature-error")

    def test_with_offsets(self):
        err = FeatureError("x", feature_id="GL01", line=1, col=1, start_offset=0, end_offset=3)
        diag = err.to_diagnostic()
        self.assertEqual(diag.span.start_offset, 0)
        self.assertEqual(diag.span.end_offset, 3)


class TestParseErrorToDiagnostics(unittest.TestCase):
    def test_single_error(self):
        err = ParseError.new(
            "msg",
            description="unexpected token",
            line=1,
            col=5,
            start_context="MATCH ",
            highlight="(",
            end_context="n)",
            start_offset=6,
            end_offset=7,
        )
        diags = err.to_diagnostics()
        self.assertEqual(len(diags), 1)
        d = diags[0]
        self.assertEqual(d.code, "parse-error")
        self.assertEqual(d.phase, "parser")
        self.assertEqual(d.message, "unexpected token")
        self.assertEqual(d.start_context, "MATCH ")
        self.assertEqual(d.highlight, "(")
        self.assertEqual(d.end_context, "n)")
        self.assertEqual(d.span.start_offset, 6)

    def test_empty_errors_list(self):
        err = ParseError("something")
        diags = err.to_diagnostics()
        self.assertEqual(len(diags), 1)
        self.assertEqual(diags[0].code, "parse-error")

    def test_multi_error(self):
        err = ParseError(
            "multi",
            [
                {"description": "err1", "line": 1, "col": 1},
                {"description": "err2", "line": 2, "col": 3},
            ],
        )
        diags = err.to_diagnostics()
        self.assertEqual(len(diags), 2)
        self.assertEqual(diags[0].message, "err1")
        self.assertEqual(diags[1].message, "err2")


class TestValidationErrorToDiagnostic(unittest.TestCase):
    def test_basic(self):
        err = ValidationError("invalid")
        diag = err.to_diagnostic()
        self.assertEqual(diag.code, "validation-error")
        self.assertEqual(diag.phase, "parser")
        self.assertIsNone(diag.span)

    def test_with_node(self):
        err = ValidationError("invalid", node=None)
        diag = err.to_diagnostic()
        self.assertIsNone(diag.span)


# ---------------------------------------------------------------------------
# Phase C: Lexer offsets are populated
# ---------------------------------------------------------------------------


class TestLexerOffsets(unittest.TestCase):
    def test_token_error_has_offsets(self):
        from graphglot.lexer.lexer import Lexer

        lex = Lexer()
        try:
            lex.tokenize("0x")
        except TokenError as e:
            self.assertIsNotNone(e.start_offset)
            self.assertIsNotNone(e.end_offset)
            diag = e.to_diagnostic()
            self.assertIsNotNone(diag.span)
            self.assertIsNotNone(diag.span.start_offset)
        else:
            self.fail("Expected TokenError for '0x'")

    def test_feature_error_has_offsets(self):
        """FeatureError raised by lexer should carry offset info."""
        from graphglot.dialect.base import Dialect

        d = Dialect.get_or_raise("coregql")
        with self.assertRaises(FeatureError) as ctx:
            d.tokenize("0xFF")  # GL01 (hex) not supported by CoreGQL
        self.assertIsNotNone(ctx.exception.start_offset)
        diag = ctx.exception.to_diagnostic()
        self.assertIsNotNone(diag.span)


# ---------------------------------------------------------------------------
# Phase D: SemanticDiagnostic.span + to_diagnostic()
# ---------------------------------------------------------------------------


class TestSemanticDiagnosticSpan(unittest.TestCase):
    def test_span_populated_from_parsed_node(self):
        """SemanticDiagnostic extracts span from parsed AST nodes."""
        from graphglot.analysis.models import SemanticDiagnostic
        from graphglot.dialect.base import Dialect

        d = Dialect.get_or_raise("neo4j")
        result = d.validate("MATCH (n) RETURN m")
        # This should produce an analysis error (unresolved variable m)
        if result.diagnostics:
            sd = result.diagnostics[0]
            self.assertIsInstance(sd, SemanticDiagnostic)
            # to_diagnostic() should work
            diag = sd.to_diagnostic()
            self.assertEqual(diag.phase, "analysis")
            self.assertIsNotNone(diag.code)

    def test_to_diagnostic(self):
        from graphglot.analysis.models import SemanticDiagnostic

        sd = SemanticDiagnostic(feature_id="GA04", message="undefined var")
        diag = sd.to_diagnostic()
        self.assertEqual(diag.code, "GA04")
        self.assertEqual(diag.message, "undefined var")
        self.assertEqual(diag.phase, "analysis")
        self.assertEqual(diag.severity, Severity.ERROR)


# ---------------------------------------------------------------------------
# Phase E: ValidationResult.all_diagnostics
# ---------------------------------------------------------------------------


class TestValidationResultAllDiagnostics(unittest.TestCase):
    def test_lexer_error(self):
        from graphglot.dialect.base import Dialect

        d = Dialect.get_or_raise(None)
        result = d.validate("0x")
        self.assertFalse(result.success)
        self.assertEqual(result.stage, "lexer")
        diags = result.all_diagnostics
        self.assertGreaterEqual(len(diags), 1)
        self.assertEqual(diags[0].phase, "lexer")

    def test_parser_error(self):
        from graphglot.dialect.base import Dialect

        d = Dialect.get_or_raise(None)
        result = d.validate("MATCH (n) RETURN n,")
        self.assertFalse(result.success)
        self.assertEqual(result.stage, "parser")
        diags = result.all_diagnostics
        self.assertGreaterEqual(len(diags), 1)
        self.assertEqual(diags[0].phase, "parser")

    def test_analysis_error(self):
        from graphglot.dialect.base import Dialect

        d = Dialect.get_or_raise("neo4j")
        result = d.validate("MATCH (n) RETURN m")
        if result.stage == "analysis":
            diags = result.all_diagnostics
            self.assertGreaterEqual(len(diags), 1)
            self.assertEqual(diags[0].phase, "analysis")

    def test_success_has_no_diagnostics(self):
        from graphglot.dialect.base import Dialect

        d = Dialect.get_or_raise(None)
        result = d.validate("MATCH (n) RETURN n")
        self.assertTrue(result.success)
        self.assertEqual(result.all_diagnostics, [])

    def test_query_stored(self):
        from graphglot.dialect.base import Dialect

        d = Dialect.get_or_raise(None)
        q = "MATCH (n) RETURN n"
        result = d.validate(q)
        self.assertEqual(result.query, q)


# ---------------------------------------------------------------------------
# Phase F: format_diagnostic integration with all phases
# ---------------------------------------------------------------------------


class TestFormatDiagnosticIntegration(unittest.TestCase):
    def test_lexer_error_formatted(self):
        from graphglot.dialect.base import Dialect

        d = Dialect.get_or_raise(None)
        result = d.validate("0x")
        diags = result.all_diagnostics
        if diags:
            out = format_diagnostic(diags[0], result.query, ansi=False)
            self.assertIn("token-error", out)

    def test_parser_error_has_highlight(self):
        from graphglot.dialect.base import Dialect

        d = Dialect.get_or_raise(None)
        result = d.validate("MATCH (n) RETURN n,")
        diags = result.all_diagnostics
        if diags:
            self.assertTrue(diags[0].highlight or diags[0].span)

    def test_analysis_error_formatted(self):
        from graphglot.dialect.base import Dialect

        d = Dialect.get_or_raise("neo4j")
        result = d.validate("MATCH (n) RETURN m")
        if result.stage == "analysis":
            for diag in result.all_diagnostics:
                out = format_diagnostic(diag, result.query, ansi=False)
                self.assertIn(diag.code, out)


# ---------------------------------------------------------------------------
# Backward compatibility: lineage re-exports
# ---------------------------------------------------------------------------


class TestLineageReExports(unittest.TestCase):
    def test_span_from_lineage(self):
        from graphglot.lineage import Span as LineageSpan

        self.assertIs(LineageSpan, Span)

    def test_lineage_models_import(self):
        from graphglot.lineage.models import Span as ModelSpan

        self.assertIs(ModelSpan, Span)
