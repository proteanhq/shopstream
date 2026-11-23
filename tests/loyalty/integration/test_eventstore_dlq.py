"""Event-store DLQ: `protean eventstore dlq list|inspect|replay|purge` on a loyalty handler.

`PoisonEventStoreHandler` reads `loyalty::poison_pill` from the event store and fails until
`heal` is set. Each test emits its own `PoisonDetonated` with a unique note, then drives one
`EventStoreSubscription` by hand, with the calls the engine makes: deliver the event, then run
recovery passes until the subscription records its global position as `Exhausted` in its
`failed-*` stream. The CLI commands then read and act on that record, with `load_domain` patched
to return the loyalty domain this suite already set up.

The suite's fixture empties the event store after every test. Within one test there can be more
than one poison event, so each test filters to its own position, and the handler's `seen` list
is checked by note.

No engine run is needed, so this runs in CI under both the memory and the real stores.
"""

import asyncio
import json
import uuid
from unittest.mock import patch

import pytest
from protean import current_domain
from protean.cli import app
from protean.server import Engine
from protean.server.subscription.event_store_subscription import EventStoreSubscription
from protean.server.subscription_status import collect_subscription_statuses
from protean.utils import fqn
from protean.utils.dlq import failed_positions_stream
from protean.utils.eventing import Message
from typer.testing import CliRunner

from loyalty.dlq.poison import EmitPoison, PoisonEventStoreHandler
from loyalty.domain import loyalty

STREAM = "loyalty::poison_pill"
MAX_RETRIES = 1
WIDE = {"COLUMNS": "200"}  # keep rich from wrapping the replay confirmation line

runner = CliRunner()


@pytest.fixture(autouse=True)
def async_processing():
    """Process `EmitPoison` asynchronously, so no handler runs inline."""
    saved = loyalty.config.get("event_processing")
    loyalty.config["event_processing"] = "async"
    try:
        yield
    finally:
        loyalty.config["event_processing"] = saved


@pytest.fixture(autouse=True)
def poison_handler():
    PoisonEventStoreHandler.heal = False
    PoisonEventStoreHandler.seen = []
    try:
        yield PoisonEventStoreHandler
    finally:
        PoisonEventStoreHandler.heal = False
        PoisonEventStoreHandler.seen = []


def _subscription(engine: Engine) -> EventStoreSubscription:
    return EventStoreSubscription(
        engine,
        STREAM,
        PoisonEventStoreHandler,
        messages_per_tick=10,
        position_update_interval=1,
        max_retries=MAX_RETRIES,
        enable_recovery=True,
        recovery_interval_seconds=0,
        retry_delay_seconds=0,
    )


def _drive(work) -> None:
    """Run `work(subscription)` on a fresh subscription, closing the loop `Engine()` opens."""
    engine = Engine(loyalty, test_mode=True)
    try:
        asyncio.run(work(_subscription(engine)))
    finally:
        engine.loop.close()


def _emit() -> tuple[Message, int, str]:
    """Emit one poison event and return its stored message, global position and note."""
    note = f"es-dlq-{uuid.uuid4().hex[:12]}"
    pill_id = current_domain.process(EmitPoison(note=note), asynchronous=False)
    messages = loyalty.event_store.store.read(f"{STREAM}-{pill_id}")
    assert len(messages) == 1, f"expected the PoisonDetonated event in the store, got {messages}"
    message = messages[0]
    return message, message.metadata.event_store.global_position, note


def _deliver() -> int:
    """Emit one poison event, deliver it once, and return its global position."""
    message, position, _ = _emit()

    async def work(subscription: EventStoreSubscription) -> None:
        await subscription.process_batch([message])

    _drive(work)
    return position


def _exhaust() -> tuple[int, str]:
    """Emit one poison event and drive the subscription until its position is exhausted."""
    message, position, note = _emit()

    async def work(subscription: EventStoreSubscription) -> None:
        await subscription.process_batch([message])
        # One pass beyond max_retries takes the position terminal.
        for _ in range(MAX_RETRIES + 1):
            await subscription.run_recovery_pass()

    _drive(work)
    assert position in _listed_positions(), f"position {position} did not exhaust"
    return position, note


def _rebuild_and_recover() -> None:
    """Start a subscription the way the engine does at startup, then run one recovery pass."""

    async def work(subscription: EventStoreSubscription) -> None:
        await subscription.initialize()
        await subscription.run_recovery_pass()

    _drive(work)


def _stored_read_position() -> int:
    engine = Engine(loyalty, test_mode=True)
    try:
        return asyncio.run(_subscription(engine).fetch_last_position())
    finally:
        engine.loop.close()


def _cli(*args: str, input: str | None = None):
    with patch("protean.cli.eventstore.load_domain", return_value=loyalty):
        return runner.invoke(app, ["eventstore", "dlq", *args], env=WIDE, input=input)


