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
    projections match field-for-field (bar the row id / timestamp).

WHY THIS WAS DEFERRED FROM T2.1, AND IS ENGINE-MARKED
    Both CI envs (memory, test) are `sync`, so a real sync-vs-async comparison
    needs the async engine + Redis + Postgres — unreliable in CI (proteanhq/
    protean#1055). So it is `@pytest.mark.engine` (deselected via `-m "not engine"`)
    and runs in the base (async) env. The `sync`/`async` test-body equivalence at
    the helper level is already covered by `process_and_wait`/`drain` (T0.1); this
    check adds the end-to-end read-model equivalence.

RUN:
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


def _level_view(inventory, item_id) -> dict | None:
    from inventory.projections.inventory_level import InventoryLevel

    try:
        level = inventory.repository_for(InventoryLevel).get(item_id)
    except Exception:  # noqa: BLE001 - projection not created yet
        return None
    return {k: v for k, v in level.to_dict().items() if k not in _VOLATILE}


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

    # Path 2 — async: events go to the outbox; drain the engine to project them.
    inv.config["event_processing"] = "async"
    async_item = _run_workload(inv, **inputs)
    _drain(inv, until=lambda: (v := _level_view(inv, async_item)) is not None and v.get("reserved") == 3)
    async_view = _level_view(inv, async_item)

    assert sync_view is not None, "sync path did not project inline"
    assert async_view is not None, "async path did not converge after draining"
    # Same inputs, same events, same fold -> identical read model (bar the row id).
    assert sync_view == async_view
