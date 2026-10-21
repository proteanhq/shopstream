"""Regressions in messaging: brokers, streams, engine outbox processors, dead-letter queues and projection rebuilds."""

from __future__ import annotations

import pytest


@pytest.mark.protean_bug(
    issue=1913,
    state="open",
    bug=(
        "`protean projection rebuild` deletes a projection's rows and replays its events, but keeps the "
        "`processed_message` markers. A projector marked `idempotent=True` finds the marker the live delivery wrote "
        "and skips every replayed event, so the rebuilt read model stays empty. The result still counts each skipped "
        "event as dispatched. ShopStream runs no rebuild today."
    ),
)
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="projection rebuild keeps the processed-message markers, so an idempotent projector skips every replayed event",
)
@pytest.mark.usefixtures("payments_ctx")
def test_rebuild_restores_a_projection_whose_projector_is_idempotent():
    """proteanhq/protean#1913: a rebuild empties an idempotent projector's read model.

    `rebuild_projection` (`protean/utils/projection_rebuilder.py`) deletes the
    projection's rows, then replays every stored event through `projector._handle`.
    It leaves the `processed_message` table alone. For a projector declared with
    `idempotent=True`, the `@on` wrapper finds the marker the live delivery wrote,
    and skips the handler. So the rebuilt read model stays empty, and the result
    still counts each skipped event as dispatched. `DailyRevenueProjector` is one
    of the projectors this affects.
    """
    from protean import current_domain
    from protean.utils.projection_rebuilder import rebuild_projection

    from payments.payment.initiation import InitiatePayment
    from payments.payment.webhook import ProcessPaymentWebhook
    from payments.projections.daily_revenue import DailyRevenue, DailyRevenueProjector

    payment_id = current_domain.process(
        InitiatePayment(
            order_id="ord-rebuild",
            customer_id="cust-rebuild",
            amount=40.0,
            currency="USD",
            payment_method_type="credit_card",
            last4="4242",
            idempotency_key="rebuild-1",
        ),
        asynchronous=False,
    )
    current_domain.process(
        ProcessPaymentWebhook(payment_id=payment_id, gateway_transaction_id="txn-rebuild", gateway_status="succeeded"),
        asynchronous=False,
    )
    repo = current_domain.repository_for(DailyRevenue)
    if not DailyRevenueProjector.meta_.idempotent or [r.transaction_count for r in repo.query.all().items] != [1]:
        pytest.fail("precondition: the idempotent projector counted the payment once")

    result = rebuild_projection(current_domain, DailyRevenue)

    if result.errors:
        pytest.fail(f"precondition: the rebuild ran without errors: {result.errors}")
    assert [r.transaction_count for r in repo.query.all().items] == [1]


