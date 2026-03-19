"""GQL type representation for type inference."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class TypeKind(StrEnum):
    # Boolean
    BOOLEAN = "boolean"
    # String
    STRING = "string"
    BYTE_STRING = "byte_string"
    # Numeric
    INT = "int"
    FLOAT = "float"
    DECIMAL = "decimal"
    NUMERIC = "numeric"  # Unspecified numeric
    # Temporal
    DATE = "date"
    TIME = "time"
    DATETIME = "datetime"
    LOCAL_DATETIME = "local_datetime"
    LOCAL_TIME = "local_time"
    DURATION = "duration"
    # Special values
    NULL = "null"
    EMPTY = "empty"
    # Graph elements
    NODE = "node"
    EDGE = "edge"
    PATH = "path"
    # Containers
    GRAPH = "graph"
    BINDING_TABLE = "binding_table"
    LIST = "list"
    RECORD = "record"
    # Catch-all
    ANY = "any"
    PROPERTY_VALUE = "property_value"
    # Unknown / error
    UNKNOWN = "unknown"
    ERROR = "error"


@dataclass(frozen=True)
class GqlType:
    """Internal type representation for GQL type inference.

    Simpler than the AST's ~130 ValueType classes. Supports UNKNOWN,
    union types, and easy comparison.
    """

    kind: TypeKind
    nullable: bool = True
    element_type: GqlType | None = None  # For LIST<T>
    field_types: tuple[tuple[str, GqlType], ...] | None = None  # For RECORD
    group_of: GqlType | None = None  # For GROUP<T> (post-GROUP BY)
    union_members: tuple[GqlType, ...] | None = None  # For ambiguous types
    labels: frozenset[str] = field(default_factory=frozenset)  # For NODE/EDGE

    # -- Convenience constructors -------------------------------------------

    @classmethod
    def unknown(cls) -> GqlType:
        return cls(kind=TypeKind.UNKNOWN)

    @classmethod
    def error(cls) -> GqlType:
        return cls(kind=TypeKind.ERROR, nullable=False)

    @classmethod
    def null(cls) -> GqlType:
        return cls(kind=TypeKind.NULL)

    @classmethod
    def boolean(cls) -> GqlType:
        return cls(kind=TypeKind.BOOLEAN)

    @classmethod
    def string(cls) -> GqlType:
        return cls(kind=TypeKind.STRING)

    @classmethod
    def byte_string(cls) -> GqlType:
        return cls(kind=TypeKind.BYTE_STRING)

    @classmethod
    def integer(cls) -> GqlType:
        return cls(kind=TypeKind.INT)

    @classmethod
    def decimal(cls) -> GqlType:
        return cls(kind=TypeKind.DECIMAL)

    @classmethod
    def float_(cls) -> GqlType:
        return cls(kind=TypeKind.FLOAT)

    @classmethod
    def numeric(cls) -> GqlType:
        return cls(kind=TypeKind.NUMERIC)

    @classmethod
    def date(cls) -> GqlType:
        return cls(kind=TypeKind.DATE)

    @classmethod
    def time(cls) -> GqlType:
        return cls(kind=TypeKind.TIME)

    @classmethod
    def datetime_(cls) -> GqlType:
        return cls(kind=TypeKind.DATETIME)

    @classmethod
    def local_datetime(cls) -> GqlType:
        return cls(kind=TypeKind.LOCAL_DATETIME)

    @classmethod
    def local_time(cls) -> GqlType:
        return cls(kind=TypeKind.LOCAL_TIME)

    @classmethod
    def duration(cls) -> GqlType:
        return cls(kind=TypeKind.DURATION)

    @classmethod
    def node(cls, labels: frozenset[str] | None = None) -> GqlType:
        return cls(kind=TypeKind.NODE, labels=labels or frozenset())

    @classmethod
    def edge(cls, labels: frozenset[str] | None = None) -> GqlType:
        return cls(kind=TypeKind.EDGE, labels=labels or frozenset())

    @classmethod
    def path(cls) -> GqlType:
        return cls(kind=TypeKind.PATH)

    @classmethod
    def graph(cls) -> GqlType:
        return cls(kind=TypeKind.GRAPH)

    @classmethod
    def binding_table(cls) -> GqlType:
        return cls(kind=TypeKind.BINDING_TABLE)

    @classmethod
    def list_(cls, element_type: GqlType | None = None) -> GqlType:
        return cls(kind=TypeKind.LIST, element_type=element_type)

    @classmethod
    def record(cls, field_types: tuple[tuple[str, GqlType], ...] | None = None) -> GqlType:
        return cls(kind=TypeKind.RECORD, field_types=field_types)

    @classmethod
    def any_(cls) -> GqlType:
        return cls(kind=TypeKind.ANY)

    @classmethod
    def union(cls, *members: GqlType) -> GqlType:
        """Create a union type from multiple possible types."""
        # Flatten nested unions
        flat: list[GqlType] = []
        for m in members:
            if m.union_members:
                flat.extend(m.union_members)
            else:
                flat.append(m)
        # Deduplicate
        seen: list[GqlType] = []
        for t in flat:
            if t not in seen:
                seen.append(t)
        if len(seen) == 1:
            return seen[0]
        return cls(kind=TypeKind.UNKNOWN, union_members=tuple(seen))

    # -- Predicates ----------------------------------------------------------

    @property
    def is_unknown(self) -> bool:
        return self.kind == TypeKind.UNKNOWN and self.union_members is None

    @property
    def is_error(self) -> bool:
        return self.kind == TypeKind.ERROR

    @property
    def is_boolean(self) -> bool:
        return self.kind == TypeKind.BOOLEAN

    @property
    def is_numeric(self) -> bool:
        return self.kind in (TypeKind.INT, TypeKind.FLOAT, TypeKind.DECIMAL, TypeKind.NUMERIC)

    @property
    def is_temporal(self) -> bool:
        return self.kind in (
            TypeKind.DATE,
            TypeKind.TIME,
            TypeKind.DATETIME,
            TypeKind.LOCAL_DATETIME,
            TypeKind.LOCAL_TIME,
        )

    @property
    def is_string(self) -> bool:
        return self.kind in (TypeKind.STRING, TypeKind.BYTE_STRING)

    @property
    def is_element(self) -> bool:
        return self.kind in (TypeKind.NODE, TypeKind.EDGE, TypeKind.PATH)

    @property
    def is_union(self) -> bool:
        return self.union_members is not None

    def is_comparable_with(self, other: GqlType) -> bool:
        """True when two types may be compared (``=``, ``<>``, ``<``, etc.).

        Returns True conservatively when either side is UNKNOWN/ANY/NULL.
        """
        # Can't determine — be conservative
        if self.is_unknown or other.is_unknown:
            return True
        if self.is_error or other.is_error:
            return True
        # ANY / NULL are universally comparable
        if self.kind in (TypeKind.ANY, TypeKind.NULL) or other.kind in (
            TypeKind.ANY,
            TypeKind.NULL,
        ):
            return True
        # Same kind is always comparable
        if self.kind == other.kind:
            return True
        # Numeric subtypes are mutually comparable
        if self.is_numeric and other.is_numeric:
            return True
        # Temporal types within the same family are comparable
        if self.is_temporal and other.is_temporal:
            return True
        # String types are mutually comparable
        if self.is_string and other.is_string:
            return True
        # Union types: comparable if any member pair is comparable
        if self.is_union:
            return any(m.is_comparable_with(other) for m in (self.union_members or ()))
        if other.is_union:
            return any(self.is_comparable_with(m) for m in (other.union_members or ()))
        # Otherwise, incompatible
        return False

    def __repr__(self) -> str:
        parts = [self.kind.value]
        if self.element_type:
            parts.append(f"<{self.element_type!r}>")
        if self.labels:
            parts.append(f"({','.join(sorted(self.labels))})")
        if self.group_of:
            parts.append(f"[group_of={self.group_of!r}]")
        if self.union_members:
            members = " | ".join(repr(m) for m in self.union_members)
            return f"({members})"
        if not self.nullable:
            parts.append("!")
        return "".join(parts)
