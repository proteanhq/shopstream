"""Regressions in domain setup and tooling: `current_domain`, config loading, `protean check`, `protean server` and `protean verify`."""

from __future__ import annotations

import sys
import warnings

import pytest


@pytest.mark.protean_bug(
    issue=1632,
    state="open",
    bug=(
        '`current_domain` has no warning-free probe: `getattr`/`isinstance` outside a context warn "Working outside of'
        ' domain context" (pytest collection). Predates the 0.16.0 → main bump.'
    ),
)
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="current_domain warns 'Working outside of domain context' on attribute and type probes",
)
def test_current_domain_probe_outside_context_is_silent():
    """Protean finding (proteanhq/protean#1632, feature request): `current_domain` has no warning-free probe.

    Test modules import `current_domain` at module level. During collection pytest
    runs `getattr(obj, "__test__", None)` (`_pytest/compat.py`) and `isinstance`
    checks over every module attribute. With no domain context active, both go
    through the proxy's `_find_domain()` and emit the "Working outside of domain
    context" `UserWarning`, so collection prints it for each module in `tests/` that does so.

    The proxy's docstring promises None-like results outside a context, not
    silence, and Protean's own tests assert that `bool`/`repr` warn. So this is a
    request for a probe that stays quiet (as `_domain_now()` already reads the
    stack without warning), not a regression. `pyproject.toml` filters the warning
    for the suite.
    """
    from protean import current_domain
    from protean.utils.globals import _domain_context_stack

    if _domain_context_stack.top is not None:
        pytest.fail("precondition: no domain context may be active")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        test_attr = getattr(current_domain, "__test__", None)
        is_type = isinstance(current_domain, type)

    assert test_attr is None
    assert is_type is False
    messages = [str(w.message) for w in caught]
    assert not any("outside of domain context" in m for m in messages), messages


@pytest.mark.protean_bug(
    issue=1629,
    state="guard",
    bug=(
        "A top-level `[lint]` table in `domain.toml` was dropped by the config loader, while an env overlay "
        "(`[test.lint]`) loaded. The key filter was applied to one and not the other. Fixed in proteanhq/protean#1646 "
        "(`c421861`)."
    ),
)
def test_lint_table_in_domain_toml_is_loaded(tmp_path, monkeypatch):
    """proteanhq/protean#1629 (guard): a top-level `[lint]` table in `domain.toml` is loaded.

    Protean's configuration docs describe a `[lint]` table (`level`, `suppressions`,
    and more) that `protean check` and `protean verify` read through
    `domain.config.get("lint", {})`. `Config2._normalize_config` used to keep only
    the top-level keys that `_default_config()` defines, and `lint` was not one of
    them, so a top-level `[lint]` was discarded. An environment overlay such as
    `[test.lint]` was deep-merged without that key filter, so it did load. Fixed
    in proteanhq/protean#1646 (`c421861`).
    """
    from protean.domain.config import Config2

    (tmp_path / "domain.toml").write_text('debug = true\n\n[lint]\nlevel = "error"\n\n[test.lint]\nlevel = "error"\n')

    monkeypatch.setenv("PROTEAN_ENV", "test")
    overlay = Config2.load_from_path(str(tmp_path))
    if overlay.get("lint", {}).get("level") != "error":
        pytest.fail("precondition: the [test.lint] overlay should load")

    monkeypatch.delenv("PROTEAN_ENV")
    config = Config2.load_from_path(str(tmp_path))

    if config["debug"] is not True:
        pytest.fail("precondition: the domain.toml was read")
    assert config.get("lint", {}).get("level") == "error"


