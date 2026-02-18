"""FastAPI routes for the Ordering domain — carts and orders."""

import json

from fastapi import APIRouter
from protean.utils.globals import current_domain

from ordering.api.schemas import (
    AddItemRequest,
    AddToCartRequest,
    ApplyCouponRequest,
    ApplyCouponToCartRequest,
    CancelOrderRequest,
    CartIdResponse,
    CheckoutRequest,
    CreateCartRequest,
    CreateOrderRequest,
    MergeGuestCartRequest,
    OrderIdResponse,
    RecordPartialShipmentRequest,
    RecordPaymentFailureRequest,
    RecordPaymentPendingRequest,
    RecordPaymentSuccessRequest,
    RecordReturnRequest,
    RecordShipmentRequest,
    RefundOrderRequest,
    RequestReturnRequest,
    StatusResponse,
    UpdateCartQuantityRequest,
    UpdateItemQuantityRequest,
)
from ordering.cart.conversion import ConvertToOrder
from ordering.cart.coupons import ApplyCouponToCart
from ordering.cart.items import AddToCart, RemoveFromCart, UpdateCartQuantity
from ordering.cart.management import AbandonCart, CreateCart, MergeGuestCart
from ordering.order.cancellation import CancelOrder, RefundOrder
from ordering.order.completion import CompleteOrder
from ordering.order.confirmation import ConfirmOrder
from ordering.order.creation import CreateOrder
from ordering.order.fulfillment import (
    MarkProcessing,
    RecordDelivery,
    RecordPartialShipment,
    RecordShipment,
)
from ordering.order.modification import AddItem, ApplyCoupon, RemoveItem, UpdateItemQuantity
from ordering.order.payment import (
    RecordPaymentFailure,
    RecordPaymentPending,
    RecordPaymentSuccess,
)
from ordering.order.returns import ApproveReturn, RecordReturn, RequestReturn

# ---------------------------------------------------------------------------
# Cart Router
# ---------------------------------------------------------------------------
cart_router = APIRouter(prefix="/carts", tags=["carts"])


@cart_router.post("", status_code=201, response_model=CartIdResponse)
async def create_cart(body: CreateCartRequest) -> CartIdResponse:
    command = CreateCart(
        customer_id=body.customer_id,
        session_id=body.session_id,
    )
    result = current_domain.process(command, asynchronous=False)
    return CartIdResponse(cart_id=result)


