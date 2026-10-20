"""The NotificationDispatcher subscription's circuit breaker, on the real Redis broker.

A channel outage makes the dispatcher raise ``ChannelUnavailableError`` on every message. After
``circuit_breaker_threshold`` consecutive handler failures the breaker opens and the subscription
stops reading. Once ``circuit_breaker_reset_seconds`` has passed it lets one probe message through,
and a successful probe closes it again. Failed messages are never acknowledged: they stay in the
consumer group's pending list for redelivery.

The test builds the engine's own subscription (so it carries the config Protean resolved from
``domain.toml``) but does not run the engine. It drives one poll turn at a time through
``get_next_batch_of_messages`` and ``process_batch``. Protean has no public way to run a single
poll turn, so the test also calls ``_circuit_permits_reads`` and ``_current_batch_size``, the two
steps of the poll loop that move the breaker from OPEN to HALF_OPEN and size the probe read.

Skips under the in-memory broker; run with ``--protean-env test``.
"""

import pytest
from protean.server import Engine
from protean.server.subscription.profiles import CircuitBreakerState
from protean.server.subscription.stream_subscription import StreamSubscription
from protean.utils.eventing import Message

from notifications.channel import get_channel, reset_channels
from notifications.domain import notifications
from notifications.notification.dispatch import NotificationDispatcher
from notifications.notification.events import NotificationDispatchRequested
from notifications.notification.notification import Notification, NotificationChannel, NotificationType

# The values set under [server.subscriptions.NotificationDispatcher] in domain.toml.
THRESHOLD = 5
RESET_SECONDS = 30


def _broker_is_redis_streams() -> bool:
    provider = notifications.config.get("brokers", {}).get("default", {}).get("provider", "")
    return "redis" in provider and "pubsub" not in provider


def _dispatch_request_message() -> Message:
    """Serialize a real NotificationDispatchRequested, raised by the aggregate, as a broker message."""
    notification = Notification.create(
        recipient_id="cust-breaker",
        notification_type=NotificationType.WELCOME.value,
        channel=NotificationChannel.EMAIL.value,
        body="Welcome!",
    )
    requested = [e for e in notification._events if isinstance(e, NotificationDispatchRequested)]
    assert len(requested) == 1
    return Message.from_domain_object(requested[0])


@pytest.fixture()
def engine():
    engine = Engine(notifications, test_mode=True)
    yield engine
    engine.loop.close()


@pytest.fixture()
def dispatcher_subscription(engine) -> StreamSubscription:
    matches = [sub for sub in engine.subscriptions.values() if sub.handler is NotificationDispatcher]
    assert len(matches) == 1
    return matches[0]


class TestDispatcherCircuitBreaker:
    def setup_method(self):
        reset_channels()

    def teardown_method(self):
        reset_channels()

    def test_dispatcher_subscription_uses_the_per_handler_breaker_values(self, dispatcher_subscription):
        """The engine builds the dispatcher's subscription with the overridden breaker values."""
        assert isinstance(dispatcher_subscription, StreamSubscription)
        assert dispatcher_subscription.circuit_breaker_threshold == THRESHOLD
        assert dispatcher_subscription.circuit_breaker_reset_seconds == RESET_SECONDS
        assert dispatcher_subscription.retention_maxlen == 50000

    def test_channel_outage_opens_the_breaker_and_a_good_probe_closes_it(self, engine, dispatcher_subscription):
        if not _broker_is_redis_streams():
            pytest.skip("The breaker exercise needs the Redis streams broker (run with --protean-env test)")

        engine.loop.run_until_complete(self._exercise(dispatcher_subscription))

    @staticmethod
    def _pending_ids(client, stream: str, group: str) -> set[str]:
        entries = client.xpending_range(stream, group, "-", "+", 1000)
        return {entry["message_id"].decode() for entry in entries}

    async def _exercise(self, sub: StreamSubscription) -> None:
        sub.retry_delay_seconds = 0  # the retry path sleeps this long before each NACK
        await sub.initialize()
        broker = sub.broker
        client = broker.redis_instance
        stream, group = sub.stream_category, sub.consumer_group
        dlq_length_before = client.xlen(sub.dlq_stream)

        published: list[str] = []
        try:
            for _ in range(THRESHOLD):
                published.append(broker.publish(stream, _dispatch_request_message().to_dict()))

            get_channel(NotificationChannel.EMAIL.value).set_outage(True)
            assert sub.circuit_state == CircuitBreakerState.CLOSED

            batch = await sub.get_next_batch_of_messages()
            failed_ids = [identifier for identifier, _ in batch]
            assert failed_ids == published

            # One failure short of the threshold, the breaker stays closed.
            await sub.process_batch(batch[: THRESHOLD - 1])
            assert sub.circuit_state == CircuitBreakerState.CLOSED
            assert sub.consecutive_handler_failures == THRESHOLD - 1

            await sub.process_batch(batch[THRESHOLD - 1 :])
            assert sub.circuit_state == CircuitBreakerState.OPEN

            # Inside the reset window, reads stay paused.
            assert await sub._circuit_permits_reads() is False
            assert sub.circuit_state == CircuitBreakerState.OPEN

            # Move the opening time back by the reset window instead of waiting it out.
            assert sub.circuit_opened_at is not None
            sub.circuit_opened_at -= RESET_SECONDS
            assert await sub._circuit_permits_reads() is True
            assert sub.circuit_state == CircuitBreakerState.HALF_OPEN
            assert sub._current_batch_size() == 1

            # Every failed message is still pending, none was dead-lettered.
            assert set(failed_ids) <= self._pending_ids(client, stream, group)
            assert client.xlen(sub.dlq_stream) == dlq_length_before

            # The probe is the oldest failed message, redelivered. The channel is back, so it
            # succeeds and closes the breaker.
            get_channel(NotificationChannel.EMAIL.value).set_outage(False)
            probe = await sub.get_next_batch_of_messages()
            assert [identifier for identifier, _ in probe] == failed_ids[:1]
            await sub.process_batch(probe)

            assert sub.circuit_state == CircuitBreakerState.CLOSED
            assert sub.consecutive_handler_failures == 0

            pending = self._pending_ids(client, stream, group)
            assert failed_ids[0] not in pending
            assert set(failed_ids[1:]) <= pending
            assert client.xlen(sub.dlq_stream) == dlq_length_before
        finally:
            # Remove only this test's entries: the stream and its consumer group also serve the
            # dev engine, which reads the same Redis database.
            if published:
                client.xack(stream, group, *published)
                client.xdel(stream, *published)
            await sub.cleanup()