@pytest.mark.protean_bug(
    issue=1911,
    state="open",
    bug=(
        "`protean check` reports `AGGREGATE_WITHOUT_COMMAND_HANDLER` for an aggregate declared with `abstract=True`. "
        "Protean accepts a command handler for one, but an abstract aggregate is never loaded or saved, so the handler"
        " would have nothing to act on. The rule skips only `protean.adapters.*`, while its sibling cluster rules skip"
        " abstract aggregates through `_abstract_aggregate_fqns()`. Loyalty's `Auditable` base trips it; "
        "`src/loyalty/domain.toml` suppresses it."
    ),
)
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="AGGREGATE_WITHOUT_COMMAND_HANDLER flags abstract aggregates, which are never loaded or saved",
)
def test_abstract_aggregate_is_not_flagged_without_command_handler():
    """proteanhq/protean#1911: `protean check` flags an abstract aggregate.

    An aggregate declared with `abstract=True` is a base for concrete aggregates. It is
    never loaded or saved, so a command handler for it would have nothing to act on. `IRBuilder._diagnose_aggregate_without_command_handler`
    walks every cluster and skips only `protean.adapters.*`, so it reports the base as
    an aggregate with no write path. Its sibling cluster rules filter abstract
    aggregates out through `_abstract_aggregate_fqns()`. Loyalty's `Auditable` base
    trips this rule, and `src/loyalty/domain.toml` suppresses it.
    """
    from protean import Domain, handle
    from protean.fields import String

    domain = Domain(name="AbstractAggregateCheckProbe")

    @domain.aggregate(abstract=True)
    class Tracked:
        created_by = String(max_length=50)

    @domain.aggregate
    class Ticket(Tracked):
        title = String(required=True)

    @domain.command(part_of=Ticket)
    class OpenTicket:
        title = String(required=True)

    @domain.command_handler(part_of=Ticket)
    class TicketCommandHandler:
        @handle(OpenTicket)
        def open_ticket(self, command):  # noqa: ARG002
            pass

    # A concrete aggregate with no handler, so the rule has one finding it must make.
    @domain.aggregate
    class Orphan:
        name = String()

    report = domain.check(traverse=False)

    if report["counts"]["errors"]:
        pytest.fail(f"precondition: the probe domain has no errors: {report['errors']}")
    flagged = [d["element"] for d in report["diagnostics"] if d["code"] == "AGGREGATE_WITHOUT_COMMAND_HANDLER"]
    if not any(element.endswith(".Orphan") for element in flagged):
        pytest.fail(f"precondition: the rule flags a concrete aggregate with no handler: {flagged}")
    assert not any(element.endswith(".Tracked") for element in flagged), flagged


@pytest.fixture
def bare_root_logger():
    """Give the test a root logger with no handlers at NOTSET, and restore it afterwards.

    pytest's log capture puts handlers on the root logger. `Domain.init()` skips
    its own logging setup when the root has handlers, so leaving them in place
    would hide a Protean fix. NOTSET means a run where nothing sets up logging
    cannot match the probe level by accident.
    """
    import logging

    import structlog

    root = logging.getLogger()
    named = {
        name: logger.level
        for name, logger in logging.root.manager.loggerDict.items()
        if isinstance(logger, logging.Logger)
    }
    saved = (root.level, root.handlers[:], root.filters[:], structlog.get_config())
    root.handlers[:] = []
    root.setLevel(logging.NOTSET)
    yield root
    level, handlers, filters, structlog_config = saved
    root.setLevel(level)
    root.handlers[:] = handlers
    root.filters[:] = filters
    for name, logger_level in named.items():
        logging.getLogger(name).setLevel(logger_level)
    structlog.configure(**structlog_config)


