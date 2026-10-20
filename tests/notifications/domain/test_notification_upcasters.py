"""A v1 NotificationDispatchRequested still loads after the v2 change."""

from datetime import UTC, datetime

from protean.utils.eventing import Message

from notifications.notification.events import NotificationDispatchRequested
from notifications.notification.notification import Notification, NotificationChannel, NotificationType


def test_v1_dispatch_request_loads_as_v2():
    notification = Notification.create(
        recipient_id="cust-upcast",
        notification_type=NotificationType.WELCOME.value,
        channel=NotificationChannel.EMAIL.value,
        body="Welcome!",
    )
    request = next(e for e in notification._events if isinstance(e, NotificationDispatchRequested))
    raw = Message.from_domain_object(request).to_dict()
    raw["metadata"]["headers"]["type"] = raw["metadata"]["headers"]["type"].replace(".v2", ".v1")
    raw["data"].update(
        recipient_id="cust-upcast",
        channel=NotificationChannel.EMAIL.value,
        subject=None,
        body="Welcome!",
        requested_at=datetime.now(UTC).isoformat(),
    )
    # The edited payload no longer matches its checksum.
    message = Message.deserialize(raw, validate=False)

    loaded = message.to_domain_object()

    assert isinstance(loaded, NotificationDispatchRequested)
    assert str(loaded.notification_id) == str(notification.id)
    assert not hasattr(loaded, "channel")
