"""Shared BDD fixtures and step definitions for the Ordering domain."""

import json
from datetime import UTC, datetime

import pytest
from ordering.cart.cart import ShoppingCart
from ordering.cart.events import (
    CartAbandoned,
    CartConverted,
    CartCouponApplied,
    CartItemAdded,
    CartItemRemoved,
    CartQuantityUpdated,
    CartsMerged,
)
from ordering.order.cancellation import RefundOrder
from ordering.order.completion import CompleteOrder
from ordering.order.confirmation import ConfirmOrder
from ordering.order.creation import CreateOrder
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
from ordering.order.fulfillment import MarkProcessing, RecordDelivery, RecordShipment
from ordering.order.order import Order
from ordering.order.payment import RecordPaymentPending
from ordering.order.returns import ApproveReturn, RecordReturn
from protean.exceptions import ValidationError
from protean.testing import given as given_
from pytest_bdd import given, parsers, then

# Map event name strings to classes for dynamic lookup in Then steps
_ORDER_EVENT_CLASSES = {
    "OrderCreated": OrderCreated,
    "ItemAdded": ItemAdded,
    "ItemRemoved": ItemRemoved,
    "ItemQuantityUpdated": ItemQuantityUpdated,
    "CouponApplied": CouponApplied,
    "OrderConfirmed": OrderConfirmed,
    "PaymentPending": PaymentPending,
    "PaymentSucceeded": PaymentSucceeded,
    "PaymentFailed": PaymentFailed,
    "OrderProcessing": OrderProcessing,
    "OrderShipped": OrderShipped,
    "OrderPartiallyShipped": OrderPartiallyShipped,
    "OrderDelivered": OrderDelivered,
    "OrderCompleted": OrderCompleted,
    "ReturnRequested": ReturnRequested,
    "ReturnApproved": ReturnApproved,
    "OrderReturned": OrderReturned,
    "OrderCancelled": OrderCancelled,
    "OrderRefunded": OrderRefunded,
}

_CART_EVENT_CLASSES = {
    "CartItemAdded": CartItemAdded,
    "CartQuantityUpdated": CartQuantityUpdated,
    "CartItemRemoved": CartItemRemoved,
    "CartCouponApplied": CartCouponApplied,
    "CartsMerged": CartsMerged,
    "CartConverted": CartConverted,
    "CartAbandoned": CartAbandoned,
}


# ---------------------------------------------------------------------------
# Scalar fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def order_id():
    return "ord-001"


@pytest.fixture()
def customer_id():
    return "cust-001"


@pytest.fixture()
def error():
    """Container for captured validation errors (used by cart tests)."""
    return {"exc": None}


# ---------------------------------------------------------------------------
# Event fixtures (past tense — what happened)
# ---------------------------------------------------------------------------
@pytest.fixture()
def order_created(order_id, customer_id):
    return OrderCreated(
        order_id=order_id,
        customer_id=customer_id,
        items=json.dumps(
            [
                {
                    "id": "item-1",
                    "product_id": "prod-001",
                    "variant_id": "var-001",
                    "sku": "SKU-001",
                    "title": "Test Product",
                    "quantity": 2,
                    "unit_price": 25.0,
                }
            ]
        ),
        shipping_address=json.dumps(
            {
                "street": "123 Main St",
                "city": "Springfield",
                "state": "IL",
                "postal_code": "62701",
                "country": "US",
            }
        ),
        billing_address=json.dumps(
            {
                "street": "123 Main St",
                "city": "Springfield",
                "state": "IL",
                "postal_code": "62701",
                "country": "US",
            }
        ),
        subtotal=50.0,
        shipping_cost=5.0,
        tax_total=4.0,
        discount_total=0.0,
        grand_total=59.0,
        currency="USD",
        created_at=datetime.now(UTC),
    )


@pytest.fixture()
def order_confirmed(order_id):
    return OrderConfirmed(order_id=order_id, confirmed_at=datetime.now(UTC))


@pytest.fixture()
def payment_pending(order_id):
    return PaymentPending(order_id=order_id, payment_id="pay-001", payment_method="credit_card")


@pytest.fixture()
def payment_succeeded(order_id):
    return PaymentSucceeded(
        order_id=order_id,
        payment_id="pay-001",
        amount=59.0,
        payment_method="credit_card",
    )


