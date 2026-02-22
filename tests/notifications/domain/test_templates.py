"""Tests for notification templates — rendering and registry."""

import pytest
from notifications.notification.notification import NotificationChannel, NotificationType
from notifications.templates import TEMPLATE_REGISTRY, get_template
from notifications.templates.cart_recovery import CartRecoveryTemplate
from notifications.templates.delivery_confirmation import DeliveryConfirmationTemplate
from notifications.templates.delivery_exception import DeliveryExceptionTemplate
from notifications.templates.low_stock_alert import LowStockAlertTemplate
from notifications.templates.order_cancellation import OrderCancellationTemplate
from notifications.templates.order_confirmation import OrderConfirmationTemplate
from notifications.templates.payment_receipt import PaymentReceiptTemplate
from notifications.templates.refund_notification import RefundNotificationTemplate
from notifications.templates.review_prompt import ReviewPromptTemplate
from notifications.templates.review_published import ReviewPublishedTemplate
from notifications.templates.review_rejected import ReviewRejectedTemplate
from notifications.templates.shipping_update import ShippingUpdateTemplate
from notifications.templates.welcome import WelcomeTemplate


# ---------------------------------------------------------------
# Template registry
# ---------------------------------------------------------------
class TestTemplateRegistry:
    def test_registry_has_13_templates(self):
        assert len(TEMPLATE_REGISTRY) == 13

    def test_every_notification_type_has_a_template(self):
        for nt in NotificationType:
            assert nt.value in TEMPLATE_REGISTRY, f"Missing template for {nt.value}"

    def test_get_template_returns_correct_class(self):
        cls = get_template(NotificationType.WELCOME.value)
        assert cls is WelcomeTemplate

    def test_get_template_unknown_type_raises(self):
        with pytest.raises(ValueError, match="No template registered"):
            get_template("NonexistentType")


# ---------------------------------------------------------------
# Welcome template
# ---------------------------------------------------------------
class TestWelcomeTemplate:
    def test_notification_type(self):
        assert WelcomeTemplate.notification_type == NotificationType.WELCOME.value

    def test_default_channels_email(self):
        assert NotificationChannel.EMAIL.value in WelcomeTemplate.default_channels

    def test_render_with_first_name(self):
        result = WelcomeTemplate.render({"first_name": "Alice"})
        assert "Alice" in result["subject"]
        assert "Alice" in result["body"]

    def test_render_without_first_name_defaults(self):
        result = WelcomeTemplate.render({})
        assert "there" in result["subject"]

    def test_render_has_subject_and_body(self):
        result = WelcomeTemplate.render({"first_name": "Bob"})
        assert "subject" in result
        assert "body" in result


# ---------------------------------------------------------------
# Order confirmation template
# ---------------------------------------------------------------
class TestOrderConfirmationTemplate:
    def test_notification_type(self):
        assert OrderConfirmationTemplate.notification_type == NotificationType.ORDER_CONFIRMATION.value

    def test_render_includes_order_id(self):
        result = OrderConfirmationTemplate.render({"order_id": "ORD-123", "grand_total": "99.99"})
        assert "ORD-123" in result["body"]


# ---------------------------------------------------------------
# Payment receipt template
# ---------------------------------------------------------------
class TestPaymentReceiptTemplate:
    def test_notification_type(self):
        assert PaymentReceiptTemplate.notification_type == NotificationType.PAYMENT_RECEIPT.value

    def test_render_includes_amount(self):
        result = PaymentReceiptTemplate.render({"order_id": "ORD-1", "amount": "49.99", "currency": "USD"})
        assert "49.99" in result["body"]


# ---------------------------------------------------------------
# Shipping update template
# ---------------------------------------------------------------
class TestShippingUpdateTemplate:
    def test_notification_type(self):
        assert ShippingUpdateTemplate.notification_type == NotificationType.SHIPPING_UPDATE.value

    def test_render_has_subject_and_body(self):
        result = ShippingUpdateTemplate.render({"order_id": "ORD-1", "carrier": "FedEx", "tracking_number": "ABC123"})
        assert "subject" in result
        assert "body" in result


# ---------------------------------------------------------------
# Delivery confirmation template
# ---------------------------------------------------------------
class TestDeliveryConfirmationTemplate:
    def test_notification_type(self):
        assert DeliveryConfirmationTemplate.notification_type == NotificationType.DELIVERY_CONFIRMATION.value

    def test_render_includes_order_id(self):
        result = DeliveryConfirmationTemplate.render({"order_id": "ORD-456"})
        assert "ORD-456" in result["body"]

    def test_render_default_order_id(self):
        result = DeliveryConfirmationTemplate.render({})
        assert "N/A" in result["body"]

    def test_default_channels(self):
        assert NotificationChannel.EMAIL.value in DeliveryConfirmationTemplate.default_channels
        assert NotificationChannel.PUSH.value in DeliveryConfirmationTemplate.default_channels


