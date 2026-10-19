#!/usr/bin/env bash
set -uo pipefail

# Event Store Integrity Check
#
# Runs `protean eventstore verify --json` once and prints one summary line. All nine
# contexts share one Message DB, so one run with any domain checks the whole store.
# The check is read-only. The script exits with verify's own code: 0 when the store is
# clean, 1 when it found violations, 2 when the domain could not load.
#
# Stop the engines and the API first. Verify pages through the store by
# global_position, and a row that another writer commits after a later row was
# already read can be skipped, which then shows as a false position_gap.
#
# Runs under the default (dev) env unless PROTEAN_ENV is set.
#
# Usage:
#   ./scripts/eventstore-verify.sh

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}"

# `--no-sync` uses the project venv as it is, so a run never rewrites uv.lock or
# replaces a locally installed Protean wheel.
PY=(uv run --no-sync python)
PROTEAN=(uv run --no-sync protean)

OUT="$(mktemp "${TMPDIR:-/tmp}/eventstore-verify.XXXXXX")"
trap 'rm -f "$OUT"' EXIT

rc=0
PROTEAN_LOG_LEVEL=WARNING "${PROTEAN[@]}" eventstore verify --domain=ordering.domain --json > "$OUT" || rc=$?

"${PY[@]}" - "$OUT" "$rc" <<'PY'
import json
import sys

path, rc = sys.argv[1], sys.argv[2]

try:
    with open(path) as fh:
        envelope = json.load(fh)
    status = envelope["status"]
    data = envelope.get("data") or {}
except Exception:
    print(f"eventstore verify returned no JSON report (exit {rc}); see the output above")
    sys.exit(0)

violations = data.get("violations")
line = (
    f"message_count={data.get('message_count', '?')} "
    f"stream_count={data.get('stream_count', '?')} "
    f"violations={len(violations) if isinstance(violations, list) else '?'} "
    f"status={status}"
)
error = str(data.get("error") or "").strip().splitlines()
if status == "error" and error:
    line += f" error={error[0]}"
print(line)
PY

exit "$rc"
