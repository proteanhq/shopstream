"""Named regressions for Protean bugs ShopStream found (the T1.5 habit).

Every Protean bug ShopStream surfaces becomes ONE permanent, named test here (or
an oracle, cross-referenced in README.md). The naming is `test_<issue>_<slug>` so
the guard and the upstream issue are one click apart.

Lifecycle of a regression:

  1. Bug found → filed upstream → a test added here that asserts the CORRECT
     (post-fix) behavior.
  2. While the installed Protean still has the bug, the test is `xfail(strict)` —
     it documents the bug and, because it is strict, flips loudly (xpass → failure)
     the moment the fix lands, prompting us to drop the marker.
  3. Once the fix is in ShopStream's Protean pin, the marker is removed and the
     test becomes a permanent green guard against regression.

See README.md for the full manifest (every filed issue → its guard → status).
"""

from __future__ import annotations

import os
import sys
import warnings
from datetime import datetime

import pytest

ENV = os.environ.get("PROTEAN_ENV")


def _earn_points_row():
    """Process a published-event command; return its PointsEarned outbox row."""
    import uuid

    from protean import current_domain

    from loyalty.reward.enrollment import EnrollRewardAccount
    from loyalty.reward.points import EarnPoints

    account_id = current_domain.process(
        EnrollRewardAccount(customer_id=f"cust-reg-{uuid.uuid4().hex[:8]}"), asynchronous=False
    )
    current_domain.process(EarnPoints(account_id=account_id, amount=120, reason="order"), asynchronous=False)

    rows = current_domain._get_outbox_repo("default").find_unprocessed()
    return next(r for r in rows if r.type == "Loyalty.PointsEarned.v1" and r.data.get("account_id") == account_id)


@pytest.mark.usefixtures("loyalty_ctx")
def test_1039_event_datetime_serialized_as_iso_utc():
    """proteanhq/protean#1039 (FIXED): datetime payloads are ISO-8601, UTC-normalized.

    The bug serialized datetimes with `str()` — naive, timezone-lossy, and in a
    different format from the metadata. The fix emits `.isoformat()` in UTC. This
    guards against a regression to `str()`.
    """
    row = _earn_points_row()
    raw = row.data["occurred_at"]

    # Must be a parseable ISO-8601 string (not str(datetime), not a bare object).
    assert isinstance(raw, str)
    parsed = datetime.fromisoformat(raw)  # raises if it regressed to str()/non-ISO

    # ...and timezone-aware, normalized to UTC (offset zero).
    assert parsed.tzinfo is not None, f"datetime lost its timezone: {raw!r}"
    assert parsed.utcoffset().total_seconds() == 0, f"datetime not UTC-normalized: {raw!r}"


@pytest.mark.skipif(
    ENV == "test",
    reason="#1071 is about the in-memory adapter; the relational path is covered by test_outbox_exactly_once",
)
@pytest.mark.usefixtures("loyalty_ctx")
def test_1071_memory_adapter_enforces_unique_index():
    """proteanhq/protean#1071 (guard): the in-memory adapter enforces Index(unique=True).

    Was a tripwire (xfail) while the fix was upstream-only; the pin bump to Protean
    main (#1074) landed it, so this is now a permanent guard against regression.
    """
    from protean import current_domain
    from protean.utils.outbox import Outbox

    row = _earn_points_row()
    duplicate = Outbox.create_message(
        message_id=row.message_id,
        stream_name=row.stream_name,
        message_type=row.type,
        data=row.data,
        metadata=row.metadata_,
        target_broker=row.target_broker,  # same composite unique key
    )

    rejected = False
    try:
        current_domain._get_outbox_repo("default")._dao.save(duplicate)
    except Exception:
        rejected = True
    assert rejected, "in-memory adapter accepted a row that violates the (message_id, target_broker) unique index"


@pytest.mark.usefixtures("inventory_ctx")
def test_1078_all_default_value_object_round_trips():
    """proteanhq/protean#1078 (guard): an all-default ValueObject survives event replay.

    An event-sourced aggregate whose ValueObject had only falsy fields (every
    `StockLevels` count at 0) came back as `None` after a persist and reload. The
    fix touched both the attribute setter (`ValueObject.__set__`) and
    serialization (`to_dict`), so the test checks the reloaded attribute and its
    serialized form. The fix arrived with the pin bump to Protean main 6b4cd312
    (after 0.17.0), so this is now a permanent guard.
    """
    import uuid

    from protean import current_domain

    from inventory.stock.stock import InventoryItem, StockLevels

    item = InventoryItem.create(
        product_id=str(uuid.uuid4()),
        variant_id=str(uuid.uuid4()),
        warehouse_id=str(uuid.uuid4()),
        sku=f"SKU-{uuid.uuid4().hex[:8]}",
        initial_quantity=0,
        reorder_point=0,
    )
    repo = current_domain.repository_for(InventoryItem)
    repo.add(item)

    reloaded = repo.get(item.id)
    assert reloaded.levels == StockLevels(on_hand=0, reserved=0, available=0, in_transit=0, damaged=0)
    assert reloaded.to_dict()["levels"] == {
        "on_hand": 0,
        "reserved": 0,
        "available": 0,
        "in_transit": 0,
        "damaged": 0,
    }


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
    context" `UserWarning`, so collection prints it for 9 modules in `tests/`.

    The proxy's docstring promises None-like results outside a context, not
    silence, and Protean's own tests assert that `bool`/`repr` warn. So this is a
    request for a probe that stays quiet (as `_domain_now()` already reads the
    stack without warning), not a regression. The warning predates this pin: it
    showed on Protean 0.16.0 too, and `pyproject.toml` filters it for the suite.
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


