#!/usr/bin/env bash
# cleanup-scan.sh - report what would leave the next session a mess. Read-only and idempotent.
#
# Checks, against the merge base with the base branch:
#   1. debug code in added lines (HARNESS_DEBUG_PATTERNS)
#   2. merge conflict markers in added lines
#   3. untracked files that are neither committed nor gitignored
#   4. task state consistency (feature.py validate)
#   5. handoff older than the latest commit
#
# Usage: scripts/harness/cleanup-scan.sh
# Exit codes: 0 clean, 1 issues found.
set -o pipefail
# shellcheck source=lib.sh
. "$(dirname "$0")/lib.sh"
cd "$HARNESS_ROOT" || exit 1

issues=0
base="$(harness_base_ref)"
if [ -n "$base" ]; then
  merge_base="$(git merge-base HEAD "$base" 2>/dev/null)"
fi
echo "=== Cleanup scan (base: ${base:-none}) ==="

# Added lines as "file:line: text", comparing the working tree with the merge base.
added_lines() {
  if [ -z "${merge_base:-}" ]; then
    return
  fi
  git diff -U0 --no-color "$merge_base" -- . ':(exclude).harness' 2>/dev/null | awk '
    /^\+\+\+ /   { file = substr($0, 7); next }
    /^@@ /       { split($3, a, ","); line = substr(a[1], 2) + 0; next }
    /^\+/        { print file ":" line ": " substr($0, 2); line++ }
  '
  git ls-files --others --exclude-standard -z -- . ':(exclude).harness' 2>/dev/null |
    while IFS= read -r -d '' file; do
      awk -v file="$file" '{ print file ":" NR ": " $0 }' "$file"
    done
}

debug_candidates() {
  added_lines | grep -v '^harness/config\.sh:'
}

debug_hits() {
  debug_candidates | HARNESS_PATTERNS="$HARNESS_DEBUG_PATTERNS" \
    HARNESS_ALLOW_PATHS="${HARNESS_DEBUG_ALLOW_PATHS:-}" \
    HARNESS_ALLOW_PATTERN="${HARNESS_DEBUG_ALLOW_PATTERN:-}" awk '
    {
      text = $0
      if (ENVIRON["HARNESS_ALLOW_PATHS"] != "" && ENVIRON["HARNESS_ALLOW_PATTERN"] != "" \
          && $0 ~ ("^(" ENVIRON["HARNESS_ALLOW_PATHS"] ")[^:]*:")) {
        gsub(ENVIRON["HARNESS_ALLOW_PATTERN"], "", text)
      }
      if (text ~ ENVIRON["HARNESS_PATTERNS"]) print
    }'
}

echo ""
echo "[1/5] Debug code in added lines"
if [ -z "${merge_base:-}" ]; then
  echo "  SKIP: no base branch found (set HARNESS_BASE_BRANCH in harness/config.sh)"
elif [ -z "${HARNESS_DEBUG_PATTERNS:-}" ]; then
  echo "  SKIP: HARNESS_DEBUG_PATTERNS is empty"
else
  hits="$(debug_hits)"
  if [ -n "$hits" ]; then
    printf '%s\n' "$hits" | sed 's/^/  DEBUG  /'
    echo "  FIX: remove the debug code, or replace it with the project's structured logger."
    issues=$((issues + 1))
  else
    echo "  OK"
  fi
fi

echo ""
echo "[2/5] Conflict markers in added lines"
if [ -n "${merge_base:-}" ]; then
  hits="$(added_lines | grep -E ': (<<<<<<< |>>>>>>> |=======$)' || true)"
  if [ -n "$hits" ]; then
    printf '%s\n' "$hits" | sed 's/^/  CONFLICT  /'
    echo "  FIX: resolve the conflict and rerun scripts/harness/verify.sh."
    issues=$((issues + 1))
  else
    echo "  OK"
  fi
else
  echo "  SKIP: no base branch found"
fi

echo ""
echo "[3/5] Stray untracked files"
stray="$(git ls-files --others --exclude-standard)"
if [ -n "$stray" ]; then
  printf '%s\n' "$stray" | sed 's/^/  UNTRACKED  /'
  echo "  FIX: commit what belongs to the change, delete temporary files, gitignore generated ones."
  issues=$((issues + 1))
else
  echo "  OK"
fi

echo ""
echo "[4/5] Task state"
task="$(harness_task_id)"
if [ -z "$task" ]; then
  echo "  SKIP: no active task in this worktree"
elif python3 scripts/harness/feature.py validate; then
  :
else
  issues=$((issues + 1))
fi

echo ""
echo "[5/5] Handoff freshness"
handoff="$HARNESS_STATE/tasks/$task/handoff.md"
if [ -z "$task" ]; then
  echo "  SKIP: no active task"
elif [ ! -f "$handoff" ]; then
  echo "  MISSING: .harness/tasks/$task/handoff.md"
  issues=$((issues + 1))
else
  last_commit="$(git log -1 --format=%ct 2>/dev/null || echo 0)"
  handoff_mtime="$(python3 -c 'import os,sys; print(int(os.path.getmtime(sys.argv[1])))' "$handoff")"
  if [ "$handoff_mtime" -lt "$last_commit" ]; then
    echo "  STALE: handoff.md is older than the latest commit"
    echo "  FIX: update it with the harness-handoff skill before ending the session."
    issues=$((issues + 1))
  else
    echo "  OK"
  fi
fi

echo ""
if [ "$issues" -eq 0 ]; then
  echo "RESULT: CLEAN"
else
  echo "RESULT: $issues check(s) found issues"
  exit 1
fi
