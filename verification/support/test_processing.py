"""Checks ShopStream's use of `protean.testing.process_and_wait`.

The `sync` contract runs end to end against the real reviews domain in memory
mode: a command driven through `process_and_wait` must report the events it
fired and leave the read model updated with no manual wait. The async branch
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
    from reviews.review.events import ReviewSubmitted
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
    assert ReviewSubmitted in outcome.events
    review_id = outcome.result

    approved = process_and_wait(
        ModerateReview(review_id=review_id, moderator_id="mod-1", action="Approve"),
        reviews,
    )
    assert approved.succeeded

    # No polling, no sleep: the projector already ran inline during commit.
    rating = current_domain.repository_for(ProductRating).get(product_id)
    assert rating.total_reviews == 1
