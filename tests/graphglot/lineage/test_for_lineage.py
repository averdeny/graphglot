"""Tests for FOR/UNWIND lineage analysis.

Verifies that FOR (GQL) and UNWIND (Cypher) statements produce correct
bindings, dependency edges, and interact properly with other clauses.
"""

from __future__ import annotations

import pytest

from graphglot.dialect.fullgql import FullGQL
from graphglot.dialect.neo4j import Neo4j
from graphglot.lineage import (
    BindingKind,
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
    [g] = dialect.lineage(query)
    return g


def _find_binding(g, name):
    for b in g.bindings.values():
        if b.name == name:
            return b
    return None


def _find_output(g, name):
    for o in g.outputs.values():
        if o.alias == name or g.source_text(o) == name:
            return o
    return None


# ── Q1: Basic FOR with list ──────────────────────────────────────


class TestBasicFor:
    def test_for_creates_variable_binding(self, gql):
        """FOR x IN [...] should create a VARIABLE binding for x."""
        g = _lineage(gql, "FOR x IN [1, 2, 3] RETURN x")
        b = _find_binding(g, "x")
        assert b is not None
        assert b.kind == BindingKind.VARIABLE

    def test_for_output_depends_on_binding(self, gql):
        """RETURN x after FOR should have output depending on x."""
        g = _lineage(gql, "FOR x IN [1, 2, 3] RETURN x")
        b = _find_binding(g, "x")
        out = _find_output(g, "x")
        assert out is not None
        dep_bids = g.binding_deps(out.id)
        assert b.id in dep_bids


# ── Q2: FOR with ORDINALITY ──────────────────────────────────────


class TestForWithOrdinality:
    def test_ordinality_creates_binding(self, gql):
        """FOR x IN [...] WITH ORDINALITY o should create binding for o."""
        g = _lineage(gql, "FOR x IN [10, 20, 30] WITH ORDINALITY o RETURN x, o")
        b_x = _find_binding(g, "x")
        b_o = _find_binding(g, "o")
        assert b_x is not None
        assert b_o is not None
        assert b_x.kind == BindingKind.VARIABLE
        assert b_o.kind == BindingKind.VARIABLE

    def test_ordinality_output_depends_on_binding(self, gql):
        """RETURN o should depend on ordinality binding."""
        g = _lineage(gql, "FOR x IN [10, 20, 30] WITH ORDINALITY o RETURN x, o")
        b_o = _find_binding(g, "o")
        out_o = _find_output(g, "o")
        assert out_o is not None
        assert b_o.id in g.binding_deps(out_o.id)


# ── Q3: FOR after MATCH ──────────────────────────────────────────


class TestForAfterMatch:
    def test_match_binding_visible_after_for(self, gql):
        """MATCH (n) FOR x ... RETURN n.name — n should be accessible."""
        g = _lineage(gql, "MATCH (n:Person) FOR x IN [1, 2] RETURN n.name, x")
        b_n = _find_binding(g, "n")
        b_x = _find_binding(g, "x")
        assert b_n is not None
        assert b_n.kind == BindingKind.NODE
        assert b_x is not None
        assert b_x.kind == BindingKind.VARIABLE

    def test_both_outputs_have_deps(self, gql):
        """Both n.name and x outputs should have correct dependencies."""
        g = _lineage(gql, "MATCH (n:Person) FOR x IN [1, 2] RETURN n.name, x")
        out_name = _find_output(g, "n.name")
        out_x = _find_output(g, "x")
        assert out_name is not None
        assert out_x is not None
        # n.name depends on n
        b_n = _find_binding(g, "n")
        assert b_n.id in g.binding_deps(out_name.id)
        # x depends on x
        b_x = _find_binding(g, "x")
        assert b_x.id in g.binding_deps(out_x.id)


# ── Q4: FOR with property reference in source ────────────────────


class TestForWithPropertySource:
    def test_for_source_property_creates_ref(self, gql):
        """FOR tag IN n.tags — source expression should create property ref for n.tags."""
        g = _lineage(gql, "MATCH (n:Person) FOR tag IN n.tags RETURN n.name, tag")
        b_tag = _find_binding(g, "tag")
        assert b_tag is not None
        assert b_tag.kind == BindingKind.VARIABLE
        # n.tags should exist as a property ref
        tag_props = [p for p in g.property_refs.values() if p.property_name == "tags"]
        assert len(tag_props) >= 1

    def test_for_variable_depends_on_source(self, gql):
        """FOR tag IN n.tags — tag binding should DEPENDS_ON n.tags property ref."""
        g = _lineage(gql, "MATCH (n:Person) FOR tag IN n.tags RETURN n.name, tag")
        b_tag = _find_binding(g, "tag")
        tag_deps = g.targets(b_tag.id, LineageEdgeKind.DEPENDS_ON)
        tag_prop_deps = [tid for tid in tag_deps if tid in g.property_refs]
        assert len(tag_prop_deps) >= 1
        assert g.property_refs[tag_prop_deps[0]].property_name == "tags"

    def test_for_source_and_return_outputs(self, gql):
        """Both n.name and tag should appear as outputs."""
        g = _lineage(gql, "MATCH (n:Person) FOR tag IN n.tags RETURN n.name, tag")
        out_name = _find_output(g, "n.name")
        out_tag = _find_output(g, "tag")
        assert out_name is not None
        assert out_tag is not None


# ── Q5: UNWIND basic (Cypher) ────────────────────────────────────


class TestUnwindBasic:
    def test_unwind_creates_variable_binding(self, neo4j):
        """UNWIND [...] AS x should create a VARIABLE binding."""
        g = _lineage(neo4j, "UNWIND [1, 2, 3] AS x RETURN x")
        b = _find_binding(g, "x")
        assert b is not None
        assert b.kind == BindingKind.VARIABLE

    def test_unwind_output_depends_on_binding(self, neo4j):
        """RETURN x after UNWIND should depend on x."""
        g = _lineage(neo4j, "UNWIND [1, 2, 3] AS x RETURN x")
        b = _find_binding(g, "x")
        out = _find_output(g, "x")
        assert out is not None
        assert b.id in g.binding_deps(out.id)


# ── Q6: UNWIND after MATCH (Cypher) ──────────────────────────────


class TestUnwindAfterMatch:
    def test_match_binding_visible_after_unwind(self, neo4j):
        """MATCH (n) UNWIND n.tags AS tag — both n and tag should be bindings."""
        g = _lineage(neo4j, "MATCH (n:Person) UNWIND n.tags AS tag RETURN n.name, tag")
        b_n = _find_binding(g, "n")
        b_tag = _find_binding(g, "tag")
        assert b_n is not None
        assert b_n.kind == BindingKind.NODE
        assert b_tag is not None
        assert b_tag.kind == BindingKind.VARIABLE

    def test_unwind_source_creates_property_ref(self, neo4j):
        """UNWIND n.tags — should create property ref for n.tags."""
        g = _lineage(neo4j, "MATCH (n:Person) UNWIND n.tags AS tag RETURN n.name, tag")
        tag_props = [p for p in g.property_refs.values() if p.property_name == "tags"]
        assert len(tag_props) >= 1


# ── Q7: FOR + FILTER WHERE ──────────────────────────────────────


class TestForWithFilter:
    def test_for_with_filter_creates_filter(self, gql):
        """FOR ... FILTER WHERE x > 3 should create a filter entity."""
        g = _lineage(gql, "FOR x IN [1, 2, 3, 4, 5] FILTER WHERE x > 3 RETURN x")
        assert len(g.filters) >= 1

    def test_for_with_filter_binding_accessible(self, gql):
        """x should be accessible in both FILTER and RETURN."""
        g = _lineage(gql, "FOR x IN [1, 2, 3, 4, 5] FILTER WHERE x > 3 RETURN x")
        b = _find_binding(g, "x")
        assert b is not None
        out = _find_output(g, "x")
        assert out is not None
        assert b.id in g.binding_deps(out.id)

    def test_filter_constrains_for_variable(self, gql):
        """Filter should constrain the FOR variable x."""
        g = _lineage(gql, "FOR x IN [1, 2, 3, 4, 5] FILTER WHERE x > 3 RETURN x")
        b = _find_binding(g, "x")
        f = next(iter(g.filters.values()))
        constrained = g.binding_deps(f.id)
        assert b.id in constrained


# ── Q8: FOR + SET mutation ───────────────────────────────────────


class TestForWithSet:
    def test_for_with_set_creates_mutation(self, gql):
        """MATCH + FOR + SET should produce a mutation."""
        g = _lineage(gql, "MATCH (n:Person) FOR label IN n.labels SET n.tag = label")
        mutations = list(g.mutations.values())
        assert len(mutations) == 1
        assert mutations[0].kind == MutationKind.SET_PROPERTY

    def test_for_set_writes_to_property(self, gql):
        """SET n.tag = label should WRITES to PropertyRef for n.tag."""
        g = _lineage(gql, "MATCH (n:Person) FOR label IN n.labels SET n.tag = label")
        m = next(iter(g.mutations.values()))
        targets = g.targets(m.id, LineageEdgeKind.WRITES)
        assert len(targets) == 1
        assert targets[0] in g.property_refs
        assert g.property_refs[targets[0]].property_name == "tag"

    def test_for_set_depends_on_loop_var(self, gql):
        """SET n.tag = label should DEPENDS_ON the FOR variable label."""
        g = _lineage(gql, "MATCH (n:Person) FOR label IN n.labels SET n.tag = label")
        m = next(iter(g.mutations.values()))
        dep_bids = g.binding_deps(m.id)
        b_label = _find_binding(g, "label")
        assert b_label.id in dep_bids


# ── Q9: UNWIND + CREATE (Cypher) ────────────────────────────────


class TestUnwindWithCreate:
    def test_unwind_create_produces_mutation(self, neo4j):
        """UNWIND + CREATE should produce an INSERT mutation."""
        g = _lineage(neo4j, "UNWIND ['Alice', 'Bob'] AS name CREATE (n:Person {name: name})")
        mutations = list(g.mutations.values())
        assert any(m.kind == MutationKind.INSERT for m in mutations)

    def test_unwind_create_bindings(self, neo4j):
        """Both name (UNWIND) and n (CREATE) bindings should exist."""
        g = _lineage(neo4j, "UNWIND ['Alice', 'Bob'] AS name CREATE (n:Person {name: name})")
        assert _find_binding(g, "name") is not None
        assert _find_binding(g, "n") is not None

    def test_unwind_create_property_ref(self, neo4j):
        """CREATE {name: name} should create PropertyRef for n.name."""
        g = _lineage(neo4j, "UNWIND ['Alice', 'Bob'] AS name CREATE (n:Person {name: name})")
        name_props = [p for p in g.property_refs.values() if p.property_name == "name"]
        assert len(name_props) >= 1


# ── Q10: MATCH + UNWIND + MATCH + RETURN (Cypher) ───────────────


class TestNestedUnwind:
    def test_all_bindings_created(self, neo4j):
        """MATCH + UNWIND + MATCH should create n, fname, and f bindings."""
        g = _lineage(
            neo4j,
            "MATCH (n:Person) UNWIND n.friends AS fname "
            "MATCH (f:Person {name: fname}) RETURN n.name, f.name",
        )
        assert _find_binding(g, "n") is not None
        assert _find_binding(g, "fname") is not None
        assert _find_binding(g, "f") is not None

    def test_outputs_depend_on_correct_bindings(self, neo4j):
        """n.name output depends on n, f.name output depends on f."""
        g = _lineage(
            neo4j,
            "MATCH (n:Person) UNWIND n.friends AS fname "
            "MATCH (f:Person {name: fname}) RETURN n.name, f.name",
        )
        # There are two n.name property refs — find outputs
        outputs = sorted(g.outputs.values(), key=lambda o: o.id)
        assert len(outputs) == 2
        b_n = _find_binding(g, "n")
        b_f = _find_binding(g, "f")
        out_0_deps = g.binding_deps(outputs[0].id)
        out_1_deps = g.binding_deps(outputs[1].id)
        # One output depends on n, the other on f
        all_dep_ids = set(out_0_deps + out_1_deps)
        assert b_n.id in all_dep_ids
        assert b_f.id in all_dep_ids

    def test_unwind_source_property_ref(self, neo4j):
        """UNWIND n.friends should create property ref for n.friends."""
        g = _lineage(
            neo4j,
            "MATCH (n:Person) UNWIND n.friends AS fname "
            "MATCH (f:Person {name: fname}) RETURN n.name, f.name",
        )
        friend_props = [p for p in g.property_refs.values() if p.property_name == "friends"]
        assert len(friend_props) >= 1

    def test_second_match_has_filter(self, neo4j):
        """MATCH (f:Person {name: fname}) should create a filter for the property spec."""
        g = _lineage(
            neo4j,
            "MATCH (n:Person) UNWIND n.friends AS fname "
            "MATCH (f:Person {name: fname}) RETURN n.name, f.name",
        )
        assert len(g.filters) >= 1
