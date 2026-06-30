"""Domain tests for the DLQ poison-pill elements (the intentional-failure fixtures)."""

from datetime import UTC, datetime

import pytest

from loyalty.dlq.poison import (
    PoisonDetonated,
    PoisonEventHandler,
    PoisonPill,
)


class TestPoisonPill:
    def test_detonate_raises_event(self):
        pill = PoisonPill.detonate("boom")
        assert pill.note == "boom"
        assert isinstance(pill._events[-1], PoisonDetonated)
        assert pill._events[-1].note == "boom"

    def test_handler_always_fails(self):
        event = PoisonDetonated(poison_id="p1", note="boom", occurred_at=datetime.now(UTC))
        with pytest.raises(RuntimeError, match="poison pill detonated"):
            PoisonEventHandler().always_fail(event)
