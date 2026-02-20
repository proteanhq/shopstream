"""Stripe payment gateway adapter (production stub).

This is a placeholder for the real Stripe SDK integration.
In production, this would use the stripe-python SDK to:
- Create PaymentIntents
- Process refunds
- Verify webhook signatures using Stripe's signing secret
"""

from payments.gateway.port import ChargeResult, PaymentGateway, RefundResult


class StripeGateway(PaymentGateway):
    """Production Stripe gateway adapter. Not yet implemented."""

    def __init__(self, api_key: str, webhook_secret: str) -> None:
        self.api_key = api_key
        self.webhook_secret = webhook_secret

    def create_charge(
        self,
        amount: float,
        currency: str,
        payment_method_type: str,
        last4: str | None,
        idempotency_key: str,
    ) -> ChargeResult:
        raise NotImplementedError(
            "StripeGateway.create_charge() is not yet implemented. Integrate stripe-python SDK here."
        )

    def create_refund(
        self,
        gateway_transaction_id: str,
        amount: float,
        reason: str,
    ) -> RefundResult:
        raise NotImplementedError(
            "StripeGateway.create_refund() is not yet implemented. Integrate stripe-python SDK here."
        )

    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        raise NotImplementedError(
            "StripeGateway.verify_webhook_signature() is not yet implemented. "
            "Use stripe.Webhook.construct_event() here."
        )
