"""Inbound cross-domain event handler — Notifications reacts to Identity events.

Listens for CustomerRegistered to send welcome emails.
"""

import structlog
from protean.utils.mixins import handle

from notifications.domain import notifications
from notifications.notification.helpers import create_notifications_for_customer
from notifications.notification.notification import Notification, NotificationType
from shared.events.identity import (
    AccountClosed,
    AccountReactivated,
    AccountSuspended,
    AddressAdded,
    AddressRemoved,
    AddressUpdated,
    CustomerRegistered,
    DefaultAddressChanged,
    ProfileUpdated,
    TierUpgraded,
)

logger = structlog.get_logger(__name__)

notifications.register_external_event(CustomerRegistered, "Identity.CustomerRegistered.v1")
notifications.register_external_event(ProfileUpdated, "Identity.ProfileUpdated.v1")
notifications.register_external_event(AddressAdded, "Identity.AddressAdded.v1")
notifications.register_external_event(AddressUpdated, "Identity.AddressUpdated.v1")
notifications.register_external_event(AddressRemoved, "Identity.AddressRemoved.v1")
notifications.register_external_event(DefaultAddressChanged, "Identity.DefaultAddressChanged.v1")
notifications.register_external_event(AccountSuspended, "Identity.AccountSuspended.v1")
notifications.register_external_event(AccountReactivated, "Identity.AccountReactivated.v1")
notifications.register_external_event(AccountClosed, "Identity.AccountClosed.v1")
notifications.register_external_event(TierUpgraded, "Identity.TierUpgraded.v1")


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
