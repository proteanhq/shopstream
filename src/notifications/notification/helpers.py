"""Shared helpers for notification event handlers.

Provides the common pattern: look up preferences → filter channels →
render template → create Notification per channel.
"""

from datetime import datetime
from typing import Any

import structlog
from protean.utils.globals import current_domain

from notifications.notification.notification import (
    Notification,
    NotificationChannel,
    RecipientType,
)
from notifications.preference.preference import NotificationPreference
from notifications.templates import get_template
from shared.money import parse_money

logger = structlog.get_logger(__name__)


def two_places(amount: float | str | None) -> str:
    """Render a payload amount as ``49.99``, or ``""`` when it is missing.

    Payment and order events carry money as a number in their older versions
    and as a 4-place string in the newer ones. Notification text shows 2
    places either way.
    """
    if amount is None or amount == "":
        return ""
    return f"{parse_money(amount):.2f}"


def create_notifications_for_customer(
    customer_id: str,
    notification_type: str,
    context: dict[str, Any],
    source_event_type: str | None = None,
    source_event_id: str | None = None,
    scheduled_for: datetime | None = None,
) -> list[str]:
    """Create notification(s) for a customer based on their preferences.

    Looks up customer preferences, filters channels, renders template,
    and creates one Notification aggregate per enabled channel.

    Returns:
        List of notification IDs created.
    """
    template_cls = get_template(notification_type)
    rendered = template_cls.render(context)
    default_channels = template_cls.default_channels

    # Look up customer preferences
    pref_repo = current_domain.repository_for(NotificationPreference)
    try:
        prefs = pref_repo.query.filter(customer_id=customer_id).all().items
        pref = prefs[0] if prefs else None
    except Exception:
        pref = None

    # Determine enabled channels
    if pref:
        # Check if customer is subscribed to this notification type
        if not pref.is_subscribed_to(notification_type):
            logger.info(
                "Customer unsubscribed from notification type",
                customer_id=customer_id,
                notification_type=notification_type,
            )
            return []

        enabled = set(pref.get_enabled_channels())
        channels = [ch for ch in default_channels if ch in enabled]
    else:
        # No preferences yet — use only email (safe default)
        channels = [ch for ch in default_channels if ch == NotificationChannel.EMAIL.value]

    if not channels:
        logger.info(
            "No enabled channels for notification",
            customer_id=customer_id,
            notification_type=notification_type,
        )
        return []

    # Create one notification per channel
    notification_ids: list[str] = []
    repo = current_domain.repository_for(Notification)

    for channel in channels:
        notification = Notification.create(
            recipient_id=customer_id,
            notification_type=notification_type,
            channel=channel,
            subject=rendered.get("subject"),
            body=rendered["body"],
            recipient_type=RecipientType.CUSTOMER.value,
            template_name=template_cls.__name__,
            source_event_type=source_event_type,
            source_event_id=source_event_id,
            context_data=context,
            scheduled_for=scheduled_for,
        )
        repo.add(notification)
        notification_ids.append(str(notification.id))

    logger.info(
        "Notifications created",
        customer_id=customer_id,
        notification_type=notification_type,
        channels=channels,
        count=len(notification_ids),
    )

    return notification_ids


def create_internal_notification(
    notification_type: str,
    context: dict[str, Any],
    channel: str = NotificationChannel.SLACK.value,
    recipient_id: str = "operations",
    source_event_type: str | None = None,
    source_event_id: str | None = None,
) -> str:
    """Create an internal notification (e.g., Slack alert for ops).

    Internal notifications skip preference checks.

    Returns:
        Notification ID.
    """
    template_cls = get_template(notification_type)
    rendered = template_cls.render(context)

    repo = current_domain.repository_for(Notification)

    notification = Notification.create(
        recipient_id=recipient_id,
        notification_type=notification_type,
        channel=channel,
        subject=rendered.get("subject"),
        body=rendered["body"],
        recipient_type=RecipientType.INTERNAL.value,
        template_name=template_cls.__name__,
        source_event_type=source_event_type,
        source_event_id=source_event_id,
        context_data=context,
    )
    repo.add(notification)

    logger.info(
        "Internal notification created",
        notification_type=notification_type,
        channel=channel,
        notification_id=str(notification.id),
    )

    return str(notification.id)
