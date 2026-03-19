"""Tests for scripts/check_version_consistency.py."""

from __future__ import annotations

import textwrap

from pathlib import Path

import pytest

from scripts.check_version_consistency import (
    check_consistency,
    read_pyproject_version,
    read_uvlock_version,
)


@pytest.fixture()
def tmp_repo(tmp_path: Path) -> Path:
    """Create a minimal repo structure under tmp_path."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        textwrap.dedent("""\
        [project]
        name = "graphglot"
        version = "1.2.3"
        """)
    )
    uvlock = tmp_path / "uv.lock"
    uvlock.write_text(
        textwrap.dedent("""\
        version = 1
        requires-python = ">=3.11"

        [[package]]
        name = "graphglot"
        version = "1.2.3"
        source = { editable = "." }
        """)
    )
    return tmp_path


# ── reader tests ─────────────────────────────────────────────────────────


class TestReadPyprojectVersion:
    def test_reads_version(self, tmp_repo: Path) -> None:
        assert read_pyproject_version(tmp_repo) == "1.2.3"

    def test_missing_file(self, tmp_path: Path) -> None:
        assert read_pyproject_version(tmp_path) is None

    def test_missing_version_field(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")
        assert read_pyproject_version(tmp_path) is None


class TestReadUvlockVersion:
    def test_reads_version(self, tmp_repo: Path) -> None:
        assert read_uvlock_version(tmp_repo) == "1.2.3"

    def test_missing_file(self, tmp_path: Path) -> None:
        assert read_uvlock_version(tmp_path) is None

    def test_wrong_package_name(self, tmp_path: Path) -> None:
        (tmp_path / "uv.lock").write_text('[[package]]\nname = "other"\nversion = "0.1.0"\n')
        assert read_uvlock_version(tmp_path) is None

    def test_multiple_packages(self, tmp_path: Path) -> None:
        (tmp_path / "uv.lock").write_text(
            textwrap.dedent("""\
            [[package]]
            name = "click"
            version = "8.1.0"

            [[package]]
            name = "graphglot"
            version = "2.0.0"
            source = { editable = "." }
            """)
        )
        assert read_uvlock_version(tmp_path) == "2.0.0"


# ── consistency check tests ──────────────────────────────────────────────


class TestCheckConsistency:
    def test_all_match(self, tmp_repo: Path) -> None:
        assert check_consistency(root=tmp_repo) is True

    def test_all_match_with_expected(self, tmp_repo: Path) -> None:
        assert check_consistency(expected="1.2.3", root=tmp_repo) is True

    def test_pyproject_uvlock_mismatch(self, tmp_repo: Path) -> None:
        (tmp_repo / "uv.lock").write_text('[[package]]\nname = "graphglot"\nversion = "0.0.1"\n')
        assert check_consistency(root=tmp_repo) is False

    def test_expected_mismatch(self, tmp_repo: Path) -> None:
        assert check_consistency(expected="9.9.9", root=tmp_repo) is False

    def test_no_sources(self, tmp_path: Path) -> None:
        assert check_consistency(root=tmp_path) is False

    def test_uvlock_missing_still_passes_if_pyproject_matches_expected(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "graphglot"\nversion = "1.0.0"\n'
        )
        # Only pyproject + expected — they agree
        assert check_consistency(expected="1.0.0", root=tmp_path) is True

    def test_uvlock_missing_fails_if_pyproject_mismatches_expected(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "graphglot"\nversion = "1.0.0"\n'
        )
        assert check_consistency(expected="2.0.0", root=tmp_path) is False


# ── real repo sanity check ───────────────────────────────────────────────


class TestRealRepo:
    """Verify the actual repo versions are in sync."""

    def test_current_repo_is_consistent(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent.parent
        assert check_consistency(root=repo_root) is True
