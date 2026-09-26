"""The gate in `scripts/verify-domains.sh`, driven with canned `protean verify` output.

The script runs `protean verify --json` per context and decides pass or fail from the
per-stage statuses in the envelope, not from verify's exit code. These tests put a
stand-in `uv` first on PATH: `uv run --no-sync protean ...` prints a canned envelope
and records how it was called, and `uv run --no-sync python ...` runs the real
interpreter, so the script's own parser and gate run unchanged. Each case runs one
context (`reviews`), which also skips the tests/integration/ run.

The real nine-context run takes about a minute and nests pytest, so it stays out of
the suite: run `bash scripts/verify-domains.sh`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "verify-domains.sh"

FAKE_UV = """#!/bin/sh
# Stand-in for `uv run --no-sync <prog> ...`.
shift 2
prog="$1"
shift
if [ "$prog" = protean ]; then
    printf '%s|%s\\n' "$*" "$PYTEST_ADDOPTS" >> "$FAKE_CALLS"
    cat "$FAKE_ENVELOPE"
    exit "$FAKE_RC"
fi
exec "$REAL_PYTHON" "$@"
"""


def _envelope(init="pass", check="pass", tests="pass", passed=5, failed=0, warnings=0) -> str:
    stages = {
        "init": {"status": init, "error": None if init == "pass" else "Domain failed to initialize: boom"},
        "check": {"status": check, "counts": {"errors": 0, "warnings": warnings, "infos": 3}},
        "tests": {"status": tests, "returncode": 0 if tests == "pass" else 1, "passed": passed, "failed": failed},
    }
    return json.dumps({"status": "pass", "data": {"verdict": "pass", "stages": stages}})


def _run(tmp_path: Path, envelope: str, verify_rc: int, *args: str) -> tuple[subprocess.CompletedProcess, Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "uv"
    fake.write_text(FAKE_UV)
    fake.chmod(0o755)
    envelope_file = tmp_path / "envelope.json"
    envelope_file.write_text(envelope)
    calls = tmp_path / "calls.log"

    env = dict(os.environ)
    env.update(
        PATH=f"{bin_dir}{os.pathsep}{env['PATH']}",
        FAKE_ENVELOPE=str(envelope_file),
        FAKE_CALLS=str(calls),
        FAKE_RC=str(verify_rc),
        REAL_PYTHON=sys.executable,
        TMPDIR=str(tmp_path),
    )
    result = subprocess.run(
        ["bash", str(SCRIPT), *args], capture_output=True, text=True, env=env, timeout=60, check=False
    )
    return result, calls


def test_unknown_context_is_rejected_before_any_run(tmp_path):
    result, calls = _run(tmp_path, _envelope(), 0, "reviews", "nosuch")

    assert result.returncode == 2
    assert "unknown context: nosuch" in result.stderr
    assert not calls.exists(), "protean verify ran for a command line that names an unknown context"


def test_passing_context_runs_its_own_tests_in_memory_mode(tmp_path):
    result, calls = _run(tmp_path, _envelope(), 0, "reviews")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "All passed (reviews)" in result.stdout
    assert calls.read_text().splitlines() == [
        "verify -d reviews.domain --path . --json|--protean-env memory -m 'not engine' tests/reviews/"
    ]


def test_check_failure_is_printed_but_does_not_gate(tmp_path):
    # verify exits 4 when check fails, even though init and tests passed.
    result, _ = _run(tmp_path, _envelope(check="fail", warnings=2), 4, "reviews")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "check=fail    (0 errors, 2 warnings, 3 infos)" in result.stdout
    assert "adopted in #56" in result.stdout


@pytest.mark.parametrize(
    ("envelope", "verify_rc", "reason"),
    [
        # Exit 4 (check) outranks exit 5 (tests), so only the envelope shows the test failure.
        (_envelope(check="fail", tests="fail", passed=3, failed=2, warnings=1), 4, "tests=fail"),
        # pytest exit 5 (no tests collected) is a pass in verify.
        (_envelope(passed=0), 0, "tests stage ran no tests"),
        (_envelope(init="fail", check="skipped", tests="skipped", passed=0), 3, "init error: Domain failed"),
        ("Traceback (most recent call last):", 1, "no usable JSON"),
    ],
    ids=["tests-fail-under-check-fail", "zero-tests", "init-fail", "no-json"],
)
def test_failing_context_fails_the_run(tmp_path, envelope, verify_rc, reason):
    result, _ = _run(tmp_path, envelope, verify_rc, "reviews")

    assert result.returncode == 1, result.stdout + result.stderr
    assert reason in result.stdout
    assert "Failed: reviews" in result.stdout
