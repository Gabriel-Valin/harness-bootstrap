#!/usr/bin/env bash
# e2e.sh - install the harness into throwaway git repositories and check that it works.
#
# Usage: bash tests/e2e.sh
# Needs bash, git and python3. Exits non-zero on the first failed check.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

new_repo() {
  local dir="$WORK/$1"
  mkdir -p "$dir"
  git -C "$dir" init -q
  git -C "$dir" -c user.name=e2e -c user.email=e2e@example.invalid commit -q --allow-empty -m init
  echo "$dir"
}

echo "== unit tests"
python3 -B "$SKILL_DIR/assets/project/scripts/harness/test_feature.py"

echo "== install with symlinked mirrors and the Claude Code adapter"
repo="$(new_repo linked)"
bash "$SKILL_DIR/scripts/install.sh" "$repo" --agents claude-code,codex,devin >/dev/null
for skill in harness-start harness-handoff harness-cleanup harness-evaluate; do
  [ -f "$repo/.agents/skills/$skill/SKILL.md" ] || fail "canonical $skill missing"
  for dir in .claude/skills .devin/skills; do
    [ -L "$repo/$dir/$skill" ] || fail "$dir/$skill is not a symlink"
    [ -f "$repo/$dir/$skill/SKILL.md" ] || fail "$dir/$skill does not resolve"
  done
done
[ -f "$repo/.claude/agents/harness-evaluator.md" ] || fail "Claude Code adapter not copied"
[ -x "$repo/scripts/harness/init.sh" ] || fail "scripts are not executable"
[ ! -e "$repo/.windsurf" ] || fail "mirror created for an agent that was not requested"

echo "== install never overwrites"
echo "team version" > "$repo/harness/config.sh"
out="$(bash "$SKILL_DIR/scripts/install.sh" "$repo" --agents claude-code)"
grep -q "SKIPPED  harness/config.sh" <<<"$out" || fail "existing file not reported as skipped"
[ "$(cat "$repo/harness/config.sh")" = "team version" ] || fail "existing file was overwritten"
cp "$SKILL_DIR/assets/project/harness/config.sh" "$repo/harness/config.sh"

echo "== init passes the file and mirror checks"
(cd "$repo" && bash scripts/harness/init.sh >"$WORK/init.log" 2>&1) || true
grep -q "\[2/4\] Setup" "$WORK/init.log" || { cat "$WORK/init.log"; fail "init stopped at the file checks"; }

echo "== task state is sealed"
(
  cd "$repo"
  python3 scripts/harness/feature.py init E2E-1 --title e2e >/dev/null
  python3 scripts/harness/feature.py add --id F1 --behavior "works" --verify true >/dev/null
  python3 scripts/harness/feature.py start F1 >/dev/null
  python3 scripts/harness/feature.py verify F1 >/dev/null
  python3 scripts/harness/feature.py validate >/dev/null
  list=.harness/tasks/E2E-1/feature_list.json
  python3 - "$list" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data["items"][0]["history"] = []
json.dump(data, open(path, "w"))
PY
  if python3 scripts/harness/feature.py status >/dev/null 2>&1; then
    echo "FAIL: a hand edit of history was accepted" >&2
    exit 1
  fi
  python3 scripts/harness/feature.py recover --reason e2e >/dev/null
  status="$(python3 scripts/harness/feature.py status)"
  grep -q "passing 0 / 1" <<<"$status" || { echo "FAIL: recover kept a passing item" >&2; exit 1; }
)

echo "== copied mirrors report drift"
repo="$(new_repo copied)"
bash "$SKILL_DIR/scripts/install.sh" "$repo" --agents windsurf --copy >/dev/null
if [ ! -d "$repo/.windsurf/skills/harness-start" ] || [ -L "$repo/.windsurf/skills/harness-start" ]; then
  fail "--copy did not create a plain directory"
fi
echo "drift" >>"$repo/.windsurf/skills/harness-start/SKILL.md"
if (cd "$repo" && bash scripts/harness/init.sh >"$WORK/drift.log" 2>&1); then
  fail "init passed with a drifted mirror"
fi
grep -q "DRIFT    .windsurf/skills/harness-start" "$WORK/drift.log" || fail "drift not reported"

echo "== bad input is rejected"
if bash "$SKILL_DIR/scripts/install.sh" "$repo" --agents not-an-agent >/dev/null 2>&1; then
  fail "unknown agent accepted"
fi
if bash "$SKILL_DIR/scripts/install.sh" "$WORK" >/dev/null 2>&1; then
  fail "a directory outside git was accepted"
fi

echo "PASS: all end-to-end checks"
