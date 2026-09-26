"""Logging config: the API reads identity's [logging] config, and no domain.toml overrides it.

Each test that runs a logging setup restores the root logger, the named
loggers' levels and structlog afterwards, so later tests' log capture keeps
working.
"""

import ast
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
    """Return `configure_api_logging` and the identity domain it reads.

    `PROTEAN_ENV` is set to `development`, so the fallback level is DEBUG,
    which differs from the WARNING and ERROR levels the tests assert. The
    domain config is already loaded, so this changes only that fallback. The
    root starts at NOTSET, so a setup that does nothing fails every level
    assertion.
    """
    from api_logging import configure_api_logging
    from identity.domain import identity

    root = logging.getLogger()
    named = {
        name: logger.level
        for name, logger in logging.root.manager.loggerDict.items()
        if isinstance(logger, logging.Logger)
    }
    saved = (root.level, root.handlers[:], root.filters[:], structlog.get_config())

    monkeypatch.setenv("PROTEAN_ENV", "development")
    monkeypatch.delenv("PROTEAN_LOG_LEVEL", raising=False)
    root.setLevel(logging.NOTSET)
    yield configure_api_logging, identity

    level, handlers, filters, structlog_config = saved
    root.setLevel(level)
    root.handlers[:] = handlers
    root.filters[:] = filters
    for name, logger_level in named.items():
        logging.getLogger(name).setLevel(logger_level)
    structlog.configure(**structlog_config)


def test_api_logging_uses_the_domain_toml_level(api_logging, monkeypatch):
    configure_api_logging, identity = api_logging
    monkeypatch.setitem(identity.config["logging"], "level", "WARNING")

    configure_api_logging()

    assert logging.getLogger().level == logging.WARNING


def test_api_logging_reads_identity_not_another_domain(api_logging, monkeypatch):
    from catalogue.domain import catalogue

    configure_api_logging, identity = api_logging
    monkeypatch.setitem(identity.config["logging"], "level", "WARNING")
    monkeypatch.setitem(catalogue.config["logging"], "level", "ERROR")

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


def _module_level_call_lines(tree: ast.Module) -> list[tuple[int, str]]:
    """(line, dotted name) of each call made as a module-level statement."""
    calls = []
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            calls.append((node.lineno, ast.unparse(node.value.func)))
    return calls


def test_app_sets_up_logging_once_before_the_first_domain_init():
    tree = ast.parse((SRC / "app.py").read_text())
    calls = _module_level_call_lines(tree)
    setup_lines = [line for line, name in calls if name == "configure_api_logging"]
    init_lines = [line for line, name in calls if name.endswith(".init")]

    assert len(setup_lines) == 1, calls
    assert init_lines, calls
    assert setup_lines[0] < min(init_lines)


def test_no_domain_toml_declares_logging():
    """Protean's defaults (`level = ""`, `log_dir = ""`) cover every context.

    A context that needs a real override, a `per_logger` level say, adds its
    table on purpose and updates this test.
    """
    tables = []
    for path in sorted(SRC.glob("*/domain.toml")):
        with path.open("rb") as f:
            config = tomllib.load(f)
        context = path.parent.name
        if "logging" in config:
            tables.append(f"src/{context}/domain.toml [logging]")
        tables += [
            f"src/{context}/domain.toml [{env}.logging]"
            for env, table in config.items()
            if isinstance(table, dict) and "logging" in table
        ]

    assert {path.parent.name for path in SRC.glob("*/domain.toml")} == CONTEXTS
    assert tables == [], f"unexpected [logging] tables: {tables}"
