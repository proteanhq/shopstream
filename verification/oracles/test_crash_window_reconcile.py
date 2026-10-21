"""P21 - crash between event-store append and relational commit; recovery.

WHAT THIS CHECKS
    Protean commits in two stores, in this order (ADR-0015):

        1. append events to the event store (Message-DB) — the durable anchor
        2. commit the relational session (aggregate rows + OUTBOX rows)

    A crash in the window between (1) and (2) leaves the event durable but its
    outbox row uncommitted — so the event exists yet was never queued for
    publishing. ADR-0015 accepts that window and promises to close it with a
    startup reconciliation sweep (`reconcile_outbox`) that recreates the missing
    outbox rows from the event store.

    P21: after such a crash, a durable event must still end up published — i.e.
    reconciliation must restore its outbox row.

HOW THE CRASH IS SIMULATED (deterministically, in-process)
    Message-DB writes through its own psycopg2 pool; the relational store uses a
    SQLAlchemy session. Patching `Session.commit` to raise fails ONLY the
    relational commit (step 2) while the event-store append (step 1) has already
    landed — exactly the ADR-0015 window, with no real process kill needed.

STATUS
    Guards (the fix is in the pin):

    - `test_crash_leaves_event_durable_but_unpublished` characterizes the window
      (event durable, outbox row missing).
    - `test_reconcile_restores_...` asserts the recovery: `reconcile_outbox`
      restores the lost row. It was xfail while `reconcile_outbox` was a no-op
      against Message-DB (`read_last_message("$all")` returned None,
      proteanhq/protean#1073).
    - the engine's own startup sweep (`Engine._reconcile_outbox_on_startup`)
      restores the row. It is called directly on an engine that is never run,
      so the check needs no live engine. The method is private; the startup
      sweep has no public entry point.
    - a lost `published=True` event gets back both its internal row and its
      `global` row, under the same message id. The sweep used to rebuild only
      the internal row (proteanhq/protean#1653, fixed in proteanhq/protean#1718).
    - another context's event, or a command, at the tail of the store shared by
      nine contexts gets no row, and the lost inventory event behind it still
      gets its row. The sweep used to give a row to every message at the tail
      that had none here (proteanhq/protean#1648, fixed in
      proteanhq/protean#1655).

    Open Protean findings (xfail(strict=True) here):

    - reconcile repairs only when the newest event this context owns is missing
      its row. If another writer in the same context commits after the crash,
      the lost event is never repaired (proteanhq/protean#1907).
    - reconcile run while a command sits between its event-store append and its
      relational commit sees no row, inserts one, and commits first. The live
      commit then fails on the `(message_id, target_broker)` unique index, so
      its caller gets `TransactionError` for an event that will be published.
      So `make outbox-reconcile` must run with the API and engines stopped
      (proteanhq/protean#1906).
    - for a state-based (CQRS) aggregate, the crash rolls back the aggregate
      row too, and reconcile still publishes its event. Here a
      `CustomerRegistered` goes out for a customer that was never saved
      (proteanhq/protean#1908).

WHY POSTGRES + MESSAGE-DB ONLY
    The two-store split and the SQLAlchemy-commit seam only exist with the real
    adapters. Skipped under `--protean-env memory`.

RUN:
    make docker-up && make setup-db && make setup-test-event-store      # once
    .venv/bin/python -m pytest \
        verification/oracles/test_crash_window_reconcile.py --protean-env test -q
"""

from __future__ import annotations

import os
import threading
import uuid

import pytest
from protean.exceptions import TransactionError

ENV = os.environ.get("PROTEAN_ENV")
pytestmark = pytest.mark.skipif(
    ENV != "test",
    reason="crash-window oracle needs the real two-store split (Postgres + Message-DB); run with --protean-env test",
)

RECEIVED = "Inventory.StockReceived.v1"
RESERVED = "Inventory.StockReserved.v1"
REGISTERED = "Identity.CustomerRegistered.v1"


class _SimulatedCrash(RuntimeError):
    """Stands in for a process kill during the relational commit."""


