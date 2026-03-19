"""Tests for data-modifying query lineage (mutations).

Tests that SET, REMOVE, DELETE, INSERT, CREATE, and MERGE produce
Mutation entities with correct WRITES edges and dependency tracking.
"""

from __future__ import annotations

import pytest

from graphglot.dialect.fullgql import FullGQL
from graphglot.dialect.neo4j import Neo4j
from graphglot.lineage import (
    LineageEdgeKind,
    MutationKind,
)

# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def gql():
    return FullGQL()


@pytest.fixture
def neo4j():
    return Neo4j()


def _lineage(dialect, query):
    """Parse and analyze lineage for a single statement."""
    [g] = dialect.lineage(query)
    return g


def _mutations(g):
    """Return list of Mutation entities sorted by id."""
    return sorted(g.mutations.values(), key=lambda m: m.id)


def _find_binding(g, name):
    for b in g.bindings.values():
        if b.name == name:
            return b
    return None


def _write_targets(g, mutation_id):
    """Entity IDs (Binding or PropertyRef) that a mutation WRITES to."""
    return g.targets(mutation_id, LineageEdgeKind.WRITES)


def _deps(g, mutation_id):
    """Binding IDs that a mutation DEPENDS_ON (direct or via property refs)."""
    return g.binding_deps(mutation_id)


def _written_property(g, mutation_id):
    """Property name that a mutation WRITES to (via PropertyRef), or None."""
    for tid in _write_targets(g, mutation_id):
        if tid in g.property_refs:
            return g.property_refs[tid].property_name
    return None


# ── SET property ──────────────────────────────────────────────────


class TestSetPropertyMutation:
    def test_set_property_creates_mutation(self, gql):
        g = _lineage(gql, 'MATCH (n:Person) SET n.name = "Bob"')
        muts = _mutations(g)
        assert len(muts) == 1
        assert muts[0].kind == MutationKind.SET_PROPERTY
        assert _written_property(g, muts[0].id) == "name"

    def test_set_property_writes_to_property_ref(self, gql):
        """SET n.name WRITES to PropertyRef(n.name), which DEPENDS_ON binding n."""
        g = _lineage(gql, 'MATCH (n:Person) SET n.name = "Bob"')
        m = _mutations(g)[0]
        targets = _write_targets(g, m.id)
        assert len(targets) == 1
        # Target is a PropertyRef, not a binding
        assert targets[0] in g.property_refs
        prop = g.property_refs[targets[0]]
        assert prop.property_name == "name"
        # PropertyRef links back to binding n
        prop_deps = g.targets(prop.id, LineageEdgeKind.DEPENDS_ON)
        assert any(g.bindings[bid].name == "n" for bid in prop_deps if bid in g.bindings)

    def test_set_property_with_expression_dep(self, gql):
        g = _lineage(gql, "MATCH (n:Person), (m:Person) SET n.name = m.name")
        m = _mutations(g)[0]
        # Should depend on m (via m.name property ref)
        dep_bids = _deps(g, m.id)
        dep_names = {g.bindings[bid].name for bid in dep_bids}
        assert "m" in dep_names

    def test_multiple_set_items(self, gql):
        g = _lineage(gql, 'MATCH (n:Person) SET n.name = "Bob", n.age = 30')
        muts = _mutations(g)
        assert len(muts) == 2
        assert all(m.kind == MutationKind.SET_PROPERTY for m in muts)
        prop_names = {_written_property(g, m.id) for m in muts}
        assert prop_names == {"name", "age"}


# ── SET all properties ────────────────────────────────────────────


class TestSetAllMutation:
    def test_set_all_creates_mutation(self, gql):
        g = _lineage(gql, 'MATCH (n:Person) SET n = {name: "Bob"}')
        muts = _mutations(g)
        assert len(muts) == 1
        assert muts[0].kind == MutationKind.SET_ALL

    def test_set_all_writes_to_binding(self, gql):
        g = _lineage(gql, 'MATCH (n:Person) SET n = {name: "Bob"}')
        m = _mutations(g)[0]
        targets = _write_targets(g, m.id)
        assert len(targets) == 1
        assert g.bindings[targets[0]].name == "n"


