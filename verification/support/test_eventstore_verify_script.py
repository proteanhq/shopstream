"""`scripts/eventstore-verify.sh` (`make eventstore-verify`), driven with canned verify output.

The script runs `protean eventstore verify --json` once, prints one summary line read
from the JSON envelope, and exits with verify's own code. These tests put a stand-in
`uv` first on PATH: `uv run --no-sync protean ...` prints a canned envelope and records
how it was called, and `uv run --no-sync python ...` runs the real interpreter, so the
script's own summary code runs unchanged.

The real check against Message DB is `verification/oracles/test_eventstore_integrity.py`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "eventstore-verify.sh"

FAKE_UV = """#!/bin/sh
# Stand-in for `uv run --no-sync <prog> ...`.
shift 2
prog="$1"
shift
if [ "$prog" = protean ]; then
    printf '%s|%s|%s\\n' "$*" "$PROTEAN_LOG_LEVEL" "$PYTHONPATH" >> "$FAKE_CALLS"
    cat "$FAKE_ENVELOPE"
    exit "$FAKE_RC"
fi
exec "$REAL_PYTHON" "$@"
"""


def _envelope(status: str, data: dict) -> str:
    return json.dumps({"version": 1, "status": status, "data": data, "diagnostics": []}, indent=2)


def _report(violations: list[dict]) -> dict:
    return {"ok": not violations, "message_count": 14, "stream_count": 9, "violations": violations}


def _run(tmp_path: Path, stdout: str, verify_rc: int) -> tuple[subprocess.CompletedProcess, Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "uv"
    fake.write_text(FAKE_UV)
    fake.chmod(0o755)
    envelope_file = tmp_path / "envelope.json"
    envelope_file.write_text(stdout)
    calls = tmp_path / "calls.log"

    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.update(
        PATH=f"{bin_dir}{os.pathsep}{env['PATH']}",
        FAKE_ENVELOPE=str(envelope_file),
        FAKE_CALLS=str(calls),
        FAKE_RC=str(verify_rc),
        REAL_PYTHON=sys.executable,
        TMPDIR=str(tmp_path),
    )
    result = subprocess.run(["bash", str(SCRIPT)], capture_output=True, text=True, env=env, timeout=60, check=False)
    return result, calls


def test_clean_store_prints_the_counts_and_exits_0(tmp_path):
    result, calls = _run(tmp_path, _envelope("pass", _report([])), 0)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == ["message_count=14 stream_count=9 violations=0 status=pass"]
    [call] = calls.read_text().splitlines()
    assert call.split("|") == ["eventstore verify --domain=ordering.domain --json", "WARNING", "src"]


def test_violations_print_their_count_and_exit_1(tmp_path):
    gap = {"kind": "position_gap", "stream": "inventory::inventory_item-1", "position": 2, "detail": "expected 1."}

    result, _ = _run(tmp_path, _envelope("fail", _report([gap])), 1)

    assert result.returncode == 1
    assert result.stdout.splitlines() == ["message_count=14 stream_count=9 violations=1 status=fail"]


def test_error_envelope_prints_the_first_error_line_and_exits_2(tmp_path):
    error = {"error": "Error loading Protean domain: boom\nTraceback (most recent call last):"}

    result, _ = _run(tmp_path, _envelope("error", error), 2)

    assert result.returncode == 2
    assert result.stdout.splitlines() == [
        "message_count=? stream_count=? violations=? status=error error=Error loading Protean domain: boom"
    ]


def test_missing_json_report_says_so_and_keeps_the_exit_code(tmp_path):
    result, _ = _run(tmp_path, "", 1)

    assert result.returncode == 1
    assert result.stdout.splitlines() == ["eventstore verify returned no JSON report (exit 1); see the output above"]