@pytest.mark.protean_bug(
    issue=None,
    state="open",
    bug=(
        "With two or more consumer groups on a Redis stream, `RedisBroker.trim` runs `XTRIM MINID` at the smallest "
        "`last-delivered-id`. That id marks what each group was handed, not what it acknowledged, so the trim deletes "
        "entries a group's failed handler left pending. Redelivery returns them with no data, `_read_blocking` skips "
        "them, and they are never retried or dead-lettered. The `shopstream` profile turns retention on for every "
        "subscription."
    ),
)
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="the multi-group stream trim deletes entries still pending in a consumer group",
)
@pytest.mark.usefixtures("loyalty_ctx")
def test_stream_trim_keeps_entries_a_consumer_group_has_not_acknowledged():
    """Protean finding (not filed yet): retention trims messages a group still has to retry.

    With two or more consumer groups on a stream, `RedisBroker.trim` runs
    `XTRIM MINID` at the smallest `last-delivered-id`. That id only says which
    entries a group was handed. A handler that failed leaves its entries in the
    group's pending list below that id, and the trim deletes them. Redelivery then
    returns those ids with no fields, `_read_blocking` skips them, and the message
    is never retried or dead-lettered. ShopStream turns retention on for every
    subscription through the `shopstream` profile, so a dispatcher that fails
    during a channel outage can lose its pending sends this way.
    """
    import uuid

    import redis
    from protean import current_domain

    broker = current_domain.brokers["default"]
    client = getattr(broker, "redis_instance", None)
    if client is None:
        pytest.skip("needs the Redis streams broker (run with --protean-env test)")
    # A local test-env run may have no Redis at the broker's URL.
    try:
        client.ping()
    except redis.exceptions.ConnectionError:
        pytest.skip("the default broker's Redis is not reachable")

    stream = f"regression::trim-{uuid.uuid4().hex[:8]}"
    try:
        # Enough entries for an approximate trim to drop whole macro-nodes.
        ids = [client.xadd(stream, {"n": str(i)}) for i in range(300)]
        client.xgroup_create(stream, "failing", id="0")
        client.xgroup_create(stream, "healthy", id="0")
        # Both groups read everything. Only the healthy group acknowledges.
        client.xreadgroup("failing", "c1", {stream: ">"}, count=1000)
        client.xreadgroup("healthy", "c1", {stream: ">"}, count=1000)
        client.xack(stream, "healthy", *ids)
        if client.xpending(stream, "failing")["pending"] != len(ids):
            pytest.fail("precondition: the failing group holds every entry as pending")

        broker.trim(stream, 50000)

        redelivered = client.xreadgroup("failing", "c1", {stream: "0"}, count=1000)
        entries = redelivered[0][1] if redelivered else []
        assert len(entries) == len(ids)
        assert all(fields for _, fields in entries), "pending entries came back without their data"
    finally:
        client.delete(stream)


async def _deliver(subscription, cycles: int) -> int:
    """Run read-then-process cycles of a subscription; return how many messages were delivered."""
    delivered = 0
    for _ in range(cycles):
        batch = await subscription.get_next_batch_of_messages()
        delivered += len(batch)
        if batch:
            await subscription.process_batch(batch)
    return delivered


@pytest.mark.protean_bug(
    issue=None,
    state="open",
    bug=(
        "Since ADR-0042 a subscription dead-letters an exhausted message to `{stream}:dlq`, and the InlineBroker never"
        " moves an owned group's message to its own `_dead_letter_queue`. But the InlineBroker's `dlq_list` reads only"
        " `_dead_letter_queue`, and it has no `dlq_depth`, so the base class returns 0. Under the memory env both "
        "report an empty DLQ while `loyalty::poison_pill:dlq` holds the message. The pin runs `dlq_list` and "
        "`dlq_depth`. `dlq_inspect`, `dlq_replay` and `dlq_purge` read the same `_dead_letter_queue`; that part was "
        "read in the code, not run."
    ),
)
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="the InlineBroker's DLQ API reads only its native DLQ, not the {stream}:dlq stream subscriptions write",
)
@pytest.mark.usefixtures("loyalty_ctx")
# One case per call, so a Protean fix to one of them alone shows as an XPASS.
@pytest.mark.parametrize("read", ["dlq_list", "dlq_depth"])
def test_inline_broker_dlq_api_reads_the_subscription_dlq_stream(monkeypatch, read):
    """Protean finding (not filed yet): the InlineBroker's DLQ API misses what subscriptions dead-letter.

    Since ADR-0042 a subscription owns dead-lettering: it publishes an exhausted
    message to `{stream}:dlq`, and the InlineBroker never moves an owned group's
    message to its own `_dead_letter_queue`. But `dlq_list` on the InlineBroker
    reads only `_dead_letter_queue`, and it has no `dlq_depth`, so the base
    class returns 0. `dlq_inspect`, `dlq_replay` and `dlq_purge` read the same
    `_dead_letter_queue` (read in the code; this pin runs only `dlq_list` and `dlq_depth`).
    Under the memory env the DLQ API reports an empty DLQ while
    `loyalty::poison_pill:dlq` holds the message. The Redis broker reads the
    `{stream}:dlq` stream and reports it.
    """
    import asyncio

    from protean import current_domain
    from protean.adapters.broker.inline import InlineBroker
    from protean.server.engine import Engine
    from protean.server.subscription.stream_subscription import StreamSubscription
    from protean.utils.eventing import Message

    from loyalty.dlq.poison import PoisonEventHandler, PoisonPill

    broker = current_domain.brokers["default"]
    if not isinstance(broker, InlineBroker):
        pytest.skip("needs the InlineBroker (run with --protean-env memory)")
    broker._data_reset()
    monkeypatch.setattr(broker, "_retry_delay", 0)

    stream = "loyalty::poison_pill"
    dlq_stream = f"{stream}:dlq"
    subscription = StreamSubscription(
        Engine(current_domain, test_mode=True),
        stream,
        PoisonEventHandler,
        blocking_timeout_ms=50,
        max_retries=1,
        retry_delay_seconds=0,
        enable_dlq=True,
    )
    asyncio.run(subscription.initialize())
    pill = PoisonPill.detonate("dlq api probe")
    broker.publish(stream, Message.from_domain_object(pill._events[0]).to_dict())
    if asyncio.run(_deliver(subscription, 1)) != 1:
        pytest.fail("precondition: the subscription received the message")
    if len(broker._messages.get(dlq_stream, [])) != 1:
        pytest.fail("precondition: the subscription published the message to the DLQ stream")

    if read == "dlq_list":
        assert len(broker.dlq_list([dlq_stream])) == 1
    else:
        assert broker.dlq_depth(dlq_stream) == 1


