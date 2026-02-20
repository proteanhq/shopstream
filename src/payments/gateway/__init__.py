"""Payment gateway factory.

Provides get_gateway() / set_gateway() to swap implementations:
- FakeGateway for development and testing
- StripeGateway for production (stub)
"""

from payments.gateway.fake_adapter import FakeGateway
from payments.gateway.port import PaymentGateway

_current_gateway: PaymentGateway | None = None


def get_gateway() -> PaymentGateway:
    """Return the current payment gateway. Defaults to FakeGateway."""
    global _current_gateway
    if _current_gateway is None:
        _current_gateway = FakeGateway()
    return _current_gateway


def set_gateway(gateway: PaymentGateway) -> None:
    """Override the active payment gateway (useful for tests)."""
    global _current_gateway
    _current_gateway = gateway


def reset_gateway() -> None:
    """Reset to default gateway."""
    global _current_gateway
    _current_gateway = None