@pytest.fixture()
def order_processing(order_id):
    return OrderProcessing(order_id=order_id, started_at=datetime.now(UTC))


@pytest.fixture()
def order_shipped(order_id):
    return OrderShipped(
        order_id=order_id,
        shipment_id="ship-001",
        carrier="FedEx",
        tracking_number="TRACK-001",
        shipped_item_ids=json.dumps(["item-1"]),
        shipped_at=datetime.now(UTC),
    )


@pytest.fixture()
def order_delivered(order_id):
    return OrderDelivered(order_id=order_id, delivered_at=datetime.now(UTC))


@pytest.fixture()
def return_requested(order_id):
    return ReturnRequested(
        order_id=order_id,
        reason="Defective product",
        requested_at=datetime.now(UTC),
    )


@pytest.fixture()
def return_approved(order_id):
    return ReturnApproved(order_id=order_id, approved_at=datetime.now(UTC))


@pytest.fixture()
def order_returned(order_id):
    return OrderReturned(
        order_id=order_id,
        returned_item_ids=json.dumps(["item-1"]),
        returned_at=datetime.now(UTC),
    )


@pytest.fixture()
def order_cancelled(order_id):
    return OrderCancelled(
        order_id=order_id,
        reason="Changed my mind",
        cancelled_by="Customer",
        cancelled_at=datetime.now(UTC),
    )


@pytest.fixture()
def order_completed(order_id):
    return OrderCompleted(order_id=order_id, completed_at=datetime.now(UTC))


@pytest.fixture()
def order_refunded(order_id):
    return OrderRefunded(order_id=order_id, refund_amount=59.0, refunded_at=datetime.now(UTC))


# ---------------------------------------------------------------------------
# Command fixtures (imperative — what to do)
# ---------------------------------------------------------------------------
@pytest.fixture()
def create_order(customer_id):
    return CreateOrder(
        customer_id=customer_id,
        items=json.dumps(
            [
                {
                    "product_id": "prod-001",
                    "variant_id": "var-001",
                    "sku": "SKU-001",
                    "title": "Test Product",
                    "quantity": 2,
                    "unit_price": 25.0,
                }
            ]
        ),
        shipping_address=json.dumps(
            {
                "street": "123 Main St",
                "city": "Springfield",
                "state": "IL",
                "postal_code": "62701",
                "country": "US",
            }
        ),
        billing_address=json.dumps(
            {
                "street": "123 Main St",
                "city": "Springfield",
                "state": "IL",
                "postal_code": "62701",
                "country": "US",
            }
        ),
        subtotal=50.0,
        shipping_cost=5.0,
        tax_total=4.0,
        discount_total=0.0,
        grand_total=59.0,
        currency="USD",
    )


@pytest.fixture()
def confirm_order(order_id):
    return ConfirmOrder(order_id=order_id)


@pytest.fixture()
def initiate_payment(order_id):
    return RecordPaymentPending(order_id=order_id, payment_id="pay-001", payment_method="credit_card")


@pytest.fixture()
def mark_processing(order_id):
    return MarkProcessing(order_id=order_id)


@pytest.fixture()
def ship_order(order_id):
    return RecordShipment(
        order_id=order_id,
        shipment_id="ship-001",
        carrier="FedEx",
        tracking_number="TRACK-001",
    )


@pytest.fixture()
def deliver_order(order_id):
    return RecordDelivery(order_id=order_id)


@pytest.fixture()
def complete_order(order_id):
    return CompleteOrder(order_id=order_id)


@pytest.fixture()
def approve_return(order_id):
    return ApproveReturn(order_id=order_id)


@pytest.fixture()
def record_return(order_id):
    return RecordReturn(order_id=order_id)


@pytest.fixture()
def refund_order(order_id):
    return RefundOrder(order_id=order_id)


# ---------------------------------------------------------------------------
# Given steps — Order (event sourcing via protean.testing)
# ---------------------------------------------------------------------------
@given("an order was created", target_fixture="order")
def _(order_created):
    return given_(Order, order_created)


@given("the order was confirmed", target_fixture="order")
def _(order, order_confirmed):
    return order.after(order_confirmed)


