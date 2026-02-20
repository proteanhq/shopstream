"""Payment aggregate (Event Sourced) — the core of the payments domain.

The Payment aggregate uses event sourcing: all state changes are captured as
domain events, and the current state is rebuilt by replaying events via
@apply decorators. This provides a complete audit trail of every charge
attempt, gateway interaction, and refund — critical for financial systems.

State Machine:
    PENDING → PROCESSING → SUCCEEDED → REFUNDED/PARTIALLY_REFUNDED
    PROCESSING → FAILED → PENDING (retry, max 3 attempts)

Refund sub-flow:
    REFUND_REQUESTED → REFUND_PROCESSING → REFUND_COMPLETED/REFUND_FAILED
"""

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from protean import apply
from protean.exceptions import ValidationError
from protean.fields import (
    DateTime,
    Float,
    HasMany,
    Identifier,
    Integer,
    String,
    ValueObject,
)

from payments.domain import payments
from payments.payment.events import (
    PaymentFailed,
    PaymentInitiated,
    PaymentRetryInitiated,
    PaymentSucceeded,
    RefundCompleted,
    RefundRequested,
)

MAX_PAYMENT_ATTEMPTS = 3


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class PaymentStatus(Enum):
    PENDING = "Pending"
    PROCESSING = "Processing"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    REFUNDED = "Refunded"
    PARTIALLY_REFUNDED = "Partially_Refunded"


class RefundStatus(Enum):
    REQUESTED = "Requested"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    FAILED = "Failed"


_VALID_TRANSITIONS = {
    PaymentStatus.PENDING: {PaymentStatus.PROCESSING, PaymentStatus.SUCCEEDED, PaymentStatus.FAILED},
    PaymentStatus.PROCESSING: {PaymentStatus.SUCCEEDED, PaymentStatus.FAILED},
    PaymentStatus.FAILED: {PaymentStatus.PENDING},  # retry
    PaymentStatus.SUCCEEDED: {PaymentStatus.REFUNDED, PaymentStatus.PARTIALLY_REFUNDED},
    PaymentStatus.REFUNDED: set(),  # Terminal
    PaymentStatus.PARTIALLY_REFUNDED: {PaymentStatus.REFUNDED},
}


# ---------------------------------------------------------------------------
# Value Objects
# ---------------------------------------------------------------------------
@payments.value_object(part_of="Payment")
class Money:
    """Monetary amount with currency."""

    currency = String(max_length=3, default="USD")
    value = Float(default=0.0)


@payments.value_object(part_of="Payment")
class PaymentMethod:
    """Payment method details captured at initiation time."""

    method_type = String(max_length=50)  # credit_card, debit_card, bank_transfer
    last4 = String(max_length=4)
    expiry_month = Integer()
    expiry_year = Integer()


@payments.value_object(part_of="Payment")
class GatewayInfo:
    """Gateway-specific information about the payment."""

    gateway_name = String(max_length=50)
    gateway_transaction_id = String(max_length=255)
    gateway_status = String(max_length=50)
    gateway_response = String(max_length=1000)


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------
@payments.entity(part_of="Payment")
class PaymentAttempt:
    """A record of a single payment processing attempt."""

    attempted_at = DateTime(required=True)
    status = String(max_length=50, required=True)  # processing, succeeded, failed
    failure_reason = String(max_length=500)
    gateway_transaction_id = String(max_length=255)


@payments.entity(part_of="Payment")
class Refund:
    """A refund against this payment."""

    amount = Float(required=True)
    reason = String(max_length=500, required=True)
    status = String(
        max_length=50,
        choices=RefundStatus,
        default=RefundStatus.REQUESTED.value,
    )
    requested_at = DateTime(required=True)
    processed_at = DateTime()
    gateway_refund_id = String(max_length=255)


