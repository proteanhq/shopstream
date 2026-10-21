"""The broker subscription is the only layer that retries and dead-letters an ordering message.

Protean's ADR-0042 makes a `BrokerSubscription` the single owner of retries and dead-lettering for
the stream it consumes. Its constructor marks its consumer group as owned on the broker. From then
on the InlineBroker holds and redelivers every nack with no retry limit of its own, and the
subscription publishes an exhausted message to `{stream}:dlq`. On the InlineBroker the owned group
never reaches the broker's own (native) DLQ.

These tests feed `OrderReturnedSubscriber` an `OrderReturned` payload with no `order_id`, so it
raises `KeyError`, through the real subscription read and process path on the `global` broker.
They run on the InlineBroker (memory env) and on Redis (test env). The native-DLQ check applies
only to the InlineBroker, since Redis has no native DLQ.
"""

import asyncio
from collections.abc import Iterator
from typing import Any

import pytest
from protean import current_domain
from protean.adapters.broker.inline import InlineBroker
from protean.port.broker import BaseBroker
from protean.server.engine import Engine
from protean.server.subscription.broker_subscription import BrokerSubscription

from payments.payment.ordering_subscriber import OrderReturnedSubscriber

SOURCE_STREAM = "ordering::order"
DLQ_STREAM = f"{SOURCE_STREAM}:dlq"
OUTAGE_CYCLES = 3
SUBSCRIPTION_ATTEMPTS = 3


@pytest.fixture()
def broker(monkeypatch: pytest.MonkeyPatch) -> Iterator[BaseBroker]:
    """The payments `global` broker, emptied first, with a fast, low InlineBroker retry limit.

    The per-test domain fixture resets the broker again afterwards, which deletes the source
    stream, the DLQ stream and the consumer group on Redis.
    """
    broker = current_domain.brokers["global"]
    broker._data_reset()
    if isinstance(broker, InlineBroker):
        # A nacked message waits `_retry_delay` seconds before the next read can redeliver it.
        monkeypatch.setattr(broker, "_retry_delay", 0)
        # Below OUTAGE_CYCLES and SUBSCRIPTION_ATTEMPTS, so a group the broker did not treat as
        # owned would reach the native DLQ first and the test would catch it.
        monkeypatch.setattr(broker, "_max_retries", 1)
    yield broker


def _subscription(broker: BaseBroker, max_retries: int = 1) -> BrokerSubscription:
    return BrokerSubscription(
        Engine(current_domain, test_mode=True),
        broker,
        SOURCE_STREAM,
        OrderReturnedSubscriber,
        max_retries=max_retries,
        retry_delay_seconds=0,
        enable_dlq=True,
    )


def _publish_bad_order_returned(broker: BaseBroker) -> str:
    """Put an `OrderReturned` payload with no `order_id` on the stream; return its broker id.

    `broker.publish` would also call every payments subscriber on the stream inline under sync
    message processing, and `OrderReturnedSubscriber` would raise right there. `_publish` only
    stores the message, which is what the outbox processor does in production.
    """
    payload = {
        "data": {"reason": "damaged"},
        "metadata": {"headers": {"id": "bad-return-1", "type": "Ordering.OrderReturned.v1"}},
    }
    return broker._publish(SOURCE_STREAM, payload)


async def _deliver(sub: BrokerSubscription, cycles: int) -> int:
    """Run read-then-process cycles and return how many messages were delivered."""
    delivered = 0
    for _ in range(cycles):
        batch = await sub.get_next_batch_of_messages()
        delivered += len(batch)
        if batch:
            await sub.process_batch(batch)
    return delivered


def _dlq_entries(broker: BaseBroker) -> list[dict[str, Any]]:
    """Read every entry on the DLQ stream itself, without the broker's DLQ API."""
    if isinstance(broker, InlineBroker):
        return [payload for _, payload in broker._messages.get(DLQ_STREAM, [])]
    return [broker._deserialize_message(fields) for _, fields in broker._client.xrange(DLQ_STREAM)]


