"""Application tests for EditReview command handler."""

import pytest
from protean import current_domain
from protean.exceptions import ValidationError
from reviews.review.editing import EditReview
from reviews.review.review import Review, ReviewStatus
from reviews.review.submission import SubmitReview


def _submit_review(**overrides):
    defaults = {
        "product_id": "prod-edit",
        "customer_id": "cust-edit",
        "rating": 3,
        "title": "Original title",
        "body": "This is the original body of the review that is long enough.",
    }
    defaults.update(overrides)
    return current_domain.process(SubmitReview(**defaults), asynchronous=False)


class TestEditReviewCommand:
    def test_edit_persists_changes(self):
        review_id = _submit_review(product_id="prod-edit-1", customer_id="cust-edit-1")
        current_domain.process(
            EditReview(
                review_id=review_id,
                customer_id="cust-edit-1",
                title="Updated title",
            ),
            asynchronous=False,
        )
        review = current_domain.repository_for(Review).get(review_id)
        assert review.title == "Updated title"
        assert review.is_edited is True

    def test_wrong_customer_rejected(self):
        review_id = _submit_review(product_id="prod-edit-2", customer_id="cust-edit-2")
        with pytest.raises(ValidationError) as exc:
            current_domain.process(
                EditReview(
                    review_id=review_id,
                    customer_id="cust-wrong",
                    title="Hacked title",
                ),
                asynchronous=False,
            )
        assert "Only the review author" in str(exc.value)

    def test_edit_rejected_review_resubmits(self):
        from reviews.review.moderation import ModerateReview

        review_id = _submit_review(product_id="prod-edit-3", customer_id="cust-edit-3")
        # Reject first
        current_domain.process(
            ModerateReview(
                review_id=review_id,
                moderator_id="mod-001",
                action="Reject",
                reason="Needs improvement",
            ),
            asynchronous=False,
        )
        review = current_domain.repository_for(Review).get(review_id)
        assert review.status == ReviewStatus.REJECTED.value

        # Edit to re-submit
        current_domain.process(
            EditReview(
                review_id=review_id,
                customer_id="cust-edit-3",
                body="New improved body that is definitely long enough to pass validation.",
            ),
            asynchronous=False,
        )
        review = current_domain.repository_for(Review).get(review_id)
        assert review.status == ReviewStatus.PENDING.value
