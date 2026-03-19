"""Tests for the TCK loader module."""

from __future__ import annotations

import pytest

from tests.graphglot.tck.loader import (
    TCK_FEATURES_DIR,
    load_all_features,
    load_all_scenarios,
    load_feature_file,
)
from tests.graphglot.tck.models import ExpectedOutcome


@pytest.mark.tck
class TestLoadFeatureFile:
    """Tests for loading individual .feature files."""

    def test_load_match1_scenario_count(self):
        """Match1.feature has 5 normal scenarios + 6 outline scenarios (expanded)."""
        ff = load_feature_file(TCK_FEATURES_DIR / "clauses" / "match" / "Match1.feature")
        assert ff.feature_name == "Match1 - Match nodes"
        # 5 plain + [6]=1 + [7]=11 + [8]=16 + [9]=21 + [10]=21 + [11]=8 = 83 outline = 86 total
        assert len(ff.scenarios) > 50

    def test_query_extraction(self):
        """First scenario should have MATCH (n) RETURN n query."""
        ff = load_feature_file(TCK_FEATURES_DIR / "clauses" / "match" / "Match1.feature")
        first = ff.scenarios[0]
        assert "MATCH (n)" in first.query
        assert "RETURN n" in first.query

    def test_setup_queries(self):
        """Scenario [2] should have a CREATE setup query."""
        ff = load_feature_file(TCK_FEATURES_DIR / "clauses" / "match" / "Match1.feature")
        second = ff.scenarios[1]
        assert len(second.setup_queries) > 0
        assert "CREATE" in second.setup_queries[0]

    def test_positive_outcome(self):
        """Normal scenarios produce RESULT outcome."""
        ff = load_feature_file(TCK_FEATURES_DIR / "clauses" / "match" / "Match1.feature")
        first = ff.scenarios[0]
        assert first.outcome == ExpectedOutcome.RESULT
        assert first.is_positive

    def test_compile_error_outcome(self):
        """Error scenarios produce ERROR_COMPILE outcome with error type."""
        ff = load_feature_file(TCK_FEATURES_DIR / "clauses" / "match" / "Match1.feature")
        # Scenario [6] is first error scenario
        error_scenario = next(s for s in ff.scenarios if s.scenario_number == 6)
        assert error_scenario.outcome == ExpectedOutcome.ERROR_COMPILE
        assert error_scenario.error_type == "SyntaxError"
        assert error_scenario.error_detail == "InvalidParameterUse"

    def test_scenario_outline_expansion(self):
        """Scenario Outline [7] should expand into multiple rows."""
        ff = load_feature_file(TCK_FEATURES_DIR / "clauses" / "match" / "Match1.feature")
        outline_scenarios = [s for s in ff.scenarios if s.scenario_number == 7]
        assert len(outline_scenarios) == 11
        # Each should have a different outline_row
        rows = {s.outline_row for s in outline_scenarios}
        assert rows == set(range(11))

    def test_scenario_number_parsing(self):
        """Scenario names like '[1] Match nodes' get parsed correctly."""
        ff = load_feature_file(TCK_FEATURES_DIR / "clauses" / "match" / "Match1.feature")
        first = ff.scenarios[0]
        assert first.scenario_number == 1
        assert first.scenario_name == "Match non-existent nodes returns empty"

    def test_test_id_format(self):
        """Test IDs should be unique and readable."""
        ff = load_feature_file(TCK_FEATURES_DIR / "clauses" / "match" / "Match1.feature")
        ids = [s.test_id for s in ff.scenarios]
        # All unique
        assert len(ids) == len(set(ids))
        # First ID format
        assert ids[0].startswith("Match1__1_")

    def test_outline_test_id_has_row(self):
        """Outline expansions include __rowN suffix."""
        ff = load_feature_file(TCK_FEATURES_DIR / "clauses" / "match" / "Match1.feature")
        outline = next(s for s in ff.scenarios if s.outline_row is not None)
        assert "__row" in outline.test_id


@pytest.mark.tck
class TestLoadAllFeatures:
    """Tests for loading all .feature files."""

    def test_feature_file_count(self):
        """Should load feature files with scenarios (28 of 220 are empty placeholders)."""
        features = load_all_features()
        assert len(features) == 192

    def test_total_scenario_count(self):
        """Should have > 2500 scenarios across all files."""
        scenarios = load_all_scenarios()
        assert len(scenarios) > 2500

    def test_outcome_distribution(self):
        """Should have scenarios of all outcome types."""
        scenarios = load_all_scenarios()
        outcomes = {s.outcome for s in scenarios}
        assert ExpectedOutcome.RESULT in outcomes
        assert ExpectedOutcome.ERROR_COMPILE in outcomes
        assert ExpectedOutcome.ERROR_RUNTIME in outcomes

    def test_all_scenarios_have_queries(self):
        """Every scenario should have a non-empty query."""
        scenarios = load_all_scenarios()
        empty = [s for s in scenarios if not s.query.strip()]
        assert len(empty) == 0, f"{len(empty)} scenarios have empty queries"

    def test_runtime_error_detection(self):
        """Should detect runtime errors correctly."""
        scenarios = load_all_scenarios()
        runtime = [s for s in scenarios if s.is_runtime_error]
        assert len(runtime) > 0
        for s in runtime:
            assert s.error_type is not None

    def test_empty_result_detection(self):
        """Should detect empty result scenarios."""
        scenarios = load_all_scenarios()
        empty = [s for s in scenarios if s.outcome == ExpectedOutcome.RESULT_EMPTY]
        assert len(empty) > 0
