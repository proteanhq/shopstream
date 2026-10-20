"""The gate in `scripts/ir-gate.sh`, driven with canned `protean ir diff` output.

`ir diff` exits 2 for non-breaking changes only, the same code Click uses for a usage
error. The script accepts exit 2 only when stdout holds a JSON report whose summary has
changes and no breaking change. These tests put a stand-in `uv` first on PATH:
`uv run protean ...` prints canned stdout and stderr for the context named in
`--domain=` and exits with that context's canned code, and `uv run python ...` runs the
real interpreter, so the script's own parser runs unchanged. `test_ir_gate.py` covers
exit 0 and 1 of `ir diff` itself.
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

# Each call records its args (with the gate's temp directory shown as WORK), the
# environment it ran in, and whether --dir held the committed ir.json and config.toml.
FAKE_UV = """#!/bin/sh
# Stand-in for `uv run <prog> ...`.
shift
prog="$1"
shift
if [ "$prog" = protean ]; then
    ctx=""
    linked=no
    for arg in "$@"; do
        case "$arg" in
            --domain=*) ctx="${arg#--domain=}"; ctx="${ctx%.domain}" ;;
            --dir=*)
                dir="${arg#--dir=}"
                if cmp -s "$dir/ir.json" "$REPO/.protean/$ctx/ir.json" \\
                    && cmp -s "$dir/config.toml" "$REPO/.protean/config.toml"; then
                    linked=yes
                fi ;;
        esac
    done
    printf '%s|%s|%s|%s\\n' "$(echo "$*" | sed "s#$TMPDIR/ir-gate\\.[A-Za-z0-9]*#WORK#")" \\
        "$PROTEAN_ENV" "$PYTHONPATH" "$linked" >> "$FAKE_CALLS"
    case "$*" in
        *"--format json"*)
            cat "$FAKE_DIR/$ctx.out"; cat "$FAKE_DIR/$ctx.err" >&2; exit "$(cat "$FAKE_DIR/$ctx.rc")" ;;
        *) cat "$FAKE_DIR/$ctx.text"; exit "$(cat "$FAKE_DIR/$ctx.rc")" ;;
    esac
fi
exec "$REAL_PYTHON" "$@"
"""


def _report(has_changes: bool, has_breaking_changes: bool | None) -> str:
    summary = {
        "counts": {"added": 1, "changed": 0, "removed": 0},
        "has_changes": has_changes,
        "has_breaking_changes": has_breaking_changes,
    }
    return json.dumps({"summary": summary, "compatibility": {"breaking_changes": [], "safe_changes": []}})


def _run_each(
    tmp_path: Path, responses: dict[str, tuple[int, str, str, str]], *contexts: str
) -> tuple[subprocess.CompletedProcess, list[str]]:
    """Run the gate with a canned (exit code, stdout, stderr, text) per context."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "uv"
    fake.write_text(FAKE_UV)
    fake.chmod(0o755)
    fake_dir = tmp_path / "fake"
    fake_dir.mkdir()
    for ctx, (code, stdout, stderr, text) in responses.items():
        (fake_dir / f"{ctx}.rc").write_text(str(code))
        (fake_dir / f"{ctx}.out").write_text(stdout)
        (fake_dir / f"{ctx}.err").write_text(stderr)
        (fake_dir / f"{ctx}.text").write_text(text)
    calls = tmp_path / "calls.log"

    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    # Protean's pytest plugin sets PROTEAN_ENV=memory in this process, so a different
    # value here shows the script sets it itself.
    env["PROTEAN_ENV"] = "test"
    env.update(
        PATH=f"{bin_dir}{os.pathsep}{env['PATH']}",
        FAKE_DIR=str(fake_dir),
        FAKE_CALLS=str(calls),
        REPO=str(ROOT),
        REAL_PYTHON=sys.executable,
        TMPDIR=str(tmp_path),
    )
    result = subprocess.run(
        ["bash", str(SCRIPT), *contexts], capture_output=True, text=True, env=env, timeout=60, check=False
    )
    lines = calls.read_text().splitlines() if calls.exists() else []
    return result, lines


def _run(
    tmp_path: Path, code: int, stdout: str = "", stderr: str = "", text: str = "", *contexts: str
) -> tuple[subprocess.CompletedProcess, list[str]]:
    """Run the gate with the same canned response for every context."""
    return _run_each(tmp_path, dict.fromkeys(CONTEXTS, (code, stdout, stderr, text)), *contexts)


