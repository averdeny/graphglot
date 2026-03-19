"""Full GQL dialect — all GQL features (extension + optional)."""

from __future__ import annotations

import typing as t

from graphglot import features as F
from graphglot.dialect.base import Dialect
from graphglot.features import ALL_FEATURES, Feature

_FULLGQL_UNSUPPORTED: set[Feature] = {
    F.GG_FN01,
}


class FullGQL(Dialect):
    """GQL dialect with all features enabled (extension + optional)."""

    SUPPORTED_FEATURES: t.ClassVar[set[Feature]] = ALL_FEATURES - _FULLGQL_UNSUPPORTED
