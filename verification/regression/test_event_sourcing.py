"""Regressions in event sourcing and sync dispatch: event-sourced repositories, version conflicts and snapshots."""

from __future__ import annotations

from datetime import datetime

import pytest


@pytest.mark.protean_bug(
    issue=1659,
    state="guard",
    bug=(
        "`BaseEventSourcedRepository` had no `get_or_none`. [#1279](https://github.com/proteanhq/protean/issues/1279) "
        "added it to `BaseRepository` only, so a lookup on an event-sourced aggregate that may miss had to catch "
        "`ObjectNotFoundError`. Fixed in proteanhq/protean#1824 (`9f20ad1`); `src/inventory/stock/expiry.py` now uses "
        "it."
    ),
)
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


@pytest.mark.protean_bug(
    issue=1628,
    state="guard",
    bug=(
        "A stale write on an event-sourced aggregate that raises a published event failed with an outbox "
        "`IntegrityError` instead of `ExpectedVersionError`: the UnitOfWork wrote outbox rows before the Message-DB "
        "append, and the external-broker row's unique check autoflushed the internal row, whose `<stream>-<version>` "
        "key clashed with the winner's. Version retry never ran. The in-memory outbox had the same clash. Fixed in "
        "proteanhq/protean#1637 (`68ed330`)."
    ),
)
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


@pytest.mark.protean_bug(
    issue=1883,
    state="guard",
    bug=(
        "Under sync dispatch, an event handler that raised `ExpectedVersionError` made the command handler's version "
        "retry run the command again, though its commit had already succeeded. With `max_retries = 3` the command ran "
        "4 times: in inventory, `ReceiveStock` ran 4 times and `StockReceived` was dispatched 4 times. Fixed in "
        "proteanhq/protean#1888 (`6aad05f`): the commit wraps the handler's failure in `TransactionError`."
    ),
)
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


@pytest.mark.protean_bug(
    issue=1682,
    state="guard",
    bug=(
        "`UnitOfWork.commit` turned a `ValueError` into `ExpectedVersionError` unless it was raised while saving "
        "outbox rows. Sync dispatch runs later in the same `try`, so a `ValueError` from an event handler was reported"
        " as a version conflict, whatever the outbox setting, and version retry ran the committed command 4 times. "
        "Fixed in proteanhq/protean#1760 (`64c023d`)."
    ),
)
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


@pytest.mark.protean_bug(
    issue=None,
    state="open",
    bug=(
        "The event store discards a snapshot only when it fails to build (`part_of(**data)` raises `ValidationError`)."
        " A snapshot that still builds is used as it is. So a field added with a default, whose value an `@apply` "
        'handler sets, loads its default from an older snapshot: PromoCampaign\'s `status` loads `"draft"` where replay'
        ' gives `"active"`. `src/loyalty/CLAUDE.md` says to rebuild snapshots after such a change.'
    ),
)
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
