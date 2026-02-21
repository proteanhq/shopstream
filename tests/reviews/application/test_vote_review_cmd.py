"""Application tests for VoteOnReview command handler."""

import pytest
from protean import current_domain
from protean.exceptions import ValidationError
from reviews.review.review import Review
from reviews.review.submission import SubmitReview
from reviews.review.voting import VoteOnReview


def _submit_review(**overrides):
    defaults = {
        "product_id": "prod-vote",
        "customer_id": "cust-vote-author",
        "rating": 4,
        "title": "Review for voting",
        "body": "This is a review body that is long enough for validation.",
    }
    defaults.update(overrides)
    return current_domain.process(SubmitReview(**defaults), asynchronous=False)


class TestVoteOnReviewCommand:
    def test_helpful_vote_persists(self):
        review_id = _submit_review(product_id="prod-vote-1", customer_id="cust-vote-1")
        current_domain.process(
            VoteOnReview(
                review_id=review_id,
                customer_id="cust-voter-1",
                vote_type="Helpful",
            ),
            asynchronous=False,
        )
        review = current_domain.repository_for(Review).get(review_id)
        assert review.helpful_count == 1

    def test_self_vote_rejected(self):
        review_id = _submit_review(product_id="prod-vote-2", customer_id="cust-vote-2")
        with pytest.raises(ValidationError) as exc:
            current_domain.process(
                VoteOnReview(
                    review_id=review_id,
                    customer_id="cust-vote-2",
                    vote_type="Helpful",
                ),
                asynchronous=False,
            )
        assert "Cannot vote on your own" in str(exc.value)

    def test_duplicate_vote_rejected(self):
        review_id = _submit_review(product_id="prod-vote-3", customer_id="cust-vote-3")
        current_domain.process(
            VoteOnReview(
                review_id=review_id,
                customer_id="cust-voter-3",
                vote_type="Helpful",
            ),
            asynchronous=False,
        )
        with pytest.raises(ValidationError) as exc:
            current_domain.process(
                VoteOnReview(
                    review_id=review_id,
                    customer_id="cust-voter-3",
                    vote_type="Unhelpful",
                ),
                asynchronous=False,
            )
        assert "already voted" in str(exc.value)
