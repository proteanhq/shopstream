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

STATUS - the recovery half is a known gap (xfail)
    `test_crash_leaves_event_durable_but_unpublished` passes: it characterizes the
    window (event durable, outbox row missing). `test_reconcile_restores_...`
    asserts the DESIRED recovery and currently FAILS: `reconcile_outbox` is a
    no-op against Message-DB because `read_last_message("$all")` returns None, so
    the lost row is never restored. Filed as proteanhq/protean#1073; marked
    xfail(strict=True) so it flips the day the fix lands.

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


def _receive_stock_crashing_on_commit(domain, item_id, quantity):
    """Process ReceiveStock but fail the relational commit AFTER the append."""
    from protean.exceptions import TransactionError
    from sqlalchemy.orm import Session

    from inventory.stock.receiving import ReceiveStock

    real_commit = Session.commit

    def crashing_commit(*_args, **_kwargs):
        raise _SimulatedCrash("crash between event-store append and relational commit")

    Session.commit = crashing_commit
    try:
        with pytest.raises(TransactionError):
            domain.process(
                ReceiveStock(inventory_item_id=item_id, quantity=quantity),
                asynchronous=False,
            )
    finally:
        Session.commit = real_commit  # reconcile below must use the real commit


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


@pytest.mark.xfail(
    strict=True,
    reason=(
        "proteanhq/protean#1073: reconcile_outbox is a no-op against Message-DB "
        "because read_last_message('$all') returns None, so the outbox row lost in "
        "the crash window is never restored. Remove xfail when the fix lands."
    ),
)
@pytest.mark.usefixtures("inventory_ctx")
def test_reconcile_restores_the_lost_outbox_row():
    """P21: reconciliation must recreate the outbox row so the event still publishes."""
    from protean import current_domain
    from protean.utils.outbox import reconcile_outbox

    _reset_stores(current_domain)
    item_id = _seed_item(current_domain, on_hand=0)

    _receive_stock_crashing_on_commit(current_domain, item_id, 10)
    assert _internal_received_rows(current_domain, item_id) == []  # precondition: row lost

    reconcile_outbox(current_domain)

    # Desired: the durable event's outbox row is restored, so it will be published.
    assert len(_internal_received_rows(current_domain, item_id)) == 1
