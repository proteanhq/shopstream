"""Inbound cross-domain event handler — Preferences reacts to Identity events.

Listens for CustomerRegistered to create default notification preferences.
"""

import structlog
from notifications.domain import notifications
from notifications.preference.preference import NotificationPreference
from protean.utils.globals import current_domain
from protean.utils.mixins import handle
from shared.events.identity import CustomerRegistered

logger = structlog.get_logger(__name__)

# Note: The external event is already registered in notification/identity_events.py.
# Protean allows multiple handlers on the same stream; we don't re-register.
# However, we do need to register it here as well since this is a separate
# handler class attached to a different aggregate.
notifications.register_external_event(CustomerRegistered, "Identity.CustomerRegistered.v1")


@notifications.event_handler(part_of=NotificationPreference, stream_category="identity::customer")
class PreferenceIdentityEventsHandler:
    """Creates default notification preferences when a customer registers."""

    @handle(CustomerRegistered)
    def on_customer_registered(self, event: CustomerRegistered) -> None:
        """Create default notification preferences for the new customer."""
        repo = current_domain.repository_for(NotificationPreference)

        # Check if preferences already exist (idempotency)
        try:
            existing = repo._dao.query.filter(customer_id=str(event.customer_id)).all().items
            if existing:
                logger.info(
                    "Preferences already exist for customer",
                    customer_id=str(event.customer_id),
                )
                return
        except Exception:
            pass

        preference = NotificationPreference.create_default(customer_id=str(event.customer_id))
        repo.add(preference)

        logger.info(
            "Default preferences created for new customer",
            customer_id=str(event.customer_id),
            preference_id=str(preference.id),
        )
