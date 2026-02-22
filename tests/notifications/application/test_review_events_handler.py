"""Application tests for Reviews cross-domain event handlers."""

from datetime import UTC, datetime

from notifications.notification.notification import (
    Notification,
    NotificationType,
)
from notifications.notification.review_events import ReviewEventsHandler
from protean import current_domain
from shared.events.reviews import ReviewApproved, ReviewRejected


class TestReviewPublishedHandler:
    def test_creates_review_published_notification(self):
        event = ReviewApproved(
            review_id="rev-001",
            product_id="prod-001",
            customer_id="cust-rev-1",
            rating=5,
            moderator_id="mod-001",
            approved_at=datetime.now(UTC),
        )
        handler = ReviewEventsHandler()
        handler.on_review_approved(event)

        repo = current_domain.repository_for(Notification)
        notifications = (
            repo._dao.query.filter(
                recipient_id="cust-rev-1",
                notification_type=NotificationType.REVIEW_PUBLISHED.value,
            )
            .all()
            .items
        )
        assert len(notifications) >= 1


class TestReviewRejectedHandler:
    def test_creates_review_rejected_notification(self):
        event = ReviewRejected(
            review_id="rev-002",
            product_id="prod-002",
            customer_id="cust-rev-2",
            moderator_id="mod-001",
            reason="Inappropriate content",
            rejected_at=datetime.now(UTC),
        )
        handler = ReviewEventsHandler()
        handler.on_review_rejected(event)

        repo = current_domain.repository_for(Notification)
        notifications = (
            repo._dao.query.filter(
                recipient_id="cust-rev-2",
                notification_type=NotificationType.REVIEW_REJECTED.value,
            )
            .all()
            .items
        )
        assert len(notifications) >= 1
