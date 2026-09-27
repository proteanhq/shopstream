from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

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


@contextmanager
def frozen_clocks() -> Iterator[Callable[[Any, datetime], FrozenClock]]:
    """Yield `freeze(domain, at)`, which installs a `FrozenClock` on `domain`.

    Each domain is set up once per session, so a stub left behind would freeze time
    for every later test. On exit, each domain gets back the clock it had before.
    """
    originals: dict[Any, Any] = {}

    def freeze(domain: Any, at: datetime) -> FrozenClock:
        originals.setdefault(domain, domain.clock)
        clock = FrozenClock(at)
        domain.clock = clock
        return clock

    try:
        yield freeze
    finally:
        for domain, original in originals.items():
            domain.clock = original


@pytest.fixture()
def frozen_clock():
    """Return `freeze(domain, at)`; the domains' own clocks come back on teardown."""
    with frozen_clocks() as freeze:
        yield freeze


def as_utc(value: datetime) -> datetime:
    """Return `value` as an aware UTC datetime.

    The Postgres adapter reads `DateTime` columns back without a timezone, and the
    values it stores are UTC. `astimezone` would read such a value as local time, so a
    naive value gets UTC attached instead.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
