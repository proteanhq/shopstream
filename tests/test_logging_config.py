"""Logging config: the API reads identity's [logging] table, and the nine tables match.

Each test that runs a logging setup restores the root logger and structlog
afterwards, so later tests' log capture keeps working.
"""

import logging
import tomllib
from pathlib import Path

import pytest
import structlog

SRC = Path(__file__).resolve().parent.parent / "src"
CONTEXTS = {
    "catalogue",
    "fulfillment",
    "identity",
    "inventory",
    "loyalty",
    "notifications",
    "ordering",
    "payments",
    "reviews",
}


@pytest.fixture
def api_logging(monkeypatch):
    """Return app.configure_api_logging and the identity domain it reads.

    Importing `app` initialises the domains, so it happens before the env
    changes below. `PROTEAN_ENV` is then set to `development` so the fallback
    level is DEBUG, apart from the WARNING and ERROR levels the tests assert.
    The domain config is already loaded, so this changes only that fallback.
    The root logger and structlog config are restored afterwards.
    """
    root = logging.getLogger()
    saved = (root.level, root.handlers[:], root.filters[:], structlog.get_config())

    import app

    monkeypatch.setenv("PROTEAN_ENV", "development")
    monkeypatch.delenv("PROTEAN_LOG_LEVEL", raising=False)
    yield app.configure_api_logging, app.identity

    level, handlers, filters, structlog_config = saved
    root.setLevel(level)
    root.handlers[:] = handlers
    root.filters[:] = filters
    structlog.configure(**structlog_config)


def test_api_logging_uses_the_domain_toml_level(api_logging, monkeypatch):
    configure_api_logging, identity = api_logging
    monkeypatch.setitem(identity.config["logging"], "level", "WARNING")

    configure_api_logging()

    assert logging.getLogger().level == logging.WARNING


def test_protean_log_level_overrides_the_domain_toml_level(api_logging, monkeypatch):
    configure_api_logging, identity = api_logging
    monkeypatch.setitem(identity.config["logging"], "level", "WARNING")
    monkeypatch.setenv("PROTEAN_LOG_LEVEL", "ERROR")

    configure_api_logging()

    assert logging.getLogger().level == logging.ERROR


def test_empty_domain_toml_level_falls_back_to_the_env_default(api_logging, monkeypatch):
    configure_api_logging, identity = api_logging
    monkeypatch.setitem(identity.config["logging"], "level", "")

    configure_api_logging()

    assert logging.getLogger().level == logging.DEBUG


def test_api_logging_attaches_the_correlation_filter(api_logging):
    from protean.integrations.logging import ProteanCorrelationFilter

    configure_api_logging, _ = api_logging
    root = logging.getLogger()
    root.filters[:] = []

    configure_api_logging()

    assert [type(f) for f in root.filters if isinstance(f, ProteanCorrelationFilter)] == [ProteanCorrelationFilter]


def test_domain_toml_logging_tables_do_not_drift():
    tables = {}
    for path in sorted(SRC.glob("*/domain.toml")):
        with path.open("rb") as f:
            config = tomllib.load(f)
        if "logging" in config:
            tables[path.parent.name] = config["logging"]

    assert set(tables) == CONTEXTS, f"contexts missing a top-level [logging]: {CONTEXTS - set(tables)}"
    expected = tables["identity"]
    assert expected == {"level": ""}
    for context, table in tables.items():
        assert table == expected, f"src/{context}/domain.toml [logging] differs from identity's: {table}"
