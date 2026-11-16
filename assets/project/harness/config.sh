# harness/config.sh - project commands for the harness scripts.
#
# Sourced by scripts/harness/*.sh. Change it by PR so every agent and developer uses the same
# definition of "verified".
#
# Each *_CMDS variable holds one command per line. Commands run from the repository root through
# `bash -c`, in order, and stop at the first failure.

# Branch that task branches start from and merge into. Leave empty to auto-detect origin/HEAD.
HARNESS_BASE_BRANCH=""

# Install dependencies and prepare the environment. Run by init.sh.
HARNESS_SETUP_CMDS=""

# Layer 1 - static checks: format, lint, type check, architecture rules. Required.
HARNESS_STATIC_CMDS='python3 scripts/harness/check_architecture.py
python3 scripts/harness/test_feature.py'

# Layer 2 - automated tests. Required.
HARNESS_TEST_CMDS=""

# Layer 2b - smoke: prove the real application starts (health check, --help, build). Optional,
# but without it nobody has proven the app runs.
HARNESS_SMOKE_CMDS=""

# Layer 3 - end-to-end user flows. Optional here, required by the definition of done for
# cross-component changes.
HARNESS_E2E_CMDS=""

# Extended regex matched against lines added on the branch by cleanup-scan.sh.
HARNESS_DEBUG_PATTERNS='TODO\(harness\)|XXX DEBUG'

# Exemption from the debug check: added lines whose path matches HARNESS_DEBUG_ALLOW_PATHS skip
# only the pattern HARNESS_DEBUG_ALLOW_PATTERN. Use it for CLI scripts that print on purpose.
# Both empty means no exemption.
HARNESS_DEBUG_ALLOW_PATHS=''
HARNESS_DEBUG_ALLOW_PATTERN=''
