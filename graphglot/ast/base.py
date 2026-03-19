from __future__ import annotations

import typing as t

from collections import deque
from functools import cached_property

from pydantic import BaseModel, ConfigDict, PrivateAttr

from graphglot.features import Feature, get_feature

if t.TYPE_CHECKING:
    from graphglot.dialect.base import DialectType
    from graphglot.lexer.token import Token as _Token
    from graphglot.typing.types import GqlType


def _has_macro(data: dict) -> bool:
    """Check if any value in data is a macro type (no imports needed)."""
    for v in data.values():
        if getattr(type(v), "__is_macro__", False):
            return True
        if isinstance(v, list):
            for item in v:
                if getattr(type(item), "__is_macro__", False):
                    return True
    return False


class Expression(BaseModel):
    """Base class for all expressions in the AST."""

    _required_features: set[Feature] = PrivateAttr(default_factory=set)

    # Private metadata for AST tracking
    _parent: Expression | None = PrivateAttr(default=None)
    _arg_key: str | None = PrivateAttr(default=None)
    _index: int | None = PrivateAttr(default=None)

    # Type annotation (set by TypeAnnotator)
    _resolved_type: GqlType | None = PrivateAttr(default=None)

    # Source span tracking (set by @parses wrapper)
    _start_token: _Token | None = PrivateAttr(default=None)
    _end_token: _Token | None = PrivateAttr(default=None)

    @property
    def source_span(self) -> tuple[int, int] | None:
        """Character offset range [start, end) in original query, or None."""
        if self._start_token and self._end_token:
            return (self._start_token.start, self._end_token.end + 1)
        return None

    model_config = ConfigDict(
        arbitrary_types_allowed=True, extra="forbid", validate_assignment=True
    )

    def __init__(self, **data):
        if not getattr(self.__class__, "__is_macro__", False) and _has_macro(data):
            constructed = self.__class__.model_construct(**data)
            object.__setattr__(self, "__dict__", constructed.__dict__)
            object.__setattr__(self, "__pydantic_fields_set__", constructed.__pydantic_fields_set__)
            object.__setattr__(
                self,
                "__pydantic_extra__",
                getattr(constructed, "__pydantic_extra__", None),
            )
            object.__setattr__(self, "__pydantic_private__", constructed.__pydantic_private__)
        else:
            super().__init__(**data)
        for k, v in data.items():
            self._set_parent(k, v)

    def require_feature(self, feature: Feature | str) -> None:
        """Require a feature to be enabled for the expression."""
        if isinstance(feature, str):
            feature = get_feature(feature)
        self._required_features.add(feature)

    def get_required_features(self) -> set[Feature]:
        """Get the required features for the expression and all its children."""
        features = set(self._required_features)
        # Recursively collect features from all child expressions
        for child in self.children():
            features.update(child.get_required_features())
        return features

    def _set_parent(self, key: str, value: t.Any) -> None:
        """Set up parent-child relationships for expressions in the AST."""

        if isinstance(value, Expression):
            value._parent = self
            value._arg_key = key
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, Expression):
                    item._parent = self
                    item._arg_key = key
                    item._index = i

    @cached_property
    def ast_fields(self) -> list[str]:
        return [name for name in self.__annotations__ if not name.startswith("_")]

    def set(self, key: str, value: t.Any, index: int | None = None) -> None:
        """Set an attribute and update parent-child links.

        If index is given and the field is a list, replace the element at that
        position. If value is None with an index, remove the element.
        """
        if index is not None:
            current = getattr(self, key, None)
            if isinstance(current, list):
                if value is None:
                    current.pop(index)
                    for i, item in enumerate(current[index:], start=index):
                        if isinstance(item, Expression):
                            item._index = i
                    return
                current[index] = value
                self._set_parent(key, value)
                if isinstance(value, Expression):
                    value._index = index
                return
        current_val = getattr(self, key, None)
        if getattr(type(value), "__is_macro__", False) or getattr(
            type(current_val), "__is_macro__", False
        ):
            # Bypass Pydantic validation when placing a macro OR replacing one
            self.__dict__[key] = value
        else:
            setattr(self, key, value)
        self._set_parent(key, value)

    def append(self, key: str, value: Expression) -> None:
        """Append a value to a list and update parent tracking."""

        current = getattr(self, key, None)
        if not isinstance(current, list):
            raise TypeError(f"'{key}' is not a list attribute.")
        current.append(value)
        self._set_parent(key, value)
        # Set the index for the newly appended value
        value._index = len(current) - 1

    def dfs(self, prune: t.Callable[[Expression], bool] | None = None) -> t.Iterator[Expression]:
        """Depth-first search (DFS) traversal of the expression tree.

        Args:
            prune: If provided, skip children of nodes where prune(node) is True.
        """
        stack = [self]
        while stack:
            node = stack.pop()
            yield node
            if prune and prune(node):
                continue
            stack.extend(reversed(list(node.children())))

    def transform(
        self,
        fn: t.Callable[..., Expression | None],
        *args: t.Any,
        copy: bool = True,
        **kwargs: t.Any,
    ) -> Expression:
        """Pre-order tree transformation.

        fn(node, *args, **kwargs) returns a replacement node, or None to remove.
        """
        root = None
        # Use a mutable container so the lambda captures the container, not the value
        state: list[Expression | None] = [None]

        for node in (self.deep_copy() if copy else self).dfs(prune=lambda n: n is not state[0]):
            parent, arg_key, index = node._parent, node._arg_key, node._index
            new_node = fn(node, *args, **kwargs)
            state[0] = new_node

            if not root:
                root = new_node
            elif parent and arg_key and new_node is not node:
                parent.set(arg_key, new_node, index)

        return root if root is not None else self

    def bfs(self) -> t.Iterator[Expression]:
        """Breadth-first search (BFS) traversal of the expression tree."""

        queue = deque([self])
        while queue:
            node = queue.popleft()
            yield node
            queue.extend(node.children())

    def children(self) -> t.Iterator[Expression]:
        """Yield all child expressions."""

        for name in self.ast_fields:
            value = getattr(self, name, None)
            if isinstance(value, Expression):
                yield value
            elif isinstance(value, list):
                yield from (v for v in value if isinstance(v, Expression))

    def find_first(self, type_: type[Expression], bfs: bool = True) -> Expression | None:
        """Find the first child of a specific type in the expression tree."""
        return next(self.find_all(type_, bfs), None)

    def find_all(self, type_: type[Expression], bfs: bool = True) -> t.Iterator[Expression]:
        """Yield all expressions of the specified type in the AST."""
        traversal = self.bfs() if bfs else self.dfs()
        yield from (e for e in traversal if isinstance(e, type_))

    def is_leaf(self) -> bool:
        """Check if the expression is a leaf node (has no children)."""

        return not any(True for _ in self.children())

    def deep_copy(self) -> Expression:
        """Create a deep copy of the expression as a standalone tree.

        The returned root has ``_parent=None`` even if called on a subtree node.
        """
        copy = self.model_copy(deep=True)
        # Pydantic's __deepcopy__ adds self to memo AFTER returning, so
        # children's _parent back-references create ghost copies of the
        # parent.  Rebuild all parent links from the copied tree structure.
        copy._parent = None
        copy._arg_key = None
        copy._index = None
        for node in copy.dfs():
            for key in node.ast_fields:
                node._set_parent(key, getattr(node, key, None))
        return copy

    def __repr__(self):
        """Return a string representation of the expression."""

        fields = ", ".join(
            f"{k}={v!r}"
            for k, v in self.__dict__.items()
            if not (k.startswith("_") or k == "ast_fields")
        )
        return f"{self.__class__.__name__}({fields})"

    def _macro_aware_dump(self) -> dict[str, t.Any]:
        """Like model_dump(), but correctly serializes macro-bypassed fields.

        Pydantic's model_dump() returns {} for fields set via model_construct
        because the serialization schema doesn't know the runtime type.
        This method walks ast_fields and recursively dumps Expression children.
        """
        result: dict[str, t.Any] = {}
        for key in self.ast_fields:
            value = getattr(self, key, None)
            if isinstance(value, Expression):
                result[key] = value._macro_aware_dump()
            elif isinstance(value, list):
                result[key] = [
                    item._macro_aware_dump() if isinstance(item, Expression) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result

    def __eq__(self, other):
        """Check equality of two expressions based on their attributes."""
        if not isinstance(other, Expression):
            return NotImplemented
        return self._macro_aware_dump() == other._macro_aware_dump()

    def to_gql(self, dialect: DialectType = None, **opts: t.Any) -> str:
        """Convert the expression to a GQL string representation.

        Args:
            dialect: The dialect to use for GQL generation. If None, the default dialect is used.
            **opts: Additional options for GQL generation.

        Returns:
            A string representing the GQL expression.
        """
        from graphglot.dialect.base import Dialect

        return Dialect.get_or_raise(dialect).generate(self, **opts)

    def leaves(self, bfs: bool = True, include_self: bool = True) -> t.Iterator[Expression]:
        """
        Yield all leaf nodes (nodes with no Expression children) in this subtree.

        Args:
            bfs: If True, traverse breadth-first; otherwise depth-first.
            include_self: If False, don't consider `self` as a candidate leaf.
        """
        traversal = self.bfs() if bfs else self.dfs()

        for node in traversal:
            if not include_self and node is self:
                continue
            if node.is_leaf():
                yield node

    def leaf_list(self, bfs: bool = True, include_self: bool = True) -> list[Expression]:
        """Convenience wrapper returning a list instead of an iterator."""
        return list(self.leaves(bfs=bfs, include_self=include_self))


def nonstandard(reason: str):
    """Mark an Expression subclass as not from the ISO/IEC 39075:2024 GQL standard."""
    if not reason or not isinstance(reason, str):
        raise ValueError("nonstandard() requires a non-empty reason string")

    def decorator(cls):
        if not (isinstance(cls, type) and issubclass(cls, Expression)):
            raise TypeError(f"@nonstandard can only decorate Expression subclasses, got {cls}")
        cls.__nonstandard__ = reason
        return cls

    return decorator


def _enclosing_class(cls) -> type | None:
    """Return the enclosing class for a nested class, or None."""
    import sys

    qualname = getattr(cls, "__qualname__", "")
    if "." not in qualname:
        return None
    module = sys.modules.get(getattr(cls, "__module__", ""))
    if not module:
        return None
    obj: object = module
    for part in qualname.split(".")[:-1]:
        obj = getattr(obj, part, None)
        if obj is None:
            return None
    return obj if isinstance(obj, type) else None


def is_nonstandard(cls_or_instance) -> bool:
    """Check if an AST class or instance is marked as non-standard.

    Also returns True for inner classes of non-standard classes.
    """
    cls = type(cls_or_instance) if isinstance(cls_or_instance, Expression) else cls_or_instance
    if hasattr(cls, "__nonstandard__"):
        return True
    outer = _enclosing_class(cls)
    return outer is not None and hasattr(outer, "__nonstandard__")


def nonstandard_reason(cls_or_instance) -> str | None:
    """Return the non-standard reason string, or None for standard classes.

    For inner classes, returns the enclosing class's reason.
    """
    cls = type(cls_or_instance) if isinstance(cls_or_instance, Expression) else cls_or_instance
    reason = getattr(cls, "__nonstandard__", None)
    if reason is not None:
        return reason
    outer = _enclosing_class(cls)
    if outer is not None:
        return getattr(outer, "__nonstandard__", None)
    return None
