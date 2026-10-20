"""Fake SMS adapter — records sent messages for testing."""

from typing import Any
from uuid import uuid4

from notifications.channel.errors import ChannelUnavailableError
from notifications.channel.sms_port import SMSPort
from notifications.channel.transaction_guard import ensure_no_open_transaction


class FakeSMSAdapter(SMSPort):
    """SMS adapter that records messages in memory for test assertions."""

    def __init__(self) -> None:
        self.sent_messages: list[dict[str, Any]] = []
        self.should_succeed = True
        self.failure_reason = "SMS delivery failed"
        self.outage = False

    def configure(self, should_succeed: bool = True, failure_reason: str = "SMS delivery failed") -> None:
        """Configure the fake adapter behavior for testing."""
        self.should_succeed = should_succeed
        self.failure_reason = failure_reason

    def set_outage(self, outage: bool) -> None:
        """Make every send raise ``ChannelUnavailableError`` until switched off."""
        self.outage = outage

    def send(self, to: str, body: str) -> dict[str, Any]:
        ensure_no_open_transaction("SMS")
        if self.outage:
            raise ChannelUnavailableError("SMS provider unavailable")
        if not self.should_succeed:
            return {
                "message_id": None,
                "status": "failed",
                "error": self.failure_reason,
            }

        message_id = f"sms-{uuid4().hex[:12]}"
        record = {
            "message_id": message_id,
            "to": to,
            "body": body,
        }
        self.sent_messages.append(record)

        return {"message_id": message_id, "status": "sent"}

    def reset(self) -> None:
        """Clear sent messages (useful between tests)."""
        self.sent_messages.clear()
        self.should_succeed = True
        self.failure_reason = "SMS delivery failed"
        self.outage = False
