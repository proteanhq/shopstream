"""Carrier port — abstract interface for shipping carrier integrations.

All carrier adapters must implement this interface. The domain code
programs against the port; adapters are swapped via configuration.
"""

from abc import ABC, abstractmethod


class CarrierPort(ABC):
    """Abstract interface for carrier adapters."""

    @abstractmethod
    def create_shipment(
        self,
        order_id: str,
        carrier: str,
        service_level: str,
        weight: float | None = None,
        dimensions: dict | None = None,
    ) -> dict:
        """Create a shipment with the carrier.

        Returns:
            dict with keys: shipment_id, tracking_number, label_url, estimated_delivery
        """
        ...

    @abstractmethod
    def get_tracking(self, tracking_number: str) -> dict:
        """Get current tracking status for a shipment.

        Returns:
            dict with keys: status, location, events (list of tracking events)
        """
        ...

    @abstractmethod
    def cancel_shipment(self, tracking_number: str) -> dict:
        """Cancel a shipment with the carrier.

        Returns:
            dict with keys: cancelled (bool), reason (str)
        """
        ...

    @abstractmethod
    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """Verify that a webhook callback is authentic.

        Returns:
            True if the signature is valid, False otherwise.
        """
        ...
