"""Inbound cross-domain event handler — Notifications reacts to Review events.

Listens for ReviewApproved (review published) and ReviewRejected (review rejected).
"""

import structlog
from notifications.domain import notifications
from notifications.notification.helpers import create_notifications_for_customer
from notifications.notification.notification import Notification, NotificationType
from protean.utils.mixins import handle
from shared.events.reviews import ReviewApproved, ReviewRejected

logger = structlog.get_logger(__name__)

notifications.register_external_event(ReviewApproved, "Reviews.ReviewApproved.v1")
notifications.register_external_event(ReviewRejected, "Reviews.ReviewRejected.v1")


@notifications.event_handler(part_of=Notification, stream_category="reviews::review")
class ReviewEventsHandler:
    """Reacts to Reviews domain events to send customer notifications."""

    @handle(ReviewApproved)
    def on_review_approved(self, event: ReviewApproved) -> None:
        """Notify the customer that their review has been published."""
        create_notifications_for_customer(
            customer_id=str(event.customer_id),
            notification_type=NotificationType.REVIEW_PUBLISHED.value,
            context={
                "product_id": str(event.product_id),
                "review_id": str(event.review_id),
                "rating": event.rating,
            },
            source_event_type="Reviews.ReviewApproved.v1",
        )

    @handle(ReviewRejected)
    def on_review_rejected(self, event: ReviewRejected) -> None:
        """Notify the customer that their review was rejected."""
        create_notifications_for_customer(
            customer_id=str(event.customer_id),
            notification_type=NotificationType.REVIEW_REJECTED.value,
            context={
                "product_id": str(event.product_id),
                "review_id": str(event.review_id),
                "reason": event.reason,
            },
            source_event_type="Reviews.ReviewRejected.v1",
        )
