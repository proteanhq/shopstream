"""Upcasters for Notification events."""

from typing import Any

from protean.core.upcaster import BaseUpcaster

from notifications.domain import notifications
from notifications.notification.events import NotificationDispatchRequested


@notifications.upcaster(event_type=NotificationDispatchRequested, from_version=1, to_version=2)
class UpcastNotificationDispatchRequestedV1ToV2(BaseUpcaster):
    """v1 carried the send payload; v2 drops it, since the claim loads the notification.

    A v1 request still in the outbox or a stream when v2 is deployed would
    otherwise fail to load, because events reject unknown fields.
    """

    def upcast(self, data: dict[str, Any]) -> dict[str, Any]:
        for field in ("recipient_id", "channel", "subject", "body"):
            data.pop(field, None)
        return data
