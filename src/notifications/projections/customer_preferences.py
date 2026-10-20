"""Customer preferences — read model for notification channel preferences."""

from datetime import datetime

from protean.core.projector import on
from protean.fields import Boolean, DateTime, Identifier, List, String
from protean.utils.globals import current_domain

from notifications.domain import notifications
from notifications.preference.events import (
    ChannelsUpdated,
    PreferencesCreated,
    QuietHoursCleared,
    QuietHoursSet,
    TypeResubscribed,
    TypeUnsubscribed,
)
from notifications.preference.preference import NotificationPreference


@notifications.projection
class CustomerPreferences:
    preference_id: str = Identifier(identifier=True, required=True)
    customer_id: str = Identifier(required=True)
    email_enabled: bool = Boolean(default=True)
    sms_enabled: bool = Boolean(default=False)
    push_enabled: bool = Boolean(default=False)
    quiet_hours_start: str | None = String()
    quiet_hours_end: str | None = String()
    unsubscribed_types: list[str] = List(String())
    created_at: datetime | None = DateTime()
    updated_at: datetime | None = DateTime()


@notifications.projector(projector_for=CustomerPreferences, aggregates=[NotificationPreference])
class CustomerPreferencesProjector:
    @on(PreferencesCreated)
    def on_preferences_created(self, event: PreferencesCreated) -> None:
        current_domain.repository_for(CustomerPreferences).add(
            CustomerPreferences(
                preference_id=event.preference_id,
                customer_id=event.customer_id,
                email_enabled=event.email_enabled,
                sms_enabled=event.sms_enabled,
                push_enabled=event.push_enabled,
                unsubscribed_types=[],
                created_at=event.created_at,
                updated_at=event.created_at,
            )
        )

    @on(ChannelsUpdated)
    def on_channels_updated(self, event: ChannelsUpdated) -> None:
        repo = current_domain.repository_for(CustomerPreferences)
        view = repo.get(event.preference_id)
        view.email_enabled = event.email_enabled
        view.sms_enabled = event.sms_enabled
        view.push_enabled = event.push_enabled
        view.updated_at = event.updated_at
        repo.add(view)

    @on(QuietHoursSet)
    def on_quiet_hours_set(self, event: QuietHoursSet) -> None:
        repo = current_domain.repository_for(CustomerPreferences)
        view = repo.get(event.preference_id)
        view.quiet_hours_start = event.start
        view.quiet_hours_end = event.end
        view.updated_at = event.updated_at
        repo.add(view)

    @on(QuietHoursCleared)
    def on_quiet_hours_cleared(self, event: QuietHoursCleared) -> None:
        repo = current_domain.repository_for(CustomerPreferences)
        view = repo.get(event.preference_id)
        view.quiet_hours_start = None
        view.quiet_hours_end = None
        view.updated_at = event.cleared_at
        repo.add(view)

    @on(TypeUnsubscribed)
    def on_type_unsubscribed(self, event: TypeUnsubscribed) -> None:
        repo = current_domain.repository_for(CustomerPreferences)
        view = repo.get(event.preference_id)
        types = list(view.unsubscribed_types or [])
        if event.notification_type not in types:
            types.append(event.notification_type)
        view.unsubscribed_types = types
        view.updated_at = event.unsubscribed_at
        repo.add(view)

    @on(TypeResubscribed)
    def on_type_resubscribed(self, event: TypeResubscribed) -> None:
        repo = current_domain.repository_for(CustomerPreferences)
        view = repo.get(event.preference_id)
        types = list(view.unsubscribed_types or [])
        if event.notification_type in types:
            types.remove(event.notification_type)
        view.unsubscribed_types = types
        view.updated_at = event.resubscribed_at
        repo.add(view)
