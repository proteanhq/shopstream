"""Every context passes `protean check` at the default `warn` level.

Runs the real CLI, as `make domain-check` does, so each context's `[lint]` table in
its domain.toml (level and suppressions) applies exactly as it does there. A context
fails when the check reports any error or any warning its suppressions do not waive.
Infos never fail it.

Each run is a fresh process, so the check never touches the domains the rest of the
suite has initialised.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PROTEAN = shutil.which("protean")

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


@pytest.mark.parametrize("context", CONTEXTS)
def test_context_passes_protean_check(context):
    assert PROTEAN, "the protean CLI is not on PATH"
    env = {**os.environ, "PYTHONPATH": str(REPO / "src"), "PROTEAN_ENV": "memory"}
    result = subprocess.run(
        [PROTEAN, "--log-level", "ERROR", "check", "-d", f"{context}.domain", "--format", "json"],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
    )
    envelope = json.loads(result.stdout)
    counts = envelope["data"]["counts"]
    warnings = [d for d in envelope["diagnostics"] if d.get("level") == "warning"]
    findings = [f"{d['code']} {d['element']}: {d['message']}" for d in [*envelope["data"]["errors"], *warnings]]

    assert (counts["errors"], counts["warnings"]) == (0, 0), findings
    assert result.returncode == 0, result.stderr
