"""Order detail — full order view for detail pages."""

import json

from protean.core.projector import on
from protean.fields import DateTime, Float, Identifier, String, Text
from protean.utils.globals import current_domain

from ordering.domain import ordering
from ordering.order.events import (
    CouponApplied,
    ItemAdded,
    ItemQuantityUpdated,
    ItemRemoved,
    OrderCancelled,
    OrderCompleted,
    OrderConfirmed,
    OrderCreated,
    OrderDelivered,
    OrderPartiallyShipped,
    OrderProcessing,
    OrderRefunded,
    OrderReturned,
    OrderShipped,
    PaymentFailed,
    PaymentPending,
    PaymentSucceeded,
    ReturnApproved,
    ReturnRequested,
)
from ordering.order.order import Order


@ordering.projection
class OrderDetail:
    order_id = Identifier(identifier=True, required=True)
    customer_id = Identifier(required=True)
    status = String(required=True)
    items = Text()  # JSON: list of item dicts
    shipping_address = Text()  # JSON: address dict
    billing_address = Text()  # JSON: address dict
    subtotal = Float()
    shipping_cost = Float()
    tax_total = Float()
    discount_total = Float()
    grand_total = Float()
    currency = String(default="USD")
    payment_id = String()
    payment_method = String()
    payment_status = String()
    shipment_id = String()
    carrier = String()
    tracking_number = String()
    estimated_delivery = String()
    cancellation_reason = String()
    cancelled_by = String()
    coupon_code = String()
    created_at = DateTime()
    updated_at = DateTime()


