#!/usr/bin/env bash
# Sync the shared adhoc-sdlc Python helper from the Claude variant (the canonical
# copy) into the Codex variants. Plugin packages cannot reference files outside
# their own install tree, so the helper is physically duplicated. This script
# keeps the shipped copies identical. Run it before committing any helper change,
# then run pytest in each scripts directory.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$REPO_ROOT/claude/skills/adhoc-sdlc/scripts"
DSTS=(
  "$REPO_ROOT/codex/skills/adhoc-sdlc/scripts"
  "$REPO_ROOT/plugins/adhoc-sdlc/skills/adhoc-sdlc/scripts"
)

if [ ! -d "$SRC" ]; then
  echo "ERROR: expected source scripts dir not found:" >&2
  echo "  SRC=$SRC" >&2
  exit 1
fi

for dst in "${DSTS[@]}"; do
  if [ ! -d "$dst" ]; then
    echo "ERROR: expected destination scripts dir not found:" >&2
    echo "  DST=$dst" >&2
    exit 1
  fi
done

# Copy every Python file (helper modules + tests). Does not delete files removed
# from the canonical copy; if you delete a helper file, remove it in every copy.
files=0
copies=0
for f in "$SRC"/*.py; do
  files=$((files + 1))
  for dst in "${DSTS[@]}"; do
    cp "$f" "$dst/$(basename "$f")"
    copies=$((copies + 1))
  done
done

echo "Synced $files Python files to ${#DSTS[@]} destinations ($copies copies)."
echo "Next: run 'python3 -m pytest -q' in each scripts dir."
