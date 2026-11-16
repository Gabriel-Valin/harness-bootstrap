<!-- Insert into the entry file (CLAUDE.md or AGENTS.md), near the top or the bottom. Replace the
     two <...> placeholders. Keep it short: details live in harness/README.md. -->

## Agent harness

Work here goes through the harness. Details: `harness/README.md`.

**Start of every session**
1. `bash scripts/harness/init.sh` (setup, quick verification, current task state)
2. No task yet: use the `harness-start` skill with the task id. Resuming: read
   `.harness/tasks/<TASK-ID>/handoff.md`.
3. `python3 scripts/harness/feature.py next`, then `start <ID>`

**Rules**
- One task per branch/worktree; one active item at a time. Finish and verify before starting another.
- An item is done only when `python3 scripts/harness/feature.py verify <ID>` passes. Never edit
  status or evidence in `feature_list.json` by hand.
- Done = `bash scripts/harness/verify.sh` passes (static, tests, smoke, e2e for cross-component
  changes) **and** `harness/clean-state-checklist.md` holds.
- Stay inside `.harness/tasks/<TASK-ID>/contract.md`. Note anything else as a follow-up.
- Boundaries: `docs/ARCHITECTURE.md`, enforced by `scripts/harness/check_architecture.py`.
- Before claiming a task is done, run the `harness-evaluate` skill in a separate context (a
  subagent or a fresh session) and fix its findings.
- Report failures with the real output. Never weaken a check to make it pass.

**End of every session**: use the `harness-handoff` skill (`--share` to hand over, `--close` to finish).

Skills are in `.claude/skills/`; in agents with slash commands, invoke them as `/harness-start`,
`/harness-handoff`, `/harness-cleanup` and `/harness-evaluate`.

Base branch: `<base branch>`. Branch naming: `<convention>`.
