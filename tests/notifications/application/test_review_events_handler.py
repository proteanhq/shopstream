"""Application tests for Reviews cross-domain subscriber."""

from datetime import UTC, datetime

from protean import current_domain

from notifications.notification.notification import (
    Notification,
    NotificationType,
)
from notifications.notification.review_subscriber import ReviewEventsSubscriber


def _build_message(event_type: str, data: dict) -> dict:
    """Build a broker message payload with metadata and data."""
    return {
        "data": data,
        "metadata": {"headers": {"type": event_type}},
    }


class TestReviewPublishedHandler:
    def test_creates_review_published_notification(self):
        subscriber = ReviewEventsSubscriber()
        subscriber(
            _build_message(
                "Reviews.ReviewApproved.v1",
                {
                    "review_id": "rev-001",
                    "product_id": "prod-001",
                    "customer_id": "cust-rev-1",
                    "rating": 5,
                    "moderator_id": "mod-001",
                    "approved_at": datetime.now(UTC).isoformat(),
                },
            )
        )

        repo = current_domain.repository_for(Notification)
        notifications = (
            repo.query.filter(
                recipient_id="cust-rev-1",
                notification_type=NotificationType.REVIEW_PUBLISHED.value,
            )
            .all()
            .items
        )
        assert len(notifications) >= 1


class TestReviewRejectedHandler:
    def test_creates_review_rejected_notification(self):
        subscriber = ReviewEventsSubscriber()
        subscriber(
            _build_message(
                "Reviews.ReviewRejected.v1",
                {
                    "review_id": "rev-002",
                    "product_id": "prod-002",
                    "customer_id": "cust-rev-2",
                    "moderator_id": "mod-001",
                    "reason": "Inappropriate content",
                    "rejected_at": datetime.now(UTC).isoformat(),
                },
            )
        )

        repo = current_domain.repository_for(Notification)
        notifications = (
            repo.query.filter(
                recipient_id="cust-rev-2",
                notification_type=NotificationType.REVIEW_REJECTED.value,
            )
            .all()
            .items
        )
        assert len(notifications) >= 1


class TestIgnoresUnrelatedEvents:
    def test_ignores_non_matching_events(self):
        """Non-review events on the stream should be ignored."""
        subscriber = ReviewEventsSubscriber()
        subscriber(_build_message("Reviews.ReviewSubmitted.v1", {"review_id": "rev-ignore"}))
