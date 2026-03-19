"""Tests for unsupported query types in lineage analysis."""

from __future__ import annotations

import pytest

from graphglot.dialect.fullgql import FullGQL
from graphglot.dialect.neo4j import Neo4j
from graphglot.error import UnsupportedLineageError
from graphglot.lineage.models import LineageGraph


@pytest.fixture
def dialect():
    return FullGQL()


@pytest.fixture
def neo4j():
    return Neo4j()


class TestUnsupportedLineage:
    """Lineage should raise UnsupportedLineageError for unsupported statement types."""

    def test_select_not_supported(self, dialect):
        """SELECT statements are not supported."""
        with pytest.raises(UnsupportedLineageError, match="SELECT"):
            dialect.lineage("SELECT 1 AS test")

    def test_to_diagnostic(self, dialect):
        """UnsupportedLineageError produces a valid diagnostic."""
        with pytest.raises(UnsupportedLineageError) as exc_info:
            dialect.lineage("SELECT 1 AS test")
        diag = exc_info.value.to_diagnostic()
        assert diag.code == "unsupported-lineage"
        assert diag.phase == "lineage"
        assert "SELECT" in diag.message


class TestDataModifyingNowSupported:
    """Data-modifying queries should now return LineageGraph with mutations."""

    def test_insert_supported(self, dialect):
        [result] = dialect.lineage('INSERT (n:Person {name: "Alice"})')
        assert isinstance(result, LineageGraph)
        assert len(result.mutations) >= 1

    def test_delete_supported(self, dialect):
        [result] = dialect.lineage("MATCH (n) DELETE n")
        assert isinstance(result, LineageGraph)
        assert len(result.mutations) >= 1

    def test_set_supported(self, dialect):
        [result] = dialect.lineage('MATCH (n) SET n.name = "Bob"')
        assert isinstance(result, LineageGraph)
        assert len(result.mutations) >= 1

    def test_remove_supported(self, dialect):
        [result] = dialect.lineage("MATCH (n) REMOVE n.name")
        assert isinstance(result, LineageGraph)
        assert len(result.mutations) >= 1

    def test_create_supported(self, neo4j):
        [result] = neo4j.lineage("CREATE (n:Person {name: 'Alice'})")
        assert isinstance(result, LineageGraph)
        assert len(result.mutations) >= 1

    def test_merge_supported(self, neo4j):
        [result] = neo4j.lineage("MERGE (n:Person {name: 'Alice'})")
        assert isinstance(result, LineageGraph)
        assert len(result.mutations) >= 1


class TestSupportedLineage:
    """Supported queries should still work normally."""

    def test_match_return_supported(self, dialect):
        """MATCH ... RETURN is supported and returns a LineageGraph."""
        [result] = dialect.lineage("MATCH (n) RETURN n")
        assert isinstance(result, LineageGraph)
        assert len(result.nodes) > 0

    def test_use_match_return_supported(self, dialect):
        """USE ... MATCH ... RETURN is supported and returns a LineageGraph."""
        [result] = dialect.lineage("USE g MATCH (n) RETURN n")
        assert isinstance(result, LineageGraph)
        assert len(result.nodes) > 0
