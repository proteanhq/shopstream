"""Checks ShopStream's use of `protean.testing.process_and_wait`.

The `sync` contract runs end to end against the real reviews domain in memory
mode: a command driven through `process_and_wait` must report the events it
fired, and only those, and leave the read model updated with no manual wait. A
failing command must come back as a failed outcome with the error attached. The async branch
and `protean.testing.drain` are covered by Protean's own tests.

    uv run pytest verification/support/test_processing.py --protean-env memory -q
"""

from __future__ import annotations

import pytest
from protean.testing import process_and_wait


@pytest.mark.usefixtures("reviews_ctx")
def test_process_and_wait_sync_settles_inline():
    """In a sync domain the read model is up to date the instant we return."""
    from protean import current_domain

    from reviews.domain import reviews
    from reviews.projections.product_rating import ProductRating
    from reviews.review.events import ReviewApproved, ReviewSubmitted
    from reviews.review.moderation import ModerateReview
    from reviews.review.submission import SubmitReview

    product_id = "prod-paw"
    outcome = process_and_wait(
        SubmitReview(
            product_id=product_id,
            customer_id="cust-paw",
            rating=5,
            title="Great",
            body="This held up well over months of regular use, would buy again.",
        ),
        reviews,
    )
    assert outcome.succeeded
    review_id = outcome.result
    assert outcome.events.types == [ReviewSubmitted]
    assert outcome.events[ReviewSubmitted].review_id == review_id

    approved = process_and_wait(
        ModerateReview(review_id=review_id, moderator_id="mod-1", action="Approve"),
        reviews,
    )
    assert approved.succeeded
    # Scoped to the approve's own correlation chain: the earlier submit is not in it.
    assert approved.events.types == [ReviewApproved]
    assert approved.events[ReviewApproved].review_id == review_id

    # No polling, no sleep: the projector already ran inline during commit.
    rating = current_domain.repository_for(ProductRating).get(product_id)
    assert rating.total_reviews == 1


@pytest.mark.usefixtures("reviews_ctx")
def test_process_and_wait_reports_a_failing_command():
    """A handler error comes back on the outcome instead of propagating."""
    from protean.exceptions import ObjectNotFoundError

    from reviews.domain import reviews
    from reviews.review.moderation import ModerateReview

    outcome = process_and_wait(
        ModerateReview(review_id="missing", moderator_id="mod-1", action="Approve"),
        reviews,
    )

    assert outcome.failed
    assert not outcome.succeeded
    assert isinstance(outcome.error, ObjectNotFoundError)
    assert outcome.events.types == []