def _reset_stores(domain):
    """Clean event store + relational stores so the check starts from empty."""
    domain.event_store.store._data_reset()
    for _, provider in domain.providers.items():
        provider._data_reset()


def _seed_item(domain, on_hand):
    from inventory.stock.stock import InventoryItem

    item = InventoryItem.create(
        product_id=f"p-{uuid.uuid4().hex[:8]}",
        variant_id=f"v-{uuid.uuid4().hex[:8]}",
        warehouse_id=f"w-{uuid.uuid4().hex[:8]}",
        sku=f"SKU-{uuid.uuid4().hex[:8]}",
        initial_quantity=on_hand,
    )
    domain.repository_for(InventoryItem).add(item)
    return str(item.id)


def _process_crashing_on_commit(domain, command):
    """Process *command* but fail the relational commit AFTER the append."""
    from sqlalchemy.orm import Session

    real_commit = Session.commit

    def crashing_commit(*_args, **_kwargs):
        raise _SimulatedCrash("crash between event-store append and relational commit")

    Session.commit = crashing_commit
    try:
        with pytest.raises(TransactionError):
            domain.process(command, asynchronous=False)
    finally:
        Session.commit = real_commit  # reconcile below must use the real commit


def _receive_stock_crashing_on_commit(domain, item_id, quantity):
    from inventory.stock.receiving import ReceiveStock

    _process_crashing_on_commit(domain, ReceiveStock(inventory_item_id=item_id, quantity=quantity))


def _stream_event_types(domain, item_id):
    msgs = domain.event_store.store.read(f"inventory::inventory_item-{item_id}")
    return [m.metadata.headers.type for m in msgs]


def _internal_received_rows(domain, item_id):
    """Pending internal-broker outbox rows for THIS item's StockReceived event."""
    stream = f"inventory::inventory_item-{item_id}"
    rows = domain._get_outbox_repo("default").find_unprocessed()
    return [r for r in rows if r.type == RECEIVED and r.target_broker == "default" and r.stream_name == stream]


@pytest.mark.protean_bug(
    issue=1040,
    state="guard",
    bug="Event-store append happened *after* the DB commit (crash window).",
)
@pytest.mark.usefixtures("inventory_ctx")
def test_crash_leaves_event_durable_but_unpublished():
    """Characterize the ADR-0015 window: event is durable, its outbox row is not."""
    from protean import current_domain

    _reset_stores(current_domain)
    item_id = _seed_item(current_domain, on_hand=0)

    _receive_stock_crashing_on_commit(current_domain, item_id, 10)

    # The append landed: StockReceived is durable in the event store...
    assert RECEIVED in _stream_event_types(current_domain, item_id)
    # ...but the relational commit rolled back, so there is no row to publish it.
    assert _internal_received_rows(current_domain, item_id) == []


@pytest.mark.protean_bug(
    issue=1073,
    state="guard",
    bug=('`reconcile_outbox` no-op on Message-DB (`read_last_message("$all")` is None).'),
)
@pytest.mark.usefixtures("inventory_ctx")
def test_reconcile_restores_the_lost_outbox_row():
    """P21 (guard): reconciliation recreates the outbox row so the event still publishes.

    Was xfail while reconcile_outbox no-op'd against Message-DB (proteanhq/protean#1073,
    read_last_message("$all") returned None); the pin bump to Protean main landed the
    fix, so this is now a permanent guard.
    """
    from protean import current_domain
    from protean.utils.outbox import reconcile_outbox

    _reset_stores(current_domain)
    item_id = _seed_item(current_domain, on_hand=0)

    _receive_stock_crashing_on_commit(current_domain, item_id, 10)
    assert _internal_received_rows(current_domain, item_id) == []  # precondition: row lost

    reconcile_outbox(current_domain)

    # Desired: the durable event's outbox row is restored, so it will be published.
    assert len(_internal_received_rows(current_domain, item_id)) == 1


