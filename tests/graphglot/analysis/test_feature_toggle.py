"""
Tests for unsupported feature validation during semantic analysis.

Analogous to tests/graphglot/lexer/test_feature_toggle.py and
tests/graphglot/parser/test_feature_toggle.py, but for features
whose restrictions are enforced by the semantic analysis module
(GA04, GA07, GA09, GE04, GE05, GE09, GG22, GG23, GP14, GP15, GQ17).
"""

import pytest

from graphglot import features as F
from graphglot.analysis import SemanticAnalyzer
from graphglot.dialect import Dialect
from graphglot.features import ALL_FEATURES, Feature
from graphglot.typing.annotator import ExternalContext
from graphglot.typing.types import GqlType

# ---------------------------------------------------------------------------
# Test cases: (feature, query_that_violates_the_restriction)
#
# Each query is *valid GQL* when the feature IS supported.
# When the feature is NOT supported, semantic analysis should flag it.
# ---------------------------------------------------------------------------
TEST_CASES = [
    # GA04: Universal comparison (type-incompatible comparisons)
    pytest.param(
        F.GA04,
        "MATCH (n) WHERE 'hello' = 1 RETURN n",
        id="GA04_string_vs_integer",
    ),
    pytest.param(
        F.GA04,
        "MATCH (n) WHERE TRUE = 1 RETURN n",
        id="GA04_boolean_vs_integer",
    ),
    # GA07: Ordering by discarded binding variables
    pytest.param(
        F.GA07,
        "MATCH (n)-[e]->(m) RETURN n ORDER BY m",
        id="GA07_order_by_discarded_variable",
    ),
    pytest.param(
        F.GA07,
        "MATCH (n)-[e]->(m) RETURN n.name ORDER BY m.age",
        id="GA07_order_by_property_of_discarded_variable",
    ),
    pytest.param(
        F.GA07,
        "MATCH (a)-[e]->(b)-[f]->(c) RETURN a ORDER BY b, c",
        id="GA07_order_by_multiple_discarded_variables",
    ),
    pytest.param(
        F.GA07,
        "MATCH (n)-[e]->(m) RETURN n AS x ORDER BY m",
        id="GA07_order_by_discarded_variable_with_alias",
    ),
    # GE09: Horizontal aggregation (aggregate inside list constructor)
    pytest.param(
        F.GE09,
        "MATCH (n) RETURN [COUNT(n)]",
        id="GE09_count_in_list_constructor",
    ),
    pytest.param(
        F.GE09,
        "MATCH (n) RETURN [SUM(n.val)]",
        id="GE09_sum_in_list_constructor",
    ),
    pytest.param(
        F.GE09,
        "MATCH (n) RETURN [[COUNT(n)]]",
        id="GE09_aggregate_in_nested_list",
    ),
    # GA09: Comparison of paths
    pytest.param(
        F.GA09,
        "MATCH p = (a)-[e]->(b), q = (c)-[f]->(d) WHERE p = q RETURN p",
        id="GA09_path_equality_comparison",
    ),
    pytest.param(
        F.GA09,
        "MATCH p = (a)-[e]->(b) WHERE p > 1 RETURN p",
        id="GA09_path_ordering_comparison",
    ),
    pytest.param(
        F.GA09,
        "MATCH p = (a)-[e]->(b), q = (c)-[f]->(d) WHERE p <> q RETURN p",
        id="GA09_path_inequality_comparison",
    ),
    # GQ17: Element-wise group variable operations
    pytest.param(
        F.GQ17,
        "MATCH (n)-[e]->(m) RETURN n.name, m.age GROUP BY n",
        id="GQ17_property_access_on_non_grouped_variable",
    ),
    pytest.param(
        F.GQ17,
        "MATCH (n)-[e]->(m) RETURN n, m GROUP BY n",
        id="GQ17_bare_non_grouped_variable",
    ),
    # GE04: Graph parameter in USE clause (structural inference)
    pytest.param(
        F.GE04,
        "USE $g MATCH (n) RETURN n",
        id="GE04_graph_parameter_in_use",
    ),
    # GE05: Binding table parameter in FOR TABLE (structural inference)
    pytest.param(
        F.GE05,
        "FOR x IN TABLE $t RETURN x",
        id="GE05_binding_table_parameter_in_for",
    ),
    # GG22: Element type key label set inference
    pytest.param(
        F.GG22,
        "CREATE GRAPH TYPE gt {"
        "  NODE TYPE :Person => :Person {name STRING},"
        "  NODE TYPE :Animal {species STRING}"
        "}",
        id="GG22_key_label_set_inference",
    ),
    # GG23: Optional element type key label sets (overlapping labels defeat GG22 inference)
    pytest.param(
        F.GG23,
        "CREATE GRAPH TYPE gt {"
        "  NODE TYPE :Person => :Person {name STRING},"
        "  NODE TYPE :Person {age INT32}"
        "}",
        id="GG23_omitted_key_label_set",
    ),
    # GP15: Graphs as procedure arguments
    pytest.param(
        F.GP15,
        "CALL proc(GRAPH CURRENT_GRAPH)",
        id="GP15_graph_as_procedure_argument",
    ),
    # GP14: Binding tables as procedure arguments
    pytest.param(
        F.GP14,
        "CALL proc(TABLE t)",
        id="GP14_binding_table_as_procedure_argument",
    ),
]


