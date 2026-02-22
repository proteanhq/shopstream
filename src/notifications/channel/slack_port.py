"""Slack channel port — abstract interface for Slack dispatch."""

from abc import ABC, abstractmethod


class SlackPort(ABC):
    """Abstract interface for Slack dispatch adapters."""

    @abstractmethod
    def send(
        self,
        channel: str,
        message: str,
        blocks: list | None = None,
    ) -> dict:
        """Send a Slack message.

        Returns:
            dict with keys: message_id, status ("sent" or "failed"), error (optional)
        """
        ...
