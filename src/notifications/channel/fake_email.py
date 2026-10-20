"""Fake email adapter — records sent emails for testing."""

from typing import Any
from uuid import uuid4

from notifications.channel.email_port import EmailPort
from notifications.channel.errors import ChannelUnavailableError
from notifications.channel.transaction_guard import ensure_no_open_transaction


class FakeEmailAdapter(EmailPort):
    """Email adapter that records messages in memory for test assertions."""

    def __init__(self) -> None:
        self.sent_emails: list[dict[str, Any]] = []
        self.should_succeed = True
        self.failure_reason = "Email delivery failed"
        self.outage = False

    def configure(self, should_succeed: bool = True, failure_reason: str = "Email delivery failed") -> None:
        """Configure the fake adapter behavior for testing."""
        self.should_succeed = should_succeed
        self.failure_reason = failure_reason

    def set_outage(self, outage: bool) -> None:
        """Make every send raise ``ChannelUnavailableError`` until switched off."""
        self.outage = outage

    def send(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> dict[str, Any]:
        ensure_no_open_transaction("Email")
        if self.outage:
            raise ChannelUnavailableError("Email provider unavailable")
        if not self.should_succeed:
            return {
                "message_id": None,
                "status": "failed",
                "error": self.failure_reason,
            }

        message_id = f"email-{uuid4().hex[:12]}"
        record = {
            "message_id": message_id,
            "to": to,
            "subject": subject,
            "body": body,
            "html_body": html_body,
        }
        self.sent_emails.append(record)

        return {"message_id": message_id, "status": "sent"}

    def reset(self) -> None:
        """Clear sent emails (useful between tests)."""
        self.sent_emails.clear()
        self.should_succeed = True
        self.failure_reason = "Email delivery failed"
        self.outage = False