# ── SET label ─────────────────────────────────────────────────────


class TestSetLabelMutation:
    def test_set_label_creates_mutation(self, gql):
        g = _lineage(gql, "MATCH (n) SET n IS Employee")
        muts = _mutations(g)
        assert len(muts) == 1
        assert muts[0].kind == MutationKind.SET_LABEL
        assert muts[0].label_name == "Employee"

    def test_set_label_writes_to_binding(self, gql):
        g = _lineage(gql, "MATCH (n) SET n IS Employee")
        m = _mutations(g)[0]
        targets = _write_targets(g, m.id)
        assert len(targets) == 1
        assert g.bindings[targets[0]].name == "n"


# ── REMOVE property ──────────────────────────────────────────────


class TestRemovePropertyMutation:
    def test_remove_property_creates_mutation(self, gql):
        g = _lineage(gql, "MATCH (n:Person) REMOVE n.name")
        muts = _mutations(g)
        assert len(muts) == 1
        assert muts[0].kind == MutationKind.REMOVE_PROPERTY
        assert _written_property(g, muts[0].id) == "name"

    def test_remove_property_writes_to_property_ref(self, gql):
        """REMOVE n.name WRITES to PropertyRef(n.name)."""
        g = _lineage(gql, "MATCH (n:Person) REMOVE n.name")
        m = _mutations(g)[0]
        targets = _write_targets(g, m.id)
        assert len(targets) == 1
        assert targets[0] in g.property_refs
        prop = g.property_refs[targets[0]]
        assert prop.property_name == "name"


# ── REMOVE label ──────────────────────────────────────────────────


class TestRemoveLabelMutation:
    def test_remove_label_creates_mutation(self, gql):
        g = _lineage(gql, "MATCH (n) REMOVE n IS Employee")
        muts = _mutations(g)
        assert len(muts) == 1
        assert muts[0].kind == MutationKind.REMOVE_LABEL
        assert muts[0].label_name == "Employee"

    def test_remove_label_writes_to_binding(self, gql):
        g = _lineage(gql, "MATCH (n) REMOVE n IS Employee")
        m = _mutations(g)[0]
        targets = _write_targets(g, m.id)
        assert len(targets) == 1
        assert g.bindings[targets[0]].name == "n"


# ── DELETE ────────────────────────────────────────────────────────


class TestDeleteMutation:
    def test_delete_creates_mutation(self, gql):
        g = _lineage(gql, "MATCH (n:Person) DELETE n")
        muts = _mutations(g)
        assert len(muts) == 1
        assert muts[0].kind == MutationKind.DELETE
        assert muts[0].is_detach is False

    def test_detach_delete(self, gql):
        g = _lineage(gql, "MATCH (n:Person) DETACH DELETE n")
        m = _mutations(g)[0]
        assert m.kind == MutationKind.DELETE
        assert m.is_detach is True

    def test_delete_writes_to_binding(self, gql):
        g = _lineage(gql, "MATCH (n:Person) DELETE n")
        m = _mutations(g)[0]
        targets = _write_targets(g, m.id)
        assert len(targets) == 1
        assert g.bindings[targets[0]].name == "n"

    def test_delete_multiple(self, gql):
        g = _lineage(gql, "MATCH (n)-[r]->(m) DELETE n, r, m")
        muts = _mutations(g)
        # One mutation per delete item
        assert len(muts) == 3
        write_names = set()
        for m in muts:
            for tid in _write_targets(g, m.id):
                write_names.add(g.bindings[tid].name)
        assert write_names == {"n", "r", "m"}


# ── INSERT (GQL) ─────────────────────────────────────────────────


