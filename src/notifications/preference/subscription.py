"""Subscription management commands + handlers — unsubscribe/resubscribe."""

from notifications.domain import notifications
from notifications.preference.preference import NotificationPreference
from protean.fields import Identifier, String
from protean.utils.globals import current_domain
from protean.utils.mixins import handle


@notifications.command(part_of="NotificationPreference")
class UnsubscribeFromType:
    """Unsubscribe a customer from a specific notification type."""

    customer_id: Identifier(required=True)
    notification_type: String(required=True, max_length=100)


@notifications.command(part_of="NotificationPreference")
class ResubscribeToType:
    """Resubscribe a customer to a previously unsubscribed notification type."""

    customer_id: Identifier(required=True)
    notification_type: String(required=True, max_length=100)


@notifications.command_handler(part_of=NotificationPreference)
class ManageSubscriptionsHandler:
    @handle(UnsubscribeFromType)
    def unsubscribe(self, command: UnsubscribeFromType):
        repo = current_domain.repository_for(NotificationPreference)
        prefs = repo._dao.query.filter(customer_id=str(command.customer_id)).all().items
        preference = prefs[0]
        preference.unsubscribe_from(command.notification_type)
        repo.add(preference)

    @handle(ResubscribeToType)
    def resubscribe(self, command: ResubscribeToType):
        repo = current_domain.repository_for(NotificationPreference)
        prefs = repo._dao.query.filter(customer_id=str(command.customer_id)).all().items
        preference = prefs[0]
        preference.resubscribe_to(command.notification_type)
        repo.add(preference)