REVIEWS_IR = os.path.join(os.path.dirname(__file__), "..", "..", ".protean", "reviews", "ir.json")


def _ir_diff(*args: str):
    import protean.cli
    from typer.testing import CliRunner

    return CliRunner().invoke(protean.cli.app, ["ir", "diff", *args])


def _plain(result) -> str:
    """Return the CLI output without ANSI styling.

    Rich colours the output on CI even under CliRunner, and it styles each dash-separated
    part of an option name separately, so a plain substring check fails there.
    """
    import click

    return click.unstyle(result.output)


def _reviews_ir_without_a_projection(tmp_path) -> str:
    """Write the reviews baseline with one projection removed, and return its path.

    Diffing it against the baseline gives a real change in either direction: an added
    projection is safe, and a removed one is breaking.
    """
    import json

    with open(REVIEWS_IR) as fh:
        ir = json.load(fh)
    if not ir["projections"]:
        pytest.fail("precondition: the reviews baseline has a projection to remove")
    del ir["projections"][next(iter(ir["projections"]))]
    path = tmp_path / "reviews-ir.json"
    path.write_text(json.dumps(ir))
    return str(path)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="ir diff exits 2 for non-breaking changes, the code Click uses for a usage error",
)
def test_ir_diff_usage_error_does_not_share_the_non_breaking_exit_code(tmp_path):
    """proteanhq/protean#1912: `ir diff` gives two outcomes one exit code.

    `protean ir diff` documents exit 2 as "non-breaking changes only". Click exits 2
    for a usage error, such as an unknown option. A CI gate that reads exit 2 as a safe
    change therefore passes when its own command line is broken: the old `make ir-gate`
    recipe would report a non-breaking change for a misspelled `--dir=`, though no diff
    ran. `scripts/ir-gate.sh` works around it by accepting exit 2 only with a JSON
    report whose summary says there are changes and none is breaking.

    The test compares the two codes rather than pinning either one, so it flips
    whichever of them Protean moves.
    """
    import json

    safe = _ir_diff(
        "--left",
        _reviews_ir_without_a_projection(tmp_path),
        "--right",
        REVIEWS_IR,
        "--dir",
        str(tmp_path),
        "--format",
        "json",
    )
    usage = _ir_diff("--no-such-flag")

    summary = json.loads(safe.stdout)["summary"]
    if safe.exit_code == 0 or not summary["has_changes"] or summary["has_breaking_changes"]:
        pytest.fail(f"precondition: an added projection is a non-breaking change\n{safe.output}")
    if usage.exit_code == 0 or "No such option: --no-such-flag" not in _plain(usage):
        pytest.fail(f"precondition: ir diff rejected the unknown option\n{usage.output}")
    assert usage.exit_code != safe.exit_code


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="ir diff exits 1 both for a breaking change and for a baseline it cannot load",
)
def test_ir_diff_load_error_does_not_share_the_breaking_exit_code(tmp_path):
    """proteanhq/protean#1912: `ir diff` exits 1 for two outcomes too.

    It exits 1 for a breaking change, and also for an error before any diff runs, such
    as a missing baseline file. Protean's CLI convention keeps exit 2 for an environment error. `ir diff` raises
    `typer.Abort()` for these errors, which exits 1. A gate cannot tell from the code
    alone whether it found a breaking change or never compared anything.
    `scripts/ir-gate.sh` reruns the diff in text format on exit 1 so the reason is
    printed either way.
    """
    breaking = _ir_diff(
        "--left", REVIEWS_IR, "--right", _reviews_ir_without_a_projection(tmp_path), "--dir", str(tmp_path)
    )
    missing = str(tmp_path / "missing.json")
    load_error = _ir_diff("--left", missing, "--right", REVIEWS_IR, "--dir", str(tmp_path))

    if breaking.exit_code == 0 or "Breaking Changes" not in _plain(breaking):
        pytest.fail(f"precondition: a removed projection is a breaking change\n{breaking.output}")
    if load_error.exit_code == 0 or "file not found" not in _plain(load_error):
        pytest.fail(f"precondition: ir diff reported the missing baseline\n{load_error.output}")
    assert load_error.exit_code != breaking.exit_code


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="ir diff --format json reports has_breaking_changes false for a breaking field type change",
)
def test_ir_diff_summary_counts_a_breaking_field_type_change(tmp_path):
    """Protean finding (not yet filed upstream): the JSON summary misses a breaking change.

    Changing a projection field's type is listed under `compatibility.breaking_changes`
    and makes `ir diff` exit 1, but `summary.has_breaking_changes` stays false. A tool
    that reads the summary takes the change as safe. `scripts/ir-gate.sh` is not fooled,
    because it accepts a summary only on exit 2.
    """
    import json

    with open(REVIEWS_IR) as fh:
        ir = json.load(fh)
    if not ir["projections"]:
        pytest.fail("precondition: the reviews baseline has a projection")
    fields = ir["projections"][next(iter(ir["projections"]))]["projection"]["fields"]
    name, field = next((n, f) for n, f in fields.items() if f.get("type") == "Integer")
    field["type"] = "Float"
    changed = tmp_path / "reviews-ir.json"
    changed.write_text(json.dumps(ir))

    result = _ir_diff("--left", REVIEWS_IR, "--right", str(changed), "--dir", str(tmp_path), "--format", "json")

    report = json.loads(result.stdout)
    breaking = report["compatibility"]["breaking_changes"]
    if result.exit_code != 1 or [c["field_name"] for c in breaking] != [name]:
        pytest.fail(f"precondition: the type change is reported as breaking\n{result.output}")
    assert report["summary"]["has_breaking_changes"] is True


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


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="the outermost UnitOfWork rolls back a doomed transaction and returns without raising",
)
def test_outer_commit_of_a_doomed_transaction_raises():
    """Protean finding (proteanhq/protean#1631): a doomed transaction ends without an error.

    A nested UnitOfWork joins the outermost one, so a nested rollback marks the
    whole transaction rollback-only. When the outermost UnitOfWork then commits,
    `UnitOfWork.commit` sees `_rollback_only`, logs a warning, rolls back and
    returns. Nothing tells the caller the work was lost. A command handler that
    catches the error from a nested `domain.process(...)` and carries on returns
    as if it succeeded, and none of its writes persist. ShopStream's batch
    handlers `ExpireStaleReservations` and `DetectAbandonedCarts` do exactly this.
    """
    from protean import Domain
    from protean.core.unit_of_work import UnitOfWork
    from protean.fields import String

    domain = Domain(name="DoomedTransactionProbe")

    @domain.aggregate
    class Probe:
        name = String()

    domain.init(traverse=False)

    with domain.domain_context():
        outer_error = None
        try:
            with UnitOfWork():
                domain.repository_for(Probe).add(Probe(name="lost"))
                try:
                    with UnitOfWork():
                        raise RuntimeError("inner failure")
                except RuntimeError:
                    pass
        except Exception as exc:  # noqa: BLE001
            outer_error = exc

        if domain.repository_for(Probe).query.all().total != 0:
            pytest.fail("precondition: the nested rollback discarded the outer write")
        assert outer_error is not None, "the outer UnitOfWork returned normally"


