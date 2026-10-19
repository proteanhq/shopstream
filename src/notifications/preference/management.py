"""Preference management commands + handlers — update channels and quiet hours."""

import logging

from protean.core.repository import BaseRepository
from protean.fields import Boolean, Identifier, String
from protean.utils.globals import current_domain
from protean.utils.mixins import handle

from notifications.domain import notifications
from notifications.preference.preference import NotificationPreference

logger = logging.getLogger(__name__)


def _get_or_create_preference(repo: BaseRepository, customer_id: str) -> NotificationPreference:
    """Fetch preference for customer, creating default if not yet provisioned."""
    prefs = repo.query.filter(customer_id=customer_id).all().items
    if prefs:
        existing: NotificationPreference = prefs[0]
        return existing
    # Preference not yet created (race: command arrived before CustomerRegistered handler ran)
    preference = NotificationPreference.create_default(customer_id=customer_id)
    repo.add(preference)
    return preference


@notifications.command(part_of="NotificationPreference")
class UpdateNotificationPreferences:
    """Update a customer's notification channel preferences."""

    customer_id: str = Identifier(required=True)
    email_enabled: bool | None = Boolean()
    sms_enabled: bool | None = Boolean()
    push_enabled: bool | None = Boolean()


@notifications.command(part_of="NotificationPreference")
class SetQuietHours:
    """Set a customer's do-not-disturb window."""

    customer_id: str = Identifier(required=True)
    start: str = String(required=True, max_length=5)
    end: str = String(required=True, max_length=5)


@notifications.command(part_of="NotificationPreference")
class ClearQuietHours:
    """Remove a customer's do-not-disturb window."""

    customer_id: str = Identifier(required=True)


@notifications.command_handler(part_of=NotificationPreference)
class ManagePreferencesHandler:
    @handle(UpdateNotificationPreferences)
    def update_preferences(self, command: UpdateNotificationPreferences) -> None:
        repo = current_domain.repository_for(NotificationPreference)
        preference = _get_or_create_preference(repo, str(command.customer_id))
        preference.update_channels(
            email=command.email_enabled,
            sms=command.sms_enabled,
            push=command.push_enabled,
        )
        repo.add(preference)

    @handle(SetQuietHours)
    def set_quiet_hours(self, command: SetQuietHours) -> None:
        repo = current_domain.repository_for(NotificationPreference)
        preference = _get_or_create_preference(repo, str(command.customer_id))
        preference.set_quiet_hours(command.start, command.end)
        repo.add(preference)

    @handle(ClearQuietHours)
    def clear_quiet_hours(self, command: ClearQuietHours) -> None:
        repo = current_domain.repository_for(NotificationPreference)
        preference = _get_or_create_preference(repo, str(command.customer_id))
        preference.clear_quiet_hours()
        repo.add(preference)
