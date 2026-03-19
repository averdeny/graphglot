#!/usr/bin/env python3
"""Strip, restore, and verify BNF grammar definitions in expressions.py.

Usage:
  python scripts/bnf.py strip         # extract BNF docstrings to bnf.json, replace with stubs
  python scripts/bnf.py restore       # re-inject BNF docstrings from bnf.json
  python scripts/bnf.py verify        # dry-run round-trip check (strip→restore == original)
  python scripts/bnf.py check-staged  # pre-commit guard: reject BNF in staged file
"""

from __future__ import annotations

import argparse
import json
import re
import sys

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPRESSIONS_PATH = REPO_ROOT / "graphglot" / "ast" / "expressions.py"
SIDECAR_PATH = REPO_ROOT / "bnf.json"

# ── helpers ──────────────────────────────────────────────────────────────────


def _find_docstring(lines: list[str], start: int) -> tuple[int, int] | None:
    """Find a triple-quoted docstring starting at or after `start`.

    Returns (first_line_idx, last_line_idx) inclusive, or None.
    Skips blank lines between `start` and the opening quotes.
    """
    i = start
    while i < len(lines):
        stripped = lines[i].lstrip()
        if stripped.startswith('"""'):
            # single-line docstring: """...""" on one line (but not just """)
            if stripped.rstrip("\n").endswith('"""') and len(stripped.rstrip("\n")) > 3:
                return (i, i)
            # multi-line docstring
            j = i + 1
            while j < len(lines):
                if '"""' in lines[j]:
                    return (i, j)
                j += 1
            return None
        elif stripped == "" or stripped == "\n" or stripped.startswith("#"):
            i += 1
            continue
        else:
            return None
    return None


def _has_fenced_block(lines: list[str], start: int, end: int) -> bool:
    """Check if lines[start:end+1] contain a triple-backtick fenced block."""
    return any(lines[k].strip().startswith("```") for k in range(start, end + 1))


def _first_sentence(lines_slice: list[str]) -> str:
    """Extract the first sentence from docstring lines."""
    # Join and strip quotes
    text = "".join(lines_slice)
    text = text.replace('"""', "").strip()
    # Get first sentence (up to and including first period)
    match = re.match(r"(.+?\.)", text, re.DOTALL)
    if match:
        return " ".join(match.group(1).split())
    return " ".join(text.split())


def _indent_of(line: str) -> str:
    """Return leading whitespace of a line."""
    return line[: len(line) - len(line.lstrip())]


def _make_stub(indent: str, sentence: str) -> list[str]:
    """Create a stub docstring, trimming if needed for line length."""
    max_content = 100 - len(indent) - 6  # 6 = two sets of """
    if len(sentence) > max_content:
        # Truncate at the last word boundary that fits, keep trailing period
        truncated = sentence[: max_content - 1].rsplit(" ", 1)[0].rstrip(".,")
        sentence = truncated + "."
    return [f'{indent}"""{sentence}"""\n']


def _raw_text(lines: list[str], start: int, end: int) -> str:
    """Extract raw text from lines[start:end+1], stripping trailing newline."""
    chunk = "".join(lines[start : end + 1])
    if chunk.endswith("\n"):
        chunk = chunk[:-1]
    return chunk


def _text_to_lines(text: str) -> list[str]:
    """Convert stored text back to lines with newlines."""
    return [ln + "\n" for ln in text.split("\n")]


def _find_class_body_start(lines: list[str], i: int) -> int:
    """Find the line after the class definition (handling multi-line class defs)."""
    line = lines[i]
    if "(" in line and "):" not in line:
        j = i + 1
        while j < len(lines) and "):" not in lines[j]:
            j += 1
        return j + 1
    return i + 1


# ── strip ────────────────────────────────────────────────────────────────────