@pytest.mark.usefixtures("inventory_ctx")
def test_event_sourced_repository_get_or_none_returns_none_on_a_miss():
    """proteanhq/protean#1659 (guard): the event-sourced repository has `get_or_none`.

    proteanhq/protean#1279 added `get_or_none` to `BaseRepository`, so CQRS aggregates
    and projections can look up a row that may not exist without catching
    `ObjectNotFoundError`. `BaseEventSourcedRepository` had only `add` and `get`.
    Fixed in proteanhq/protean#1824 (`9f20ad1`). `src/inventory/stock/expiry.py`
    uses it.
    """
    from protean import current_domain
    from protean.core.event_sourced_repository import BaseEventSourcedRepository
    from protean.core.repository import BaseRepository

    from inventory.stock.stock import InventoryItem

    repo = current_domain.repository_for(InventoryItem)
    if not isinstance(repo, BaseEventSourcedRepository) or not hasattr(BaseRepository, "get_or_none"):
        pytest.fail("precondition: InventoryItem uses the event-sourced repository and BaseRepository has get_or_none")

    assert repo.get_or_none("inventory-item-that-does-not-exist") is None


@pytest.mark.usefixtures("inventory_ctx")
def test_stale_event_sourced_write_raises_expected_version_error():
    """proteanhq/protean#1628 (guard): a stale event-sourced write raises `ExpectedVersionError`.

    For an event-sourced aggregate, the Message-DB append decides the version
    conflict. `UnitOfWork._do_commit` used to write the outbox rows before that
    append. A published event gets a second row for the external broker, and
    saving it ran `_validate_unique`, whose query autoflushed the first row. The
    outbox message id is `<stream>-<version>`, so the stale writer's row had the
    same `(message_id, target_broker)` as the winner's and the outbox's unique
    index rejected it. The caller got `sqlalchemy.exc.IntegrityError` on
    Postgres, or a `ValidationError` from the in-memory adapter, instead of
    `ExpectedVersionError`. So version retry never ran and a concurrent
    `ReserveStock` failed outright. The test runs on both. The fix (proteanhq/protean#1637) arrived with
    the pin bump to Protean main e79a817, so this is now a permanent guard.
    Guarded under real contention by `oracles/test_no_lost_updates.py`.
    """
    import uuid
    from datetime import UTC, timedelta

    from protean import current_domain
    from protean.core.unit_of_work import UnitOfWork
    from protean.exceptions import ExpectedVersionError

    from inventory.stock.events import StockReserved
    from inventory.stock.stock import InventoryItem

    # The bug needs a second outbox row for the same event, which only a
    # published event with an external broker produces.
    if not StockReserved.meta_.published:
        pytest.fail("precondition: StockReserved is a published event")
    if not current_domain.config["outbox"].get("external_brokers"):
        pytest.fail("precondition: the inventory outbox writes to an external broker")

    repo = current_domain.repository_for(InventoryItem)
    item = InventoryItem.create(
        product_id=str(uuid.uuid4()),
        variant_id=str(uuid.uuid4()),
        warehouse_id=str(uuid.uuid4()),
        sku=f"SKU-{uuid.uuid4().hex[:8]}",
        initial_quantity=5,
        reorder_point=-1,
    )
    repo.add(item)
    expires_at = datetime.now(UTC) + timedelta(minutes=15)

    stale = repo.get(item.id)
    with UnitOfWork():
        winner = repo.get(item.id)
        winner.reserve(order_id=str(uuid.uuid4()), quantity=1, expires_at=expires_at)
        repo.add(winner)

    outcome = None
    try:
        with UnitOfWork():
            stale.reserve(order_id=str(uuid.uuid4()), quantity=1, expires_at=expires_at)
            repo.add(stale)
    except Exception as exc:  # noqa: BLE001
        outcome = exc

    assert repo.get(item.id).levels.reserved == 1, "lost update: the stale write overwrote the winner's reservation"
    assert isinstance(outcome, ExpectedVersionError), repr(outcome)


