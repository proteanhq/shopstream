"""The engine's `/readyz` answer has the shape ShopStream's probes and runbooks read.

WHAT THIS CHECKS
    `/readyz` reports `checks.subscriptions` as an object: a `total` and one
    `details` row per subscription, with lag, pending, DLQ depth, status and
    circuit-breaker state. This check builds the ordering engine, starts a
    `HealthServer` for it on an OS-assigned port, reads `/readyz` over HTTP and
    asserts:

    - it answers 200, which the compose healthcheck relies on;
    - every subscription the engine wired (handlers, broker subscribers and
      outbox processors, including the one that publishes to the shared
      `global` bus) has a row, and no row is `unknown`;
    - each row carries the documented fields, including `lag_seconds` and
      `lag_drain_rate`, the two fields the planned subscription-lag measurement
      reads (#98);
    - an empty outbox reads `lag: 0` and `status: ok`, not `lag: null`
      (proteanhq/protean#1288 made an unknown lag `null`, so a healthy row
      reading `null` would hide real lag);
    - `lag_seconds` is `null` on every row. Protean computes it only for
      event-store subscriptions, and ShopStream runs none.

    `lag_drain_rate` is checked only for presence. It needs two refreshes and a
    numeric `lag_seconds`, so it is `null` on every row here.

WHY IT DOES NOT RUN THE ENGINE
    `Engine(test_mode=True)` wires every subscription but skips the health
    server, and `Engine.run()` is unreliable against CI's Redis
    (proteanhq/protean#1055). The check builds the engine, starts a
    `HealthServer` for it on the engine's own event loop, and never calls
    `run()`. The subscription block is collected from the stores, not from
    running consumers, so it is complete without `run()`.
"""

from __future__ import annotations

import asyncio

import pytest

from verification.support.health_http import health_request

# The fields Protean documents for a `/readyz` subscription row: the
# SubscriptionStatus fields minus the stream cursors, plus the drain rate.
# `circuit_state` appears only on rows the engine has a breaker for.
ROW_FIELDS = {
    "name",
    "handler_name",
    "subscription_type",
    "stream_category",
    "lag",
    "lag_seconds",
    "lag_drain_rate",
    "pending",
    "dlq_depth",
    "status",
}

GLOBAL_OUTBOX = "outbox-processor-default-to-global-external"


async def _read_readyz(engine) -> tuple[int, dict]:
    from protean.server.health import HealthServer

    server = HealthServer(engine)
    server.port = 0
    await server.start()
    assert server.port != 0, f"the health server did not bind on {server.host}"
    try:
        # The first collection runs in a worker thread; until it lands the
        # block says `collection_pending` and has no rows.
        for _ in range(100):
            code, body = await health_request(server.host, server.port, "GET", "/readyz")
            block = body.get("checks", {}).get("subscriptions", {})
            if not block.get("collection_pending"):
                return code, body
            await asyncio.sleep(0.1)
        pytest.fail("/readyz never finished its first subscription collection")
    finally:
        await server.stop()


@pytest.fixture(scope="module")
def readyz(ordering_bed):
    """`(status code, body, names of the subscriptions the engine wired)`."""
    from protean.server.engine import Engine

    with ordering_bed.domain_context():
        engine = Engine(ordering_bed.domain, test_mode=True)
        try:
            code, body = engine.loop.run_until_complete(_read_readyz(engine))
            wired = {*engine._subscriptions, *engine._broker_subscriptions, *engine._outbox_processors}
            return code, body, wired
        finally:
            engine.loop.close()


@pytest.fixture(scope="module")
def rows(readyz):
    _, body, _ = readyz
    return {row["name"]: row for row in body["checks"]["subscriptions"]["details"]}


def test_readyz_is_ready(readyz):
    code, body, _ = readyz
    assert code == 200, body
    assert body["status"] == "ok"


def test_the_subscription_block_is_fresh_and_complete(readyz):
    _, body, _ = readyz
    block = body["checks"]["subscriptions"]

    assert block["details"], "no subscription rows"
    assert "collection_error" not in block
    assert "stale" not in block
    names = [row["name"] for row in block["details"]]
    assert len(set(names)) == len(names), "a subscription appears twice"


def test_every_wired_subscription_has_a_row(readyz, rows):
    _, _, wired = readyz

    assert GLOBAL_OUTBOX in wired
    assert wired <= rows.keys(), f"no row for {sorted(wired - rows.keys())}"
    unknown = [name for name, row in rows.items() if row["subscription_type"] == "unknown"]
    assert not unknown, f"rows the collector could not match: {unknown}"


def test_every_row_has_the_documented_fields(rows):
    assert rows
    for name, row in rows.items():
        missing = ROW_FIELDS - row.keys()
        assert not missing, f"{name} lacks {sorted(missing)}"


def test_empty_global_outbox_reads_zero_lag(rows):
    outbox = rows[GLOBAL_OUTBOX]

    assert outbox["subscription_type"] == "outbox"
    assert outbox["lag"] == 0
    assert outbox["pending"] == 0
    assert outbox["dlq_depth"] == 0
    assert outbox["status"] == "ok"


def test_no_row_reports_lag_seconds(rows):
    assert rows
    for name, row in rows.items():
        assert row["lag_seconds"] is None, name


def test_every_stream_row_reports_a_closed_breaker(rows):
    stream_rows = {name: row for name, row in rows.items() if row["subscription_type"] == "stream"}

    assert stream_rows
    for name, row in stream_rows.items():
        assert row.get("circuit_state") == "closed", name
