"""Generator functions package - exposes DEFAULT_GENERATORS registry."""

from __future__ import annotations

# Import modules with @generates decorators to populate the registry
from graphglot.generator.generators import (  # noqa: F401
    clauses,
    commands,
    core,
    cypher_compat,
    expressions,
    literals,
    macros,
    patterns,
    predicates,
    statements,
    types,
)
from graphglot.generator.registry import get_registry

DEFAULT_GENERATORS = get_registry()

__all__ = ["DEFAULT_GENERATORS"]