@pytest.mark.usefixtures("loyalty_ctx")
def test_auto_now_stamp_does_not_run_pre_invariants():
    """proteanhq/protean#1663 (guard): saving a closed RewardAccount passes its own pre-invariant.

    `RewardAccount.closed_accounts_are_immutable` is an `@invariant.pre` that rejects
    any change to an account that is already Closed. `close()` itself passes, because
    the check runs before the status is assigned. On save, `BaseDAO._apply_pre_persist_hooks`
    stamps the `auto_now` field `updated_at` through `setattr`
    (`_stamp_lifecycle_timestamps` in `protean/port/dao.py`). That assignment used to
    run the pre-invariants again, now against the Closed status, so the save raised
    `ValidationError`. Aggregate enrichers run in the same hook and also assign
    through `setattr`, so loyalty's `stamp_actor` enricher hit the same check. Fixed
    for the whole pre-persist hook in proteanhq/protean#1811 (`3a546f3`).
    """
    from protean import current_domain
    from protean.exceptions import ValidationError

    from loyalty.reward.reward_account import AccountStatus, RewardAccount

    repo = current_domain.repository_for(RewardAccount)
    account = RewardAccount.enroll(customer_id="cust-close-save")
    repo.add(account)
    account = repo.get(account.id)
    account.close()

    try:
        repo.add(account)
    except ValidationError as exc:
        raise AssertionError(f"saving a just-closed account failed: {exc.messages}") from exc

    assert repo.get(account.id).status == AccountStatus.CLOSED.value


