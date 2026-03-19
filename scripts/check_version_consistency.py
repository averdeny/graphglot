#!/usr/bin/env python3
"""Check that all version sources in the project are consistent.

Sources checked:
  - pyproject.toml  (project.version)
  - uv.lock         (graphglot package version)
  - optional: --expected flag or git tag context

Usage:
  python scripts/check_version_consistency.py
  python scripts/check_version_consistency.py --expected 0.9.4
"""

from __future__ import annotations

import argparse
import re
import sys

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# ── readers ──────────────────────────────────────────────────────────────────


def read_pyproject_version(root: Path = REPO_ROOT) -> str | None:
    """Extract version from pyproject.toml [project] section."""
    path = root / "pyproject.toml"
    if not path.exists():
        return None
    content = path.read_text()
    match = re.search(r'^\s*version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    return match.group(1) if match else None


def read_uvlock_version(root: Path = REPO_ROOT) -> str | None:
    """Extract graphglot version from uv.lock.

    The lock file uses TOML-style ``[[package]]`` blocks.  We look for the
    block whose ``name = "graphglot"`` and read the next ``version = "..."``
    line.
    """
    path = root / "uv.lock"
    if not path.exists():
        return None
    lines = path.read_text().splitlines()
    found_package = False
    for line in lines:
        stripped = line.strip()
        if stripped == 'name = "graphglot"':
            found_package = True
            continue
        if found_package:
            m = re.match(r'^version\s*=\s*"([^"]+)"', stripped)
            if m:
                return m.group(1)
            # If we hit a blank line or another section before version, stop.
            if stripped == "" or stripped.startswith("["):
                break
    return None


# ── main ─────────────────────────────────────────────────────────────────────


def check_consistency(
    expected: str | None = None,
    root: Path = REPO_ROOT,
) -> bool:
    """Return True when all version sources agree, False otherwise."""
    pyproject_ver = read_pyproject_version(root)
    uvlock_ver = read_uvlock_version(root)

    sources: dict[str, str | None] = {
        "pyproject.toml": pyproject_ver,
        "uv.lock": uvlock_ver,
    }
    if expected is not None:
        sources["expected (--expected / tag)"] = expected

    # Display table
    max_label = max(len(k) for k in sources)
    print("\nVersion consistency check")
    print("=" * (max_label + 20))
    for label, ver in sources.items():
        status = ver if ver is not None else "(not found)"
        print(f"  {label:<{max_label}}  {status}")
    print()

    # Collect non-None values
    found = {k: v for k, v in sources.items() if v is not None}
    if not found:
        print("ERROR: No version sources found.")
        return False

    unique = set(found.values())
    if len(unique) == 1:
        print(f"OK: All sources agree on version {unique.pop()}")
        return True

    print("MISMATCH: Version sources disagree!")
    print()
    print("Remediation:")
    if pyproject_ver and uvlock_ver and pyproject_ver != uvlock_ver:
        print("  Run: uv lock")
        print("  This regenerates uv.lock from pyproject.toml.")
    if expected and pyproject_ver != expected:
        print(f'  Update pyproject.toml version to "{expected}" and run: uv lock')
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Check version consistency across project files.")
    parser.add_argument(
        "--expected",
        default=None,
        help="Expected version (e.g. from a git tag or release context).",
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Repository root directory (defaults to auto-detected).",
    )
    args = parser.parse_args()
    root = Path(args.root) if args.root else REPO_ROOT
    ok = check_consistency(expected=args.expected, root=root)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
