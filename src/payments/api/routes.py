"""FastAPI routes for the Payments domain — payments and invoices."""

import json
import os

from fastapi import APIRouter, Header, HTTPException
from protean.utils.globals import current_domain

from payments.api.schemas import (
    ConfigureGatewayRequest,
    GatewayConfigResponse,
    GenerateInvoiceRequest,
    InitiatePaymentRequest,
    InvoiceIdResponse,
    PaymentIdResponse,
    ProcessRefundWebhookRequest,
    ProcessWebhookRequest,
    RefundIdResponse,
    RequestRefundRequest,
    StatusResponse,
    VoidInvoiceRequest,
)
from payments.gateway import get_gateway
from payments.gateway.fake_adapter import FakeGateway
from payments.invoice.generation import GenerateInvoice
from payments.invoice.voiding import VoidInvoice
from payments.payment.initiation import InitiatePayment
from payments.payment.refund import ProcessRefundWebhook, RequestRefund
from payments.payment.retry import RetryPayment
from payments.payment.webhook import ProcessPaymentWebhook

# ---------------------------------------------------------------------------
# Payment Router
# ---------------------------------------------------------------------------
payment_router = APIRouter(prefix="/payments", tags=["payments"])


@payment_router.post("", status_code=201, response_model=PaymentIdResponse)
async def initiate_payment(body: InitiatePaymentRequest) -> PaymentIdResponse:
    """Initiate a new payment for an order."""
    command = InitiatePayment(
        order_id=body.order_id,
        customer_id=body.customer_id,
        amount=body.amount,
        currency=body.currency,
        payment_method_type=body.payment_method_type,
        last4=body.last4,
        idempotency_key=body.idempotency_key,
    )
    result = current_domain.process(command, asynchronous=False)
    return PaymentIdResponse(payment_id=result)


@payment_router.post("/webhook", response_model=StatusResponse)
async def process_webhook(
    body: ProcessWebhookRequest,
    x_gateway_signature: str = Header(default=""),
) -> StatusResponse:
    """Process a payment gateway webhook callback."""
    gateway = get_gateway()
    if not gateway.verify_webhook_signature(json.dumps(body.model_dump()), x_gateway_signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    command = ProcessPaymentWebhook(
        payment_id=body.payment_id,
        gateway_transaction_id=body.gateway_transaction_id,
        gateway_status=body.gateway_status,
        failure_reason=body.failure_reason,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse(status="processed")


@payment_router.post("/{payment_id}/retry", response_model=StatusResponse)
async def retry_payment(payment_id: str) -> StatusResponse:
    """Retry a failed payment."""
    command = RetryPayment(payment_id=payment_id)
    current_domain.process(command, asynchronous=False)
    return StatusResponse(status="retry_initiated")


@payment_router.post("/{payment_id}/refund", response_model=RefundIdResponse)
async def request_refund(payment_id: str, body: RequestRefundRequest) -> RefundIdResponse:
    """Request a refund for a payment."""
    command = RequestRefund(
        payment_id=payment_id,
        amount=body.amount,
        reason=body.reason,
    )
    refund_id = current_domain.process(command, asynchronous=False)
    return RefundIdResponse(refund_id=refund_id)


@payment_router.post("/refund/webhook", response_model=StatusResponse)
async def process_refund_webhook(
    body: ProcessRefundWebhookRequest,
    x_gateway_signature: str = Header(default=""),
) -> StatusResponse:
    """Process a refund confirmation from the gateway."""
    gateway = get_gateway()
    if not gateway.verify_webhook_signature(json.dumps(body.model_dump()), x_gateway_signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    command = ProcessRefundWebhook(
        payment_id=body.payment_id,
        refund_id=body.refund_id,
        gateway_refund_id=body.gateway_refund_id,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse(status="refund_processed")


@payment_router.post("/gateway/configure", response_model=GatewayConfigResponse)
async def configure_gateway(body: ConfigureGatewayRequest) -> GatewayConfigResponse:
    """Configure the FakeGateway behavior (non-production only).

    This endpoint is only available when PROTEAN_ENV is not 'production'.
    It allows toggling success/failure behavior for manual API testing.
    """
    if os.environ.get("PROTEAN_ENV") == "production":
        raise HTTPException(status_code=403, detail="Gateway configuration not available in production")

    gateway = get_gateway()
    if not isinstance(gateway, FakeGateway):
        raise HTTPException(status_code=400, detail="Gateway configuration only available for FakeGateway")

    gateway.configure(
        should_succeed=body.should_succeed,
        failure_reason=body.failure_reason,
    )
    return GatewayConfigResponse(
        gateway=type(gateway).__name__,
        should_succeed=gateway.should_succeed,
        failure_reason=gateway.failure_reason,
    )


# ---------------------------------------------------------------------------
# Invoice Router
# ---------------------------------------------------------------------------
invoice_router = APIRouter(prefix="/invoices", tags=["invoices"])


@invoice_router.post("", status_code=201, response_model=InvoiceIdResponse)
async def generate_invoice(body: GenerateInvoiceRequest) -> InvoiceIdResponse:
    """Generate a new invoice for an order."""
    line_items_json = json.dumps([item.model_dump() for item in body.line_items])
    command = GenerateInvoice(
        order_id=body.order_id,
        customer_id=body.customer_id,
        line_items=line_items_json,
        tax=body.tax,
    )
    result = current_domain.process(command, asynchronous=False)
    return InvoiceIdResponse(invoice_id=result)


@invoice_router.put("/{invoice_id}/void", response_model=StatusResponse)
async def void_invoice(invoice_id: str, body: VoidInvoiceRequest) -> StatusResponse:
    """Void an existing invoice."""
    command = VoidInvoice(
        invoice_id=invoice_id,
        reason=body.reason,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse(status="voided")
