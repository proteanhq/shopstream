"""Inbound cross-domain subscriber — Notifications reacts to Review events.

Listens for ReviewApproved (review published) and ReviewRejected (review rejected).

Uses the subscriber (ACL) pattern: receives raw dict payloads from the global
broker, filters by event type, and translates into domain-local side effects.
No dependency on shared event classes or register_external_event.
"""

import structlog

from notifications.domain import notifications
from notifications.notification.helpers import create_notifications_for_customer
from notifications.notification.notification import NotificationType

logger = structlog.get_logger(__name__)


@notifications.subscriber(broker="global", stream="reviews::review")
class ReviewEventsSubscriber:
    """Reacts to Reviews domain events to send customer notifications.

    ACL pattern: receives raw broker message dict, extracts event type from
    metadata.headers.type, and creates notifications. Ignores all event
    types not relevant to the Notifications domain.
    """

    def __call__(self, payload: dict) -> None:
        event_type = payload.get("metadata", {}).get("headers", {}).get("type", "")
        data = payload.get("data", {})

        if "ReviewApproved" in event_type:
            self._on_review_approved(data)
        elif "ReviewRejected" in event_type:
            self._on_review_rejected(data)

    def _on_review_approved(self, data: dict) -> None:
        """Notify the customer that their review has been published."""
        create_notifications_for_customer(
            customer_id=str(data["customer_id"]),
            notification_type=NotificationType.REVIEW_PUBLISHED.value,
            context={
                "product_id": str(data["product_id"]),
                "review_id": str(data["review_id"]),
                "rating": data.get("rating"),
            },
            source_event_type="Reviews.ReviewApproved.v1",
        )

    def _on_review_rejected(self, data: dict) -> None:
        """Notify the customer that their review was rejected."""
        create_notifications_for_customer(
            customer_id=str(data["customer_id"]),
            notification_type=NotificationType.REVIEW_REJECTED.value,
            context={
                "product_id": str(data["product_id"]),
                "review_id": str(data["review_id"]),
                "reason": data.get("reason"),
            },
            source_event_type="Reviews.ReviewRejected.v1",
        )
