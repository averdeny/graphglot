"""Tests for macro AST nodes, parsing, generation, and tree transformation."""

from __future__ import annotations

import unittest

from pydantic import ValidationError

from graphglot import ast
from graphglot.ast.base import is_nonstandard
from graphglot.ast.macros import MacroCall, MacroVar
from graphglot.dialect.neo4j import Neo4j
from tests.graphglot.parser.helpers import ParserTestHelper


class TestSetScalarValidation(unittest.TestCase):
    """Bug #1: set() scalar path must preserve Pydantic validation."""

    def test_set_rejects_wrong_type_on_normal_node(self):
        """set() on a non-macro node should reject invalid types."""
        ident = ast.Identifier(name="foo")
        with self.assertRaises((ValidationError, TypeError)):
            ident.set("name", 123)  # name: str — int should be rejected

    def test_set_accepts_valid_type_on_normal_node(self):
        """set() on a non-macro node should accept valid types."""
        ident = ast.Identifier(name="foo")
        ident.set("name", "bar")
        self.assertEqual(ident.name, "bar")

    def test_set_allows_macro_in_typed_field(self):
        """set() should allow placing a macro node in a typed field."""
        stmt = ast.SimpleMatchStatement(graph_pattern_binding_table=MacroVar(name="orig"))
        new_macro = MacroVar(name="replaced")
        stmt.set("graph_pattern_binding_table", new_macro)
        self.assertIs(stmt.graph_pattern_binding_table, new_macro)


class TestMacroEquality(unittest.TestCase):
    """Bug #2: macro-containing nodes must compare correctly."""

    def test_macro_aware_dump_preserves_macro_data(self):
        """_macro_aware_dump includes macro field data that model_dump loses."""
        mv = MacroVar(name="tbl")
        stmt = ast.SimpleMatchStatement(graph_pattern_binding_table=mv)
        dumped = stmt._macro_aware_dump()
        field = dumped["graph_pattern_binding_table"]
        self.assertIn("name", field)
        self.assertEqual(field["name"], "tbl")

    def test_macro_aware_dump_distinguishes_different_macros(self):
        """_macro_aware_dump produces different output for different macros."""
        stmt1 = ast.SimpleMatchStatement(graph_pattern_binding_table=MacroVar(name="a"))
        stmt2 = ast.SimpleMatchStatement(graph_pattern_binding_table=MacroVar(name="b"))
        self.assertNotEqual(stmt1._macro_aware_dump(), stmt2._macro_aware_dump())

    def test_macro_aware_dump_matches_same_macros(self):
        """_macro_aware_dump produces equal output for identical macros."""
        stmt1 = ast.SimpleMatchStatement(graph_pattern_binding_table=MacroVar(name="x"))
        stmt2 = ast.SimpleMatchStatement(graph_pattern_binding_table=MacroVar(name="x"))
        self.assertEqual(stmt1._macro_aware_dump(), stmt2._macro_aware_dump())

    def test_macro_accessible_via_getattr(self):
        """Macro data is accessible via field access on the parent node."""
        mv = MacroVar(name="tbl")
        stmt = ast.SimpleMatchStatement(graph_pattern_binding_table=mv)
        self.assertIsInstance(stmt.graph_pattern_binding_table, MacroVar)
        self.assertEqual(stmt.graph_pattern_binding_table.name, "tbl")


class TestMacroAST(unittest.TestCase):
    """Test MacroVar and MacroCall AST node construction."""

    def test_macro_var_creation(self):
        mv = MacroVar(name="x")
        self.assertEqual(mv.name, "x")

    def test_macro_call_creation(self):
        arg = ast.UnsignedNumericLiteral(value=1)
        mc = MacroCall(name="fn", arguments=[arg])
        self.assertEqual(mc.name, "fn")
        self.assertEqual(len(mc.arguments), 1)

    def test_macro_call_empty_args(self):
        mc = MacroCall(name="fn", arguments=[])
        self.assertEqual(mc.arguments, [])

    def test_macro_is_nonstandard(self):
        self.assertTrue(is_nonstandard(MacroVar(name="x")))
        self.assertTrue(is_nonstandard(MacroCall(name="fn")))

    def test_macro_children(self):
        arg1 = ast.UnsignedNumericLiteral(value=1)
        arg2 = ast.UnsignedNumericLiteral(value=2)
        mc = MacroCall(name="fn", arguments=[arg1, arg2])
        children = list(mc.children())
        self.assertEqual(len(children), 2)

    def test_macro_find_all(self):
        inner = MacroVar(name="inner")
        outer = MacroCall(name="outer", arguments=[inner])
        found = list(outer.find_all(MacroVar))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].name, "inner")


