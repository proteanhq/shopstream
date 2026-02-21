"""Tests for Review aggregate invariants."""

import pytest
from protean.exceptions import ValidationError
from reviews.review.review import Review


def _make_review(**overrides):
    defaults = {
        "product_id": "prod-001",
        "customer_id": "cust-001",
        "rating": 4,
        "title": "Great product",
        "body": "I really enjoyed this product, it exceeded expectations.",
    }
    defaults.update(overrides)
    return Review.submit(**defaults)


class TestMaxImagesInvariant:
    def test_5_images_allowed(self):
        review = _make_review(images=[{"url": f"https://cdn.example.com/img{i}.jpg"} for i in range(5)])
        assert len(review.images) == 5

    def test_6th_image_rejected(self):
        with pytest.raises(ValidationError) as exc:
            _make_review(images=[{"url": f"https://cdn.example.com/img{i}.jpg"} for i in range(6)])
        assert "Cannot attach more than 5 images" in str(exc.value)


class TestAtMostOneSellerReply:
    def test_one_reply_allowed(self):
        review = _make_review()
        review._events.clear()
        # Advance to published
        review.approve(moderator_id="mod-001")
        review._events.clear()

        review.add_seller_reply(seller_id="seller-001", body="Thank you for your feedback!")
        assert len(review.reply) == 1

    def test_second_reply_rejected(self):
        review = _make_review()
        review._events.clear()
        review.approve(moderator_id="mod-001")
        review._events.clear()

        review.add_seller_reply(seller_id="seller-001", body="Thank you for your feedback!")
        review._events.clear()

        with pytest.raises(ValidationError) as exc:
            review.add_seller_reply(seller_id="seller-001", body="Another reply")
        assert "at most one seller reply" in str(exc.value)


class TestBodyMinimumLength:
    def test_20_char_body_accepted(self):
        review = _make_review(body="This is exactly twenty characters long!")
        assert review.body is not None

    def test_short_body_rejected(self):
        with pytest.raises(ValidationError) as exc:
            _make_review(body="Too short")
        assert "at least 20 characters" in str(exc.value)

    def test_whitespace_only_body_rejected(self):
        with pytest.raises(ValidationError) as exc:
            _make_review(body="   short   ")
        assert "at least 20 characters" in str(exc.value)


class TestTitleNotEmpty:
    def test_valid_title(self):
        review = _make_review(title="Great product review")
        assert review.title == "Great product review"

    def test_whitespace_only_title_rejected(self):
        with pytest.raises(ValidationError) as exc:
            _make_review(title="   ")
        assert "title cannot be empty" in str(exc.value)
