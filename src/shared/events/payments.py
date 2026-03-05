"""Cross-domain event contracts for Payments domain events.

These classes define the event shape for consumption by other domains
(e.g., the OrderCheckoutSaga in the ordering domain). They are registered
as external events via domain.register_external_event() with matching
__type__ strings so Protean's stream deserialization works correctly.

The source-of-truth events are in src/payments/payment/events.py.
"""

from protean.core.event import BaseEvent
from protean.fields import Boolean, DateTime, Float, Identifier, Integer, String


class PaymentSucceeded(BaseEvent):
    """Payment was successfully captured by the gateway."""

    __version__ = "v1"

    payment_id = Identifier(required=True)
    order_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    amount = Float(required=True)
    currency = String(required=True)
    gateway_transaction_id = String(required=True)
    succeeded_at = DateTime(required=True)


class PaymentFailed(BaseEvent):
    """Payment processing failed at the gateway."""

    __version__ = "v1"

    payment_id = Identifier(required=True)
    order_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    reason = String(required=True)
    attempt_number = Integer(required=True)
    can_retry = Boolean(required=True)
    failed_at = DateTime(required=True)


class PaymentInitiated(BaseEvent):
    """A new payment was created for an order."""

    __version__ = "v1"

    payment_id = Identifier(required=True)
    order_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    amount = Float(required=True)
    currency = String(required=True)
    payment_method_type = String(required=True)
    last4 = String()
    gateway_name = String(required=True)
    idempotency_key = String(required=True)
    initiated_at = DateTime(required=True)


class PaymentProcessing(BaseEvent):
    """Payment was sent to the gateway for processing."""

    __version__ = "v1"

    payment_id = Identifier(required=True)
    order_id = Identifier(required=True)
    processing_at = DateTime(required=True)


class PaymentRetryInitiated(BaseEvent):
    """A failed payment is being retried."""

    __version__ = "v1"

    payment_id = Identifier(required=True)
    order_id = Identifier(required=True)
    attempt_number = Integer(required=True)
    retried_at = DateTime(required=True)


class RefundRequested(BaseEvent):
    """A refund was requested for a successful payment."""

    __version__ = "v1"

    payment_id = Identifier(required=True)
    refund_id = Identifier(required=True)
    order_id = Identifier(required=True)
    amount = Float(required=True)
    reason = String(required=True)
    requested_at = DateTime(required=True)


class RefundCompleted(BaseEvent):
    """A refund was completed by the payment gateway.

    Consumed by the Notifications domain to send refund confirmation emails.
    """

    __version__ = "v1"

    payment_id = Identifier(required=True)
    refund_id = Identifier(required=True)
    order_id = Identifier(required=True)
    customer_id = Identifier()
    amount = Float(required=True)
    gateway_refund_id = String(required=True)
    completed_at = DateTime(required=True)
    currency = String(default="USD")
    reason = String()
    completed_at = DateTime(required=True)
