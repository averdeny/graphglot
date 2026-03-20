"""Tests for variable type inference rules."""

from graphglot.ast import expressions as ast
from graphglot.dialect.base import Dialect
from graphglot.typing import ExternalContext, GqlType, TypeAnnotator, TypeKind


def _annotate(query: str, **kwargs) -> ast.Expression:
    d = Dialect.get_or_raise("ir")
    exprs = d.parse(query)
    TypeAnnotator(**kwargs).annotate(exprs[0])
    return exprs[0]


class TestNodeVariable:
    def test_node_variable_type(self):
        root = _annotate("MATCH (n) RETURN n")
        evd = root.find_first(ast.ElementVariableDeclaration)
        assert evd._resolved_type.kind == TypeKind.NODE

    def test_node_variable_with_label(self):
        root = _annotate("MATCH (n:Person) RETURN n")
        evd = root.find_first(ast.ElementVariableDeclaration)
        assert evd._resolved_type.kind == TypeKind.NODE
        assert "Person" in evd._resolved_type.labels

    def test_node_variable_with_multiple_labels(self):
        root = _annotate("MATCH (n:Person&Employee) RETURN n")
        evd = root.find_first(ast.ElementVariableDeclaration)
        assert evd._resolved_type.kind == TypeKind.NODE
        assert evd._resolved_type.labels == frozenset({"Person", "Employee"})

    def test_node_variable_reference_resolves(self):
        root = _annotate("MATCH (n:Person) RETURN n")
        # The 'n' in RETURN should resolve to NODE
        for ident in root.find_all(ast.Identifier):
            if ident.name == "n" and ident._resolved_type and not ident._resolved_type.is_unknown:
                assert ident._resolved_type.kind == TypeKind.NODE
                break
        else:
            raise AssertionError("No resolved identifier 'n' found")


class TestEdgeVariable:
    def test_edge_variable_type(self):
        root = _annotate("MATCH (a)-[e]->(b) RETURN e")
        evds = list(root.find_all(ast.ElementVariableDeclaration))
        edge_evd = [e for e in evds if e._resolved_type and e._resolved_type.kind == TypeKind.EDGE]
        assert len(edge_evd) >= 1

    def test_edge_variable_with_label(self):
        root = _annotate("MATCH (a)-[e:KNOWS]->(b) RETURN e")
        evds = list(root.find_all(ast.ElementVariableDeclaration))
        edge_evd = [e for e in evds if e._resolved_type and e._resolved_type.kind == TypeKind.EDGE]
        assert len(edge_evd) >= 1
        assert "KNOWS" in edge_evd[0]._resolved_type.labels


class TestPathVariable:
    def test_path_variable_type(self):
        root = _annotate("MATCH p = (a)-[e]->(b) RETURN p")
        pvd = root.find_first(ast.PathVariableDeclaration)
        assert pvd._resolved_type.kind == TypeKind.PATH

    def test_path_variable_reference(self):
        root = _annotate("MATCH p = (a)-[e]->(b) RETURN p")
        for ident in root.find_all(ast.Identifier):
            if ident.name == "p" and ident._resolved_type and not ident._resolved_type.is_unknown:
                assert ident._resolved_type.kind == TypeKind.PATH
                break
        else:
            raise AssertionError("No resolved identifier 'p' found")


class TestBindingVariableReference:
    """Tests that BindingVariableReference propagates the type from its inner Identifier."""

    def test_binding_variable_reference_type(self):
        root = _annotate("MATCH (n:Person) RETURN n")
        bvr = root.find_first(ast.BindingVariableReference)
        assert bvr is not None
        assert bvr._resolved_type.kind == TypeKind.NODE
        assert "Person" in bvr._resolved_type.labels

    def test_multi_label_binding_variable_reference(self):
        root = _annotate("MATCH (n:Person&Employee) RETURN n")
        bvr = root.find_first(ast.BindingVariableReference)
        assert bvr is not None
        assert bvr._resolved_type.kind == TypeKind.NODE
        assert bvr._resolved_type.labels == frozenset({"Person", "Employee"})

    def test_multiple_bvr_in_return(self):
        root = _annotate("MATCH (a:Person)-[r:KNOWS]->(b:Company) RETURN a, r, b")
        bvrs = list(root.find_all(ast.BindingVariableReference))
        resolved = {b.binding_variable.name: b._resolved_type for b in bvrs if b._resolved_type}
        assert resolved["a"].kind == TypeKind.NODE
        assert "Person" in resolved["a"].labels
        assert resolved["r"].kind == TypeKind.EDGE
        assert "KNOWS" in resolved["r"].labels
        assert resolved["b"].kind == TypeKind.NODE
        assert "Company" in resolved["b"].labels

    def test_bvr_with_alias(self):
        root = _annotate("MATCH (n:Person) RETURN n AS person")
        bvr = root.find_first(ast.BindingVariableReference)
        assert bvr is not None
        assert bvr._resolved_type.kind == TypeKind.NODE
        assert "Person" in bvr._resolved_type.labels

    def test_edge_binding_variable_reference_type(self):
        root = _annotate("MATCH (a)-[e:KNOWS]->(b) RETURN e")
        bvrs = list(root.find_all(ast.BindingVariableReference))
        edge_bvr = [b for b in bvrs if b.binding_variable.name == "e"]
        assert len(edge_bvr) == 1
        assert edge_bvr[0]._resolved_type.kind == TypeKind.EDGE
        assert "KNOWS" in edge_bvr[0]._resolved_type.labels

    def test_path_binding_variable_reference_type(self):
        root = _annotate("MATCH p = (a)-[e]->(b) RETURN p")
        bvrs = list(root.find_all(ast.BindingVariableReference))
        path_bvr = [b for b in bvrs if b.binding_variable.name == "p"]
        assert len(path_bvr) == 1
        assert path_bvr[0]._resolved_type.kind == TypeKind.PATH

    def test_bvr_unlabeled_node(self):
        root = _annotate("MATCH (n) RETURN n")
        bvr = root.find_first(ast.BindingVariableReference)
        assert bvr is not None
        assert bvr._resolved_type.kind == TypeKind.NODE
        assert bvr._resolved_type.labels == frozenset()


class TestParameterReference:
    def test_unknown_without_context(self):
        root = _annotate("RETURN $param")
        ref = root.find_first(ast.GeneralParameterReference)
        assert ref._resolved_type.is_unknown

    def test_known_with_context(self):
        ctx = ExternalContext(parameter_types={"param": GqlType.integer()})
        root = _annotate("RETURN $param", external_context=ctx)
        ref = root.find_first(ast.GeneralParameterReference)
        assert ref._resolved_type.kind == TypeKind.INT


class TestAnnotationResult:
    def test_annotated_count(self):
        d = Dialect.get_or_raise("ir")
        exprs = d.parse("MATCH (n) RETURN n")
        annotator = TypeAnnotator()
        result = annotator.annotate(exprs[0])
        assert result.annotated_count > 0
        assert result.ok
