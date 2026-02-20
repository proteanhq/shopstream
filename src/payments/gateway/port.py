"""Payment gateway port (abstract interface).

Defines the contract that all payment gateway adapters must implement.
This enables swapping between FakeGateway (dev/test) and StripeGateway
(production) without changing any domain or application code.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ChargeResult:
    """Result of a payment charge attempt."""

    success: bool
    gateway_transaction_id: str | None = None
    gateway_status: str | None = None
    gateway_response: str | None = None
    failure_reason: str | None = None


@dataclass(frozen=True)
class RefundResult:
    """Result of a refund attempt."""

    success: bool
    gateway_refund_id: str | None = None
    gateway_status: str | None = None
    failure_reason: str | None = None


class PaymentGateway(ABC):
    """Abstract payment gateway interface."""

    @abstractmethod
    def create_charge(
        self,
        amount: float,
        currency: str,
        payment_method_type: str,
        last4: str | None,
        idempotency_key: str,
    ) -> ChargeResult:
        """Create a charge via the payment gateway."""
        ...

    @abstractmethod
    def create_refund(
        self,
        gateway_transaction_id: str,
        amount: float,
        reason: str,
    ) -> RefundResult:
        """Refund a previous charge."""
        ...

    @abstractmethod
    def verify_webhook_signature(
        self,
        payload: str,
        signature: str,
    ) -> bool:
        """Verify that a webhook payload is authentically from the gateway."""
        ...
