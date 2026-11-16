#!/usr/bin/env bash
# lib.sh - shared helpers for the harness scripts. Source it; do not execute it.

HARNESS_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
HARNESS_SCRIPTS="$HARNESS_ROOT/scripts/harness"
HARNESS_STATE="$HARNESS_ROOT/.harness"

if [ -f "$HARNESS_ROOT/harness/config.sh" ]; then
  # shellcheck source=/dev/null
  . "$HARNESS_ROOT/harness/config.sh"
fi

harness_require_python() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 not found." >&2
    echo "WHY:   the harness state tools (feature.py, check_architecture.py) need Python 3.8+." >&2
    echo "FIX:   install Python 3 and make sure 'python3' is on PATH." >&2
    exit 127
  fi
}

# Print the current task id, or nothing when no task is active in this worktree.
harness_task_id() {
  if [ -n "${HARNESS_TASK:-}" ]; then
    printf '%s\n' "$HARNESS_TASK"
  elif [ -f "$HARNESS_STATE/current" ]; then
    head -n 1 "$HARNESS_STATE/current"
  fi
}

# Print a fresh log file path for a run named $1, inside the task folder when a task is active.
harness_run_log() {
  local name="$1" task dir stamp
  task="$(harness_task_id)"
  if [ -n "$task" ] && [ -d "$HARNESS_STATE/tasks/$task" ]; then
    dir="$HARNESS_STATE/tasks/$task/runs"
  else
    dir="$HARNESS_STATE/runs"
  fi
  mkdir -p "$dir"
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  printf '%s/%s-%s.log\n' "$dir" "$name" "$stamp"
}

# Resolve the base ref used for diffs: config value, then origin/HEAD, then main or master.
harness_base_ref() {
  local ref
  if [ -n "${HARNESS_BASE_BRANCH:-}" ]; then
    if git rev-parse --verify --quiet "origin/$HARNESS_BASE_BRANCH" >/dev/null; then
      printf 'origin/%s\n' "$HARNESS_BASE_BRANCH"
    else
      printf '%s\n' "$HARNESS_BASE_BRANCH"
    fi
    return
  fi
  ref="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null)"
  if [ -n "$ref" ]; then
    printf '%s\n' "$ref"
    return
  fi
  for ref in origin/main origin/master main master; do
    if git rev-parse --verify --quiet "$ref" >/dev/null; then
      printf '%s\n' "$ref"
      return
    fi
  done
}

# Run every non-empty line of $2 as a command. $1 is a label, $3 a log file.
# Returns 0 when all pass, 1 on the first failure, 2 when there was nothing to run.
harness_run_cmds() {
  local label="$1" cmds="$2" log="$3" cmd ran=0
  while IFS= read -r cmd; do
    case "$cmd" in ''|'#'*) continue ;; esac
    ran=1
    echo "  \$ $cmd" | tee -a "$log"
    # stdin from /dev/null so a command cannot swallow the rest of this loop's input.
    if ! (cd "$HARNESS_ROOT" && bash -c "$cmd") </dev/null 2>&1 | tee -a "$log"; then
      echo "  FAIL [$label]: $cmd" | tee -a "$log"
      return 1
    fi
  done <<EOF
$cmds
EOF
  [ "$ran" -eq 1 ] || return 2
  return 0
}