def strip(lines: list[str]) -> tuple[list[str], dict[str, str]]:
    """Strip BNF docstrings, return (modified_lines, sidecar_dict)."""
    sidecar: dict[str, str] = {}
    replacements: list[tuple[int, int, list[str]]] = []  # (start, end, new_lines)
    current_parent: str | None = None
    i = 0

    while i < len(lines):
        line = lines[i]

        # Track top-level class (indent level 0)
        m = re.match(r"^class (\w+)", line)
        if m:
            current_parent = m.group(1)
            body_start = _find_class_body_start(lines, i)
            ds = _find_docstring(lines, body_start)
            if ds and _has_fenced_block(lines, ds[0], ds[1]):
                key = current_parent
                sidecar[key] = _raw_text(lines, ds[0], ds[1])
                indent = _indent_of(lines[ds[0]])
                sentence = _first_sentence(lines[ds[0] : ds[1] + 1])
                stub = _make_stub(indent, sentence)
                replacements.append((ds[0], ds[1], stub))
            i += 1
            continue

        # Nested class (indented)
        m = re.match(r"^(\s+)class (\w+)", line)
        if m and current_parent:
            nested_name = m.group(2)
            body_start = _find_class_body_start(lines, i)
            ds = _find_docstring(lines, body_start)
            if ds and _has_fenced_block(lines, ds[0], ds[1]):
                key = f"{current_parent}.{nested_name}"
                sidecar[key] = _raw_text(lines, ds[0], ds[1])
                indent = _indent_of(lines[ds[0]])
                # Internal expressions get a fixed stub
                full = "".join(lines[ds[0] : ds[1] + 1])
                if "Internal expression for:" in full or "Internal expression for " in full:
                    stub = _make_stub(indent, "Internal expression.")
                else:
                    sentence = _first_sentence(lines[ds[0] : ds[1] + 1])
                    stub = _make_stub(indent, sentence)
                replacements.append((ds[0], ds[1], stub))
            i += 1
            continue

        # TypeAlias: single-line or multi-line
        m = re.match(r"^(\w+)\s*:\s*t\.TypeAlias\s*=", line.strip())
        if m:
            alias_name = m.group(1)
            # Find end of assignment (could span multiple lines with parens)
            assign_end = i
            if "(" in line and ")" not in line:
                j = i + 1
                while j < len(lines) and ")" not in lines[j]:
                    j += 1
                assign_end = j
            # Look for docstring after assignment
            ds = _find_docstring(lines, assign_end + 1)
            if ds and _has_fenced_block(lines, ds[0], ds[1]):
                key = f"TypeAlias:{alias_name}"
                sidecar[key] = _raw_text(lines, ds[0], ds[1])
                # TypeAlias docstrings are removed entirely (no stub)
                replacements.append((ds[0], ds[1], []))
            i += 1
            continue

        i += 1

    # Apply replacements in reverse order to preserve line indices
    result = list(lines)
    for start, end, new_lines in sorted(replacements, key=lambda r: r[0], reverse=True):
        result[start : end + 1] = new_lines

    return result, sidecar


# ── restore ──────────────────────────────────────────────────────────────────


def restore(lines: list[str], sidecar: dict[str, str]) -> list[str]:
    """Restore BNF docstrings from sidecar dict into stripped lines."""
    remaining = dict(sidecar)  # keys we still need to restore
    replacements: list[tuple[int, int, list[str]]] = []
    current_parent: str | None = None
    i = 0

    while i < len(lines):
        line = lines[i]

        # Top-level class
        m = re.match(r"^class (\w+)", line)
        if m:
            current_parent = m.group(1)
            key = current_parent
            if key in remaining:
                body_start = _find_class_body_start(lines, i)
                ds = _find_docstring(lines, body_start)
                if ds:
                    original_lines = _text_to_lines(remaining[key])
                    replacements.append((ds[0], ds[1], original_lines))
                    del remaining[key]
            i += 1
            continue

        # Nested class
        m = re.match(r"^(\s+)class (\w+)", line)
        if m and current_parent:
            nested_name = m.group(2)
            key = f"{current_parent}.{nested_name}"
            if key in remaining:
                body_start = _find_class_body_start(lines, i)
                ds = _find_docstring(lines, body_start)
                if ds:
                    original_lines = _text_to_lines(remaining[key])
                    replacements.append((ds[0], ds[1], original_lines))
                    del remaining[key]
            i += 1
            continue

        # TypeAlias
        stripped = line.strip()
        m_ta = re.match(r"^(\w+)\s*:\s*t\.TypeAlias\s*=", stripped)
        if m_ta:
            alias_name = m_ta.group(1)
            key = f"TypeAlias:{alias_name}"
            if key in remaining:
                # Find end of assignment
                assign_end = i
                if "(" in line and ")" not in line:
                    j = i + 1
                    while j < len(lines) and ")" not in lines[j]:
                        j += 1
                    assign_end = j
                # Insert the docstring after the assignment
                original_lines = _text_to_lines(remaining[key])
                insert_at = assign_end + 1
                replacements.append((insert_at, insert_at - 1, original_lines))  # pure insertion
                del remaining[key]
            i += 1
            continue

        i += 1

    # Apply in reverse
    result = list(lines)
    for start, end, new_lines in sorted(replacements, key=lambda r: r[0], reverse=True):
        if end < start:
            # Pure insertion (TypeAlias case)
            result[start:start] = new_lines
        else:
            result[start : end + 1] = new_lines

    if remaining:
        print(
            f"WARNING: {len(remaining)} sidecar entries not restored: {list(remaining.keys())[:5]}"
        )

    return result


