"""Tests for analysis integration with type annotations."""

from graphglot.dialect.base import Dialect
from graphglot.features import ALL_FEATURES, get_feature


def _make_dialect(exclude_features: list[str]):
    """Create a dialect without specified features."""
    excluded = {get_feature(f) for f in exclude_features}

    class _TestDialect(Dialect):
        SUPPORTED_FEATURES = ALL_FEATURES - excluded

    return _TestDialect()


class TestGA09WithTypes:
    def test_path_comparison_detected(self):
        d = _make_dialect(["GA09"])
        results = d.analyze("MATCH p = (a)-[e]->(b) WHERE p = p RETURN p")
        diags = [diag for r in results for diag in r.diagnostics if diag.feature_id == "GA09"]
        assert len(diags) == 1
        assert "path variable" in diags[0].message.lower()

    def test_no_path_comparison_no_diagnostic(self):
        d = _make_dialect(["GA09"])
        results = d.analyze("MATCH (a)-[e]->(b) WHERE a = b RETURN a")
        diags = [diag for r in results for diag in r.diagnostics if diag.feature_id == "GA09"]
        assert len(diags) == 0

    def test_path_in_one_side_only(self):
        d = _make_dialect(["GA09"])
        results = d.analyze("MATCH p = (a)-[e]->(b) WHERE p = a RETURN p")
        diags = [diag for r in results for diag in r.diagnostics if diag.feature_id == "GA09"]
        assert len(diags) == 1


class TestGA07WithTypes:
    def test_discarded_variable(self):
        d = _make_dialect(["GA07"])
        results = d.analyze("MATCH (a)-[e]->(b) RETURN a ORDER BY b")
        diags = [diag for r in results for diag in r.diagnostics if diag.feature_id == "GA07"]
        assert len(diags) == 1

    def test_no_discarded_variable(self):
        d = _make_dialect(["GA07"])
        results = d.analyze("MATCH (a)-[e]->(b) RETURN a, b ORDER BY b")
        diags = [diag for r in results for diag in r.diagnostics if diag.feature_id == "GA07"]
        assert len(diags) == 0


class TestAnnotationResultOk:
    def test_ok_result(self):
        """TypeAnnotator produces ok=True for valid queries."""
        from graphglot.typing import TypeAnnotator

        d = Dialect.get_or_raise("ir")
        exprs = d.parse("MATCH (n) RETURN n")
        result = TypeAnnotator().annotate(exprs[0])
        assert result.ok
        assert result.annotated_count > 0
