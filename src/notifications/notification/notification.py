"""Notification aggregate (CQRS) — tracks individual notification lifecycle.

Each notification represents a single message sent to a recipient via a
specific channel. Notifications are created reactively from cross-domain
events and dispatched through channel adapters (email, SMS, push, Slack).

State Machine (6 states):
    PENDING → SENT → DELIVERED
    PENDING → SENT → BOUNCED
    PENDING → SENT → FAILED → (retry) → PENDING
    PENDING → FAILED → (retry) → PENDING
    PENDING → CANCELLED
"""

from datetime import UTC, datetime
from enum import Enum

from notifications.domain import notifications
from notifications.notification.events import (
    NotificationBounced,
    NotificationCancelled,
    NotificationCreated,
    NotificationDelivered,
    NotificationFailed,
    NotificationRetried,
    NotificationSent,
)
from protean.exceptions import ValidationError
from protean.fields import DateTime, Identifier, Integer, String, Text


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class NotificationType(Enum):
    WELCOME = "Welcome"
    ORDER_CONFIRMATION = "OrderConfirmation"
    PAYMENT_RECEIPT = "PaymentReceipt"
    SHIPPING_UPDATE = "ShippingUpdate"
    DELIVERY_CONFIRMATION = "DeliveryConfirmation"
    DELIVERY_EXCEPTION = "DeliveryException"
    REVIEW_PROMPT = "ReviewPrompt"
    CART_RECOVERY = "CartRecovery"
    LOW_STOCK_ALERT = "LowStockAlert"
    REVIEW_PUBLISHED = "ReviewPublished"
    REVIEW_REJECTED = "ReviewRejected"
    REFUND_NOTIFICATION = "RefundNotification"
    ORDER_CANCELLATION = "OrderCancellation"


class NotificationChannel(Enum):
    EMAIL = "Email"
    SMS = "SMS"
    PUSH = "Push"
    SLACK = "Slack"


class NotificationStatus(Enum):
    PENDING = "Pending"
    SENT = "Sent"
    DELIVERED = "Delivered"
    FAILED = "Failed"
    BOUNCED = "Bounced"
    CANCELLED = "Cancelled"


class RecipientType(Enum):
    CUSTOMER = "Customer"
    INTERNAL = "Internal"


# ---------------------------------------------------------------------------
# State Machine
# ---------------------------------------------------------------------------
_VALID_TRANSITIONS = {
    NotificationStatus.PENDING: {
        NotificationStatus.SENT,
        NotificationStatus.FAILED,
        NotificationStatus.CANCELLED,
    },
    NotificationStatus.SENT: {
        NotificationStatus.DELIVERED,
        NotificationStatus.FAILED,
        NotificationStatus.BOUNCED,
    },
    NotificationStatus.FAILED: {
        NotificationStatus.PENDING,  # Via retry
    },
    NotificationStatus.DELIVERED: set(),  # Terminal
    NotificationStatus.BOUNCED: set(),  # Terminal
    NotificationStatus.CANCELLED: set(),  # Terminal
}


