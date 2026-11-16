#!/usr/bin/env bash
# init.sh - get a fresh checkout or worktree to a known-good state before any work starts.
#
# Run it at the start of every session, after cloning, and in every new worktree.
# It proves the four startup conditions: can start, can test, can see progress, can pick up the
# next step.
set -o pipefail
# shellcheck source=lib.sh
. "$(dirname "$0")/lib.sh"
harness_require_python
cd "$HARNESS_ROOT" || exit 1

echo "=== Harness init ($(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'no branch')) ==="

echo ""
echo "[1/4] Harness files"
missing=0
for f in harness/config.sh harness/architecture-rules.json harness/clean-state-checklist.md \
         harness/evaluator-rubric.md harness/templates/feature_list.json \
         harness/templates/handoff.md harness/templates/progress.md harness/templates/contract.md \
         scripts/harness/verify.sh scripts/harness/feature.py scripts/harness/check_architecture.py \
         scripts/harness/cleanup-scan.sh; do
  if [ -f "$f" ]; then
    echo "  OK       $f"
  else
    echo "  MISSING  $f"
    missing=1
  fi
done
if [ "$missing" -eq 1 ]; then
  echo "ERROR: harness files are missing."
  echo "FIX:   restore them from the base branch (git checkout <base> -- <file>) or rerun harness-bootstrap."
  exit 1
fi

echo ""
echo "[2/4] Setup"
LOG="$(harness_run_log init)"
harness_run_cmds "setup" "${HARNESS_SETUP_CMDS:-}" "$LOG"
case $? in
  0) echo "  PASS: setup" ;;
  2) echo "  SKIP: no setup command configured" ;;
  *) echo "ERROR: setup failed. FIX: read ${LOG#"$HARNESS_ROOT"/}; fix the environment before writing code."
     exit 1 ;;
esac

echo ""
echo "[3/4] Quick verification (static + tests)"
bash scripts/harness/verify.sh --quick
rc=$?
if [ "$rc" -eq 1 ]; then
  echo ""
  echo "WARN: the branch is not green before you start. Fix or record this first, so you do not"
  echo "      build on top of a broken state or blame your change for an existing failure."
fi

echo ""
echo "[4/4] Task state"
mkdir -p .harness
task="$(harness_task_id)"
if [ -n "$task" ]; then
  # status already explains a broken seal; validate would only repeat it.
  if python3 scripts/harness/feature.py status; then
    python3 scripts/harness/feature.py validate || true
  fi
  if [ -f ".harness/tasks/$task/handoff.md" ]; then
    echo ""
    echo "Read next: .harness/tasks/$task/handoff.md"
  fi
else
  echo "  No active task in this worktree. Start one with the harness-start skill"
  echo "  (or: python3 scripts/harness/feature.py init <TASK-ID> --title \"...\")."
fi

echo ""
if [ "$rc" -eq 0 ]; then
  echo "=== Init complete ==="
else
  echo "=== Init complete with problems (verification exit code $rc) ==="
fi
exit "$rc"
