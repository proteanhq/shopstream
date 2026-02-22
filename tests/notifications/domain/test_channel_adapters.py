"""Tests for channel adapters — fake adapters for testing."""

import pytest
from notifications.channel import get_channel, reset_channels
from notifications.channel.fake_email import FakeEmailAdapter
from notifications.channel.fake_push import FakePushAdapter
from notifications.channel.fake_slack import FakeSlackAdapter
from notifications.channel.fake_sms import FakeSMSAdapter
from notifications.notification.notification import NotificationChannel


class TestFakeEmailAdapter:
    def setup_method(self):
        self.adapter = FakeEmailAdapter()

    def test_send_records_email(self):
        result = self.adapter.send(to="test@example.com", subject="Hi", body="Hello!")
        assert result["status"] == "sent"
        assert result["message_id"] is not None
        assert len(self.adapter.sent_emails) == 1
        assert self.adapter.sent_emails[0]["to"] == "test@example.com"

    def test_send_with_html_body(self):
        self.adapter.send(to="a@b.com", subject="Hi", body="Hi", html_body="<b>Hi</b>")
        assert self.adapter.sent_emails[0]["html_body"] == "<b>Hi</b>"

    def test_send_failure(self):
        self.adapter.configure(should_succeed=False, failure_reason="SMTP error")
        result = self.adapter.send(to="a@b.com", subject="Hi", body="Hello")
        assert result["status"] == "failed"
        assert result["error"] == "SMTP error"
        assert len(self.adapter.sent_emails) == 0

    def test_reset(self):
        self.adapter.send(to="a@b.com", subject="Hi", body="Hello")
        self.adapter.configure(should_succeed=False)
        self.adapter.reset()
        assert len(self.adapter.sent_emails) == 0
        assert self.adapter.should_succeed is True


class TestFakeSMSAdapter:
    def setup_method(self):
        self.adapter = FakeSMSAdapter()

    def test_send_records_message(self):
        result = self.adapter.send(to="+15551234567", body="Your order shipped!")
        assert result["status"] == "sent"
        assert len(self.adapter.sent_messages) == 1
        assert self.adapter.sent_messages[0]["to"] == "+15551234567"

    def test_send_failure(self):
        self.adapter.configure(should_succeed=False)
        result = self.adapter.send(to="+15551234567", body="Hello")
        assert result["status"] == "failed"

    def test_reset(self):
        self.adapter.send(to="+1555", body="Hi")
        self.adapter.reset()
        assert len(self.adapter.sent_messages) == 0


class TestFakePushAdapter:
    def setup_method(self):
        self.adapter = FakePushAdapter()

    def test_send_records_push(self):
        result = self.adapter.send(device_token="abc123", title="New order", body="Order confirmed")
        assert result["status"] == "sent"
        assert len(self.adapter.sent_pushes) == 1
        assert self.adapter.sent_pushes[0]["device_token"] == "abc123"

    def test_send_with_data(self):
        self.adapter.send(device_token="abc", title="Hi", body="Hello", data={"order_id": "123"})
        assert self.adapter.sent_pushes[0]["data"] == {"order_id": "123"}

    def test_send_failure(self):
        self.adapter.configure(should_succeed=False)
        result = self.adapter.send(device_token="abc", title="Hi", body="Hello")
        assert result["status"] == "failed"

    def test_reset(self):
        self.adapter.send(device_token="abc", title="Hi", body="Hello")
        self.adapter.reset()
        assert len(self.adapter.sent_pushes) == 0


class TestFakeSlackAdapter:
    def setup_method(self):
        self.adapter = FakeSlackAdapter()

    def test_send_records_message(self):
        result = self.adapter.send(channel="#operations", message="Low stock alert!")
        assert result["status"] == "sent"
        assert len(self.adapter.sent_messages) == 1
        assert self.adapter.sent_messages[0]["channel"] == "#operations"

    def test_send_with_blocks(self):
        blocks = [{"type": "section", "text": {"type": "plain_text", "text": "Hello"}}]
        self.adapter.send(channel="#alerts", message="Hi", blocks=blocks)
        assert self.adapter.sent_messages[0]["blocks"] == blocks

    def test_send_failure(self):
        self.adapter.configure(should_succeed=False)
        result = self.adapter.send(channel="#ops", message="Hi")
        assert result["status"] == "failed"

    def test_reset(self):
        self.adapter.send(channel="#ops", message="Hi")
        self.adapter.reset()
        assert len(self.adapter.sent_messages) == 0


# ---------------------------------------------------------------
# Channel registry
# ---------------------------------------------------------------
class TestChannelRegistry:
    def setup_method(self):
        reset_channels()

    def teardown_method(self):
        reset_channels()

    def test_get_email_channel(self):
        adapter = get_channel(NotificationChannel.EMAIL.value)
        assert isinstance(adapter, FakeEmailAdapter)

    def test_get_sms_channel(self):
        adapter = get_channel(NotificationChannel.SMS.value)
        assert isinstance(adapter, FakeSMSAdapter)

    def test_get_push_channel(self):
        adapter = get_channel(NotificationChannel.PUSH.value)
        assert isinstance(adapter, FakePushAdapter)

    def test_get_slack_channel(self):
        adapter = get_channel(NotificationChannel.SLACK.value)
        assert isinstance(adapter, FakeSlackAdapter)

    def test_get_channel_returns_singleton(self):
        a1 = get_channel(NotificationChannel.EMAIL.value)
        a2 = get_channel(NotificationChannel.EMAIL.value)
        assert a1 is a2

    def test_get_unknown_channel_raises(self):
        with pytest.raises(ValueError, match="Unknown channel type"):
            get_channel("Pigeon")

    def test_reset_channels_clears_singletons(self):
        a1 = get_channel(NotificationChannel.EMAIL.value)
        reset_channels()
        a2 = get_channel(NotificationChannel.EMAIL.value)
        assert a1 is not a2
