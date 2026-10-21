"""Print the Protean regression manifest, built from `protean_bug` markers.

Every test that guards a Protean bug ShopStream found carries
`@pytest.mark.protean_bug(issue=..., state=..., bug=...)`. This script collects
`verification/` and `tests/` (collection only, no test runs) and prints one
markdown row per bug, sorted by issue number.

The table is not committed: a committed copy would be edited by every PR that
adds a regression, and those PRs would clash on it.

Usage:
    python scripts/regression_manifest.py          # markdown table
    python scripts/regression_manifest.py --json   # the collected markers, for checks
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PATHS = ["verification", "tests"]
ISSUE_URL = "https://github.com/proteanhq/protean/issues/{}"


def _without_params(nodeid: str) -> str:
    return nodeid.split("[", 1)[0]


class _Collector:
    def __init__(self) -> None:
        self.records: list[dict] = []
        self.file_tests: dict[str, set[str]] = defaultdict(set)
        self.xfail_tests: set[str] = set()

    def pytest_collection_modifyitems(self, items):
        for item in items:
            # Checks need every parametrized case, since a mark can sit on one case only.
            # Cases are folded into one test only when rendering.
            path = item.nodeid.partition("::")[0]
            self.file_tests[path].add(_without_params(item.nodeid))
            xfail = item.get_closest_marker("xfail")
            if xfail is not None:
                self.xfail_tests.add(item.nodeid)
            for mark in item.iter_markers("protean_bug"):
                self.records.append(
                    {
                        "test": item.nodeid,
                        "file": path,
                        "issue": mark.kwargs.get("issue"),
                        "state": mark.kwargs.get("state"),
                        "bug": mark.kwargs.get("bug"),
                        "xfail": None if xfail is None else {"strict": bool(xfail.kwargs.get("strict", False))},
                    }
                )


def collect() -> dict:
    """Collect every marked test, the test count per file, and every xfail test."""
    os.environ.setdefault("PROTEAN_ENV", "memory")
    collector = _Collector()
    args = ["--collect-only", "-q", "-p", "no:cacheprovider", "--protean-env", os.environ["PROTEAN_ENV"], *PATHS]
    cwd = os.getcwd()
    saved = os.dup(1)
    # pytest writes the collected node IDs to fd 1; keep them out of the table.
    with tempfile.TemporaryFile("w+") as log:
        os.dup2(log.fileno(), 1)
        os.chdir(ROOT)
        try:
            code = pytest.main(args, plugins=[collector])
        finally:
            sys.stdout.flush()
            os.dup2(saved, 1)
            os.close(saved)
            os.chdir(cwd)
        if code != 0:
            log.seek(0)
            sys.stderr.write(log.read())
            raise SystemExit(f"pytest collection failed with exit code {code}")

    counts = {path: len(names) for path, names in collector.file_tests.items()}
    return {"records": collector.records, "counts": counts, "xfail_tests": sorted(collector.xfail_tests)}


def render(records: list[dict], counts: dict[str, int]) -> str:
    rows: dict[tuple, list[str]] = defaultdict(list)
    for r in records:
        rows[(r["issue"], r["state"], r["bug"])].append(_without_params(r["test"]))

    def sort_key(row):
        (issue, _, _), tests = row
        return (issue is None, issue or 0, min(tests))

    lines = ["| Issue | State | Bug | Guard |", "|-------|-------|-----|-------|"]
    for (issue, state, bug), tests in sorted(rows.items(), key=sort_key):
        by_file: dict[str, list[str]] = defaultdict(list)
        for test in sorted(set(tests)):
            by_file[test.split("::", 1)[0]].append(test)
        guards = []
        for path, file_tests in by_file.items():
            # A file whose every test guards this bug is listed once, by path.
            guards += [path] if len(file_tests) == counts.get(path) else file_tests
        cell = f"[#{issue}]({ISSUE_URL.format(issue)})" if issue is not None else "not filed yet"
        guard = ", ".join(f"`{g}`" for g in guards)
        lines.append(f"| {cell} | **{state}** | {bug.replace('|', chr(92) + '|')} | {guard} |")
    return "\n".join(lines)


def main() -> None:
    collected = collect()
    if "--json" in sys.argv[1:]:
        print(json.dumps(collected, indent=2))
    else:
        print(render(collected["records"], collected["counts"]))


if __name__ == "__main__":
    main()
