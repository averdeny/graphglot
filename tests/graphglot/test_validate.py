"""Tests for Dialect.validate() — unified pipeline with feature reporting."""

from __future__ import annotations

import unittest

from graphglot import features as F
from graphglot.dialect import Dialect, ValidationResult
from graphglot.dialect.neo4j import Neo4j
from graphglot.error import FeatureError, ParseError, TokenError
from graphglot.features import ALL_FEATURES


class TestValidateSuccess(unittest.TestCase):
    """Valid queries should return success with features."""

    def test_simple_match_return(self):
        result = Dialect().validate("MATCH (n) RETURN n")
        self.assertTrue(result.success)
        self.assertEqual(result.stage, "ok")
        self.assertIsNone(result.error)
        self.assertIsInstance(result.features, set)
        self.assertGreater(len(result.expressions), 0)

    def test_features_empty_diagnostics(self):
        result = Dialect().validate("MATCH (n) RETURN n")
        self.assertEqual(result.diagnostics, [])


class TestValidateLexerFailure(unittest.TestCase):
    """Lexer-stage failures should be caught."""

    def test_unterminated_string(self):
        result = Dialect().validate("MATCH (n) WHERE n.name = 'unterminated")
        self.assertFalse(result.success)
        self.assertEqual(result.stage, "lexer")
        self.assertIsInstance(result.error, TokenError)
        self.assertIn("Unterminated string literal", str(result.error))

    def test_lexer_feature_error(self):
        """Hex literal with GL01 unsupported -> FeatureError at lexer stage."""

        class _NoGL01(Dialect):
            SUPPORTED_FEATURES = ALL_FEATURES - {F.GL01}

        result = _NoGL01().validate("RETURN 0xFF")
        self.assertFalse(result.success)
        self.assertEqual(result.stage, "lexer")
        self.assertIsInstance(result.error, FeatureError)
        self.assertEqual(result.error.feature_id, "GL01")


class TestValidateParserFailure(unittest.TestCase):
    """Parser-stage failures should be caught."""

    def test_syntax_error(self):
        result = Dialect().validate("MATCH RETURN")
        self.assertFalse(result.success)
        self.assertEqual(result.stage, "parser")
        self.assertIsInstance(result.error, ParseError)

    def test_parser_feature_error(self):
        """DIFFERENT EDGES with G002 unsupported -> FeatureError at parser stage."""

        class _NoG002(Dialect):
            SUPPORTED_FEATURES = ALL_FEATURES - {F.G002}

        result = _NoG002().validate("MATCH DIFFERENT EDGES (n)-[e]->(m) RETURN n")
        self.assertFalse(result.success)
        self.assertEqual(result.stage, "parser")
        self.assertIsInstance(result.error, FeatureError)
        self.assertEqual(result.error.feature_id, "G002")


class TestValidateAnalysisFailure(unittest.TestCase):
    """Semantic analysis failures should be reported."""

    def test_horizontal_aggregation_without_ge09(self):
        """Aggregate in list constructor without GE09 -> analysis failure."""

        class _NoGE09(Dialect):
            SUPPORTED_FEATURES = ALL_FEATURES - {F.GE09}

        result = _NoGE09().validate("MATCH (n) RETURN [COUNT(n)]")
        self.assertFalse(result.success)
        self.assertEqual(result.stage, "analysis")
        self.assertIsNone(result.error)
        self.assertGreater(len(result.diagnostics), 0)
        self.assertEqual(result.diagnostics[0].feature_id, "GE09")
        # Expressions should still be present on analysis failure
        self.assertGreater(len(result.expressions), 0)


class TestValidateNeo4j(unittest.TestCase):
    """Neo4j dialect-specific validation."""

    def test_neo4j_session_command(self):
        """Neo4j doesn't support SESSION SET -> FeatureError."""
        result = Neo4j().validate("SESSION SET SCHEMA HOME_SCHEMA")
        self.assertFalse(result.success)
        self.assertEqual(result.stage, "parser")
        self.assertIsInstance(result.error, FeatureError)

    def test_neo4j_valid_query(self):
        result = Neo4j().validate("MATCH (n) RETURN n")
        self.assertTrue(result.success)
        self.assertEqual(result.stage, "ok")


class TestValidateFeatureTracking(unittest.TestCase):
    """Feature collection from lexer + AST."""

    def test_decimal_literal_features(self):
        """Decimal literal 1.5 -> features includes GL04."""
        result = Dialect().validate("RETURN 1.5")
        self.assertTrue(result.success)
        feature_ids = {f.id for f in result.features}
        self.assertIn("GL04", feature_ids)

    def test_different_edges_features(self):
        """DIFFERENT EDGES -> features includes G002."""
        result = Dialect().validate("MATCH DIFFERENT EDGES (n)-[e]->(m) RETURN n")
        self.assertTrue(result.success)
        feature_ids = {f.id for f in result.features}
        self.assertIn("G002", feature_ids)

    def test_comment_features(self):
        """Double-dash comment -> features includes GB02."""
        result = Dialect().validate("-- comment\nMATCH (n) RETURN n")
        self.assertTrue(result.success)
        feature_ids = {f.id for f in result.features}
        self.assertIn("GB02", feature_ids)


class TestAnalysisFeaturesInValidationResult(unittest.TestCase):
    """Analysis-level features should appear in ValidationResult.features."""

    def test_ga04_in_features_when_supported(self):
        """Universal comparison (GA04) detected in features on success."""
        result = Dialect().validate("MATCH (n) WHERE 'hello' = 1 RETURN n")
        self.assertTrue(result.success)
        feature_ids = {f.id for f in result.features}
        self.assertIn("GA04", feature_ids)

    def test_ga07_in_features_when_supported(self):
        """ORDER BY non-output variable (GA07) detected in features on success."""
        result = Dialect().validate("MATCH (n), (m) RETURN n ORDER BY m")
        self.assertTrue(result.success)
        feature_ids = {f.id for f in result.features}
        self.assertIn("GA07", feature_ids)

    def test_ge09_in_features_when_supported(self):
        """Horizontal aggregation (GE09) detected in features on success."""
        result = Dialect().validate("MATCH (n) RETURN [COUNT(n)]")
        self.assertTrue(result.success)
        feature_ids = {f.id for f in result.features}
        self.assertIn("GE09", feature_ids)

    def test_analysis_failure_includes_features(self):
        """Analysis failure path also includes detected features."""

        class _NoGA04(Dialect):
            SUPPORTED_FEATURES = ALL_FEATURES - {F.GA04}

        result = _NoGA04().validate("MATCH (n) WHERE 'hello' = 1 RETURN n")
        self.assertFalse(result.success)
        self.assertEqual(result.stage, "analysis")
        feature_ids = {f.id for f in result.features}
        self.assertIn("GA04", feature_ids)


class TestValidationResultDefaults(unittest.TestCase):
    """ValidationResult dataclass defaults."""

    def test_defaults(self):
        r = ValidationResult(success=True, stage="ok")
        self.assertIsNone(r.error)
        self.assertEqual(r.features, set())
        self.assertEqual(r.diagnostics, [])
        self.assertEqual(r.expressions, [])
