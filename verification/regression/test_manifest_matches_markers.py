"""The `protean_bug` markers and the xfail markers must agree.

An **open** or **tripwire** bug is still in the pin, so its test must carry
`xfail(strict=True)`: strict makes the test fail the moment the fix lands. A
**guard** or **fixed** bug's test protects a fix that is in the pin, so it must
not carry xfail. Without this check a pin bump can promote a test and leave its
marker saying **open**, or the reverse.

The markers are read by collecting the whole suite in a subprocess, through the
same script that prints the manifest (`make regression-manifest`).
"""

from __future__ import annotations

import json
import subprocess
import sys
from functools import cache
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
STATES = {"guard", "open", "tripwire", "fixed"}


@cache
def _collected() -> dict:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "regression_manifest.py"), "--json"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(f"precondition: collecting the markers failed\n{result.stderr[-4000:]}")
    return json.loads(result.stdout)


def _records() -> list[dict]:
    return _collected()["records"]


def _is_xfail(test: str) -> bool:
    return test in _collected()["xfail_tests"]


def test_markers_name_a_known_state_an_issue_and_a_bug():
    bad = [
        r
        for r in _records()
        if r["state"] not in STATES
        or not (r["issue"] is None or isinstance(r["issue"], int))
        or not (isinstance(r["bug"], str) and r["bug"].strip())
    ]
    assert bad == []


def test_open_and_tripwire_tests_are_strict_xfail_and_the_rest_are_not():
    states = {r["state"] for r in _records()}
    if not {"open", "guard"} <= states:
        pytest.fail(f"precondition: the markers have both open and guard bugs, got {sorted(states)}")

    expected = {"open": {"strict": True}, "tripwire": {"strict": True}}
    mismatched = [(r["state"], r["test"]) for r in _records() if r["xfail"] != expected.get(r["state"])]
    assert mismatched == []


def test_every_xfail_test_has_a_protean_bug_marker():
    marked = {r["test"] for r in _records()}
    unmarked = [t for t in _collected()["xfail_tests"] if t not in marked]
    assert unmarked == []


def test_is_xfail_reads_the_marker():
    assert _is_xfail("verification/regression/test_persistence.py::test_outer_commit_of_a_doomed_transaction_raises")
    assert not _is_xfail(
        "verification/regression/test_tooling.py::test_server_single_worker_applies_domain_toml_logging_level"
    )


def _fake_item(nodeid: str, *marks: pytest.MarkDecorator) -> SimpleNamespace:
    found = [m.mark for m in marks]
    return SimpleNamespace(
        nodeid=nodeid,
        get_closest_marker=lambda name: next((m for m in found if m.name == name), None),
        iter_markers=lambda name: (m for m in found if m.name == name),
    )


def test_collector_keeps_each_parametrized_case():
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        from regression_manifest import _Collector
    finally:
        sys.path.remove(str(ROOT / "scripts"))

    bug = pytest.mark.protean_bug(issue=1, state="open", bug="b")
    collector = _Collector()
    collector.pytest_collection_modifyitems(
        [
            _fake_item("t.py::test_x[a]", bug, pytest.mark.xfail(strict=True)),
            _fake_item("t.py::test_x[b]", bug, pytest.mark.xfail(strict=False)),
            _fake_item("t.py::test_x[c]", pytest.mark.xfail(strict=True)),
        ]
    )

    assert collector.xfail_tests == {"t.py::test_x[a]", "t.py::test_x[b]", "t.py::test_x[c]"}
    assert [(r["test"], r["xfail"]) for r in collector.records] == [
        ("t.py::test_x[a]", {"strict": True}),
        ("t.py::test_x[b]", {"strict": False}),
    ]
