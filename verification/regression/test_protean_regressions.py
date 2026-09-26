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
    """Protean finding (not filed, feature request): `current_domain` has no warning-free probe.

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


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Config2 keeps only keys from _default_config(), so a top-level [lint] table in domain.toml is dropped",
)
def test_lint_table_in_domain_toml_is_loaded(tmp_path, monkeypatch):
    """Protean finding (not filed): a top-level `[lint]` table in `domain.toml` is dropped.

    Protean's configuration docs describe a `[lint]` table (`level`, `suppressions`,
    and more) that `protean check` and `protean verify` read through
    `domain.config.get("lint", {})`. `Config2._normalize_config` keeps only the
    top-level keys that `_default_config()` defines, and `lint` is not one of
    them, so a top-level `[lint]` is discarded. An environment overlay such as
    `[test.lint]` is deep-merged without that key filter, so it does load. The
    bug is that the filter is applied to one and not the other.

    On this pin any warning makes `protean check` exit 1. Because the `[lint]`
    table is dropped, ShopStream cannot set `level = "error"` to keep
    `make domain-check` failing on errors only.
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


def _pytest_project(tmp_path, test_source: str, ini: str = "") -> str:
    """A small pytest project in `tmp_path`, cut off from ShopStream's pytest config."""
    (tmp_path / "pytest.ini").write_text(f"[pytest]\n{ini}")
    (tmp_path / "test_probe.py").write_text(test_source)
    return str(tmp_path)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="protean verify's tests stage removes PROTEAN_ENV from the pytest subprocess",
)
def test_verify_tests_stage_keeps_protean_env(tmp_path, monkeypatch):
    """Protean finding (not filed): `protean verify` drops `PROTEAN_ENV` before its tests stage.

    `_run_tests` in `protean/cli/verify.py` pops `PROTEAN_ENV` (and `PROTEAN_DEBUG`,
    `VIRTUAL_ENV`) from the environment it hands to `python -m pytest`. The init and
    check stages run in the verify process and do see `PROTEAN_ENV`. So
    `PROTEAN_ENV=memory protean verify` inits and checks under `memory` and then
    tests under Protean's pytest plugin default, `test`, which points at Postgres.
    `scripts/verify-domains.sh` works around it with `--protean-env memory` in
    `PYTEST_ADDOPTS`.
    """
    from protean.cli.verify import _run_tests

    project = _pytest_project(
        tmp_path,
        "import os\n\ndef test_env():\n    assert os.environ.get('PROTEAN_ENV') == 'memory'\n",
    )
    monkeypatch.delenv("PYTEST_ADDOPTS", raising=False)
    monkeypatch.setenv("PROTEAN_ENV", "memory")

    stage, output = _run_tests(project)

    if stage["passed"] + stage["failed"] != 1:
        pytest.fail(f"precondition: the probe test ran once\n{output}")
    assert stage["status"] == "pass", output


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="protean verify counts failed tests from the first 'N failed' anywhere in the pytest output",
)
def test_verify_tests_stage_counts_failures_from_the_summary(tmp_path, monkeypatch):
    """Protean finding (not filed): `protean verify` can report a port number as the failure count.

    `_run_tests` reads the counts with `re.search(r"(\\d+) failed", output)`, which
    matches the first hit anywhere in pytest's output, not the summary line. A
    failure message that contains "<number> failed" wins. Seen in ShopStream: with
    the tests stage under the `test` env and no Postgres running, `verify -d
    identity.domain` reported `"failed": 15432`, taken from psycopg2's
    "connection to server at "localhost", port 15432 failed". The status comes
    from the return code, so only the count is wrong.
    """
    from protean.cli.verify import _run_tests

    project = _pytest_project(
        tmp_path,
        "def test_db():\n    raise AssertionError('connection to server on port 15432 failed')\n",
    )
    monkeypatch.delenv("PYTEST_ADDOPTS", raising=False)

    stage, output = _run_tests(project)

    if stage["status"] != "fail" or "1 failed" not in output:
        pytest.fail(f"precondition: the probe test ran and failed\n{output}")
    assert stage["failed"] == 1


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="protean verify counts passed tests from the first 'N passed' anywhere in the pytest output",
)
def test_verify_tests_stage_counts_passes_from_the_summary(tmp_path, monkeypatch):
    """Protean finding (not filed): `protean verify` can read the passed count from a skip reason.

    `_run_tests` reads the passed count with `re.search(r"(\\d+) passed", output)`, the
    same first-match read as the failed count. With `-ra` in a project's addopts (ShopStream
    has it), pytest prints skip reasons before the summary line, so a reason such as
    "0 passed on this platform" is read as the passed count. `scripts/verify-domains.sh`
    fails a context whose tests stage passed zero tests, so this count feeds its gate.
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

    stage, output = _run_tests(project)

    if stage["status"] != "pass" or "1 passed, 1 skipped" not in output:
        pytest.fail(f"precondition: one test passed and one was skipped\n{output}")
    assert stage["passed"] == 1


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="the is_event_sourced deprecation warning is attributed to protean/domain/__init__.py, not the caller",
)
def test_is_event_sourced_warning_points_at_the_decorator():
    """Protean finding (not filed): the `is_event_sourced` warning names the wrong line.

    Registering an element with the deprecated `is_event_sourced=True` warns, but
    the warning's file and line are Protean's own `_domain_element.wrap` in
    `protean/domain/__init__.py`, not the `@domain.aggregate(...)` line that used
    the option. The `stacklevel` stops one frame short, so a user cannot see which
    of their elements to change.
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
    """Protean finding (not filed): a doomed transaction ends without an error.

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


@pytest.mark.skipif(
    ENV != "test",
    reason="needs the Postgres outbox and a Message-DB event store; the in-memory adapters do not autoflush",
)
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="a stale write on an event-sourced aggregate with a published event fails on the outbox unique index",
)
@pytest.mark.usefixtures("inventory_ctx")
def test_stale_event_sourced_write_raises_expected_version_error():
    """Protean finding (not filed): a stale write surfaces as an IntegrityError.

    For an event-sourced aggregate, the Message-DB append decides the version
    conflict. `UnitOfWork._do_commit` writes the outbox rows before that append.
    A published event gets a second row for the external broker, and saving it
    runs `_validate_unique`, whose query autoflushes the first row. The outbox
    message id is `<stream>-<version>`, so the stale writer's row has the same
    `(message_id, target_broker)` as the winner's and Postgres rejects it. The
    caller gets `sqlalchemy.exc.IntegrityError` instead of `ExpectedVersionError`,
    so version retry never runs and a concurrent `ReserveStock` fails outright.
    Guarded under real contention by `oracles/test_no_lost_updates.py`.
    """
    import uuid
    from datetime import UTC, timedelta

    from protean import current_domain
    from protean.core.unit_of_work import UnitOfWork
    from protean.exceptions import ExpectedVersionError

    from inventory.stock.stock import InventoryItem

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

    if repo.get(item.id).levels.reserved != 1:
        pytest.fail("precondition: only the winner's reservation persisted")
    assert isinstance(outcome, ExpectedVersionError), repr(outcome)
