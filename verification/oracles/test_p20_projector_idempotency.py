"""P20 - projector idempotency under redelivery.

WHAT THIS CHECKS
    Protean delivers events to projectors at least once (a message can be
    delivered more than once: after publish-then-crash the engine re-publishes
    it). Protean does NOT dedupe events on the consume side. So a projector that
    is not idempotent will apply the same event twice and corrupt its read model.

    Property P20: delivering one event N times must leave the read model in the
    same state as delivering it once.

WHY THIS CHECK IS DIFFERENT FROM "projection == fold(events)"
    The usual convergence check folds the event stream and compares it to the
    projection. If the stream contains the duplicate, BOTH sides see the
    duplicate, so they agree and the check passes even though the read model is
    wrong. That check shares the bug.

    This check does NOT share the bug: the expected value (1 review) is computed
    by hand, independently of the event stream. That independence is the whole
    point - it can catch a bug the convergence check is blind to.

STATUS
    Expected to FAIL today: ProductRatingProjector does total_reviews += 1 on
    every delivery (reviews/projections/product_rating.py:56). Marked xfail so
    the suite stays green; when the projector is made idempotent this test will
    pass, xfail(strict=True) will flag it, and the marker should be removed.

RUN (no Docker):
    .venv/bin/python -m pytest \
        verification/oracles/test_p20_projector_idempotency.py --protean-env memory -q
"""

from datetime import UTC, datetime

import pytest
from protean import current_domain

from reviews.projections.product_rating import ProductRating, ProductRatingProjector
from reviews.review.events import ReviewApproved
from reviews.review.moderation import ModerateReview
from reviews.review.submission import SubmitReview


def _submit_and_approve(product_id: str, rating: int = 5) -> str:
    """Create one approved review; the projector raises total_reviews to 1."""
    review_id = current_domain.process(
        SubmitReview(
            product_id=product_id,
            customer_id="cust-p20",
            rating=rating,
            title="Solid product",
            body="This held up well over months of regular use, would buy again.",
        ),
        asynchronous=False,
    )
    current_domain.process(
        ModerateReview(review_id=review_id, moderator_id="mod-1", action="Approve"),
        asynchronous=False,
    )
    return review_id


@pytest.mark.usefixtures("reviews_ctx")
@pytest.mark.xfail(
    strict=True,
    reason=(
        "P20 gap: ProductRatingProjector.on_review_approved is not idempotent "
        "(total_reviews += 1 per delivery). Protean has no consume-side event "
        "dedup and delivery is at-least-once, so a redelivered ReviewApproved "
        "double-counts. Fix: upsert by (product_id, review_id) or add framework "
        "idempotency. See VERIFICATION_STRATEGY.md (P20) and the Protean gap issue."
    ),
)
def test_product_rating_projector_is_idempotent_under_redelivery():
    product_id = "prod-p20"
    review_id = _submit_and_approve(product_id)

    repo = current_domain.repository_for(ProductRating)
    assert repo.get(product_id).total_reviews == 1  # baseline: one approved review

    # Simulate at-least-once redelivery of the SAME ReviewApproved event.
    redelivered = ReviewApproved(
        review_id=review_id,
        product_id=product_id,
        customer_id="cust-p20",
        rating=5,
        moderator_id="mod-1",
        approved_at=datetime.now(UTC),
    )
    ProductRatingProjector().on_review_approved(redelivered)

    # Independent expected value: one review was approved, so the count is 1,
    # no matter how many times the event was delivered.
    assert repo.get(product_id).total_reviews == 1
