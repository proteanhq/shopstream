"""The gate in `scripts/verify-domains.sh`, driven with canned `protean verify` output.

The script runs `protean verify --json` per context and decides pass or fail from the
per-stage statuses in the envelope, not from verify's exit code. These tests put a
stand-in `uv` first on PATH: `uv run --no-sync protean ...` prints a canned envelope
and records how it was called, and `uv run --no-sync python ...` runs the real
interpreter, so the script's own parser and gate run unchanged. `uv run --no-sync
python -m pytest ...` (the tests/integration/ run) is faked too: it records its args
and prints a canned summary line. Most cases name one context (`reviews`), which skips
the tests/integration/ run; the full-run cases name none.

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
    printf '%s|%s|%s|%s\\n' "$*" "$PYTEST_ADDOPTS" "$PROTEAN_ENV" "$PYTHONPATH" >> "$FAKE_CALLS"
    cat "$FAKE_ENVELOPE"
    exit "$FAKE_RC"
fi
if [ "$1" = -m ] && [ "$2" = pytest ]; then
    printf 'pytest %s|%s\\n' "$*" "$PYTEST_ADDOPTS" >> "$FAKE_CALLS"
    echo "$FAKE_PYTEST_OUT"
    exit "$FAKE_PYTEST_RC"
fi
if [ "$1" = - ] && [ -n "$FAKE_SUMMARY_RC" ]; then
    exit "$FAKE_SUMMARY_RC"
fi
exec "$REAL_PYTHON" "$@"
"""

CONTEXTS = [
    "identity",
    "catalogue",
    "ordering",
    "inventory",
    "payments",
    "fulfillment",
    "reviews",
    "notifications",
    "loyalty",
]


def _envelope(init="pass", check="pass", tests="pass", passed=5, failed=0, warnings=0) -> str:
    stages = {
        "init": {"status": init, "error": None if init == "pass" else "Domain failed to initialize: boom"},
        "check": {"status": check, "counts": {"errors": 0, "warnings": warnings, "infos": 3}},
        "tests": {"status": tests, "returncode": 0 if tests == "pass" else 1, "passed": passed, "failed": failed},
    }
    return json.dumps({"status": "pass", "data": {"verdict": "pass", "stages": stages}})


