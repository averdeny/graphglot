"""Core GQL dialect — mandatory extension features only, no optional features."""

from __future__ import annotations

import typing as t

from graphglot import features as F
from graphglot.dialect.gql import GqlDialect
from graphglot.features import ALL_EXTENSION_FEATURES, Feature

_COREGQL_UNSUPPORTED: set[Feature] = {
    F.GG_FN01,
}


class CoreGQL(GqlDialect):
    """GQL dialect with only mandatory (extension) features — no optional features."""

    SUPPORTED_FEATURES: t.ClassVar[set[Feature]] = ALL_EXTENSION_FEATURES - _COREGQL_UNSUPPORTED
