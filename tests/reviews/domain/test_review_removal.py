"""Tests for Review removal — only from published, event raising."""

import pytest
from protean.exceptions import ValidationError
from reviews.review.review import Review, ReviewStatus


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


class TestRemoveReview:
    def test_remove_sets_removed_status(self):
        review = _published_review()
        review.remove(removed_by="Admin", reason="Policy violation")
        assert review.status == ReviewStatus.REMOVED.value

    def test_remove_stores_reason_as_notes(self):
        review = _published_review()
        review.remove(removed_by="Admin", reason="Policy violation")
        assert review.moderation_notes == "Policy violation"

    def test_remove_updates_timestamp(self):
        review = _published_review()
        original = review.updated_at
        review.remove(removed_by="Admin", reason="Policy violation")
        assert review.updated_at >= original

    def test_cannot_remove_pending_review(self):
        review = _make_review()
        review._events.clear()
        with pytest.raises(ValidationError) as exc:
            review.remove(removed_by="Admin", reason="Policy")
        assert "Cannot transition" in str(exc.value)

    def test_cannot_remove_already_removed_review(self):
        review = _published_review()
        review.remove(removed_by="Admin", reason="First removal")
        review._events.clear()
        with pytest.raises(ValidationError):
            review.remove(removed_by="Admin", reason="Second removal")


class TestRemoveRaisesEvent:
    def test_remove_raises_event(self):
        review = _published_review()
        review.remove(removed_by="Admin", reason="Policy violation")
        assert len(review._events) == 1
        event = review._events[0]
        assert event.__class__.__name__ == "ReviewRemoved"
        assert str(event.review_id) == str(review.id)
        assert str(event.product_id) == "prod-001"
        assert str(event.customer_id) == "cust-001"
        assert event.rating == 4
        assert event.removed_by == "Admin"
        assert event.reason == "Policy violation"
        assert event.removed_at is not None
