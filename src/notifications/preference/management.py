"""Preference management commands + handlers — update channels and quiet hours."""

from notifications.domain import notifications
from notifications.preference.preference import NotificationPreference
from protean.fields import Boolean, Identifier, String
from protean.utils.globals import current_domain
from protean.utils.mixins import handle


@notifications.command(part_of="NotificationPreference")
class UpdateNotificationPreferences:
    """Update a customer's notification channel preferences."""

    customer_id: Identifier(required=True)
    email_enabled: Boolean()
    sms_enabled: Boolean()
    push_enabled: Boolean()


@notifications.command(part_of="NotificationPreference")
class SetQuietHours:
    """Set a customer's do-not-disturb window."""

    customer_id: Identifier(required=True)
    start: String(required=True, max_length=5)
    end: String(required=True, max_length=5)


@notifications.command(part_of="NotificationPreference")
class ClearQuietHours:
    """Remove a customer's do-not-disturb window."""

    customer_id: Identifier(required=True)


@notifications.command_handler(part_of=NotificationPreference)
class ManagePreferencesHandler:
    @handle(UpdateNotificationPreferences)
    def update_preferences(self, command: UpdateNotificationPreferences):
        repo = current_domain.repository_for(NotificationPreference)
        prefs = repo._dao.query.filter(customer_id=str(command.customer_id)).all().items
        preference = prefs[0]
        preference.update_channels(
            email=command.email_enabled,
            sms=command.sms_enabled,
            push=command.push_enabled,
        )
        repo.add(preference)

    @handle(SetQuietHours)
    def set_quiet_hours(self, command: SetQuietHours):
        repo = current_domain.repository_for(NotificationPreference)
        prefs = repo._dao.query.filter(customer_id=str(command.customer_id)).all().items
        preference = prefs[0]
        preference.set_quiet_hours(command.start, command.end)
        repo.add(preference)

    @handle(ClearQuietHours)
    def clear_quiet_hours(self, command: ClearQuietHours):
        repo = current_domain.repository_for(NotificationPreference)
        prefs = repo._dao.query.filter(customer_id=str(command.customer_id)).all().items
        preference = prefs[0]
        preference.clear_quiet_hours()
        repo.add(preference)
