"""Tests for Review state machine — valid transitions and invalid transition guards."""

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


def _review_at_state(target_status):
    """Create a review and advance it to the desired state."""
    review = _make_review()
    review._events.clear()

    if target_status == ReviewStatus.PENDING:
        return review

    if target_status == ReviewStatus.PUBLISHED:
        review.approve(moderator_id="mod-001")
        review._events.clear()
        return review

    if target_status == ReviewStatus.REJECTED:
        review.reject(moderator_id="mod-001", reason="Inappropriate content")
        review._events.clear()
        return review

    if target_status == ReviewStatus.REMOVED:
        review.approve(moderator_id="mod-001")
        review._events.clear()
        review.remove(removed_by="Admin", reason="Policy violation")
        review._events.clear()
        return review

    raise ValueError(f"Cannot create review at state {target_status}")


# ---------------------------------------------------------------
# Happy path transitions
# ---------------------------------------------------------------
class TestValidTransitions:
    def test_pending_to_published(self):
        review = _review_at_state(ReviewStatus.PENDING)
        review.approve(moderator_id="mod-001")
        assert review.status == ReviewStatus.PUBLISHED.value

    def test_pending_to_rejected(self):
        review = _review_at_state(ReviewStatus.PENDING)
        review.reject(moderator_id="mod-001", reason="Spam")
        assert review.status == ReviewStatus.REJECTED.value

    def test_rejected_to_pending_via_edit(self):
        review = _review_at_state(ReviewStatus.REJECTED)
        review.edit(body="Updated review content that is long enough to pass.")
        assert review.status == ReviewStatus.PENDING.value

    def test_published_to_removed(self):
        review = _review_at_state(ReviewStatus.PUBLISHED)
        review.remove(removed_by="Admin", reason="Policy violation")
        assert review.status == ReviewStatus.REMOVED.value


# ---------------------------------------------------------------
# Invalid transitions
# ---------------------------------------------------------------
class TestInvalidTransitions:
    def test_cannot_approve_published_review(self):
        review = _review_at_state(ReviewStatus.PUBLISHED)
        with pytest.raises(ValidationError) as exc:
            review.approve(moderator_id="mod-002")
        assert "Cannot transition" in str(exc.value)

    def test_cannot_reject_published_review(self):
        review = _review_at_state(ReviewStatus.PUBLISHED)
        with pytest.raises(ValidationError) as exc:
            review.reject(moderator_id="mod-002", reason="Too late")
        assert "Cannot transition" in str(exc.value)

    def test_cannot_approve_removed_review(self):
        review = _review_at_state(ReviewStatus.REMOVED)
        with pytest.raises(ValidationError) as exc:
            review.approve(moderator_id="mod-002")
        assert "Cannot transition" in str(exc.value)

    def test_cannot_reject_removed_review(self):
        review = _review_at_state(ReviewStatus.REMOVED)
        with pytest.raises(ValidationError) as exc:
            review.reject(moderator_id="mod-002", reason="Too late")
        assert "Cannot transition" in str(exc.value)

    def test_cannot_remove_pending_review(self):
        review = _review_at_state(ReviewStatus.PENDING)
        with pytest.raises(ValidationError) as exc:
            review.remove(removed_by="Admin", reason="Policy")
        assert "Cannot transition" in str(exc.value)

    def test_cannot_remove_rejected_review(self):
        review = _review_at_state(ReviewStatus.REJECTED)
        with pytest.raises(ValidationError) as exc:
            review.remove(removed_by="Admin", reason="Policy")
        assert "Cannot transition" in str(exc.value)

    def test_removed_is_terminal(self):
        review = _review_at_state(ReviewStatus.REMOVED)
        with pytest.raises(ValidationError):
            review.remove(removed_by="Admin", reason="Again")

    def test_cannot_approve_rejected_review_directly(self):
        review = _review_at_state(ReviewStatus.REJECTED)
        with pytest.raises(ValidationError) as exc:
            review.approve(moderator_id="mod-002")
        assert "Cannot transition" in str(exc.value)


# ---------------------------------------------------------------
# Edit state constraints
# ---------------------------------------------------------------
class TestEditStateConstraints:
    def test_can_edit_pending_review(self):
        review = _review_at_state(ReviewStatus.PENDING)
        review.edit(title="Updated title for my review")
        assert review.title == "Updated title for my review"

    def test_can_edit_rejected_review(self):
        review = _review_at_state(ReviewStatus.REJECTED)
        review.edit(body="Updated body content that is long enough to pass validation.")
        assert review.status == ReviewStatus.PENDING.value

    def test_cannot_edit_published_review(self):
        review = _review_at_state(ReviewStatus.PUBLISHED)
        with pytest.raises(ValidationError) as exc:
            review.edit(title="Try to edit published")
        assert "Pending or Rejected" in str(exc.value)

    def test_cannot_edit_removed_review(self):
        review = _review_at_state(ReviewStatus.REMOVED)
        with pytest.raises(ValidationError) as exc:
            review.edit(title="Try to edit removed")
        assert "Pending or Rejected" in str(exc.value)
