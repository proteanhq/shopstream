"""sync == async - the same workload yields the same read model either way (T2.1).

WHAT THIS CHECKS
    Protean can process a domain's events two ways, chosen by `event_processing`:
      * `sync`  - events fire inline during the command's UoW; projectors run
        immediately, so the read model is up to date when `process()` returns.
      * `async` - events land in the outbox; a background engine later publishes
        them to the broker and the subscription runs the projectors.

    Metamorphic property (source B): the FINAL read model must be identical
    whichever path ran. The paths differ only in WHEN and by what machinery the
    projector runs, never in WHAT it computes.

    We run one FIXED workload (init 20 units, reserve 3) twice against the same
    real Postgres — once with `event_processing=sync` (inline) and once with
    `async` (outbox + `Engine.run()` drain) — and assert the two InventoryLevel
    projections match field-for-field (bar the row id, timestamp and version).

    The outbox is on in both modes, so the sync run also leaves its events as
    pending outbox rows. The test marks them published before the async run.
    Otherwise the drain publishes them and every consumer receives the sync
    item's events a second time. Projectors marked `idempotent=True` skip the
    copy. EventAudit is not idempotent and adds a row per delivery, so the test
    checks its row count for the sync item to prove no replay happened.

KNOWN FAILURE: PROTEAN CAN PUBLISH ONE AGGREGATE'S EVENTS OUT OF ORDER
    The outbox claims rows by priority alone, so rows with the same priority
    publish in whatever order the database returns them (proteanhq/protean#1893).
    On Postgres this shows up in two ways:
      * the async item's `StockReserved` arrives before its `StockInitialized`.
        The projectors raise `ObjectNotFoundError`, the retries use up the
        drain's cycles, and the async row is missing or short.
      * its three `StockReserved` arrive out of order. InventoryLevel copies
        `available` from the last event it applies, so it ends at 19, not 17.
    Until the pin has the fix, this check passes on some runs only. It gets no
    xfail: the repo pins open bugs with strict xfails, and a strict xfail would
    fail on the runs that pass.

WHY THIS WAS DEFERRED FROM T2.1, AND IS ENGINE-MARKED
    Both CI envs (memory, test) are `sync`, so a real sync-vs-async comparison
    needs the async engine + Redis + Postgres, which was unreliable in CI
    (proteanhq/protean#1055, now fixed in the pin). It stays `@pytest.mark.engine`
    (deselected via `-m "not engine"`) until an engine CI job is re-added, and
    runs in the base (async) env. The `sync`/`async` test-body equivalence at
    the helper level is not checked here: `protean.testing.process_and_wait` and
    `drain` are tested in Protean (T0.1). This check covers the end-to-end
    read-model equivalence.

RUN:
    Stop the dev engines first. They read the same `inventory_local` outbox and
    Redis DB 3, so they can publish the sync rows before the test marks them.
    make docker-up && make truncate-db
    make sync-async-verify        # PROTEAN_ENV=development, base(async) env
"""

from __future__ import annotations

import contextlib
import os
import socket
import uuid

import pytest

_VOLATILE = {"inventory_item_id", "updated_at", "_version"}


def _stack_ready() -> tuple[bool, str]:
    if os.environ.get("PROTEAN_ENV") in ("test", "memory"):
        return False, "needs the base (async) env; run with PROTEAN_ENV=development"
    for host, port, name in [("127.0.0.1", 16379, "redis"), ("127.0.0.1", 15432, "postgres")]:
        try:
            with socket.create_connection((host, port), timeout=2):
                pass
        except OSError:
            return False, f"{name} not reachable on {host}:{port} (run `make docker-up`)"
    return True, ""


_ready, _why = _stack_ready()
pytestmark = [
    pytest.mark.engine,
    pytest.mark.slow,
    pytest.mark.skipif(not _ready, reason=f"async engine stack unavailable: {_why}"),
]


@pytest.fixture()
def inventory_domain():
    from inventory.domain import inventory

    inventory.init()
    original = inventory.config.get("event_processing")
    with inventory.domain_context():
        inventory.truncate_database()
        yield inventory
    inventory.config["event_processing"] = original  # don't leak the flipped mode