def _leftover_temp_files(tmp_path: Path) -> list[str]:
    return [p.name for p in tmp_path.iterdir() if p.name.startswith("ir-gate.")]


def test_no_change_passes_every_context_in_memory_mode(tmp_path):
    result, calls = _run(tmp_path, 0, _report(False, False))

    assert result.returncode == 0, result.stdout + result.stderr
    assert [line.split("|")[0] for line in calls] == [
        f"--log-level ERROR ir diff --domain={ctx}.domain --dir=WORK/{ctx} --format json" for ctx in CONTEXTS
    ]
    assert {tuple(line.split("|")[1:]) for line in calls} == {("memory", "src", "yes")}
    assert [line for line in result.stdout.splitlines() if line.startswith("ok: ")] == [
        f"ok: {ctx}" for ctx in CONTEXTS
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
        json.dumps({"summary": {"has_changes": True}}),
        _report(True, None),
        json.dumps({"summary": []}),
        json.dumps({"clusters": {}}),
        json.dumps([1, 2]),
    ],
    ids=[
        "empty",
        "not-json",
        "breaking",
        "no-changes",
        "string-flag",
        "breaking-missing",
        "breaking-null",
        "summary-not-an-object",
        "no-summary",
        "not-an-object",
    ],
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
    assert "Traceback" not in result.stdout + result.stderr
    assert _leftover_temp_files(tmp_path) == []


def test_exit_2_report_is_read_from_stdout_alone(tmp_path):
    result, _ = _run(tmp_path, 2, _report(True, False), "UserWarning: something on stderr", "", "reviews")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "note: non-breaking IR change in reviews" in result.stdout


def test_each_context_reads_only_its_own_output(tmp_path):
    report = (2, _report(True, False), "", "")
    result, _ = _run_each(tmp_path, {"reviews": report, "loyalty": report}, "reviews", "loyalty")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "note: non-breaking IR change in reviews" in result.stdout
    assert "note: non-breaking IR change in loyalty" in result.stdout


def test_a_failed_context_fails_the_gate_when_later_ones_pass(tmp_path):
    responses = {
        "reviews": (1, _report(True, True), "", "Breaking Changes (1): ! removed event"),
        "loyalty": (0, _report(False, False), "", ""),
    }
    result, calls = _run_each(tmp_path, responses, "reviews", "loyalty")

    assert result.returncode == 1, result.stdout + result.stderr
    assert "=== BREAKING IR change or ir diff error in reviews (exit 1) ===" in result.stdout
    assert "ok: loyalty" in result.stdout
    assert "IR gate FAILED" in result.stdout


@pytest.mark.parametrize("code", [1, 3])
def test_a_non_breaking_report_passes_only_with_exit_2(tmp_path, code):
    result, _ = _run(tmp_path, code, _report(True, False), "", "", "reviews")

    assert result.returncode == 1, result.stdout + result.stderr
    assert "note: non-breaking" not in result.stdout
    assert "IR gate FAILED" in result.stdout


def test_exit_1_reruns_in_text_format_and_fails(tmp_path):
    text = "Breaking Changes (1): ! removed event Reviews.ReviewSubmitted"
    result, calls = _run(tmp_path, 1, _report(True, True), "", text, "reviews")

    assert result.returncode == 1, result.stdout + result.stderr
    assert [line.split("|")[0] for line in calls] == [
        "--log-level ERROR ir diff --domain=reviews.domain --dir=WORK/reviews --format json",
        "--log-level ERROR ir diff --domain=reviews.domain --dir=WORK/reviews",
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


def test_a_missing_baseline_is_rejected_before_any_run(tmp_path, monkeypatch):
    # A copy of the script in a fake repo whose reviews baseline is missing.
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / "scripts" / "ir-gate.sh").write_text(SCRIPT.read_text())
    (repo / ".protean" / "loyalty").mkdir(parents=True)
    (repo / ".protean" / "loyalty" / "ir.json").write_text("{}")
    monkeypatch.setattr(sys.modules[__name__], "SCRIPT", repo / "scripts" / "ir-gate.sh")

    result, calls = _run(tmp_path, 0, _report(False, False), "", "", "loyalty", "reviews")

    assert result.returncode == 2
    assert "no baseline at .protean/reviews/ir.json" in result.stderr
    assert calls == []