@pytest.mark.protean_bug(
    issue=None,
    state="open",
    bug=(
        "`RedisBroker.dlq_replay` strips `_dlq_metadata`, including the failing `consumer_group`, and appends the "
        "message to the source stream again. Every consumer group on the stream reads it as new, including groups that"
        " already handled it. Replaying a payments failure on the shared `ordering::order` stream would deliver the "
        "order event again to every other context subscribed to it: fulfillment, inventory, loyalty, notifications and"
        " reviews. `dlq_purge` takes no consumer group and deletes the whole `{stream}:dlq` key, so it would also "
        "clear every other group's dead letters on that stream; that part was read in the code "
        "(`RedisBroker._dlq_purge`), not run or pinned."
    ),
)
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="dlq_replay appends the message to the source stream, so every consumer group reads it again",
)
@pytest.mark.usefixtures("payments_ctx")
def test_dlq_replay_reaches_only_the_failing_consumer_group():
    """Protean finding (not filed yet): replaying a dead letter redelivers it to every consumer group.

    A `BrokerSubscription` dead-letters to `{stream}:dlq` and records its own
    group in `_dlq_metadata.consumer_group`. `RedisBroker.dlq_replay` strips
    that metadata and appends the message to the source stream again, so every
    group on the stream reads it as a new message, including groups that
    already handled it. On the shared bus, replaying a payments failure on
    `ordering::order` would deliver the order event again to every other
    context subscribed to it: fulfillment, inventory, loyalty, notifications
    and reviews.
    """
    import asyncio

    import redis
    from protean import current_domain
    from protean.server.engine import Engine
    from protean.server.subscription.broker_subscription import BrokerSubscription

    from payments.payment.ordering_subscriber import OrderReturnedSubscriber

    broker = current_domain.brokers["global"]
    client = getattr(broker, "redis_instance", None)
    if client is None:
        pytest.skip("needs the Redis streams broker (run with --protean-env test)")
    try:
        client.ping()
    except redis.exceptions.ConnectionError:
        pytest.skip("the global broker's Redis is not reachable")
    broker._data_reset()

    stream = "ordering::order"
    dlq_stream = f"{stream}:dlq"
    other_group = "fulfillment.order_subscriber"
    subscription = BrokerSubscription(
        Engine(current_domain, test_mode=True),
        broker,
        stream,
        OrderReturnedSubscriber,
        max_retries=1,
        retry_delay_seconds=0,
        enable_dlq=True,
    )
    payload = {
        "data": {"reason": "damaged"},
        "metadata": {"headers": {"id": "replay-probe-1", "type": "Ordering.OrderReturned.v1"}},
    }
    # `_publish` stores the message without calling the subscribers inline, like the outbox processor.
    original_id = broker._publish(stream, payload)
    client.xgroup_create(stream, other_group, id="0")
    client.xreadgroup(other_group, "c1", {stream: ">"}, count=10)
    client.xack(stream, other_group, original_id)

    if asyncio.run(_deliver(subscription, 1)) != 1:
        pytest.fail("precondition: the subscription received the message")
    dead = broker.dlq_list([dlq_stream])
    if len(dead) != 1:
        pytest.fail("precondition: the subscription dead-lettered the message")

    if not broker.dlq_replay(dlq_stream, dead[0].dlq_id, target_stream=stream):
        pytest.fail("precondition: dlq_replay reported success")
    # A replay that the failing group never sees would leave the other group nothing to read and XPASS.
    if asyncio.run(_deliver(subscription, 1)) != 1:
        pytest.fail("precondition: the failing subscription received the replay")

    replayed_to_other = client.xreadgroup(other_group, "c1", {stream: ">"}, count=10)
    assert replayed_to_other == [], "a group that already handled the message received the replay"