class TestMacroAwareInit(unittest.TestCase):
    """Test that macro nodes bypass Pydantic validation in typed fields."""

    def test_macro_in_typed_field(self):
        mv = MacroVar(name="tbl")
        # SimpleMatchStatement expects graph_pattern_binding_table: GraphPatternBindingTable
        # With macro-aware init, MacroVar should be accepted.
        stmt = ast.SimpleMatchStatement(graph_pattern_binding_table=mv)
        self.assertIs(stmt.graph_pattern_binding_table, mv)

    def test_macro_in_list_field(self):
        mc = MacroCall(name="clause")
        # SimpleLinearQueryStatement expects list[SimpleQueryStatement]
        stmt = ast.SimpleLinearQueryStatement(list_simple_query_statement=[mc])
        self.assertEqual(len(stmt.list_simple_query_statement), 1)

    def test_non_macro_validation_unchanged(self):
        # Normal invalid data should still raise ValidationError
        with self.assertRaises(ValidationError):
            ast.SimpleMatchStatement(graph_pattern_binding_table="not_valid")

    def test_parent_tracking_with_macro(self):
        mv = MacroVar(name="tbl")
        stmt = ast.SimpleMatchStatement(graph_pattern_binding_table=mv)
        self.assertIs(mv._parent, stmt)

    def test_arg_key_and_index_tracking(self):
        arg1 = MacroVar(name="a")
        arg2 = MacroVar(name="b")
        mc = MacroCall(name="fn", arguments=[arg1, arg2])
        self.assertEqual(arg1._arg_key, "arguments")
        self.assertEqual(arg1._index, 0)
        self.assertEqual(arg2._index, 1)
        self.assertIs(arg1._parent, mc)


