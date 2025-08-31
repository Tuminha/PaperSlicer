#!/usr/bin/env bash
set -euo pipefail

# Clean outputs to start fresh:
# - out/meta, out/tests, out/rag (reports and JSONs)
# - data/xml (TEI)
# - media (exported images)
#
# Usage:
#   scripts/clean_corpus.sh            # interactive confirm
#   scripts/clean_corpus.sh --yes      # no prompt
#   scripts/clean_corpus.sh --dry-run  # show what would be removed

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

YES=0
DRY=0
for arg in "$@"; do
  case "$arg" in
    --yes|-y) YES=1 ;;
    --dry-run|--dry) DRY=1 ;;
    *) echo "Unknown arg: $arg" >&2; exit 2 ;;
  esac
done

TARGETS=(
  "$ROOT/out/meta"
  "$ROOT/out/tests"
  "$ROOT/out/rag"
  "$ROOT/data/xml"
  "$ROOT/media"
)

echo "About to clean the following directories (contents only):"
for d in "${TARGETS[@]}"; do
  echo "  - $d"
done

if [[ $DRY -eq 1 ]]; then
  echo "\n[dry-run] No changes made."
  exit 0
fi

if [[ $YES -ne 1 ]]; then
  read -r -p "Proceed? Type 'yes' to confirm: " ANSW
  if [[ "$ANSW" != "yes" ]]; then
    echo "Aborted."
    exit 1
  fi
fi

purge_dir() {
  local dir="$1"
  mkdir -p "$dir"
  # Remove everything except .gitkeep if present
  if command -v find >/dev/null 2>&1; then
    find "$dir" -mindepth 1 -not -name '.gitkeep' -exec rm -rf {} + 2>/dev/null || true
  else
    rm -rf "$dir"/* "$dir"/.[!.]* "$dir"/..?* 2>/dev/null || true
    # recreate .gitkeep if it was there before (best-effort)
    :
  fi
}

for d in "${TARGETS[@]}"; do
  echo "Cleaning $d ..."
  purge_dir "$d"
done

echo "Done. Fresh start ready."

