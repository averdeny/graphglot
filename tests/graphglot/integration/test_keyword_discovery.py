"""Discover keyword/reserved-word differences between GQL spec and Neo4j.

Probes:
- OFFSET vs SKIP acceptance
- INSERT vs CREATE in GQL mode
"""

from __future__ import annotations

import pytest

from tests.graphglot.integration.conftest import neo4j_accepts

pytestmark = pytest.mark.integration


class TestKeywordOverrides:
    def test_skip_accepted(self, neo4j_session):
        """Neo4j should accept SKIP (its native keyword)."""
        accepted, error = neo4j_accepts(neo4j_session, "MATCH (n) RETURN n SKIP 1")
        assert accepted, f"SKIP rejected: {error}"

    def test_offset_accepted(self, neo4j_session):
        """Neo4j 2026 accepts OFFSET (GQL standard keyword)."""
        accepted, error = neo4j_accepts(neo4j_session, "MATCH (n) RETURN n OFFSET 1")
        assert accepted, f"OFFSET rejected: {error}"

    def test_insert_in_gql_mode(self, neo4j_session):
        """INSERT should be accepted in GQL mode."""
        accepted, error = neo4j_accepts(neo4j_session, "INSERT (:TestKeyword)")
        assert accepted, f"INSERT rejected — GQL mode may not be enabled: {error}"

    def test_create_in_gql_mode(self, neo4j_session):
        """Neo4j 2026 accepts CREATE even in GQL mode (dual-mode)."""
        accepted, error = neo4j_accepts(neo4j_session, "CREATE (:TestKeyword)")
        assert accepted, f"CREATE rejected in GQL mode: {error}"
