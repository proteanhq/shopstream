"""Tests for Review.edit() behavior — partial updates, re-submission, sentinel handling."""

import json
from datetime import UTC, datetime

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
        "pros": ["Durable", "Good value"],
        "cons": ["Heavy"],
    }
    defaults.update(overrides)
    return Review.submit(**defaults)


class TestPartialUpdate:
    def test_edit_title_only(self):
        review = _make_review()
        review._events.clear()
        review.edit(title="Updated title")
        assert review.title == "Updated title"
        assert review.body == "I really enjoyed this product, it exceeded expectations."

    def test_edit_body_only(self):
        review = _make_review()
        review._events.clear()
        review.edit(body="New body content that is absolutely long enough.")
        assert review.body == "New body content that is absolutely long enough."
        assert review.title == "Great product"

    def test_edit_rating_only(self):
        review = _make_review()
        review._events.clear()
        review.edit(rating=5)
        assert review.rating.score == 5
        assert review.title == "Great product"

    def test_edit_pros_and_cons(self):
        review = _make_review()
        review._events.clear()
        review.edit(pros=["New pro"], cons=["New con"])
        assert json.loads(review.pros) == ["New pro"]
        assert json.loads(review.cons) == ["New con"]

    def test_edit_multiple_fields(self):
        review = _make_review()
        review._events.clear()
        review.edit(
            title="Updated title",
            body="Updated body content for the review that is long enough.",
            rating=2,
        )
        assert review.title == "Updated title"
        assert review.body == "Updated body content for the review that is long enough."
        assert review.rating.score == 2


class TestEditMarksReviewAsEdited:
    def test_is_edited_set_to_true(self):
        review = _make_review()
        assert review.is_edited is False
        review._events.clear()
        review.edit(title="Edited title")
        assert review.is_edited is True

    def test_edited_at_set(self):
        review = _make_review()
        assert review.edited_at is None
        before = datetime.now(UTC)
        review._events.clear()
        review.edit(title="Edited title")
        assert review.edited_at is not None
        assert review.edited_at >= before

    def test_updated_at_refreshed(self):
        review = _make_review()
        original_updated = review.updated_at
        review._events.clear()
        review.edit(title="Edited title")
        assert review.updated_at >= original_updated


class TestEditReSubmitsRejectedReview:
    def test_editing_rejected_review_moves_to_pending(self):
        review = _make_review()
        review._events.clear()
        review.reject(moderator_id="mod-001", reason="Needs improvement")
        assert review.status == ReviewStatus.REJECTED.value

        review._events.clear()
        review.edit(body="Completely rewritten body with enough content to pass.")
        assert review.status == ReviewStatus.PENDING.value

    def test_editing_pending_review_stays_pending(self):
        review = _make_review()
        review._events.clear()
        review.edit(title="Still pending")
        assert review.status == ReviewStatus.PENDING.value


class TestEditRaisesEvent:
    def test_edit_raises_review_edited_event(self):
        review = _make_review()
        review._events.clear()
        review.edit(title="New title", rating=5)
        assert len(review._events) == 1
        event = review._events[0]
        assert event.__class__.__name__ == "ReviewEdited"
        assert str(event.review_id) == str(review.id)
        assert event.title == "New title"
        assert event.rating == 5

    def test_edit_event_carries_current_values_for_unset_fields(self):
        review = _make_review()
        review._events.clear()
        review.edit(title="Only title changed")
        event = review._events[0]
        assert event.body == "I really enjoyed this product, it exceeded expectations."
        assert event.rating == 4


class TestEditValidation:
    def test_cannot_edit_to_short_body(self):
        review = _make_review()
        review._events.clear()
        with pytest.raises(ValidationError) as exc:
            review.edit(body="Short")
        assert "at least 20 characters" in str(exc.value)