@pytest.mark.protean_bug(
    issue=1923,
    state="guard",
    bug=(
        "Protean's default config always defines a `memory` database provider, and the engine ran an outbox "
        "processor for every managed provider. Each ShopStream engine therefore ran `memory-to-<broker>` outbox "
        "processors for a database it never configured, and they showed as rows in `/readyz` and `protean "
        "subscriptions status`. Fixed in proteanhq/protean#1924 (`3109190`)."
    ),
)
def test_1923_engine_runs_outbox_processors_only_for_configured_databases(ordering_bed):
    """proteanhq/protean#1923 (guard): engines run outbox processors only for configured databases.

    Protean's default config always defines a `memory` database provider. The
    engine used to create an outbox processor per managed provider, so Ordering's
    engine also ran `memory-to-default` and `memory-to-global-external`, which
    polled an outbox nothing writes to and showed as rows in /readyz and
    `protean subscriptions status`. Ordering's domain.toml configures only
    `default`, so only its two processors may run.
    """
    from protean.server.engine import Engine

    with ordering_bed.domain_context():
        engine = Engine(ordering_bed.domain, test_mode=True)
        try:
            processors = sorted(engine._outbox_processors)
        finally:
            engine.loop.close()

    assert processors == [
        "outbox-processor-default-to-default",
        "outbox-processor-default-to-global-external",
    ]