def _rows_for(domain, message_id):
    """Every outbox row of one message, for any broker and status."""
    return domain._get_outbox_repo("default").find_all_by_message_id(message_id)


def _total_rows(domain):
    return sum(domain._get_outbox_repo("default").count_by_status().values())


def _newest(domain):
    return domain.event_store.store.read_last_message("$all")


def _stored(domain, stream, message_type):
    return [m for m in domain.event_store.store.read(stream) if m.metadata.headers.type == message_type]


def _lose_a_stock_received(domain):
    """Seed an item and crash a `ReceiveStock` on it, so its StockReceived has no row."""
    item_id = _seed_item(domain, on_hand=0)
    _receive_stock_crashing_on_commit(domain, item_id, 10)
    (lost,) = _stored(domain, f"inventory::inventory_item-{item_id}", RECEIVED)
    assert _rows_for(domain, lost.metadata.headers.id) == []  # precondition: row lost
    return lost


@pytest.mark.usefixtures("inventory_ctx")
def test_engine_startup_sweep_restores_the_lost_outbox_row():
    """The sweep the engine runs before it starts its subscriptions restores the row."""
    from protean import current_domain
    from protean.server.engine import Engine

    _reset_stores(current_domain)
    item_id = _seed_item(current_domain, on_hand=0)

    _receive_stock_crashing_on_commit(current_domain, item_id, 10)
    assert _internal_received_rows(current_domain, item_id) == []  # precondition: row lost

    engine = Engine(current_domain, test_mode=True)
    try:
        repaired = engine._reconcile_outbox_on_startup()
    finally:
        engine.loop.close()

    # The sweep returns 0 on any exception, so the row is the proof.
    # StockReceived is not published, so the internal row is the only one.
    assert repaired == 1
    assert len(_internal_received_rows(current_domain, item_id)) == 1


@pytest.mark.protean_bug(
    issue=1653,
    state="guard",
    bug=(
        "`reconcile_outbox` rebuilt only the internal row, so a lost `published=True` event never got back its row for"
        " the external broker. Fixed in proteanhq/protean#1718 (`4e82cdc`)."
    ),
)
@pytest.mark.usefixtures("inventory_ctx")
def test_reconcile_restores_the_external_row_of_a_published_event():
    """A lost published event gets back its internal row and its `global` row."""
    from protean import current_domain
    from protean.utils.outbox import OutboxStatus, reconcile_outbox

    from inventory.stock.reservation import ReserveStock

    _reset_stores(current_domain)
    # Enough stock that the reservation stays above the reorder point, so no
    # LowStockDetected joins StockReserved in the same commit.
    item_id = _seed_item(current_domain, on_hand=100)

    _process_crashing_on_commit(
        current_domain,
        ReserveStock(inventory_item_id=item_id, order_id=f"ord-{uuid.uuid4().hex[:8]}", quantity=5),
    )
    (stored,) = _stored(current_domain, f"inventory::inventory_item-{item_id}", RESERVED)  # the append landed
    message_id = stored.metadata.headers.id
    assert _rows_for(current_domain, message_id) == []  # precondition: rows lost
    rows_before = _total_rows(current_domain)

    assert reconcile_outbox(current_domain) == 2

    rows = _rows_for(current_domain, message_id)
    assert sorted(r.target_broker for r in rows) == ["default", "global"]
    assert {r.type for r in rows} == {RESERVED}
    assert {r.status for r in rows} == {OutboxStatus.PENDING.value}
    assert _total_rows(current_domain) == rows_before + 2