def _sync_dispatch_probe(projector_failure: Exception):
    """Build a sync-dispatch domain whose one event handler always raises ``projector_failure``.

    Returns the domain, its ``LabelParcel`` command class, and a list that gets one
    entry each time the command handler body runs.
    """
    from protean import Domain, current_domain, handle
    from protean.fields import Identifier, String

    domain = Domain(
        name="SyncDispatchRetryProbe",
        config={
            "databases": {"default": {"provider": "memory"}},
            "event_store": {"provider": "memory"},
            "brokers": {"default": {"provider": "inline"}},
            "command_processing": "sync",
            "event_processing": "sync",
        },
    )
    domain.config["server"]["version_retry"]["base_delay_seconds"] = 0.001
    handled: list[str] = []

    @domain.aggregate
    class Parcel:
        label = String(required=True)

    @domain.event(part_of=Parcel)
    class ParcelLabelled:
        parcel_id = Identifier(required=True)

    @domain.command(part_of=Parcel)
    class LabelParcel:
        label = String(required=True)

    @domain.command_handler(part_of=Parcel)
    class ParcelCommandHandler:
        @handle(LabelParcel)
        def label_parcel(self, command):
            handled.append(command.label)
            parcel = Parcel(label=command.label)
            parcel.raise_(ParcelLabelled(parcel_id=parcel.id))
            current_domain.repository_for(Parcel).add(parcel)

    @domain.event_handler(part_of=Parcel)
    class ParcelLabelledHandler:
        @handle(ParcelLabelled)
        def react(self, event):  # noqa: ARG002
            raise projector_failure

    domain.init(traverse=False)
    return domain, Parcel, LabelParcel, handled


def test_1883_committed_command_is_not_rerun_when_a_sync_handler_raises_expected_version_error():
    """proteanhq/protean#1883 (guard): a committed command does not run again.

    Under ``event_processing = "sync"``, `UnitOfWork.commit` dispatches events
    after the relational commit, inside the same `try`. A handler that raised
    `ExpectedVersionError` ended the drain, and the commit re-raised it as itself.
    The command handler's version retry then ran the whole command again, though
    its first attempt was already saved: 4 runs and 4 saved aggregates with the
    default ``max_retries = 3``. Fixed in proteanhq/protean#1888 (`6aad05f`): the
    commit now wraps a sync handler's failure in `TransactionError`.
    `tests/inventory/application/test_handler_failure_isolation.py` checks the
    same on `ReceiveStock`.
    """
    from protean.exceptions import ExpectedVersionError, TransactionError

    failure = ExpectedVersionError("simulated conflict")
    domain, parcel_cls, label_parcel, handled = _sync_dispatch_probe(failure)

    with domain.domain_context():
        with pytest.raises(TransactionError) as excinfo:
            domain.process(label_parcel(label="fragile"), asynchronous=False)
        saved = domain.repository_for(parcel_cls).query.all().total

    if not handled:
        pytest.fail("precondition: the command handler ran")
    assert excinfo.value.__cause__ is failure
    assert handled == ["fragile"], f"the command body ran {len(handled)} times"
    assert saved == 1


