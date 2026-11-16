#!/usr/bin/env bash
# install.sh - copy the harness scaffold into a repository without overwriting anything.
#
# Usage: bash install.sh <repo-root> [--agents a,b,...] [--copy] [--dry-run]
#
# The portable core (harness/, scripts/harness/, docs/, and the lifecycle skills in
# .agents/skills/) is always installed. --agents adds what each named coding agent needs on top:
# a mirror of the skills in the folder that agent reads, and any agent-specific adapter files.
# Mirrors are relative symlinks to .agents/skills/ by default, so there is one source of truth;
# --copy writes plain copies instead (for checkouts where symlinks do not work, such as Windows
# without core.symlinks). init.sh reports mirrors that drift from the canonical skills.
#
# Prints CREATED, LINKED or SKIPPED for every path. Existing files are never touched; merge them
# by hand.
set -o pipefail

# Agent ids follow the `npx skills` CLI. Agents in the first group read .agents/skills/ already.
READS_AGENTS_DIR="amp cline codex cursor gemini-cli github-copilot opencode pi universal warp zed"
mirror_dir() {
  case "$1" in
    claude-code) echo ".claude/skills" ;;
    devin) echo ".devin/skills" ;;
    windsurf) echo ".windsurf/skills" ;;
    kiro-cli) echo ".kiro/skills" ;;
    *) echo "" ;;
  esac
}
KNOWN_AGENTS="$READS_AGENTS_DIR claude-code devin windsurf kiro-cli"

usage() {
  echo "Usage: bash install.sh <repo-root> [--agents a,b,...] [--copy] [--dry-run]" >&2
  echo "Agents: $KNOWN_AGENTS" >&2
  exit 2
}

TARGET=""
DRY_RUN=0
COPY=0
AGENTS=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --copy) COPY=1 ;;
    --agents)
      [ $# -ge 2 ] || usage
      AGENTS="$2"
      shift
      ;;
    --agents=*) AGENTS="${1#--agents=}" ;;
    -h|--help) usage ;;
    -*) usage ;;
    *)
      if [ -n "$TARGET" ]; then
        usage
      fi
      TARGET="$1"
      ;;
  esac
  shift
done
[ -n "$TARGET" ] || usage

AGENT_LIST="$(printf '%s' "$AGENTS" | tr ',' ' ')"
for agent in $AGENT_LIST; do
  case " $KNOWN_AGENTS " in
    *" $agent "*) ;;
    *)
      echo "ERROR: unknown agent: $agent" >&2
      echo "WHY:   install.sh only knows where these agents read skills: $KNOWN_AGENTS" >&2
      echo "FIX:   use one of those ids. An agent that reads .agents/skills/ needs no id at all." >&2
      exit 2
      ;;
  esac
done

if [ ! -d "$TARGET" ]; then
  echo "ERROR: target directory not found: $TARGET" >&2
  exit 1
fi
TARGET="$(cd "$TARGET" && pwd)"

if ! git -C "$TARGET" rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "ERROR: $TARGET is not inside a git repository." >&2
  echo "WHY:   worktree isolation and base-branch checks need git." >&2
  echo "FIX:   run 'git init' there first, or point install.sh at the repository root." >&2
  exit 1
fi

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CORE="$SKILL_DIR/assets/project"
ADAPTERS="$SKILL_DIR/assets/adapters"

created=0
linked=0
skipped=0

# copy_tree SRC: copy every file under SRC to the same relative path in the target.
# Process substitution keeps the counters in this shell instead of a pipe subshell.
copy_tree() {
  local src="$1" file rel dest
  while IFS= read -r -d '' file; do
    rel="${file#"$src"/}"
    dest="$TARGET/$rel"
    if [ -e "$dest" ] || [ -L "$dest" ]; then
      echo "SKIPPED  $rel (already exists, merge by hand)"
      skipped=$((skipped + 1))
      continue
    fi
    echo "CREATED  $rel"
    created=$((created + 1))
    if [ "$DRY_RUN" -eq 0 ]; then
      mkdir -p "$(dirname "$dest")"
      cp "$file" "$dest"
      case "$rel" in
        *.sh|*.py) chmod +x "$dest" ;;
      esac
    fi
  done < <(find "$src" -type f -not -path '*/__pycache__/*' -not -name '.DS_Store' -print0 | sort -z)
}

# mirror_skills DIR: make every canonical lifecycle skill visible under DIR (relative to target).
mirror_skills() {
  local dir="$1" skill name dest
  for skill in "$CORE"/.agents/skills/*/; do
    name="$(basename "$skill")"
    dest="$TARGET/$dir/$name"
    if [ -e "$dest" ] || [ -L "$dest" ]; then
      echo "SKIPPED  $dir/$name (already exists, merge by hand)"
      skipped=$((skipped + 1))
      continue
    fi
    if [ "$COPY" -eq 1 ]; then
      echo "CREATED  $dir/$name (copy of .agents/skills/$name)"
      created=$((created + 1))
      if [ "$DRY_RUN" -eq 0 ]; then
        mkdir -p "$TARGET/$dir"
        cp -R "$skill" "$dest"
      fi
    else
      # Every mirror dir is two levels deep, so the link climbs two levels to the repo root.
      echo "LINKED   $dir/$name -> ../../.agents/skills/$name"
      linked=$((linked + 1))
      if [ "$DRY_RUN" -eq 0 ]; then
        mkdir -p "$TARGET/$dir"
        ln -s "../../.agents/skills/$name" "$dest"
      fi
    fi
  done
}

copy_tree "$CORE"

for agent in $AGENT_LIST; do
  dir="$(mirror_dir "$agent")"
  if [ -n "$dir" ]; then
    mirror_skills "$dir"
  fi
  if [ -d "$ADAPTERS/$agent/files" ]; then
    copy_tree "$ADAPTERS/$agent/files"
  fi
done

echo ""
summary="$created file(s) created, $linked link(s), $skipped skipped"
if [ "$DRY_RUN" -eq 1 ]; then
  echo "Dry run: $summary would result. Nothing was written."
else
  echo "Done: $summary."
fi
echo "Next: fill harness/config.sh and harness/architecture-rules.json, then merge the snippets in"
echo "      $SKILL_DIR/assets/snippets/ (entry section, .gitignore lines)."
case " $AGENT_LIST " in
  *" claude-code "*)
    echo "      Claude Code hooks: merge $ADAPTERS/claude-code/settings-hooks.json into .claude/settings.json."
    ;;
esac
