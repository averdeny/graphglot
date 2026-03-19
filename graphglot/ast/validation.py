from __future__ import annotations

import typing as t

from graphglot.error import FeatureError

if t.TYPE_CHECKING:
    from graphglot.ast.base import Expression
    from graphglot.dialect.base import Dialect


def validate_expression_features(
    expression: Expression,
    dialect: Dialect,
    context: str = "operation",
) -> None:
    """Validate that all required features are supported."""
    required_features = expression.get_required_features()
    unsupported = [
        feature for feature in required_features if not dialect.is_feature_supported(feature)
    ]

    if unsupported:
        unsupported.sort(key=lambda f: f.id)
        feature_list = ", ".join(f.id for f in unsupported)
        dialect_name = dialect.__class__.__name__
        if len(unsupported) == 1:
            f = unsupported[0]
            msg = f"Feature {f.id} ({f.description}) not supported by dialect '{dialect_name}'."
        else:
            lines = [f"  {f.id} \u2014 {f.description}" for f in unsupported]
            msg = f"Unsupported feature(s) for dialect '{dialect_name}':\n" + "\n".join(lines)
        raise FeatureError(
            msg,
            feature_id=feature_list,
            expression_type=expression.__class__.__name__,
        )