class TestMacroParsing(unittest.TestCase):
    """Test parsing of @-prefixed macro syntax."""

    def setUp(self):
        self.helper = ParserTestHelper()
        self.dialect = Neo4j()

    def _parse_cypher(self, query: str):
        """Parse a query using the Neo4j dialect."""
        from graphglot.lexer import Lexer

        lexer = Lexer(dialect=self.dialect)
        parser = self.dialect.parser()
        tokens = lexer.tokenize(query)
        return parser.parse(raw_tokens=tokens, query=query)

    def test_parse_macro_var(self):
        result = self.helper.parse_single("@name", ast.MacroCall)
        self.assertIsInstance(result, MacroVar)
        self.assertEqual(result.name, "name")

    def test_parse_macro_call_no_args(self):
        result = self.helper.parse_single("@fn()", ast.MacroCall)
        self.assertIsInstance(result, MacroCall)
        self.assertEqual(result.name, "fn")
        self.assertEqual(result.arguments, [])

    def test_parse_macro_call_with_args(self):
        result = self.helper.parse_single("@fn(1, 'hello')", ast.MacroCall)
        self.assertIsInstance(result, MacroCall)
        self.assertEqual(result.name, "fn")
        self.assertEqual(len(result.arguments), 2)

    def test_parse_nested_macros(self):
        result = self.helper.parse_single("@outer(@inner())", ast.MacroCall)
        self.assertIsInstance(result, MacroCall)
        self.assertEqual(result.name, "outer")
        self.assertEqual(len(result.arguments), 1)
        # Args parse as ValueExpression, so inner macro is nested inside wrappers
        inner_macros = list(result.find_all(MacroCall))
        # Should find at least 2: outer + inner
        inner_names = [m.name for m in inner_macros]
        self.assertIn("inner", inner_names)

    def test_macro_in_where(self):
        results = self._parse_cypher("MATCH (n) WHERE @pred(n) RETURN n")
        tree = results[0]
        # Macro should be inside a GraphPatternWhereClause
        where = tree.find_first(ast.GraphPatternWhereClause)
        self.assertIsNotNone(where, "GraphPatternWhereClause not found in AST")
        found = list(where.find_all(MacroCall))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].name, "pred")

    def test_macro_in_return(self):
        results = self._parse_cypher("MATCH (n) RETURN @expr")
        tree = results[0]
        # Macro should be inside a ReturnStatementBody
        ret = tree.find_first(ast.ReturnStatementBody)
        self.assertIsNotNone(ret, "ReturnStatementBody not found in AST")
        found = list(ret.find_all(MacroVar))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].name, "expr")

    def test_macro_as_statement(self):
        results = self._parse_cypher("@match_users() RETURN n")
        tree = results[0]
        found = list(tree.find_all(MacroCall))
        self.assertTrue(any(m.name == "match_users" for m in found))

    def test_macro_as_identifier(self):
        results = self._parse_cypher("MATCH (@var) RETURN @var")
        tree = results[0]
        found_vars = list(tree.find_all(MacroVar))
        self.assertTrue(
            any(m.name == "var" for m in found_vars),
            f"Expected MacroVar(name='var'), got: {found_vars}",
        )

    def test_macro_as_label(self):
        results = self._parse_cypher("MATCH (n:@lbl) RETURN n")
        tree = results[0]
        # Macro should be inside an IsLabelExpression
        label_expr = tree.find_first(ast.IsLabelExpression)
        self.assertIsNotNone(label_expr, "IsLabelExpression not found in AST")
        found = list(label_expr.find_all(MacroVar))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].name, "lbl")

    def test_macro_source_span(self):
        result = self.helper.parse_single("@name", ast.MacroCall)
        self.assertIsNotNone(result.source_span)

    def test_macro_full_query(self):
        results = self.helper.parse("@full_query()")
        self.assertIsNotNone(results)
        self.assertGreaterEqual(len(results), 1)
        # Full query wraps in GqlProgram; find the MacroCall inside
        found = list(results[0].find_all(MacroCall))
        self.assertGreaterEqual(len(found), 1)
        self.assertEqual(found[0].name, "full_query")


class TestMacroGeneration(unittest.TestCase):
    """Test generation of macro nodes back to text."""

    def setUp(self):
        self.dialect = Neo4j()

    def _generate(self, expr):
        return self.dialect.generate(expr)

    def test_generate_macro_var(self):
        result = self._generate(MacroVar(name="name"))
        self.assertEqual(result, "@name")

    def test_generate_macro_call_empty(self):
        result = self._generate(MacroCall(name="fn", arguments=[]))
        self.assertEqual(result, "@fn()")

    def test_generate_macro_call_with_args(self):
        result = self._generate(
            MacroCall(
                name="fn",
                arguments=[
                    ast.UnsignedNumericLiteral(value=1),
                    ast.CharacterStringLiteral(value="hello"),
                ],
            )
        )
        self.assertEqual(result, "@fn(1, 'hello')")


