---
name: harness-cleanup
description: >-
  Periodic maintenance loop for a repository with the agent harness: full verification, cleanup
  and architecture scans, an evidence-based update of harness/quality-document.md, promotion of
  repeated review feedback into executable checks, an audit of the entry file and docs for stale
  or bloated rules, and a proposal for harness components that can be simplified. Use it on a
  schedule (for example weekly), when agent output quality seems to be degrading, when sessions
  take long to get started, or when someone asks to "clean up the harness" or "pay down debt".
---

# Harness cleanup loop

Entropy is the default: agents copy whatever patterns they find, so small messes compound.
This loop reduces it on a regular cadence and keeps the harness itself honest and lean. Work on a
dedicated branch from the base branch; the output is one reviewable PR.

## 1. Measure

- `bash scripts/harness/init.sh` and `bash scripts/harness/verify.sh`: record results per layer,
  including flaky tests (rerun failures once; a test that flips is flaky, record it).
- `python3 scripts/harness/check_architecture.py`
- `bash scripts/harness/cleanup-scan.sh`
- Time a fresh start: how long `init.sh` takes, and whether a fresh session can answer the five
  questions (what, how organized, how to run, how to verify, where are we) from the files alone.

## 2. Update the quality document

Edit `harness/quality-document.md`: one row per module, graded only from evidence gathered above
(failing or flaky tests, violations, missing docs, code that is hard to follow). Use `unknown`
where you have no evidence. List the lowest-graded modules first; they are the next cleanup
targets.

## 3. Promote feedback into checks

Look at recent review comments and fix commits (`git log --since=...`, PR comments through an
available tool). Any problem that appeared twice becomes executable:

- a boundary -> a rule in `harness/architecture-rules.json` with `why` and `fix`
- a pattern -> a lint rule in the project's linter, wired into `HARNESS_STATIC_CMDS`
- a debug habit -> `HARNESS_DEBUG_PATTERNS`
- a missing test category -> a test, or a line in the evaluator rubric

Only when a rule cannot be made executable does it go into the entry file or docs.

## 4. Audit instructions

- Entry file: still under ~200 lines? Rules without a reason, contradictory rules, rules for code
  that no longer exists? Move topic detail into `docs/`. Put the hard constraints at the top.
- `docs/`: anything out of date with the code? Stale docs are worse than none because they send
  agents the wrong way confidently. Fix or delete.

## 5. Propose simplifications

Each harness component exists to compensate for something the model could not do reliably. Pick
one component that may no longer be needed (for example a rule nobody violates, a doc nobody
reads, a checklist line that is always satisfied) and propose a trial: disable it for a few
representative tasks and compare results. Record the proposal, and later the outcome, in the
"Harness changes log" of the quality document. Do not remove components without that evidence.

## 6. Deliver

Fix the small, mechanical problems found (dead code flagged by tools, doc drift, missing rules).
Leave larger refactors as follow-up tasks with a short description each. Open or propose one PR
with the changes and a summary of the measurements. Ask before pushing.