def _run_workload(inventory, *, product_id, variant_id, warehouse_id, sku) -> str:
    """Init 20 units, reserve 3 -> reserved=3. Same inputs each call, fresh item id."""
    from inventory.stock.initialization import InitializeStock
    from inventory.stock.reservation import ReserveStock

    item_id = inventory.process(
        InitializeStock(
            product_id=product_id,
            variant_id=variant_id,
            warehouse_id=warehouse_id,
            sku=sku,
            initial_quantity=20,
        ),
        asynchronous=False,
    )
    for i in range(3):
        inventory.process(
            ReserveStock(inventory_item_id=item_id, order_id=f"ord-{item_id}-{i}", quantity=1),
            asynchronous=False,
        )
    return item_id


def _mark_published(inventory, item_id) -> int:
    """Mark the item's pending outbox rows, for every broker, as published. Returns how many."""
    stream = f"inventory::inventory_item-{item_id}"
    repo = inventory._get_outbox_repo("default")
    rows = [r for r in repo.find_unprocessed() if r.stream_name == stream]
    for row in rows:
        row.mark_published()
        repo.add(row)
    return len(rows)


def _audit_count(inventory, item_id) -> int:
    from inventory.projections.event_audit import EventAudit

    return len(inventory.repository_for(EventAudit).query.filter(inventory_item_id=item_id).all().items)


def _level_view(inventory, item_id) -> dict | None:
    from inventory.projections.inventory_level import InventoryLevel

    level = inventory.repository_for(InventoryLevel).get_or_none(item_id)
    if level is None:  # projection not created yet
        return None
    return {k: v for k, v in level.to_dict().items() if k not in _VOLATILE}


# Hand-rolled on purpose: this loop suppresses an exception from each engine
# pass, and `protean.testing.drain` lets it propagate. The
# `broker._ensure_connection()` call is a leftover: since proteanhq/protean#1086
# the Redis broker reconnects on its own after a close.
def _drain(inventory, *, until, max_cycles=10) -> None:
    from protean.server.engine import Engine

    broker = inventory.brokers["default"]
    for _ in range(max_cycles):
        with contextlib.suppress(Exception):
            broker._ensure_connection()
        with contextlib.suppress(Exception):
            Engine(inventory, test_mode=True).run()
        if until():
            return


def test_sync_and_async_yield_the_same_projection(inventory_domain):
    inv = inventory_domain
    sfx = uuid.uuid4().hex[:8]
    inputs = {
        "product_id": f"prod-{sfx}",
        "variant_id": f"var-{sfx}",
        "warehouse_id": f"wh-{sfx}",
        "sku": f"SKU-{sfx}",
    }

    # Path 1 — sync: events fire inline, so the projection is ready immediately.
    inv.config["event_processing"] = "sync"
    sync_item = _run_workload(inv, **inputs)
    sync_view = _level_view(inv, sync_item)
    sync_audit_rows = _audit_count(inv, sync_item)
    # One StockInitialized row for the internal broker, and two rows (internal
    # and the global bus) for each of the three published StockReserved.
    assert _mark_published(inv, sync_item) == 7, "not every sync outbox row was kept out of the drain"

    # Path 2 — async: events go to the outbox; drain the engine to project them.
    inv.config["event_processing"] = "async"
    async_item = _run_workload(inv, **inputs)
    # Wait for EventAudit too, so the replay check below sees what it would
    # have processed by the time the async item is fully projected.
    _drain(
        inv,
        until=lambda: (
            (v := _level_view(inv, async_item)) is not None
            and v.get("reserved") == 3
            and _audit_count(inv, async_item) == 4
        ),
    )
    async_view = _level_view(inv, async_item)

    assert sync_view is not None, "sync path did not project inline"
    assert sync_audit_rows == 4, "sync path did not run EventAudit inline"
    after_drain = _level_view(inv, sync_item)
    assert (after_drain["reserved"], after_drain["available"]) == (3, 17)
    # EventAudit adds a row per delivery, so a replay of the sync item's events
    # would raise this count.
    assert _audit_count(inv, sync_item) == sync_audit_rows, "the async drain replayed the sync item's events"
    assert async_view is not None, "async path did not converge after draining"
    # Same inputs, same events, same fold -> identical read model (bar the row id).
    assert sync_view == async_view
