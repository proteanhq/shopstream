"""Deliberately-failing event handlers used to exercise both dead-letter queues.

`PoisonPill` is a tiny aggregate whose only purpose is to emit an event that its event handlers
fail to process. It isolates the DLQ demos from real loyalty flows on its own
``loyalty::poison_pill`` stream. Two handlers fail on it, one per DLQ:

- `PoisonEventHandler` reads the Redis stream. Under asynchronous event processing the engine
  delivers the event, the handler raises, and once the retries are exhausted the subscription
  moves the message to the stream's `:dlq`, where it can be inspected and replayed (see
  `tests/loyalty/integration/test_dlq.py`).
- `PoisonEventStoreHandler` reads the event store. When its recovery pass exhausts the retries,
  the subscription records the global position as `Exhausted` in its `failed-*` stream, which
  `protean eventstore dlq list|inspect|replay|purge` reads and acts on (see
  `tests/loyalty/integration/test_eventstore_dlq.py`). Setting `heal` lets a replay succeed.
"""

from datetime import UTC, datetime
from typing import ClassVar

from protean.fields import DateTime, Identifier, String
from protean.server.subscription.profiles import SubscriptionType
from protean.utils.globals import current_domain
from protean.utils.mixins import handle

from loyalty.domain import loyalty


@loyalty.event(part_of="PoisonPill")
class PoisonDetonated:
    poison_id: str = Identifier(required=True)
    note: str | None = String()
    occurred_at: datetime = DateTime(required=True)


@loyalty.aggregate
class PoisonPill:
    note: str = String(max_length=120, default="intentional DLQ demo failure")

    @classmethod
    def detonate(cls, note: str | None = None) -> "PoisonPill":
        pill = cls(note=note or "intentional DLQ demo failure")
        pill.raise_(PoisonDetonated(poison_id=pill.id, note=pill.note, occurred_at=datetime.now(UTC)))
        return pill


@loyalty.command(part_of="PoisonPill")
class EmitPoison:
    note: str = String(max_length=120, default="intentional DLQ demo failure")


@loyalty.command_handler(part_of="PoisonPill")
class EmitPoisonHandler:
    @handle(EmitPoison)
    def emit(self, command: EmitPoison) -> str:
        pill = PoisonPill.detonate(command.note)
        current_domain.repository_for(PoisonPill).add(pill)
        return pill.id


@loyalty.event_handler(part_of=PoisonPill)
class PoisonEventHandler:
    """Always fails — every delivery raises, so the message exhausts its retries and is DLQ'd."""

    @handle(PoisonDetonated)
    def always_fail(self, event: PoisonDetonated) -> None:
        raise RuntimeError(f"poison pill detonated: {event.note}")


# The enum, not the string "event_store": `protean ir` fails on a string here, though the
# resolver accepts it (a Protean bug pinned in verification/regression/).
@loyalty.event_handler(part_of=PoisonPill, subscription_type=SubscriptionType.EVENT_STORE)
class PoisonEventStoreHandler:
    """Fails until `heal` is set, so an event-store position exhausts and can then be replayed.

    `seen` records the note of every event it is called with, so a test can tell whether a
    recovery pass or a replay ran it for that test's event.
    """

    heal: ClassVar[bool] = False
    seen: ClassVar[list[str | None]] = []

    @handle(PoisonDetonated)
    def fail_until_healed(self, event: PoisonDetonated) -> None:
        type(self).seen.append(event.note)
        if not type(self).heal:
            raise RuntimeError(f"poison pill detonated: {event.note}")