@pytest.mark.protean_bug(
    issue=1635,
    state="guard",
    bug=(
        '`protean server` with one worker calls `configure_logging(level=PROTEAN_LOG_LEVEL or "INFO")` before '
        "`Domain.init()`. Init then found root handlers and skipped all of `Domain.configure_logging`: the `[logging]`"
        " level, redaction, the correlation processor and filter, the OpenTelemetry processor and `per_logger`. So "
        "engine logs carried no `correlation_id`. `protean observatory` had the same gap. Fixed in "
        "proteanhq/protean#1640 (`e79a817`): both commands now call `apply_domain_logging` after the domain loads, "
        "which replaces the early setup. `protean observatory` applies only the first `--domain`'s `[logging]`. The "
        "guard covers the server path only and checks the level and the correlation filter."
    ),
)
def test_server_single_worker_applies_domain_toml_logging_level(tmp_path, monkeypatch, bare_root_logger):
    """proteanhq/protean#1635 (guard): `protean server` applies `[logging]` from `domain.toml`.

    With one worker (the default, and how every ShopStream engine runs), the
    `server` command calls
    `configure_logging(level=os.getenv("PROTEAN_LOG_LEVEL", "INFO"))` before it
    loads the domain. Before the fix, `Domain.init()` then found handlers on the
    root logger and skipped all of `Domain.configure_logging`: the `[logging]`
    level, redaction, the correlation processor and filter, the OpenTelemetry
    processor and `per_logger`, so engine logs carried no `correlation_id`.
    `protean observatory` had the same gap. The fix (proteanhq/protean#1640)
    makes both commands call `apply_domain_logging` after the domain loads,
    which replaces that early setup with the domain's `[logging]`. It arrived
    with the pin bump to Protean main e79a817, so this is now a permanent guard.

    The probe level is ERROR, not a default level, so a Protean change that
    stops setting up logging at all does not pass by accident. The test also
    checks for the correlation filter, so a fix that applies only the level
    does not pass.
    """
    import logging

    import protean.cli
    from protean.integrations.logging import ProteanCorrelationFilter
    from typer.testing import CliRunner

    class _StoppedEngine:
        def __init__(self, *_args, **_kwargs):
            self.exit_code = 0

        def run(self):
            pass

    (tmp_path / "domain.toml").write_text('[logging]\nlevel = "ERROR"\n')
    (tmp_path / "logging_probe_domain.py").write_text(
        'from protean import Domain\n\nprobe = Domain(name="LoggingProbe")\n'
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DOMAIN_ROOT_PATH", raising=False)
    monkeypatch.delenv("PROTEAN_LOG_LEVEL", raising=False)
    monkeypatch.delenv("PROTEAN_NO_AUTO_LOGGING", raising=False)
    monkeypatch.setattr(protean.cli, "Engine", _StoppedEngine)
    monkeypatch.delitem(sys.modules, "logging_probe_domain", raising=False)

    result = CliRunner().invoke(protean.cli.app, ["server", "--domain", "logging_probe_domain"])
    module = sys.modules.pop("logging_probe_domain", None)

    if result.exit_code != 0:
        pytest.fail(f"precondition: protean server ran and exited cleanly\n{result.output}\n{result.exception!r}")
    if module is None or module.probe.config["logging"]["level"] != "ERROR":
        pytest.fail("precondition: the probe domain loaded its domain.toml")
    assert bare_root_logger.level == logging.ERROR, logging.getLevelName(bare_root_logger.level)
    assert any(isinstance(f, ProteanCorrelationFilter) for f in bare_root_logger.filters), bare_root_logger.filters


def _pytest_project(tmp_path, test_source: str, ini: str = "") -> str:
    """A small pytest project in `tmp_path`, cut off from ShopStream's pytest config."""
    (tmp_path / "pytest.ini").write_text(f"[pytest]\n{ini}")
    (tmp_path / "test_probe.py").write_text(test_source)
    return str(tmp_path)


@pytest.mark.protean_bug(
    issue=1662,
    state="guard",
    bug=(
        "`protean verify`'s tests stage removed `PROTEAN_ENV` from the pytest subprocess, so init and check ran under "
        "the caller's env while the tests ran under the plugin default (`test`, Postgres). Fixed in "
        "proteanhq/protean#1810 (`29e1252`): `--env` now sets the environment for all three stages. "
        "`scripts/verify-domains.sh` passes `--env memory`."
    ),
)
def test_verify_tests_stage_keeps_protean_env(tmp_path, monkeypatch):
    """proteanhq/protean#1662 (guard): `protean verify` keeps `PROTEAN_ENV` for its tests stage.

    `_run_tests` in `protean/cli/verify.py` used to pop `PROTEAN_ENV` (and
    `PROTEAN_DEBUG`, `VIRTUAL_ENV`) from the environment it handed to
    `python -m pytest`. The init and check stages run in the verify process and
    did see `PROTEAN_ENV`. So `PROTEAN_ENV=memory protean verify` inited and
    checked under `memory` and then tested under Protean's pytest plugin default,
    `test`, which points at Postgres. Fixed in proteanhq/protean#1810 (`29e1252`):
    `--env` names one environment for all three stages, and `_run_tests` hands it
    to the pytest child even when the shell exports a different `PROTEAN_ENV`.
    """
    from protean.cli.verify import _run_tests

    project = _pytest_project(
        tmp_path,
        "import os\n\ndef test_env():\n    assert os.environ.get('PROTEAN_ENV') == 'memory'\n",
    )
    monkeypatch.delenv("PYTEST_ADDOPTS", raising=False)
    monkeypatch.setenv("PROTEAN_ENV", "test")

    stage, output = _run_tests(project, "memory")

    if stage["passed"] + stage["failed"] != 1:
        pytest.fail(f"precondition: the probe test ran once\n{output}")
    assert stage["status"] == "pass", output


@pytest.mark.protean_bug(
    issue=1661,
    state="guard",
    bug=(
        "`protean verify` took the failed-test count from the first `<N> failed` anywhere in pytest's output, so a "
        'failure message such as psycopg2\'s "port 15432 failed" was reported as 15432 failures. The pass/fail status '
        "was right. Fixed in proteanhq/protean#1801 (`0a5103f`)."
    ),
)
def test_verify_tests_stage_counts_failures_from_the_summary(tmp_path, monkeypatch):
    """proteanhq/protean#1661 (guard): `protean verify` reads the failure count from the summary line.

    `_run_tests` used to read the counts with `re.search(r"(\\d+) failed", output)`,
    which matches the first hit anywhere in pytest's output, not the summary line.
    A failure message that contains "<number> failed" won. Seen in ShopStream: with
    the tests stage under the `test` env and no Postgres running, `verify -d
    identity.domain` reported `"failed": 15432`, taken from psycopg2's
    "connection to server at "localhost", port 15432 failed". The status comes
    from the return code, so only the count was wrong. Fixed in
    proteanhq/protean#1801 (`0a5103f`).
    """
    from protean.cli.verify import _run_tests

    project = _pytest_project(
        tmp_path,
        "def test_db():\n    raise AssertionError('connection to server on port 15432 failed')\n",
    )
    monkeypatch.delenv("PYTEST_ADDOPTS", raising=False)

    stage, output = _run_tests(project, "memory")

    if stage["status"] != "fail" or "1 failed" not in output:
        pytest.fail(f"precondition: the probe test ran and failed\n{output}")
    assert stage["failed"] == 1


@pytest.mark.protean_bug(
    issue=1661,
    state="guard",
    bug=(
        "`protean verify` took the passed-test count from the first `<N> passed` anywhere in pytest's output. With "
        '`-ra` in addopts, a skip reason such as "0 passed on this platform" was read as the count. '
        "`scripts/verify-domains.sh` gates on `passed > 0`, so this count feeds its gate. Fixed in "
        "proteanhq/protean#1801 (`0a5103f`)."
    ),
)
def test_verify_tests_stage_counts_passes_from_the_summary(tmp_path, monkeypatch):
    """proteanhq/protean#1661 (guard): `protean verify` reads the passed count from the summary line.

    `_run_tests` used to read the passed count with `re.search(r"(\\d+) passed", output)`,
    the same first-match read as the failed count. With `-ra` in a project's addopts
    (ShopStream has it), pytest prints skip reasons before the summary line, so a reason
    such as "0 passed on this platform" was read as the passed count. `scripts/verify-domains.sh`
    fails a context whose tests stage passed zero tests, so this count feeds its gate.
    Fixed in proteanhq/protean#1801 (`0a5103f`).
    """
    from protean.cli.verify import _run_tests

    project = _pytest_project(
        tmp_path,
        "import pytest\n\n"
        "def test_ok():\n    pass\n\n"
        "@pytest.mark.skip(reason='0 passed on this platform')\n"
        "def test_skipped():\n    pass\n",
        ini="addopts = -ra\n",
    )
    monkeypatch.delenv("PYTEST_ADDOPTS", raising=False)

    stage, output = _run_tests(project, "memory")

    if stage["status"] != "pass" or "1 passed, 1 skipped" not in output:
        pytest.fail(f"precondition: one test passed and one was skipped\n{output}")
    assert stage["passed"] == 1


@pytest.mark.protean_bug(
    issue=1630,
    state="guard",
    bug=(
        "The `is_event_sourced` deprecation warning was attributed to `protean/domain/__init__.py` instead of the "
        "decorator that used the option (`stacklevel` one frame short). Fixed in proteanhq/protean#1643 (`3dd06a4`)."
    ),
)
def test_is_event_sourced_warning_points_at_the_decorator():
    """proteanhq/protean#1630 (guard): the `is_event_sourced` warning names the caller's line.

    Registering an element with the deprecated `is_event_sourced=True` warns. The
    warning's file and line used to be Protean's own `_domain_element.wrap` in
    `protean/domain/__init__.py`, not the `@domain.aggregate(...)` line that used
    the option, because the `stacklevel` stopped one frame short. The fix
    (proteanhq/protean#1643) arrived with the pin bump to Protean main e79a817,
    so this is now a permanent guard.
    """
    from protean import Domain
    from protean.fields import String

    domain = Domain(name="StacklevelProbe")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")

        @domain.aggregate(is_event_sourced=True)
        class Probe:
            name = String()

    deprecations = [w for w in caught if "is_event_sourced" in str(w.message)]
    if not deprecations:
        pytest.fail("precondition: the deprecation warning was raised")
    assert deprecations[0].filename == __file__, deprecations[0].filename