def test_1682_value_error_from_a_sync_handler_is_not_a_version_conflict():
    """proteanhq/protean#1682 (guard): a handler's `ValueError` is not reported as a version conflict.

    `UnitOfWork.commit` used to turn any `ValueError` into `ExpectedVersionError`,
    unless it was raised while the outbox rows were being saved. Sync dispatch runs
    later in the same `try`, so a `ValueError` from an event handler took that
    branch, whatever the outbox setting. The caller got `ExpectedVersionError`, and
    version retry ran the already committed command again, 4 times in all. Fixed in
    proteanhq/protean#1760 (`64c023d`).
    """
    from protean.exceptions import TransactionError

    failure = ValueError("handler bug, not a version conflict")
    domain, parcel_cls, label_parcel, handled = _sync_dispatch_probe(failure)

    outcome = None
    with domain.domain_context():
        try:
            domain.process(label_parcel(label="fragile"), asynchronous=False)
        except Exception as exc:  # noqa: BLE001
            outcome = exc
        saved = domain.repository_for(parcel_cls).query.all().total

    if not handled:
        pytest.fail("precondition: the command handler ran")
    assert isinstance(outcome, TransactionError), repr(outcome)
    assert outcome.__cause__ is failure
    assert handled == ["fragile"], f"the command body ran {len(handled)} times"
    assert saved == 1


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="projection rebuild keeps the processed-message markers, so an idempotent projector skips every replayed event",
)
@pytest.mark.usefixtures("payments_ctx")
def test_rebuild_restores_a_projection_whose_projector_is_idempotent():
    """proteanhq/protean#1913: a rebuild empties an idempotent projector's read model.

    `rebuild_projection` (`protean/utils/projection_rebuilder.py`) deletes the
    projection's rows, then replays every stored event through `projector._handle`.
    It leaves the `processed_message` table alone. For a projector declared with
    `idempotent=True`, the `@on` wrapper finds the marker the live delivery wrote,
    and skips the handler. So the rebuilt read model stays empty, and the result
    still counts each skipped event as dispatched. `DailyRevenueProjector` is one
    of the projectors this affects.
    """
    from protean import current_domain
    from protean.utils.projection_rebuilder import rebuild_projection

    from payments.payment.initiation import InitiatePayment
    from payments.payment.webhook import ProcessPaymentWebhook
    from payments.projections.daily_revenue import DailyRevenue, DailyRevenueProjector

    payment_id = current_domain.process(
        InitiatePayment(
            order_id="ord-rebuild",
            customer_id="cust-rebuild",
            amount=40.0,
            currency="USD",
            payment_method_type="credit_card",
            last4="4242",
            idempotency_key="rebuild-1",
        ),
        asynchronous=False,
    )
    current_domain.process(
        ProcessPaymentWebhook(payment_id=payment_id, gateway_transaction_id="txn-rebuild", gateway_status="succeeded"),
        asynchronous=False,
    )
    repo = current_domain.repository_for(DailyRevenue)
    if not DailyRevenueProjector.meta_.idempotent or [r.transaction_count for r in repo.query.all().items] != [1]:
        pytest.fail("precondition: the idempotent projector counted the payment once")

    result = rebuild_projection(current_domain, DailyRevenue)

    if result.errors:
        pytest.fail(f"precondition: the rebuild ran without errors: {result.errors}")
    assert [r.transaction_count for r in repo.query.all().items] == [1]


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="the memory provider compares datetimes as strings in lt/lte/gt/gte lookups",
)
def test_1900_memory_datetime_lookup_compares_instants():
    """proteanhq/protean#1900: memory lookups compare datetimes by wall-clock text.

    `MemoryLookup._coerce()` turns a `datetime` into `str(value)` before comparing,
    so two values with different UTC offsets compare by their wall-clock digits.
    12:00 UTC is after 13:00+02:00 (11:00 UTC), yet `lte` returns the row.
    Postgres compares instants. The notification scheduler converts its cutoff
    to UTC to stay correct on memory.
    """
    from datetime import UTC, timedelta, timezone

    from protean import Domain
    from protean.fields import DateTime

    domain = Domain(name="DatetimeLookupProbe")

    @domain.aggregate
    class Slot:
        at = DateTime()

    domain.init(traverse=False)

    with domain.domain_context():
        repo = domain.repository_for(Slot)
        repo.add(Slot(at=datetime(2026, 10, 20, 12, 0, tzinfo=UTC)))
        eleven_utc = datetime(2026, 10, 20, 13, 0, tzinfo=timezone(timedelta(hours=2)))
        thirteen_utc = datetime(2026, 10, 20, 11, 0, tzinfo=timezone(timedelta(hours=-2)))

        assert repo.query.filter(at__lte=eleven_utc).all().items == []
        assert len(repo.query.filter(at__lte=thirteen_utc).all().items) == 1


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="the multi-group stream trim deletes entries still pending in a consumer group",
)
@pytest.mark.usefixtures("loyalty_ctx")
def test_stream_trim_keeps_entries_a_consumer_group_has_not_acknowledged():
    """Protean finding (not filed yet): retention trims messages a group still has to retry.

    With two or more consumer groups on a stream, `RedisBroker.trim` runs
    `XTRIM MINID` at the smallest `last-delivered-id`. That id only says which
    entries a group was handed. A handler that failed leaves its entries in the
    group's pending list below that id, and the trim deletes them. Redelivery then
    returns those ids with no fields, `_read_blocking` skips them, and the message
    is never retried or dead-lettered. ShopStream turns retention on for every
    subscription through the `shopstream` profile, so a dispatcher that fails
    during a channel outage can lose its pending sends this way.
    """
    import uuid

    import redis
    from protean import current_domain

    broker = current_domain.brokers["default"]
    client = getattr(broker, "redis_instance", None)
    if client is None:
        pytest.skip("needs the Redis streams broker (run with --protean-env test)")
    # A local test-env run may have no Redis at the broker's URL.
    try:
        client.ping()
    except redis.exceptions.ConnectionError:
        pytest.skip("the default broker's Redis is not reachable")

    stream = f"regression::trim-{uuid.uuid4().hex[:8]}"
    try:
        # Enough entries for an approximate trim to drop whole macro-nodes.
        ids = [client.xadd(stream, {"n": str(i)}) for i in range(300)]
        client.xgroup_create(stream, "failing", id="0")
        client.xgroup_create(stream, "healthy", id="0")
        # Both groups read everything. Only the healthy group acknowledges.
        client.xreadgroup("failing", "c1", {stream: ">"}, count=1000)
        client.xreadgroup("healthy", "c1", {stream: ">"}, count=1000)
        client.xack(stream, "healthy", *ids)
        if client.xpending(stream, "failing")["pending"] != len(ids):
            pytest.fail("precondition: the failing group holds every entry as pending")

        broker.trim(stream, 50000)

        redelivered = client.xreadgroup("failing", "c1", {stream: "0"}, count=1000)
        entries = redelivered[0][1] if redelivered else []
        assert len(entries) == len(ids)
        assert all(fields for _, fields in entries), "pending entries came back without their data"
    finally:
        client.delete(stream)


