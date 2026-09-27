from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their directory location."""
    for item in items:
        test_path = Path(item.fspath)

        if "/domain/" in str(test_path):
            item.add_marker(pytest.mark.domain)
        elif "/application/" in str(test_path):
            item.add_marker(pytest.mark.application)
        elif "/integration/" in str(test_path):
            item.add_marker(pytest.mark.integration)
            if not any(m.name == "fast" for m in item.iter_markers()):
                item.add_marker(pytest.mark.slow)

        if "/bdd/" in str(test_path):
            item.add_marker(pytest.mark.bdd)


class FrozenClock:
    """A stub domain clock whose `now()` returns a fixed, settable UTC time."""

    def __init__(self, at: datetime):
        if at.tzinfo is None:
            raise ValueError("FrozenClock needs a timezone-aware datetime")
        self._now = at.astimezone(UTC)

    def now(self) -> datetime:
        return self._now

    def set(self, at: datetime) -> None:
        self._now = at.astimezone(UTC)

    def advance(self, delta: timedelta) -> None:
        self._now += delta


@pytest.fixture()
def frozen_clock():
    """Return `freeze(domain, at)`, which installs a `FrozenClock` on `domain`.

    Each domain is set up once per session, so a stub left behind would freeze time
    for every later test. Teardown puts back the clock each domain had before.
    """
    originals = {}

    def freeze(domain, at: datetime) -> FrozenClock:
        originals.setdefault(domain, domain.clock)
        clock = FrozenClock(at)
        domain.clock = clock
        return clock

    yield freeze

    for domain, original in originals.items():
        domain.clock = original
