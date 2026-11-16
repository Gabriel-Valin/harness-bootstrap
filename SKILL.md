---
name: harness-bootstrap
description: >-
  Install a complete, team-ready agent harness into any git repository: a short entry file
  (CLAUDE.md / AGENTS.md), architecture and reliability docs, layered verification scripts,
  executable architecture rules, a per-task feature list whose status only a verifier can change,
  session handoff and progress files that stay local (gitignored), a clean-state checklist, an
  independent evaluator, and integrity checks that enforce it all. Works with any coding agent
  (Claude Code, Codex, Cursor, Copilot, Devin, Pi and others). Use this whenever someone wants
  to "set up a harness", make a repo agent-ready, stop agents from forgetting context between
  sessions, stop agents from claiming "done" before things work, organize handoffs between
  developers or worktrees, or create AGENTS.md / CLAUDE.md / feature_list.json / init.sh /
  session-handoff files for a project, even if they never say the word "harness".
license: Apache-2.0
compatibility: Needs git, bash and python3 (standard library only) on the machine running the agent.
---

# Harness Bootstrap

Turn a repository into one where any fresh agent session, on any developer's machine, can answer
five questions from the repo alone: what is this, how is it organized, how do I run it, how do I
verify it, and where did we stop. Then make "done" something a script decides, not the agent.

This skill runs once per repository. It installs a **contract** that the team commits, and
lifecycle skills (`harness-start`, `harness-handoff`, `harness-cleanup`, `harness-evaluate`) that
live inside the repo so every teammate gets them on clone, whatever coding agent they use.

Paths in this file (`scripts/`, `references/`, `assets/`) are relative to the directory that
contains this `SKILL.md`. Where that directory is depends on the agent and on how the skill was
installed, so resolve it from the location you loaded this file from; never assume a fixed path
such as `~/.claude/skills/`.

Read `references/principles.md` if you need the reasoning behind any artifact (for example, to
explain it to the user or to adapt it to an unusual repo).

## The model you are installing

| Layer | Where | Committed? | Purpose |
|---|---|---|---|
| Entry file | `CLAUDE.md` and/or `AGENTS.md` | yes | Short map: what, how to run, how to verify, hard rules, links |
| Docs | `docs/ARCHITECTURE.md`, `PRODUCT.md`, `RELIABILITY.md`, `docs/decisions/` | yes | Knowledge the agent cannot infer from code |
| Contract | `harness/` (config, rules, checklist, rubric, quality doc, templates, README) | yes | Same rules for everyone, changed only by PR |
| Verification | `scripts/harness/` | yes | `init.sh`, `verify.sh`, `feature.py`, `check_architecture.py`, `cleanup-scan.sh` |
| Lifecycle | `.agents/skills/harness-*`, mirrored for agents that read another folder | yes | Start, hand off, clean up, evaluate |
| Adapters | Per agent, for example `.claude/agents/`, `.claude/hooks/` for Claude Code | yes | Optional extras: subagent, hooks |
| Task state | `.harness/tasks/<TASK-ID>/` | **no** | Feature list, contract, progress, handoff, run logs for one task |

Task state is local because it changes every session and belongs to one person's branch.
Committing it causes merge conflicts and lets one developer's stale state mislead another
developer's agent. It is a cache: everything durable is promoted to code, tests, docs, the PR, or
the issue tracker before the task ends. `harness/README.md` explains this to the team.

## Workflow

### 1. Confirm the target

Run `git rev-parse --show-toplevel` in the directory the user means. If it is not a git
repository, stop and say so: worktree isolation and the base-branch checks depend on git. Note
whether the working tree is dirty; suggest doing the bootstrap on its own branch so it can be
reviewed as one PR.

### 2. Inventory what already exists

Look before you write. Find and read:

- Instruction files: `AGENTS.md`, `CLAUDE.md`, `.claude/CLAUDE.md`, `CLAUDE.local.md`,
  `GEMINI.md`, `.cursorrules`, `.cursor/rules/`, `.github/copilot-instructions.md`,
  `.windsurfrules`
- Docs: `README*`, `docs/`, ADR folders, `CONTRIBUTING*`
- Existing harness pieces: `feature_list.json`, `progress.md`, `init.sh`, `Makefile`, `harness/`,
  `scripts/harness/`, `.harness/`
