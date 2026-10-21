"""Checks the Protean extras ShopStream installs, and the database drivers they bring.

uv and pip only warn on an extra name a package does not define, so a typo in the
`protean[...]` requirement would install less and nothing would fail. The driver
check needs Postgres and runs only under `--protean-env test`.

    uv run pytest verification/support/test_protean_extras.py --protean-env memory -q
    uv run pytest verification/support/test_protean_extras.py --protean-env test -q
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import os
import re
import tomllib
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from protean.utils.dependencies import FEATURE_EXTRA_MODULES

ROOT = Path(__file__).resolve().parents[2]


def _protean_extras() -> set[str]:
    with (ROOT / "pyproject.toml").open("rb") as f:
        dependencies = tomllib.load(f)["project"]["dependencies"]
    protean = [r for r in map(Requirement, dependencies) if r.name == "protean"]
    assert len(protean) == 1, f"expected one protean requirement, found {len(protean)}"
    return {canonicalize_name(e) for e in protean[0].extras}


def test_every_named_extra_is_defined_by_protean():
    named = _protean_extras()
    assert named, "the protean requirement names no extras"
    defined = {canonicalize_name(e) for e in importlib.metadata.metadata("protean").get_all("Provides-Extra")}
    assert named - defined == set(), f"Protean defines no extra named {sorted(named - defined)}"


@pytest.mark.parametrize("extra", ["server", "shell"])
def test_feature_extra_modules_import(extra):
    assert extra in _protean_extras(), f"pyproject.toml does not name the {extra} extra"
    modules = FEATURE_EXTRA_MODULES[extra]
    assert modules, f"Protean maps no modules to the {extra} extra"
    missing = [m for m in modules if importlib.util.find_spec(m) is None]
    assert missing == [], f"the {extra} extra is named, but {missing} do not import"


# Built-in providers (memory, inline) need no extra.
PROVIDER_EXTRAS = {
    "memory": None,
    "inline": None,
    "postgresql": "postgresql",
    "sqlite": "sqlite",
    "message_db": "message-db",
    "redis": "redis",
}


def _configured(node: object) -> set[str]:
    """Provider names, plus "telemetry" for a telemetry table, anywhere in a domain.toml."""
    if isinstance(node, list):
        return set().union(*map(_configured, node))
    if not isinstance(node, dict):
        return set()
    found = {node["provider"]} if isinstance(node.get("provider"), str) else set()
    if isinstance(node.get("telemetry"), dict):
        found.add("telemetry")
    return found.union(*map(_configured, node.values()))


def test_every_configured_feature_has_its_extra_named():
    # The packages an extra brings can arrive through another one (SQLAlchemy comes
    # with postgresql), so a missing name would go unnoticed until that one is dropped.
    used: set[str] = set()
    for config in sorted((ROOT / "src").glob("*/domain.toml")):
        with config.open("rb") as f:
            used |= _configured(tomllib.load(f))
    assert "telemetry" in used and "postgresql" in used, f"walk found only {sorted(used)}"
    extras = {**PROVIDER_EXTRAS, "telemetry": "telemetry"}
    unknown = used - extras.keys()
    assert unknown == set(), f"add {sorted(unknown)} to PROVIDER_EXTRAS"
    needed = {extras[p] for p in used} - {None}
    assert needed - _protean_extras() == set(), "pyproject.toml does not name these extras"


def test_docker_entrypoint_installs_the_same_extras():
    # The dev image reinstalls Protean from the mounted source, and that install
    # names its extras again. A shorter list there runs only as long as the
    # earlier Poetry step happens to have installed the missing packages.
    script = (ROOT / "docker" / "entrypoint.dev.sh").read_text(encoding="utf-8")
    found = re.findall(r"/protean\[([^\]]+)\]", script)
    assert len(found) == 1, f"expected one /protean[...] install, found {len(found)}"
    assert {canonicalize_name(e.strip()) for e in found[0].split(",")} == _protean_extras()


@pytest.mark.skipif(
    os.environ.get("PROTEAN_ENV") != "test",
    reason="needs real Postgres; run with --protean-env test",
)
@pytest.mark.usefixtures("loyalty_ctx")
def test_plain_postgresql_url_runs_on_psycopg3():
    # message-db-py depends on psycopg2, so both drivers are installed. Without a
    # working psycopg2 this check would not show that Protean prefers psycopg 3.
    import psycopg2  # noqa: F401
    from protean import current_domain

    default = current_domain.providers["default"]
    assert default.conn_info["database_uri"].startswith("postgresql://")
    engine = default._engine
    assert (engine.dialect.name, engine.dialect.driver) == ("postgresql", "psycopg")

    engine = current_domain.providers["reporting"]._engine
    assert (engine.dialect.name, engine.dialect.driver) == ("sqlite", "pysqlite")
