"""Checks for the process_and_wait / drain helpers (verification/support).

The `sync` contract runs end to end against the real reviews domain in memory
mode - a command driven through `process_and_wait` must leave the read model
updated with no manual wait. The `async` branch needs a live engine + broker, so
here we verify only its control flow (cycle counting, early stop, max-cycle
bound, sync-vs-async branching) with a stubbed Engine; the real engine path is
exercised by the engine-marked DLQ test.

    .venv/bin/python -m pytest verification/support/test_processing.py \
        --protean-env memory -q
"""

from __future__ import annotations

import pytest

from verification.support import processing
from verification.support.processing import DEFAULT_MAX_CYCLES, drain, process_and_wait


class _StubEngine:
    """Stand-in for protean's Engine: counts how many times run() is called."""

    calls = 0

    def __init__(self, domain, test_mode=False):
        self.domain = domain
        self.test_mode = test_mode

    def run(self):
        type(self).calls += 1


class _FakeDomain:
    """Minimal domain exposing just the surface the helpers touch."""

    def __init__(self, event_processing):
        self.config = {"event_processing": event_processing}
        self.processed = []

    def process(self, command, asynchronous=None):
        self.processed.append((command, asynchronous))
        return "result-id"


@pytest.fixture()
def stub_engine(monkeypatch):
    _StubEngine.calls = 0
    monkeypatch.setattr(processing, "Engine", _StubEngine)
    return _StubEngine


# --- sync path: real domain, real projector, no wait --------------------------


@pytest.mark.usefixtures("reviews_ctx")
def test_process_and_wait_sync_settles_inline():
    """In a sync domain the read model is up to date the instant we return."""
    from protean import current_domain

    from reviews.domain import reviews
    from reviews.projections.product_rating import ProductRating
    from reviews.review.moderation import ModerateReview
    from reviews.review.submission import SubmitReview

    product_id = "prod-paw"
    review_id = process_and_wait(
        SubmitReview(
            product_id=product_id,
            customer_id="cust-paw",
            rating=5,
            title="Great",
            body="This held up well over months of regular use, would buy again.",
        ),
        reviews,
    )
    process_and_wait(
        ModerateReview(review_id=review_id, moderator_id="mod-1", action="Approve"),
        reviews,
    )

    # No polling, no sleep: the projector already ran inline during commit.
    rating = current_domain.repository_for(ProductRating).get(product_id)
    assert rating.total_reviews == 1


# --- async branch control flow: stubbed engine --------------------------------


def test_drain_stops_as_soon_as_condition_holds(stub_engine):
    state = {"cycle": 0}

    def until():
        state["cycle"] += 1
        return state["cycle"] >= 2  # satisfied after the 2nd check

    cycles = drain(_FakeDomain("async"), until=until, max_cycles=10)
    assert cycles == 2
    assert stub_engine.calls == 2  # stopped early, did not burn all 10


def test_drain_respects_max_cycles_when_condition_never_holds(stub_engine):
    cycles = drain(_FakeDomain("async"), until=lambda: False, max_cycles=3)
    assert cycles == 3
    assert stub_engine.calls == 3  # bounded, never hangs


def test_drain_without_condition_runs_default_cycles(stub_engine):
    cycles = drain(_FakeDomain("async"))
    assert cycles == DEFAULT_MAX_CYCLES
    assert stub_engine.calls == DEFAULT_MAX_CYCLES


def test_process_and_wait_sync_domain_never_touches_engine(stub_engine):
    domain = _FakeDomain("sync")
    result = process_and_wait("cmd", domain)
    assert result == "result-id"
    assert domain.processed == [("cmd", False)]  # handler ran synchronously
    assert stub_engine.calls == 0  # sync -> no engine drain


def test_process_and_wait_async_domain_drains_engine(stub_engine):
    domain = _FakeDomain("async")
    result = process_and_wait("cmd", domain, until=lambda: True)
    assert result == "result-id"
    assert stub_engine.calls == 1  # async -> drained until condition (immediately) held
