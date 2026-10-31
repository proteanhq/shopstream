"""Regressions in persistence: repositories, adapters, value objects and the unit of work."""

from __future__ import annotations

import os
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


@pytest.mark.protean_bug(
    issue=1039,
    state="guard",
    bug="Datetime payloads serialized with `str()`, not ISO/UTC.",
)
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


@pytest.mark.protean_bug(
    issue=1071,
    state="guard",
    bug="In-memory adapter ignores `Index(unique=True)`.",
)
@pytest.mark.skipif(
    ENV == "test",
    reason="#1071 is about the in-memory adapter; the relational path is covered by test_outbox_exactly_once",
)
@pytest.mark.usefixtures("loyalty_ctx")
def test_1071_memory_adapter_enforces_unique_index():
    """proteanhq/protean#1071 (guard): the in-memory adapter enforces Index(unique=True)."""
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


@pytest.mark.protean_bug(
    issue=1078,
    state="guard",
    bug="All-default ValueObject round-trips to `None`.",
)
@pytest.mark.usefixtures("inventory_ctx")
def test_1078_all_default_value_object_round_trips():
    """proteanhq/protean#1078 (guard): an all-default ValueObject survives event replay.

    An event-sourced aggregate whose ValueObject had only falsy fields (every
    `StockLevels` count at 0) came back as `None` after a persist and reload. The
    fix touched both the attribute setter (`ValueObject.__set__`) and
    serialization (`to_dict`), so the test checks the reloaded attribute and its
    serialized form.
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


@pytest.mark.protean_bug(
    issue=1631,
    state="open",
    bug=(
        "The outermost UnitOfWork rolls back a transaction a nested UnitOfWork doomed, then returns without raising, "
        "so the caller sees success for writes that were lost."
    ),
)
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


@pytest.mark.protean_bug(
    issue=1663,
    state="guard",
    bug=(
        "Saving an aggregate ran its `@invariant.pre` checks again when `BaseDAO._apply_pre_persist_hooks` stamped "
        "`auto_now` fields and ran aggregate enrichers, because both assign through `setattr`. A pre-invariant that "
        "rejects changes in the new state (loyalty's `closed_accounts_are_immutable`) then blocked the save of the "
        "transition that reached it: `close()` worked, and saving the closed `RewardAccount` raised `ValidationError`."
        " Fixed in proteanhq/protean#1811 (`3a546f3`)."
    ),
)
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


@pytest.mark.protean_bug(
    issue=1900,
    state="open",
    bug=(
        "The memory provider turns a `datetime` into a string before an `lt`/`lte`/`gt`/`gte` comparison, so two "
        "values with different UTC offsets compare by wall-clock text. `src/notifications/notification/scheduler.py` "
        "converts its `as_of` cutoff to UTC to stay correct on memory."
    ),
)
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


@pytest.mark.protean_bug(
    issue=1892,
    state="open",
    bug=(
        "A process manager with a `Decimal` field cannot persist a transition. "
        "`BaseProcessManager._persist_transition` turns only `datetime` and `date` state values into strings, so "
        "`MessageEnvelope.compute_checksum` raises `TypeError` from `json.dumps` at UnitOfWork commit. Under "
        '`event_processing = "sync"` the command that raised the event fails. `OrderCheckoutSaga.amount` stays `Float`'
        " for this reason, though the event money it copies is `Decimal`."
    ),
)
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


@pytest.mark.protean_bug(
    issue=1928,
    state="open",
    bug=(
        "Value objects compare and hash by their `to_dict()`, which renders a `Decimal` as a string. Two value objects "
        "whose amounts are equal but carry different decimal places compare unequal: catalogue's "
        '`TierPrice(amount=Decimal("9.99"))` is not equal to `TierPrice(amount=Decimal("9.9900"))`. The `Decimal` field '
        "does not round a value to its scale, so both forms occur."
    ),
)
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="value objects compare by to_dict strings, so equal Decimals with different scales are unequal",
)
@pytest.mark.usefixtures("catalogue_ctx")
def test_1928_value_objects_with_equal_decimals_compare_equal():
    """proteanhq/protean#1928: equal Decimal amounts make equal value objects."""
    from decimal import Decimal

    from catalogue.product.product import TierPrice

    short, padded = TierPrice(amount=Decimal("9.99")), TierPrice(amount=Decimal("9.9900"))
    if short.amount != padded.amount:
        pytest.fail("precondition: the two amounts are equal Decimals")

    assert short == padded
    assert hash(short) == hash(padded)
