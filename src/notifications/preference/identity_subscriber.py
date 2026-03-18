"""Inbound cross-domain subscriber — Preferences reacts to Identity events.

Listens for CustomerRegistered to create default notification preferences.

Uses the subscriber (ACL) pattern: receives raw dict payloads from the global
broker, filters by event type, and translates into domain-local side effects.
No dependency on shared event classes or register_external_event.
"""

import structlog
from protean.utils.globals import current_domain

from notifications.domain import notifications
from notifications.preference.preference import NotificationPreference

logger = structlog.get_logger(__name__)


@notifications.subscriber(broker="global", stream="identity::customer")
class PreferenceIdentitySubscriber:
    """Creates default notification preferences when a customer registers.

    ACL pattern: receives raw broker message dict, extracts event type from
    metadata.headers.type, and creates preferences. Ignores all event
    types not relevant to preference management.
    """

    def __call__(self, payload: dict) -> None:
        event_type = payload.get("metadata", {}).get("headers", {}).get("type", "")
        data = payload.get("data", {})

        if "CustomerRegistered" in event_type:
            self._on_customer_registered(data)

    def _on_customer_registered(self, data: dict) -> None:
        """Create default notification preferences for the new customer."""
        customer_id = str(data["customer_id"])
        repo = current_domain.repository_for(NotificationPreference)

        # Check if preferences already exist (idempotency)
        try:
            existing = repo.query.filter(customer_id=customer_id).all().items
            if existing:
                logger.info(
                    "Preferences already exist for customer",
                    customer_id=customer_id,
                )
                return
        except Exception:
            pass

        preference = NotificationPreference.create_default(customer_id=customer_id)
        repo.add(preference)

        logger.info(
            "Default preferences created for new customer",
            customer_id=customer_id,
            preference_id=str(preference.id),
        )
