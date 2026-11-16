# Discovering how a project runs

Goal: for each verification layer, a command that works from the repo root, plus where you found
it. Prefer evidence in this order, strongest first:

1. **CI configuration**: `.github/workflows/*.yml`, `.gitlab-ci.yml`, `.circleci/config.yml`,
   `azure-pipelines.yml`, `Jenkinsfile`, `bitbucket-pipelines.yml`, `.buildkite/`. What CI runs is
   what the team trusts.
2. **Task runners**: `Makefile`, `justfile`, `Taskfile.yml`, `package.json` scripts, `tox.ini`,
   `noxfile.py`, `Rakefile`, `build.gradle(.kts)`, `pom.xml`, `mix.exs` aliases.
3. **Hooks**: `.husky/`, `.pre-commit-config.yaml`, `lefthook.yml`.
4. **Docs**: `README`, `CONTRIBUTING`, existing instruction files.
5. **Ecosystem defaults** (below), only when nothing above exists. Mark these as assumptions.

If the repo is a monorepo (workspaces, `turbo.json`, `nx.json`, `pnpm-workspace.yaml`, Cargo
workspace, Go multi-module, Bazel), prefer the root-level orchestrated command (`turbo run lint`,
`nx affected`, `cargo test --workspace`) so `verify.sh` covers everything, and note the per-package
variant in `docs/RELIABILITY.md` for faster local loops.

## Package manager and runtime pinning

| Signal | Means |
|---|---|
| `package-lock.json` / `yarn.lock` / `pnpm-lock.yaml` / `bun.lockb` | npm / yarn / pnpm / bun. Use the matching install (`npm ci`, `yarn install --frozen-lockfile` or `yarn install --immutable` for Yarn 2+, `pnpm install --frozen-lockfile`, `bun install --frozen-lockfile`) |
| `packageManager` field in `package.json` | Exact manager and version (Corepack) |
| `.nvmrc`, `.node-version`, `.tool-versions`, `.python-version`, `rust-toolchain.toml`, `go.mod` `go` line | Runtime version to state in the entry file |
| `poetry.lock` / `uv.lock` / `Pipfile.lock` / `requirements*.txt` | poetry / uv / pipenv / pip |
| `Gemfile.lock`, `composer.lock`, `mix.lock`, `go.sum`, `Cargo.lock` | bundler, composer, mix, go modules, cargo |
| `Dockerfile`, `docker-compose.yml`, `devcontainer.json` | Services the app needs to run; the smoke layer may depend on them |

## Ecosystem defaults (last resort)

| Stack | Setup | Static | Test | Notes |
|---|---|---|---|---|
| Node/TS | lockfile install | `<pm> run lint`, `<pm> run typecheck` or `npx tsc --noEmit` | `<pm> test` | Check that scripts exist before using them |
| Python | `uv sync` / `poetry install` / `pip install -e .[dev]` | `ruff check .`, `mypy .` | `pytest -q` | |
| Go | `go mod download` | `go vet ./...`, `gofmt -l .` (fails if output) | `go test ./...` | `test -z "$(gofmt -l .)"` makes gofmt fail properly |
| Rust | `cargo fetch` | `cargo clippy --all-targets -- -D warnings`, `cargo fmt --check` | `cargo test` | |
| JVM | `./gradlew assemble` / `mvn -q -DskipTests package` | `./gradlew check -x test` | `./gradlew test` / `mvn test` | Use the wrapper if present |
| Ruby | `bundle install` | `bundle exec rubocop` | `bundle exec rspec` / `rails test` | |
| PHP | `composer install` | `vendor/bin/phpstan`, `vendor/bin/php-cs-fixer fix --dry-run` | `vendor/bin/phpunit` | |
| .NET | `dotnet restore` | `dotnet format --verify-no-changes` | `dotnet test` | |
| Elixir | `mix deps.get` | `mix format --check-formatted`, `mix credo` | `mix test` | |

## Smoke and end-to-end layers

- **Smoke** proves the real thing starts: a CLI `--help` or `--version`, a server started in the
  background with a health check (`curl -fsS localhost:PORT/health`) and then stopped, a build of
  a desktop or mobile app. Keep it under a minute. If starting the app needs services (database,
  queue), say so in `docs/RELIABILITY.md` and reuse the repo's own compose file.
- **E2E** drives a user flow through the deployed shape of the system, from outside the process:
  Playwright, Cypress, Detox, Maestro, an HTTP scenario script against the started server, a CLI
  golden-output test against the built binary. Look for `e2e/`, `tests/e2e`,
  `playwright.config.*`, `cypress.config.*`.
  - **Do not relabel existing tests as E2E.** Integration tests that already run in the test layer
    (for example API tests that start the app in-process, or call handlers with a test database)
    are tests, not E2E, even when they speak HTTP. Putting the same command in both layers makes
    `verify.sh` report a layer as proven that adds no evidence, which is exactly what the harness
    exists to prevent.
  - If no real E2E exists, leave `HARNESS_E2E_CMDS` empty, add `TODO(confirm)` in the report, and
    suggest that the first task in this repo be "add a minimal E2E flow". An empty layer is
    reported honestly as not configured; a duplicated one lies.

## Architecture boundaries

Look for:

- Directory layering: `ui/` `api/` `domain/` `infra/`, `controllers/` `services/` `repositories/`,
  `main/` `preload/` `renderer/`, `app/` `lib/` `components/`, `cmd/` `internal/` `pkg/`.
- Existing enforcement: `eslint-plugin-boundaries`, `import/no-restricted-paths`,
  `dependency-cruiser`, `import-linter` (Python), ArchUnit, Go `internal/` packages, Nx module
  boundaries. If one exists, call it from `HARNESS_STATIC_CMDS` instead of duplicating its rules in
  `architecture-rules.json`.
- Cross-workspace imports in monorepos (packages importing apps).
- Rules in docs or review comments ("never call the DB from handlers").

Confirm inferred boundaries with the user before encoding them; a wrong rule teaches the agent the
wrong architecture.

## Debug patterns per stack

Used by `cleanup-scan.sh` on added lines only. Combine with `|`:

- JS/TS: `console\.log\(|debugger;?$|\.only\(`
- Python: `breakpoint\(\)|pdb\.set_trace|^\s*print\(` (only if the project does not use print for output)
- Ruby: `binding\.pry|byebug`
- Go: `fmt\.Print(ln|f)?\("DEBUG`
- Rust: `dbg!\(`
- Any: `TODO\(harness\)|XXX DEBUG`
