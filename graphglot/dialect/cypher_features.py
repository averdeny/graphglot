"""Cypher extension feature definitions.

Features use the ``CY:`` prefix to distinguish them from GQL standard features.
They are registered in :data:`CYPHER_FEATURES` and merged into the global
:func:`get_feature` lookup via :mod:`graphglot.features`.
"""

from __future__ import annotations

from graphglot import features as F
from graphglot.features import Feature

# =============================================================================
# Cypher extension features (shared across Cypher-compatible databases)
# =============================================================================

CYPHER_FEATURES: dict[str, Feature] = {
    f.id: f
    for f in [
        F.CY_CL01,
        F.CY_CL02,
        F.CY_CL04,
        F.CY_CL05,
        F.CY_EX01,
        F.CY_EX02,
        F.CY_OP01,
        F.CY_OP02,
        F.CY_OP03,
        F.CY_OP04,
        F.CY_FN01,
        F.CY_FN04,
        F.CY_QP01,
        F.CY_TF01,
        F.CY_TF02,
        F.CY_DD01,
        F.CY_DD02,
    ]
}

ALL_CYPHER_FEATURES: set[Feature] = set(CYPHER_FEATURES.values())
