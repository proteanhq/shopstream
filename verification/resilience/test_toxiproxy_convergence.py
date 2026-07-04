"""T2.6 - fault-tolerant convergence under Toxiproxy fault injection.

WHAT THIS CHECKS
    Property: under a TRANSIENT broker fault, a FIXED workload with a hand-computed
    end state must still converge — the outbox drains to zero and the read-model
    projection reaches the expected value. Nothing is lost.

    The async pipeline under test (inventory domain):
        command -> aggregate + outbox row (Postgres, sync)
                -> engine OutboxProcessor publishes to the Redis broker
                -> StreamSubscription -> projector -> InventoryLevel projection

    Toxiproxy sits in front of the Redis broker; the inventory broker is routed
    through it just by setting `REDIS_URL` to the proxy port (the domain.toml URI is
    `${REDIS_URL|...}` — no src change). Postgres + the event store stay direct, so
    a Redis toxic stalls exactly the publish/consume steps.

    Workload: init 20 units, reserve 3 -> reserved=3, available=17. FIXED, not the
    random Locust load.

SCOPE — the PASSING assertion is the LATENCY case
    Under broker LATENCY the pipeline converges cleanly, so that is the guarded
    property. A hard PARTITION was also injected during exploration and surfaced
    real findings (documented in TICKETS T2.6), but full re-convergence after a
    hard partition is NOT reliable via an in-process `Engine.run()` drain (see the
    findings below), so it is not asserted here — it needs the real engine process.

    Findings from the partition injection (all proteanhq/protean#1055-class):
      * without a socket timeout on the broker, the engine BLOCKS FOREVER on a
        Redis read during a partition instead of failing fast;
      * after a partition the broker's `redis_instance` is left None and the engine
        never re-establishes it (needs a manual `broker._ensure_connection()`);
      * messages already delivered-but-unacked when the partition hits can stay
        stuck in the consumer group's pending list and are not reclaimed by an
        in-process drain, so the projection converges only partially.

WHY ENGINE-MARKED / LOCAL
    Needs the real async engine + Redis + Postgres + a running Toxiproxy.
    `@pytest.mark.engine` (deselected in CI via `-m "not engine"`, like the saga +
    DLQ tests; #1055). Run in base (async) env.

RUN:
    make docker-up && make toxiproxy-up && make toxiproxy-verify
"""

from __future__ import annotations

import contextlib
import os
import uuid

# Route the inventory broker through Toxiproxy — MUST be set before the inventory
# domain is imported/initialized (the broker URI is read at init time). The socket
# timeouts bound broker ops so a fault fails fast instead of hanging.
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:26379/3?socket_connect_timeout=1&socket_timeout=2")

import pytest  # noqa: E402
import requests  # noqa: E402

TOXIPROXY_API = "http://localhost:8474"
PROXY_NAME = "redis"
PROXY_LISTEN = "0.0.0.0:26379"
REDIS_UPSTREAM = "host.docker.internal:16379"


def _toxiproxy_ready() -> tuple[bool, str]:
    if os.environ.get("PROTEAN_ENV") in ("test", "memory"):
        return False, "needs the base (async) env; run with PROTEAN_ENV=development"
    try:
        if requests.get(f"{TOXIPROXY_API}/version", timeout=2).status_code != 200:
            return False, "toxiproxy API not healthy on :8474"
    except requests.RequestException:
        return False, "toxiproxy not reachable on :8474 (run `make toxiproxy-up`)"
    return True, ""


_ready, _why = _toxiproxy_ready()
pytestmark = [
    pytest.mark.engine,
    pytest.mark.slow,
    pytest.mark.skipif(not _ready, reason=f"toxiproxy fault-injection stack unavailable: {_why}"),
]


# --- toxiproxy control -------------------------------------------------------


def _ensure_proxy() -> None:
    existing = requests.get(f"{TOXIPROXY_API}/proxies", timeout=5).json()
    if PROXY_NAME not in existing:
        requests.post(
            f"{TOXIPROXY_API}/proxies",
            json={"name": PROXY_NAME, "listen": PROXY_LISTEN, "upstream": REDIS_UPSTREAM},
            timeout=5,
        )
    _clear_toxics()
    requests.post(f"{TOXIPROXY_API}/proxies/{PROXY_NAME}", json={"enabled": True}, timeout=5)


