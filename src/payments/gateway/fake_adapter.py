"""Configurable fake payment gateway for development and testing.

This adapter simulates a real payment gateway without any external calls.
It can be configured at runtime to succeed or fail, making it useful for:
- Manual API testing via /payments/gateway/configure
- Automated tests with predictable outcomes
- Development without real gateway credentials

Follows the same pattern as Stripe's test mode (test API keys + test card
numbers) but simplified for a learning/demo platform.
"""

from uuid import uuid4

from payments.gateway.port import ChargeResult, PaymentGateway, RefundResult


class FakeGateway(PaymentGateway):
    """Configurable fake payment gateway."""

    def __init__(self) -> None:
        self.should_succeed: bool = True
        self.failure_reason: str = "Card declined"
        self.calls: list[dict] = []

    def configure(self, should_succeed: bool, failure_reason: str = "Card declined") -> None:
        """Configure gateway behavior at runtime."""
        self.should_succeed = should_succeed
        self.failure_reason = failure_reason

    def create_charge(
        self,
        amount: float,
        currency: str,
        payment_method_type: str,
        last4: str | None,
        idempotency_key: str,
    ) -> ChargeResult:
        call = {
            "method": "create_charge",
            "amount": amount,
            "currency": currency,
            "payment_method_type": payment_method_type,
            "last4": last4,
            "idempotency_key": idempotency_key,
        }
        self.calls.append(call)

        if self.should_succeed:
            return ChargeResult(
                success=True,
                gateway_transaction_id=f"fake_txn_{uuid4().hex[:12]}",
                gateway_status="succeeded",
                gateway_response="Charge successful",
            )
        return ChargeResult(
            success=False,
            gateway_status="failed",
            failure_reason=self.failure_reason,
        )

    def create_refund(
        self,
        gateway_transaction_id: str,
        amount: float,
        reason: str,
    ) -> RefundResult:
        call = {
            "method": "create_refund",
            "gateway_transaction_id": gateway_transaction_id,
            "amount": amount,
            "reason": reason,
        }
        self.calls.append(call)

        if self.should_succeed:
            return RefundResult(
                success=True,
                gateway_refund_id=f"fake_ref_{uuid4().hex[:12]}",
                gateway_status="succeeded",
            )
        return RefundResult(
            success=False,
            failure_reason=self.failure_reason,
        )

    def verify_webhook_signature(self, payload: str, signature: str) -> bool:  # noqa: ARG002
        return signature == "test-signature"
