"""Abstract base for pure-GQL dialects."""

from __future__ import annotations

import typing as t

from graphglot.dialect.base import Dialect
from graphglot.transformations import with_to_next


class GqlDialect(Dialect):
    """Abstract base for dialects that emit pure GQL syntax (``NEXT``, not ``WITH``).

    Vendors like :class:`CoreGQL` and :class:`FullGQL` inherit from this class.
    Prepends ``with_to_next`` (lowers ``CypherWithStatement`` to standard
    ``NEXT`` chains) ahead of the base class's ``resolve_ambiguous`` pass.

    **Not** registered in the :class:`Dialects` enum -- pick a concrete subclass.
    """

    WRITE_TRANSFORMATIONS: t.ClassVar[list] = [with_to_next, *Dialect.WRITE_TRANSFORMATIONS]