@pytest.mark.protean_bug(
    issue=1648,
    state="guard",
    bug=(
        "`reconcile_outbox` gave a row to every message at the tail of `$all` that had none in this context's outbox, "
        "so another context's event or a command at the tail of the shared store got a row this context never owns. "
        "Fixed in proteanhq/protean#1655 (`581276a`)."
    ),
)
@pytest.mark.usefixtures("inventory_ctx")
def test_reconcile_skips_another_contexts_event_at_the_tail(ordering_bed):
    """An ordering event at the tail gets no row, and the lost inventory event behind it does."""
    from protean import current_domain
    from protean.utils.outbox import reconcile_outbox

    from ordering.cart.cart import ShoppingCart

    _reset_stores(current_domain)
    lost = _lose_a_stock_received(current_domain)

    # Append only to the shared event store, so ordering's relational stores
    # stay empty and inventory_ctx's event-store reset clears the message.
    with ordering_bed.domain.domain_context():
        cart = ShoppingCart.create(customer_id=f"cust-{uuid.uuid4().hex[:8]}")
        cart.add_item(product_id="p-1", variant_id="v-1", quantity=1)
        assert cart._events, "Expected add_item to raise an event"
        ordering_bed.domain.event_store.store.append(cart._events[-1])

    foreign = _newest(current_domain)
    assert foreign.metadata.headers.type.startswith("Ordering.")  # precondition
    rows_before = _total_rows(current_domain)

    assert reconcile_outbox(current_domain) == 1

    assert [r.target_broker for r in _rows_for(current_domain, lost.metadata.headers.id)] == ["default"]
    assert _rows_for(current_domain, foreign.metadata.headers.id) == []
    assert _total_rows(current_domain) == rows_before + 1


@pytest.mark.protean_bug(
    issue=1648,
    state="guard",
    bug=(
        "`reconcile_outbox` gave a row to every message at the tail of `$all` that had none in this context's outbox, "
        "so another context's event or a command at the tail of the shared store got a row this context never owns. "
        "Fixed in proteanhq/protean#1655 (`581276a`)."
    ),
)
@pytest.mark.usefixtures("inventory_ctx")
def test_reconcile_skips_a_command_at_the_tail():
    """A command at the tail gets no row, and the lost event behind it does."""
    from protean import current_domain
    from protean.utils.outbox import reconcile_outbox

    from inventory.stock.receiving import ReceiveStock

    _reset_stores(current_domain)
    lost = _lose_a_stock_received(current_domain)

    command = current_domain._enrich_command(
        ReceiveStock(inventory_item_id=lost.metadata.headers.stream.split("-", 1)[1], quantity=10),
        asynchronous=True,
    )
    current_domain.event_store.store.append(command)

    tail = _newest(current_domain)
    assert tail.metadata.headers.type == ReceiveStock.__type__  # precondition
    rows_before = _total_rows(current_domain)

    assert reconcile_outbox(current_domain) == 1

    assert [r.target_broker for r in _rows_for(current_domain, lost.metadata.headers.id)] == ["default"]
    assert _rows_for(current_domain, tail.metadata.headers.id) == []
    assert _total_rows(current_domain) == rows_before + 1


@pytest.mark.protean_bug(
    issue=1907,
    state="open",
    bug=(
        "`reconcile_outbox` repairs only when the newest event the context owns has no outbox row. When another writer"
        " in the same context (an API request, a subscriber, a second engine worker) commits after the crash, the lost"
        " event is never repaired, whatever `--limit` is."
    ),
)
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Protean bug proteanhq/protean#1907: reconcile repairs only when the newest event of the context lacks its row",
)
@pytest.mark.usefixtures("inventory_ctx")
def test_reconcile_repairs_a_lost_event_behind_a_later_commit():
    """A lost event is repaired even when a later commit of the same context succeeded."""
    from protean import current_domain
    from protean.utils.outbox import reconcile_outbox

    from inventory.stock.receiving import ReceiveStock

    _reset_stores(current_domain)
    lost = _lose_a_stock_received(current_domain)
    # Another writer (an API request, a subscriber, a second engine worker)
    # commits after the crash, so the newest inventory event has its row.
    current_domain.process(ReceiveStock(inventory_item_id=_seed_item(current_domain, on_hand=0), quantity=5))

    reconcile_outbox(current_domain)

    assert [r.target_broker for r in _rows_for(current_domain, lost.metadata.headers.id)] == ["default"]