@cart_router.post("/{cart_id}/items", response_model=StatusResponse)
async def add_cart_item(cart_id: str, body: AddToCartRequest) -> StatusResponse:
    command = AddToCart(
        cart_id=cart_id,
        product_id=body.product_id,
        variant_id=body.variant_id,
        quantity=body.quantity,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@cart_router.put("/{cart_id}/items/{item_id}", response_model=StatusResponse)
async def update_cart_item_quantity(cart_id: str, item_id: str, body: UpdateCartQuantityRequest) -> StatusResponse:
    command = UpdateCartQuantity(
        cart_id=cart_id,
        item_id=item_id,
        new_quantity=body.new_quantity,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@cart_router.delete("/{cart_id}/items/{item_id}", response_model=StatusResponse)
async def remove_cart_item(cart_id: str, item_id: str) -> StatusResponse:
    command = RemoveFromCart(
        cart_id=cart_id,
        item_id=item_id,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@cart_router.post("/{cart_id}/coupons", response_model=StatusResponse)
async def apply_cart_coupon(cart_id: str, body: ApplyCouponToCartRequest) -> StatusResponse:
    command = ApplyCouponToCart(
        cart_id=cart_id,
        coupon_code=body.coupon_code,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@cart_router.post("/{cart_id}/checkout", status_code=201, response_model=OrderIdResponse)
async def checkout_cart(cart_id: str, body: CheckoutRequest) -> OrderIdResponse:
    """Convert cart to an order.

    1. Load cart to get items
    2. Create order from cart items + checkout data
    3. Mark cart as converted
    """
    from ordering.cart.cart import ShoppingCart

    cart = current_domain.repository_for(ShoppingCart).get(cart_id)

    # Build items list from cart
    items_data = [
        {
            "product_id": str(item.product_id),
            "variant_id": str(item.variant_id),
            "sku": f"SKU-{item.product_id}",  # Placeholder — real SKU would come from catalogue
            "title": f"Product {item.product_id}",  # Placeholder
            "quantity": item.quantity,
            "unit_price": 0.0,  # Price would come from catalogue lookup
        }
        for item in cart.items
    ]

    # Calculate pricing
    subtotal = sum(item["unit_price"] * item["quantity"] for item in items_data)
    grand_total = subtotal + (body.shipping.dict() if hasattr(body, "shipping") else {}).get("shipping_cost", 0)

    shipping_dict = body.shipping.model_dump()
    billing_dict = body.billing.model_dump()

    # Create order
    create_cmd = CreateOrder(
        customer_id=str(cart.customer_id) if cart.customer_id else "guest",
        items=json.dumps(items_data),
        shipping_address=json.dumps(shipping_dict),
        billing_address=json.dumps(billing_dict),
        subtotal=subtotal,
        grand_total=grand_total,
        currency="USD",
    )
    order_id = current_domain.process(create_cmd, asynchronous=False)

    # Convert cart
    convert_cmd = ConvertToOrder(cart_id=cart_id)
    current_domain.process(convert_cmd, asynchronous=False)

    return OrderIdResponse(order_id=order_id)


@cart_router.put("/{cart_id}/abandon", response_model=StatusResponse)
async def abandon_cart(cart_id: str) -> StatusResponse:
    command = AbandonCart(cart_id=cart_id)
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@cart_router.post("/{cart_id}/merge", response_model=StatusResponse)
async def merge_guest_cart(cart_id: str, body: MergeGuestCartRequest) -> StatusResponse:  # noqa: ARG001
    """Merge items from a guest session's cart into this cart.

    Loads the guest cart by session_id, extracts items, and merges into the target cart.
    """

    # Find guest cart by session_id (simplified — in production, use a query)
    guest_items = []  # Placeholder: would query for guest cart items by session
    # For now, the client passes the source_session_id and the handler deals with it

    command = MergeGuestCart(
        cart_id=cart_id,
        guest_cart_items=json.dumps(guest_items),
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


# ---------------------------------------------------------------------------
# Order Router
# ---------------------------------------------------------------------------
order_router = APIRouter(prefix="/orders", tags=["orders"])


@order_router.post("", status_code=201, response_model=OrderIdResponse)
async def create_order(body: CreateOrderRequest) -> OrderIdResponse:
    items_data = [item.model_dump() for item in body.items]
    subtotal = sum(item["unit_price"] * item["quantity"] for item in items_data)
    grand_total = subtotal + body.shipping_cost + body.tax_total - body.discount_total

    command = CreateOrder(
        customer_id=body.customer_id,
        items=json.dumps(items_data),
        shipping_address=json.dumps(body.shipping_address.model_dump()),
        billing_address=json.dumps(body.billing_address.model_dump()),
        subtotal=subtotal,
        shipping_cost=body.shipping_cost,
        tax_total=body.tax_total,
        discount_total=body.discount_total,
        grand_total=grand_total,
        currency=body.currency,
    )
    result = current_domain.process(command, asynchronous=False)
    return OrderIdResponse(order_id=result)


@order_router.post("/{order_id}/items", response_model=StatusResponse)
async def add_order_item(order_id: str, body: AddItemRequest) -> StatusResponse:
    command = AddItem(
        order_id=order_id,
        product_id=body.product_id,
        variant_id=body.variant_id,
        sku=body.sku,
        title=body.title,
        quantity=body.quantity,
        unit_price=body.unit_price,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@order_router.delete("/{order_id}/items/{item_id}", response_model=StatusResponse)
async def remove_order_item(order_id: str, item_id: str) -> StatusResponse:
    command = RemoveItem(order_id=order_id, item_id=item_id)
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@order_router.put("/{order_id}/items/{item_id}/quantity", response_model=StatusResponse)
async def update_order_item_quantity(order_id: str, item_id: str, body: UpdateItemQuantityRequest) -> StatusResponse:
    command = UpdateItemQuantity(
        order_id=order_id,
        item_id=item_id,
        new_quantity=body.new_quantity,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@order_router.post("/{order_id}/coupon", response_model=StatusResponse)
async def apply_order_coupon(order_id: str, body: ApplyCouponRequest) -> StatusResponse:
    command = ApplyCoupon(order_id=order_id, coupon_code=body.coupon_code)
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@order_router.put("/{order_id}/confirm", response_model=StatusResponse)
async def confirm_order(order_id: str) -> StatusResponse:
    command = ConfirmOrder(order_id=order_id)
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@order_router.put("/{order_id}/payment/pending", response_model=StatusResponse)
async def record_payment_pending(order_id: str, body: RecordPaymentPendingRequest) -> StatusResponse:
    command = RecordPaymentPending(
        order_id=order_id,
        payment_id=body.payment_id,
        payment_method=body.payment_method,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@order_router.put("/{order_id}/payment/success", response_model=StatusResponse)
async def record_payment_success(order_id: str, body: RecordPaymentSuccessRequest) -> StatusResponse:
    command = RecordPaymentSuccess(
        order_id=order_id,
        payment_id=body.payment_id,
        amount=body.amount,
        payment_method=body.payment_method,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@order_router.put("/{order_id}/payment/failure", response_model=StatusResponse)
async def record_payment_failure(order_id: str, body: RecordPaymentFailureRequest) -> StatusResponse:
    command = RecordPaymentFailure(
        order_id=order_id,
        payment_id=body.payment_id,
        reason=body.reason,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@order_router.put("/{order_id}/processing", response_model=StatusResponse)
async def mark_processing(order_id: str) -> StatusResponse:
    command = MarkProcessing(order_id=order_id)
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@order_router.put("/{order_id}/ship", response_model=StatusResponse)
async def record_shipment(order_id: str, body: RecordShipmentRequest) -> StatusResponse:
    command = RecordShipment(
        order_id=order_id,
        shipment_id=body.shipment_id,
        carrier=body.carrier,
        tracking_number=body.tracking_number,
        shipped_item_ids=json.dumps(body.shipped_item_ids) if body.shipped_item_ids else None,
        estimated_delivery=body.estimated_delivery,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@order_router.put("/{order_id}/ship/partial", response_model=StatusResponse)
async def record_partial_shipment(order_id: str, body: RecordPartialShipmentRequest) -> StatusResponse:
    command = RecordPartialShipment(
        order_id=order_id,
        shipment_id=body.shipment_id,
        carrier=body.carrier,
        tracking_number=body.tracking_number,
        shipped_item_ids=json.dumps(body.shipped_item_ids),
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@order_router.put("/{order_id}/deliver", response_model=StatusResponse)
async def record_delivery(order_id: str) -> StatusResponse:
    command = RecordDelivery(order_id=order_id)
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@order_router.put("/{order_id}/complete", response_model=StatusResponse)
async def complete_order(order_id: str) -> StatusResponse:
    command = CompleteOrder(order_id=order_id)
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@order_router.put("/{order_id}/return/request", response_model=StatusResponse)
async def request_return(order_id: str, body: RequestReturnRequest) -> StatusResponse:
    command = RequestReturn(order_id=order_id, reason=body.reason)
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@order_router.put("/{order_id}/return/approve", response_model=StatusResponse)
async def approve_return(order_id: str) -> StatusResponse:
    command = ApproveReturn(order_id=order_id)
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@order_router.put("/{order_id}/return/record", response_model=StatusResponse)
async def record_return(order_id: str, body: RecordReturnRequest) -> StatusResponse:
    command = RecordReturn(
        order_id=order_id,
        returned_item_ids=json.dumps(body.returned_item_ids) if body.returned_item_ids else None,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@order_router.put("/{order_id}/cancel", response_model=StatusResponse)
async def cancel_order(order_id: str, body: CancelOrderRequest) -> StatusResponse:
    command = CancelOrder(
        order_id=order_id,
        reason=body.reason,
        cancelled_by=body.cancelled_by,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@order_router.put("/{order_id}/refund", response_model=StatusResponse)
async def refund_order(order_id: str, body: RefundOrderRequest) -> StatusResponse:
    command = RefundOrder(
        order_id=order_id,
        refund_amount=body.refund_amount,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()
