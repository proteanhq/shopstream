"""Application tests for AddSellerReply command handler."""

import pytest
from protean import current_domain
from protean.exceptions import ValidationError
from reviews.review.moderation import ModerateReview
from reviews.review.reply import AddSellerReply
from reviews.review.review import Review
from reviews.review.submission import SubmitReview


def _submit_and_approve(**overrides):
    defaults = {
        "product_id": "prod-reply",
        "customer_id": "cust-reply",
        "rating": 4,
        "title": "Review for reply",
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


class TestAddSellerReplyCommand:
    def test_reply_persists(self):
        review_id = _submit_and_approve(product_id="prod-rply-1", customer_id="cust-rply-1")
        current_domain.process(
            AddSellerReply(
                review_id=review_id,
                seller_id="seller-001",
                body="Thank you for your feedback!",
            ),
            asynchronous=False,
        )
        review = current_domain.repository_for(Review).get(review_id)
        assert len(review.reply) == 1
        assert review.reply[0].body == "Thank you for your feedback!"

    def test_duplicate_reply_rejected(self):
        review_id = _submit_and_approve(product_id="prod-rply-2", customer_id="cust-rply-2")
        current_domain.process(
            AddSellerReply(
                review_id=review_id,
                seller_id="seller-001",
                body="First reply",
            ),
            asynchronous=False,
        )
        with pytest.raises(ValidationError) as exc:
            current_domain.process(
                AddSellerReply(
                    review_id=review_id,
                    seller_id="seller-001",
                    body="Second reply",
                ),
                asynchronous=False,
            )
        assert "at most one seller reply" in str(exc.value)

    def test_reply_to_pending_rejected(self):
        review_id = current_domain.process(
            SubmitReview(
                product_id="prod-rply-3",
                customer_id="cust-rply-3",
                rating=4,
                title="Pending review",
                body="This is a pending review body that is long enough.",
            ),
            asynchronous=False,
        )
        with pytest.raises(ValidationError) as exc:
            current_domain.process(
                AddSellerReply(
                    review_id=review_id,
                    seller_id="seller-001",
                    body="Cannot reply to pending",
                ),
                asynchronous=False,
            )
        assert "published reviews" in str(exc.value)
