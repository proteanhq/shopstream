"""Template registry — maps NotificationType to template classes.

Each template knows its default channels and how to render content
from event context data.
"""

from notifications.notification.notification import NotificationType
from notifications.templates.cart_recovery import CartRecoveryTemplate
from notifications.templates.delivery_confirmation import (
    DeliveryConfirmationTemplate,
)
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

TEMPLATE_REGISTRY: dict[str, type] = {
    NotificationType.WELCOME.value: WelcomeTemplate,
    NotificationType.ORDER_CONFIRMATION.value: OrderConfirmationTemplate,
    NotificationType.PAYMENT_RECEIPT.value: PaymentReceiptTemplate,
    NotificationType.SHIPPING_UPDATE.value: ShippingUpdateTemplate,
    NotificationType.DELIVERY_CONFIRMATION.value: DeliveryConfirmationTemplate,
    NotificationType.DELIVERY_EXCEPTION.value: DeliveryExceptionTemplate,
    NotificationType.REVIEW_PROMPT.value: ReviewPromptTemplate,
    NotificationType.CART_RECOVERY.value: CartRecoveryTemplate,
    NotificationType.LOW_STOCK_ALERT.value: LowStockAlertTemplate,
    NotificationType.REVIEW_PUBLISHED.value: ReviewPublishedTemplate,
    NotificationType.REVIEW_REJECTED.value: ReviewRejectedTemplate,
    NotificationType.REFUND_NOTIFICATION.value: RefundNotificationTemplate,
    NotificationType.ORDER_CANCELLATION.value: OrderCancellationTemplate,
}


def get_template(notification_type: str):
    """Look up a template class by notification type string."""
    template_cls = TEMPLATE_REGISTRY.get(notification_type)
    if template_cls is None:
        raise ValueError(f"No template registered for notification type: {notification_type}")
    return template_cls
