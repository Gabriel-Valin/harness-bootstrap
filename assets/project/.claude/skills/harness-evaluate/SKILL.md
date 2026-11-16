---
name: harness-evaluate
description: >-
  Independent, skeptical check of a harness task before it is called done. Use it before declaring
  a task done, before opening a PR, or whenever an agent claims a feature works. It reruns the
  verification, reads the diff against the task contract and scores the work with
  harness/evaluator-rubric.md. It never edits code; it returns a PASS or REVISE verdict with
  evidence and concrete fixes.
---

# Evaluate a harness task

The agent that wrote the code grades it generously. This check is useful only to the extent that
it runs **apart from that agent** and finds where the work is not done.

## Run it in a separate context

Pick the first option your environment supports:

1. **A subagent or delegated task** with read-only intent (in Claude Code, the
   `harness-evaluator` subagent). Give it only the task id and these instructions, not your own
   opinion of the work.
2. **A fresh session** of any coding agent in the same worktree, asked to use the
   `harness-evaluate` skill.
3. **The same session**, only as a last resort. Say in the report that the evaluation was not
   independent, and read every file again instead of relying on what you remember.

Whoever invoked the evaluation saves the report to
`.harness/tasks/<TASK-ID>/runs/eval-<UTC timestamp>.md`.

## Rules for the evaluator

Assume nothing you have not observed. Do not modify source files, tests, the contract or the
rubric, and do not fix anything: the author fixes, you verify. Running the project's commands and
`python3 scripts/harness/feature.py verify <ID>` is fine, because that only records evidence.

## Inputs

The current task id is in `.harness/current` (or `HARNESS_TASK`). Read, in this order:

1. `.harness/tasks/<TASK-ID>/contract.md`: what was agreed. This is the standard you grade against.
2. `.harness/tasks/<TASK-ID>/feature_list.json`: items, their verification commands and evidence.
3. `harness/evaluator-rubric.md`: the dimensions, scale and verdict rule.
4. The diff: `git diff $(git merge-base HEAD <base>)` where `<base>` comes from
   `harness/config.sh` (`HARNESS_BASE_BRANCH`) or `origin/HEAD`.
5. `docs/ARCHITECTURE.md` and the entry file for the boundaries the change must respect.

## What to do

1. Run `python3 scripts/harness/feature.py validate`. A broken seal, a missing evidence log or a log
   changed after its run means the state cannot be trusted: report it as a blocker.
2. Run `bash scripts/harness/verify.sh` and record the real result per layer. A layer reported as
   UNVERIFIED counts as not proven.
3. For each item, read its verification command and the test or script behind it. Ask: would this
   command fail if the change were reverted? If not, the item is not really verified. Then rerun it
   with `python3 scripts/harness/feature.py verify <ID>`.
4. Exercise the behavior the way a user would when a smoke or e2e command exists or the contract
   describes a user flow: start the app, call the endpoint, run the CLI. Report what you saw.
5. Read the diff for: stubs and hard-coded results, presentational-only features, swallowed
   errors, tests that only cover the happy path, mocks that hide integration, out-of-scope changes,
   pattern drift from the surrounding code, leftover debug code.
6. Run `python3 scripts/harness/check_architecture.py` and `bash scripts/harness/cleanup-scan.sh`.

## Output

Return exactly this structure:

```
VERDICT: PASS | REVISE
INDEPENDENT: yes (subagent | fresh session) | no (same session)

SCORES
- Contract coverage: n/5 - evidence
- Verified behavior: n/5 - evidence
- End-to-end: n/5 - evidence
- Tests: n/5 - evidence
- Architecture: n/5 - evidence
- Error handling and observability: n/5 - evidence
- Clean state: n/5 - evidence

FINDINGS (most severe first)
1. [severity] what is wrong
   Evidence: command output, file:line
   Fix: the concrete change, naming files

COMMANDS RUN
- command -> result
```

PASS requires every score at 4 or more. When in doubt between two scores, choose the lower and
say what evidence would raise it.
