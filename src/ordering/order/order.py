"""Order aggregate (Event Sourced) — the core of the ordering domain.

The Order aggregate uses event sourcing: all state changes are captured as
domain events, and the current state is rebuilt by replaying events via
@apply decorators. This provides a complete audit trail, temporal queries,
and reliable state reconstruction.

State Machine (14 states):
    CREATED → CONFIRMED → PAYMENT_PENDING → PAID → PROCESSING →
    SHIPPED/PARTIALLY_SHIPPED → DELIVERED → COMPLETED
    DELIVERED → RETURN_REQUESTED → RETURN_APPROVED → RETURNED → REFUNDED
    CANCELLED (from CREATED, CONFIRMED, PAYMENT_PENDING, PAID) → REFUNDED
"""

import json
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


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class OrderStatus(Enum):
    CREATED = "Created"
    CONFIRMED = "Confirmed"
    PAYMENT_PENDING = "Payment_Pending"
    PAID = "Paid"
    PROCESSING = "Processing"
    PARTIALLY_SHIPPED = "Partially_Shipped"
    SHIPPED = "Shipped"
    DELIVERED = "Delivered"
    COMPLETED = "Completed"
    RETURN_REQUESTED = "Return_Requested"
    RETURN_APPROVED = "Return_Approved"
    RETURNED = "Returned"
    CANCELLED = "Cancelled"
    REFUNDED = "Refunded"


class ItemStatus(Enum):
    PENDING = "Pending"
    RESERVED = "Reserved"
    SHIPPED = "Shipped"
    DELIVERED = "Delivered"
    RETURNED = "Returned"


class CancellationActor(Enum):
    CUSTOMER = "Customer"
    SYSTEM = "System"
    ADMIN = "Admin"


# State machine transition map
_VALID_TRANSITIONS = {
    OrderStatus.CREATED: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.PAYMENT_PENDING, OrderStatus.CANCELLED},
    OrderStatus.PAYMENT_PENDING: {
        OrderStatus.PAID,
        OrderStatus.CONFIRMED,  # Payment failure → retry
        OrderStatus.CANCELLED,
    },
    OrderStatus.PAID: {OrderStatus.PROCESSING, OrderStatus.CANCELLED},
    OrderStatus.PROCESSING: {OrderStatus.SHIPPED, OrderStatus.PARTIALLY_SHIPPED},
    OrderStatus.PARTIALLY_SHIPPED: {OrderStatus.SHIPPED},
    OrderStatus.SHIPPED: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: {OrderStatus.COMPLETED, OrderStatus.RETURN_REQUESTED},
    OrderStatus.RETURN_REQUESTED: {OrderStatus.RETURN_APPROVED},
    OrderStatus.RETURN_APPROVED: {OrderStatus.RETURNED},
    OrderStatus.RETURNED: {OrderStatus.REFUNDED},
    OrderStatus.CANCELLED: {OrderStatus.REFUNDED},
    OrderStatus.COMPLETED: set(),  # Terminal
    OrderStatus.REFUNDED: set(),  # Terminal
}

# States from which cancellation is allowed
_CANCELLABLE_STATES = {
    OrderStatus.CREATED,
    OrderStatus.CONFIRMED,
    OrderStatus.PAYMENT_PENDING,
    OrderStatus.PAID,
}


# ---------------------------------------------------------------------------
# Value Objects
# ---------------------------------------------------------------------------
@ordering.value_object(part_of="Order")
class ShippingAddress:
    """A delivery or billing address captured at checkout time.

    Once recorded on an Order, the address is immutable — it represents where
    the order was shipped, regardless of future address changes on the Customer.
    """

    street = String(required=True, max_length=255)
    city = String(required=True, max_length=100)
    state = String(max_length=100)
    postal_code = String(required=True, max_length=20)
    country = String(required=True, max_length=100)