def _json(result) -> dict:
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)["data"]


def _failed_records(position: int) -> list[str]:
    """The record types in the handler's `failed-*` stream for `position`, oldest first."""
    failed_stream = failed_positions_stream(fqn(PoisonEventStoreHandler), STREAM)
    return [
        m.metadata.headers.type
        for m in loyalty.event_store.store.read(failed_stream)
        if m.data.get("position") == position
    ]


def _listed_positions() -> list[int]:
    """The exhausted positions `dlq list` shows for `PoisonEventStoreHandler`."""
    subscriptions = _json(_cli("list", "--json"))["subscriptions"]
    return [
        position
        for sub in subscriptions
        if sub["handler"] == fqn(PoisonEventStoreHandler) and sub["stream_category"] == STREAM
        for position in sub["exhausted"]
    ]


def test_status_lists_the_handler_as_an_event_store_subscription():
    rows = [s for s in collect_subscription_statuses(loyalty) if s.handler_name == "PoisonEventStoreHandler"]
    assert len(rows) == 1, f"expected one PoisonEventStoreHandler row, got {rows}"
    assert rows[0].subscription_type == "event_store"
    assert rows[0].stream_category == STREAM


def test_list_shows_the_exhausted_position():
    position, _ = _exhaust()

    subscriptions = _json(_cli("list", "--json"))["subscriptions"]

    owners = [sub for sub in subscriptions if position in sub["exhausted"]]
    assert len(owners) == 1, f"position {position} not listed exactly once: {subscriptions}"
    assert owners[0]["handler"] == fqn(PoisonEventStoreHandler)
    assert owners[0]["stream_category"] == STREAM


def test_inspect_rereads_the_failing_event():
    position, note = _exhaust()

    data = _json(_cli("inspect", str(position), "--json"))

    assert "PoisonDetonated" in data["type"]
    assert data["global_position"] == position
    assert data["data"]["note"] == note


def test_replay_refused_at_the_prompt_leaves_the_position_exhausted(poison_handler):
    position, note = _exhaust()

    result = _cli("replay", str(position), input="n\n")

    assert result.exit_code == 1, result.output
    assert "targets an event handler" in result.output
    assert "side effects a second time" in result.output
    assert "Aborted" in result.output
    assert position in _listed_positions()
    # Two calls while exhausting it (the delivery and one retry), none from the refused replay.
    assert poison_handler.seen.count(note) == 2


def test_replay_that_fails_again_reopens_the_position(poison_handler):
    position, note = _exhaust()

    result = _cli("replay", str(position), "--yes")

    assert result.exit_code == 1, result.output
    assert "reopened" in result.output
    assert poison_handler.seen.count(note) == 3
    assert position not in _listed_positions()

    # A restarted subscription rebuilds its failed positions from the failed stream and retries
    # the reopened one, so the reopen survives the rebuild.
    _rebuild_and_recover()
    assert poison_handler.seen.count(note) == 4

    # The retry budget runs out again on the next pass.
    _rebuild_and_recover()
    assert position in _listed_positions()


def test_replay_after_the_fault_is_fixed_resolves_the_position(poison_handler):
    position, note = _exhaust()
    poison_handler.heal = True
    # Move the read cursor past the exhausted position, so a replay that wrote the cursor to the
    # replayed position would show as a change.
    read_position = _deliver()
    assert _stored_read_position() == read_position > position

    result = _cli("replay", str(position), "--yes")

    assert result.exit_code == 0, result.output
    assert "resolved" in result.output
    assert poison_handler.seen.count(note) == 3
    assert position not in _listed_positions()
    assert _failed_records(position)[-1] == "Resolved"
    # Replay re-reads the event from its own stream; it never moves the read cursor.
    assert _stored_read_position() == read_position

    # A restarted subscription does not retry a resolved position.
    _rebuild_and_recover()
    assert poison_handler.seen.count(note) == 3
    assert position not in _listed_positions()


def test_purge_clears_the_position_without_running_the_handler(poison_handler):
    _exhaust()  # a second exhausted position, so purge must pick the one it was given
    position, note = _exhaust()

    result = _cli("purge", str(position), "--yes")

    assert result.exit_code == 0, result.output
    assert position not in _listed_positions()
    assert _failed_records(position)[-2:] == ["Exhausted", "Purged"]

    # A purged position can no longer be replayed, so the handler does not run again.
    replay = _cli("replay", str(position), "--yes")
    assert replay.exit_code != 0, replay.output
    assert f"No exhausted position {position} found" in replay.output
    assert poison_handler.seen.count(note) == 2

    # A rebuild drops an exhausted position as it drops a purged one, so this check cannot tell
    # the two apart. It guards only against a `Purged` record putting the position back.
    _rebuild_and_recover()
    assert poison_handler.seen.count(note) == 2
