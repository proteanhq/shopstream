"""A deliberately-failing event handler used to exercise the Dead Letter Queue (DLQ).

`PoisonPill` is a tiny aggregate whose only purpose is to emit an event that an event handler
*always* fails to process. Under asynchronous event processing the engine delivers the event,
the handler raises, and after the configured retries are exhausted the engine routes the message
to the stream's `:dlq` — where it can be inspected and replayed (see
`tests/loyalty/integration/test_dlq.py`). This is the only intentionally-failing handler in
ShopStream; it isolates the DLQ demo from real loyalty flows on its own
``loyalty::poison_pill`` stream.
"""

from datetime import UTC, datetime

from protean.fields import DateTime, Identifier, String
from protean.utils.globals import current_domain
from protean.utils.mixins import handle

from loyalty.domain import loyalty


@loyalty.event(part_of="PoisonPill")
class PoisonDetonated:
    poison_id = Identifier(required=True)
    note = String()
    occurred_at = DateTime(required=True)


@loyalty.aggregate
class PoisonPill:
    note = String(max_length=120, default="intentional DLQ demo failure")

    @classmethod
    def detonate(cls, note=None):
        pill = cls(note=note or "intentional DLQ demo failure")
        pill.raise_(PoisonDetonated(poison_id=pill.id, note=pill.note, occurred_at=datetime.now(UTC)))
        return pill


@loyalty.command(part_of="PoisonPill")
class EmitPoison:
    note = String(max_length=120, default="intentional DLQ demo failure")


@loyalty.command_handler(part_of="PoisonPill")
class EmitPoisonHandler:
    @handle(EmitPoison)
    def emit(self, command: EmitPoison):
        pill = PoisonPill.detonate(command.note)
        current_domain.repository_for(PoisonPill).add(pill)
        return pill.id


@loyalty.event_handler(part_of=PoisonPill)
class PoisonEventHandler:
    """Always fails — every delivery raises, so the message exhausts its retries and is DLQ'd."""

    @handle(PoisonDetonated)
    def always_fail(self, event: PoisonDetonated):
        raise RuntimeError(f"poison pill detonated: {event.note}")