@ordering.value_object(part_of="Order")
class OrderPricing:
    """Financial summary of an order: subtotal, shipping, tax, discounts, and grand total.

    Prices are locked at checkout and never change, even if the catalogue prices
    change later. The currency is captured alongside the amounts.
    """

    subtotal = Float(default=0.0)
    shipping_cost = Float(default=0.0)
    tax_total = Float(default=0.0)
    discount_total = Float(default=0.0)
    grand_total = Float(default=0.0)
    currency = String(max_length=3, default="USD")


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------
@ordering.entity(part_of="Order")
class OrderItem:
    """A line item in an order, representing a specific product variant and quantity.

    Each item tracks its own status through the fulfillment lifecycle
    (Pending -> Shipped -> Delivered -> optionally Returned), enabling partial
    shipments where some items ship before others.
    """

    product_id = Identifier(required=True)
    variant_id = Identifier(required=True)
    sku = String(required=True, max_length=50)
    title = String(required=True, max_length=255)
    quantity = Integer(required=True, min_value=1)
    unit_price = Float(required=True, min_value=0.0)
    discount = Float(default=0.0)
    tax_amount = Float(default=0.0)
    item_status = String(
        choices=ItemStatus,
        default=ItemStatus.PENDING.value,
    )


# ---------------------------------------------------------------------------
# Aggregate Root (Event Sourced)
# ---------------------------------------------------------------------------
@ordering.aggregate(is_event_sourced=True)
class Order:
    customer_id = Identifier(required=True)
    status = String(
        choices=OrderStatus,
        default=OrderStatus.CREATED.value,
    )
    items = HasMany(OrderItem)
    shipping_address = ValueObject(ShippingAddress)
    billing_address = ValueObject(ShippingAddress)
    pricing = ValueObject(OrderPricing)
    payment_id = String(max_length=255)
    payment_method = String(max_length=50)
    payment_status = String(max_length=50)
    shipment_id = String(max_length=255)
    carrier = String(max_length=100)
    tracking_number = String(max_length=255)
    estimated_delivery = String(max_length=10)  # ISO date string
    cancellation_reason = String(max_length=500)
    cancelled_by = String(max_length=50)
    coupon_code = String(max_length=100)
    created_at = DateTime()
    updated_at = DateTime()

    # -------------------------------------------------------------------
    # Factory method
    # -------------------------------------------------------------------
    @classmethod
    def create(
        cls,
        customer_id,
        items_data,
        shipping_address,
        billing_address,
        pricing,
    ):
        """Create a new order from checkout data.

        Uses _create_new() to get a blank aggregate with auto-generated
        identity.  All state is established by the OrderCreated event's
        @apply handler — the single source of truth.

        Args:
            customer_id: The customer placing the order.
            items_data: List of dicts with product_id, variant_id, sku,
                        title, quantity, unit_price.
            shipping_address: Dict with street, city, state, postal_code, country.
            billing_address: Dict with street, city, state, postal_code, country.
            pricing: Dict with subtotal, shipping_cost, tax_total,
                     discount_total, grand_total, currency.
        """
        now = datetime.now(UTC)

        # Pre-generate item IDs for deterministic replay
        items_with_ids = [{**item, "id": str(uuid4())} for item in items_data]

        order = cls._create_new()
        order.raise_(
            OrderCreated(
                order_id=str(order.id),
                customer_id=str(customer_id),
                items=json.dumps(items_with_ids),
                shipping_address=json.dumps(shipping_address),
                billing_address=json.dumps(billing_address),
                subtotal=pricing.get("subtotal", 0.0),
                shipping_cost=pricing.get("shipping_cost", 0.0),
                tax_total=pricing.get("tax_total", 0.0),
                discount_total=pricing.get("discount_total", 0.0),
                grand_total=pricing.get("grand_total", 0.0),
                currency=pricing.get("currency", "USD"),
                created_at=now,
            )
        )
        return order

    # -------------------------------------------------------------------
    # State transition helper
    # -------------------------------------------------------------------
    def _assert_can_transition(self, target_status):
        """Validate that the current state allows transition to target."""
        current = OrderStatus(self.status)
        if target_status not in _VALID_TRANSITIONS.get(current, set()):
            raise ValidationError({"status": [f"Cannot transition from {current.value} to {target_status.value}"]})

    def _recalculate_pricing(self):
        """Recalculate subtotal and grand total from items."""
        subtotal = sum(item.unit_price * item.quantity - item.discount for item in self.items)
        grand_total = subtotal + self.pricing.shipping_cost + self.pricing.tax_total - self.pricing.discount_total
        self.pricing = OrderPricing(
            subtotal=subtotal,
            shipping_cost=self.pricing.shipping_cost,
            tax_total=self.pricing.tax_total,
            discount_total=self.pricing.discount_total,
            grand_total=grand_total,
            currency=self.pricing.currency,
        )

    # -------------------------------------------------------------------
    # Order modification (only in CREATED state)
    # -------------------------------------------------------------------
    def add_item(self, product_id, variant_id, sku, title, quantity, unit_price):
        """Add an item to the order. Only allowed in CREATED state."""
        self._assert_can_transition(OrderStatus.CONFIRMED)  # Proxy: if we can confirm, we can modify

        item = OrderItem(
            product_id=product_id,
            variant_id=variant_id,
            sku=sku,
            title=title,
            quantity=quantity,
            unit_price=unit_price,
        )
        self.add_items(item)
        self._recalculate_pricing()
        now = datetime.now(UTC)
        self.updated_at = now

        self.raise_(
            ItemAdded(
                order_id=str(self.id),
                item_id=str(item.id),
                product_id=str(product_id),
                variant_id=str(variant_id),
                sku=sku,
                title=title,
                quantity=str(quantity),
                unit_price=str(unit_price),
                new_subtotal=self.pricing.subtotal,
                new_grand_total=self.pricing.grand_total,
            )
        )

    def remove_item(self, item_id):
        """Remove an item from the order. Only allowed in CREATED state."""
        if OrderStatus(self.status) != OrderStatus.CREATED:
            raise ValidationError({"status": ["Items can only be removed in Created state"]})

        item = next((i for i in self.items if str(i.id) == str(item_id)), None)
        if item is None:
            raise ValidationError({"item_id": ["Item not found"]})

        self.remove_items(item)
        self._recalculate_pricing()
        now = datetime.now(UTC)
        self.updated_at = now

        self.raise_(
            ItemRemoved(
                order_id=str(self.id),
                item_id=str(item_id),
                new_subtotal=self.pricing.subtotal,
                new_grand_total=self.pricing.grand_total,
            )
        )

    def update_item_quantity(self, item_id, new_quantity):
        """Update item quantity. Only allowed in CREATED state."""
        if OrderStatus(self.status) != OrderStatus.CREATED:
            raise ValidationError({"status": ["Item quantities can only be updated in Created state"]})
        if new_quantity < 1:
            raise ValidationError({"quantity": ["Quantity must be at least 1"]})

        item = next((i for i in self.items if str(i.id) == str(item_id)), None)
        if item is None:
            raise ValidationError({"item_id": ["Item not found"]})

        previous_quantity = item.quantity
        item.quantity = new_quantity
        self._recalculate_pricing()
        now = datetime.now(UTC)
        self.updated_at = now

        self.raise_(
            ItemQuantityUpdated(
                order_id=str(self.id),
                item_id=str(item_id),
                previous_quantity=str(previous_quantity),
                new_quantity=str(new_quantity),
                new_subtotal=self.pricing.subtotal,
                new_grand_total=self.pricing.grand_total,
            )
        )

    def apply_coupon(self, coupon_code):
        """Apply a coupon code. Only allowed in CREATED state."""
        if OrderStatus(self.status) != OrderStatus.CREATED:
            raise ValidationError({"status": ["Coupons can only be applied in Created state"]})

        self.coupon_code = coupon_code
        now = datetime.now(UTC)
        self.updated_at = now

        self.raise_(
            CouponApplied(
                order_id=str(self.id),
                coupon_code=coupon_code,
            )
        )

    # -------------------------------------------------------------------
    # Order lifecycle transitions
    # -------------------------------------------------------------------
    def confirm(self):
        """Confirm the order (inventory reserved)."""
        self._assert_can_transition(OrderStatus.CONFIRMED)
        self.raise_(
            OrderConfirmed(
                order_id=str(self.id),
                confirmed_at=datetime.now(UTC),
            )
        )

    def record_payment_pending(self, payment_id, payment_method):
        """Record that payment has been initiated."""
        self._assert_can_transition(OrderStatus.PAYMENT_PENDING)
        self.status = OrderStatus.PAYMENT_PENDING.value
        self.payment_id = payment_id
        self.payment_method = payment_method
        self.payment_status = "pending"
        now = datetime.now(UTC)
        self.updated_at = now

        self.raise_(
            PaymentPending(
                order_id=str(self.id),
                payment_id=payment_id,
                payment_method=payment_method,
            )
        )

    def record_payment_success(self, payment_id, amount, payment_method):
        """Record successful payment capture."""
        self._assert_can_transition(OrderStatus.PAID)
        self.status = OrderStatus.PAID.value
        self.payment_id = payment_id
        self.payment_method = payment_method
        self.payment_status = "succeeded"
        now = datetime.now(UTC)
        self.updated_at = now

        self.raise_(
            PaymentSucceeded(
                order_id=str(self.id),
                payment_id=payment_id,
                amount=amount,
                payment_method=payment_method,
            )
        )

    def record_payment_failure(self, payment_id, reason):
        """Record payment failure. Returns order to CONFIRMED for retry."""
        self._assert_can_transition(OrderStatus.CONFIRMED)
        self.status = OrderStatus.CONFIRMED.value
        self.payment_status = "failed"
        now = datetime.now(UTC)
        self.updated_at = now

        self.raise_(
            PaymentFailed(
                order_id=str(self.id),
                payment_id=payment_id,
                reason=reason,
            )
        )

    def mark_processing(self):
        """Mark order as being processed (fulfillment started)."""
        self._assert_can_transition(OrderStatus.PROCESSING)
        self.raise_(
            OrderProcessing(
                order_id=str(self.id),
                started_at=datetime.now(UTC),
            )
        )

    def record_shipment(
        self,
        shipment_id,
        carrier,
        tracking_number,
        shipped_item_ids=None,
        estimated_delivery=None,
    ):
        """Record that the order has been shipped (all items)."""
        if OrderStatus(self.status) not in (
            OrderStatus.PAID,
            OrderStatus.PROCESSING,
            OrderStatus.PARTIALLY_SHIPPED,
        ):
            raise ValidationError({"status": ["Order must be Paid, Processing, or Partially Shipped to ship"]})

        self.raise_(
            OrderShipped(
                order_id=str(self.id),
                shipment_id=shipment_id,
                carrier=carrier,
                tracking_number=tracking_number,
                shipped_item_ids=json.dumps(shipped_item_ids or [str(i.id) for i in self.items]),
                estimated_delivery=estimated_delivery,
                shipped_at=datetime.now(UTC),
            )
        )

    def record_partial_shipment(
        self,
        shipment_id,
        carrier,
        tracking_number,
        shipped_item_ids,
    ):
        """Record partial shipment (some items shipped)."""
        if OrderStatus(self.status) != OrderStatus.PROCESSING:
            raise ValidationError({"status": ["Order must be Processing for partial shipment"]})

        self.raise_(
            OrderPartiallyShipped(
                order_id=str(self.id),
                shipment_id=shipment_id,
                carrier=carrier,
                tracking_number=tracking_number,
                shipped_item_ids=json.dumps(shipped_item_ids),
                shipped_at=datetime.now(UTC),
            )
        )

    def record_delivery(self):
        """Record that the order has been delivered."""
        self._assert_can_transition(OrderStatus.DELIVERED)
        self.raise_(
            OrderDelivered(
                order_id=str(self.id),
                delivered_at=datetime.now(UTC),
            )
        )

    def complete(self):
        """Complete the order (return window expired)."""
        self._assert_can_transition(OrderStatus.COMPLETED)
        self.raise_(
            OrderCompleted(
                order_id=str(self.id),
                completed_at=datetime.now(UTC),
            )
        )

    # -------------------------------------------------------------------
    # Returns
    # -------------------------------------------------------------------
    def request_return(self, reason):
        """Request a return (within return window)."""
        self._assert_can_transition(OrderStatus.RETURN_REQUESTED)
        self.raise_(
            ReturnRequested(
                order_id=str(self.id),
                reason=reason,
                requested_at=datetime.now(UTC),
            )
        )

    def approve_return(self):
        """Approve a return request."""
        self._assert_can_transition(OrderStatus.RETURN_APPROVED)
        self.raise_(
            ReturnApproved(
                order_id=str(self.id),
                approved_at=datetime.now(UTC),
            )
        )

    def record_return(self, returned_item_ids=None):
        """Record that returned items have been received."""
        self._assert_can_transition(OrderStatus.RETURNED)
        ids_to_return = returned_item_ids or [str(i.id) for i in self.items]
        self.raise_(
            OrderReturned(
                order_id=str(self.id),
                returned_item_ids=json.dumps(ids_to_return),
                returned_at=datetime.now(UTC),
            )
        )

    # -------------------------------------------------------------------
    # Cancellation & Refund
    # -------------------------------------------------------------------
    def cancel(self, reason, cancelled_by):
        """Cancel the order."""
        current = OrderStatus(self.status)
        if current not in _CANCELLABLE_STATES:
            raise ValidationError(
                {
                    "status": [
                        f"Cannot cancel order in {current.value} state. "
                        f"Cancellation is only allowed from: "
                        f"{', '.join(s.value for s in _CANCELLABLE_STATES)}"
                    ]
                }
            )

        self.raise_(
            OrderCancelled(
                order_id=str(self.id),
                reason=reason,
                cancelled_by=cancelled_by,
                cancelled_at=datetime.now(UTC),
            )
        )

    def refund(self, refund_amount=None):
        """Refund a cancelled or returned order."""
        current = OrderStatus(self.status)
        if current not in (OrderStatus.CANCELLED, OrderStatus.RETURNED):
            raise ValidationError({"status": ["Only cancelled or returned orders can be refunded"]})

        amount = refund_amount if refund_amount is not None else self.pricing.grand_total
        self.raise_(
            OrderRefunded(
                order_id=str(self.id),
                refund_amount=amount,
                refunded_at=datetime.now(UTC),
            )
        )

    # -------------------------------------------------------------------
    # @apply methods — rebuild state during event replay
    # -------------------------------------------------------------------
    @apply
    def _on_order_created(self, event: OrderCreated):
        self.id = event.order_id
        self.customer_id = event.customer_id
        self.status = OrderStatus.CREATED.value
        self.created_at = event.created_at
        self.updated_at = event.created_at

        # Reconstruct items from JSON (includes IDs for deterministic replay)
        items_data = json.loads(event.items) if isinstance(event.items, str) else []
        self.items = [OrderItem(**item_data) for item_data in items_data]

        # Reconstruct addresses
        ship_data = json.loads(event.shipping_address) if isinstance(event.shipping_address, str) else {}
        if ship_data:
            self.shipping_address = ShippingAddress(**ship_data)

        bill_data = json.loads(event.billing_address) if isinstance(event.billing_address, str) else {}
        if bill_data:
            self.billing_address = ShippingAddress(**bill_data)

        # Reconstruct pricing
        self.pricing = OrderPricing(
            subtotal=event.subtotal,
            shipping_cost=event.shipping_cost or 0.0,
            tax_total=event.tax_total or 0.0,
            discount_total=event.discount_total or 0.0,
            grand_total=event.grand_total,
            currency=event.currency or "USD",
        )

    @apply
    def _on_item_added(self, event: ItemAdded):
        # Idempotent: skip if already added (live path pre-mutates)
        existing = next((i for i in (self.items or []) if str(i.id) == str(event.item_id)), None)
        if not existing:
            self.add_items(
                OrderItem(
                    id=event.item_id,
                    product_id=event.product_id,
                    variant_id=event.variant_id,
                    sku=event.sku,
                    title=event.title,
                    quantity=int(event.quantity),
                    unit_price=float(event.unit_price),
                )
            )
        self.pricing = OrderPricing(
            subtotal=event.new_subtotal,
            shipping_cost=self.pricing.shipping_cost if self.pricing else 0.0,
            tax_total=self.pricing.tax_total if self.pricing else 0.0,
            discount_total=self.pricing.discount_total if self.pricing else 0.0,
            grand_total=event.new_grand_total,
            currency=self.pricing.currency if self.pricing else "USD",
        )

    @apply
    def _on_item_removed(self, event: ItemRemoved):
        item = next((i for i in self.items if str(i.id) == str(event.item_id)), None)
        if item:
            self.remove_items(item)
        self.pricing = OrderPricing(
            subtotal=event.new_subtotal,
            shipping_cost=self.pricing.shipping_cost if self.pricing else 0.0,
            tax_total=self.pricing.tax_total if self.pricing else 0.0,
            discount_total=self.pricing.discount_total if self.pricing else 0.0,
            grand_total=event.new_grand_total,
            currency=self.pricing.currency if self.pricing else "USD",
        )

    @apply
    def _on_item_quantity_updated(self, event: ItemQuantityUpdated):
        item = next((i for i in self.items if str(i.id) == str(event.item_id)), None)
        if item:
            item.quantity = int(event.new_quantity)
        self.pricing = OrderPricing(
            subtotal=event.new_subtotal,
            shipping_cost=self.pricing.shipping_cost if self.pricing else 0.0,
            tax_total=self.pricing.tax_total if self.pricing else 0.0,
            discount_total=self.pricing.discount_total if self.pricing else 0.0,
            grand_total=event.new_grand_total,
            currency=self.pricing.currency if self.pricing else "USD",
        )

    @apply
    def _on_coupon_applied(self, event: CouponApplied):
        self.coupon_code = event.coupon_code

    @apply
    def _on_order_confirmed(self, event: OrderConfirmed):
        self.status = OrderStatus.CONFIRMED.value
        self.updated_at = event.confirmed_at

    @apply
    def _on_payment_pending(self, event: PaymentPending):
        self.status = OrderStatus.PAYMENT_PENDING.value
        self.payment_id = event.payment_id
        self.payment_method = event.payment_method
        self.payment_status = "pending"

    @apply
    def _on_payment_succeeded(self, event: PaymentSucceeded):
        self.status = OrderStatus.PAID.value
        self.payment_id = event.payment_id
        self.payment_method = event.payment_method
        self.payment_status = "succeeded"

    @apply
    def _on_payment_failed(self, event: PaymentFailed):  # noqa: ARG002
        self.status = OrderStatus.CONFIRMED.value
        self.payment_status = "failed"

    @apply
    def _on_order_processing(self, event: OrderProcessing):
        self.status = OrderStatus.PROCESSING.value
        self.updated_at = event.started_at

    @apply
    def _on_order_shipped(self, event: OrderShipped):
        self.status = OrderStatus.SHIPPED.value
        self.shipment_id = event.shipment_id
        self.carrier = event.carrier
        self.tracking_number = event.tracking_number
        if event.estimated_delivery:
            self.estimated_delivery = event.estimated_delivery
        self.updated_at = event.shipped_at
        for item in self.items:
            item.item_status = ItemStatus.SHIPPED.value

    @apply
    def _on_order_partially_shipped(self, event: OrderPartiallyShipped):
        self.status = OrderStatus.PARTIALLY_SHIPPED.value
        self.shipment_id = event.shipment_id
        self.carrier = event.carrier
        self.tracking_number = event.tracking_number
        self.updated_at = event.shipped_at
        shipped_ids = json.loads(event.shipped_item_ids) if event.shipped_item_ids else []
        for item in self.items:
            if str(item.id) in shipped_ids:
                item.item_status = ItemStatus.SHIPPED.value

    @apply
    def _on_order_delivered(self, event: OrderDelivered):
        self.status = OrderStatus.DELIVERED.value
        self.updated_at = event.delivered_at
        for item in self.items:
            item.item_status = ItemStatus.DELIVERED.value

    @apply
    def _on_order_completed(self, event: OrderCompleted):
        self.status = OrderStatus.COMPLETED.value
        self.updated_at = event.completed_at

    @apply
    def _on_return_requested(self, event: ReturnRequested):
        self.status = OrderStatus.RETURN_REQUESTED.value
        self.updated_at = event.requested_at

    @apply
    def _on_return_approved(self, event: ReturnApproved):
        self.status = OrderStatus.RETURN_APPROVED.value
        self.updated_at = event.approved_at

    @apply
    def _on_order_returned(self, event: OrderReturned):
        self.status = OrderStatus.RETURNED.value
        self.updated_at = event.returned_at
        returned_ids = json.loads(event.returned_item_ids) if event.returned_item_ids else []
        for item in self.items:
            if str(item.id) in returned_ids:
                item.item_status = ItemStatus.RETURNED.value

    @apply
    def _on_order_cancelled(self, event: OrderCancelled):
        self.status = OrderStatus.CANCELLED.value
        self.cancellation_reason = event.reason
        self.cancelled_by = event.cancelled_by
        self.updated_at = event.cancelled_at

    @apply
    def _on_order_refunded(self, event: OrderRefunded):
        self.status = OrderStatus.REFUNDED.value
        self.updated_at = event.refunded_at
