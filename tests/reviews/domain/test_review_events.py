"""Tests for Review event structure — all 8 events have correct fields and versions."""

from reviews.review.events import (
    HelpfulVoteRecorded,
    ReviewApproved,
    ReviewEdited,
    ReviewRejected,
    ReviewRemoved,
    ReviewReported,
    ReviewSubmitted,
    SellerReplyAdded,
)
from reviews.review.review import ReportReason, Review, VoteType


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


class TestEventVersions:
    def test_review_submitted_version(self):
        assert ReviewSubmitted.__version__ == "v1"

    def test_review_edited_version(self):
        assert ReviewEdited.__version__ == "v1"

    def test_review_approved_version(self):
        assert ReviewApproved.__version__ == "v1"

    def test_review_rejected_version(self):
        assert ReviewRejected.__version__ == "v1"

    def test_helpful_vote_recorded_version(self):
        assert HelpfulVoteRecorded.__version__ == "v1"

    def test_review_reported_version(self):
        assert ReviewReported.__version__ == "v1"

    def test_review_removed_version(self):
        assert ReviewRemoved.__version__ == "v1"

    def test_seller_reply_added_version(self):
        assert SellerReplyAdded.__version__ == "v1"


class TestReviewSubmittedEvent:
    def test_event_fields(self):
        review = _make_review(
            variant_id="var-001",
            images=[{"url": "https://cdn.example.com/img.jpg"}],
        )
        event = review._events[0]
        assert isinstance(event, ReviewSubmitted)
        assert str(event.product_id) == "prod-001"
        assert str(event.variant_id) == "var-001"
        assert str(event.customer_id) == "cust-001"
        assert event.rating == 4
        assert event.title == "Great product"
        assert event.image_count == 1
        assert event.submitted_at is not None


class TestReviewEditedEvent:
    def test_event_fields(self):
        review = _make_review()
        review._events.clear()
        review.edit(title="Updated", rating=5)
        event = review._events[0]
        assert isinstance(event, ReviewEdited)
        assert event.title == "Updated"
        assert event.rating == 5
        assert event.edited_at is not None


class TestReviewApprovedEvent:
    def test_event_fields(self):
        review = _make_review()
        review._events.clear()
        review.approve(moderator_id="mod-001")
        event = review._events[0]
        assert isinstance(event, ReviewApproved)
        assert str(event.product_id) == "prod-001"
        assert str(event.customer_id) == "cust-001"
        assert event.rating == 4
        assert str(event.moderator_id) == "mod-001"


class TestReviewRejectedEvent:
    def test_event_fields(self):
        review = _make_review()
        review._events.clear()
        review.reject(moderator_id="mod-001", reason="Spam content")
        event = review._events[0]
        assert isinstance(event, ReviewRejected)
        assert str(event.product_id) == "prod-001"
        assert str(event.moderator_id) == "mod-001"
        assert event.reason == "Spam content"


class TestHelpfulVoteRecordedEvent:
    def test_event_fields(self):
        review = _make_review()
        review._events.clear()
        review.vote(customer_id="cust-002", vote_type=VoteType.HELPFUL.value)
        event = review._events[0]
        assert isinstance(event, HelpfulVoteRecorded)
        assert str(event.voter_id) == "cust-002"
        assert event.vote_type == VoteType.HELPFUL.value
        assert event.helpful_count == 1
        assert event.unhelpful_count == 0


class TestReviewReportedEvent:
    def test_event_fields(self):
        review = _make_review()
        review._events.clear()
        review.report(
            customer_id="cust-002",
            reason=ReportReason.OFFENSIVE.value,
            detail="Contains profanity",
        )
        event = review._events[0]
        assert isinstance(event, ReviewReported)
        assert str(event.reporter_id) == "cust-002"
        assert event.reason == ReportReason.OFFENSIVE.value
        assert event.detail == "Contains profanity"
        assert event.report_count == 1


class TestReviewRemovedEvent:
    def test_event_fields(self):
        review = _published_review()
        review.remove(removed_by="Admin", reason="Policy violation")
        event = review._events[0]
        assert isinstance(event, ReviewRemoved)
        assert str(event.product_id) == "prod-001"
        assert event.rating == 4
        assert event.removed_by == "Admin"
        assert event.reason == "Policy violation"


class TestSellerReplyAddedEvent:
    def test_event_fields(self):
        review = _published_review()
        review.add_seller_reply(seller_id="seller-001", body="Thank you!")
        event = review._events[0]
        assert isinstance(event, SellerReplyAdded)
        assert str(event.seller_id) == "seller-001"
        assert event.body == "Thank you!"
        assert event.replied_at is not None
