# Agent harness

This folder, `scripts/harness/` and the `harness-*` skills under `.claude/` make the repository
workable by coding agents across sessions, worktrees and people. Read this once; agents read the
entry file (`CLAUDE.md` / `AGENTS.md`), which links here.

## Two kinds of files

| | Where | In git? | Who changes it |
|---|---|---|---|
| **Contract**: rules, docs, scripts, checklists, templates | `harness/`, `scripts/harness/`, `.claude/`, `docs/` | yes | anyone, through a PR |
| **Task state**: feature list, contract, progress, handoff, logs | `.harness/tasks/<TASK-ID>/` | **no** (gitignored) | the person and agent working on that task |

Task state is personal and short-lived, so it stays out of git: it would conflict between
branches and one person's stale notes would mislead another person's agent. Treat it as a cache.
Anything that must survive goes somewhere durable before the task ends (see "Closing a task").

## Daily flow

### Start a task

One task = one branch = one worktree. With Claude Code:

```bash
claude --worktree <TASK-ID>          # isolated checkout under .claude/worktrees/<TASK-ID>
```

Then, inside the session:

```
/harness-start <TASK-ID> <link or description of the task>
```

It initializes `.harness/tasks/<TASK-ID>/`, writes the contract (scope, out of scope, done
criteria), turns the done criteria into items with exact verification commands, records a red
baseline (the checks should fail before the change), and runs `init.sh`. Review the contract
before letting the agent code: this is the cheapest moment to fix a misunderstanding.

Without worktrees, use a normal branch; the state folder is still per checkout.

### Work

- One item at a time: `python3 scripts/harness/feature.py next`, then `start <ID>`.
- An item becomes `passing` only through `python3 scripts/harness/feature.py verify <ID>`, which
  runs its command and stores the log as evidence. A hook blocks hand edits of status.
- Full check at any time: `bash scripts/harness/verify.sh` (static, tests, smoke, e2e).

### End a session

```
/harness-handoff
```

Runs verification and the cleanup scan, appends to `progress.md`, rewrites `handoff.md`, and walks
the clean-state checklist. Resume later with `claude --worktree <TASK-ID> --resume`; the
session-start hook prints the task state.

### Hand a task to someone else

`/harness-handoff --share` pushes the branch (after asking) and publishes the handoff where the
team can see it: the PR (draft is fine) or the issue tracker. The next person creates their own
worktree on that branch and runs `/harness-start <TASK-ID>`, which rebuilds local state from the
shared handoff, the git log and the diff.

### Closing a task

Before merging, promote what must survive, then delete `.harness/tasks/<TASK-ID>/`:

- Decisions that outlive the task -> `docs/decisions/NNNN-title.md` (template:
  `harness/templates/adr.md`)
- Evidence -> PR description: each item, its command, its result
- Regression checks -> the real test suite
- Changed architecture or behavior -> `docs/ARCHITECTURE.md`, `docs/PRODUCT.md`

If a machine is lost, nothing important is lost: rebuild state from the branch, the PR and the
tracker.

### Before asking for review

Ask Claude to run the `harness-evaluator` subagent. It is a separate, skeptical checker that
reruns the verification, reads the diff against the contract and scores it with
`harness/evaluator-rubric.md`. Fix REVISE findings before opening the PR.

### Periodically (for example weekly)

`/harness-cleanup` on the base branch: full verification, cleanup and architecture scans,
quality-document update, promotion of repeated review comments into checks, and a proposal for
harness components that no longer pull their weight.

## Configuration

- `harness/config.sh`: commands for each verification layer, base branch, debug patterns.
- `harness/architecture-rules.json`: executable boundaries.
- `.claude/settings.json`: the session-start and guard hooks.
- `.worktreeinclude`: gitignored files (such as `.env`) copied into each new worktree.

### Architecture rules

Each rule in `harness/architecture-rules.json` has: `id`, `description`, `paths` (globs), optional
`allow` (globs exempted), `forbid` (Python regex matched per line), `why` and `fix`. Write `fix` so
an agent can make the change from the message alone. Prefer an existing linter when one already
enforces the boundary.

## Commands

| Command | Purpose |
|---|---|
| `bash scripts/harness/init.sh` | Setup + quick verification + task state. Start of every session. |
| `bash scripts/harness/verify.sh [--quick]` | Layered verification; exit 3 means a required layer is not configured. |
| `python3 scripts/harness/feature.py <cmd>` | Task state: `init`, `status`, `add`, `next`, `start`, `verify`, `block`, `unblock`, `reopen`, `remove`, `validate`. |
| `python3 scripts/harness/check_architecture.py` | Boundary rules. |
| `bash scripts/harness/cleanup-scan.sh` | Debug code, conflict markers, stray files, stale state. |

Requirements: `bash`, `git`, `python3` (standard library only).
