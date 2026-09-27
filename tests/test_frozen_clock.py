"""The `frozen_clocks` helper behind the `frozen_clock` fixture puts each domain's clock back.

Domains are set up once per session, so a stub clock left on one would freeze time
for every later test that relies on a job's default `as_of`.
"""

from datetime import UTC, datetime, timedelta

import pytest

from tests.conftest import FrozenClock, frozen_clocks

T = datetime(2030, 1, 1, tzinfo=UTC)


class FakeDomain:
    """Stands in for a `protean.Domain`: the helper only reads and writes `clock`."""

    def __init__(self, clock):
        self.clock = clock


def test_exit_restores_each_frozen_domain_clock():
    original_a, original_b = object(), object()
    domain_a = FakeDomain(original_a)
    domain_b = FakeDomain(original_b)

    with frozen_clocks() as freeze:
        freeze(domain_a, T)
        freeze(domain_b, T)
        assert isinstance(domain_a.clock, FrozenClock)
        assert isinstance(domain_b.clock, FrozenClock)

    assert domain_a.clock is original_a
    assert domain_b.clock is original_b


def test_freezing_twice_restores_the_first_original():
    original = object()
    domain = FakeDomain(original)

    with frozen_clocks() as freeze:
        freeze(domain, T)
        freeze(domain, T + timedelta(days=1))

    assert domain.clock is original


def test_exit_restores_the_clock_when_the_test_raises():
    original = object()
    domain = FakeDomain(original)

    with pytest.raises(RuntimeError), frozen_clocks() as freeze:
        freeze(domain, T)
        raise RuntimeError("test failed")

    assert domain.clock is original


def test_frozen_clock_rejects_a_naive_datetime():
    with pytest.raises(ValueError):
        FrozenClock(datetime(2030, 1, 1))