def _run(
    tmp_path: Path,
    envelope: str,
    verify_rc: int,
    *args: str,
    pytest_out: str = "17 passed in 2.00s",
    pytest_rc: int = 0,
    **extra_env: str,
) -> tuple[subprocess.CompletedProcess, Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "uv"
    fake.write_text(FAKE_UV)
    fake.chmod(0o755)
    envelope_file = tmp_path / "envelope.json"
    envelope_file.write_text(envelope)
    calls = tmp_path / "calls.log"

    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.pop("PYTEST_ADDOPTS", None)
    env.update(
        PATH=f"{bin_dir}{os.pathsep}{env['PATH']}",
        FAKE_ENVELOPE=str(envelope_file),
        FAKE_CALLS=str(calls),
        FAKE_RC=str(verify_rc),
        REAL_PYTHON=sys.executable,
        FAKE_PYTEST_OUT=pytest_out,
        FAKE_PYTEST_RC=str(pytest_rc),
        TMPDIR=str(tmp_path),
        **extra_env,
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
        "verify -d reviews.domain --path . --json|--protean-env memory -m 'not engine' tests/reviews/|memory|src"
    ]
    # Check counts are printed when check passes too.
    assert "check=pass    (0 errors, 0 warnings, 3 infos)" in result.stdout


def test_caller_protean_env_is_overridden(tmp_path):
    _, calls = _run(tmp_path, _envelope(), 0, "reviews", PROTEAN_ENV="test")

    assert calls.read_text().split("|")[2] == "memory"


def test_full_run_verifies_all_nine_contexts_then_integration(tmp_path):
    # The caller's --co must not turn the integration run into a collection-only pass.
    result, calls = _run(tmp_path, _envelope(), 0, PYTEST_ADDOPTS="--co")

    assert result.returncode == 0, result.stdout + result.stderr
    lines = calls.read_text().splitlines()
    assert lines, "nothing was run"
    verify_calls = [line.split("|")[0] for line in lines[:-1]]
    assert verify_calls == [f"verify -d {ctx}.domain --path . --json" for ctx in CONTEXTS]
    assert lines[-1] == "pytest -m pytest tests/integration/ --protean-env memory -m not engine -q|"
    assert "integration    pytest tests/integration/: 17 passed in 2.00s" in result.stdout
    assert f"All passed ({' '.join(CONTEXTS)} integration)" in result.stdout


@pytest.mark.parametrize(
    ("pytest_out", "pytest_rc", "reason"),
    [
        ("16 passed, 1 failed in 2.00s", 1, "exited 1: 16 passed, 1 failed"),
        ("5 skipped in 0.10s", 0, "no test passed"),
        ("no tests ran in 0.01s", 5, "exited 5"),
    ],
    ids=["failure", "all-skipped", "none-collected"],
)
def test_integration_failure_fails_the_full_run(tmp_path, pytest_out, pytest_rc, reason):
    result, _ = _run(tmp_path, _envelope(), 0, pytest_out=pytest_out, pytest_rc=pytest_rc)

    assert result.returncode == 1, result.stdout + result.stderr
    assert reason in result.stdout
    assert "Failed: integration" in result.stdout
    assert "Logs kept in" in result.stdout


def test_named_contexts_run_once_each_and_skip_integration(tmp_path):
    result, calls = _run(tmp_path, _envelope(), 0, "loyalty", "reviews", "loyalty")

    assert result.returncode == 0, result.stdout + result.stderr
    lines = calls.read_text().splitlines()
    assert [line.split("|")[0] for line in lines] == [
        "verify -d loyalty.domain --path . --json",
        "verify -d reviews.domain --path . --json",
    ]
    assert "All passed (loyalty reviews)" in result.stdout


@pytest.mark.parametrize(
    "envelope",
    [
        json.dumps({"data": {"stages": {"init": {}, "check": None, "tests": {"status": "pass"}}}}),
        json.dumps({"data": {"stages": {"init": {"status": "pass", "error": "   "}, "tests": {"passed": "5"}}}}),
        json.dumps({"data": None}),
    ],
    ids=["empty-stages", "odd-types", "null-data"],
)
def test_unreadable_envelope_fails_each_context_without_stopping(tmp_path, envelope):
    result, calls = _run(tmp_path, envelope, 1, "reviews", "loyalty")

    assert result.returncode == 1, result.stdout + result.stderr
    assert len(calls.read_text().splitlines()) == 2, "the loop stopped after the first context"
    assert "Failed: reviews loyalty" in result.stdout
    assert "Logs kept in" in result.stdout


def test_summary_step_that_cannot_start_fails_each_context_without_stopping(tmp_path):
    # Exit 127: the interpreter behind the summary step could not be started.
    result, calls = _run(tmp_path, _envelope(), 0, "reviews", "loyalty", FAKE_SUMMARY_RC="127")

    assert result.returncode == 1, result.stdout + result.stderr
    assert len(calls.read_text().splitlines()) == 2, "the loop stopped after the first context"
    assert "reviews        could not read the verify output" in result.stdout
    assert "Failed: reviews loyalty" in result.stdout


def test_verify_usage_error_is_printed(tmp_path):
    stages = {"init": {"status": "skipped"}, "check": {"status": "skipped"}, "tests": {"status": "skipped"}}
    envelope = json.dumps({"status": "error", "data": {"error": "--path is not a directory", "stages": stages}})
    result, _ = _run(tmp_path, envelope, 2, "reviews")

    assert result.returncode == 1
    assert "verify error: --path is not a directory" in result.stdout


def test_check_failure_is_printed_but_does_not_gate(tmp_path):
    # verify exits 4 when check fails, even though init and tests passed.
    result, _ = _run(tmp_path, _envelope(check="fail", warnings=2), 4, "reviews")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "check=fail    (0 errors, 2 warnings, 3 infos)" in result.stdout
    assert "adopted in #56" in result.stdout
    assert "rerun the tests" not in result.stdout


@pytest.mark.parametrize(
    ("envelope", "verify_rc", "reason"),
    [
        # Exit 4 (check) outranks exit 5 (tests), so only the envelope shows the test failure.
        (_envelope(check="fail", tests="fail", passed=3, failed=2, warnings=1), 4, "tests=fail"),
        # verify reports a tests stage that ran nothing as a pass.
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
    assert "Logs kept in" in result.stdout


def test_rerun_hint_skips_uv_sync(tmp_path):
    result, _ = _run(tmp_path, _envelope(tests="fail", passed=3, failed=2), 5, "reviews")

    assert "rerun the tests with: uv run --no-sync pytest tests/reviews/" in result.stdout
