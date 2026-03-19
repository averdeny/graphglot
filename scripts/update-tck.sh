#!/usr/bin/env bash
# Update vendored openCypher TCK feature files from upstream.
#
# Usage:
#   scripts/update-tck.sh                  # update to latest master
#   scripts/update-tck.sh <commit-or-tag>  # update to specific revision
#
# This script:
#   1. Clones the openCypher repo at the specified revision
#   2. Copies tck/features/ into tests/graphglot/tck/features/
#   3. Updates the commit reference in loader.py
#   4. Cleans up the temporary clone

set -euo pipefail

REPO_URL="https://github.com/opencypher/openCypher.git"
TARGET_DIR="tests/graphglot/tck/features"
LOADER_FILE="tests/graphglot/tck/loader.py"
REVISION="${1:-master}"

# Resolve to project root (script lives in scripts/)
cd "$(dirname "$0")/.."

echo "==> Cloning openCypher at revision: ${REVISION}"
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

git clone --depth 1 --branch "$REVISION" "$REPO_URL" "$TMPDIR/openCypher" 2>/dev/null || {
    # branch/tag clone failed — try as a commit hash
    git clone "$REPO_URL" "$TMPDIR/openCypher"
    git -C "$TMPDIR/openCypher" checkout "$REVISION"
}

COMMIT=$(git -C "$TMPDIR/openCypher" rev-parse --short HEAD)
echo "==> Resolved to commit: ${COMMIT}"

# Verify source exists
if [ ! -d "$TMPDIR/openCypher/tck/features" ]; then
    echo "ERROR: tck/features/ not found in openCypher repo" >&2
    exit 1
fi

# Replace vendored features
echo "==> Replacing ${TARGET_DIR}/"
rm -rf "$TARGET_DIR"
cp -r "$TMPDIR/openCypher/tck/features" "$TARGET_DIR"

# Update commit reference in loader.py
if [ -f "$LOADER_FILE" ]; then
    sed -i "s/commit [0-9a-f]\{7,\}/commit ${COMMIT}/" "$LOADER_FILE"
    echo "==> Updated commit reference in ${LOADER_FILE}"
fi

# Summary
FEATURE_COUNT=$(find "$TARGET_DIR" -name '*.feature' | wc -l)
echo "==> Done: ${FEATURE_COUNT} feature files vendored from commit ${COMMIT}"
