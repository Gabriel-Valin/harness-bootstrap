---
name: harness-handoff
description: >-
  End a work session cleanly in a repository with the agent harness: verify, run the cleanup
  scan, update progress.md and handoff.md for the current task, walk the clean-state checklist,
  and optionally share the handoff with a teammate or close the task. Use it whenever a session
  is ending, context is getting long, someone says "wrap up", "pause", "hand this over", "I'll
  continue tomorrow", or before switching to another task, even without naming the skill.
argument-hint: "[--share | --close]"
---

# Hand off a harness task

The next session (yours tomorrow, a teammate's, or a fresh context after compaction) starts with
no memory of this one. Everything it needs must be in files, and the repo must be in a state
where it can start coding immediately. Arguments: `$ARGUMENTS`.

Report honestly throughout. A red check reported with its real output is a good handoff; a green
claim without evidence is a bad one.

## 1. Verify

- `bash scripts/harness/verify.sh` (full). Note the result per layer.
- For the active item, if you believe it works: `python3 scripts/harness/feature.py verify <ID>`.
  If it fails, it stays active; record why.
- `python3 scripts/harness/feature.py status`

## 2. Clean up

- `bash scripts/harness/cleanup-scan.sh` and fix what it reports: debug code, conflict markers,
  stray files. Scratch files and temporary data created this session go away.
- Abandoned attempts are reverted, not left half-applied.

## 3. Commit completed work

Completed, verified work belongs in atomic commits with messages that say what and why. Follow
the repository's commit conventions and the user's instructions about committing; if you have no
standing permission, show the proposed commits and ask. Never bypass hooks.

## 4. Record

Append a session entry at the top of "Sessions" in `.harness/tasks/<TASK-ID>/progress.md`: items
worked on, what is done with its evidence (log paths), what failed with the real error,
decisions with their reasons (also add them to the Decisions table), and anything learned.

Rewrite `.harness/tasks/<TASK-ID>/handoff.md` completely from its template sections: state
(commit, clean or dirty tree, verify result), active item and the **exact next action**, blockers,
and "do not redo" (approaches already tried). Write it for a reader who has only the repo.

## 5. Walk the checklist

Go through `harness/clean-state-checklist.md` and tell the user which boxes are not satisfied and
why. Do not tick boxes you have not checked.

## 6. Share (`--share`)

For a teammate or another machine to continue:

- Push the branch (ask first unless the user already told you to).
- Publish the handoff where the team will see it: the PR description or a PR comment (a draft PR
  is fine), or the issue tracker through an available tool. If no tool is available, print the
  handoff in a form the user can paste.
- Include: branch, last commit, item list with states, the next action, blockers.

## 7. Close (`--close`)

When every item passes and the evaluator returned PASS:

- Promote durable knowledge: decisions to `docs/decisions/` (template `harness/templates/adr.md`),
  behavior or architecture changes to `docs/`, regression checks into the test suite.
- Draft the PR description: summary, each item with its verification command and result, the
  evaluator verdict, known limitations.
- Tell the user that `.harness/tasks/<TASK-ID>/` can be deleted after the merge (do not delete it
  yourself).

## 8. Report

Finish with a short summary: what is done (with evidence), what is not, the next action, and any
checklist items still open.
