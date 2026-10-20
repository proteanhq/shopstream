"""Domain events for the Payment aggregate.

All events are versioned, immutable facts representing payment state changes.
Events are persisted to the event store and used for:
- Rebuilding aggregate state via @apply (event sourcing)
- Updating projections via projectors
- Cross-domain communication via Redis Streams (consumed by OrderCheckoutSaga)
"""

from datetime import datetime

from protean.fields import Boolean, DateTime, Float, Identifier, Integer, String

from payments.domain import payments


@payments.event(part_of="Payment")
class PaymentInitiated:
    """A new payment was created for an order."""

    payment_id: str = Identifier(required=True)
    order_id: str = Identifier(required=True)
    customer_id: str = Identifier(required=True)
    amount: float = Float(required=True)
    currency: str = String(required=True)
    payment_method_type: str = String(required=True)
    last4: str | None = String()
    gateway_name: str = String(required=True)
    idempotency_key: str = String(required=True)
    # Pre-generated identity for the first PaymentAttempt, carried on the event so
    # replay reconstructs the same child-entity id (deterministic event sourcing).
    attempt_id: str = Identifier(required=True)
    initiated_at: datetime = DateTime(required=True)


@payments.event(part_of="Payment")
class PaymentProcessing:
    """Payment was sent to the gateway for processing."""

    payment_id: str = Identifier(required=True)
    order_id: str = Identifier(required=True)
    processing_at: datetime = DateTime(required=True)


@payments.event(part_of="Payment", published=True)
class PaymentSucceeded:
    """Payment was successfully captured by the gateway."""

    payment_id: str = Identifier(required=True)
    order_id: str = Identifier(required=True)
    customer_id: str = Identifier(required=True)
    amount: float = Float(required=True)
    currency: str = String(required=True)
    gateway_transaction_id: str = String(required=True)
    succeeded_at: datetime = DateTime(required=True)


@payments.event(part_of="Payment", published=True)
class PaymentFailed:
    """Payment processing failed at the gateway."""

    payment_id: str = Identifier(required=True)
    order_id: str = Identifier(required=True)
    customer_id: str = Identifier(required=True)
    reason: str = String(required=True)
    attempt_number: int = Integer(required=True)
    can_retry: bool = Boolean(required=True)
    failed_at: datetime = DateTime(required=True)


@payments.event(part_of="Payment")
class PaymentRetryInitiated:
    """A failed payment is being retried."""

    payment_id: str = Identifier(required=True)
    order_id: str = Identifier(required=True)
    attempt_number: int = Integer(required=True)
    # Pre-generated identity for the retry's PaymentAttempt (see PaymentInitiated).
    attempt_id: str = Identifier(required=True)
    retried_at: datetime = DateTime(required=True)


@payments.event(part_of="Payment")
class RefundRequested:
    """A refund was requested for a successful payment."""

    payment_id: str = Identifier(required=True)
    refund_id: str = Identifier(required=True)
    order_id: str = Identifier(required=True)
    amount: float = Float(required=True)
    reason: str = String(required=True)
    requested_at: datetime = DateTime(required=True)


@payments.event(part_of="Payment", published=True)
class RefundCompleted:
    """A refund was completed by the gateway."""

    payment_id: str = Identifier(required=True)
    refund_id: str = Identifier(required=True)
    order_id: str = Identifier(required=True)
    customer_id: str = Identifier(required=True)
    amount: float = Float(required=True)
    gateway_refund_id: str = String(required=True)
    completed_at: datetime = DateTime(required=True)
