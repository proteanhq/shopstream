"""Application tests for SubmitReview command handler."""

import json

import pytest
from protean import current_domain
from protean.exceptions import ValidationError
from reviews.review.review import Review, ReviewStatus
from reviews.review.submission import SubmitReview


def _submit_review(**overrides):
    defaults = {
        "product_id": "prod-001",
        "customer_id": "cust-001",
        "rating": 4,
        "title": "Great product",
        "body": "I really enjoyed this product, it exceeded expectations.",
    }
    defaults.update(overrides)
    return current_domain.process(SubmitReview(**defaults), asynchronous=False)


class TestSubmitReviewCommand:
    def test_submit_persists_review(self):
        review_id = _submit_review()
        review = current_domain.repository_for(Review).get(review_id)
        assert review is not None
        assert str(review.product_id) == "prod-001"
        assert str(review.customer_id) == "cust-001"
        assert review.rating.score == 4
        assert review.status == ReviewStatus.PENDING.value

    def test_submit_with_pros_and_cons(self):
        review_id = _submit_review(
            pros=json.dumps(["Good quality", "Fast shipping"]),
            cons=json.dumps(["A bit pricey"]),
        )
        review = current_domain.repository_for(Review).get(review_id)
        assert json.loads(review.pros) == ["Good quality", "Fast shipping"]
        assert json.loads(review.cons) == ["A bit pricey"]

    def test_submit_with_images(self):
        review_id = _submit_review(
            images=json.dumps(
                [
                    {"url": "https://cdn.example.com/img1.jpg", "alt_text": "Front"},
                ]
            )
        )
        review = current_domain.repository_for(Review).get(review_id)
        assert len(review.images) == 1

    def test_submit_returns_review_id(self):
        review_id = _submit_review()
        assert review_id is not None
        assert isinstance(review_id, str)


class TestOneReviewPerCustomerPerProduct:
    def test_duplicate_review_rejected(self):
        _submit_review(product_id="prod-dup", customer_id="cust-dup")
        with pytest.raises(ValidationError) as exc:
            _submit_review(product_id="prod-dup", customer_id="cust-dup")
        assert "already reviewed" in str(exc.value)

    def test_different_product_allowed(self):
        _submit_review(product_id="prod-a", customer_id="cust-same")
        review_id = _submit_review(product_id="prod-b", customer_id="cust-same")
        assert review_id is not None

    def test_different_customer_allowed(self):
        _submit_review(product_id="prod-same", customer_id="cust-x")
        review_id = _submit_review(product_id="prod-same", customer_id="cust-y")
        assert review_id is not None