- Agent config and skills: `.agents/skills/`, `.claude/` (`settings.json`, `skills/`, `agents/`,
  `hooks/`), `.devin/`, `.cursor/`, `.github/`, `.worktreeinclude`
- `.gitignore`

Existing content wins. You extend it; you never replace a file the team wrote without asking.

### 3. Discover how the project runs

Follow `references/discovery.md`. The goal is a verified list of commands for each verification
layer, each with the place you found it (CI config is the strongest evidence, because it is what
the team actually trusts). Also identify the layers or modules of the code and the dependency
directions between them; those become architecture rules.

### 4. Ask only for the gaps

Batch the questions you could not answer from the repo into one structured question call if your
environment has one, otherwise into a single message. Typical gaps:

- Architecture boundaries you inferred but are not sure about ("is `ui/` allowed to import `db/`?")
- The end-to-end or smoke command, if none exists
- Base branch and branch naming convention, if not documented
- Which coding agents the team uses (Claude Code, Codex, Cursor, Copilot, Devin, Pi, others). This
  decides the entry file and which agent adapters to install.
- If the team uses Claude Code: whether to install its hooks (recommended; they surface task state
  at session start and block hand edits of task state before they happen)

Do not ask about things with a conventional default; pick it and mention it in the final report.

### 5. Copy the scaffold

```bash
bash <this skill's directory>/scripts/install.sh <repo-root> --agents <ids>
```

`--agents` takes the team's agents from step 4 as comma-separated ids, the same ids the
`npx skills` CLI uses (`claude-code`, `codex`, `cursor`, `github-copilot`, `gemini-cli`,
`opencode`, `pi`, `devin`, `windsurf`, `kiro-cli`, ...; `--help` lists them).

The script copies `assets/project/` into the repo, including the lifecycle skills in
`.agents/skills/`, which most agents read directly. For agents that read another folder
(`claude-code`, `devin`, `windsurf`, `kiro-cli`) it adds relative symlinks to those skills, and
for agents with an adapter in `assets/adapters/<id>/` it copies the adapter files. Pass `--copy`
for copies instead of symlinks when the team has Windows checkouts without symlink support;
`init.sh` then reports copies that drift. The script **never overwrites** an existing path,
marks scripts executable, and prints `CREATED` / `LINKED` / `SKIPPED` per path. Use `--dry-run`
first if the repo already has harness pieces. For every `SKIPPED` path, read the existing file and
merge the missing ideas into it by hand instead of forcing the template.

If the script reports `FAILED` paths, your agent's sandbox probably protects a folder such as
`.agents/` or `.claude/` (Codex does this for `.agents/` by default). Rerun the same command with
the permission your environment offers for it, or ask the user to run it. Never relocate the
skills to another folder to get around it: agents discover skills only in the folders they read,
so relocated skills silently stop working.

### 6. Fill in the project specifics

Everything the scaffold cannot know is yours to write, grounded in what you read in steps 2-4:

1. **`harness/config.sh`**: one command per line for each layer (setup, static, test, smoke, e2e),
   the base branch, and the debug patterns for the stack. Leave a layer empty only if it truly
   does not exist; `verify.sh` reports empty required layers as UNVERIFIED instead of passing.
2. **`harness/architecture-rules.json`**: one rule per boundary, following
   `references/architecture-rules.md`. Every rule needs `why` and `fix` written for an agent,
   because the error message is the feedback loop.
3. **Docs**: create `docs/ARCHITECTURE.md`, `docs/PRODUCT.md`, `docs/RELIABILITY.md` only where the
   repo has no equivalent, starting from `assets/docs-skeletons/`. Write from the code you read,
   keep each under ~150 lines, and mark anything you could not confirm as `TODO(confirm): ...`
   rather than guessing. If equivalents exist elsewhere, link to them instead of duplicating.
4. **Decision records**: the scaffold adds `docs/decisions/`. If the repo already keeps ADRs
   elsewhere (`doc/adr/`, `docs/adr/`), remove the new folder and point `harness/README.md`, the
   handoff and cleanup skills, and the templates at the existing one.
5. **`harness/quality-document.md`**: list the real modules with an honest initial grade, or
   `unknown` where you have no evidence. Never grade from a feeling.

### 7. Wire the entry file

Insert the section from `assets/snippets/entry-section.md` into the entry file, near the top or
the bottom (models recall the edges of long files better than the middle). Keep the entry file a
router: if it grows past ~200 lines, move detail into `docs/` and link to it.

