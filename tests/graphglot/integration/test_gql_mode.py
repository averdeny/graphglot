"""Verify Neo4j is running in GQL mode.

If these tests fail, all other integration tests are meaningless —
Neo4j must have GQL mode enabled via NEO4J_server_gql_default__language__version=2.
"""

import pytest

from tests.graphglot.integration.conftest import neo4j_accepts

pytestmark = pytest.mark.integration


class TestGqlMode:
    def test_insert_accepted(self, neo4j_session):
        """INSERT is GQL syntax — must work in GQL mode."""
        accepted, error = neo4j_accepts(neo4j_session, "INSERT (:TestGqlMode)")
        assert accepted, f"INSERT rejected — Neo4j may not be in GQL mode: {error}"

    def test_return_literal(self, neo4j_session):
        """Basic RETURN should work in any mode."""
        result = neo4j_session.run("RETURN 1 AS x")
        record = result.single()
        assert record["x"] == 1

    def test_match_return(self, neo4j_session):
        """MATCH ... RETURN should work in any mode."""
        accepted, error = neo4j_accepts(neo4j_session, "MATCH (n) RETURN n LIMIT 1")
        assert accepted, f"Basic MATCH failed: {error}"
