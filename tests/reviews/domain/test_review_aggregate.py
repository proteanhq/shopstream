"""Tests for Review aggregate creation and structure."""

import json

from reviews.review.review import Review, ReviewStatus


class TestReviewSubmission:
    def test_submit_creates_review(self):
        review = Review.submit(
            product_id="prod-001",
            customer_id="cust-001",
            rating=4,
            title="Great product",
            body="I really enjoyed this product, it exceeded expectations.",
        )
        assert review.id is not None
        assert str(review.product_id) == "prod-001"
        assert str(review.customer_id) == "cust-001"

    def test_submit_sets_pending_status(self):
        review = Review.submit(
            product_id="prod-001",
            customer_id="cust-001",
            rating=4,
            title="Great product",
            body="I really enjoyed this product, it exceeded expectations.",
        )
        assert review.status == ReviewStatus.PENDING.value

    def test_submit_sets_rating(self):
        review = Review.submit(
            product_id="prod-001",
            customer_id="cust-001",
            rating=5,
            title="Amazing product",
            body="Absolutely love this product, best purchase ever!",
        )
        assert review.rating.score == 5

    def test_submit_sets_title_and_body(self):
        review = Review.submit(
            product_id="prod-001",
            customer_id="cust-001",
            rating=3,
            title="Decent product",
            body="It works as expected, nothing special though.",
        )
        assert review.title == "Decent product"
        assert review.body == "It works as expected, nothing special though."

    def test_submit_sets_timestamps(self):
        review = Review.submit(
            product_id="prod-001",
            customer_id="cust-001",
            rating=4,
            title="Great product",
            body="I really enjoyed this product, it exceeded expectations.",
        )
        assert review.created_at is not None
        assert review.updated_at is not None

    def test_submit_defaults(self):
        review = Review.submit(
            product_id="prod-001",
            customer_id="cust-001",
            rating=4,
            title="Great product",
            body="I really enjoyed this product, it exceeded expectations.",
        )
        assert review.verified_purchase is False
        assert review.is_edited is False
        assert review.helpful_count == 0
        assert review.unhelpful_count == 0
        assert review.report_count == 0
        assert len(review.images) == 0
        assert len(review.votes) == 0
        assert len(review.reply) == 0

    def test_submit_with_optional_fields(self):
        review = Review.submit(
            product_id="prod-001",
            customer_id="cust-001",
            rating=4,
            title="Great product",
            body="I really enjoyed this product, it exceeded expectations.",
            variant_id="var-001",
            order_id="order-001",
            verified_purchase=True,
        )
        assert str(review.variant_id) == "var-001"
        assert str(review.order_id) == "order-001"
        assert review.verified_purchase is True


class TestReviewWithProsAndCons:
    def test_submit_with_pros_and_cons(self):
        review = Review.submit(
            product_id="prod-001",
            customer_id="cust-001",
            rating=4,
            title="Great product",
            body="I really enjoyed this product, it exceeded expectations.",
            pros=["Durable", "Great value"],
            cons=["Heavy"],
        )
        assert json.loads(review.pros) == ["Durable", "Great value"]
        assert json.loads(review.cons) == ["Heavy"]

    def test_submit_without_pros_and_cons(self):
        review = Review.submit(
            product_id="prod-001",
            customer_id="cust-001",
            rating=4,
            title="Great product",
            body="I really enjoyed this product, it exceeded expectations.",
        )
        assert review.pros is None
        assert review.cons is None


class TestReviewWithImages:
    def test_submit_with_images(self):
        review = Review.submit(
            product_id="prod-001",
            customer_id="cust-001",
            rating=4,
            title="Great product",
            body="I really enjoyed this product, it exceeded expectations.",
            images=[
                {"url": "https://cdn.example.com/img1.jpg", "alt_text": "Front view"},
                {"url": "https://cdn.example.com/img2.jpg"},
            ],
        )
        assert len(review.images) == 2
        assert review.images[0].url == "https://cdn.example.com/img1.jpg"
        assert review.images[0].alt_text == "Front view"
        assert review.images[1].display_order == 1

    def test_submit_without_images(self):
        review = Review.submit(
            product_id="prod-001",
            customer_id="cust-001",
            rating=4,
            title="Great product",
            body="I really enjoyed this product, it exceeded expectations.",
        )
        assert len(review.images) == 0


class TestReviewRaisesEvent:
    def test_submit_raises_review_submitted_event(self):
        review = Review.submit(
            product_id="prod-001",
            customer_id="cust-001",
            rating=4,
            title="Great product",
            body="I really enjoyed this product, it exceeded expectations.",
        )
        assert len(review._events) == 1
        event = review._events[0]
        assert event.__class__.__name__ == "ReviewSubmitted"
        assert str(event.review_id) == str(review.id)
        assert str(event.product_id) == "prod-001"
        assert str(event.customer_id) == "cust-001"
        assert event.rating == 4