class TestMacroRoundTrip(unittest.TestCase):
    """Test parse → generate → parse round-trips for macros."""

    def setUp(self):
        self.dialect = Neo4j()
        self.helper = ParserTestHelper()

    def _roundtrip(self, query: str, expr_type=ast.MacroCall):
        parsed = self.helper.parse_single(query, expr_type)
        generated = self.dialect.generate(parsed)
        reparsed = self.helper.parse_single(generated, expr_type)
        return parsed, generated, reparsed

    def test_roundtrip_macro_var(self):
        parsed, generated, reparsed = self._roundtrip("@name")
        self.assertEqual(generated, "@name")
        self.assertIsInstance(reparsed, MacroVar)
        self.assertEqual(reparsed.name, "name")

    def test_roundtrip_macro_call(self):
        parsed, generated, reparsed = self._roundtrip("@fn(1, 'hello')")
        self.assertIsInstance(reparsed, MacroCall)
        self.assertEqual(reparsed.name, "fn")
        self.assertEqual(len(reparsed.arguments), 2)

    def test_roundtrip_nested(self):
        parsed, generated, reparsed = self._roundtrip("@outer(@inner())")
        self.assertIsInstance(reparsed, MacroCall)
        self.assertEqual(len(reparsed.arguments), 1)
        # Inner macro is wrapped in ValueExpression layers
        inner_macros = list(reparsed.find_all(MacroCall))
        inner_names = [m.name for m in inner_macros]
        self.assertIn("inner", inner_names)

    def test_roundtrip_macro_in_query(self):
        query = "MATCH (n) WHERE @pred(n) RETURN n"
        from graphglot.lexer import Lexer

        lexer = Lexer(dialect=self.dialect)
        parser = self.dialect.parser()
        tokens = lexer.tokenize(query)
        results = parser.parse(raw_tokens=tokens, query=query)
        generated = self.dialect.generate(results[0])
        # Re-parse
        tokens2 = lexer.tokenize(generated)
        results2 = parser.parse(raw_tokens=tokens2, query=generated)
        # Verify macro survived the round-trip
        found = list(results2[0].find_all(MacroCall))
        self.assertTrue(
            any(m.name == "pred" for m in found),
            f"MacroCall(name='pred') not found after round-trip. Generated: {generated}",
        )


class TestTransform(unittest.TestCase):
    """Test Expression.transform() tree transformation."""

    def test_transform_identity(self):
        mc = MacroCall(name="fn", arguments=[MacroVar(name="x"), MacroVar(name="y")])
        result = mc.transform(lambda n: n)
        self.assertEqual(result.name, "fn")
        self.assertEqual(len(result.arguments), 2)

    def test_transform_replace_node(self):
        mc = MacroCall(name="fn", arguments=[MacroVar(name="x")])

        def replace_macro_var(node):
            if isinstance(node, MacroVar):
                return ast.Identifier(name=node.name)
            return node

        result = mc.transform(replace_macro_var)
        self.assertIsInstance(result, MacroCall)
        self.assertEqual(len(result.arguments), 1)
        self.assertIsInstance(result.arguments[0], ast.Identifier)

    def test_transform_returns_none_removes(self):
        mc = MacroCall(name="fn", arguments=[MacroVar(name="x"), MacroVar(name="y")])

        def remove_x(node):
            if isinstance(node, MacroVar) and node.name == "x":
                return None
            return node

        result = mc.transform(remove_x)
        self.assertIsInstance(result, MacroCall)

    def test_transform_copy_default(self):
        original = MacroCall(name="fn", arguments=[MacroVar(name="x")])
        result = original.transform(lambda n: n)
        # copy=True is default, so original should be unchanged
        self.assertIsNot(result, original)

    def test_transform_no_copy(self):
        original = MacroCall(name="fn", arguments=[MacroVar(name="x")])
        result = original.transform(lambda n: n, copy=False)
        # With copy=False, result IS the original
        self.assertIs(result, original)

    def test_transform_in_list_field(self):
        mv1 = MacroVar(name="a")
        mv2 = MacroVar(name="b")
        mc = MacroCall(name="fn", arguments=[mv1, mv2])

        def replace_a(node):
            if isinstance(node, MacroVar) and node.name == "a":
                return MacroVar(name="replaced")
            return node

        result = mc.transform(replace_a)
        self.assertIsInstance(result, MacroCall)
        names = [a.name for a in result.arguments if isinstance(a, MacroVar)]
        self.assertIn("replaced", names)
        self.assertIn("b", names)


