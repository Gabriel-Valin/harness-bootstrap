---
name: harness-start
description: >-
  Start or resume work on one task (feature, bug, chore) in a repository that has the agent
  harness (scripts/harness/, harness/). Creates the local task state in .harness/tasks/<TASK-ID>/,
  writes the scope contract, turns the done criteria into verifiable items, records a failing
  baseline and runs init. Use it whenever someone begins a task, picks up a ticket or issue,
  takes over a branch from a teammate, or says "let's work on X", even without naming the skill.
argument-hint: <TASK-ID> [issue link or description]
---

# Start a harness task

The goal is that coding starts only after three things exist: an agreed scope, done criteria
that a command can check, and proof that those checks fail today. Agreement is cheapest now;
every misunderstanding found later costs a rework cycle.

Arguments: `$ARGUMENTS` (task id first, then an optional link or description).

## 1. Place the work

- Run `git status --short` and `git rev-parse --abbrev-ref HEAD`.
- One task = one branch = one worktree. If this session is on the base branch or on another
  task's branch, propose an isolated worktree (`claude --worktree <TASK-ID>`, or the
  `EnterWorktree` tool when available) or a new branch that follows the naming convention in the
  entry file. Do not mix two tasks in one checkout: their state and diffs would collide.
- If `.harness/tasks/<TASK-ID>/` already exists here, this is a **resume**: read `handoff.md`,
  `contract.md` and `progress.md`, run `bash scripts/harness/init.sh`, report the state, and skip
  to step 6.

## 2. Gather the task

Get the real requirements rather than inventing them:

- An issue tracker reachable through an available tool (for example `gh issue view`, a tracker
  MCP connector), or the link the user gave.
- Otherwise ask the user to paste the description and acceptance criteria.
- When **taking over** from someone, also read their shared handoff (PR description or comments,
  tracker comments), `git log <base>..HEAD` and the diff. Rebuild state from those.

Read the parts of `docs/` and the entry file that cover the affected area.

## 3. Create the state

```bash
python3 scripts/harness/feature.py init <TASK-ID> --title "<short title>"
```

## 4. Write the contract

Fill `.harness/tasks/<TASK-ID>/contract.md`: goal, in scope, **out of scope** (name the tempting
neighbours: refactors, related bugs), done criteria, required verification layers, risks.
Cross-component changes require the end-to-end layer.

## 5. Turn done criteria into items

Each item is one observable behavior plus an exact command that proves it:

```bash
python3 scripts/harness/feature.py add --id F1 \
  --behavior "POST /reset-password returns 202 and queues an email" \
  --verify "npm test -- reset-password.e2e"
```

Guidelines:

- **Granularity**: each item fits in one session. "User can add an item to the cart" is right;
  "implement the cart" is too big; "add a field to the model" is too small.
- **For bugs**, the first item is a reproduction as close to the user's experience as possible
  (an end-to-end or integration test that shows the failure), and the fix items depend on it.
- **The command must fail without the change.** If the test does not exist yet, the command names
  the test you will write; it fails today because the test is missing, and that is fine.
- Use `--depends` to order items. Prefer existing test runners; add a filtering argument so the
  command runs only what the item needs.
- **Filters can silently change what runs.** `pnpm test -- <file>` forwards a literal `--` to the
  runner, which can drop the file filter and run other tests, and exit 0. Use the runner's direct
  form, for example `pnpm vitest run --project unit <file>`, and check that it fails when the file is
  missing (rename the file and run the command). `feature.py verify` rejects a run that executes
  zero tests, but it cannot detect a filter that runs the wrong tests.
- `verification` is a promise: once work starts, changing it needs the human's agreement and a
  line in `progress.md` explaining why. Change it with `feature.py set-verify <ID> --verify "..."
  --reason "..."`, which works at any WIP level and keeps the old command in the history.

## 6. Record the baseline

- Run `bash scripts/harness/init.sh`. If the branch is already red before you change anything,
  record the failing layer in `progress.md` under Baseline and tell the user; do not silently build
  on a broken state.
- Run `python3 scripts/harness/feature.py verify <ID>` for each item once. They should fail now, and
  the log must show a failure about the missing behavior or test, not about the harness or setup.
  An item that already passes proves nothing: fix its command with `feature.py set-verify <ID>
  --verify "..." --reason "baseline passed: <why>"`, or drop it with the user using
  `feature.py remove <ID> --reason "..."`. Then verify again until each item fails for the right reason.
- Note the baseline results in `progress.md`.

## 7. Confirm and start

Show the user the contract and the item list (`python3 scripts/harness/feature.py status`) and ask
for confirmation or corrections before writing code. Then:

```bash
python3 scripts/harness/feature.py next
python3 scripts/harness/feature.py start <ID>
```

## Working rules until the task ends

- One active item. Finish and verify it before starting the next; if stuck, block it with a reason.
- An item becomes passing only through `feature.py verify`. Never edit status, evidence or history.
- Do not "also fix" things outside the contract. Note them in `progress.md` as follow-ups.
- No refactoring until the current item's behavior is verified.
- Run `bash scripts/harness/verify.sh` before claiming anything works; report failures with the
  real output.
- Before saying the task is done, run the `harness-evaluate` skill in a separate context and
  address REVISE findings.
- End every session with `/harness-handoff`.