def build_dialect_without_feature(feature: Feature) -> Dialect:
    """Return a Dialect instance with a specific feature disabled."""
    supported = ALL_FEATURES - {feature}

    class RestrictedDialect(Dialect):
        SUPPORTED_FEATURES = supported

    return RestrictedDialect()


@pytest.fixture(scope="module")
def full_dialect() -> Dialect:
    """Shared full dialect instance."""
    return Dialect()


@pytest.fixture(scope="module")
def analyzer() -> SemanticAnalyzer:
    """Shared analyzer instance."""
    return SemanticAnalyzer()


@pytest.mark.parametrize(("feature", "query"), TEST_CASES)
def test_supported_feature_analyzes_cleanly(
    full_dialect: Dialect, analyzer: SemanticAnalyzer, feature: Feature, query: str
):
    """Verify that queries produce no diagnostics when the feature is supported."""
    ast_nodes = full_dialect.parse(query)
    assert ast_nodes, "Expected non-empty parse result"
    result = analyzer.analyze(ast_nodes[0], full_dialect)
    assert result.ok, (
        f"Expected no diagnostics with full dialect, got: {[d.message for d in result.diagnostics]}"
    )


@pytest.mark.parametrize(("feature", "query"), TEST_CASES)
def test_unsupported_feature_produces_diagnostic(
    analyzer: SemanticAnalyzer, feature: Feature, query: str
):
    """Verify that queries produce a diagnostic when the feature is not supported."""
    dialect = build_dialect_without_feature(feature)
    ast_nodes = dialect.parse(query)
    assert ast_nodes, "Expected non-empty parse result"
    result = analyzer.analyze(ast_nodes[0], dialect)

    assert not result.ok, f"Expected diagnostics for {feature.id}, got none"
    feature_ids = {d.feature_id for d in result.diagnostics}
    assert str(feature) in feature_ids, f"Expected diagnostic for {feature.id}, got: {feature_ids}"


# ---------------------------------------------------------------------------
# GE04 / GE05: require ExternalContext — tested separately
# ---------------------------------------------------------------------------

CONTEXT_TEST_CASES = [
    # GE04: Graph parameters
    pytest.param(
        F.GE04,
        "USE $g MATCH (n) RETURN n",
        ExternalContext(parameter_types={"g": GqlType.graph()}),
        id="GE04_graph_parameter",
    ),
    # GE05: Binding table parameters
    pytest.param(
        F.GE05,
        "MATCH (n) WHERE n.name = $t RETURN n",
        ExternalContext(parameter_types={"t": GqlType.binding_table()}),
        id="GE05_binding_table_parameter",
    ),
]


@pytest.mark.parametrize(("feature", "query", "ext_ctx"), CONTEXT_TEST_CASES)
def test_context_feature_supported_analyzes_cleanly(
    full_dialect: Dialect,
    analyzer: SemanticAnalyzer,
    feature: Feature,
    query: str,
    ext_ctx: ExternalContext,
):
    """Verify that context-dependent queries produce no diagnostics when supported."""
    ast_nodes = full_dialect.parse(query)
    assert ast_nodes, "Expected non-empty parse result"
    result = analyzer.analyze(ast_nodes[0], full_dialect, external_context=ext_ctx)
    feature_diags = [d for d in result.diagnostics if d.feature_id == str(feature)]
    assert not feature_diags, (
        f"Expected no {feature.id} diagnostics with full dialect, "
        f"got: {[d.message for d in feature_diags]}"
    )


@pytest.mark.parametrize(("feature", "query", "ext_ctx"), CONTEXT_TEST_CASES)
def test_context_feature_unsupported_produces_diagnostic(
    analyzer: SemanticAnalyzer,
    feature: Feature,
    query: str,
    ext_ctx: ExternalContext,
):
    """Verify that context-dependent queries produce diagnostics when unsupported."""
    dialect = build_dialect_without_feature(feature)
    ast_nodes = dialect.parse(query)
    assert ast_nodes, "Expected non-empty parse result"
    result = analyzer.analyze(ast_nodes[0], dialect, external_context=ext_ctx)

    feature_ids = {d.feature_id for d in result.diagnostics}
    assert str(feature) in feature_ids, f"Expected diagnostic for {feature.id}, got: {feature_ids}"
