"""Tests for predicate parsing functionality."""

import unittest

from graphglot import ast
from graphglot.error import ParseError

from .helpers import ParserTestHelper


class TestPredicates(unittest.TestCase):
    """Test suite for predicate parser."""

    def setUp(self):
        self.helper = ParserTestHelper()

    def test_comparison_predicate_equals(self):
        query = "n.age = 30"
        expr = self.helper.parse_single(query, ast.ComparisonPredicate)
        self.assertIsInstance(expr, ast.ComparisonPredicate)
        self.assertIsInstance(expr.comparison_predicate_part_2, ast.ComparisonPredicatePart2)
        self.assertEqual(
            expr.comparison_predicate_part_2.comp_op,
            ast.ComparisonPredicatePart2.CompOp.EQUALS,
        )

    def test_comparison_predicate_greater_than(self):
        query = "n.age > 30"
        expr = self.helper.parse_single(query, ast.ComparisonPredicate)
        self.assertIsInstance(expr, ast.ComparisonPredicate)
        self.assertEqual(
            expr.comparison_predicate_part_2.comp_op,
            ast.ComparisonPredicatePart2.CompOp.GREATER_THAN,
        )

    def test_null_predicate_is_null(self):
        query = "n.name IS NOT NULL"
        expr = self.helper.parse_single(query, ast.NullPredicate)
        self.assertIsInstance(expr, ast.NullPredicate)
        self.assertIsInstance(expr.null_predicate_part_2, ast.NullPredicatePart2)
        self.assertTrue(expr.null_predicate_part_2.not_)

    def test_value_type_predicate(self):
        query = "n.age IS NOT TYPED INTEGER"
        expr = self.helper.parse_single(query, ast.ValueTypePredicate)
        self.assertIsInstance(expr, ast.ValueTypePredicate)
        self.assertIsInstance(
            expr.value_type_predicate_part_2,
            ast.ValueTypePredicatePart2,
        )
        self.assertTrue(expr.value_type_predicate_part_2.not_)
        self.assertIsInstance(
            expr.value_type_predicate_part_2.value_type,
            ast.NumericType,
        )

    def test_normalized_predicate(self):
        query = "n.name IS NOT NFC NORMALIZED"
        expr = self.helper.parse_single(query, ast.NormalizedPredicate)
        self.assertIsInstance(expr, ast.NormalizedPredicate)
        self.assertTrue(expr.normalized_predicate_part_2.not_)
        self.assertIsNotNone(expr.normalized_predicate_part_2.normal_form)

    def test_directed_predicate(self):
        query = "e IS NOT DIRECTED"
        expr = self.helper.parse_single(query, ast.DirectedPredicate)
        self.assertIsInstance(expr, ast.DirectedPredicate)
        self.assertTrue(expr.directed_predicate_part_2.not_)

    def test_labeled_predicate(self):
        query = "n : Person"
        expr = self.helper.parse_single(query, ast.LabeledPredicate)
        self.assertIsInstance(expr, ast.LabeledPredicate)
        self.assertIsInstance(
            expr.labeled_predicate_part_2,
            ast.LabeledPredicatePart2,
        )

    def test_labeled_predicate_with_keyword(self):
        query = "n IS LABELED Person"
        expr = self.helper.parse_single(query, ast.LabeledPredicate)
        self.assertIsInstance(expr, ast.LabeledPredicate)
        inner = expr.labeled_predicate_part_2.is_labeled_or_colon.is_labeled_or_colon
        self.assertIsInstance(inner, ast.IsLabeledOrColon._IsNotLabeled)
        self.assertFalse(inner.not_)

    def test_labeled_predicate_negated_with_keyword(self):
        query = "n IS NOT LABELED Person"
        expr = self.helper.parse_single(query, ast.LabeledPredicate)
        self.assertIsInstance(expr, ast.LabeledPredicate)
        inner = expr.labeled_predicate_part_2.is_labeled_or_colon.is_labeled_or_colon
        self.assertIsInstance(inner, ast.IsLabeledOrColon._IsNotLabeled)
        self.assertTrue(inner.not_)

    def test_labeled_predicate_with_complex_label_expression(self):
        # Label expressions allow disjunction/conjunction/negation per ISO 39075 §16.8.
        query = "n IS LABELED Person | Manager"
        expr = self.helper.parse_single(query, ast.LabeledPredicate)
        self.assertIsInstance(expr, ast.LabeledPredicate)

    def test_bare_is_label_is_rejected(self):
        # ISO 39075 §19.9 requires the LABELED keyword in the IS-prefixed
        # form (only NOT is optional). The colon form (`n :Person`) is
        # the alternative for omitting the keyword.
        with self.assertRaises(ParseError):
            self.helper.parse_single("n IS Person", ast.LabeledPredicate)

    def test_property_exists_predicate(self):
        query = "PROPERTY_EXISTS(n, name)"
        expr = self.helper.parse_single(query, ast.PropertyExistsPredicate)
        self.assertIsInstance(expr, ast.PropertyExistsPredicate)

    def test_all_different_predicate(self):
        query = "ALL_DIFFERENT(n1, n2, n3)"
        expr = self.helper.parse_single(query, ast.AllDifferentPredicate)
        self.assertIsInstance(expr, ast.AllDifferentPredicate)
        self.assertGreaterEqual(len(expr.list_element_variable_reference), 2)

    def test_same_predicate(self):
        query = "SAME(n1, n2)"
        expr = self.helper.parse_single(query, ast.SamePredicate)
        self.assertIsInstance(expr, ast.SamePredicate)
        self.assertEqual(len(expr.list_element_variable_reference), 2)

    def test_exists_predicate_graph_pattern(self):
        query = "EXISTS {(n)-[r]->(m)}"
        expr = self.helper.parse_single(query, ast.ExistsPredicate)
        self.assertIsInstance(expr, ast.ExistsPredicate)

    def test_exists_with_statement_block(self):
        query = "EXISTS {MATCH (n)-[r]->(m)}"
        expr = self.helper.parse_single(query, ast.ExistsPredicate)
        self.assertIsInstance(expr, ast.ExistsPredicate)
