"""The gate in `scripts/ir-gate.sh`, driven with canned `protean ir diff` output.

`ir diff` exits 2 for non-breaking changes only, the same code Click uses for a usage
error. The script accepts exit 2 only when stdout holds a JSON report whose summary has
changes and no breaking change. These tests put a stand-in `uv` first on PATH:
`uv run protean ...` prints canned stdout and stderr and exits with a canned code, and
`uv run python ...` runs the real interpreter, so the script's own parser runs
unchanged. `test_ir_gate.py` covers the exit codes of `ir diff` itself.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "ir-gate.sh"

FAKE_UV = """#!/bin/sh
# Stand-in for `uv run <prog> ...`.
shift
prog="$1"
shift
if [ "$prog" = protean ]; then
    printf '%s|%s|%s\\n' "$*" "$PROTEAN_ENV" "$PYTHONPATH" >> "$FAKE_CALLS"
    case "$*" in
        *"--format json"*) cat "$FAKE_STDOUT"; cat "$FAKE_STDERR" >&2; exit "$FAKE_RC" ;;
        *) echo "$FAKE_TEXT"; exit "$FAKE_RC" ;;
    esac
fi
exec "$REAL_PYTHON" "$@"
"""


def _report(has_changes: bool, has_breaking_changes: bool) -> str:
    summary = {
        "counts": {"added": 1, "changed": 0, "removed": 0},
        "has_changes": has_changes,
        "has_breaking_changes": has_breaking_changes,
    }
    return json.dumps({"summary": summary, "compatibility": {"breaking_changes": [], "safe_changes": []}})


def _run(
    tmp_path: Path, code: int, stdout: str = "", stderr: str = "", text: str = "", *contexts: str
) -> tuple[subprocess.CompletedProcess, list[str]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "uv"
    fake.write_text(FAKE_UV)
    fake.chmod(0o755)
    out_file = tmp_path / "stdout.txt"
    out_file.write_text(stdout)
    err_file = tmp_path / "stderr.txt"
    err_file.write_text(stderr)
    calls = tmp_path / "calls.log"

    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.update(
        PATH=f"{bin_dir}{os.pathsep}{env['PATH']}",
        FAKE_STDOUT=str(out_file),
        FAKE_STDERR=str(err_file),
        FAKE_TEXT=text,
        FAKE_RC=str(code),
        FAKE_CALLS=str(calls),
        REAL_PYTHON=sys.executable,
        TMPDIR=str(tmp_path),
    )
    result = subprocess.run(
        ["bash", str(SCRIPT), *contexts], capture_output=True, text=True, env=env, timeout=60, check=False
    )
    lines = calls.read_text().splitlines() if calls.exists() else []
    return result, lines


def _leftover_temp_files(tmp_path: Path) -> list[str]:
    return [p.name for p in tmp_path.iterdir() if p.name.startswith("ir-gate.")]


def test_no_change_passes_every_context_in_memory_mode(tmp_path):
    result, calls = _run(tmp_path, 0, _report(False, False))

    assert result.returncode == 0, result.stdout + result.stderr
    contexts = [
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
    assert [line.split("|")[0] for line in calls] == [
        f"--log-level ERROR ir diff --domain={ctx}.domain --dir=.protean/{ctx} --format json" for ctx in contexts
    ]
    assert {tuple(line.split("|")[1:]) for line in calls} == {("memory", "src")}
    assert [line for line in result.stdout.splitlines() if line.startswith("ok: ")] == [
        f"ok: {ctx}" for ctx in contexts
    ]
    assert "IR gate passed (no breaking changes)" in result.stdout
    assert _leftover_temp_files(tmp_path) == []


def test_exit_2_with_a_non_breaking_report_passes(tmp_path):
    result, _ = _run(tmp_path, 2, _report(True, False), "", "", "reviews")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "note: non-breaking IR change in reviews (baseline behind; run 'make ir')" in result.stdout
    assert "IR gate passed (no breaking changes)" in result.stdout


@pytest.mark.parametrize(
    "stdout",
    [
        "",
        "Usage: protean ir diff [OPTIONS]",
        _report(True, True),
        _report(False, False),
        json.dumps({"summary": {"has_changes": "yes", "has_breaking_changes": False}}),
        json.dumps({"clusters": {}}),
        json.dumps([1, 2]),
    ],
    ids=["empty", "not-json", "breaking", "no-changes", "string-flag", "no-summary", "not-an-object"],
)
def test_exit_2_without_a_non_breaking_report_fails(tmp_path, stdout):
    stderr = "No such option: --dirr Did you mean --dir?"
    result, calls = _run(tmp_path, 2, stdout, stderr, "", "reviews", "loyalty")

    assert result.returncode == 1, result.stdout + result.stderr
    assert len(calls) == 2, "the loop stopped after the first context"
    for ctx in ("reviews", "loyalty"):
        assert f"=== ir diff exited 2 for {ctx} without a non-breaking JSON report (usage error?) ===" in result.stdout
    assert stderr in result.stdout
    assert "note: non-breaking" not in result.stdout
    assert "IR gate FAILED" in result.stdout
    assert _leftover_temp_files(tmp_path) == []


def test_exit_1_reruns_in_text_format_and_fails(tmp_path):
    text = "Breaking Changes (1): ! removed event Reviews.ReviewSubmitted"
    result, calls = _run(tmp_path, 1, _report(True, True), "", text, "reviews")

    assert result.returncode == 1, result.stdout + result.stderr
    assert [line.split("|")[0] for line in calls] == [
        "--log-level ERROR ir diff --domain=reviews.domain --dir=.protean/reviews --format json",
        "--log-level ERROR ir diff --domain=reviews.domain --dir=.protean/reviews",
    ]
    assert "=== BREAKING IR change or ir diff error in reviews (exit 1) ===" in result.stdout
    assert text in result.stdout
    assert "IR gate FAILED" in result.stdout


def test_other_exit_code_prints_both_streams_and_fails(tmp_path):
    result, _ = _run(tmp_path, 3, "partial output", "Traceback (most recent call last):", "", "reviews")

    assert result.returncode == 1, result.stdout + result.stderr
    assert "=== ir diff ERROR for reviews (exit 3) ===" in result.stdout
    assert "partial output" in result.stdout
    assert "Traceback (most recent call last):" in result.stdout
    assert "IR gate FAILED" in result.stdout


def test_unknown_context_is_rejected_before_any_run(tmp_path):
    result, calls = _run(tmp_path, 0, _report(False, False), "", "", "reviews", "nosuch")

    assert result.returncode == 2
    assert "unknown context: nosuch" in result.stderr
    assert calls == []