@pytest.mark.xfail(
    strict=True,
    raises=TypeError,
    reason="a process manager with a Decimal field fails to persist its transition: the state is not JSON-encoded",
)
def test_process_manager_with_a_decimal_field_persists_its_transition():
    """proteanhq/protean#1892 (open): a ``Decimal`` field on a process manager breaks its commit.

    `BaseProcessManager._persist_transition` turns only `datetime` and `date`
    values in the state into strings. `MessageEnvelope.compute_checksum` then
    calls `json.dumps` on the transition, which raises `TypeError` for a
    `Decimal`, so the UnitOfWork that runs the handler fails. Under
    ``event_processing = "sync"`` the command that raised the event fails with
    it. ShopStream's `OrderCheckoutSaga.amount` stays a `Float` for this reason.
    """
    from decimal import Decimal as D

    from protean import Domain, handle
    from protean.exceptions import TransactionError
    from protean.fields import Decimal, Identifier, String

    domain = Domain(name="ProcessManagerDecimalProbe")
    domain.config["event_processing"] = "sync"

    @domain.aggregate
    class Till:
        name = String()

    @domain.event(part_of=Till)
    class TillCharged:
        till_id = Identifier(required=True)
        amount = Decimal(precision=19, scale=4, required=True)

    @domain.process_manager(stream_categories=["processmanagerdecimalprobe::till"])
    class ChargeTracker:
        till_id = Identifier()
        amount = Decimal(precision=19, scale=4)

        @handle(TillCharged, start=True, correlate="till_id")
        def on_charged(self, event):
            self.till_id = event.till_id
            self.amount = event.amount

    domain.init(traverse=False)

    with domain.domain_context():
        till = Till(name="front")
        till.raise_(TillCharged(till_id=till.id, amount=D("49.99")))
        try:
            domain.repository_for(Till).add(till)
        except TransactionError as exc:
            raise exc.__cause__ or exc from None

        transitions = [
            message
            for message in domain.event_store.store.read("$all")
            if "charge_tracker" in message.metadata.headers.stream
        ]
        assert len(transitions) == 1
        assert str(transitions[0].data["state"]["amount"]) in ("49.99", "49.9900")


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="a snapshot that still builds is used as it is, even when it disagrees with replay",
)
@pytest.mark.usefixtures("loyalty_ctx")
def test_snapshot_that_builds_but_disagrees_with_replay_is_not_used():
    """Protean finding (not filed yet): a stale snapshot that still builds loads its defaults.

    The event store discards a snapshot only when `part_of(**data)` raises
    `ValidationError`. A snapshot written before a field with a default was
    added still builds, so the field loads its default. When an `@apply`
    handler sets that field, replay gives a different value. PromoCampaign's
    `status` defaults to "draft" and is set by its handlers: a snapshot without
    `status` loads "draft" where replay gives "active".
    """
    from protean import current_domain

    from loyalty.campaign.campaign import PromoCampaign

    campaign = PromoCampaign.launch(
        campaign_code="DEFAULTED",
        name="Defaulted Days",
        discount_type="points_multiplier",
        discount_value=2,
    )
    campaign.activate()
    repo = current_domain.repository_for(PromoCampaign)
    repo.add(campaign)
    full_replay = repo.get(campaign.id)
    if full_replay.status != "active":
        pytest.fail("precondition: replay gives an active campaign")

    stale = {k: v for k, v in full_replay.to_dict().items() if k != "status"}
    current_domain.event_store.store._write(
        f"{PromoCampaign.meta_.stream_category}:snapshot-{campaign.id}", "SNAPSHOT", stale
    )

    assert repo.get(campaign.id).to_dict() == full_replay.to_dict()


