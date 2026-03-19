"""Shared fixtures for Neo4j integration tests."""

from __future__ import annotations

import os

import neo4j as neo4j_pkg
import pytest

# All tests in this directory require a running Neo4j instance.
pytestmark = pytest.mark.integration

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "testpassword")

# Permission/edition errors are not syntax errors — Neo4j Community lacks multi-db etc.
_PERMISSION_INDICATORS = [
    "enterprise",
    "not available",
    "unsupported administration",
    "permission",
    "authorization",
    "community edition",
]


def is_permission_error(error_msg: str) -> bool:
    """Distinguish permission/edition errors from syntax errors."""
    lower = error_msg.lower()
    return any(indicator in lower for indicator in _PERMISSION_INDICATORS)


@pytest.fixture(scope="session")
def neo4j_driver():
    """Session-scoped Neo4j driver."""
    driver = neo4j_pkg.GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        driver.verify_connectivity()
    except Exception as exc:
        driver.close()
        pytest.fail(f"Neo4j not reachable at {NEO4J_URI}: {exc}")

    yield driver
    driver.close()


@pytest.fixture
def neo4j_session(neo4j_driver):
    """Function-scoped Neo4j session."""
    with neo4j_driver.session() as session:
        yield session


# ---------------------------------------------------------------------------
# Seed data for execution tests
# ---------------------------------------------------------------------------
_SEED_CYPHER = """
CREATE (alice:Person:Employee {name: 'Alice', age: 30, active: true, score: 85.5,
        email: 'alice@example.com', born: date('1994-06-15')})
CREATE (bob:Person {name: 'Bob', age: 25, active: true, score: 72.0,
        email: 'bob@example.com', born: date('1999-03-20'), rating: 42})
CREATE (carol:Person:Manager {name: 'Carol', age: 45, active: true, score: 91.2,
        email: null, born: date('1979-11-01'), rating: 100})
CREATE (dave:Person {name: 'Dave', age: 19, active: false, score: 55.0,
        email: 'dave@example.com', born: date('2005-01-10')})
CREATE (eve:Person {name: 'Eve', age: 35, active: true, score: 60.0,
        email: 'eve@example.com', born: date('1989-07-22'), rating: 0})
CREATE (acme:Company {name: 'Acme', founded: 2010, active: true})
CREATE (alice)-[:KNOWS {since: 2020, weight: 0.9}]->(bob)
CREATE (alice)-[:KNOWS {since: 2021, weight: 0.5}]->(carol)
CREATE (bob)-[:KNOWS {since: 2022, weight: 0.7}]->(carol)
CREATE (bob)-[:WORKS_AT {role: 'engineer'}]->(acme)
CREATE (carol)-[:WORKS_AT {role: 'manager'}]->(acme)
CREATE (carol)-[:KNOWS {since: 2023, weight: 0.3}]->(dave)
CREATE (dave)-[:LIKES {score: 8}]->(alice)
"""


@pytest.fixture(scope="session")
def seed_neo4j(neo4j_driver):
    """Session-scoped fixture that seeds Neo4j with canonical test data.

    Clears the database, loads seed data, and cleans up after all tests.
    Uses native Cypher CREATE — we're testing GraphGlot output, not seed loading.
    """
    with neo4j_driver.session() as s:
        s.run("MATCH (n) DETACH DELETE n")
        s.run(_SEED_CYPHER)
    yield neo4j_driver


@pytest.fixture
def neo4j_exec_session(seed_neo4j):
    """Function-scoped session backed by seeded data."""
    with seed_neo4j.session() as session:
        yield session


def neo4j_accepts(session, query: str) -> tuple[bool, str]:
    """Check whether Neo4j accepts a query (syntax validation only).

    Uses ``EXPLAIN`` prefix for syntax validation without execution.
    Falls back to direct execution for non-plannable commands
    (SESSION, COMMIT, etc.).

    Returns:
        ``(True, "")`` if accepted, ``(False, error_message)`` otherwise.
    """
    explain_query = f"EXPLAIN {query}"
    try:
        result = session.run(explain_query)
        result.consume()
        return True, ""
    except Exception as exc:
        error_msg = str(exc)
        # If EXPLAIN is not supported for this query type, try direct execution
        if "EXPLAIN" in error_msg.upper() or "Unable to" in error_msg:
            try:
                result = session.run(query)
                result.consume()
                return True, ""
            except Exception as direct_exc:
                return False, str(direct_exc)
        return False, error_msg
