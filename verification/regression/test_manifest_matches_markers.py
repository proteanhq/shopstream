"""The README manifest and the xfail markers must agree.

An **open** row's test documents a bug still in the pin, so it must carry an
xfail marker. A **guard** row's test protects a fix that is in the pin, so it
must not. Without this check a pin bump can promote a test and leave its README
row saying **open**, or the reverse.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from verification.regression import test_protean_regressions

README = Path(__file__).with_name("README.md")
ROW = re.compile(r"^\| [^|]+ \| \*\*(open|guard)\*\*[^|]* \| [^|]+ \| `regression/test_protean_regressions\.py::(\w+)`")


def _manifest_rows() -> list[tuple[str, str]]:
    return [m.groups() for line in README.read_text().splitlines() if (m := ROW.match(line))]


def _is_xfail(test_name: str) -> bool:
    test = getattr(test_protean_regressions, test_name)
    return any(mark.name == "xfail" for mark in getattr(test, "pytestmark", []))


def test_open_rows_are_xfail_and_guard_rows_are_not():
    rows = _manifest_rows()
    states = {state for state, _ in rows}
    if states != {"open", "guard"}:
        pytest.fail(f"precondition: the manifest has both open and guard rows, got {sorted(states)}")

    mismatched = [(state, name) for state, name in rows if _is_xfail(name) != (state == "open")]
    assert mismatched == []


def test_is_xfail_reads_the_marker():
    assert _is_xfail("test_outer_commit_of_a_doomed_transaction_raises")
    assert not _is_xfail("test_server_single_worker_applies_domain_toml_logging_level")
