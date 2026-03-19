"""Anti-drift tests for typed feature constants."""

from __future__ import annotations

import re
import unittest

from pathlib import Path

from graphglot import features as F
from graphglot.features import ALL_FEATURE_MAP, Feature


class TestFeatureConstants(unittest.TestCase):
    """Ensure features.py stays in sync with the unified registry."""

    def test_all_features_are_constants(self):
        """Every Feature in ALL_FEATURE_MAP has a matching constant in features.py."""
        constants = {v for v in vars(F).values() if isinstance(v, Feature)}
        self.assertEqual(constants, set(ALL_FEATURE_MAP.values()))

    def test_constant_names_match_ids(self):
        """Each constant's name matches its feature ID (: → _)."""
        for name, val in vars(F).items():
            if isinstance(val, Feature):
                expected_name = val.id.replace(":", "_")
                self.assertEqual(name, expected_name, f"Constant {name} has id {val.id}")

    def test_no_string_feature_ids_in_source(self):
        """No require_feature("..") or get_feature("..") in graphglot/ source.

        Only ast/base.py is exempt — it keeps the Feature | str fallback
        signature for the require_feature method.
        """
        src = Path(__file__).resolve().parents[3] / "graphglot"
        pattern = re.compile(r'(?:require_feature|get_feature)\("[^"]+"\)')
        exempt = {(src / "ast" / "base.py").resolve()}
        violations: list[str] = []
        for py in src.rglob("*.py"):
            if py.resolve() in exempt:
                continue
            text = py.read_text()
            for m in pattern.finditer(text):
                violations.append(f"{py.relative_to(src)}:{m.group()}")
        self.assertEqual(violations, [], "String feature IDs found:\n" + "\n".join(violations))

    def test_no_duplicate_ids(self):
        """No two constants share the same feature ID."""
        seen: dict[str, str] = {}
        for name, val in vars(F).items():
            if isinstance(val, Feature):
                self.assertNotIn(
                    val.id,
                    seen,
                    f"Duplicate ID {val.id}: {name} and {seen.get(val.id)}",
                )
                seen[val.id] = name
