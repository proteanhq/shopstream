"""Channel adapter registry — pluggable notification dispatch channels.

Provides singleton access to channel adapters. Uses fake adapters
by default; real adapters (SendGrid, Twilio, FCM, Slack API) can
be configured via environment variables in production.
"""

from notifications.notification.notification import NotificationChannel

_channel_instances: dict[str, object] = {}


def get_channel(channel_type: str):
    """Return the configured channel adapter (singleton per channel type).

    Args:
        channel_type: One of NotificationChannel enum values ("Email", "SMS", "Push", "Slack")
    """
    if channel_type not in _channel_instances:
        if channel_type == NotificationChannel.EMAIL.value:
            from notifications.channel.fake_email import FakeEmailAdapter

            _channel_instances[channel_type] = FakeEmailAdapter()
        elif channel_type == NotificationChannel.SMS.value:
            from notifications.channel.fake_sms import FakeSMSAdapter

            _channel_instances[channel_type] = FakeSMSAdapter()
        elif channel_type == NotificationChannel.PUSH.value:
            from notifications.channel.fake_push import FakePushAdapter

            _channel_instances[channel_type] = FakePushAdapter()
        elif channel_type == NotificationChannel.SLACK.value:
            from notifications.channel.fake_slack import FakeSlackAdapter

            _channel_instances[channel_type] = FakeSlackAdapter()
        else:
            raise ValueError(f"Unknown channel type: {channel_type}")

    return _channel_instances[channel_type]


def reset_channels():
    """Reset all channel singletons (useful for testing)."""
    global _channel_instances
    _channel_instances.clear()
