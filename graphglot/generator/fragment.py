"""Fragment class for composable GQL output generation."""

from __future__ import annotations

import typing as t


class Fragment:
    """Represents a composable piece of GQL output.

    Fragments can be combined using various methods to build complex GQL strings
    while maintaining proper formatting and spacing.
    """

    __slots__ = ("_parts",)

    def __init__(self, *parts: str | Fragment | None) -> None:
        """Initialize a Fragment with optional parts.

        Args:
            *parts: String literals, other Fragments, or None values to compose.
        """
        self._parts: list[str | Fragment] = [p for p in parts if p is not None and p != ""]

    @classmethod
    def empty(cls) -> Fragment:
        """Create an empty fragment."""
        return cls()

    @classmethod
    def literal(cls, text: str) -> Fragment:
        """Create a fragment from a literal string."""
        return cls(text)

    def seq(self, *parts: str | Fragment | None, sep: str = " ") -> Fragment:
        """Create a new fragment by appending parts with a separator.

        Args:
            *parts: Parts to append.
            sep: Separator between parts (default: space).

        Returns:
            New Fragment with combined parts.
        """
        all_parts = list(self._parts)
        for part in parts:
            if part is not None and part != "":
                all_parts.append(part)
        return Fragment(sep.join(str(p) for p in all_parts) if all_parts else "")

    def append(self, *parts: str | Fragment | None, sep: str = " ") -> Fragment:
        """Append parts to this fragment with a separator.

        Args:
            *parts: Parts to append.
            sep: Separator between parts (default: space).

        Returns:
            New Fragment with appended parts.
        """
        filtered = [p for p in parts if p is not None and p != ""]
        if not filtered:
            return self
        if not self._parts:
            return Fragment(*filtered)
        return Fragment(str(self) + sep + sep.join(str(p) for p in filtered))

    def prepend(self, *parts: str | Fragment | None, sep: str = " ") -> Fragment:
        """Prepend parts to this fragment with a separator.

        Args:
            *parts: Parts to prepend.
            sep: Separator between parts (default: space).

        Returns:
            New Fragment with prepended parts.
        """
        filtered = [p for p in parts if p is not None and p != ""]
        if not filtered:
            return self
        if not self._parts:
            return Fragment(*filtered)
        return Fragment(sep.join(str(p) for p in filtered) + sep + str(self))

    def join(self, sep: str = ", ") -> Fragment:
        """Join all parts with the given separator.

        Args:
            sep: Separator to use between parts.

        Returns:
            New Fragment with joined parts.
        """
        return Fragment(sep.join(str(p) for p in self._parts))

    def parens(self) -> Fragment:
        """Wrap this fragment in parentheses.

        Returns:
            New Fragment wrapped in parentheses.
        """
        content = str(self)
        if not content:
            return Fragment("()")
        return Fragment(f"({content})")

    def brackets(self) -> Fragment:
        """Wrap this fragment in square brackets.

        Returns:
            New Fragment wrapped in brackets.
        """
        content = str(self)
        if not content:
            return Fragment("[]")
        return Fragment(f"[{content}]")

    def braces(self) -> Fragment:
        """Wrap this fragment in curly braces.

        Returns:
            New Fragment wrapped in braces.
        """
        content = str(self)
        if not content:
            return Fragment("{}")
        return Fragment(f"{{{content}}}")

    def __str__(self) -> str:
        """Render this fragment as a string."""
        return " ".join(str(p) for p in self._parts)

    def __repr__(self) -> str:
        return f"Fragment({self._parts!r})"

    def __bool__(self) -> bool:
        """Return True if fragment has non-empty content."""
        return bool(self._parts) and any(str(p) for p in self._parts)

    def __eq__(self, other: t.Any) -> bool:
        if isinstance(other, Fragment):
            return str(self) == str(other)
        if isinstance(other, str):
            return str(self) == other
        return NotImplemented

    def render(self, pretty: bool = False, indent: int = 0) -> str:
        """Render this fragment to a string.

        Args:
            pretty: If True, format with newlines and indentation.
            indent: Base indentation level (used when pretty=True).

        Returns:
            The rendered GQL string.
        """
        # For now, just return the basic string representation
        # Pretty printing can be enhanced later
        return str(self)


def seq(*parts: str | Fragment | None, sep: str = " ") -> Fragment:
    """Create a fragment from parts separated by the given separator.

    Args:
        *parts: Parts to combine.
        sep: Separator between parts (default: space).

    Returns:
        New Fragment with combined parts.
    """
    filtered = [p for p in parts if p is not None and p != ""]
    if not filtered:
        return Fragment.empty()
    return Fragment(sep.join(str(p) for p in filtered))


def join(items: t.Iterable[str | Fragment | None], sep: str = ", ") -> Fragment:
    """Join items with the given separator.

    Args:
        items: Items to join.
        sep: Separator between items (default: comma-space).

    Returns:
        New Fragment with joined items.
    """
    filtered = [p for p in items if p is not None and p != ""]
    if not filtered:
        return Fragment.empty()
    return Fragment(sep.join(str(p) for p in filtered))


def parens(content: str | Fragment | None) -> Fragment:
    """Wrap content in parentheses.

    Args:
        content: Content to wrap.

    Returns:
        New Fragment wrapped in parentheses.
    """
    if content is None or content == "":
        return Fragment("()")
    return Fragment(f"({content})")


def brackets(content: str | Fragment | None) -> Fragment:
    """Wrap content in square brackets.

    Args:
        content: Content to wrap.

    Returns:
        New Fragment wrapped in brackets.
    """
    if content is None or content == "":
        return Fragment("[]")
    return Fragment(f"[{content}]")


def braces(content: str | Fragment | None) -> Fragment:
    """Wrap content in curly braces.

    Args:
        content: Content to wrap.

    Returns:
        New Fragment wrapped in braces.
    """
    if content is None or content == "":
        return Fragment("{}")
    return Fragment(f"{{{content}}}")