class TestInsertMutation:
    def test_insert_node(self, gql):
        g = _lineage(gql, 'INSERT (n:Person {name: "Alice"})')
        muts = _mutations(g)
        assert len(muts) >= 1
        assert any(m.kind == MutationKind.INSERT for m in muts)

    def test_insert_creates_bindings(self, gql):
        g = _lineage(gql, 'INSERT (n:Person {name: "Alice"})')
        assert _find_binding(g, "n") is not None

    def test_insert_writes_to_new_binding(self, gql):
        g = _lineage(gql, 'INSERT (n:Person {name: "Alice"})')
        m = next(m for m in _mutations(g) if m.kind == MutationKind.INSERT)
        targets = _write_targets(g, m.id)
        # WRITES only to PropertyRef n.name (binding covered via prop_ref→binding)
        assert len(targets) == 1
        prop_targets = {
            g.property_refs[tid].property_name for tid in targets if tid in g.property_refs
        }
        assert "name" in prop_targets

    def test_insert_bare_variable(self, gql):
        """INSERT (n) — variable only, no label or properties."""
        g = _lineage(gql, "INSERT (n)")
        muts = _mutations(g)
        assert len(muts) >= 1
        assert any(m.kind == MutationKind.INSERT for m in muts)
        b = _find_binding(g, "n")
        assert b is not None
        # Should WRITES to n
        m = next(m for m in muts if m.kind == MutationKind.INSERT)
        targets = _write_targets(g, m.id)
        assert b.id in targets

    def test_insert_label_only(self, gql):
        """INSERT (:Person) — label only, no variable name."""
        g = _lineage(gql, "INSERT (:Person)")
        muts = _mutations(g)
        assert len(muts) >= 1
        assert any(m.kind == MutationKind.INSERT for m in muts)
        # Should still create a binding (anonymous) and WRITES to it
        m = next(m for m in muts if m.kind == MutationKind.INSERT)
        targets = _write_targets(g, m.id)
        assert len(targets) >= 1

    def test_insert_path(self, gql):
        g = _lineage(gql, "INSERT (a:Person)-[r:KNOWS]->(b:Person)")
        muts = _mutations(g)
        assert len(muts) >= 1
        # All new bindings should exist
        assert _find_binding(g, "a") is not None
        assert _find_binding(g, "r") is not None
        assert _find_binding(g, "b") is not None

    def test_insert_creates_pattern(self, gql):
        """INSERT path should create a Pattern with bindings linked via IN_PATTERN."""
        g = _lineage(gql, "INSERT (a:Person)-[r:KNOWS]->(b:Person)")
        assert len(g.patterns) == 1
        pat = next(iter(g.patterns.values()))
        in_pattern_bids = g.sources(pat.id, LineageEdgeKind.IN_PATTERN)
        bound_names = {g.bindings[bid].name for bid in in_pattern_bids if bid in g.bindings}
        assert bound_names == {"a", "r", "b"}

    def test_insert_property_spec_creates_property_refs(self, gql):
        """INSERT (n:Pet {name: "Boris"}) should WRITES to PropertyRef(n.name)."""
        g = _lineage(gql, 'INSERT (n:Pet {name: "Boris"})')
        m = next(m for m in _mutations(g) if m.kind == MutationKind.INSERT)
        assert _written_property(g, m.id) == "name"

    def test_insert_path_property_specs(self, gql):
        """INSERT path with property specs creates PropertyRefs for each."""
        g = _lineage(
            gql,
            'INSERT (pb:Pet {name: "Boris"})<-[:HAS]-(a)-[:HAS]->(pa:Pet {name: "Andy"})',
        )
        m = next(m for m in _mutations(g) if m.kind == MutationKind.INSERT)
        targets = _write_targets(g, m.id)
        # Two property refs (pb.name, pa.name) + 3 uncovered bindings (a, 2x :HAS edges)
        prop_targets = [tid for tid in targets if tid in g.property_refs]
        assert len(prop_targets) == 2
        binding_targets = [tid for tid in targets if tid in g.bindings]
        assert len(binding_targets) == 3


# ── CREATE (Cypher) ──────────────────────────────────────────────


