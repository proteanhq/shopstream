"""Email channel port — abstract interface for email dispatch."""

from abc import ABC, abstractmethod


class EmailPort(ABC):
    """Abstract interface for email dispatch adapters."""

    @abstractmethod
    def send(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> dict:
        """Send an email message.

        Returns:
            dict with keys: message_id, status ("sent" or "failed"), error (optional)
        """
        ...
