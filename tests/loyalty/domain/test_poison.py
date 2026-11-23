"""Domain tests for the DLQ poison-pill elements (the intentional-failure fixtures)."""

from datetime import UTC, datetime

import pytest

from loyalty.dlq.poison import (
    PoisonDetonated,
    PoisonEventHandler,
    PoisonEventStoreHandler,
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


class TestPoisonEventStoreHandler:
    @pytest.fixture(autouse=True)
    def _reset(self):
        PoisonEventStoreHandler.heal = False
        PoisonEventStoreHandler.seen = []
        yield
        PoisonEventStoreHandler.heal = False
        PoisonEventStoreHandler.seen = []

    def _event(self) -> PoisonDetonated:
        return PoisonDetonated(poison_id="p1", note="boom", occurred_at=datetime.now(UTC))

    def test_fails_and_records_the_call_until_healed(self):
        with pytest.raises(RuntimeError, match="poison pill detonated: boom"):
            PoisonEventStoreHandler().fail_until_healed(self._event())
        assert PoisonEventStoreHandler.seen == ["boom"]

    def test_succeeds_and_records_the_call_once_healed(self):
        PoisonEventStoreHandler.heal = True
        PoisonEventStoreHandler().fail_until_healed(self._event())
        assert PoisonEventStoreHandler.seen == ["boom"]
