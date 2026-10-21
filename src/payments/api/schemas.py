"""Pydantic request/response schemas for the Payments API.

These are external contracts (anti-corruption layer) — separate from
internal Protean commands.
"""

from decimal import Decimal

from pydantic import BaseModel, Field, field_serializer

from shared.api.money import MoneyIn
from shared.money import to_money


# ---------------------------------------------------------------------------
# Shared sub-models
# ---------------------------------------------------------------------------
class InvoiceLineItemSchema(BaseModel):
    description: str
    quantity: float = Field(ge=0)
    unit_price: MoneyIn = Field(ge=0)


# ---------------------------------------------------------------------------
# Payment Request Schemas
# ---------------------------------------------------------------------------
class InitiatePaymentRequest(BaseModel):
    order_id: str
    customer_id: str
    # A plain Decimal, not MoneyIn: the Payment aggregate checks places and
    # size itself and answers with a 400 that names the amount.
    amount: Decimal = Field(gt=0)
    currency: str = "USD"
    payment_method_type: str
    last4: str | None = None
    idempotency_key: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "order_id": "ord-001",
                    "customer_id": "cust-001",
                    "amount": 59.99,
                    "currency": "USD",
                    "payment_method_type": "credit_card",
                    "last4": "4242",
                    "idempotency_key": "idem-001",
                }
            ]
        }
    }


class ProcessWebhookRequest(BaseModel):
    payment_id: str
    gateway_transaction_id: str | None = None
    gateway_status: str  # succeeded, failed
    failure_reason: str | None = None


class RetryPaymentRequest(BaseModel):
    pass


class RequestRefundRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    reason: str


class ProcessRefundWebhookRequest(BaseModel):
    payment_id: str
    refund_id: str
    gateway_refund_id: str


class ConfigureGatewayRequest(BaseModel):
    should_succeed: bool = True
    failure_reason: str = "Card declined"


# ---------------------------------------------------------------------------
# Invoice Request Schemas
# ---------------------------------------------------------------------------
class GenerateInvoiceRequest(BaseModel):
    order_id: str
    customer_id: str
    line_items: list[InvoiceLineItemSchema]
    tax: MoneyIn = Decimal("0")


class VoidInvoiceRequest(BaseModel):
    reason: str


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------
class PaymentIdResponse(BaseModel):
    payment_id: str


class InvoiceIdResponse(BaseModel):
    invoice_id: str


class RefundIdResponse(BaseModel):
    refund_id: str


class StatusResponse(BaseModel):
    status: str


class GatewayConfigResponse(BaseModel):
    gateway: str
    should_succeed: bool
    failure_reason: str


# ---------------------------------------------------------------------------
# Read Response Schemas
# ---------------------------------------------------------------------------
class PaymentStatusResponse(BaseModel):
    payment_id: str
    order_id: str
    customer_id: str
    amount: Decimal | None = None
    currency: str | None = None
    status: str
    gateway_transaction_id: str | None = None
    attempt_count: int | None = None
    failure_reason: str | None = None
    total_refunded: Decimal | None = None
    created_at: str | None = None
    updated_at: str | None = None

    @field_serializer("amount", "total_refunded")
    def _money_as_string(self, value: Decimal | None) -> str | None:
        # Protean's Decimal(scale=4) limits the number of places but does not
        # pad to them, so the memory store returns the Decimal("0") default as
        # "0". Postgres NUMERIC(19, 4) pads to "0.0000". Both are sent padded.
        return None if value is None else str(to_money(value))
