"""Fake Slack adapter — records sent messages for testing."""

from typing import Any
from uuid import uuid4

from notifications.channel.slack_port import SlackPort


class FakeSlackAdapter(SlackPort):
    """Slack adapter that records messages in memory for test assertions."""

    def __init__(self) -> None:
        self.sent_messages: list[dict[str, Any]] = []
        self.should_succeed = True
        self.failure_reason = "Slack delivery failed"

    def configure(self, should_succeed: bool = True, failure_reason: str = "Slack delivery failed") -> None:
        """Configure the fake adapter behavior for testing."""
        self.should_succeed = should_succeed
        self.failure_reason = failure_reason

    def send(
        self,
        channel: str,
        message: str,
        blocks: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if not self.should_succeed:
            return {
                "message_id": None,
                "status": "failed",
                "error": self.failure_reason,
            }

        message_id = f"slack-{uuid4().hex[:12]}"
        record = {
            "message_id": message_id,
            "channel": channel,
            "message": message,
            "blocks": blocks,
        }
        self.sent_messages.append(record)

        return {"message_id": message_id, "status": "sent"}

    def reset(self) -> None:
        """Clear sent messages (useful between tests)."""
        self.sent_messages.clear()
        self.should_succeed = True
        self.failure_reason = "Slack delivery failed"
