"""The NotificationDispatcher subscription's circuit breaker, on the real Redis broker.

A channel outage makes the dispatcher raise ``ChannelUnavailableError`` on every message. After
``circuit_breaker_threshold`` consecutive handler failures the breaker opens and the subscription
stops reading. Once ``circuit_breaker_reset_seconds`` has passed it lets one probe message through.
A successful probe closes the breaker. A failed probe opens it again, and each failure counts
towards the message's ``max_retries``: when the oldest message has failed that many times, Protean
moves it to the dead-letter queue and acknowledges it.

The test builds the engine's own subscription (so it carries the config Protean resolved from
``domain.toml``) but does not run the engine. It drives one poll turn at a time through
``_read_primary_nonblocking``, the read the poll loop uses first when priority lanes are on (as
they are for notifications), and ``process_batch``. Protean has no public way to run a single
poll turn and no clock to inject, so the test also calls ``_circuit_permits_reads`` and
``_current_batch_size``, and moves ``circuit_opened_at`` back instead of waiting out the window.

The subscription reads through a scratch consumer group created at the end of the stream, so a
dev engine reading the dispatcher's real group cannot take the test's messages.

Skips under the in-memory broker; run with ``--protean-env test``.
"""

import uuid

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
        _skip_unless_redis_streams()
        engine.loop.run_until_complete(_with_scratch_group(dispatcher_subscription, self._good_probe))

    def test_failed_probes_reopen_the_breaker_until_the_message_is_dead_lettered(self, engine, dispatcher_subscription):
        _skip_unless_redis_streams()
        engine.loop.run_until_complete(_with_scratch_group(dispatcher_subscription, self._failed_probes))

    @staticmethod
    async def _good_probe(sub: StreamSubscription, published: list[str]) -> None:
        client = sub.broker.redis_instance
        dlq_length_before = client.xlen(sub.dlq_stream)
        failed_ids = await _fail_until_open(sub, published)

        # Every failed message is still pending, none was dead-lettered.
        assert set(failed_ids) <= _pending_ids(sub)
        assert client.xlen(sub.dlq_stream) == dlq_length_before

        # The probe is the oldest failed message, redelivered. The channel is back, so it
        # succeeds and closes the breaker.
        await _reach_half_open(sub)
        get_channel(NotificationChannel.EMAIL.value).set_outage(False)
        probe = await sub._read_primary_nonblocking()
        assert [identifier for identifier, _ in probe] == failed_ids[:1]
        await sub.process_batch(probe)

        assert sub.circuit_state == CircuitBreakerState.CLOSED
        assert sub.consecutive_handler_failures == 0

        pending = _pending_ids(sub)
        assert failed_ids[0] not in pending
        assert set(failed_ids[1:]) <= pending
        assert client.xlen(sub.dlq_stream) == dlq_length_before

    @staticmethod
    async def _failed_probes(sub: StreamSubscription, published: list[str]) -> None:
        client = sub.broker.redis_instance
        dlq_length_before = client.xlen(sub.dlq_stream)
        failed_ids = await _fail_until_open(sub, published)
        oldest = failed_ids[0]
        assert sub.max_retries == 3  # the production profile's value

        # The first failure was the original delivery. The probes are the remaining attempts.
        for attempt in range(2, sub.max_retries + 1):
            await _reach_half_open(sub)
            probe = await sub._read_primary_nonblocking()
            assert [identifier for identifier, _ in probe] == [oldest]
            await sub.process_batch(probe)

            assert sub.circuit_state == CircuitBreakerState.OPEN
            if attempt < sub.max_retries:
                assert oldest in _pending_ids(sub)
                assert client.xlen(sub.dlq_stream) == dlq_length_before

        # Retries are spent: the oldest request is in the DLQ and no longer pending, so only a
        # DLQ replay sends it. The others are still pending behind it.
        pending = _pending_ids(sub)
        assert oldest not in pending
        assert set(failed_ids[1:]) <= pending
        assert client.xlen(sub.dlq_stream) == dlq_length_before + 1


def _skip_unless_redis_streams() -> None:
    if not _broker_is_redis_streams():
        pytest.skip("The breaker exercise needs the Redis streams broker (run with --protean-env test)")


def _pending_ids(sub: StreamSubscription) -> set[str]:
    entries = sub.broker.redis_instance.xpending_range(sub.stream_category, sub.consumer_group, "-", "+", 1000)
    return {entry["message_id"].decode() for entry in entries}


async def _with_scratch_group(sub: StreamSubscription, exercise) -> None:
    """Run ``exercise(sub, published)`` on a scratch consumer group, then remove the group and entries."""
    sub.retry_delay_seconds = 0  # the retry path sleeps this long before each NACK
    sub.consumer_group = f"breaker-test-{uuid.uuid4().hex[:8]}"
    client = notifications.brokers["default"].redis_instance
    # Created at "$" so the group reads only the entries this test publishes. `initialize` then
    # finds the group and leaves it as it is.
    client.xgroup_create(sub.stream_category, sub.consumer_group, id="$", mkstream=True)
    await sub.initialize()

    published: list[str] = []
    try:
        for _ in range(THRESHOLD):
            published.append(sub.broker.publish(sub.stream_category, _dispatch_request_message().to_dict()))
        await exercise(sub, published)
    finally:
        client.xgroup_destroy(sub.stream_category, sub.consumer_group)
        if published:
            client.xdel(sub.stream_category, *published)
        await sub.cleanup()


async def _fail_until_open(sub: StreamSubscription, published: list[str]) -> list[str]:
    """Fail the published messages under an email outage until the breaker opens; return their ids."""
    get_channel(NotificationChannel.EMAIL.value).set_outage(True)
    assert sub.circuit_state == CircuitBreakerState.CLOSED

    batch = await sub._read_primary_nonblocking()
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
    return failed_ids


async def _reach_half_open(sub: StreamSubscription) -> None:
    """Move the opening time back by the reset window, then let the poll-loop check run."""
    assert sub.circuit_opened_at is not None
    sub.circuit_opened_at -= RESET_SECONDS
    assert await sub._circuit_permits_reads() is True
    assert sub.circuit_state == CircuitBreakerState.HALF_OPEN
    assert sub._current_batch_size() == 1
