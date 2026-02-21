"""Application tests for RemoveReview command handler."""

import pytest
from protean import current_domain
from protean.exceptions import ValidationError
from reviews.review.moderation import ModerateReview
from reviews.review.removal import RemoveReview
from reviews.review.review import Review, ReviewStatus
from reviews.review.submission import SubmitReview


def _submit_and_approve(**overrides):
    defaults = {
        "product_id": "prod-remove",
        "customer_id": "cust-remove",
        "rating": 4,
        "title": "Review to remove",
        "body": "This is a review body that is long enough for validation.",
    }
    defaults.update(overrides)
    review_id = current_domain.process(SubmitReview(**defaults), asynchronous=False)
    current_domain.process(
        ModerateReview(
            review_id=review_id,
            moderator_id="mod-001",
            action="Approve",
        ),
        asynchronous=False,
    )
    return review_id


class TestRemoveReviewCommand:
    def test_remove_persists(self):
        review_id = _submit_and_approve(product_id="prod-rm-1", customer_id="cust-rm-1")
        current_domain.process(
            RemoveReview(
                review_id=review_id,
                removed_by="Admin",
                reason="Policy violation",
            ),
            asynchronous=False,
        )
        review = current_domain.repository_for(Review).get(review_id)
        assert review.status == ReviewStatus.REMOVED.value

    def test_remove_pending_fails(self):
        review_id = current_domain.process(
            SubmitReview(
                product_id="prod-rm-2",
                customer_id="cust-rm-2",
                rating=4,
                title="Pending review",
                body="This is a pending review body that is long enough.",
            ),
            asynchronous=False,
        )
        with pytest.raises(ValidationError) as exc:
            current_domain.process(
                RemoveReview(
                    review_id=review_id,
                    removed_by="Admin",
                    reason="Policy",
                ),
                asynchronous=False,
            )
        assert "Cannot transition" in str(exc.value)