def _restart_after_a_batch(shutting_down: bool) -> tuple[int, int, int]:
    """Read a batch, process it with the engine shutting down or not, then let a restarted consumer catch up.

    Returns `(handled, pending, dead_lettered)` for the three messages. Protean's own
    asserts inside the subscription fail the test outright, so the pin's xfail
    stays tied to its one assertion.
    """
    import asyncio
    import uuid

    from protean import current_domain
    from protean.server.engine import Engine
    from protean.server.subscription.stream_subscription import StreamSubscription
    from protean.utils.eventing import Message

    from inventory.projections.event_audit import EventAudit, EventAuditHandler
    from inventory.stock.stock import InventoryItem

    broker = current_domain.brokers["default"]
    client = broker.redis_instance
    stream = f"regression::sigterm-{uuid.uuid4().hex[:8]}"
    engines = []

    def subscription(consumer: str | None = None) -> StreamSubscription:
        engines.append(Engine(current_domain, test_mode=True))
        sub = StreamSubscription(engines[-1], stream, EventAuditHandler, blocking_timeout_ms=50, retry_delay_seconds=0)
        if consumer:
            # A restart on another host or pod: nothing in the name matches the stopped consumer.
            sub.consumer_name = sub.subscription_id = consumer
        return sub

    try:
        stopping = subscription()
        asyncio.run(stopping.initialize())
        ids = []
        for n in range(3):
            item = InventoryItem.create(f"p{n}", f"v{n}", "w", f"SIGTERM-{n}")
            ids.append(str(item.id))
            broker.publish(stream, Message.from_domain_object(item._events[0]).to_dict())
        batch = asyncio.run(stopping.get_next_batch_of_messages())
        if len(batch) != 3:
            pytest.fail(f"precondition: one read handed the subscription all 3 messages, got {len(batch)}")

        # What SIGTERM does first: Engine.shutdown() sets this flag, which Engine.handle_message reads, then
        # waits for the batch in hand.
        stopping.engine.shutting_down = shutting_down
        try:
            asyncio.run(stopping.process_batch(batch))
        except AssertionError as exc:
            pytest.fail(f"Protean asserted while processing the batch: {exc}")

        # Age what the stopped consumer left, so a fix that claims idle entries at startup has something to claim.
        left = [entry["message_id"] for entry in client.xpending_range(stream, stopping.consumer_group, "-", "+", 10)]
        if left:
            client.xclaim(stream, stopping.consumer_group, stopping.consumer_name, 0, left, idle=3_600_000)

        restarted = subscription(f"EventAuditHandler-restarted-host-1-{uuid.uuid4().hex[:6]}")
        asyncio.run(restarted.initialize())
        asyncio.run(_deliver(restarted, 3))

        audits = current_domain.repository_for(EventAudit)._dao.query.filter(inventory_item_id__in=ids).all()
        pending = client.xpending(stream, stopping.consumer_group)["pending"]
        dead = client.xlen(stopping.dlq_stream)
        return audits.total, pending, dead
    finally:
        client.delete(stream, f"{stream}:dlq", f"{stream}:backfill", f"{stream}:backfill:dlq")
        for engine in engines:
            engine.loop.close()


@pytest.mark.protean_bug(
    issue=1929,
    state="open",
    bug=(
        "On SIGTERM, `Engine.shutdown()` sets `shutting_down` and `Engine.handle_message` then returns False, so "
        "`StreamSubscription.process_batch` marks every message left in its batch as failed without running it. They "
        "stay pending under the stopped process's consumer name, which no later process reads, and the multi-group "
        "trim then deletes them. Draining with `POST /drainz` and waiting for the batch to finish before SIGTERM "
        "avoids it for messages that do not fail."
    ),
)
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="SIGTERM leaves the rest of an in-flight batch pending, and no restarted consumer handles it",
)
@pytest.mark.usefixtures("inventory_ctx")
def test_1929_sigterm_does_not_strand_the_rest_of_an_in_flight_batch():
    """proteanhq/protean#1929: messages in hand at SIGTERM are never handled.

    The subscription reads three messages, then the engine starts shutting down
    before it handles them. A subscription with an unrelated consumer name,
    standing in for an engine restarted on another host, then catches up, an hour
    after the stopped consumer last touched the messages. Each message should be
    handled once by one of the two, with nothing left pending and nothing
    dead-lettered. Today none is handled and all three stay pending in the group.
    The same steps without the shutdown handle all three, which the test checks
    first so it can only fail on the bug.
    """
    import redis
    from protean import current_domain

    client = getattr(current_domain.brokers["default"], "redis_instance", None)
    if client is None:
        pytest.skip("needs the Redis streams broker (run with --protean-env test)")
    try:
        client.ping()
    except redis.exceptions.ConnectionError:
        pytest.skip("the default broker's Redis is not reachable")

    if _restart_after_a_batch(shutting_down=False) != (3, 0, 0):
        pytest.fail("precondition: without a shutdown all three are handled and acknowledged")

    assert _restart_after_a_batch(shutting_down=True) == (3, 0, 0)
