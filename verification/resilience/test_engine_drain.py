"""Every engine reads ShopStream's drain window and reports a drain on `POST /drainz`.

WHAT THIS CHECKS
    For each of the nine contexts, this builds the engine, starts its own
    health server on an OS-assigned port and asserts:

    - `engine.drain_timeout` is 20.0, the `[server] drain_timeout` in the
      context's `domain.toml`. Protean falls back to 10 on a missing or invalid
      value, so a typo there would read 10.0 here;
    - before a drain, `/readyz` reports `checks.draining: false`;
    - `POST /drainz` answers 200 with `status: draining` and this process's pid;
    - after it, `/readyz` answers 503 with exactly
      `{"status": "unavailable", "checks": {"draining": true}}`, `/healthz`
      still answers 200, and `GET /drainz` is a 404;
    - after it, every Redis stream subscription and every `global` broker
      subscriber would stop before its next read, and every outbox processor
      would not, so committed rows keep publishing while the engine drains.
      Identity and catalogue run no `global` broker subscriber; the other seven
      contexts must wire at least one.

    The last check reads Protean internals on purpose: the engine's
    `_subscriptions`, `_broker_subscriptions` and `_outbox_processors` dicts and
    each one's `_quiescing()`, the method its poll loop asks before it reads the
    next batch. No public API reports per-subscription drain state.

WHY IT DOES NOT RUN THE ENGINE
    `Engine(test_mode=True)` wires every subscription and builds the health
    server but does not start it, and `Engine.run()` is unreliable against CI's
    Redis (proteanhq/protean#1055). The check starts the engine's own
    `_health_server` on the engine's event loop and never calls `run()`. That a
    drained subscription really stops pulling, and that a message survives a
    drain and restart, is the hand check in `scripts/verify-drain.sh`.

WHY IT NEEDS `--protean-env test`
    The memory env swaps the Redis brokers for inline ones. The check is about
    the Redis stream subscriptions the engines run in production, so it skips
    anywhere else.
"""

from __future__ import annotations

import os

import pytest

from verification.support.health_http import health_request

pytestmark = pytest.mark.skipif(
    os.environ.get("PROTEAN_ENV") != "test",
    reason="builds the Redis stream subscriptions; run with --protean-env test",
)

# Contexts that consume nothing from the shared `global` bus.
NO_GLOBAL_SUBSCRIBERS = {"identity", "catalogue"}

CONTEXTS = [
    "identity",
    "catalogue",
    "ordering",
    "inventory",
    "payments",
    "fulfillment",
    "reviews",
    "notifications",
    "loyalty",
]


async def _drain(engine) -> dict[str, tuple[int, dict]]:
    """Start the engine's health server, drain it, and collect each answer."""
    server = engine._health_server
    await server.start()
    assert server.port != 0, f"the health server did not bind on {server.host}"
    host, port = server.host, server.port
    try:
        return {
            "readyz_before": await health_request(host, port, "GET", "/readyz"),
            "drainz": await health_request(host, port, "POST", "/drainz"),
            "readyz_after": await health_request(host, port, "GET", "/readyz"),
            "healthz_after": await health_request(host, port, "GET", "/healthz"),
            "get_drainz": await health_request(host, port, "GET", "/drainz"),
        }
    finally:
        await server.stop()


@pytest.fixture(scope="module", params=CONTEXTS)
def drained(request):
    """`(engine, answers)` for one context's engine after a `POST /drainz`."""
    from protean.server.engine import Engine

    bed = request.getfixturevalue(f"{request.param}_bed")
    with bed.domain_context(), pytest.MonkeyPatch.context() as mp:
        # Port 0 lets the OS pick a free port, so a running engine on the
        # context's real port cannot clash with this one.
        mp.setitem(bed.domain.config["server"]["health"], "port", 0)
        engine = Engine(bed.domain, test_mode=True)
        try:
            yield engine, engine.loop.run_until_complete(_drain(engine))
        finally:
            engine.loop.close()


def test_engine_reads_the_drain_window(drained):
    engine, _ = drained

    assert engine.drain_timeout == 20.0


def test_readyz_reports_not_draining_before_the_drain(drained):
    _, answers = drained
    _, body = answers["readyz_before"]

    assert body["checks"]["draining"] is False


def test_drainz_answers_with_this_process(drained):
    engine, answers = drained
    code, body = answers["drainz"]

    assert code == 200
    assert body == {"status": "draining", "pid": os.getpid()}
    assert engine.draining is True


def test_a_drained_engine_is_alive_but_not_ready(drained):
    _, answers = drained

    assert answers["readyz_after"] == (503, {"status": "unavailable", "checks": {"draining": True}})
    code, body = answers["healthz_after"]
    assert code == 200, body
    assert answers["get_drainz"][0] == 404


def test_a_drain_quiesces_the_message_subscriptions_but_not_the_outbox(drained):
    engine, _ = drained
    subscriptions = {**engine._subscriptions, **engine._broker_subscriptions}

    assert engine._subscriptions, "the engine wired no stream subscriptions"
    context = engine.domain.name.lower()
    assert bool(engine._broker_subscriptions) == (context not in NO_GLOBAL_SUBSCRIBERS), context
    assert engine._outbox_processors, "the engine wired no outbox processors"
    still_pulling = [name for name, sub in subscriptions.items() if not sub._quiescing()]
    assert not still_pulling, f"still pulling while draining: {still_pulling}"
    paused = [name for name, outbox in engine._outbox_processors.items() if outbox._quiescing()]
    assert not paused, f"outbox processors paused by the drain: {paused}"