@pytest.mark.protean_bug(
    issue=1906,
    state="open",
    bug=(
        "`reconcile_outbox` run while a unit of work sits between its event-store append and its relational commit "
        "sees no outbox row, inserts one and commits first. The live commit then fails on the `(message_id, "
        "target_broker)` unique index and its caller gets `TransactionError`, though the event is in the store and "
        'will be published. The engine docstring calls a race "safe", which holds only for one sweep against another. '
        "`make outbox-reconcile` says to stop the API and engines first."
    ),
)
@pytest.mark.xfail(
    strict=True,
    raises=TransactionError,
    reason="Protean bug proteanhq/protean#1906: reconcile inserts the row of a live, uncommitted unit of work, so its commit fails",
)
@pytest.mark.usefixtures("inventory_ctx")
def test_reconcile_beside_a_live_commit_does_not_fail_it():
    """Reconcile run while a command sits between its append and its commit leaves that commit alone."""
    from protean import current_domain
    from protean.utils.outbox import reconcile_outbox
    from sqlalchemy.orm import Session

    from inventory.stock.receiving import ReceiveStock

    domain = current_domain._get_current_object()
    _reset_stores(domain)
    item_id = _seed_item(domain, on_hand=0)

    # Hold the live commit after its append and run one sweep in another
    # thread, the way `make outbox-reconcile` or a starting worker would.
    real_commit = Session.commit
    sweep = {}

    def commit_after_a_sweep(session, *args, **kwargs):
        if "created" not in sweep:
            sweep["created"] = None  # the sweep's own commit must go straight through
            thread = threading.Thread(target=lambda: sweep.update(created=reconcile_outbox(domain)))
            thread.start()
            thread.join(timeout=30)
            # Recorded, not asserted: the unit of work would wrap an assertion
            # raised here in the TransactionError this test expects.
            sweep["blocked"] = thread.is_alive()
        return real_commit(session, *args, **kwargs)

    def assert_the_sweep_finished():
        assert not sweep["blocked"], "the sweep blocked on the live transaction"
        assert sweep["created"] is not None, "the sweep did not run to the end"

    Session.commit = commit_after_a_sweep
    try:
        domain.process(ReceiveStock(inventory_item_id=item_id, quantity=10), asynchronous=False)
    except TransactionError:
        assert_the_sweep_finished()
        raise
    finally:
        Session.commit = real_commit

    assert_the_sweep_finished()
    assert len(_internal_received_rows(domain, item_id)) == 1


@pytest.mark.protean_bug(
    issue=1908,
    state="open",
    bug=(
        "For a state-based (CQRS) aggregate, a crash after the event-store append rolls back the aggregate row with "
        "the outbox rows. `reconcile_outbox` then restores the outbox rows, so the event is published for an aggregate"
        " that was never saved: identity's `CustomerRegistered` goes out on the internal and `global` brokers with no "
        "customer row."
    ),
)
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Protean bug proteanhq/protean#1908: reconcile publishes the event of a state-based aggregate whose row rolled back",
)
@pytest.mark.usefixtures("identity_ctx")
def test_reconcile_does_not_publish_an_event_whose_aggregate_was_never_saved():
    """For a state-based aggregate, a crash rolls back the row; its event must not go out alone."""
    from protean import current_domain
    from protean.utils.outbox import reconcile_outbox

    from identity.customer.customer import Customer
    from identity.customer.registration import RegisterCustomer

    _reset_stores(current_domain)
    tag = uuid.uuid4().hex[:8]
    _process_crashing_on_commit(
        current_domain,
        RegisterCustomer(external_id=f"ext-{tag}", email=f"{tag}@example.com", first_name="Ada", last_name="Lovelace"),
    )
    stored = _newest(current_domain)
    assert stored.metadata.headers.type == REGISTERED  # the append landed
    assert current_domain.repository_for(Customer)._dao.query.all().total == 0  # the row rolled back

    reconcile_outbox(current_domain)

    # Either the customer is restored or its event stays unpublished.
    customers = current_domain.repository_for(Customer)._dao.query.all().total
    assert customers == 1 or _rows_for(current_domain, stored.metadata.headers.id) == []
