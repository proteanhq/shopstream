"""Negative test for the IR backward-compatibility gate (ticket T0.2).

Proves `make ir-gate` actually catches a breaking contract change instead of
passing silently. Removing a published event from the IR must be classified
breaking and exit non-zero under the committed strict config
(.protean/config.toml -> [compatibility] strictness = "strict").

This guards the guard: without it, a regression that made the gate always
pass (e.g. strictness reverted to "warn", where breaking changes exit 0)
would go unnoticed.
"""

import copy
import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BASELINE = REPO / ".protean" / "reviews" / "ir.json"
PROTEAN = shutil.which("protean")


def _diff_exit_code(left: Path, right: Path) -> int:
    # Run from the repo root so .protean/config.toml (strictness) is picked up.
    return subprocess.run(
        [PROTEAN, "--log-level", "ERROR", "ir", "diff", "--left", str(left), "--right", str(right)],
        cwd=REPO,
        capture_output=True,
        text=True,
    ).returncode


def _drop_first_published_event(node) -> bool:
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("contracts", "events") and isinstance(value, list) and value:
                value.pop(0)
                return True
            if _drop_first_published_event(value):
                return True
    elif isinstance(node, list):
        for item in node:
            if _drop_first_published_event(item):
                return True
    return False


@pytest.mark.skipif(PROTEAN is None, reason="protean CLI not on PATH")
def test_ir_gate_flags_a_breaking_removal(tmp_path):
    baseline = json.loads(BASELINE.read_text())

    breaking = copy.deepcopy(baseline)
    assert _drop_first_published_event(breaking), "no published event found to drop"
    right = tmp_path / "breaking.json"
    right.write_text(json.dumps(breaking))

    # Removing a published event is a breaking change -> exit 1 under strict.
    assert _diff_exit_code(BASELINE, right) == 1, (
        "IR gate did NOT flag a breaking removal (is strictness still 'strict'?)"
    )


@pytest.mark.skipif(PROTEAN is None, reason="protean CLI not on PATH")
def test_ir_gate_passes_on_no_change():
    # Identical IR -> no change -> exit 0.
    assert _diff_exit_code(BASELINE, BASELINE) == 0
