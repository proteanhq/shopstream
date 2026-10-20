"""Fake push notification adapter — records sent pushes for testing."""

from typing import Any
from uuid import uuid4

from notifications.channel.errors import ChannelUnavailableError
from notifications.channel.push_port import PushPort
from notifications.channel.transaction_guard import ensure_no_open_transaction


class FakePushAdapter(PushPort):
    """Push adapter that records notifications in memory for test assertions."""

    def __init__(self) -> None:
        self.sent_pushes: list[dict[str, Any]] = []
        self.should_succeed = True
        self.failure_reason = "Push delivery failed"
        self.outage = False

    def configure(self, should_succeed: bool = True, failure_reason: str = "Push delivery failed") -> None:
        """Configure the fake adapter behavior for testing."""
        self.should_succeed = should_succeed
        self.failure_reason = failure_reason

    def set_outage(self, outage: bool) -> None:
        """Make every send raise ``ChannelUnavailableError`` until switched off."""
        self.outage = outage

    def send(
        self,
        device_token: str,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ensure_no_open_transaction("Push")
        if self.outage:
            raise ChannelUnavailableError("Push provider unavailable")
        if not self.should_succeed:
            return {
                "message_id": None,
                "status": "failed",
                "error": self.failure_reason,
            }

        message_id = f"push-{uuid4().hex[:12]}"
        record = {
            "message_id": message_id,
            "device_token": device_token,
            "title": title,
            "body": body,
            "data": data,
        }
        self.sent_pushes.append(record)

        return {"message_id": message_id, "status": "sent"}

    def reset(self) -> None:
        """Clear sent pushes (useful between tests)."""
        self.sent_pushes.clear()
        self.should_succeed = True
        self.failure_reason = "Push delivery failed"
        self.outage = False