class TestCreateMutation:
    def test_create_node(self, neo4j):
        g = _lineage(neo4j, "CREATE (n:Person {name: 'Alice'})")
        muts = _mutations(g)
        assert len(muts) >= 1
        assert any(m.kind == MutationKind.INSERT for m in muts)

    def test_create_path(self, neo4j):
        g = _lineage(neo4j, "CREATE (a:Person)-[r:KNOWS]->(b:Person)")
        assert _find_binding(g, "a") is not None
        assert _find_binding(g, "r") is not None
        assert _find_binding(g, "b") is not None

    def test_create_creates_pattern(self, neo4j):
        """CREATE path should create a Pattern with bindings linked via IN_PATTERN."""
        g = _lineage(neo4j, "CREATE (a:Person)-[r:KNOWS]->(b:Person)")
        assert len(g.patterns) == 1
        pat = next(iter(g.patterns.values()))
        in_pattern_bids = g.sources(pat.id, LineageEdgeKind.IN_PATTERN)
        bound_names = {g.bindings[bid].name for bid in in_pattern_bids if bid in g.bindings}
        assert bound_names == {"a", "r", "b"}

    def test_create_writes_to_bindings(self, neo4j):
        g = _lineage(neo4j, "CREATE (n:Person {name: 'Alice'})")
        m = next(m for m in _mutations(g) if m.kind == MutationKind.INSERT)
        targets = _write_targets(g, m.id)
        # WRITES only to PropertyRef (binding covered via prop_ref→binding)
        assert len(targets) == 1
        prop_targets = {
            g.property_refs[tid].property_name for tid in targets if tid in g.property_refs
        }
        assert "name" in prop_targets


# ── MERGE (Cypher) ───────────────────────────────────────────────


class TestMergeMutation:
    def test_merge_creates_mutation(self, neo4j):
        g = _lineage(neo4j, "MERGE (n:Person {name: 'Alice'})")
        muts = _mutations(g)
        assert any(m.kind == MutationKind.MERGE for m in muts)

    def test_merge_writes_to_binding(self, neo4j):
        g = _lineage(neo4j, "MERGE (n:Person {name: 'Alice'})")
        m = next(m for m in _mutations(g) if m.kind == MutationKind.MERGE)
        targets = _write_targets(g, m.id)
        assert len(targets) >= 1
        target_names = {g.bindings[tid].name for tid in targets}
        assert "n" in target_names

    def test_merge_creates_binding(self, neo4j):
        g = _lineage(neo4j, "MERGE (n:Person {name: 'Alice'})")
        assert _find_binding(g, "n") is not None

    def test_merge_on_create_set(self, neo4j):
        g = _lineage(neo4j, "MERGE (n:Person) ON CREATE SET n.created = 1")
        muts = _mutations(g)
        # Should have MERGE + SET_PROPERTY
        kinds = {m.kind for m in muts}
        assert MutationKind.MERGE in kinds
        assert MutationKind.SET_PROPERTY in kinds

    def test_merge_on_match_set(self, neo4j):
        g = _lineage(neo4j, "MERGE (n:Person) ON MATCH SET n.lastSeen = 2")
        muts = _mutations(g)
        kinds = {m.kind for m in muts}
        assert MutationKind.MERGE in kinds
        assert MutationKind.SET_PROPERTY in kinds


# ── Cypher SET extensions ────────────────────────────────────────


class TestCypherSetExtensions:
    def test_set_map_append(self, neo4j):
        g = _lineage(neo4j, "MATCH (n:Person) SET n += {name: 'Bob'}")
        muts = _mutations(g)
        assert len(muts) == 1
        assert muts[0].kind == MutationKind.SET_ALL

    def test_set_all_from_expr(self, neo4j):
        g = _lineage(neo4j, "MATCH (n:Person), (m:Person) SET n = m")
        muts = _mutations(g)
        assert len(muts) == 1
        assert muts[0].kind == MutationKind.SET_ALL

    def test_set_property_from_expr(self, neo4j):
        """SET (n).prop = val — parenthesized expression target."""
        g = _lineage(neo4j, "MATCH (n:Person) SET (n).name = 'Bob'")
        muts = _mutations(g)
        assert len(muts) == 1
        assert muts[0].kind == MutationKind.SET_PROPERTY
        assert _written_property(g, muts[0].id) == "name"

    def test_set_property_cypher(self, neo4j):
        g = _lineage(neo4j, "MATCH (n:Person) SET n.name = 'Bob'")
        muts = _mutations(g)
        assert len(muts) == 1
        assert muts[0].kind == MutationKind.SET_PROPERTY
        assert _written_property(g, muts[0].id) == "name"

    def test_set_label_cypher(self, neo4j):
        g = _lineage(neo4j, "MATCH (n) SET n:Employee")
        muts = _mutations(g)
        assert len(muts) == 1
        assert muts[0].kind == MutationKind.SET_LABEL


