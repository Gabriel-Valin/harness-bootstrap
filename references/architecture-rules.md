# Writing architecture rules

`harness/architecture-rules.json` turns boundaries from the docs into checks that fail with
instructions. `scripts/harness/check_architecture.py` evaluates them line by line over tracked and
untracked (not ignored) files.

## Format

```json
{
  "exclude": ["node_modules/**", "dist/**", "build/**", "vendor/**", "**/*.min.js"],
  "rules": [
    {
      "id": "ui-no-database",
      "description": "UI code never talks to the database directly",
      "paths": ["src/ui/**", "src/components/**"],
      "allow": ["src/ui/**/*.stories.tsx"],
      "forbid": "from ['\"][./]*(db|database|prisma)['\"/]",
      "why": "The UI runs in the browser and must stay storage-agnostic; DB access lives in the service layer.",
      "fix": "Call the matching function in src/services/ (add one if missing) and import that instead."
    }
  ]
}
```

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Stable kebab-case name, shown in errors |
| `description` | yes | One line, human readable |
| `paths` | yes | Globs (relative to repo root) the rule applies to. `*` also matches `/` |
| `allow` | no | Globs exempted from the rule |
| `forbid` | yes | Python regular expression, matched against each line |
| `why` | yes | The reason, so the agent understands rather than just complies |
| `fix` | yes | Concrete repair instruction: where the code should go and how to call it |

Top-level `exclude` applies to every rule.

## Guidelines

- **Encode invariants, not implementations.** "Handlers do not import the ORM" is good. "Use
  library X for validation" belongs in docs, not in a check.
- **One boundary per rule.** Small rules give precise messages.
- **Write `fix` for an agent.** Name the target directory or module and the call pattern. A good
  test: an agent reading only the error message can make the change.
- **Match imports, not prose.** Anchor regexes on import syntax (`^\s*import`, `from '...'`,
  `require\(`, `use crate::`) so comments and strings rarely trip them.
- **Prefer existing linters.** If ESLint, dependency-cruiser, import-linter, ArchUnit or similar
  already enforce a boundary, run that tool in `HARNESS_STATIC_CMDS` and skip the duplicate rule.
- **Start with the two or three boundaries that actually get violated.** Add more through
  `/harness-cleanup` when review feedback repeats.

## Common examples

| Boundary | `paths` | `forbid` |
|---|---|---|
| Browser code uses no Node core modules | `src/renderer/**` | `^\s*(import .* from |const .*= require\()['"](node:)?(fs|path|os|child_process)['"]` |
| Domain layer has no framework imports | `src/domain/**` | `from ['"](express|@nestjs|next)` |
| Packages never import apps (monorepo) | `packages/**` | `from ['"](\.\./)+apps/` |
| Python handlers do not import the ORM | `app/api/**` | `^\s*(from|import) (sqlalchemy|app\.db)` |
| Go: `pkg/` must not import `cmd/` | `pkg/**` | `"[^"]*/cmd/` |
| Rust: core crate stays IO-free | `crates/core/**` | `use (std::fs|tokio::fs|reqwest)` |
