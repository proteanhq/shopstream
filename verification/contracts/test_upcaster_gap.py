"""Negative test for Protean's UPCASTER_GAP check on loyalty's upcaster chain.

`CampaignLaunched` is at v3 and loyalty ships a complete v1->v2->v3 chain, so `protean check`
reports no gap today. That alone proves nothing: a check that never fires is also quiet. This
builds a loyalty domain with the v1->v2 upcaster removed and asserts the check flags the
stranded v1 payloads, then asserts the real loyalty and ordering domains stay clean.

The probe runs `protean check` in a subprocess so the session's shared loyalty domain is never
mutated (every replay test depends on the full chain).
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src"
PROTEAN = shutil.which("protean")

# Imports loyalty with its upcasters registered, then drops the v1->v2 edge from the registry
# before `protean check` builds the IR. `check` re-traverses the package, but the upcasters
# module is already imported, so the edge is not registered again.
GAP_PROBE = """\
from protean.utils import DomainObjects, fqn

from loyalty.campaign.upcasters import UpcastCampaignLaunchedV1ToV2
from loyalty.domain import loyalty

_upcasters = loyalty._domain_registry._elements[DomainObjects.UPCASTER.value]
del _upcasters[fqn(UpcastCampaignLaunchedV1ToV2)]
"""


def _check_diagnostics(domain: str, extra_path: Path | None = None) -> list[dict]:
    paths = [str(SRC)] + ([str(extra_path)] if extra_path else [])
    env = {**os.environ, "PROTEAN_ENV": "memory", "PYTHONPATH": os.pathsep.join(paths)}
    # Exit code is not the signal: existing warnings (unrelated to upcasters) already make
    # `protean check` exit 1 on loyalty. Read the JSON diagnostics instead.
    result = subprocess.run(
        [PROTEAN, "--log-level", "ERROR", "check", "--domain", domain, "--format", "json"],
        cwd=SRC,
        env=env,
        capture_output=True,
        text=True,
    )
    report = json.loads(result.stdout)
    diagnostics = report["diagnostics"]
    assert isinstance(diagnostics, list) and diagnostics, (
        f"`protean check --domain {domain}` returned no diagnostics; the probe is not reading the report"
    )
    return diagnostics


def _upcaster_gaps(diagnostics: list[dict]) -> list[dict]:
    return [d for d in diagnostics if d["code"] == "UPCASTER_GAP"]


@pytest.mark.skipif(PROTEAN is None, reason="protean CLI not on PATH")
def test_missing_v1_upcaster_is_reported(tmp_path):
    (tmp_path / "gap_probe.py").write_text(GAP_PROBE)

    gaps = _upcaster_gaps(_check_diagnostics("gap_probe", extra_path=tmp_path))

    assert len(gaps) == 1, f"Expected one UPCASTER_GAP for CampaignLaunched, got {gaps}"
    gap = gaps[0]
    assert gap["element"] == "loyalty.campaign.events.CampaignLaunched"
    # Only v1 is stranded: the v2->v3 edge is still registered.
    assert "at v1," in gap["message"]
    assert "v2," not in gap["message"]


@pytest.mark.skipif(PROTEAN is None, reason="protean CLI not on PATH")
@pytest.mark.parametrize("domain", ["loyalty.domain", "ordering.domain"])
def test_real_domains_have_no_upcaster_gap(domain):
    assert _upcaster_gaps(_check_diagnostics(domain)) == []