class TestSetWithIndex(unittest.TestCase):
    """Test Expression.set() with index parameter."""

    def test_set_replaces_list_element(self):
        mv1 = MacroVar(name="a")
        mv2 = MacroVar(name="b")
        mc = MacroCall(name="fn", arguments=[mv1, mv2])
        new_var = MacroVar(name="c")
        mc.set("arguments", new_var, index=1)
        self.assertEqual(mc.arguments[1].name, "c")

    def test_set_parent_tracking_after_replace(self):
        mv1 = MacroVar(name="a")
        mv2 = MacroVar(name="b")
        mc = MacroCall(name="fn", arguments=[mv1, mv2])
        new_var = MacroVar(name="c")
        mc.set("arguments", new_var, index=0)
        self.assertIs(new_var._parent, mc)

    def test_set_none_removes_list_element(self):
        mv1 = MacroVar(name="a")
        mv2 = MacroVar(name="b")
        mv3 = MacroVar(name="c")
        mc = MacroCall(name="fn", arguments=[mv1, mv2, mv3])
        mc.set("arguments", None, index=1)
        self.assertEqual(len(mc.arguments), 2)
        self.assertEqual(mc.arguments[0].name, "a")
        self.assertEqual(mc.arguments[1].name, "c")


class TestDfsPrune(unittest.TestCase):
    """Test Expression.dfs() with prune parameter."""

    def test_dfs_prune_skips_subtree(self):
        inner = MacroVar(name="inner")
        outer = MacroCall(name="outer", arguments=[inner])

        # Prune at MacroCall level — should NOT visit MacroVar children
        visited = list(outer.dfs(prune=lambda n: isinstance(n, MacroCall)))
        types = [type(n).__name__ for n in visited]
        self.assertIn("MacroCall", types)
        self.assertNotIn("MacroVar", types)

    def test_dfs_no_prune_visits_all(self):
        inner = MacroVar(name="inner")
        outer = MacroCall(name="outer", arguments=[inner])

        visited = list(outer.dfs())
        self.assertEqual(len(visited), 2)


class TestMacroComposition(unittest.TestCase):
    """Test that bare MacroCall composes with UNION/OTHERWISE/NEXT."""

    def setUp(self):
        from graphglot.dialect import Dialect

        self.dialect = Dialect.get_or_raise(None)

    def _parse(self, query: str):
        from graphglot.lexer import Lexer

        lexer = Lexer(dialect=self.dialect)
        parser = self.dialect.parser()
        tokens = lexer.tokenize(query)
        return parser.parse(raw_tokens=tokens, query=query)

    def test_macro_otherwise(self):
        """@ref("parent") OTHERWISE MATCH (b) RETURN b → CompositeQueryExpression."""
        results = self._parse('@ref("parent") OTHERWISE MATCH (b) RETURN b')
        tree = results[0]
        cqe = tree.find_first(ast.CompositeQueryExpression)
        self.assertIsNotNone(cqe, "CompositeQueryExpression not found in AST")
        # Left side should contain the macro
        found = list(cqe.find_all(MacroCall))
        self.assertTrue(any(m.name == "ref" for m in found))

    def test_macro_union_all(self):
        """@ref("a") UNION ALL @ref("b") → CompositeQueryExpression with SetOperator."""
        results = self._parse('@ref("a") UNION ALL @ref("b")')
        tree = results[0]
        cqe = tree.find_first(ast.CompositeQueryExpression)
        self.assertIsNotNone(cqe, "CompositeQueryExpression not found in AST")
        macros = list(cqe.find_all(MacroCall))
        macro_names = [m.name for m in macros]
        self.assertIn("ref", macro_names)
        self.assertGreaterEqual(len(macros), 2)

    def test_macro_next(self):
        """@ref("parent") NEXT MATCH (b) RETURN b → StatementBlock with NextStatement."""
        results = self._parse('@ref("parent") NEXT MATCH (b) RETURN b')
        tree = results[0]
        sb = tree.find_first(ast.StatementBlock)
        self.assertIsNotNone(sb, "StatementBlock not found in AST")
        found = list(sb.find_all(MacroCall))
        self.assertTrue(any(m.name == "ref" for m in found))

    def test_multi_union(self):
        """@ref("a") UNION @ref("b") UNION @ref("c") → 2 conjunction elements."""
        results = self._parse('@ref("a") UNION @ref("b") UNION @ref("c")')
        tree = results[0]
        cqe = tree.find_first(ast.CompositeQueryExpression)
        self.assertIsNotNone(cqe, "CompositeQueryExpression not found in AST")
        self.assertIsNotNone(cqe.query_conjunction_elements)
        self.assertEqual(len(cqe.query_conjunction_elements), 2)
        macros = list(cqe.find_all(MacroCall))
        self.assertEqual(len(macros), 3)

    def test_macro_with_return_unchanged(self):
        """@macro() RETURN n still uses candidate 1 path (PQS + PRS)."""
        results = self._parse("@macro() RETURN n")
        tree = results[0]
        found = list(tree.find_all(MacroCall))
        self.assertTrue(any(m.name == "macro" for m in found))
        ret = tree.find_first(ast.ReturnStatementBody)
        self.assertIsNotNone(
            ret, "ReturnStatementBody not found — candidate 1 path should still work"
        )


