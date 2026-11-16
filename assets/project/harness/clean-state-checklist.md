# Clean-state checklist

A session is done only when its task work is verified **and** this checklist passes. The next
session should be able to start coding immediately, not fight fires.

## 1. Build and checks

- [ ] `bash scripts/harness/verify.sh` passes (or the failure is recorded in handoff.md with the
      real error and is not caused by this session)
- [ ] No check was weakened, skipped or deleted to get a pass

## 2. Task state

- [ ] Every item marked `passing` got there through `feature.py verify` (evidence points to a log)
- [ ] At most one item is `active`
- [ ] `python3 scripts/harness/feature.py validate` passes

## 3. Recorded progress

- [ ] `progress.md` has an entry for this session, including decisions and their reasons
- [ ] `handoff.md` was rewritten: state, active item, exact next action, blockers

## 4. No stray artifacts

- [ ] `bash scripts/harness/cleanup-scan.sh` is clean: no debug code, no conflict markers, no
      untracked leftovers
- [ ] Temporary files, scratch scripts and test data created this session are gone

## 5. Startup path works

- [ ] `bash scripts/harness/init.sh` succeeds from this state
- [ ] Completed work is committed in atomic commits; abandoned attempts are reverted, not left
      half-applied

## Before the task closes (merge or hand-over)

- [ ] Decisions that outlive the task are in `docs/decisions/`
- [ ] The PR description lists each item with its verification command and result
- [ ] Regression checks live in the test suite, not only in `.harness/`
- [ ] Docs affected by the change (`docs/ARCHITECTURE.md`, `docs/PRODUCT.md`, entry file) are updated