# ---------------------------------------------------------------------------
# Aggregate Root (Event Sourced)
# ---------------------------------------------------------------------------
@payments.aggregate(is_event_sourced=True)
class Payment:
    order_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    amount = ValueObject(Money)
    status = String(
        choices=PaymentStatus,
        default=PaymentStatus.PENDING.value,
    )
    payment_method = ValueObject(PaymentMethod)
    gateway_info = ValueObject(GatewayInfo)
    attempts = HasMany(PaymentAttempt)
    refunds = HasMany(Refund)
    attempt_count = Integer(default=0)
    total_refunded = Float(default=0.0)
    idempotency_key = String(max_length=255, required=True)
    created_at = DateTime()
    updated_at = DateTime()

    # -------------------------------------------------------------------
    # Factory method
    # -------------------------------------------------------------------
    @classmethod
    def create(
        cls,
        order_id: str,
        customer_id: str,
        amount: float,
        currency: str,
        payment_method_type: str,
        last4: str | None,
        gateway_name: str,
        idempotency_key: str,
    ):
        """Create a new payment for an order.

        Uses _create_new() for event-sourced aggregates. All state is set
        via the PaymentInitiated event's @apply handler.
        """
        now = datetime.now(UTC)
        payment = cls._create_new()
        payment.raise_(
            PaymentInitiated(
                payment_id=str(payment.id),
                order_id=order_id,
                customer_id=customer_id,
                amount=amount,
                currency=currency,
                payment_method_type=payment_method_type,
                last4=last4 or "",
                gateway_name=gateway_name,
                idempotency_key=idempotency_key,
                initiated_at=now,
            )
        )
        return payment

    # -------------------------------------------------------------------
    # State transition helper
    # -------------------------------------------------------------------
    def _assert_can_transition(self, target_status: PaymentStatus) -> None:
        current = PaymentStatus(self.status)
        if target_status not in _VALID_TRANSITIONS.get(current, set()):
            raise ValidationError({"status": [f"Cannot transition from {current.value} to {target_status.value}"]})

    # -------------------------------------------------------------------
    # Payment lifecycle
    # -------------------------------------------------------------------
    def record_processing(self) -> None:
        """Record that the payment is being processed by the gateway."""
        self._assert_can_transition(PaymentStatus.PROCESSING)
        # State mutation happens in @apply — no explicit state changes here
        # This is a live-path convenience; the event drives state

    def record_success(self, gateway_transaction_id: str) -> None:
        """Record successful payment capture from gateway webhook."""
        self._assert_can_transition(PaymentStatus.SUCCEEDED)
        now = datetime.now(UTC)
        self.raise_(
            PaymentSucceeded(
                payment_id=str(self.id),
                order_id=str(self.order_id),
                customer_id=str(self.customer_id),
                amount=self.amount.value,
                currency=self.amount.currency,
                gateway_transaction_id=gateway_transaction_id,
                succeeded_at=now,
            )
        )

    def record_failure(self, reason: str) -> None:
        """Record payment failure from gateway webhook."""
        self._assert_can_transition(PaymentStatus.FAILED)
        now = datetime.now(UTC)
        can_retry = self.attempt_count < MAX_PAYMENT_ATTEMPTS
        self.raise_(
            PaymentFailed(
                payment_id=str(self.id),
                order_id=str(self.order_id),
                customer_id=str(self.customer_id),
                reason=reason,
                attempt_number=self.attempt_count,
                can_retry=can_retry,
                failed_at=now,
            )
        )

    def can_retry(self) -> bool:
        """Check if the payment can be retried."""
        return PaymentStatus(self.status) == PaymentStatus.FAILED and self.attempt_count < MAX_PAYMENT_ATTEMPTS

    def retry(self) -> None:
        """Retry a failed payment."""
        if not self.can_retry():
            if self.attempt_count >= MAX_PAYMENT_ATTEMPTS:
                raise ValidationError({"attempts": [f"Maximum retry attempts ({MAX_PAYMENT_ATTEMPTS}) exceeded"]})
            raise ValidationError({"status": ["Payment can only be retried from Failed state"]})

        self._assert_can_transition(PaymentStatus.PENDING)
        now = datetime.now(UTC)
        self.raise_(
            PaymentRetryInitiated(
                payment_id=str(self.id),
                order_id=str(self.order_id),
                attempt_number=self.attempt_count + 1,
                retried_at=now,
            )
        )

    # -------------------------------------------------------------------
    # Refunds
    # -------------------------------------------------------------------
    def request_refund(self, amount: float, reason: str) -> str:
        """Request a refund for this payment.

        Returns the refund_id for tracking.
        """
        if PaymentStatus(self.status) not in (
            PaymentStatus.SUCCEEDED,
            PaymentStatus.PARTIALLY_REFUNDED,
        ):
            raise ValidationError(
                {"status": ["Refunds can only be requested for succeeded or partially refunded payments"]}
            )

        if self.total_refunded + amount > self.amount.value:
            raise ValidationError(
                {
                    "amount": [
                        f"Refund total ({self.total_refunded + amount}) would exceed payment amount ({self.amount.value})"
                    ]
                }
            )

        now = datetime.now(UTC)
        refund_id = str(uuid4())
        self.raise_(
            RefundRequested(
                payment_id=str(self.id),
                refund_id=refund_id,
                order_id=str(self.order_id),
                amount=amount,
                reason=reason,
                requested_at=now,
            )
        )
        return refund_id

    def complete_refund(self, refund_id: str, gateway_refund_id: str) -> None:
        """Complete a refund after gateway confirmation."""
        refund = next((r for r in (self.refunds or []) if str(r.id) == refund_id), None)
        if refund is None:
            raise ValidationError({"refund_id": ["Refund not found"]})
        if refund.status != RefundStatus.REQUESTED.value:
            raise ValidationError({"refund": ["Refund is not in Requested state"]})

        now = datetime.now(UTC)
        self.raise_(
            RefundCompleted(
                payment_id=str(self.id),
                refund_id=refund_id,
                order_id=str(self.order_id),
                amount=refund.amount,
                gateway_refund_id=gateway_refund_id,
                completed_at=now,
            )
        )

    # -------------------------------------------------------------------
    # @apply methods — rebuild state during event replay
    # -------------------------------------------------------------------
    @apply
    def _on_payment_initiated(self, event: PaymentInitiated):
        self.id = event.payment_id
        self.order_id = event.order_id
        self.customer_id = event.customer_id
        self.amount = Money(currency=event.currency, value=event.amount)
        self.status = PaymentStatus.PENDING.value
        self.payment_method = PaymentMethod(
            method_type=event.payment_method_type,
            last4=event.last4,
        )
        self.gateway_info = GatewayInfo(gateway_name=event.gateway_name)
        self.idempotency_key = event.idempotency_key
        self.attempt_count = 1
        self.total_refunded = 0.0
        self.created_at = event.initiated_at
        self.updated_at = event.initiated_at

        # Record first attempt
        self.add_attempts(
            PaymentAttempt(
                attempted_at=event.initiated_at,
                status="processing",
            )
        )

    @apply
    def _on_payment_succeeded(self, event: PaymentSucceeded):
        self.status = PaymentStatus.SUCCEEDED.value
        self.gateway_info = GatewayInfo(
            gateway_name=self.gateway_info.gateway_name if self.gateway_info else "",
            gateway_transaction_id=event.gateway_transaction_id,
            gateway_status="succeeded",
        )
        self.updated_at = event.succeeded_at

        # Update latest attempt
        if self.attempts:
            latest = self.attempts[-1]
            latest.status = "succeeded"
            latest.gateway_transaction_id = event.gateway_transaction_id

    @apply
    def _on_payment_failed(self, event: PaymentFailed):
        self.status = PaymentStatus.FAILED.value
        self.updated_at = event.failed_at

        # Update latest attempt
        if self.attempts:
            latest = self.attempts[-1]
            latest.status = "failed"
            latest.failure_reason = event.reason

    @apply
    def _on_payment_retry_initiated(self, event: PaymentRetryInitiated):
        self.status = PaymentStatus.PENDING.value
        self.attempt_count = event.attempt_number
        self.updated_at = event.retried_at

        # Add new attempt
        self.add_attempts(
            PaymentAttempt(
                attempted_at=event.retried_at,
                status="processing",
            )
        )

    @apply
    def _on_refund_requested(self, event: RefundRequested):
        self.add_refunds(
            Refund(
                id=event.refund_id,
                amount=event.amount,
                reason=event.reason,
                status=RefundStatus.REQUESTED.value,
                requested_at=event.requested_at,
            )
        )
        self.updated_at = event.requested_at

    @apply
    def _on_refund_completed(self, event: RefundCompleted):
        refund = next((r for r in (self.refunds or []) if str(r.id) == str(event.refund_id)), None)
        if refund:
            refund.status = RefundStatus.COMPLETED.value
            refund.gateway_refund_id = event.gateway_refund_id
            refund.processed_at = event.completed_at

        self.total_refunded = (self.total_refunded or 0.0) + event.amount
        if self.total_refunded >= self.amount.value:
            self.status = PaymentStatus.REFUNDED.value
        else:
            self.status = PaymentStatus.PARTIALLY_REFUNDED.value
        self.updated_at = event.completed_at
