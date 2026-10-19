"""Carrier adapter abstraction — pluggable shipping carrier integration."""

import os

from fulfillment.carrier.port import CarrierPort

_carrier_instance: CarrierPort | None = None


def get_carrier() -> CarrierPort:
    """Return the configured carrier adapter (singleton).

    Uses FakeCarrier by default. In production, configure via
    CARRIER_ADAPTER environment variable.
    """
    global _carrier_instance
    if _carrier_instance is None:
        adapter = os.environ.get("CARRIER_ADAPTER", "fake")
        if adapter == "fake":
            from fulfillment.carrier.fake_adapter import FakeCarrier

            _carrier_instance = FakeCarrier()
        else:
            raise ValueError(f"Unknown carrier adapter: {adapter}")
    return _carrier_instance


def reset_carrier() -> None:
    """Reset the carrier singleton (useful for testing)."""
    global _carrier_instance
    _carrier_instance = None
