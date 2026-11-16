#!/usr/bin/env bash
# harness-session-start.sh - SessionStart hook. Prints the task state of the current worktree so
# a fresh session knows where it stopped. Output becomes session context. Never fails the session.

input="$(cat)"
cwd="$(printf '%s' "$input" | python3 -c 'import json,sys
try:
    print(json.load(sys.stdin).get("cwd", ""))
except Exception:
    pass' 2>/dev/null)"
if [ -n "$cwd" ]; then
  cd "$cwd" 2>/dev/null || exit 0
fi

root="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$root" || exit 0
[ -f scripts/harness/feature.py ] || exit 0

echo "## Harness state"
echo "Branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null)  Commit: $(git rev-parse --short HEAD 2>/dev/null)"

task="${HARNESS_TASK:-}"
if [ -z "$task" ] && [ -f .harness/current ]; then
  task="$(head -n 1 .harness/current)"
fi

if [ -z "$task" ]; then
  echo "No harness task is active in this worktree. To begin work on a task, run /harness-start <TASK-ID>."
else
  python3 scripts/harness/feature.py status 2>&1 | head -n 40
  handoff=".harness/tasks/$task/handoff.md"
  if [ -f "$handoff" ]; then
    echo ""
    echo "### Last handoff ($handoff)"
    head -n 60 "$handoff"
  fi
  echo ""
  echo "Before editing: run bash scripts/harness/init.sh, then python3 scripts/harness/feature.py next."
fi

changes="$(git status --short 2>/dev/null | head -n 20)"
if [ -n "$changes" ]; then
  echo ""
  echo "### Uncommitted changes"
  printf '%s\n' "$changes"
fi
exit 0
