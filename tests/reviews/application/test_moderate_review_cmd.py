"""Application tests for ModerateReview command handler."""

import pytest
from protean import current_domain
from protean.exceptions import ValidationError
from reviews.review.moderation import ModerateReview
from reviews.review.review import Review, ReviewStatus
from reviews.review.submission import SubmitReview


def _submit_review(**overrides):
    defaults = {
        "product_id": "prod-mod",
        "customer_id": "cust-mod",
        "rating": 4,
        "title": "Review to moderate",
        "body": "This is a review body that is long enough for validation.",
    }
    defaults.update(overrides)
    return current_domain.process(SubmitReview(**defaults), asynchronous=False)


class TestApproveCommand:
    def test_approve_persists(self):
        review_id = _submit_review(product_id="prod-mod-1", customer_id="cust-mod-1")
        current_domain.process(
            ModerateReview(
                review_id=review_id,
                moderator_id="mod-001",
                action="Approve",
            ),
            asynchronous=False,
        )
        review = current_domain.repository_for(Review).get(review_id)
        assert review.status == ReviewStatus.PUBLISHED.value

    def test_approve_with_notes(self):
        review_id = _submit_review(product_id="prod-mod-2", customer_id="cust-mod-2")
        current_domain.process(
            ModerateReview(
                review_id=review_id,
                moderator_id="mod-001",
                action="Approve",
                reason="Looks great",
            ),
            asynchronous=False,
        )
        review = current_domain.repository_for(Review).get(review_id)
        assert review.moderation_notes == "Looks great"


class TestRejectCommand:
    def test_reject_persists(self):
        review_id = _submit_review(product_id="prod-mod-3", customer_id="cust-mod-3")
        current_domain.process(
            ModerateReview(
                review_id=review_id,
                moderator_id="mod-001",
                action="Reject",
                reason="Contains spam",
            ),
            asynchronous=False,
        )
        review = current_domain.repository_for(Review).get(review_id)
        assert review.status == ReviewStatus.REJECTED.value

    def test_reject_without_reason_fails(self):
        review_id = _submit_review(product_id="prod-mod-4", customer_id="cust-mod-4")
        with pytest.raises(ValidationError) as exc:
            current_domain.process(
                ModerateReview(
                    review_id=review_id,
                    moderator_id="mod-001",
                    action="Reject",
                ),
                asynchronous=False,
            )
        assert "Reason is required" in str(exc.value)
