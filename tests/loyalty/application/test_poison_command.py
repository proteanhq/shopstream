"""Application test for the EmitPoison command handler.

Processing `EmitPoison` creates a `PoisonPill` and raises `PoisonDetonated`. Under synchronous
event processing the always-failing `PoisonEventHandler` runs inline, so the call fails fast —
which also covers the command handler's happy path before the dispatch. (The asynchronous
retry → DLQ → replay path is exercised by the engine-driven `tests/loyalty/integration/test_dlq.py`.)
"""

import pytest
from protean import current_domain

from loyalty.dlq.poison import EmitPoison


class TestEmitPoison:
    def test_emitting_poison_triggers_the_failing_handler(self):
        with pytest.raises(Exception, match="poison pill detonated"):
            current_domain.process(EmitPoison(note="unit-test"), asynchronous=False)