def _clear_toxics() -> None:
    for toxic in requests.get(f"{TOXIPROXY_API}/proxies/{PROXY_NAME}/toxics", timeout=5).json():
        requests.delete(f"{TOXIPROXY_API}/proxies/{PROXY_NAME}/toxics/{toxic['name']}", timeout=5)


def _add_latency(ms: int) -> None:
    requests.post(
        f"{TOXIPROXY_API}/proxies/{PROXY_NAME}/toxics",
        json={"name": "lat", "type": "latency", "attributes": {"latency": ms}},
        timeout=5,
    )


# --- inventory async pipeline helpers ----------------------------------------


@pytest.fixture()
def inventory_domain():
    """Inventory domain (async, broker via Toxiproxy), with a clean outbox+stream."""
    _ensure_proxy()

    from inventory.domain import inventory

    inventory.init()
    with inventory.domain_context():
        inventory.truncate_database()
        import redis

        redis.Redis(host="localhost", port=26379, db=3).flushdb()
        yield inventory
    _clear_toxics()


def _drain(inventory, *, until, max_cycles=10) -> int:
    from protean.server.engine import Engine

    broker = inventory.brokers["default"]
    for cycle in range(1, max_cycles + 1):
        # The engine won't re-establish a dropped broker connection on its own;
        # ping + reconnect-if-broken (preserving pool settings). #1055-class.
        with contextlib.suppress(Exception):
            broker._ensure_connection()
        with contextlib.suppress(Exception):
            Engine(inventory, test_mode=True).run()
        if until():
            return cycle
    return max_cycles


def _pending_outbox(inventory) -> int:
    repo = inventory._get_outbox_repo("default")
    return repo._dao.query.exclude(status="published").filter(target_broker="default").count()


def _reserved(inventory, item_id):
    from inventory.projections.inventory_level import InventoryLevel

    try:
        return inventory.repository_for(InventoryLevel).get(item_id).reserved
    except Exception:  # noqa: BLE001 - projection not created yet
        return None


def _run_fixed_workload(inventory) -> str:
    from inventory.stock.initialization import InitializeStock
    from inventory.stock.reservation import ReserveStock

    sfx = uuid.uuid4().hex[:8]
    item_id = inventory.process(
        InitializeStock(
            product_id=f"p-{sfx}",
            variant_id=f"v-{sfx}",
            warehouse_id=f"w-{sfx}",
            sku=f"SKU-{sfx}",
            initial_quantity=20,
        ),
        asynchronous=False,
    )
    for i in range(3):
        inventory.process(
            ReserveStock(inventory_item_id=item_id, order_id=f"o-{sfx}-{i}", quantity=1),
            asynchronous=False,
        )
    return item_id


# --- the check ---------------------------------------------------------------


def test_outbox_durable_before_publish(inventory_domain):
    """The fixed workload writes its events to the outbox synchronously (pending),
    independent of the broker — so a broker fault can delay publishing but never
    lose the events. Fast, fault-free sanity check of the durability premise."""
    item_id = _run_fixed_workload(inventory_domain)
    assert _pending_outbox(inventory_domain) > 0
    assert _reserved(inventory_domain, item_id) is None  # nothing published/projected yet


def test_converges_under_broker_latency(inventory_domain):
    """Under a 80ms latency toxic on the Redis broker, the fixed workload still
    drains the outbox to zero and the InventoryLevel projection converges to
    reserved=3. The fault delays the pipeline; it loses nothing."""
    _add_latency(80)
    item_id = _run_fixed_workload(inventory_domain)

    cycles = _drain(
        inventory_domain,
        until=lambda: _pending_outbox(inventory_domain) == 0 and _reserved(inventory_domain, item_id) == 3,
        max_cycles=10,
    )

    assert _reserved(inventory_domain, item_id) == 3, f"projection did not converge under latency (in {cycles} cycles)"
    assert _pending_outbox(inventory_domain) == 0, "outbox did not drain to zero under latency"
