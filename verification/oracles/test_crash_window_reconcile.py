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

STATUS - all six tests are guards
    `test_crash_leaves_event_durable_but_unpublished` characterizes the window
    (event durable, outbox row missing). `test_reconcile_restores_...` asserts the
    recovery: `reconcile_outbox` restores the lost row. It was xfail while
    `reconcile_outbox` was a no-op against Message-DB (`read_last_message("$all")`
    returned None, proteanhq/protean#1073). That fix is in the pin.

    The other four pin how the sweep behaves in a store shared by nine contexts.
    The sweep used to keep every message at the tail of `$all` that had no row
    here, so another context's event or a command at the tail got a row this
    context never owns (proteanhq/protean#1648, fixed in proteanhq/protean#1655).
    It also rebuilt only the internal row, so a published event lost its row for
    the external `global` broker (proteanhq/protean#1653, fixed in
    proteanhq/protean#1718). Both fixes are in the pin:

    - the engine's own startup sweep (`Engine._reconcile_outbox_on_startup`)
      restores the row. It is called directly on an engine that is never run,
      so the check needs no live engine. The method is private; the startup
      sweep has no public entry point.
    - a lost `published=True` event gets back both its internal row and its
      `global` row, under the same message id.
    - another context's event at the tail of the shared store gives 0 rows.
    - a command at the tail gives 0 rows.

WHY POSTGRES + MESSAGE-DB ONLY
    The two-store split and the SQLAlchemy-commit seam only exist with the real
    adapters. Skipped under `--protean-env memory`.

RUN:
    make docker-up && make setup-db      # once
    .venv/bin/python -m pytest \
        verification/oracles/test_crash_window_reconcile.py --protean-env test -q
"""

from __future__ import annotations

import os
import uuid

import pytest

ENV = os.environ.get("PROTEAN_ENV")
pytestmark = pytest.mark.skipif(
    ENV != "test",
    reason="crash-window oracle needs the real two-store split (Postgres + Message-DB); run with --protean-env test",
)

RECEIVED = "Inventory.StockReceived.v1"
RESERVED = "Inventory.StockReserved.v1"


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
    from protean.exceptions import TransactionError
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


def _rows_of_type(domain, message_type, stream):
    """Every outbox row of *message_type* on *stream*, for any broker and status."""
    return [r for r in domain._get_outbox_repo("default").find_by_message_type(message_type) if r.stream_name == stream]


def _total_rows(domain):
    return sum(domain._get_outbox_repo("default").count_by_status().values())


def _newest_type(domain):
    return domain.event_store.store.read_last_message("$all").metadata.headers.type


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

    # The sweep swallows every error and returns 0, so the row is the proof.
    assert repaired >= 1
    assert len(_internal_received_rows(current_domain, item_id)) == 1


@pytest.mark.usefixtures("inventory_ctx")
def test_reconcile_restores_the_external_row_of_a_published_event():
    """A lost published event gets back its internal row and its `global` row."""
    from protean import current_domain
    from protean.utils.outbox import reconcile_outbox

    from inventory.stock.reservation import ReserveStock

    _reset_stores(current_domain)
    # Enough stock that the reservation stays above the reorder point, so no
    # LowStockDetected joins StockReserved in the same commit.
    item_id = _seed_item(current_domain, on_hand=100)
    stream = f"inventory::inventory_item-{item_id}"

    _process_crashing_on_commit(
        current_domain,
        ReserveStock(inventory_item_id=item_id, order_id=f"ord-{uuid.uuid4().hex[:8]}", quantity=5),
    )
    stored = [m for m in current_domain.event_store.store.read(stream) if m.metadata.headers.type == RESERVED]
    assert len(stored) == 1  # the append landed
    assert _rows_of_type(current_domain, RESERVED, stream) == []  # precondition: rows lost

    reconcile_outbox(current_domain)

    rows = _rows_of_type(current_domain, RESERVED, stream)
    assert sorted(r.target_broker for r in rows) == ["default", "global"]
    assert {r.message_id for r in rows} == {stored[0].metadata.headers.id}


@pytest.mark.usefixtures("inventory_ctx")
def test_reconcile_skips_another_contexts_event_at_the_tail(ordering_bed):
    """An ordering event at the tail of the shared store is not inventory's to repair."""
    from protean import current_domain
    from protean.utils.outbox import reconcile_outbox

    from ordering.cart.cart import ShoppingCart

    _reset_stores(current_domain)
    _seed_item(current_domain, on_hand=0)  # inventory's newest event, with its row

    # Append only to the shared event store, so ordering's relational stores
    # stay empty and inventory_ctx's event-store reset clears the message.
    with ordering_bed.domain.domain_context():
        cart = ShoppingCart.create(customer_id=f"cust-{uuid.uuid4().hex[:8]}")
        cart.add_item(product_id="p-1", variant_id="v-1", quantity=1)
        assert cart._events, "Expected add_item to raise an event"
        ordering_bed.domain.event_store.store.append(cart._events[-1])

    assert _newest_type(current_domain).startswith("Ordering.")  # precondition
    rows_before = _total_rows(current_domain)
    assert rows_before > 0

    assert reconcile_outbox(current_domain) == 0
    assert _total_rows(current_domain) == rows_before


@pytest.mark.usefixtures("inventory_ctx")
def test_reconcile_skips_a_command_at_the_tail():
    """A command at the tail never gets an outbox row, so it is not a lost commit."""
    from protean import current_domain
    from protean.utils.outbox import reconcile_outbox

    from inventory.stock.receiving import ReceiveStock

    _reset_stores(current_domain)
    item_id = _seed_item(current_domain, on_hand=0)

    command = current_domain._enrich_command(ReceiveStock(inventory_item_id=item_id, quantity=10), asynchronous=True)
    current_domain.event_store.store.append(command)

    assert _newest_type(current_domain) == ReceiveStock.__type__  # precondition
    rows_before = _total_rows(current_domain)
    assert rows_before > 0

    assert reconcile_outbox(current_domain) == 0
    assert _total_rows(current_domain) == rows_before