async def _deliver(subscription, cycles: int) -> int:
    """Run read-then-process cycles of a subscription; return how many messages were delivered."""
    delivered = 0
    for _ in range(cycles):
        batch = await subscription.get_next_batch_of_messages()
        delivered += len(batch)
        if batch:
            await subscription.process_batch(batch)
    return delivered


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="the InlineBroker's DLQ API reads only its native DLQ, not the {stream}:dlq stream subscriptions write",
)
@pytest.mark.usefixtures("loyalty_ctx")
# One case per call, so a Protean fix to one of them alone shows as an XPASS.
@pytest.mark.parametrize("read", ["dlq_list", "dlq_depth"])
def test_inline_broker_dlq_api_reads_the_subscription_dlq_stream(monkeypatch, read):
    """Protean finding (not filed yet): the InlineBroker's DLQ API misses what subscriptions dead-letter.

    Since ADR-0042 a subscription owns dead-lettering: it publishes an exhausted
    message to `{stream}:dlq`, and the InlineBroker never moves an owned group's
    message to its own `_dead_letter_queue`. But `dlq_list` on the InlineBroker
    reads only `_dead_letter_queue`, and it has no `dlq_depth`, so the base
    class returns 0. `dlq_inspect`, `dlq_replay` and `dlq_purge` read the same
    `_dead_letter_queue` (read in the code; this pin runs only the first two).
    Under the memory env the DLQ API reports an empty DLQ while
    `loyalty::poison_pill:dlq` holds the message. The Redis broker reads the
    `{stream}:dlq` stream and reports it.
    """
    import asyncio

    from protean import current_domain
    from protean.adapters.broker.inline import InlineBroker
    from protean.server.engine import Engine
    from protean.server.subscription.stream_subscription import StreamSubscription
    from protean.utils.eventing import Message

    from loyalty.dlq.poison import PoisonEventHandler, PoisonPill

    broker = current_domain.brokers["default"]
    if not isinstance(broker, InlineBroker):
        pytest.skip("needs the InlineBroker (run with --protean-env memory)")
    broker._data_reset()
    monkeypatch.setattr(broker, "_retry_delay", 0)

    stream = "loyalty::poison_pill"
    dlq_stream = f"{stream}:dlq"
    subscription = StreamSubscription(
        Engine(current_domain, test_mode=True),
        stream,
        PoisonEventHandler,
        blocking_timeout_ms=50,
        max_retries=1,
        retry_delay_seconds=0,
        enable_dlq=True,
    )
    asyncio.run(subscription.initialize())
    pill = PoisonPill.detonate("dlq api probe")
    broker.publish(stream, Message.from_domain_object(pill._events[0]).to_dict())
    if asyncio.run(_deliver(subscription, 1)) != 1:
        pytest.fail("precondition: the subscription received the message")
    if len(broker._messages.get(dlq_stream, [])) != 1:
        pytest.fail("precondition: the subscription published the message to the DLQ stream")

    if read == "dlq_list":
        assert len(broker.dlq_list([dlq_stream])) == 1
    else:
        assert broker.dlq_depth(dlq_stream) == 1


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="dlq_replay appends the message to the source stream, so every consumer group reads it again",
)
@pytest.mark.usefixtures("payments_ctx")
def test_dlq_replay_reaches_only_the_failing_consumer_group():
    """Protean finding (not filed yet): replaying a dead letter redelivers it to every consumer group.

    A `BrokerSubscription` dead-letters to `{stream}:dlq` and records its own
    group in `_dlq_metadata.consumer_group`. `RedisBroker.dlq_replay` strips
    that metadata and appends the message to the source stream again, so every
    group on the stream reads it as a new message, including groups that
    already handled it. On the shared bus, replaying a payments failure on
    `ordering::order` would deliver the order event again to every other
    context subscribed to it: fulfillment, inventory, loyalty, notifications
    and reviews.
    """
    import asyncio

    import redis
    from protean import current_domain
    from protean.server.engine import Engine
    from protean.server.subscription.broker_subscription import BrokerSubscription

    from payments.payment.ordering_subscriber import OrderReturnedSubscriber

    broker = current_domain.brokers["global"]
    client = getattr(broker, "redis_instance", None)
    if client is None:
        pytest.skip("needs the Redis streams broker (run with --protean-env test)")
    try:
        client.ping()
    except redis.exceptions.ConnectionError:
        pytest.skip("the global broker's Redis is not reachable")
    broker._data_reset()

    stream = "ordering::order"
    dlq_stream = f"{stream}:dlq"
    other_group = "fulfillment.order_subscriber"
    subscription = BrokerSubscription(
        Engine(current_domain, test_mode=True),
        broker,
        stream,
        OrderReturnedSubscriber,
        max_retries=1,
        retry_delay_seconds=0,
        enable_dlq=True,
    )
    payload = {
        "data": {"reason": "damaged"},
        "metadata": {"headers": {"id": "replay-probe-1", "type": "Ordering.OrderReturned.v1"}},
    }
    # `_publish` stores the message without calling the subscribers inline, like the outbox processor.
    original_id = broker._publish(stream, payload)
    client.xgroup_create(stream, other_group, id="0")
    client.xreadgroup(other_group, "c1", {stream: ">"}, count=10)
    client.xack(stream, other_group, original_id)

    if asyncio.run(_deliver(subscription, 1)) != 1:
        pytest.fail("precondition: the subscription received the message")
    dead = broker.dlq_list([dlq_stream])
    if len(dead) != 1:
        pytest.fail("precondition: the subscription dead-lettered the message")

    if not broker.dlq_replay(dlq_stream, dead[0].dlq_id, target_stream=stream):
        pytest.fail("precondition: dlq_replay reported success")
    # A replay that reached no stream would leave the other group nothing to read and XPASS.
    if client.xlen(stream) != 2:
        pytest.fail("precondition: the replay appended the message to the source stream")

    replayed_to_other = client.xreadgroup(other_group, "c1", {stream: ">"}, count=10)
    assert replayed_to_other == [], "a group that already handled the message received the replay"
