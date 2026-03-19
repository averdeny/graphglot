"""Generator module for GraphGlot - converts AST expressions to GQL strings."""

from __future__ import annotations

import sys
import typing as t

from graphglot.ast.base import Expression
from graphglot.generator.fragment import Fragment, braces, brackets, join, parens, seq
from graphglot.generator.generators import DEFAULT_GENERATORS
from graphglot.generator.registry import GeneratorKey

if t.TYPE_CHECKING:
    from graphglot.dialect.base import Dialect


class Generator:
    """Converts AST expressions to GQL strings.

    The Generator class maintains a registry of generator functions that handle
    specific AST expression types. It dispatches to the appropriate generator
    based on the expression's type.

    Attributes:
        GENERATORS: Class-level registry mapping AST types to generator functions.
    """

    GENERATORS: t.ClassVar[dict[GeneratorKey, GeneratorFunc]] = DEFAULT_GENERATORS

    def __init__(self, dialect: Dialect | None = None, **opts: t.Any) -> None:
        """Initialize the generator.

        Args:
            dialect: Optional dialect for keyword selection.
            **opts: Additional generation options.
        """
        self.dialect = dialect
        self.opts = opts
        self.pretty = opts.get("pretty", False)
        self._indent = 0

    def sep(self, sep: str = " ") -> str:
        """Clause separator: newline in pretty mode, ``sep`` in compact mode."""
        return "\n" if self.pretty else sep

    _MIN_RECURSION_LIMIT = 5000

    def generate(self, expression: Expression, copy: bool = False) -> str:
        """Generate GQL string from an AST expression.

        Args:
            expression: The AST expression to convert.
            copy: If True, operate on a copy of the expression.

        Returns:
            The generated GQL string.
        """
        old_limit = sys.getrecursionlimit()
        if old_limit < self._MIN_RECURSION_LIMIT:
            sys.setrecursionlimit(self._MIN_RECURSION_LIMIT)

        try:
            if copy:
                expression = expression.deep_copy()
            fragment = self.dispatch(expression)
            return fragment.render() if fragment else ""
        finally:
            sys.setrecursionlimit(old_limit)

    def dispatch(self, expr: Expression | None) -> Fragment:
        """Route an expression to its appropriate generator function.

        Args:
            expr: The expression to generate GQL for.

        Returns:
            A Fragment containing the generated GQL.

        Raises:
            NotImplementedError: If no generator is registered for the expression type.
        """
        if expr is None:
            return Fragment.empty()

        # Look up the generator for this expression type
        expr_type = type(expr)
        generator_func = self.GENERATORS.get(expr_type)

        if generator_func is None:
            # Try to find a generator for a parent class
            for base_type in expr_type.__mro__:
                if base_type in self.GENERATORS:
                    generator_func = self.GENERATORS[base_type]
                    break

        if generator_func is None:
            raise NotImplementedError(
                f"No generator registered for {expr_type.__name__}. "
                f"Add a @generates decorator to a generator function."
            )

        return generator_func(self, expr)

    def get_generator(self, expr_type: GeneratorKey) -> t.Callable[[Expression], Fragment]:
        """Get a bound generator function for an expression type.

        Args:
            expr_type: The expression type to get a generator for.

        Returns:
            A callable that generates GQL for expressions of the given type.
        """
        generator_func = self.GENERATORS.get(expr_type)
        if generator_func is None:
            name = getattr(expr_type, "__name__", str(expr_type))
            raise NotImplementedError(f"No generator registered for {name}")
        return lambda expr: generator_func(self, expr)

    # Helper methods for building fragments

    def seq(self, *parts: str | Fragment | None, sep: str = " ") -> Fragment:
        """Create a space-separated sequence of parts.

        Args:
            *parts: Parts to combine.
            sep: Separator between parts (default: space).

        Returns:
            Fragment with combined parts.
        """
        return seq(*parts, sep=sep)

    def join(self, items: t.Iterable[str | Fragment | None], sep: str = ", ") -> Fragment:
        """Join items with a separator.

        Args:
            items: Items to join.
            sep: Separator between items (default: comma-space).

        Returns:
            Fragment with joined items.
        """
        return join(items, sep=sep)

    def parens(self, content: str | Fragment | None) -> Fragment:
        """Wrap content in parentheses.

        Args:
            content: Content to wrap.

        Returns:
            Fragment wrapped in parentheses.
        """
        return parens(content)

    def brackets(self, content: str | Fragment | None) -> Fragment:
        """Wrap content in square brackets.

        Args:
            content: Content to wrap.

        Returns:
            Fragment wrapped in brackets.
        """
        return brackets(content)

    def braces(self, content: str | Fragment | None) -> Fragment:
        """Wrap content in curly braces.

        In pretty mode, block content (containing newlines) is indented by
        2 spaces.  Inline braces (maps, properties, quantifiers) pass through
        unchanged because they never contain newlines.

        Args:
            content: Content to wrap.

        Returns:
            Fragment wrapped in braces.
        """
        if not self.pretty:
            return braces(content)
        text = str(content) if content is not None else ""
        if not text or "\n" not in text:
            return braces(content)
        indent = "  "
        indented = text.replace("\n", f"\n{indent}")
        return Fragment(f"{{\n{indent}{indented}\n}}")

    def keyword(self, kw: str) -> str:
        """Return a keyword, possibly transformed by dialect.

        Checks the dialect's KEYWORD_OVERRIDES dict to allow dialects to
        customize keyword output (e.g., Neo4j uses SKIP instead of OFFSET).

        Args:
            kw: The keyword to return (e.g., "OFFSET", "MATCH").

        Returns:
            The dialect-appropriate keyword string (uppercase).
        """
        # Check dialect overrides first
        if self.dialect:
            overrides = getattr(self.dialect, "KEYWORD_OVERRIDES", None)
            if overrides and kw.upper() in overrides:
                return overrides[kw.upper()]
        # Default: return uppercase keyword
        return kw.upper()

    def dispatch_list(self, items: t.Sequence[Expression] | None, sep: str = ", ") -> Fragment:
        """Dispatch and join a list of expressions.

        Args:
            items: List of expressions to generate.
            sep: Separator between items.

        Returns:
            Fragment with joined generated items.
        """
        if not items:
            return Fragment.empty()
        return self.join([self.dispatch(item) for item in items], sep=sep)


GeneratorFunc = t.Callable[[Generator, Expression], Fragment]


# ---------------------------------------------------------------------------
# Func generator helpers
# ---------------------------------------------------------------------------


def rename_func(name: str) -> GeneratorFunc:
    """Return a generator that emits ``name(args)`` for any Func node."""

    def _generate(gen: Generator, expr: Expression) -> Fragment:
        args_list = getattr(expr, "arguments", None)
        if args_list:
            args = gen.join([gen.dispatch(a) for a in args_list], sep=", ")
            return gen.seq(f"{name}(", args, ")", sep="")
        return Fragment(f"{name}()")

    return _generate


def func_generators(
    functions: dict[str, type],
) -> dict[type, GeneratorFunc]:
    """Create per-subclass generators from a ``FUNCTIONS`` dict.

    Each entry maps a Func subclass to a generator that emits
    ``NAME(args)`` using the FUNCTIONS key as the output name.
    """
    result: dict[type, GeneratorFunc] = {}
    for name, cls in functions.items():
        if cls not in result:
            result[cls] = rename_func(name)
    return result
