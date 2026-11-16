# Principles behind the harness

Distilled from the Learn Harness Engineering course (lectures 1-12), the Anthropic articles on
long-running agent harnesses, and the OpenAI harness engineering write-up. Use this to explain
choices to the user or to adapt the scaffold to a repo it does not fit.

## Contents

1. What a harness is
2. Why each artifact exists
3. Rules that make it work
4. Team model: contract vs state
5. The fresh-session test
6. Known failure modes of harnesses themselves

## 1. What a harness is

Everything around the model that is not the model: instructions, tools, environment, state, and
feedback. When an agent fails on a task a capable model should handle, attribute the failure to
one of five layers before blaming the model: unclear task, missing context, broken environment,
missing verification, lost state. Fix that layer, rerun, repeat.

## 2. Why each artifact exists

| Artifact | Failure it prevents |
|---|---|
| Entry file (short) | Agent guessing conventions; giant instruction files that bury rules in the middle and eat context |
| `docs/ARCHITECTURE.md` | Agent copying whatever pattern it sees first; boundary drift |
| `docs/PRODUCT.md` | Agent inventing scope from a one-line request |
| `docs/RELIABILITY.md` | Agent debugging blind: no idea where logs are or what a healthy run looks like |
| `docs/decisions/` | Next session re-deciding (differently) what was already decided, or "optimizing away" a deliberate choice |
| `init.sh` | Every session burning context rediscovering how to install and run |
| `verify.sh` (layered) | "Unit tests pass" being mistaken for "it works" |
| `check_architecture.py` | Boundaries existing only on paper |
| `feature_list.json` per task | "Mostly done" with no definition of done; overreach across many half-finished items |
| `feature.py verify` (gating) | Agent marking its own work as passing |
| `contract.md` | Generator and evaluator disagreeing about what was asked |
| `progress.md` | Losing the "why" of decisions across sessions |
| `handoff.md` | Next session (or next person) starting cold |
| `clean-state-checklist.md` | Sessions ending with red builds, debug code, stale state |
| `evaluator-rubric.md` + evaluator subagent | Self-evaluation bias: the same model that wrote the code grades it generously |
| `quality-document.md` | Not knowing which modules are degrading |
| `cleanup-scan.sh` + `/harness-cleanup` | Entropy: agents copy existing mess, so mess compounds |

## 3. Rules that make it work

- **WIP = 1.** One active item at a time. Attention split across k tasks gives each C/k; below a
  threshold none finish. `feature.py start` refuses a second active item.
- **The triple.** Every item has an observable behavior, an exact verification command, and a
  state (`not_started`, `active`, `blocked`, `passing`). Missing any one makes it unusable.
- **Pass-state gating.** Only the verifier moves an item to `passing`, by running its command. The
  guard hook blocks hand edits of status and evidence. Evidence is command output, not prose.
- **Three verification layers.** Static (lint, types), runtime (tests, the app starts), system
  (end-to-end user flow). Stop at the first failing layer. Cross-component changes need the E2E
  layer; component boundary defects are invisible to unit tests by design.
- **Agent-oriented errors.** Every failure says what, why, and how to fix. This turns checks into a
  self-correcting loop.
- **A verification that already passes before the change proves nothing.** For bugs, the first
  item is a reproduction that fails now. Record the red baseline.
- **Separate worker and checker.** The evaluator is a different invocation with read-only intent,
  a rubric, and instructions to be skeptical.
- **Clean state is part of done.** Build passes, tests pass, progress recorded, no stray artifacts,
  standard startup works.
- **Promote review feedback into checks.** A comment made twice in review becomes a rule.
- **Simplify periodically.** Disable one component, rerun representative tasks; if nothing
  degrades, remove it. Harness components encode model weaknesses, and those change.

## 4. Team model: contract vs state

The course projects commit everything because they model one agent on one branch of a greenfield
project. With many developers and parallel tasks:

- **Contract (committed):** entry file, docs, `harness/`, `scripts/harness/`, `.claude/` skills,
  agents, hooks, settings. Changes go through PR so every agent obeys the same rules.
- **State (gitignored, `.harness/`):** per task, per worktree. One task = one branch = one worktree,
  so tasks never fight over one handoff file. Claude Code's worktree isolation blocks edits to the
  main checkout, which is why state lives inside each worktree, not in a central folder.
- **Durability:** before a task ends, promote what must survive: decisions to `docs/decisions/`,
  evidence to the PR description, regression checks to the test suite, handoff to the issue
  tracker when someone else will continue. After that, local state can be deleted. If a machine is
  lost, state is rebuilt from git log, the PR and the tracker.

## 5. The fresh-session test

Open a new session with no verbal context. Using only repo files, it must answer:

1. What is this system? (entry file, README)
2. How is it organized? (ARCHITECTURE.md, module docs)
3. How do I run it? (`init.sh`, `config.sh`)
4. How do I verify it? (`verify.sh`, layers in `config.sh`)
5. Where are we now? (`feature.py status`, `handoff.md`, git log)

Every question it cannot answer is a missing piece of the harness.

## 6. Known failure modes of harnesses themselves

The course's own capstone solution illustrates these; avoid them:

- State files claiming success that no command ever proved (a benchmark script that crashes while
  the quality document grades it A; `npm test` documented with zero test files).
- `evidence` written as a description of the code instead of the output of a check.
- An evaluator rubric filled in by the same agent that did the work.
- Checks that exist but are not wired into `init.sh`, `verify.sh` or the entry file, so nobody runs
  them.
- Counters incremented inside a pipe (a subshell), so failures are never counted.
- Two state files with overlapping content that drift apart.
