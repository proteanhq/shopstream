"""Tests for Notification domain enums."""

from notifications.notification.notification import (
    NotificationChannel,
    NotificationStatus,
    NotificationType,
    RecipientType,
)


class TestNotificationType:
    def test_has_13_types(self):
        assert len(NotificationType) == 13

    def test_welcome(self):
        assert NotificationType.WELCOME.value == "Welcome"

    def test_order_confirmation(self):
        assert NotificationType.ORDER_CONFIRMATION.value == "OrderConfirmation"

    def test_payment_receipt(self):
        assert NotificationType.PAYMENT_RECEIPT.value == "PaymentReceipt"

    def test_shipping_update(self):
        assert NotificationType.SHIPPING_UPDATE.value == "ShippingUpdate"

    def test_delivery_confirmation(self):
        assert NotificationType.DELIVERY_CONFIRMATION.value == "DeliveryConfirmation"

    def test_delivery_exception(self):
        assert NotificationType.DELIVERY_EXCEPTION.value == "DeliveryException"

    def test_review_prompt(self):
        assert NotificationType.REVIEW_PROMPT.value == "ReviewPrompt"

    def test_cart_recovery(self):
        assert NotificationType.CART_RECOVERY.value == "CartRecovery"

    def test_low_stock_alert(self):
        assert NotificationType.LOW_STOCK_ALERT.value == "LowStockAlert"

    def test_review_published(self):
        assert NotificationType.REVIEW_PUBLISHED.value == "ReviewPublished"

    def test_review_rejected(self):
        assert NotificationType.REVIEW_REJECTED.value == "ReviewRejected"

    def test_refund_notification(self):
        assert NotificationType.REFUND_NOTIFICATION.value == "RefundNotification"

    def test_order_cancellation(self):
        assert NotificationType.ORDER_CANCELLATION.value == "OrderCancellation"


class TestNotificationChannel:
    def test_has_4_channels(self):
        assert len(NotificationChannel) == 4

    def test_email(self):
        assert NotificationChannel.EMAIL.value == "Email"

    def test_sms(self):
        assert NotificationChannel.SMS.value == "SMS"

    def test_push(self):
        assert NotificationChannel.PUSH.value == "Push"

    def test_slack(self):
        assert NotificationChannel.SLACK.value == "Slack"


class TestNotificationStatus:
    def test_has_6_statuses(self):
        assert len(NotificationStatus) == 6

    def test_pending(self):
        assert NotificationStatus.PENDING.value == "Pending"

    def test_sent(self):
        assert NotificationStatus.SENT.value == "Sent"

    def test_delivered(self):
        assert NotificationStatus.DELIVERED.value == "Delivered"

    def test_failed(self):
        assert NotificationStatus.FAILED.value == "Failed"

    def test_bounced(self):
        assert NotificationStatus.BOUNCED.value == "Bounced"

    def test_cancelled(self):
        assert NotificationStatus.CANCELLED.value == "Cancelled"


class TestRecipientType:
    def test_has_2_types(self):
        assert len(RecipientType) == 2

    def test_customer(self):
        assert RecipientType.CUSTOMER.value == "Customer"

    def test_internal(self):
        assert RecipientType.INTERNAL.value == "Internal"
