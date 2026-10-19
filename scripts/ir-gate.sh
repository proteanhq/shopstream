#!/usr/bin/env bash
set -uo pipefail

# IR Gate Script
#
# Runs `protean ir diff --format json` for each bounded context against its committed
# baseline in .protean/<context>/ir.json and fails on a breaking change. `make ir-gate`
# calls it, and so does CI.
#
# `ir diff` exits 0 for no change, 1 for a breaking change and 2 for non-breaking
# changes only. Click also exits 2 for a usage error, such as a misspelled option, so
# the exit code alone cannot tell a safe change from a broken command line. The gate
# accepts exit 2 only when stdout holds the JSON report and its summary says there are
# changes and none of them is breaking. Any other exit 2 fails the gate.
#
# Exit 1 also covers `ir diff` errors (bad config, a missing baseline), not only
# breaking changes. On exit 1 the gate runs the diff again in text format for that
# context and prints it, so the reason is readable either way.
#
# Usage:
#   ./scripts/ir-gate.sh                     # all nine contexts
#   ./scripts/ir-gate.sh ordering loyalty    # only these contexts

CONTEXTS=(identity catalogue ordering inventory payments fulfillment reviews notifications loyalty)

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

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
else
    SELECTED=("${CONTEXTS[@]}")
fi

export PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}"
export PROTEAN_ENV=memory

OUT="$(mktemp "${TMPDIR:-/tmp}/ir-gate.out.XXXXXX")"
ERR="$(mktemp "${TMPDIR:-/tmp}/ir-gate.err.XXXXXX")"
trap 'rm -f "$OUT" "$ERR"' EXIT

ir_diff() {
    local ctx="$1"
    shift
    uv run protean --log-level ERROR ir diff --domain="$ctx.domain" --dir=".protean/$ctx" "$@"
}

# Exit 0 when the file holds an `ir diff` JSON report with changes and no breaking change.
is_non_breaking_report() {
    uv run python - "$1" <<'PY'
import json
import sys

try:
    with open(sys.argv[1]) as fh:
        summary = json.load(fh)["summary"]
except Exception:
    sys.exit(1)
ok = summary.get("has_changes") is True and summary.get("has_breaking_changes") is False
sys.exit(0 if ok else 1)
PY
}

show_output() {
    echo "--- stdout ---"
    cat "$OUT"
    echo "--- stderr ---"
    cat "$ERR"
}

fail=0
for ctx in "${SELECTED[@]}"; do
    code=0
    ir_diff "$ctx" --format json > "$OUT" 2> "$ERR" || code=$?
    if [ "$code" -eq 0 ]; then
        echo "ok: $ctx"
    elif [ "$code" -eq 2 ] && is_non_breaking_report "$OUT"; then
        echo "note: non-breaking IR change in $ctx (baseline behind; run 'make ir')"
    elif [ "$code" -eq 2 ]; then
        echo ""
        echo "=== ir diff exited 2 for $ctx without a non-breaking JSON report (usage error?) ==="
        show_output
        echo "=== end $ctx ==="
        fail=1
    elif [ "$code" -eq 1 ]; then
        echo ""
        echo "=== BREAKING IR change or ir diff error in $ctx (exit 1) ==="
        ir_diff "$ctx" 2>&1
        echo "=== end $ctx ==="
        fail=1
    else
        echo ""
        echo "=== ir diff ERROR for $ctx (exit $code) ==="
        show_output
        echo "=== end $ctx ==="
        fail=1
    fi
done

if [ "$fail" -ne 0 ]; then
    echo ""
    echo "IR gate FAILED (details above). If a change is intended, run 'make ir' and commit the reviewed baseline."
    exit 1
fi
echo ""
echo "IR gate passed (no breaking changes)"
