"""`make outbox-reconcile`, driven with a stand-in `uv`.

The target runs `protean outbox reconcile` once per context and exits non-zero
when any run failed, after trying the rest. These tests put a stand-in `uv`
first on PATH that records each call and fails for the context named in
`FAKE_FAIL`, so they need no database.

The real reconcile against Postgres and Message DB is
`verification/oracles/test_crash_window_reconcile.py`.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

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

FAKE_UV = """#!/bin/sh
# Stand-in for `uv run protean ...`.
shift
echo "$*" >> "$FAKE_CALLS"
case "$*" in
    *"--domain=$FAKE_FAIL.domain"*) exit 1 ;;
esac
"""


def _make(tmp_path: Path, *args: str, fail: str = "none") -> tuple[subprocess.CompletedProcess, list[str]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "uv"
    fake.write_text(FAKE_UV)
    fake.chmod(0o755)
    calls = tmp_path / "calls.log"

    env = dict(os.environ)
    env.pop("LIMIT", None)
    env.update(PATH=f"{bin_dir}{os.pathsep}{env['PATH']}", FAKE_CALLS=str(calls), FAKE_FAIL=fail)
    result = subprocess.run(
        ["make", "-s", "-C", str(ROOT), "outbox-reconcile", *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )
    return result, calls.read_text().splitlines() if calls.exists() else []


def test_reconciles_every_context_with_the_default_limit(tmp_path):
    result, calls = _make(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert calls == [f"protean outbox reconcile --domain={d}.domain --limit=1000" for d in CONTEXTS]


def test_limit_is_passed_through(tmp_path):
    result, calls = _make(tmp_path, "LIMIT=5000")

    assert result.returncode == 0, result.stdout + result.stderr
    assert calls, "precondition: the target ran"
    assert {call.rsplit(" ", 1)[1] for call in calls} == {"--limit=5000"}


def test_one_failed_context_fails_the_target_after_the_rest_run(tmp_path):
    result, calls = _make(tmp_path, fail="ordering")

    assert result.returncode != 0
    assert [call.split()[3] for call in calls] == [f"--domain={d}.domain" for d in CONTEXTS]


def test_help_lists_the_target():
    result = subprocess.run(
        ["make", "-s", "-C", str(ROOT), "help"], capture_output=True, text=True, timeout=60, check=True
    )

    assert any(line.split()[:1] == ["outbox-reconcile"] for line in result.stdout.splitlines())
