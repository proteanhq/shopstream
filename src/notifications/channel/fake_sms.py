"""Fake SMS adapter — records sent messages for testing."""

from uuid import uuid4

from notifications.channel.sms_port import SMSPort


class FakeSMSAdapter(SMSPort):
    """SMS adapter that records messages in memory for test assertions."""

    def __init__(self):
        self.sent_messages: list[dict] = []
        self.should_succeed = True
        self.failure_reason = "SMS delivery failed"

    def configure(self, should_succeed: bool = True, failure_reason: str = "SMS delivery failed"):
        """Configure the fake adapter behavior for testing."""
        self.should_succeed = should_succeed
        self.failure_reason = failure_reason

    def send(self, to: str, body: str) -> dict:
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

    def reset(self):
        """Clear sent messages (useful between tests)."""
        self.sent_messages.clear()
        self.should_succeed = True
        self.failure_reason = "SMS delivery failed"