# ── commands ─────────────────────────────────────────────────────────────────


def cmd_strip() -> int:
    original = EXPRESSIONS_PATH.read_text()
    lines = original.splitlines(keepends=True)
    stripped_lines, sidecar = strip(lines)

    sidecar_out = {
        "_meta": {
            "version": 1,
            "source": "graphglot/ast/expressions.py",
            "count": len(sidecar),
        },
        **sidecar,
    }

    SIDECAR_PATH.write_text(json.dumps(sidecar_out, indent=2, ensure_ascii=False) + "\n")
    EXPRESSIONS_PATH.write_text("".join(stripped_lines))

    print(f"Stripped {len(sidecar)} BNF docstrings → {SIDECAR_PATH.name}")
    return 0


def cmd_restore() -> int:
    if not SIDECAR_PATH.exists():
        print(f"ERROR: {SIDECAR_PATH.name} not found. Run 'strip' first.")
        return 1

    sidecar_data = json.loads(SIDECAR_PATH.read_text())
    meta = sidecar_data.pop("_meta", {})
    sidecar = sidecar_data

    lines = EXPRESSIONS_PATH.read_text().splitlines(keepends=True)
    restored_lines = restore(lines, sidecar)
    EXPRESSIONS_PATH.write_text("".join(restored_lines))

    print(f"Restored {meta.get('count', len(sidecar))} BNF docstrings from {SIDECAR_PATH.name}")
    return 0


def cmd_verify() -> int:
    original = EXPRESSIONS_PATH.read_text()
    lines = original.splitlines(keepends=True)

    # Strip
    stripped_lines, sidecar = strip(lines)
    stripped_text = "".join(stripped_lines)

    # Check no fenced blocks remain in stripped docstrings
    in_docstring = False
    for sline in stripped_text.splitlines():
        s = sline.strip()
        if s.startswith("#"):
            continue
        quotes = s.count('"""')
        if quotes >= 2:
            if "```" in s:
                print(f"FAIL: fenced block remains after stripping: {s}")
                return 1
            continue
        if quotes == 1:
            in_docstring = not in_docstring
            continue
        if in_docstring and s.startswith("```"):
            print("FAIL: fenced block remains in docstring after stripping")
            return 1

    # Restore
    restored_lines = restore(stripped_lines, sidecar)
    restored_text = "".join(restored_lines)

    # Compare
    if restored_text == original:
        print(f"OK: Round-trip verified ({len(sidecar)} docstrings)")
        return 0
    else:
        # Find first diff
        orig_lines = original.splitlines(keepends=True)
        rest_lines = restored_text.splitlines(keepends=True)
        for idx, (a, b) in enumerate(zip(orig_lines, rest_lines, strict=False)):
            if a != b:
                print(f"FAIL: First difference at line {idx + 1}")
                print(f"  original: {a.rstrip()}")
                print(f"  restored: {b.rstrip()}")
                break
        else:
            len_diff = len(orig_lines) - len(rest_lines)
            print(f"FAIL: Line count differs by {len_diff}")
        return 1


def cmd_check_staged() -> int:
    """Pre-commit hook: check if expressions.py contains BNF."""
    if not EXPRESSIONS_PATH.exists():
        return 0

    content = EXPRESSIONS_PATH.read_text()
    # Check for any fenced blocks in docstrings
    in_docstring = False
    for line in content.splitlines():
        s = line.strip()
        if s.startswith("#"):
            continue
        quotes = s.count('"""')
        if quotes >= 2:
            continue
        if quotes == 1:
            in_docstring = not in_docstring
            continue
        if in_docstring and s.startswith("```"):
            print("BNF grammar found in expressions.py")
            print("Run `make bnf-strip` before committing.")
            return 1
    return 0


# ── main ─────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Strip/restore BNF definitions in expressions.py")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("strip", help="Extract BNF to bnf.json, replace docstrings with stubs")
    sub.add_parser("restore", help="Re-inject BNF from bnf.json")
    sub.add_parser("verify", help="Dry-run round-trip check")
    cs = sub.add_parser("check-staged", help="Pre-commit: reject BNF in staged file")
    cs.add_argument("files", nargs="*", help="Filenames passed by pre-commit (ignored)")

    args = parser.parse_args()
    if args.command == "strip":
        return cmd_strip()
    elif args.command == "restore":
        return cmd_restore()
    elif args.command == "verify":
        return cmd_verify()
    elif args.command == "check-staged":
        return cmd_check_staged()
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
