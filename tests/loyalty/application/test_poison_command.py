"""Application test for the EmitPoison command handler.

Processing `EmitPoison` creates a `PoisonPill` and raises `PoisonDetonated`. Under synchronous
event processing the failing `PoisonEventHandler` and `PoisonEventStoreHandler` both run inline,
and the call fails fast. The test also covers the command handler's happy path before the
dispatch. The engine-driven `tests/loyalty/integration/test_dlq.py` exercises the asynchronous
retry → DLQ → replay path.
"""

import pytest
from protean import current_domain

from loyalty.dlq.poison import EmitPoison


class TestEmitPoison:
    def test_emitting_poison_triggers_the_failing_handler(self):
        with pytest.raises(Exception, match="poison pill detonated"):
            current_domain.process(EmitPoison(note="unit-test"), asynchronous=False)
