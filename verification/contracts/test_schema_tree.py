"""Presence checks for the committed schema tree and the IR-based event catalog.

`make schemas` writes a JSON, an Avro and a Protobuf file for every element of every context,
and `make events-catalog` reads the committed IR with no database. These tests fail if a
context loses one of the three formats or if loyalty's IR loses the `CampaignLaunched`
upcaster chain. They do not compare the committed schemas against the code: whether schema
drift should fail CI is a separate decision.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PROTEAN = Path(sys.executable).with_name("protean")
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


def _stems(schemas: Path, suffix: str) -> set[str]:
    return {str(p.relative_to(schemas).with_suffix("")) for p in schemas.rglob(f"*{suffix}")}


@pytest.mark.parametrize("context", CONTEXTS)
def test_every_schema_exists_in_all_three_formats(context: str) -> None:
    schemas = REPO / ".protean" / context / "schemas"
    json_stems = _stems(schemas, ".json")
    assert json_stems, f"no JSON schemas under {schemas}; run `make schemas`"
    assert _stems(schemas, ".avsc") == json_stems
    assert _stems(schemas, ".proto") == json_stems


def test_catalog_lists_campaign_launched_at_v3_with_both_upcasters() -> None:
    result = subprocess.run(
        [
            str(PROTEAN),
            "--log-level",
            "ERROR",
            "events",
            "catalog",
            "--ir",
            str(REPO / ".protean" / "loyalty" / "ir.json"),
            "--json",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    events = json.loads(result.stdout)["data"]["events"]
    matches = [e for e in events if e["name"] == "CampaignLaunched"]
    assert len(matches) == 1, [e["name"] for e in events]
    assert matches[0]["version"] == 3
    assert matches[0]["upcasters"] == [
        {"from_version": 1, "to_version": 2},
        {"from_version": 2, "to_version": 3},
    ]
