"""Tests for Review moderation — approve and reject behaviors."""

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


class TestApprove:
    def test_approve_sets_published_status(self):
        review = _make_review()
        review._events.clear()
        review.approve(moderator_id="mod-001")
        assert review.status == ReviewStatus.PUBLISHED.value

    def test_approve_stores_notes(self):
        review = _make_review()
        review._events.clear()
        review.approve(moderator_id="mod-001", notes="Looks good")
        assert review.moderation_notes == "Looks good"

    def test_approve_updates_timestamp(self):
        review = _make_review()
        original = review.updated_at
        review._events.clear()
        review.approve(moderator_id="mod-001")
        assert review.updated_at >= original

    def test_approve_raises_event(self):
        review = _make_review()
        review._events.clear()
        review.approve(moderator_id="mod-001")
        assert len(review._events) == 1
        event = review._events[0]
        assert event.__class__.__name__ == "ReviewApproved"
        assert str(event.review_id) == str(review.id)
        assert str(event.product_id) == "prod-001"
        assert str(event.customer_id) == "cust-001"
        assert event.rating == 4
        assert str(event.moderator_id) == "mod-001"
        assert event.approved_at is not None

    def test_approve_without_notes(self):
        review = _make_review()
        review._events.clear()
        review.approve(moderator_id="mod-001")
        assert review.moderation_notes is None


class TestReject:
    def test_reject_sets_rejected_status(self):
        review = _make_review()
        review._events.clear()
        review.reject(moderator_id="mod-001", reason="Contains spam")
        assert review.status == ReviewStatus.REJECTED.value

    def test_reject_stores_reason_as_notes(self):
        review = _make_review()
        review._events.clear()
        review.reject(moderator_id="mod-001", reason="Contains spam")
        assert review.moderation_notes == "Contains spam"

    def test_reject_raises_event(self):
        review = _make_review()
        review._events.clear()
        review.reject(moderator_id="mod-001", reason="Inappropriate")
        assert len(review._events) == 1
        event = review._events[0]
        assert event.__class__.__name__ == "ReviewRejected"
        assert str(event.review_id) == str(review.id)
        assert str(event.moderator_id) == "mod-001"
        assert event.reason == "Inappropriate"
        assert event.rejected_at is not None