`AGENTS.md` is the canonical entry file: most coding agents read it directly. Other agents get
a thin pointer to it, never a second copy of the rules, so the files cannot drift apart.

| Situation | Do this |
|---|---|
| Neither `AGENTS.md` nor `CLAUDE.md` exists | Create `AGENTS.md` from what you learned, plus the section. |
| Only `AGENTS.md` exists | Add the section to `AGENTS.md`. |
| Only `CLAUDE.md` exists, the team uses only Claude Code | Add the section to `CLAUDE.md`. |
| Only `CLAUDE.md` exists, the team uses other agents too | Ask before moving it: propose moving its content to `AGENTS.md` and leaving `@AGENTS.md` in `CLAUDE.md`. If the team declines, add the section to `CLAUDE.md` and create `AGENTS.md` with the section and a link to `CLAUDE.md`. |
| Both exist | Add the section to `AGENTS.md`, and make sure `CLAUDE.md` imports it with `@AGENTS.md`. |

Then add the pointer for each agent the team uses that does not read `AGENTS.md` by default:

| Agent | Pointer |
|---|---|
| Claude Code | `CLAUDE.md` containing `@AGENTS.md`. By default Claude Code reads `AGENTS.md` only when no `CLAUDE.md` or `CLAUDE.local.md` exists, so a repo with both silently drops `AGENTS.md` without the import. |
| Gemini CLI | `GEMINI.md` containing `@AGENTS.md`, or `"contextFileName": "AGENTS.md"` in `.gemini/settings.json`. |
| Any agent with its own rules file already in the repo (`.github/copilot-instructions.md`, `.cursor/rules/`, `.windsurfrules`) | One line in that file saying to read `AGENTS.md`, which holds the rules. |

Check the current behavior of an agent you are unsure about in its own documentation rather than
guessing; agents change which files they read.

### 8. Merge the configuration

- **`.gitignore`**: append the lines from `assets/snippets/gitignore.txt` that are missing.
- **Claude Code only, `.claude/settings.json`**: merge the hooks from
  `assets/adapters/claude-code/settings-hooks.json`. Read the existing file, append to existing
  `hooks.SessionStart` / `hooks.PreToolUse` arrays rather than replacing them, and keep the JSON
  valid. If the team declined hooks, skip this and delete the `.claude/hooks/` the adapter copied.
  The harness does not depend on hooks: `feature.py` seals task state and refuses to work after a
  hand edit, and the entry file tells every agent to run `init.sh` at session start.
- **Claude Code only, `.worktreeinclude`**: if the project needs gitignored files such as `.env`
  to run, list them so every worktree Claude Code creates gets a copy. For plain
  `git worktree add`, mention those files in `harness/README.md` so people copy them.

### 9. Prove it once

Run `bash scripts/harness/init.sh` and `python3 scripts/harness/check_architecture.py` and report
the real result. If something fails because of the project (not the harness), say so plainly and
leave it as the first entry in the report; do not loosen a rule or delete a command to make it
green. Then do the fresh-session test from `references/principles.md`: answer the five questions
using only the files, and fix any you cannot answer.

### 10. Report

Tell the user, briefly:

- What was created, what was merged, and what was skipped because it already existed
- The commands per layer and where each came from
- Every `TODO(confirm)` and every assumption you made
- The init/verification result, including failures
- If this skill itself was installed into the repository (`.agents/skills/harness-bootstrap/` or
  another agent's skills folder, plus `skills-lock.json`), say so: the team does not need it after
  the bootstrap, and it can be removed or kept for re-running later. Do not remove it yourself.
- Next step: review and commit the bootstrap on a branch, then start a task with the
  `harness-start` skill (in agents with slash commands, `/harness-start <TASK-ID>`)

Do not commit or push unless the user asks.

## Design rules for adapting the scaffold

- Prefer the project's existing tools. If the repo has a `Makefile` with `make check`, put
  `make check` in `config.sh` instead of re-listing its parts.
- Keep runtime dependencies to `bash`, `git` and `python3` (standard library only). Do not add
  packages to the project for the harness.
- Error messages from any harness script say what failed, why, and how to fix it.
- Nothing destructive in scripts. Cleanup only reports; humans or agents act on the report.
- Make the harness smaller when you can. A component that does not change agent behavior on this
  repo is overhead; say so instead of installing it for completeness.