# ---------------------------------------------------------------------------
# Aggregate Root
# ---------------------------------------------------------------------------
@notifications.aggregate
class Notification:
    """A single notification dispatched to a recipient via a channel.

    Notifications are created reactively from cross-domain events. Each
    notification tracks its delivery lifecycle for audit and retry.
    """

    # Recipient
    recipient_id: Identifier(required=True)
    recipient_type: String(choices=RecipientType, default=RecipientType.CUSTOMER.value)

    # Notification type and channel
    notification_type: String(choices=NotificationType, required=True)
    channel: String(choices=NotificationChannel, required=True)

    # Content
    subject: String(max_length=500)
    body: Text(required=True)

    # Template
    template_name: String(max_length=200)

    # Source event correlation
    source_event_type: String(max_length=200)
    source_event_id: String(max_length=200)
    context_data: Text()  # JSON — data used to render the template

    # Status
    status: String(choices=NotificationStatus, default=NotificationStatus.PENDING.value)

    # Scheduling
    scheduled_for: DateTime()  # Null means immediate

    # Delivery tracking
    sent_at: DateTime()
    delivered_at: DateTime()
    failure_reason: String(max_length=500)

    # Retry
    retry_count: Integer(default=0)
    max_retries: Integer(default=3)

    # Timestamps
    created_at: DateTime()
    updated_at: DateTime()

    # -------------------------------------------------------------------
    # Factory
    # -------------------------------------------------------------------
    @classmethod
    def create(
        cls,
        recipient_id,
        notification_type,
        channel,
        body,
        subject=None,
        recipient_type=RecipientType.CUSTOMER.value,
        template_name=None,
        source_event_type=None,
        source_event_id=None,
        context_data=None,
        scheduled_for=None,
        max_retries=3,
    ):
        """Create a new notification in PENDING status."""
        now = datetime.now(UTC)

        notification = cls(
            recipient_id=recipient_id,
            recipient_type=recipient_type,
            notification_type=notification_type,
            channel=channel,
            subject=subject,
            body=body,
            template_name=template_name,
            source_event_type=source_event_type,
            source_event_id=source_event_id,
            context_data=context_data,
            scheduled_for=scheduled_for,
            status=NotificationStatus.PENDING.value,
            retry_count=0,
            max_retries=max_retries,
            created_at=now,
            updated_at=now,
        )

        notification.raise_(
            NotificationCreated(
                notification_id=str(notification.id),
                recipient_id=str(recipient_id),
                recipient_type=recipient_type,
                notification_type=notification_type,
                channel=channel,
                subject=subject,
                template_name=template_name,
                source_event_type=source_event_type,
                scheduled_for=scheduled_for,
                created_at=now,
            )
        )

        return notification

    # -------------------------------------------------------------------
    # State transitions
    # -------------------------------------------------------------------
    def _assert_can_transition(self, target_status):
        """Validate state machine transition."""
        current = NotificationStatus(self.status)
        if target_status not in _VALID_TRANSITIONS.get(current, set()):
            raise ValidationError({"status": [f"Cannot transition from {current.value} to {target_status.value}"]})

    def mark_sent(self, sent_at=None):
        """Mark notification as successfully sent to the channel."""
        self._assert_can_transition(NotificationStatus.SENT)

        now = sent_at or datetime.now(UTC)
        self.status = NotificationStatus.SENT.value
        self.sent_at = now
        self.updated_at = now

        self.raise_(
            NotificationSent(
                notification_id=str(self.id),
                recipient_id=str(self.recipient_id),
                channel=self.channel,
                sent_at=now,
            )
        )

    def mark_delivered(self, delivered_at=None):
        """Mark notification as confirmed delivered."""
        self._assert_can_transition(NotificationStatus.DELIVERED)

        now = delivered_at or datetime.now(UTC)
        self.status = NotificationStatus.DELIVERED.value
        self.delivered_at = now
        self.updated_at = now

        self.raise_(
            NotificationDelivered(
                notification_id=str(self.id),
                recipient_id=str(self.recipient_id),
                channel=self.channel,
                delivered_at=now,
            )
        )

    def mark_failed(self, reason):
        """Mark notification as failed."""
        self._assert_can_transition(NotificationStatus.FAILED)

        now = datetime.now(UTC)
        self.status = NotificationStatus.FAILED.value
        self.failure_reason = reason
        self.retry_count = self.retry_count + 1
        self.updated_at = now

        self.raise_(
            NotificationFailed(
                notification_id=str(self.id),
                recipient_id=str(self.recipient_id),
                channel=self.channel,
                reason=reason,
                retry_count=self.retry_count,
                max_retries=self.max_retries,
                failed_at=now,
            )
        )

    def mark_bounced(self, reason):
        """Mark notification as bounced (permanent delivery failure)."""
        self._assert_can_transition(NotificationStatus.BOUNCED)

        now = datetime.now(UTC)
        self.status = NotificationStatus.BOUNCED.value
        self.failure_reason = reason
        self.updated_at = now

        self.raise_(
            NotificationBounced(
                notification_id=str(self.id),
                recipient_id=str(self.recipient_id),
                channel=self.channel,
                reason=reason,
                bounced_at=now,
            )
        )

    def cancel(self, reason):
        """Cancel a pending notification."""
        self._assert_can_transition(NotificationStatus.CANCELLED)

        now = datetime.now(UTC)
        self.status = NotificationStatus.CANCELLED.value
        self.failure_reason = reason
        self.updated_at = now

        self.raise_(
            NotificationCancelled(
                notification_id=str(self.id),
                recipient_id=str(self.recipient_id),
                channel=self.channel,
                reason=reason,
                cancelled_at=now,
            )
        )

    def retry(self):
        """Retry a failed notification."""
        if NotificationStatus(self.status) != NotificationStatus.FAILED:
            raise ValidationError({"status": ["Only failed notifications can be retried"]})
        if self.retry_count >= self.max_retries:
            raise ValidationError({"retry_count": ["Maximum retry attempts exceeded"]})

        now = datetime.now(UTC)
        self.status = NotificationStatus.PENDING.value
        self.failure_reason = None
        self.updated_at = now

        self.raise_(
            NotificationRetried(
                notification_id=str(self.id),
                recipient_id=str(self.recipient_id),
                channel=self.channel,
                retry_count=self.retry_count,
                retried_at=now,
            )
        )
