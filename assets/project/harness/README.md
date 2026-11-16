# Agent harness

This folder, `scripts/harness/` and the `harness-*` skills under `.agents/skills/` make the
repository workable by coding agents across sessions, worktrees and people, whichever agent each
person uses. Read this once; agents read the entry file (`AGENTS.md`, or a pointer to it such as
`CLAUDE.md`), which links here.

The skills are written once, in `.agents/skills/`. Agents that read another folder (Claude Code:
`.claude/skills/`, Devin: `.devin/skills/`, and so on) get mirrors of it, normally symlinks. Edit
only `.agents/skills/`; `init.sh` reports a mirror that is broken or drifted. Below, "use the
`harness-start` skill" means asking your agent for it by name, or `/harness-start` in agents with
slash commands.

## Two kinds of files

| | Where | In git? | Who changes it |
|---|---|---|---|
| **Contract**: rules, docs, scripts, checklists, templates | `harness/`, `scripts/harness/`, `.agents/skills/` and mirrors, agent adapters, `docs/` | yes | anyone, through a PR |
| **Task state**: feature list, contract, progress, handoff, logs | `.harness/tasks/<TASK-ID>/` | **no** (gitignored) | the person and agent working on that task |

Task state is personal and short-lived, so it stays out of git: it would conflict between
branches and one person's stale notes would mislead another person's agent. Treat it as a cache.
Anything that must survive goes somewhere durable before the task ends (see "Closing a task").

## Daily flow

### Start a task

One task = one branch = one worktree:

```bash
git worktree add ../<repo>-<TASK-ID> -b <branch>   # any agent
claude --worktree <TASK-ID>                         # Claude Code: isolated checkout under .claude/worktrees/
```

Then, inside an agent session in that worktree, use the `harness-start` skill with the task id and
a link or description of the task (`/harness-start <TASK-ID> <link>` in agents with slash commands).

It initializes `.harness/tasks/<TASK-ID>/`, writes the contract (scope, out of scope, done
criteria), turns the done criteria into items with exact verification commands, records a red
baseline (the checks should fail before the change), and runs `init.sh`. Review the contract
before letting the agent code: this is the cheapest moment to fix a misunderstanding.

Without worktrees, use a normal branch; the state folder is still per checkout.

### Work

- One item at a time: `python3 scripts/harness/feature.py next`, then `start <ID>`.
- An item becomes `passing` only through `python3 scripts/harness/feature.py verify <ID>`, which
  runs its command and stores the log as evidence. Every `feature.py` command checks a seal over
  the state and refuses to work after a hand edit of status, evidence or history; `feature.py
  recover` reseals and sends passing items back to be verified again. An optional hook blocks the
  hand edit earlier in agents that support hooks.
- Full check at any time: `bash scripts/harness/verify.sh` (static, tests, smoke, e2e).

### End a session

Use the `harness-handoff` skill. It runs verification and the cleanup scan, appends to
`progress.md`, rewrites `handoff.md`, and walks the clean-state checklist. To resume later, open a
session in the same worktree and run `bash scripts/harness/init.sh`, which prints the task state
and points at the handoff (in Claude Code, `claude --worktree <TASK-ID> --resume`; its
session-start hook prints the state for you).

### Hand a task to someone else

The `harness-handoff` skill with `--share` pushes the branch (after asking) and publishes the handoff where the
team can see it: the PR (draft is fine) or the issue tracker. The next person creates their own
worktree on that branch and uses the `harness-start` skill with the task id, which rebuilds local state from the
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

Run the `harness-evaluate` skill in a separate context: a subagent where your agent has them (in
Claude Code, the `harness-evaluator` subagent), otherwise a fresh session. It is a skeptical checker that
reruns the verification, reads the diff against the contract and scores it with
`harness/evaluator-rubric.md`. Fix REVISE findings before opening the PR.

### Periodically (for example weekly)

The `harness-cleanup` skill on the base branch: full verification, cleanup and architecture scans,
quality-document update, promotion of repeated review comments into checks, and a proposal for
harness components that no longer pull their weight.

## Configuration

- `harness/config.sh`: commands for each verification layer, base branch, debug patterns.
- `harness/architecture-rules.json`: executable boundaries.
- `.claude/settings.json`: optional session-start and guard hooks for Claude Code. The harness
  works without them; they only surface state earlier and block hand edits before they happen.
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
| `python3 scripts/harness/feature.py <cmd>` | Task state: `init`, `status`, `add`, `next`, `start`, `verify`, `block`, `unblock`, `reopen`, `remove`, `set-verify`, `recover`, `validate`. |
| `python3 scripts/harness/check_architecture.py` | Boundary rules. |
| `bash scripts/harness/cleanup-scan.sh` | Debug code, conflict markers, stray files, stale state. |

Requirements: `bash`, `git`, `python3` (standard library only).
