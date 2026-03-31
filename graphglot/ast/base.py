from __future__ import annotations

import copy
import typing as t

from collections import deque

from graphglot.features import Feature, get_feature

if t.TYPE_CHECKING:
    from graphglot.dialect.base import DialectType
    from graphglot.lexer.token import Token as _Token
    from graphglot.typing.types import GqlType

_SENTINEL = object()
_E = t.TypeVar("_E", bound="Expression")


# ---------------------------------------------------------------------------
# Shims: drop-in replacements for pydantic's Field and model_validator
# ---------------------------------------------------------------------------


class _FieldInfo:
    """Stores default/constraints for an Expression field."""

    __slots__ = ("default", "default_factory", "ge", "min_length")

    def __init__(
        self,
        default: t.Any = _SENTINEL,
        *,
        ge: int | float | None = None,
        min_length: int | None = None,
        default_factory: t.Callable | None = None,
    ):
        self.default = default
        self.default_factory = default_factory
        self.ge = ge
        self.min_length = min_length


def field(
    default: t.Any = _SENTINEL,
    *,
    ge: int | float | None = None,
    min_length: int | None = None,
    default_factory: t.Callable | None = None,
) -> t.Any:
    """Declare field constraints (shim for pydantic.Field)."""
    return _FieldInfo(
        default=default, ge=ge, min_length=min_length, default_factory=default_factory
    )


def model_validator(*, mode: str = "after"):
    """Mark a method as a post-init validator (shim for pydantic.model_validator)."""

    def decorator(fn):
        fn.__is_post_init__ = True
        return fn

    return decorator


# ---------------------------------------------------------------------------
# Introspection helpers used by __init_subclass__
# ---------------------------------------------------------------------------


def _is_classvar(annotation_str: str) -> bool:
    """Check whether a stringified annotation is ClassVar[...]."""
    # With `from __future__ import annotations`, ClassVar annotations are
    # literally "ClassVar[...]" or "ClassVar".  Guard against types whose
    # name merely *contains* "ClassVar" (e.g. "MyClassVarHelper").
    s = annotation_str.strip()
    return s == "ClassVar" or s.startswith("ClassVar[")


def _annotation_allows_none(annotation_str: str) -> bool:
    """Check whether a stringified annotation includes None as a union member.

    With ``from __future__ import annotations`` the format is ``X | None``
    or ``X | Y | None``.  A plain substring check would false-positive on
    type names containing "None" (e.g. "NoneHandler"); split on ``|`` instead.
    """
    return any(part.strip() == "None" for part in annotation_str.split("|"))


def _collect_fields(cls) -> tuple[tuple[str, ...], dict[str, _FieldInfo], dict[str, t.Any]]:
    """Walk the MRO and collect declared AST field names, constraints, and defaults.

    Returns (field_names, {name: Field}, {name: default_value}).
    """
    seen: dict[str, None] = {}  # ordered set
    constraints: dict[str, _FieldInfo] = {}
    defaults: dict[str, t.Any] = {}

    for klass in reversed(cls.__mro__):
        if klass is object or klass is Expression:
            continue
        for name, ann in klass.__dict__.get("__annotations__", {}).items():
            if name.startswith("_") or _is_classvar(str(ann)):
                continue
            seen[name] = None

            val = klass.__dict__.get(name, _SENTINEL)
            if isinstance(val, _FieldInfo):
                constraints[name] = val
                # Precompute the Field's static default (not factory — that must run each time)
                if val.default is not _SENTINEL:
                    defaults[name] = val.default
            elif val is not _SENTINEL:
                # Explicit class-level default (e.g. `field: X | None = None`)
                defaults[name] = val
            elif name not in defaults and _annotation_allows_none(str(ann)):
                # Implicit None default from `X | None` annotation
                defaults[name] = None

    return tuple(seen), constraints, defaults


