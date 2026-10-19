"""Push notification channel port — abstract interface for push dispatch."""

from abc import ABC, abstractmethod
from typing import Any


class PushPort(ABC):
    """Abstract interface for push notification dispatch adapters."""

    @abstractmethod
    def send(
        self,
        device_token: str,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a push notification.

        Returns:
            dict with keys: message_id, status ("sent" or "failed"), error (optional)
        """
        ...