# ---------------------------------------------------------------
# Delivery exception template
# ---------------------------------------------------------------
class TestDeliveryExceptionTemplate:
    def test_notification_type(self):
        assert DeliveryExceptionTemplate.notification_type == NotificationType.DELIVERY_EXCEPTION.value

    def test_render_includes_order_and_reason(self):
        result = DeliveryExceptionTemplate.render({"order_id": "ORD-789", "reason": "Address not found"})
        assert "ORD-789" in result["body"]
        assert "Address not found" in result["body"]

    def test_render_defaults(self):
        result = DeliveryExceptionTemplate.render({})
        assert "N/A" in result["body"]
        assert "an issue during delivery" in result["body"]

    def test_default_channels(self):
        assert NotificationChannel.EMAIL.value in DeliveryExceptionTemplate.default_channels
        assert NotificationChannel.SMS.value in DeliveryExceptionTemplate.default_channels


# ---------------------------------------------------------------
# Review prompt template
# ---------------------------------------------------------------
class TestReviewPromptTemplate:
    def test_notification_type(self):
        assert ReviewPromptTemplate.notification_type == NotificationType.REVIEW_PROMPT.value

    def test_render_includes_order_id(self):
        result = ReviewPromptTemplate.render({"order_id": "ORD-1"})
        assert "ORD-1" in result["body"]


# ---------------------------------------------------------------
# Cart recovery template
# ---------------------------------------------------------------
class TestCartRecoveryTemplate:
    def test_notification_type(self):
        assert CartRecoveryTemplate.notification_type == NotificationType.CART_RECOVERY.value

    def test_render_has_subject_and_body(self):
        result = CartRecoveryTemplate.render({"cart_id": "cart-1"})
        assert "subject" in result
        assert "body" in result
        assert "cart" in result["body"].lower()

    def test_default_channels(self):
        assert NotificationChannel.EMAIL.value in CartRecoveryTemplate.default_channels


# ---------------------------------------------------------------
# Low stock alert template
# ---------------------------------------------------------------
class TestLowStockAlertTemplate:
    def test_notification_type(self):
        assert LowStockAlertTemplate.notification_type == NotificationType.LOW_STOCK_ALERT.value

    def test_default_channels_slack(self):
        assert NotificationChannel.SLACK.value in LowStockAlertTemplate.default_channels


# ---------------------------------------------------------------
# Review published template
# ---------------------------------------------------------------
class TestReviewPublishedTemplate:
    def test_notification_type(self):
        assert ReviewPublishedTemplate.notification_type == NotificationType.REVIEW_PUBLISHED.value

    def test_render_has_subject_and_body(self):
        result = ReviewPublishedTemplate.render({"product_id": "P1"})
        assert "subject" in result
        assert "body" in result
        assert "published" in result["subject"].lower()

    def test_default_channels(self):
        assert NotificationChannel.EMAIL.value in ReviewPublishedTemplate.default_channels


# ---------------------------------------------------------------
# Review rejected template
# ---------------------------------------------------------------
class TestReviewRejectedTemplate:
    def test_notification_type(self):
        assert ReviewRejectedTemplate.notification_type == NotificationType.REVIEW_REJECTED.value

    def test_render_includes_reason(self):
        result = ReviewRejectedTemplate.render({"product_id": "P1", "review_id": "R1", "reason": "Spam content"})
        assert "Spam content" in result["body"]


# ---------------------------------------------------------------
# Refund notification template
# ---------------------------------------------------------------
class TestRefundNotificationTemplate:
    def test_notification_type(self):
        assert RefundNotificationTemplate.notification_type == NotificationType.REFUND_NOTIFICATION.value

    def test_render_includes_amount_and_order(self):
        result = RefundNotificationTemplate.render({"order_id": "ORD-R1", "amount": "25.00", "currency": "EUR"})
        assert "25.00" in result["body"]
        assert "ORD-R1" in result["body"]
        assert "EUR" in result["body"]
        assert "EUR" in result["subject"]

    def test_render_defaults(self):
        result = RefundNotificationTemplate.render({})
        assert "N/A" in result["body"]
        assert "0.00" in result["body"]

    def test_default_channels(self):
        assert NotificationChannel.EMAIL.value in RefundNotificationTemplate.default_channels


# ---------------------------------------------------------------
# Order cancellation template
# ---------------------------------------------------------------
class TestOrderCancellationTemplate:
    def test_notification_type(self):
        assert OrderCancellationTemplate.notification_type == NotificationType.ORDER_CANCELLATION.value

    def test_render_includes_order_id_and_reason(self):
        result = OrderCancellationTemplate.render(
            {"order_id": "ORD-C1", "reason": "Customer request", "cancelled_by": "customer"}
        )
        assert "ORD-C1" in result["body"]
        assert "ORD-C1" in result["subject"]
        assert "Customer request" in result["body"]
        assert "customer" in result["body"]

    def test_render_defaults(self):
        result = OrderCancellationTemplate.render({})
        assert "N/A" in result["body"]
        assert "as requested" in result["body"]
        assert "system" in result["body"]

    def test_default_channels(self):
        assert NotificationChannel.EMAIL.value in OrderCancellationTemplate.default_channels
