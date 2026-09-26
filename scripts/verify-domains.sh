#!/usr/bin/env bash
set -euo pipefail

# Domain Verification Script
#
# Runs `protean verify --json` once for each bounded context, in memory mode, and gives
# one verdict. Each run has three stages:
#
#   init   Domain.init(traverse=True)
#   check  Domain.check(), the engine behind `protean check`
#   tests  pytest, scoped to the context's own tests/<context>/ directory
#
# The gate reads each context's per-stage status from the JSON envelope, not from the
# exit code: verify exits 4 for a check failure even when the tests failed too, so the
# exit code alone can hide a test failure. A context fails the gate when init or tests
# does not pass, or when its tests stage ran zero tests. The check stage is printed on
# every run but does not gate yet; it becomes a gate once the `protean check` rules are
# adopted (#56).
#
# On a full run (no context arguments) the cross-domain tests in tests/integration/ run
# once more at the end, as plain pytest, since they belong to no single context.
#
# Needs no running stack: everything runs on the in-memory adapters.
#
# Prerequisites:
#   uv sync
#
# Usage:
#   ./scripts/verify-domains.sh                     # all nine contexts + tests/integration/
#   ./scripts/verify-domains.sh ordering loyalty    # only these contexts (skips tests/integration/)

CONTEXTS=(identity catalogue ordering inventory payments fulfillment reviews notifications loyalty)

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# ============================================================
#  Arguments
# ============================================================
if [ "$#" -gt 0 ]; then
    for arg in "$@"; do
        known=0
        for ctx in "${CONTEXTS[@]}"; do
            if [ "$arg" = "$ctx" ]; then known=1; fi
        done
        if [ "$known" -eq 0 ]; then
            echo "ERROR: unknown context: $arg" >&2
            echo "Valid contexts: ${CONTEXTS[*]}" >&2
            exit 2
        fi
    done
    SELECTED=("$@")
    RUN_INTEGRATION=0
else
    SELECTED=("${CONTEXTS[@]}")
    RUN_INTEGRATION=1
fi

# Init and check read PROTEAN_ENV in the verify process. The tests stage drops
# PROTEAN_ENV before starting pytest, so memory mode reaches pytest through
# --protean-env in PYTEST_ADDOPTS instead.
export PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}"
export PROTEAN_ENV=memory

# `--no-sync` uses the project venv as it is, so a run never rewrites uv.lock or
# replaces a locally installed Protean wheel.
PY=(uv run --no-sync python)
PROTEAN=(uv run --no-sync protean)

LOG_DIR="$(mktemp -d "${TMPDIR:-/tmp}/verify-domains.XXXXXX")"

FAILED=()

# Read a verify --json envelope and print one summary line. The last word of the
# output is the gate result, "ok" or "fail".
summarize() {
    "${PY[@]}" - "$1" "$2" "$3" <<'PY'
import json
import sys

path, context, seconds = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    with open(path) as fh:
        stages = json.load(fh)["data"]["stages"]
    init, check, tests = stages["init"], stages["check"], stages["tests"]
except (OSError, ValueError, KeyError, TypeError) as exc:
    print(f"  {context:<14} no usable JSON from protean verify ({exc})  {seconds}s  fail")
    sys.exit(0)

counts = check.get("counts", {})
errors = counts.get("errors", "-")
warnings = counts.get("warnings", "-")
infos = counts.get("infos", "-")
passed = tests.get("passed", 0)
failed = tests.get("failed", 0)

ok = init["status"] == "pass" and tests["status"] == "pass" and passed > 0
line = (
    f"  {context:<14} init={init['status']:<7} "
    f"check={check['status']:<7} ({errors} errors, {warnings} warnings, {infos} infos)  "
    f"tests={tests['status']:<7} ({passed} passed, {failed} failed)  {seconds}s"
)
print(f"{line}  {'ok' if ok else 'fail'}")
if init.get("error"):
    print(f"      init error: {init['error'].strip().splitlines()[0]}")
if check["status"] == "fail":
    print("      check does not gate yet; the protean check rules are adopted in #56")
if tests["status"] == "pass" and passed == 0:
    print("      tests stage ran no tests")
PY
}

echo ""
echo "==========================================="
echo "  protean verify (memory mode)"
echo "==========================================="

for ctx in "${SELECTED[@]}"; do
    json="$LOG_DIR/$ctx.json"
    start=$(date +%s)
    rc=0
    PYTEST_ADDOPTS="--protean-env memory -m 'not engine' tests/$ctx/" \
        "${PROTEAN[@]}" verify -d "$ctx.domain" --path . --json \
        > "$json" 2> "$LOG_DIR/$ctx.stderr.log" || rc=$?
    seconds=$(( $(date +%s) - start ))

    summary=$(summarize "$json" "$ctx" "$seconds")
    echo "$summary"
    if [ "$(echo "$summary" | head -1 | awk '{print $NF}')" != "ok" ]; then
        FAILED+=("$ctx")
        echo "      verify exited $rc; rerun the tests with:"
        echo "      uv run pytest tests/$ctx/ --protean-env memory -m 'not engine'"
    fi
done

if [ "$RUN_INTEGRATION" -eq 1 ]; then
    start=$(date +%s)
    rc=0
    "${PY[@]}" -m pytest tests/integration/ --protean-env memory -m "not engine" -q \
        > "$LOG_DIR/integration.log" 2>&1 || rc=$?
    seconds=$(( $(date +%s) - start ))
    result=$(grep -E '[0-9]+ (passed|failed|error)' "$LOG_DIR/integration.log" | tail -1 || true)
    if [ "$rc" -eq 0 ]; then
        echo "  $(printf '%-14s' integration) pytest tests/integration/: ${result}  ${seconds}s  ok"
    else
        FAILED+=("integration")
        echo "  $(printf '%-14s' integration) pytest tests/integration/ exited $rc: ${result}  ${seconds}s  fail"
    fi
fi

echo ""
if [ "${#FAILED[@]}" -eq 0 ]; then
    rm -rf "$LOG_DIR"
    echo "All passed (${SELECTED[*]})"
    exit 0
fi
echo "Failed: ${FAILED[*]}"
echo "Logs kept in $LOG_DIR"
exit 1
