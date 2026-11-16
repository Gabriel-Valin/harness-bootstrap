#!/usr/bin/env bash
# verify.sh - layered verification. Stops at the first failing layer.
#
#   Layer 1  static   lint, types, format, architecture rules   (required)
#   Layer 2  tests    automated tests                            (required)
#            smoke    the real application starts                (optional)
#   Layer 3  e2e      end-to-end user flows                      (optional)
#
# Usage: scripts/harness/verify.sh [--quick]
#   --quick  run layers 1 and 2 only (no smoke, no e2e)
#
# Exit codes: 0 all configured layers passed, 1 a layer failed, 3 a required layer is not
# configured (UNVERIFIED: nothing proved the code works).
set -o pipefail
# shellcheck source=lib.sh
. "$(dirname "$0")/lib.sh"

QUICK=0
case "${1:-}" in
  --quick) QUICK=1 ;;
  '') ;;
  *) echo "Usage: scripts/harness/verify.sh [--quick]" >&2; exit 2 ;;
esac

LOG="$(harness_run_log verify)"
UNVERIFIED=""
echo "Verification log: ${LOG#"$HARNESS_ROOT"/}"

# layer <name> <commands> <required:1|0> <hint when it fails>
layer() {
  local name="$1" cmds="$2" required="$3" hint="$4" rc start
  echo ""
  echo "== $name ==" | tee -a "$LOG"
  start="$(wc -l < "$LOG")"
  harness_run_cmds "$name" "$cmds" "$LOG"
  rc=$?
  if [ "$rc" -eq 0 ] && { [ "$name" = "tests" ] || [ "$name" = "e2e" ]; }; then
    if ! tail -n +"$((start + 1))" "$LOG" | python3 "$HARNESS_SCRIPTS/feature.py" check-log --require-tests - >/dev/null; then
      echo "  FAIL [$name]: the run did not prove behavior: no tests ran, some were skipped, or no passing summary was printed" | tee -a "$LOG"
      rc=1
    fi
  fi
  if [ "$rc" -eq 0 ]; then
    echo "PASS: $name" | tee -a "$LOG"
    return 0
  fi
  if [ "$rc" -eq 2 ]; then
    if [ "$required" -eq 1 ]; then
      echo "UNVERIFIED: no $name command configured in harness/config.sh" | tee -a "$LOG"
      UNVERIFIED="$UNVERIFIED $name"
    else
      echo "SKIP: no $name command configured" | tee -a "$LOG"
    fi
    return 0
  fi
  echo "" | tee -a "$LOG"
  echo "ERROR: layer '$name' failed. Later layers were not run." | tee -a "$LOG"
  echo "WHY:   $hint" | tee -a "$LOG"
  echo "FIX:   read the output above (full log: ${LOG#"$HARNESS_ROOT"/}), fix the cause in the code," | tee -a "$LOG"
  echo "       and rerun. Do not weaken the check or edit harness/config.sh to get a pass." | tee -a "$LOG"
  exit 1
}

# Each layer must add evidence the others do not. The same command in two layers (for example
# the integration tests listed again as e2e) would report a layer as proven while proving nothing
# new, so it is a configuration error, not a pass.
duplicates="$(
  for pair in "static:${HARNESS_STATIC_CMDS:-}" "tests:${HARNESS_TEST_CMDS:-}" \
              "smoke:${HARNESS_SMOKE_CMDS:-}" "e2e:${HARNESS_E2E_CMDS:-}"; do
    name="${pair%%:*}"
    printf '%s\n' "${pair#*:}" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' |
      grep -v '^$' | sed "s/^/$name	/"
  done | awk -F '\t' '
    { if ($2 in seen && seen[$2] != $1) print "  " seen[$2] " and " $1 ": " $2; else seen[$2] = $1 }'
)"
if [ -n "$duplicates" ]; then
  echo ""
  echo "ERROR: the same command is configured in two verification layers:" | tee -a "$LOG"
  printf '%s\n' "$duplicates" | tee -a "$LOG"
  echo "WHY:   a layer that reruns another layer's command adds no evidence, so reporting it as" | tee -a "$LOG"
  echo "       passed would overstate what was verified." | tee -a "$LOG"
  echo "FIX:   in harness/config.sh, keep the command in the layer it belongs to and leave the other" | tee -a "$LOG"
  echo "       layer empty (it is then reported as not configured), or give it a real command of its own." | tee -a "$LOG"
  exit 1
fi

layer "static" "${HARNESS_STATIC_CMDS:-}" 1 \
  "static checks catch the cheapest defects; nothing else is trustworthy until they pass."
layer "tests" "${HARNESS_TEST_CMDS:-}" 1 \
  "a test that passed before your change now fails, or your new test exposes a defect."
if [ "$QUICK" -eq 0 ]; then
  layer "smoke" "${HARNESS_SMOKE_CMDS:-}" 0 \
    "the application does not start; unit tests cannot see wiring, config or environment errors."
  layer "e2e" "${HARNESS_E2E_CMDS:-}" 0 \
    "a user flow is broken across components; this is what unit tests are blind to."
fi

echo ""
if [ -n "$UNVERIFIED" ]; then
  echo "RESULT: UNVERIFIED (missing required layers:$UNVERIFIED)"
  echo "FIX:    configure those layers in harness/config.sh; until then this code is not proven."
  exit 3
fi
if [ "$QUICK" -eq 1 ]; then
  echo "RESULT: PASS (quick: static + tests)"
else
  echo "RESULT: PASS"
fi
