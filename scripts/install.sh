#!/usr/bin/env bash
# install.sh - copy the harness scaffold into a repository without overwriting anything.
#
# Usage: bash install.sh <repo-root> [--dry-run]
#
# Prints CREATED or SKIPPED for every file. Existing files are never touched; merge them by hand.
set -o pipefail

usage() {
  echo "Usage: bash install.sh <repo-root> [--dry-run]" >&2
  exit 2
}

TARGET=""
DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    -h|--help) usage ;;
    *)
      if [ -n "$TARGET" ]; then
        usage
      fi
      TARGET="$arg"
      ;;
  esac
done
[ -n "$TARGET" ] || usage

if [ ! -d "$TARGET" ]; then
  echo "ERROR: target directory not found: $TARGET" >&2
  exit 1
fi
TARGET="$(cd "$TARGET" && pwd)"

if ! git -C "$TARGET" rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "ERROR: $TARGET is not inside a git repository." >&2
  echo "WHY:   worktree isolation and base-branch checks need git." >&2
  echo "FIX:   run 'git init' there first, or point install.sh at the repository root." >&2
  exit 1
fi

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$SKILL_DIR/assets/project"

created=0
skipped=0

# Process substitution keeps the counters in this shell instead of a pipe subshell.
while IFS= read -r -d '' file; do
  rel="${file#"$SRC"/}"
  dest="$TARGET/$rel"
  if [ -e "$dest" ]; then
    echo "SKIPPED  $rel (already exists, merge by hand)"
    skipped=$((skipped + 1))
    continue
  fi
  echo "CREATED  $rel"
  created=$((created + 1))
  if [ "$DRY_RUN" -eq 0 ]; then
    mkdir -p "$(dirname "$dest")"
    cp "$file" "$dest"
    case "$rel" in
      *.sh|*.py) chmod +x "$dest" ;;
    esac
  fi
done < <(find "$SRC" -type f -not -path '*/__pycache__/*' -not -name '.DS_Store' -print0 | sort -z)

echo ""
if [ "$DRY_RUN" -eq 1 ]; then
  echo "Dry run: $created file(s) would be created, $skipped skipped. Nothing was written."
else
  echo "Done: $created file(s) created, $skipped skipped."
fi
echo "Next: fill harness/config.sh and harness/architecture-rules.json, then merge the snippets in"
echo "      $SKILL_DIR/assets/snippets/ (entry section, .gitignore lines, hook settings)."
