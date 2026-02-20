"""Pydantic request/response schemas for the Payments API.

These are external contracts (anti-corruption layer) — separate from
internal Protean commands.
"""

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared sub-models
# ---------------------------------------------------------------------------
class InvoiceLineItemSchema(BaseModel):
    description: str
    quantity: float = Field(ge=0)
    unit_price: float = Field(ge=0)


# ---------------------------------------------------------------------------
# Payment Request Schemas
# ---------------------------------------------------------------------------
class InitiatePaymentRequest(BaseModel):
    order_id: str
    customer_id: str
    amount: float = Field(gt=0)
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
    amount: float = Field(gt=0)
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
    tax: float = 0.0


class VoidInvoiceRequest(BaseModel):
    reason: str


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------
class PaymentIdResponse(BaseModel):
    payment_id: str


class InvoiceIdResponse(BaseModel):
    invoice_id: str


class StatusResponse(BaseModel):
    status: str


class GatewayConfigResponse(BaseModel):
    gateway: str
    should_succeed: bool
    failure_reason: str