def _assert_native_dlq_empty(broker: BaseBroker) -> None:
    # Redis has no native DLQ: `{stream}:dlq` is the only one it has. Every group key is read,
    # so a message filed under an unexpected key still fails the check.
    if isinstance(broker, InlineBroker):
        assert {key: entries for key, entries in broker._dead_letter_queue.items() if entries} == {}


def _held_ids(broker: BaseBroker, sub: BrokerSubscription) -> set[str]:
    """The broker ids the broker still holds for the group: failed, in flight, or pending."""
    group = sub.subscriber_name
    if isinstance(broker, InlineBroker):
        group_key = f"{SOURCE_STREAM}:{group}"
        failed = {entry[0] for entry in broker._failed_messages[group_key]}
        return failed | set(broker._in_flight[group_key])
    pending = broker._client.xpending_range(SOURCE_STREAM, group, min="-", max="+", count=10)
    return {broker._decode_if_bytes(entry["message_id"]) for entry in pending}


def _assert_single_dlq_entry(broker: BaseBroker, sub: BrokerSubscription, broker_id: str) -> None:
    entries = _dlq_entries(broker)
    assert len(entries) == 1
    assert entries[0]["metadata"]["headers"]["id"] == "bad-return-1"
    assert entries[0]["_dlq_metadata"]["original_stream"] == SOURCE_STREAM
    assert entries[0]["_dlq_metadata"]["original_id"] == broker_id
    assert entries[0]["_dlq_metadata"]["consumer_group"] == sub.subscriber_name


class TestBrokerSubscriptionOwnsTheDLQ:
    def test_exhausted_message_lands_only_in_the_stream_dlq(self, broker):
        sub = _subscription(broker, max_retries=SUBSCRIPTION_ATTEMPTS)
        broker_id = _publish_bad_order_returned(broker)

        # Each failure before the last is nacked, and the broker redelivers it on the next read.
        assert asyncio.run(_deliver(sub, SUBSCRIPTION_ATTEMPTS - 1)) == SUBSCRIPTION_ATTEMPTS - 1
        assert _dlq_entries(broker) == []
        assert list(sub.retry_counts) == [broker_id]
        _assert_native_dlq_empty(broker)

        assert asyncio.run(_deliver(sub, 1)) == 1

        _assert_single_dlq_entry(broker, sub, broker_id)
        _assert_native_dlq_empty(broker)
        assert sub.retry_counts == {}
        assert _held_ids(broker, sub) == set()
        assert asyncio.run(_deliver(sub, 2)) == 0

    def test_dlq_outage_holds_the_message_then_lands_it_once(self, broker, monkeypatch):
        sub = _subscription(broker)
        broker_id = _publish_bad_order_returned(broker)

        real_publish = broker.publish

        def publish_with_dlq_down(stream: str, message: dict[str, Any]) -> str | None:
            if stream == DLQ_STREAM:
                raise RuntimeError("DLQ down")
            return real_publish(stream, message)

        monkeypatch.setattr(broker, "publish", publish_with_dlq_down)

        assert asyncio.run(_deliver(sub, OUTAGE_CYCLES)) == OUTAGE_CYCLES
        assert _dlq_entries(broker) == []
        assert _held_ids(broker, sub) == {broker_id}
        _assert_native_dlq_empty(broker)
        assert list(sub.retry_counts) == [broker_id]

        monkeypatch.setattr(broker, "publish", real_publish)
        assert asyncio.run(_deliver(sub, 1)) == 1

        _assert_single_dlq_entry(broker, sub, broker_id)
        _assert_native_dlq_empty(broker)
        assert sub.retry_counts == {}
        assert _held_ids(broker, sub) == set()
        assert asyncio.run(_deliver(sub, 2)) == 0
