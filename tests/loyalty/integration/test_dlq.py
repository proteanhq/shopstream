"""Dead Letter Queue integration test — drives the real Protean engine.

This is ShopStream's first engine-driven integration test. It exercises Protean's
retry → DLQ → replay pipeline end to end:

  1. Emit a `PoisonDetonated` event whose handler (`PoisonEventHandler`) always raises.
  2. Run the engine (`Engine(test_mode=True)`), which delivers the event, retries the
     failing handler, and — once retries are exhausted — routes the message to the
     stream's `:dlq`.
  3. Assert the message is in the DLQ, then **replay** it back onto the source stream.

Requires asynchronous event processing (so the engine, not the inline path, handles the
event) and the **Redis** streams broker (the subscription-routed DLQ and the `broker.dlq_*`
inspection API only line up on Redis). It is therefore skipped under the in-memory broker —
run it with `--protean-env test` (the Postgres/Redis job).
"""

import pytest
import redis
from protean import current_domain
from protean.server.engine import Engine

from loyalty.dlq.poison import EmitPoison
from loyalty.domain import loyalty

DLQ_STREAM = "loyalty::poison_pill:dlq"
SOURCE_STREAM = "loyalty::poison_pill"


def _broker_is_redis_streams() -> bool:
    provider = loyalty.config.get("brokers", {}).get("default", {}).get("provider", "")
    return "redis" in provider and "pubsub" not in provider


@pytest.fixture()
def async_dlq_config():
    """Flip loyalty to async event processing + fast-fail retries for the duration of the test.

    Restored afterwards so the rest of the (synchronous) suite is unaffected.
    """
    cfg = loyalty.config
    saved_event_processing = cfg.get("event_processing")
    server = cfg["server"]
    saved_stream_sub = dict(server.get("stream_subscription") or {})

    cfg["event_processing"] = "async"
    stream_sub = server.setdefault("stream_subscription", {})
    stream_sub["max_retries"] = 1  # DLQ after a single failed attempt
    stream_sub["retry_delay_seconds"] = 0  # no real sleeps — stay within the engine's test budget
    stream_sub["enable_dlq"] = True

    yield

    cfg["event_processing"] = saved_event_processing
    server["stream_subscription"] = saved_stream_sub


@pytest.mark.slow
class TestDeadLetterQueue:
    def test_failing_handler_routes_to_dlq_then_replays(self, async_dlq_config):
        if not _broker_is_redis_streams():
            pytest.skip("DLQ exercise requires the Redis streams broker (run with --protean-env test)")

        # Clean slate on the poison streams.
        broker = current_domain.brokers["default"]
        broker.dlq_purge(DLQ_STREAM)

        # 1. Emit the poison event (the command is synchronous; the event is async).
        current_domain.process(EmitPoison(note="dlq-integration-test"), asynchronous=False)

        # 2. Run the engine: deliver → fail → exhaust retries → route to DLQ.
        Engine(loyalty, test_mode=True).run()

        # The engine closes the shared Redis connection pool on shutdown; hand the broker a
        # fresh client so the inspection/replay calls below are deterministic.
        broker = loyalty.brokers["default"]
        broker.redis_instance = redis.Redis.from_url(broker.conn_info["URI"])

        # 3. Assert the message landed in the DLQ.
        assert broker.dlq_depth(DLQ_STREAM) == 1
        entries = broker.dlq_list([DLQ_STREAM])
        assert len(entries) == 1
        entry = entries[0]
        assert entry.stream == SOURCE_STREAM
        assert entry.retry_count >= 1

        # 4. Replay it back onto the source stream; the DLQ drains.
        assert broker.dlq_replay(DLQ_STREAM, entry.dlq_id, target_stream=entry.stream) is True
        assert broker.dlq_depth(DLQ_STREAM) == 0

        # Tidy up so a replayed message doesn't linger for the next test.
        broker.dlq_purge(DLQ_STREAM)
