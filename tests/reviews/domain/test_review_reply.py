"""Tests for Review seller reply — only on published, max 1, event raising."""

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


def _published_review():
    review = _make_review()
    review._events.clear()
    review.approve(moderator_id="mod-001")
    review._events.clear()
    return review


class TestAddSellerReply:
    def test_reply_added_to_published_review(self):
        review = _published_review()
        review.add_seller_reply(seller_id="seller-001", body="Thank you!")
        assert len(review.reply) == 1
        assert str(review.reply[0].seller_id) == "seller-001"
        assert review.reply[0].body == "Thank you!"
        assert review.reply[0].replied_at is not None

    def test_reply_updates_timestamp(self):
        review = _published_review()
        original = review.updated_at
        review.add_seller_reply(seller_id="seller-001", body="Thank you!")
        assert review.updated_at >= original


class TestSellerReplyGuards:
    def test_cannot_reply_to_pending_review(self):
        review = _make_review()
        review._events.clear()
        with pytest.raises(ValidationError) as exc:
            review.add_seller_reply(seller_id="seller-001", body="Reply")
        assert "published reviews" in str(exc.value)

    def test_cannot_reply_to_rejected_review(self):
        review = _make_review()
        review._events.clear()
        review.reject(moderator_id="mod-001", reason="Bad content")
        review._events.clear()
        with pytest.raises(ValidationError) as exc:
            review.add_seller_reply(seller_id="seller-001", body="Reply")
        assert "published reviews" in str(exc.value)

    def test_cannot_reply_to_removed_review(self):
        review = _published_review()
        review.remove(removed_by="Admin", reason="Policy")
        review._events.clear()
        with pytest.raises(ValidationError) as exc:
            review.add_seller_reply(seller_id="seller-001", body="Reply")
        assert "published reviews" in str(exc.value)

    def test_cannot_add_second_reply(self):
        review = _published_review()
        review.add_seller_reply(seller_id="seller-001", body="Thank you!")
        review._events.clear()
        with pytest.raises(ValidationError) as exc:
            review.add_seller_reply(seller_id="seller-001", body="Another reply")
        assert "at most one seller reply" in str(exc.value)


class TestReplyRaisesEvent:
    def test_reply_raises_event(self):
        review = _published_review()
        review.add_seller_reply(seller_id="seller-001", body="Thank you!")
        assert len(review._events) == 1
        event = review._events[0]
        assert event.__class__.__name__ == "SellerReplyAdded"
        assert str(event.review_id) == str(review.id)
        assert str(event.seller_id) == "seller-001"
        assert event.body == "Thank you!"
        assert event.replied_at is not None
