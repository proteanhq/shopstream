"""SMS channel port — abstract interface for SMS dispatch."""

from abc import ABC, abstractmethod


class SMSPort(ABC):
    """Abstract interface for SMS dispatch adapters."""

    @abstractmethod
    def send(self, to: str, body: str) -> dict:
        """Send an SMS message.

        Returns:
            dict with keys: message_id, status ("sent" or "failed"), error (optional)
        """
        ...