@given("the order payment is pending", target_fixture="order")
def _(order, payment_pending):
    return order.after(payment_pending)


@given("the order was paid", target_fixture="order")
def _(order, payment_succeeded):
    return order.after(payment_succeeded)


@given("the order is processing", target_fixture="order")
def _(order, order_processing):
    return order.after(order_processing)


@given("the order was shipped", target_fixture="order")
def _(order, order_shipped):
    return order.after(order_shipped)


@given("the order was delivered", target_fixture="order")
def _(order, order_delivered):
    return order.after(order_delivered)


@given("a return was requested", target_fixture="order")
def _(order, return_requested):
    return order.after(return_requested)


@given("the return was approved", target_fixture="order")
def _(order, return_approved):
    return order.after(return_approved)


@given("the order was returned", target_fixture="order")
def _(order, order_returned):
    return order.after(order_returned)


@given("the order was cancelled", target_fixture="order")
def _(order, order_cancelled):
    return order.after(order_cancelled)


@given("the order was completed", target_fixture="order")
def _(order, order_completed):
    return order.after(order_completed)


@given("the order was refunded", target_fixture="order")
def _(order, order_refunded):
    return order.after(order_refunded)


# ---------------------------------------------------------------------------
# Given steps — Shopping Cart (standard DDD, unchanged)
# ---------------------------------------------------------------------------
@given("an active cart", target_fixture="cart")
def active_cart():
    cart = ShoppingCart.create(customer_id="cust-001")
    cart._events.clear()
    return cart


@given("a guest cart", target_fixture="cart")
def guest_cart():
    cart = ShoppingCart.create(session_id="sess-001")
    cart._events.clear()
    return cart


@given("the cart has an item", target_fixture="cart")
def cart_with_item(cart):
    cart.add_item(product_id="prod-001", variant_id="var-001", quantity=2)
    cart._events.clear()
    return cart


@given("the cart has 2 items", target_fixture="cart")
def cart_with_two_items(cart):
    cart.add_item(product_id="prod-001", variant_id="var-001", quantity=2)
    cart.add_item(product_id="prod-002", variant_id="var-002", quantity=1)
    cart._events.clear()
    return cart


@given("the cart has a coupon applied", target_fixture="cart")
def cart_with_coupon(cart):
    cart.apply_coupon("SAVE10")
    cart._events.clear()
    return cart


@given("the cart is converted", target_fixture="cart")
def converted_cart(cart):
    if not cart.items:
        cart.add_item(product_id="prod-001", variant_id="var-001", quantity=1)
    cart.convert_to_order()
    cart._events.clear()
    return cart


@given("the cart is abandoned", target_fixture="cart")
def abandoned_cart(cart):
    cart.abandon()
    cart._events.clear()
    return cart


# ---------------------------------------------------------------------------
# Then steps — Order (shared, plain assertions)
# ---------------------------------------------------------------------------
@then(parsers.cfparse('the order status is "{status}"'))
def _(order, status):
    assert order.status == status


@then("the order action fails with a validation error")
def _(order):
    assert order.rejected
    assert isinstance(order.rejection, ValidationError)


@then(parsers.cfparse("an {event_type} order event is raised"))
def _(order, event_type):
    event_cls = _ORDER_EVENT_CLASSES[event_type]
    assert event_cls in order.events


@then(parsers.cfparse("a {event_type} order event is raised"))
def _(order, event_type):
    event_cls = _ORDER_EVENT_CLASSES[event_type]
    assert event_cls in order.events


# ---------------------------------------------------------------------------
# Then steps — Cart (shared, unchanged)
# ---------------------------------------------------------------------------
@then(parsers.cfparse('the cart status is "{status}"'))
def cart_status_is(cart, status):
    assert cart.status == status


@then("the cart action fails with a validation error")
def cart_action_fails(error):
    assert error["exc"] is not None, "Expected a validation error but none was raised"
    assert isinstance(error["exc"], ValidationError)


@then(parsers.cfparse("a {event_type} cart event is raised"))
def cart_event_raised(cart, event_type):
    event_cls = _CART_EVENT_CLASSES[event_type]
    assert any(
        isinstance(e, event_cls) for e in cart._events
    ), f"No {event_type} event found. Events: {[type(e).__name__ for e in cart._events]}"