@ordering.projector(projector_for=OrderDetail, aggregates=[Order])
class OrderDetailProjector:
    @on(OrderCreated)
    def on_order_created(self, event):
        current_domain.repository_for(OrderDetail).add(
            OrderDetail(
                order_id=event.order_id,
                customer_id=event.customer_id,
                status="Created",
                items=event.items,
                shipping_address=event.shipping_address,
                billing_address=event.billing_address,
                subtotal=event.subtotal,
                shipping_cost=event.shipping_cost,
                tax_total=event.tax_total,
                discount_total=event.discount_total,
                grand_total=event.grand_total,
                currency=event.currency,
                created_at=event.created_at,
                updated_at=event.created_at,
            )
        )

    @on(ItemAdded)
    def on_item_added(self, event):
        repo = current_domain.repository_for(OrderDetail)
        detail = repo.get(event.order_id)
        items = json.loads(detail.items) if detail.items else []
        items.append(
            {
                "item_id": event.item_id,
                "product_id": event.product_id,
                "variant_id": event.variant_id,
                "sku": event.sku,
                "title": event.title,
                "quantity": event.quantity,
                "unit_price": event.unit_price,
            }
        )
        detail.items = json.dumps(items)
        detail.subtotal = event.new_subtotal
        detail.grand_total = event.new_grand_total
        repo.add(detail)

    @on(ItemRemoved)
    def on_item_removed(self, event):
        repo = current_domain.repository_for(OrderDetail)
        detail = repo.get(event.order_id)
        items = json.loads(detail.items) if detail.items else []
        items = [i for i in items if i.get("item_id") != str(event.item_id)]
        detail.items = json.dumps(items)
        detail.subtotal = event.new_subtotal
        detail.grand_total = event.new_grand_total
        repo.add(detail)

    @on(ItemQuantityUpdated)
    def on_item_quantity_updated(self, event):
        repo = current_domain.repository_for(OrderDetail)
        detail = repo.get(event.order_id)
        items = json.loads(detail.items) if detail.items else []
        for item in items:
            if item.get("item_id") == str(event.item_id):
                item["quantity"] = event.new_quantity
                break
        detail.items = json.dumps(items)
        detail.subtotal = event.new_subtotal
        detail.grand_total = event.new_grand_total
        repo.add(detail)

    @on(CouponApplied)
    def on_coupon_applied(self, event):
        repo = current_domain.repository_for(OrderDetail)
        detail = repo.get(event.order_id)
        detail.coupon_code = event.coupon_code
        repo.add(detail)

    @on(OrderConfirmed)
    def on_order_confirmed(self, event):
        repo = current_domain.repository_for(OrderDetail)
        detail = repo.get(event.order_id)
        detail.status = "Confirmed"
        detail.updated_at = event.confirmed_at
        repo.add(detail)

    @on(PaymentPending)
    def on_payment_pending(self, event):
        repo = current_domain.repository_for(OrderDetail)
        detail = repo.get(event.order_id)
        detail.status = "Payment_Pending"
        detail.payment_id = event.payment_id
        detail.payment_method = event.payment_method
        detail.payment_status = "pending"
        repo.add(detail)

    @on(PaymentSucceeded)
    def on_payment_succeeded(self, event):
        repo = current_domain.repository_for(OrderDetail)
        detail = repo.get(event.order_id)
        detail.status = "Paid"
        detail.payment_id = event.payment_id
        detail.payment_method = event.payment_method
        detail.payment_status = "succeeded"
        repo.add(detail)

    @on(PaymentFailed)
    def on_payment_failed(self, event):
        repo = current_domain.repository_for(OrderDetail)
        detail = repo.get(event.order_id)
        detail.status = "Confirmed"
        detail.payment_status = "failed"
        repo.add(detail)

    @on(OrderProcessing)
    def on_order_processing(self, event):
        repo = current_domain.repository_for(OrderDetail)
        detail = repo.get(event.order_id)
        detail.status = "Processing"
        detail.updated_at = event.started_at
        repo.add(detail)

    @on(OrderShipped)
    def on_order_shipped(self, event):
        repo = current_domain.repository_for(OrderDetail)
        detail = repo.get(event.order_id)
        detail.status = "Shipped"
        detail.shipment_id = event.shipment_id
        detail.carrier = event.carrier
        detail.tracking_number = event.tracking_number
        detail.estimated_delivery = event.estimated_delivery
        detail.updated_at = event.shipped_at
        repo.add(detail)

    @on(OrderPartiallyShipped)
    def on_order_partially_shipped(self, event):
        repo = current_domain.repository_for(OrderDetail)
        detail = repo.get(event.order_id)
        detail.status = "Partially_Shipped"
        detail.shipment_id = event.shipment_id
        detail.carrier = event.carrier
        detail.tracking_number = event.tracking_number
        detail.updated_at = event.shipped_at
        repo.add(detail)

    @on(OrderDelivered)
    def on_order_delivered(self, event):
        repo = current_domain.repository_for(OrderDetail)
        detail = repo.get(event.order_id)
        detail.status = "Delivered"
        detail.updated_at = event.delivered_at
        repo.add(detail)

    @on(OrderCompleted)
    def on_order_completed(self, event):
        repo = current_domain.repository_for(OrderDetail)
        detail = repo.get(event.order_id)
        detail.status = "Completed"
        detail.updated_at = event.completed_at
        repo.add(detail)

    @on(ReturnRequested)
    def on_return_requested(self, event):
        repo = current_domain.repository_for(OrderDetail)
        detail = repo.get(event.order_id)
        detail.status = "Return_Requested"
        detail.updated_at = event.requested_at
        repo.add(detail)

    @on(ReturnApproved)
    def on_return_approved(self, event):
        repo = current_domain.repository_for(OrderDetail)
        detail = repo.get(event.order_id)
        detail.status = "Return_Approved"
        detail.updated_at = event.approved_at
        repo.add(detail)

    @on(OrderReturned)
    def on_order_returned(self, event):
        repo = current_domain.repository_for(OrderDetail)
        detail = repo.get(event.order_id)
        detail.status = "Returned"
        detail.updated_at = event.returned_at
        repo.add(detail)

    @on(OrderCancelled)
    def on_order_cancelled(self, event):
        repo = current_domain.repository_for(OrderDetail)
        detail = repo.get(event.order_id)
        detail.status = "Cancelled"
        detail.cancellation_reason = event.reason
        detail.cancelled_by = event.cancelled_by
        detail.updated_at = event.cancelled_at
        repo.add(detail)

    @on(OrderRefunded)
    def on_order_refunded(self, event):
        repo = current_domain.repository_for(OrderDetail)
        detail = repo.get(event.order_id)
        detail.status = "Refunded"
        detail.updated_at = event.refunded_at
        repo.add(detail)