class TestDeepCopy(unittest.TestCase):
    """Test Expression.deep_copy() produces correct parent links."""

    def test_deep_copy_parent_links_point_to_copied_tree(self):
        """Every child's _parent in the copy must be reachable from the copy root."""
        query = "MATCH (n:Person) RETURN n.name"
        dialect = Neo4j()
        tree = dialect.parse(query)[0]
        copy = tree.deep_copy()

        copy_nodes = {id(n) for n in copy.dfs()}
        for node in copy.dfs():
            if node is copy:
                continue
            self.assertIsNotNone(node._parent, f"{node!r} has no parent")
            self.assertIn(
                id(node._parent),
                copy_nodes,
                f"{node!r}._parent is a ghost — not in copied tree",
            )

    def test_deep_copy_root_has_no_parent(self):
        """The root of a deep-copied tree should have no parent metadata."""
        query = "MATCH (n) RETURN n"
        dialect = Neo4j()
        tree = dialect.parse(query)[0]
        copy = tree.deep_copy()

        self.assertIsNone(copy._parent)
        self.assertIsNone(copy._arg_key)
        self.assertIsNone(copy._index)

    def test_transform_copy_true_replaces_scalar_field(self):
        """transform(copy=True) replacing a node should be visible in generated output."""
        dialect = Neo4j()
        tree = dialect.parse("MATCH (n) RETURN n")[0]

        def replace_identifier(node):
            if isinstance(node, ast.Identifier) and node.name == "n":
                return ast.Identifier(name="x")
            return node

        result = tree.transform(replace_identifier, copy=True)
        gql = result.to_gql(dialect="neo4j")
        self.assertIn("x", gql)

    def test_transform_copy_true_preserves_original(self):
        """transform(copy=True) must not modify the original tree."""
        dialect = Neo4j()
        tree = dialect.parse("MATCH (n) RETURN n")[0]
        original_gql = tree.to_gql(dialect="neo4j")

        def replace_identifier(node):
            if isinstance(node, ast.Identifier) and node.name == "n":
                return ast.Identifier(name="x")
            return node

        tree.transform(replace_identifier, copy=True)
        self.assertEqual(tree.to_gql(dialect="neo4j"), original_gql)

    def test_deep_copy_preserves_spans(self):
        """source_span should survive deep_copy for all span-bearing nodes."""
        dialect = Neo4j()
        tree = dialect.parse("MATCH (n) RETURN n")[0]

        original_spans = [
            (i, node.source_span)
            for i, node in enumerate(tree.dfs())
            if node.source_span is not None
        ]
        if not original_spans:
            self.skipTest("No spans found in parsed tree")

        copy = tree.deep_copy()
        copy_nodes = list(copy.dfs())
        for i, expected_span in original_spans:
            self.assertEqual(
                copy_nodes[i].source_span,
                expected_span,
                f"Span mismatch at DFS index {i} ({type(copy_nodes[i]).__name__})",
            )


