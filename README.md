# harness-bootstrap

An [Agent Skill](https://agentskills.io) that turns any git repository into one where coding
agents can work across sessions, worktrees and people without forgetting where they stopped, and
without calling something "done" before a script proves it.

It works with any agent that supports Agent Skills: Claude Code, Codex, Cursor, GitHub Copilot,
Gemini CLI, OpenCode, Pi, Devin, Windsurf, Kiro and others.

## Install

```bash
npx skills add Gabriel-Valin/harness-bootstrap -g
```

The [`skills` CLI](https://github.com/vercel-labs/skills) detects your agents and installs the skill
where each one reads it. `-g` installs it for your user, which fits a skill you run once per
repository; leave it out to install into the current project only. `-a <agent>` picks agents, and
`@<tag>` pins a version (`npx skills add Gabriel-Valin/harness-bootstrap@v1.0.0 -g`).

Then, in a repository, ask your agent to **set up the agent harness** (or invoke
`/harness-bootstrap` in agents with slash commands).

## What it installs in your repository

The skill reads the repo first, asks only what it cannot find out (for example which agents your
team uses), and never overwrites a file you already have.

| Layer | Where | Committed |
|---|---|---|
| Entry file | `AGENTS.md`, plus pointers such as `CLAUDE.md` for agents that need one | yes |
| Docs | `docs/ARCHITECTURE.md`, `PRODUCT.md`, `RELIABILITY.md`, `docs/decisions/` | yes |
| Contract | `harness/`: commands per verification layer, architecture rules, checklist, rubric | yes |
| Verification | `scripts/harness/`: `init.sh`, `verify.sh`, `feature.py`, `check_architecture.py`, `cleanup-scan.sh` | yes |
| Lifecycle skills | `.agents/skills/harness-{start,handoff,cleanup,evaluate}`, mirrored for agents that read another folder | yes |
| Agent adapters | Optional extras, for example a subagent and hooks for Claude Code | yes |
| Task state | `.harness/tasks/<TASK-ID>/`: feature list, contract, progress, handoff, run logs | no |

Day to day, your agent uses four skills that ship inside the repository, so every teammate gets
them on clone:

- **harness-start**: agree on scope, turn the done criteria into items with exact verification
  commands, and record that they fail before any code is written.
- **harness-handoff**: verify, clean up and write a handoff that the next session (or teammate)
  can resume from with nothing but the repo.
- **harness-evaluate**: an independent, skeptical check, run in a subagent or a fresh session,
  before anything is called done.
- **harness-cleanup**: periodic maintenance that turns repeated review feedback into executable
  checks.

## Guarantees that do not depend on your agent

- An item becomes `passing` only by running its verification command through `feature.py`. The
  task state is sealed on every save, so a hand edit makes every command refuse to work until
  `feature.py recover` sends the passing items back to be verified again. Evidence logs are
  hashed.
- Verification that runs zero tests or skips tests counts as a failure, not a pass.
- Agent-specific hooks (Claude Code today) only catch hand edits earlier. The harness works
  without them.

The seal detects edits; it is not a security boundary. That is why the evaluator reruns every
verification instead of trusting stored evidence.

## Requirements

`git`, `bash` and `python3` (standard library only) on the machine running the agent. Nothing is
added to your project's dependencies.

On Windows, the skill mirrors use symlinks by default. Enable `core.symlinks` in git, or have the
agent install with `--copy`; `init.sh` reports copies that drift from the canonical skills.

## Repository layout

```
SKILL.md            instructions the agent follows to bootstrap a repository
references/         background the agent reads on demand
scripts/install.sh  copies the scaffold, never overwrites, mirrors skills per agent
assets/project/     the portable scaffold copied into your repository
assets/adapters/    optional per-agent extras (claude-code/)
assets/snippets/    text the agent merges into existing files
tests/e2e.sh        installs into throwaway repositories and checks the result
```

## Development

```bash
bash tests/e2e.sh                                     # unit + end-to-end checks
uvx --from skills-ref agentskills validate "$PWD"     # Agent Skills spec (folder must be named harness-bootstrap)
npx skills add "$PWD" --list                          # what the CLI will install
```

To try local changes in an agent, install from your checkout: `npx skills add ./harness-bootstrap`.

## License

[Apache-2.0](LICENSE). See [NOTICE](NOTICE).
