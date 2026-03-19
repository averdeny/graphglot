"""Tests for the @nonstandard decorator and helper functions."""

import pytest

from graphglot.ast import (
    AmbiguousValueExpression,
    ArithmeticAbsoluteValueFunction,
    ArithmeticFactor,
    ArithmeticTerm,
    ArithmeticValueExpression,
    BindingVariableReference,
    ConcatenationValueExpression,
    Expression,
    GqlProgram,
    Identifier,
    is_nonstandard,
    nonstandard,
    nonstandard_reason,
)


class TestNonstandardDetection:
    """Test that known non-standard classes are correctly detected."""

    @pytest.mark.parametrize(
        "cls",
        [
            AmbiguousValueExpression,
            ConcatenationValueExpression,
            ArithmeticValueExpression,
            ArithmeticAbsoluteValueFunction,
            ArithmeticFactor,
            ArithmeticTerm,
        ],
        ids=lambda c: c.__name__,
    )
    def test_known_nonstandard_classes(self, cls):
        assert is_nonstandard(cls)

    @pytest.mark.parametrize(
        "cls",
        [GqlProgram, Identifier, Expression],
        ids=lambda c: c.__name__,
    )
    def test_standard_classes_not_detected(self, cls):
        assert not is_nonstandard(cls)


class TestMROInheritance:
    """Test that subclasses inherit __nonstandard__ via MRO."""

    def test_concatenation_inherits_from_ambiguous(self):
        assert is_nonstandard(ConcatenationValueExpression)
        reason = nonstandard_reason(ConcatenationValueExpression)
        assert reason == nonstandard_reason(AmbiguousValueExpression)

    def test_arithmetic_value_expr_has_own_reason(self):
        assert is_nonstandard(ArithmeticValueExpression)
        reason = nonstandard_reason(ArithmeticValueExpression)
        assert reason == "Parse-time ambiguity: arithmetic could be numeric or duration"


class TestInnerClasses:
    """Inner classes are detected as nonstandard via their enclosing class."""

    def test_multiplicative_factor_is_nonstandard(self):
        assert is_nonstandard(ArithmeticTerm._MultiplicativeFactor)

    def test_signed_term_is_nonstandard(self):
        assert is_nonstandard(ArithmeticValueExpression._SignedTerm)

    def test_multiplicative_factor_reason_from_enclosing(self):
        assert nonstandard_reason(ArithmeticTerm._MultiplicativeFactor) == nonstandard_reason(
            ArithmeticTerm
        )

    def test_signed_term_reason_from_enclosing(self):
        assert nonstandard_reason(ArithmeticValueExpression._SignedTerm) == nonstandard_reason(
            ArithmeticValueExpression
        )

    def test_standard_inner_class_not_flagged(self):
        """Inner classes of standard classes should not be flagged."""
        from graphglot.ast import NumericValueExpression

        assert not is_nonstandard(NumericValueExpression._SignedTerm)


class TestInstanceSupport:
    """Test that is_nonstandard and nonstandard_reason work on instances."""

    def test_is_nonstandard_on_instance(self):
        instance = Identifier(name="x")
        assert not is_nonstandard(instance)

    def test_is_nonstandard_on_nonstandard_instance(self):
        instance = ArithmeticFactor(
            arithmetic_primary=BindingVariableReference(binding_variable=Identifier(name="x")),
        )
        assert is_nonstandard(instance)

    def test_nonstandard_reason_on_instance(self):
        instance = ArithmeticFactor(
            arithmetic_primary=BindingVariableReference(binding_variable=Identifier(name="x")),
        )
        assert nonstandard_reason(instance) == "Parse convenience: not a concept from the GQL spec"


class TestNonstandardReason:
    """Test nonstandard_reason returns correct strings."""

    def test_ambiguous_reason(self):
        reason = nonstandard_reason(AmbiguousValueExpression)
        assert (
            reason == "Parse-time ambiguity: expression type undetermined until semantic analysis"
        )

    def test_abs_reason(self):
        reason = nonstandard_reason(ArithmeticAbsoluteValueFunction)
        assert reason == "Parse-time ambiguity: ABS() could be numeric or duration"

    def test_factor_reason(self):
        assert nonstandard_reason(ArithmeticFactor) == (
            "Parse convenience: not a concept from the GQL spec"
        )

    def test_term_reason(self):
        assert nonstandard_reason(ArithmeticTerm) == (
            "Parse convenience: not a concept from the GQL spec"
        )

    def test_standard_class_returns_none(self):
        assert nonstandard_reason(GqlProgram) is None

    def test_standard_instance_returns_none(self):
        assert nonstandard_reason(Identifier(name="x")) is None


class TestDecoratorValidation:
    """Test that the decorator validates its inputs."""

    def test_empty_reason_raises_value_error(self):
        with pytest.raises(ValueError, match="non-empty reason string"):
            nonstandard("")

    def test_non_string_reason_raises_value_error(self):
        with pytest.raises(ValueError, match="non-empty reason string"):
            nonstandard(123)

    def test_non_expression_class_raises_type_error(self):
        with pytest.raises(TypeError, match="Expression subclasses"):

            @nonstandard("test reason")
            class NotAnExpression:
                pass

    def test_decorating_plain_function_raises_type_error(self):
        with pytest.raises(TypeError, match="Expression subclasses"):

            @nonstandard("test reason")
            def some_function():
                pass