# ── Compound queries ─────────────────────────────────────────────


class TestMutationWithReturn:
    def test_match_set_return(self, neo4j):
        g = _lineage(neo4j, "MATCH (n:Person) SET n.name = 'Bob' RETURN n")
        muts = _mutations(g)
        assert len(muts) == 1
        assert muts[0].kind == MutationKind.SET_PROPERTY
        # Also has outputs
        assert len(list(g.outputs.values())) >= 1

    def test_match_delete_return(self, neo4j):
        g = _lineage(neo4j, "MATCH (n:Person) DELETE n RETURN n")
        muts = _mutations(g)
        assert len(muts) == 1
        assert muts[0].kind == MutationKind.DELETE


# ── USE graph + mutations ────────────────────────────────────────


class TestMutationWithUseGraph:
    def test_set_uses_named_graph(self, gql):
        """USE g MATCH ... SET ... — mutation targets bind to named graph."""
        g = _lineage(gql, 'USE g MATCH (n:Person) SET n.name = "Bob"')
        graph_names = {gr.name for gr in g.graphs.values()}
        assert graph_names == {"g"}
        # Pattern belongs to named graph
        assert len(g.patterns) == 1
        pat = next(iter(g.patterns.values()))
        belongs = g.targets(pat.id, LineageEdgeKind.BELONGS_TO)
        assert len(belongs) == 1
        named_graph = g.graphs[belongs[0]]
        assert named_graph.name == "g"

    def test_insert_uses_named_graph(self, gql):
        """USE g INSERT ... — insert pattern belongs to named graph."""
        g = _lineage(gql, 'USE g INSERT (n:Person {name: "Alice"})')
        graph_names = {gr.name for gr in g.graphs.values()}
        assert graph_names == {"g"}
        # Pattern belongs to named graph
        pat = next(iter(g.patterns.values()))
        belongs = g.targets(pat.id, LineageEdgeKind.BELONGS_TO)
        assert len(belongs) == 1
        assert g.graphs[belongs[0]].name == "g"

    def test_delete_uses_named_graph(self, gql):
        """USE g MATCH ... DELETE ... — bindings in named graph context."""
        g = _lineage(gql, "USE g MATCH (n:Person) DELETE n")
        graph_names = {gr.name for gr in g.graphs.values()}
        assert graph_names == {"g"}
        muts = _mutations(g)
        assert len(muts) == 1
        assert muts[0].kind == MutationKind.DELETE


# ── Mutation dependencies ────────────────────────────────────────


class TestMutationDependencies:
    def test_set_depends_on_source_binding(self, gql):
        """SET n.name = m.name should depend on m."""
        g = _lineage(gql, "MATCH (n:Person), (m:Person) SET n.name = m.name")
        m = _mutations(g)[0]
        dep_bids = _deps(g, m.id)
        dep_names = {g.bindings[bid].name for bid in dep_bids}
        assert "m" in dep_names

    def test_set_depends_on_property_ref(self, gql):
        """SET n.name = m.name should have DEPENDS_ON to m.name property ref."""
        g = _lineage(gql, "MATCH (n:Person), (m:Person) SET n.name = m.name")
        m = _mutations(g)[0]
        prop_targets = [
            tid for tid in g.targets(m.id, LineageEdgeKind.DEPENDS_ON) if tid in g.property_refs
        ]
        assert len(prop_targets) >= 1
        prop_names = {g.property_refs[pid].property_name for pid in prop_targets}
        assert "name" in prop_names
