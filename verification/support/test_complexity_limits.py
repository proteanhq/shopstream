"""Checks the complexity limits in pyproject.toml: Ruff's cyclomatic check and complexipy's cognitive check.

Each tool runs as a subprocess under the project's config, the way CI and
pre-commit run it. For each Ruff rule (C901, PLR0911, PLR0912, PLR0915) and for
complexipy, a function one past the limit fails and a function at the limit
passes. pyproject.toml writes out each limit. The whole tree passes the Ruff
complexity rules, and src/, tests/ and verification/ pass complexipy.

    uv run pytest verification/support/test_complexity_limits.py --protean-env memory -q
"""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BIN = Path(sys.executable).parent


def _flat_ifs(count: int) -> str:
    """A function with `count` flat `if` statements and one return.

    Its cyclomatic complexity is count + 1 (one path per `if`, plus the straight
    path), it has `count` branches, and its cognitive complexity is count, since
    nothing is nested.
    """
    body = "".join(f"    if x == {i}:\n        total += {i}\n" for i in range(count))
    return f"def flat(x):\n    total = 0\n{body}    return total\n"


def _returns(count: int) -> str:
    """A function with `count` return statements."""
    body = "".join(f"    if x == {i}:\n        return {i}\n" for i in range(count - 1))
    return f"def returns(x):\n{body}    return -1\n"


def _statements(count: int) -> str:
    """A function with `count` statements in its body."""
    body = "".join(f"    x = {i}\n" for i in range(count))
    return f"def statements(x):\n{body}"


def _run(tool: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(BIN / tool), *args], cwd=ROOT, capture_output=True, text=True, check=False)


def _ruff_check(*paths: str) -> subprocess.CompletedProcess[str]:
    # --no-fix: pyproject.toml sets fix = true, and this check must not edit files.
    return _run("ruff", "check", "--no-fix", "--config", str(ROOT / "pyproject.toml"), *paths)


@pytest.mark.parametrize(
    ("code", "source", "fails"),
    [
        ("C901", _flat_ifs(9), False),  # 10 paths
        ("C901", _flat_ifs(10), True),  # 11 paths
        ("PLR0911", _returns(6), False),
        ("PLR0911", _returns(7), True),
        ("PLR0912", _flat_ifs(12), False),
        ("PLR0912", _flat_ifs(13), True),
        ("PLR0915", _statements(50), False),
        ("PLR0915", _statements(51), True),
    ],
    ids=[
        "10-paths",
        "11-paths",
        "6-returns",
        "7-returns",
        "12-branches",
        "13-branches",
        "50-statements",
        "51-statements",
    ],
)
def test_ruff_flags_a_function_past_its_limit(tmp_path, code, source, fails):
    compile(source, "sample.py", "exec")  # a sample that does not parse would carry no rule code either
    sample = tmp_path / "sample.py"
    sample.write_text(source, encoding="utf-8")

    result = _ruff_check(str(sample))

    # Check the rule code, not the exit code: the 12-branch sample still fails C901.
    output = result.stdout + result.stderr
    assert (code in output) == fails, output
    if fails:
        assert result.returncode != 0, output


@pytest.mark.parametrize(("complexity", "fails"), [(15, False), (16, True)])
def test_complexipy_flags_a_function_over_fifteen(tmp_path, complexity, fails):
    sample = tmp_path / "sample.py"
    sample.write_text(_flat_ifs(complexity), encoding="utf-8")

    result = _run("complexipy", str(sample), "--plain")

    output = result.stdout + result.stderr
    assert f"flat {complexity}" in output, f"complexipy did not score the sample at {complexity}: {output}"
    assert (result.returncode != 0) == fails, output


def test_limits_are_written_out():
    # The written-out values equal the tools' defaults, so the samples above pass
    # with or without them. This pins the values a reader sees.
    with (ROOT / "pyproject.toml").open("rb") as f:
        tool = tomllib.load(f)["tool"]
    lint = tool["ruff"]["lint"]
    assert {"C901", "PLR0911", "PLR0912", "PLR0915"} <= set(lint["select"])
    assert "C901" not in lint["ignore"]
    assert lint["mccabe"] == {"max-complexity": 10}
    assert lint["pylint"] == {"max-returns": 6, "max-branches": 12, "max-statements": 50}
    assert tool["complexipy"] == {"paths": ["src", "tests", "verification"], "max-complexity-allowed": 15}


def test_repository_passes_ruff():
    # The whole tree, since the Ruff pre-commit hook lints every staged Python file.
    result = _ruff_check("--select", "C901,PLR0911,PLR0912,PLR0915", ".")
    assert result.returncode == 0, result.stdout + result.stderr


def test_repository_passes_complexipy():
    # No path argument: complexipy reads src, tests and verification from [tool.complexipy].
    result = _run("complexipy", "--plain", "--failed")
    assert result.returncode == 0, result.stdout + result.stderr
