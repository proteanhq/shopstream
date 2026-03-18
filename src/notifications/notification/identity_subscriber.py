"""Inbound cross-domain subscriber — Notifications reacts to Identity events.

Listens for CustomerRegistered to send welcome emails.

Uses the subscriber (ACL) pattern: receives raw dict payloads from the global
broker, filters by event type, and translates into domain-local side effects.
No dependency on shared event classes or register_external_event.
"""

import structlog

from notifications.domain import notifications
from notifications.notification.helpers import create_notifications_for_customer
from notifications.notification.notification import NotificationType

logger = structlog.get_logger(__name__)


@notifications.subscriber(broker="global", stream="identity::customer")
class IdentityEventsSubscriber:
    """Reacts to Identity domain events to send customer notifications.

    ACL pattern: receives raw broker message dict, extracts event type from
    metadata.headers.type, and creates notifications. Ignores all event
    types not relevant to the Notifications domain.
    """

    def __call__(self, payload: dict) -> None:
        event_type = payload.get("metadata", {}).get("headers", {}).get("type", "")
        data = payload.get("data", {})

        if "CustomerRegistered" in event_type:
            self._on_customer_registered(data)

    def _on_customer_registered(self, data: dict) -> None:
        """Send welcome email when a new customer registers."""
        create_notifications_for_customer(
            customer_id=str(data["customer_id"]),
            notification_type=NotificationType.WELCOME.value,
            context={
                "first_name": data.get("first_name", ""),
                "last_name": data.get("last_name", ""),
                "email": data.get("email", ""),
            },
            source_event_type="Identity.CustomerRegistered.v1",
        )
