# Handoff: {{TASK_ID}} - {{TITLE}}

Snapshot for whoever opens this worktree next, human or agent. Rewrite it completely at the end
of every session; history lives in progress.md.

## State

- Updated: {{DATE}}
- Branch / commit: {{BRANCH}} @ {{BASE_COMMIT}}
- Working tree: clean | dirty (what is uncommitted and why)
- verify.sh: PASS | FAIL (layer) | UNVERIFIED (layer)
- Items: run `python3 scripts/harness/feature.py status`

## Active item

- Id and behavior:
- Where it stands:
- Exact next action:

## Blockers and risks

- 

## Do not redo

Things already tried or decided, so the next session does not repeat them.

- 

## Startup

1. `bash scripts/harness/init.sh`
2. Read `contract.md`, then this file.
3. `python3 scripts/harness/feature.py next`
