"""Inbound cross-domain event handler — Notifications reacts to Identity events.

Listens for CustomerRegistered to send welcome emails.
"""

import structlog
from notifications.domain import notifications
from notifications.notification.helpers import create_notifications_for_customer
from notifications.notification.notification import Notification, NotificationType
from protean.utils.mixins import handle
from shared.events.identity import CustomerRegistered

logger = structlog.get_logger(__name__)

notifications.register_external_event(CustomerRegistered, "Identity.CustomerRegistered.v1")


@notifications.event_handler(part_of=Notification, stream_category="identity::customer")
class IdentityEventsHandler:
    """Reacts to Identity domain events to send customer notifications."""

    @handle(CustomerRegistered)
    def on_customer_registered(self, event: CustomerRegistered) -> None:
        """Send welcome email when a new customer registers."""
        create_notifications_for_customer(
            customer_id=str(event.customer_id),
            notification_type=NotificationType.WELCOME.value,
            context={
                "first_name": event.first_name,
                "last_name": event.last_name,
                "email": event.email,
            },
            source_event_type="Identity.CustomerRegistered.v1",
        )