class TestTransformMacroExpansion(unittest.TestCase):
    """Test that transform() can replace MacroCall with non-macro expansions."""

    def test_transform_expands_macro_in_scalar_typed_field(self):
        """Replacing a MacroCall in a typed scalar field with a non-macro should work."""
        macro = MacroCall(name="ref", arguments=[])
        # Place macro in a typed field via model_construct (as __init__ does for macros)
        stmt = ast.SimpleMatchStatement.model_construct(
            graph_pattern_binding_table=macro,
        )
        macro._parent = stmt
        macro._arg_key = "graph_pattern_binding_table"

        # Transform: replace the macro with an Identifier (wrong type for the field,
        # but should be allowed because we're replacing a macro)
        replacement = ast.Identifier(name="expanded")

        def expand(node):
            if isinstance(node, MacroCall) and node.name == "ref":
                return replacement
            return node

        result = stmt.transform(expand, copy=True)
        self.assertEqual(result.graph_pattern_binding_table.name, "expanded")

    def test_set_replaces_macro_with_nonmacro_in_typed_field(self):
        """Direct set() replacing a macro with a type-mismatched non-macro should succeed."""
        macro = MacroCall(name="placeholder", arguments=[])
        stmt = ast.SimpleMatchStatement.model_construct(
            graph_pattern_binding_table=macro,
        )
        macro._parent = stmt
        macro._arg_key = "graph_pattern_binding_table"

        # This would fail with Pydantic validation without the fix
        replacement = ast.Identifier(name="expanded")
        stmt.set("graph_pattern_binding_table", replacement)
        self.assertIs(stmt.graph_pattern_binding_table, replacement)

    def test_set_parent_tracking_after_macro_expansion(self):
        """Parent and arg_key should be correct after replacing a macro."""
        macro = MacroCall(name="placeholder", arguments=[])
        stmt = ast.SimpleMatchStatement.model_construct(
            graph_pattern_binding_table=macro,
        )
        macro._parent = stmt
        macro._arg_key = "graph_pattern_binding_table"

        replacement = ast.Identifier(name="expanded")
        stmt.set("graph_pattern_binding_table", replacement)
        self.assertIs(replacement._parent, stmt)
        self.assertEqual(replacement._arg_key, "graph_pattern_binding_table")

    def test_transform_macro_expansion_preserves_original(self):
        """copy=True must not modify the original tree."""
        macro = MacroCall(name="ref", arguments=[])
        stmt = ast.SimpleMatchStatement.model_construct(
            graph_pattern_binding_table=macro,
        )
        macro._parent = stmt
        macro._arg_key = "graph_pattern_binding_table"

        def expand(node):
            if isinstance(node, MacroCall):
                return ast.Identifier(name="expanded")
            return node

        result = stmt.transform(expand, copy=True)
        # Original should still have the macro
        self.assertIsInstance(stmt.graph_pattern_binding_table, MacroCall)
        # Result should have the replacement
        self.assertEqual(result.graph_pattern_binding_table.name, "expanded")

    def test_set_still_validates_normal_scalar_field(self):
        """Regression: non-macro scalar fields should still be validated."""
        ident = ast.Identifier(name="foo")
        with self.assertRaises((ValidationError, TypeError)):
            ident.set("name", 123)  # name: str — int should be rejected

    def test_transform_macro_expansion_full_query(self):
        """End-to-end: parse with macro, transform to expand, generate result."""
        dialect = Neo4j()
        # Parse a query containing a macro reference
        trees = dialect.parse('@ref("parent") UNION ALL MATCH (n) RETURN n')
        tree = trees[0]

        # Parse the replacement query
        replacement_trees = dialect.parse("MATCH (a) RETURN a")
        replacement = replacement_trees[0]

        # Transform: replace the macro with the parsed query
        def expand(node):
            if isinstance(node, MacroCall) and node.name == "ref":
                return replacement
            return node

        result = tree.transform(expand, copy=True)
        generated = result.to_gql(dialect="neo4j")
        self.assertIn("MATCH", generated)
        self.assertNotIn("@ref", generated)


if __name__ == "__main__":
    unittest.main()
