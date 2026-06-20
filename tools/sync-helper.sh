#!/usr/bin/env bash
# Sync the shared adhoc-sdlc Python helper from the Claude variant (the canonical
# copy) into the Codex variant. The Claude plugin cannot reference files outside
# its own directory (path traversal is rejected after a marketplace install), so
# the helper is physically duplicated. This script keeps the two copies identical.
# Run it before committing any helper change, then run pytest in both variants.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$REPO_ROOT/claude/skills/adhoc-sdlc/scripts"
DST="$REPO_ROOT/codex/skills/adhoc-sdlc/scripts"

if [ ! -d "$SRC" ] || [ ! -d "$DST" ]; then
  echo "ERROR: expected scripts dirs not found:" >&2
  echo "  SRC=$SRC" >&2
  echo "  DST=$DST" >&2
  exit 1
fi

# Copy every Python file (helper modules + tests). Does not delete files removed
# from the canonical copy; if you delete a helper file, remove it in both places.
count=0
for f in "$SRC"/*.py; do
  cp "$f" "$DST/$(basename "$f")"
  count=$((count + 1))
done

echo "Synced $count Python files: claude -> codex"
echo "Next: run 'python3 -m pytest -q' in both scripts dirs."
