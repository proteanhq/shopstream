"""The subscription is the only layer that retries and dead-letters a loyalty event.

Protean's ADR-0042 makes a `StreamSubscription` the single owner of retries and dead-lettering
for the stream it consumes. When it initializes, it marks its consumer group as owned on the
broker. From then on the broker holds and redelivers every nack with no retry limit of its own,
and the subscription publishes an exhausted message to `{stream}:dlq`, the one dead-letter
destination. On the InlineBroker the owned group never reaches the broker's own (native) DLQ.

These tests drive `PoisonEventHandler`, which always raises, through the real subscription read
and process path (`get_next_batch_of_messages` then `process_batch`), without running the engine
loop. They run on both brokers:

- **Memory env (InlineBroker):** the adapter ADR-0042 changed. The native-DLQ check applies only
  here, since Redis has no native DLQ.
- **Test env (Redis):** the held message stays pending in the consumer group (`XPENDING`) while
  the DLQ is down.

Each test checks three things at the end: one entry on `loyalty::poison_pill:dlq`, an empty native
DLQ, and an empty `retry_counts`.
"""

import asyncio
from collections.abc import Iterator
from typing import Any

import pytest
from protean import current_domain
from protean.adapters.broker.inline import InlineBroker
from protean.port.broker import BaseBroker
from protean.server.engine import Engine
from protean.server.subscription.stream_subscription import StreamSubscription
from protean.utils.eventing import Message

from loyalty.dlq.poison import PoisonEventHandler, PoisonPill

SOURCE_STREAM = "loyalty::poison_pill"
DLQ_STREAM = f"{SOURCE_STREAM}:dlq"

# The outage case runs this many delivery cycles while the DLQ is down. Each one redelivers the
# held message and fails the DLQ publish again.
OUTAGE_CYCLES = 3


@pytest.fixture()
def broker(monkeypatch: pytest.MonkeyPatch) -> Iterator[BaseBroker]:
    """The loyalty default broker, emptied first, with a fast, low InlineBroker retry limit.

    The per-test domain fixture resets the broker again afterwards, which deletes the source
    stream, the DLQ stream and the consumer group on Redis.
    """
    broker = current_domain.brokers["default"]
    broker._data_reset()
    if isinstance(broker, InlineBroker):
        # A nacked message waits `_retry_delay` seconds before the next read can redeliver it.
        monkeypatch.setattr(broker, "_retry_delay", 0)
        # Below OUTAGE_CYCLES, so a group the broker did not treat as owned would reach the
        # native DLQ during the outage and the test would catch it.
        monkeypatch.setattr(broker, "_max_retries", 1)
    yield broker


def _subscription() -> StreamSubscription:
    return StreamSubscription(
        Engine(current_domain, test_mode=True),
        SOURCE_STREAM,
        PoisonEventHandler,
        blocking_timeout_ms=50,
        max_retries=1,
        retry_delay_seconds=0,
        enable_dlq=True,
    )


def _publish_poison(broker: BaseBroker) -> tuple[str, str]:
    """Publish one `PoisonDetonated` message; return its broker id and its message id."""
    pill = PoisonPill.detonate("dlq ownership test")
    message = Message.from_domain_object(pill._events[0]).to_dict()
    broker_id = broker.publish(SOURCE_STREAM, message)
    assert broker_id is not None
    return broker_id, message["metadata"]["headers"]["id"]


async def _deliver(sub: StreamSubscription, cycles: int) -> int:
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


def _assert_native_dlq_empty(broker: BaseBroker, sub: StreamSubscription) -> None:
    # Redis has no native DLQ: `{stream}:dlq` is the only one it has.
    if isinstance(broker, InlineBroker):
        native = broker.get_dlq_messages(sub.consumer_group, SOURCE_STREAM)
        assert [entry for entries in native.values() for entry in entries] == []


def _is_held(broker: BaseBroker, sub: StreamSubscription, broker_id: str) -> bool:
    """Whether the broker still holds the message for redelivery to the group."""
    if isinstance(broker, InlineBroker):
        group_key = f"{SOURCE_STREAM}:{sub.consumer_group}"
        return broker_id in [entry[0] for entry in broker._failed_messages[group_key]]
    pending = broker._client.xpending_range(SOURCE_STREAM, sub.consumer_group, min="-", max="+", count=10)
    return [broker._decode_if_bytes(entry["message_id"]) for entry in pending] == [broker_id]


def _assert_single_dlq_entry(broker: BaseBroker, broker_id: str, message_id: str) -> None:
    entries = _dlq_entries(broker)
    assert len(entries) == 1
    assert entries[0]["metadata"]["headers"]["id"] == message_id
    assert entries[0]["_dlq_metadata"]["original_stream"] == SOURCE_STREAM
    assert entries[0]["_dlq_metadata"]["original_id"] == broker_id


class TestStreamSubscriptionOwnsTheDLQ:
    def test_exhausted_message_lands_only_in_the_stream_dlq(self, broker):
        sub = _subscription()
        asyncio.run(sub.initialize())
        broker_id, message_id = _publish_poison(broker)

        assert asyncio.run(_deliver(sub, 1)) == 1

        _assert_single_dlq_entry(broker, broker_id, message_id)
        _assert_native_dlq_empty(broker, sub)
        assert sub.retry_counts == {}
        # The message was acked away, so nothing is held and nothing comes back.
        assert not _is_held(broker, sub, broker_id)
        assert asyncio.run(_deliver(sub, 2)) == 0

    def test_dlq_outage_holds_the_message_then_lands_it_once(self, broker, monkeypatch):
        sub = _subscription()
        asyncio.run(sub.initialize())
        broker_id, message_id = _publish_poison(broker)

        real_publish = broker.publish

        def publish_with_dlq_down(stream: str, message: dict[str, Any]) -> str | None:
            if stream == DLQ_STREAM:
                raise RuntimeError("DLQ down")
            return real_publish(stream, message)

        monkeypatch.setattr(broker, "publish", publish_with_dlq_down)

        # Each cycle redelivers the held message, so it is neither acked away nor dead-lettered
        # by the broker.
        assert asyncio.run(_deliver(sub, OUTAGE_CYCLES)) == OUTAGE_CYCLES
        assert _dlq_entries(broker) == []
        assert _is_held(broker, sub, broker_id)
        _assert_native_dlq_empty(broker, sub)
        assert list(sub.retry_counts) == [broker_id]

        monkeypatch.setattr(broker, "publish", real_publish)
        assert asyncio.run(_deliver(sub, 1)) == 1

        _assert_single_dlq_entry(broker, broker_id, message_id)
        _assert_native_dlq_empty(broker, sub)
        assert sub.retry_counts == {}
        assert not _is_held(broker, sub, broker_id)
        assert asyncio.run(_deliver(sub, 2)) == 0
