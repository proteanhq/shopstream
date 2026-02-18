"""Pydantic request/response schemas for the Ordering API.

These are external contracts (anti-corruption layer) — separate from
internal Protean commands.
"""

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared sub-models
# ---------------------------------------------------------------------------
class AddressSchema(BaseModel):
    street: str
    city: str
    state: str | None = None
    postal_code: str
    country: str


class OrderItemSchema(BaseModel):
    product_id: str
    variant_id: str
    sku: str
    title: str
    quantity: int = Field(ge=1)
    unit_price: float = Field(ge=0)


# ---------------------------------------------------------------------------
# Cart Request Schemas
# ---------------------------------------------------------------------------
class CreateCartRequest(BaseModel):
    customer_id: str | None = None
    session_id: str | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "customer_id": "cust-001",
                    "session_id": None,
                }
            ]
        }
    }


class AddToCartRequest(BaseModel):
    product_id: str
    variant_id: str
    quantity: int = Field(ge=1, default=1)


class UpdateCartQuantityRequest(BaseModel):
    new_quantity: int = Field(ge=1)


class ApplyCouponToCartRequest(BaseModel):
    coupon_code: str


class MergeGuestCartRequest(BaseModel):
    source_session_id: str


class CheckoutRequest(BaseModel):
    shipping: AddressSchema
    billing: AddressSchema
    payment_method: str | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "shipping": {
                        "street": "123 Main St",
                        "city": "Springfield",
                        "state": "IL",
                        "postal_code": "62701",
                        "country": "US",
                    },
                    "billing": {
                        "street": "123 Main St",
                        "city": "Springfield",
                        "state": "IL",
                        "postal_code": "62701",
                        "country": "US",
                    },
                    "payment_method": "credit_card",
                }
            ]
        }
    }


# ---------------------------------------------------------------------------
# Order Request Schemas
# ---------------------------------------------------------------------------
class CreateOrderRequest(BaseModel):
    customer_id: str
    items: list[OrderItemSchema]
    shipping_address: AddressSchema
    billing_address: AddressSchema
    shipping_cost: float = 0.0
    tax_total: float = 0.0
    discount_total: float = 0.0
    currency: str = "USD"

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "customer_id": "cust-001",
                    "items": [
                        {
                            "product_id": "prod-001",
                            "variant_id": "var-001",
                            "sku": "TSHIRT-BLK-M",
                            "title": "Black T-Shirt (M)",
                            "quantity": 2,
                            "unit_price": 29.99,
                        }
                    ],
                    "shipping_address": {
                        "street": "123 Main St",
                        "city": "Springfield",
                        "state": "IL",
                        "postal_code": "62701",
                        "country": "US",
                    },
                    "billing_address": {
                        "street": "123 Main St",
                        "city": "Springfield",
                        "state": "IL",
                        "postal_code": "62701",
                        "country": "US",
                    },
                }
            ]
        }
    }


class AddItemRequest(BaseModel):
    product_id: str
    variant_id: str
    sku: str
    title: str
    quantity: int = Field(ge=1)
    unit_price: float = Field(ge=0)


class UpdateItemQuantityRequest(BaseModel):
    new_quantity: int = Field(ge=1)


class ApplyCouponRequest(BaseModel):
    coupon_code: str


class RecordPaymentPendingRequest(BaseModel):
    payment_id: str
    payment_method: str


class RecordPaymentSuccessRequest(BaseModel):
    payment_id: str
    amount: float
    payment_method: str


class RecordPaymentFailureRequest(BaseModel):
    payment_id: str
    reason: str


class RecordShipmentRequest(BaseModel):
    shipment_id: str
    carrier: str
    tracking_number: str
    shipped_item_ids: list[str] | None = None
    estimated_delivery: str | None = None


class RecordPartialShipmentRequest(BaseModel):
    shipment_id: str
    carrier: str
    tracking_number: str
    shipped_item_ids: list[str]


class RequestReturnRequest(BaseModel):
    reason: str


class RecordReturnRequest(BaseModel):
    returned_item_ids: list[str] | None = None


class CancelOrderRequest(BaseModel):
    reason: str
    cancelled_by: str


class RefundOrderRequest(BaseModel):
    refund_amount: float | None = None


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------
class CartIdResponse(BaseModel):
    cart_id: str


class OrderIdResponse(BaseModel):
    order_id: str


class StatusResponse(BaseModel):
    status: str = "ok"
