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
# once more at the end, as plain pytest, since they belong to no single context. That
# run also fails when no test passed.
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
    # Keep each named context once, in the order given.
    SELECTED=()
    for arg in "$@"; do
        seen=0
        for ctx in ${SELECTED[@]+"${SELECTED[@]}"}; do
            if [ "$arg" = "$ctx" ]; then seen=1; fi
        done
        if [ "$seen" -eq 0 ]; then SELECTED+=("$arg"); fi
    done
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
# If the script stops early, say where the logs are rather than leaving them unnamed.
trap 'rc=$?; if [ "$rc" -ne 0 ] && [ -d "$LOG_DIR" ]; then echo "Logs kept in $LOG_DIR"; fi' EXIT

FAILED=()

# Read a verify --json envelope and print one summary line. The last word of the
# output is the gate result, "ok" or "fail".
summarize() {
    "${PY[@]}" - "$1" "$2" "$3" <<'PY'
import json
import sys

path, context, seconds = sys.argv[1], sys.argv[2], sys.argv[3]
rerun = f"uv run --no-sync pytest tests/{context}/ --protean-env memory -m 'not engine'"


def first_line(text):
    lines = str(text or "").strip().splitlines()
    return lines[0] if lines else ""


try:
    with open(path) as fh:
        data = json.load(fh)["data"]
    stages = data.get("stages") or {}
    init, check, tests = (stages.get(name) or {} for name in ("init", "check", "tests"))
    counts = check.get("counts") or {}
    errors = counts.get("errors", "-")
    warnings = counts.get("warnings", "-")
    infos = counts.get("infos", "-")
    passed = tests.get("passed", 0)
    failed = tests.get("failed", 0)
    init_status = init.get("status", "missing")
    check_status = check.get("status", "missing")
    tests_status = tests.get("status", "missing")
    ran_tests = isinstance(passed, int) and passed > 0

    ok = init_status == "pass" and tests_status == "pass" and ran_tests
    line = (
        f"  {context:<14} init={init_status:<7} "
        f"check={check_status:<7} ({errors} errors, {warnings} warnings, {infos} infos)  "
        f"tests={tests_status:<7} ({passed} passed, {failed} failed)  {seconds}s"
    )
    notes = []
    if first_line(data.get("error")):
        notes.append(f"verify error: {first_line(data['error'])}")
    if first_line(init.get("error")):
        notes.append(f"init error: {first_line(init['error'])}")
    if check_status == "fail":
        notes.append("check does not gate yet; the protean check rules are adopted in #56")
    if tests_status == "pass" and not ran_tests:
        notes.append("tests stage ran no tests")
    if init_status == "pass" and not (tests_status == "pass" and ran_tests):
        notes.append(f"rerun the tests with: {rerun}")
except Exception as exc:  # any envelope shape we cannot read fails this context only
    print(f"  {context:<14} no usable JSON from protean verify ({type(exc).__name__}: {exc})  {seconds}s  fail")
    sys.exit(0)

print(f"{line}  {'ok' if ok else 'fail'}")
for note in notes:
    print(f"      {note}")
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

    summary=$(summarize "$json" "$ctx" "$seconds") \
        || summary="  $(printf '%-14s' "$ctx") could not read the verify output  ${seconds}s  fail"
    echo "$summary"
    if [ "$(echo "$summary" | head -1 | awk '{print $NF}')" != "ok" ]; then
        FAILED+=("$ctx")
        echo "      verify exited $rc"
    fi
done

if [ "$RUN_INTEGRATION" -eq 1 ]; then
    start=$(date +%s)
    rc=0
    # An empty PYTEST_ADDOPTS keeps the caller's options (--co, -k, -x) from changing
    # what this run checks.
    PYTEST_ADDOPTS="" "${PY[@]}" -m pytest tests/integration/ --protean-env memory -m "not engine" -q \
        > "$LOG_DIR/integration.log" 2>&1 || rc=$?
    seconds=$(( $(date +%s) - start ))
    result=$(grep -E '[0-9]+ (passed|failed|error)' "$LOG_DIR/integration.log" | tail -1 || true)
    if [ "$rc" -ne 0 ]; then
        FAILED+=("integration")
        echo "  $(printf '%-14s' integration) pytest tests/integration/ exited $rc: ${result}  ${seconds}s  fail"
    elif ! echo "$result" | grep -Eq '(^|[^0-9])[1-9][0-9]* passed'; then
        # Exit 0 with nothing passed (all skipped, or collection only) is not a pass.
        FAILED+=("integration")
        echo "  $(printf '%-14s' integration) pytest tests/integration/: no test passed (${result})  ${seconds}s  fail"
    else
        echo "  $(printf '%-14s' integration) pytest tests/integration/: ${result}  ${seconds}s  ok"
    fi
fi

echo ""
if [ "${#FAILED[@]}" -eq 0 ]; then
    rm -rf "$LOG_DIR"
    if [ "$RUN_INTEGRATION" -eq 1 ]; then SELECTED+=("integration"); fi
    echo "All passed (${SELECTED[*]})"
    exit 0
fi
echo "Failed: ${FAILED[*]}"
exit 1  # the EXIT trap prints where the logs are
