# Evaluator rubric

Used by the `harness-evaluator` subagent and by human reviewers. Score every dimension from
evidence you observed (a command you ran, a line you read), never from the author's summary.

## Scale

- 5: fully meets the contract, verified end to end, nothing to fix
- 4: meets it; minor issues that do not affect behavior
- 3: core works, but there are real gaps (an untested path, a weak check)
- 2: partially works; a contract item is missing, stubbed or only works under mocks
- 1: does not work, or cannot be verified

## Dimensions

| Dimension | What 5 looks like | Typical evidence |
|---|---|---|
| Contract coverage | Every "Done when" line is implemented, nothing out of scope was added | `contract.md` vs diff |
| Verified behavior | Each item passes its own command, rerun by you, and the command really exercises the behavior | `feature.py verify`, reading the test |
| End-to-end | The real application runs the user flow; no stubs, fake data or hard-coded results | `verify.sh`, smoke/e2e output, running the app |
| Tests | New behavior has tests that would fail without the change; edge and error paths covered | tests in the diff, a mutation spot check |
| Architecture | No boundary violations; follows existing patterns instead of inventing parallel ones | `check_architecture.py`, reading the diff |
| Error handling and observability | Failures surface with useful messages and logs; nothing swallowed | error paths in the diff, logs from a failing run |
| Clean state | Checklist passes; no debug code, no stray files; handoff and progress are accurate | `cleanup-scan.sh`, the state files |

## Verdict

- **PASS** only if every dimension scores 4 or more.
- **REVISE** otherwise. List findings ordered by severity, each with: what is wrong, the evidence,
  and the concrete fix (file and change).

Be skeptical by default. The author already believes it works; your value is finding where it
does not. Look especially for: features that are presentational only, happy-path-only tests,
mocks hiding integration bugs, verification commands that would pass even without the change,
and "done" claims without logs.