def _collect_validators(cls) -> tuple[t.Callable, ...]:
    """Collect methods marked __is_post_init__ across MRO (parent-first)."""
    seen_names: set[str] = set()
    validators: list[t.Callable] = []
    for klass in reversed(cls.__mro__):
        if klass is object:
            continue
        for name, val in klass.__dict__.items():
            if name not in seen_names and getattr(val, "__is_post_init__", False):
                seen_names.add(name)
                validators.append(val)
    return tuple(validators)


# ---------------------------------------------------------------------------
# Macro helper
# ---------------------------------------------------------------------------


def _has_macro(data: dict) -> bool:
    """Check if any value in data is a macro type."""
    for v in data.values():
        if getattr(type(v), "__is_macro__", False):
            return True
        if isinstance(v, list):
            for item in v:
                if getattr(type(item), "__is_macro__", False):
                    return True
    return False


# ---------------------------------------------------------------------------
# Expression base class
# ---------------------------------------------------------------------------


class Expression:
    """Base class for all expressions in the AST."""

    __ast_field_names__: t.ClassVar[tuple[str, ...]] = ()
    __field_constraints__: t.ClassVar[dict[str, _FieldInfo]] = {}
    __field_defaults__: t.ClassVar[dict[str, t.Any]] = {}
    __post_init_validators__: t.ClassVar[tuple[t.Callable, ...]] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.__ast_field_names__, cls.__field_constraints__, cls.__field_defaults__ = (
            _collect_fields(cls)
        )
        cls.__post_init_validators__ = _collect_validators(cls)

    # -- Private attribute defaults ------------------------------------------

    _required_features: set[Feature]
    _parent: Expression | None
    _arg_key: str | None
    _index: int | None
    _resolved_type: GqlType | None
    _start_token: _Token | None
    _end_token: _Token | None

    def _init_private(self):
        self._required_features = set()
        self._parent = None
        self._arg_key = None
        self._index = None
        self._resolved_type = None
        self._start_token = None
        self._end_token = None

    # -- Construction --------------------------------------------------------

    def __init__(self, **kwargs):
        self._init_private()

        macro_bypass = not getattr(self.__class__, "__is_macro__", False) and _has_macro(kwargs)
        field_defaults = self.__class__.__field_defaults__
        field_constraints = self.__class__.__field_constraints__

        # Set fields from kwargs, applying precomputed defaults
        for name in self.__ast_field_names__:
            if name in kwargs:
                self.__dict__[name] = kwargs[name]
            elif name in field_defaults:
                # Static default (including implicit None from `X | None`)
                self.__dict__[name] = field_defaults[name]
            else:
                # Field with default_factory — must call each time
                field = field_constraints.get(name)
                if field is not None and field.default_factory is not None:
                    self.__dict__[name] = field.default_factory()

        if not macro_bypass:
            # Validate Field constraints
            for name, field in field_constraints.items():
                val = self.__dict__.get(name)
                if val is None:
                    continue
                if field.ge is not None and val < field.ge:
                    raise ValueError(
                        f"Input should be greater than or equal to {field.ge} [input_value={val!r}]"
                    )
                if field.min_length is not None and len(val) < field.min_length:
                    raise ValueError(
                        f"List should have at least {field.min_length} items after validation, "
                        f"not {len(val)} [input_value={val!r}]"
                    )
            # Run post-init validators
            for validator in self.__class__.__post_init_validators__:
                validator(self)

        # Set parent links
        for k, v in kwargs.items():
            self._set_parent(k, v)

    @classmethod
    def _construct(cls, **kwargs) -> t.Self:
        """Create an instance without validation (replaces model_construct)."""
        obj = object.__new__(cls)
        obj._init_private()
        field_defaults = cls.__field_defaults__
        field_constraints = cls.__field_constraints__
        for name in cls.__ast_field_names__:
            if name in kwargs:
                obj.__dict__[name] = kwargs[name]
            elif name in field_defaults:
                obj.__dict__[name] = field_defaults[name]
            else:
                field = field_constraints.get(name)
                if field is not None and field.default_factory is not None:
                    obj.__dict__[name] = field.default_factory()
            obj._set_parent(name, obj.__dict__.get(name))
        return obj

    @property
    def source_span(self) -> tuple[int, int] | None:
        """Character offset range [start, end) in original query, or None."""
        if self._start_token and self._end_token:
            return (self._start_token.start, self._end_token.end + 1)
        return None

    # -- Feature tracking ----------------------------------------------------

    def require_feature(self, feature: Feature | str) -> None:
        """Require a feature to be enabled for the expression."""
        if isinstance(feature, str):
            feature = get_feature(feature)
        self._required_features.add(feature)

    def get_required_features(self) -> set[Feature]:
        """Get the required features for the expression and all its children."""
        features = set(self._required_features)
        for child in self.children():
            features.update(child.get_required_features())
        return features

    # -- Parent tracking -----------------------------------------------------

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

    # -- Field introspection -------------------------------------------------

    @property
    def ast_fields(self) -> tuple[str, ...]:
        return self.__ast_field_names__

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
        self.__dict__[key] = value
        self._set_parent(key, value)

    def append(self, key: str, value: Expression) -> None:
        """Append a value to a list and update parent tracking."""
        current = getattr(self, key, None)
        if not isinstance(current, list):
            raise TypeError(f"'{key}' is not a list attribute.")
        current.append(value)
        self._set_parent(key, value)
        value._index = len(current) - 1

    # -- Traversal -----------------------------------------------------------

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
        for name in self.__ast_field_names__:
            value = getattr(self, name, None)
            if isinstance(value, Expression):
                yield value
            elif isinstance(value, list):
                yield from (v for v in value if isinstance(v, Expression))

    def find_first(self, type_: type[_E], bfs: bool = True) -> _E | None:
        """Find the first child of a specific type in the expression tree."""
        return next(self.find_all(type_, bfs), None)

    def find_all(self, type_: type[_E], bfs: bool = True) -> t.Iterator[_E]:
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
        c = copy.deepcopy(self)
        c._parent = None
        c._arg_key = None
        c._index = None
        for node in c.dfs():
            for key in node.__ast_field_names__:
                node._set_parent(key, getattr(node, key, None))
        return c

    # -- Representation & equality -------------------------------------------

    def __repr__(self):
        """Return a string representation of the expression."""
        fields = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items() if not k.startswith("_"))
        return f"{self.__class__.__name__}({fields})"

    def _macro_aware_dump(self) -> dict[str, t.Any]:
        """Recursively dump ast_fields to a dict."""
        result: dict[str, t.Any] = {}
        for key in self.__ast_field_names__:
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

    def __hash__(self):
        return id(self)

    def to_gql(self, dialect: DialectType = None, **opts: t.Any) -> str:
        """Convert the expression to a GQL string representation."""
        from graphglot.dialect.base import Dialect

        return Dialect.get_or_raise(dialect).generate(self, **opts)

    def leaves(self, bfs: bool = True, include_self: bool = True) -> t.Iterator[Expression]:
        """Yield all leaf nodes in this subtree."""
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
    """Check if an AST class or instance is marked as non-standard."""
    cls = type(cls_or_instance) if isinstance(cls_or_instance, Expression) else cls_or_instance
    if hasattr(cls, "__nonstandard__"):
        return True
    outer = _enclosing_class(cls)
    return outer is not None and hasattr(outer, "__nonstandard__")


def nonstandard_reason(cls_or_instance) -> str | None:
    """Return the non-standard reason string, or None for standard classes."""
    cls = type(cls_or_instance) if isinstance(cls_or_instance, Expression) else cls_or_instance
    reason = getattr(cls, "__nonstandard__", None)
    if reason is not None:
        return reason
    outer = _enclosing_class(cls)
    if outer is not None:
        return getattr(outer, "__nonstandard__", None)
    return None
