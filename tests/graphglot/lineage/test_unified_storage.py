"""Tests for unified LineageGraph node storage."""

from graphglot.lineage.models import (
    Binding,
    BindingKind,
    Filter,
    Graph,
    LineageGraph,
    LineageNode,
    OutputField,
    Pattern,
    PropertyRef,
)


def _binding(id: str, name: str = "x") -> Binding:
    """Helper to create a Binding with required fields filled in."""
    return Binding(id=id, name=name, kind=BindingKind.NODE, scope_id="")


class TestUnifiedNodes:
    """Test that LineageGraph.nodes stores all entity types."""

    def test_all_entities_in_nodes(self):
        g = LineageGraph()
        graph = Graph(id="g_0", name="default")
        binding = _binding("b_0", "n")
        pattern = Pattern(id="pat_0")
        prop = PropertyRef(id="prop_0", property_name="name", span=None)
        output = OutputField(id="o_0", alias=None, position=0, span=None)
        filt = Filter(id="f_0")

        for entity in [graph, binding, pattern, prop, output, filt]:
            g.nodes[entity.id] = entity

        assert len(g.nodes) == 6
        assert all(isinstance(v, LineageNode) for v in g.nodes.values())

    def test_typed_views_filter_correctly(self):
        g = LineageGraph()
        g.nodes["g_0"] = Graph(id="g_0", name="default")
        g.nodes["b_0"] = _binding("b_0", "n")
        g.nodes["b_1"] = _binding("b_1", "m")
        g.nodes["f_0"] = Filter(id="f_0")

        assert len(g.bindings) == 2
        assert len(g.graphs) == 1
        assert len(g.filters) == 1
        assert "b_0" in g.bindings
        assert "g_0" not in g.bindings
        assert g.bindings["b_0"].name == "n"

    def test_typed_view_get(self):
        g = LineageGraph()
        g.nodes["b_0"] = _binding("b_0", "n")

        assert g.bindings.get("b_0") is not None
        assert g.bindings.get("missing") is None
        assert g.graphs.get("b_0") is None  # wrong type

    def test_node_lookup(self):
        g = LineageGraph()
        binding = _binding("b_0", "n")
        g.nodes["b_0"] = binding

        assert g.node("b_0") is binding
        assert g.node("missing") is None

    def test_typed_view_iteration(self):
        g = LineageGraph()
        g.nodes["b_0"] = _binding("b_0", "a")
        g.nodes["b_1"] = _binding("b_1", "b")
        g.nodes["g_0"] = Graph(id="g_0", name="default")

        keys = list(g.bindings.keys())
        assert set(keys) == {"b_0", "b_1"}

        items = list(g.bindings.items())
        assert len(items) == 2

        values = list(g.bindings.values())
        assert all(isinstance(v, Binding) for v in values)

    def test_entity_classes_inherit_lineage_node(self):
        for cls in [Graph, Binding, Pattern, PropertyRef, OutputField, Filter]:
            assert issubclass(cls, LineageNode)
