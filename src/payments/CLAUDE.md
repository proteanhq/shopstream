# Payments Domain

Payment lifecycle (event-sourced), refunds, invoice generation (CQRS), and gateway abstraction.

## Domain Composition Root

`domain.py` — `payments = Domain(name="payments")`

All elements register via `@payments.<element_type>` decorators.

## Configuration

`domain.toml` — PostgreSQL database, Redis broker, Message DB event store. Priority lanes enabled. Environment overlays for test (`payments_test` DB) and production (`payments` DB, async events).

## Aggregate: Payment (Event-Sourced)

**File:** `payment/payment.py`

Root fields: `order_id`, `customer_id`, `amount` (Money VO), `status` (PaymentStatus enum), `payment_method` (PaymentMethod VO), `gateway_info` (GatewayInfo VO), `attempts` (HasMany PaymentAttempt), `refunds` (HasMany Refund), `attempt_count` (default 0), `total_refunded` (default 0.0), `idempotency_key`, `created_at`, `updated_at`.

### Enums
- `PaymentStatus`: Pending, Processing, Succeeded, Failed, Refunded, Partially_Refunded
- `RefundStatus`: Requested, Processing, Completed, Failed

### State Machine
```
Pending              → Processing, Succeeded, Failed
Processing           → Succeeded, Failed
Failed               → Pending (retry, max 3 attempts)
Succeeded            → Refunded, Partially_Refunded
Partially_Refunded   → Refunded
Refunded             → (terminal)
```

### Value Objects (part_of="Payment")
- `Money` — currency (default "USD"), value (Float)
- `PaymentMethod` — method_type (credit_card/debit_card/bank_transfer), last4, expiry_month, expiry_year
- `GatewayInfo` — gateway_name, gateway_transaction_id, gateway_status, gateway_response

### Entities (part_of="Payment")
- `PaymentAttempt` — attempted_at, status (processing/succeeded/failed), failure_reason, gateway_transaction_id
- `Refund` — amount, reason, status (RefundStatus), requested_at, processed_at, gateway_refund_id

### Aggregate Methods
| Method | Behavior |
|--------|----------|
| `Payment.create(order_id, customer_id, amount, currency, payment_method_type, last4, gateway_name, idempotency_key)` | Factory, event-sourced `_create_new()`, raises `PaymentInitiated` |
| `record_processing()` | Validates transition to Processing |
| `record_success(gateway_transaction_id)` | → Succeeded, raises `PaymentSucceeded` |
| `record_failure(reason)` | → Failed, computes can_retry, raises `PaymentFailed` |
| `can_retry()` | Returns True if Failed and attempt_count < 3 |
| `retry()` | Failed → Pending, raises `PaymentRetryInitiated` |
| `request_refund(amount, reason)` | Succeeded/Partially_Refunded only, validates ceiling, raises `RefundRequested`, returns refund_id |
| `complete_refund(refund_id, gateway_refund_id)` | Finds Requested refund, raises `RefundCompleted`, auto-transitions to Refunded or Partially_Refunded |

All state changes applied via `@apply` handlers for event-sourcing replay.

## Aggregate: Invoice (CQRS)

**File:** `invoice/invoice.py`

Root fields: `order_id`, `customer_id`, `invoice_number` (auto-generated INV-XXXXXXXX), `line_items` (HasMany InvoiceLineItem), `subtotal`, `tax`, `total`, `status` (InvoiceStatus enum), `issued_at`, `paid_at`, `created_at`, `updated_at`.

### Enums
- `InvoiceStatus`: Draft, Issued, Paid, Voided

### State Machine
```
Draft  → Issued, Voided
Issued → Paid, Voided
Paid   → (terminal)
Voided → (terminal)
```

### Entities (part_of="Invoice")
- `InvoiceLineItem` — description, quantity, unit_price, total

### Aggregate Methods
| Method | Behavior |
|--------|----------|
| `Invoice.create(order_id, customer_id, line_items_data, tax?)` | Factory, generates invoice_number, computes totals, raises `InvoiceGenerated` |
| `issue()` | Draft → Issued, raises `InvoiceIssued` |
| `mark_paid()` | Issued → Paid, raises `InvoicePaid` |
| `void(reason)` | Draft/Issued → Voided, raises `InvoiceVoided` |

## Events

**Payment events** (`payment/events.py`): `PaymentInitiated`, `PaymentSucceeded`, `PaymentFailed`, `PaymentRetryInitiated`, `RefundRequested`, `RefundCompleted`

**Invoice events** (`invoice/events.py`): `InvoiceGenerated`, `InvoiceIssued`, `InvoicePaid`, `InvoiceVoided`

## Commands & Handlers

### Payment Commands

| File | Commands |
|------|---------|
| `payment/initiation.py` | `InitiatePayment` → `InitiatePaymentHandler` (resolves gateway, creates Payment) |
| `payment/webhook.py` | `ProcessPaymentWebhook` → `ProcessWebhookHandler` (routes to record_success/record_failure based on gateway_status) |
| `payment/retry.py` | `RetryPayment` → `RetryPaymentHandler` |
| `payment/refund.py` | `RequestRefund`, `ProcessRefundWebhook` → `RefundHandler` |

### Invoice Commands

| File | Commands |
|------|---------|
| `invoice/generation.py` | `GenerateInvoice` → `GenerateInvoiceHandler` |
| `invoice/voiding.py` | `VoidInvoice` → `VoidInvoiceHandler` |

## Gateway Abstraction

**Directory:** `gateway/`

| File | Contents |
|------|----------|
| `gateway/port.py` | `PaymentGateway` ABC — `create_charge()`, `create_refund()`, `verify_webhook_signature()`. Data classes: `ChargeResult`, `RefundResult`. |
| `gateway/fake_adapter.py` | `FakeGateway` — configurable success/failure for dev/testing, records all calls |
| `gateway/stripe_adapter.py` | `StripeGateway` — production stub (raises NotImplementedError) |
| `gateway/__init__.py` | `get_gateway()` / `set_gateway()` / `reset_gateway()` — singleton factory |

## Projections

**Directory:** `projections/`

| File | Projection | Projector | Purpose |
|------|-----------|-----------|---------|
| `payment_status.py` | `PaymentStatusView` | `PaymentStatusProjector` | Payment status with gateway details, attempt count, refund totals |
| `customer_payments.py` | `CustomerPayment` | `CustomerPaymentProjector` | Per-customer payment listing |
| `failed_payments.py` | `FailedPayment` | `FailedPaymentProjector` | Failed payments with retry tracking (status: failed/retrying/recovered) |
| `daily_revenue.py` | `DailyRevenue` | `DailyRevenueProjector` | Daily revenue/refund aggregation (keyed by YYYY-MM-DD) |
| `refund_report.py` | `RefundReport` | `RefundReportProjector` | Individual refund tracking (requested → completed) |

## Cross-Domain Integration

### Outbound: Payments → Ordering
Events marked `published=True` (`PaymentSucceeded`, `PaymentFailed`, `PaymentInitiated`) are dual-written to the external bus for consumption by Ordering's checkout subscribers.

### Inbound: Ordering → Payments
**File:** `payment/ordering_subscriber.py`

`@payments.subscriber(broker="global", stream="ordering::order")` — receives raw dict payloads (ACL pattern).

Subscriber `OrderingEventsSubscriber`:
- `OrderReturned` → dispatches `RequestRefund` command

## API

**Package:** `api/`

| File | Contents |
|------|----------|
| `api/__init__.py` | Re-exports `payment_router` and `invoice_router` |
| `api/schemas.py` | Pydantic request/response models (external contract) |
| `api/routes.py` | 8 endpoints (6 payment + 2 invoice) |

### Payment Endpoints (`tags=["payments"]`)
| Method | Path | Request Body | Response |
|--------|------|-------------|----------|
| POST | `/payments` | `InitiatePaymentRequest` | `PaymentIdResponse` (201) |
| POST | `/payments/webhook` | `ProcessWebhookRequest` + `X-Gateway-Signature` header | `StatusResponse` |
| POST | `/payments/{payment_id}/retry` | — | `StatusResponse` |
| POST | `/payments/{payment_id}/refund` | `RequestRefundRequest` | `StatusResponse` |
| POST | `/payments/refund/webhook` | `ProcessRefundWebhookRequest` + `X-Gateway-Signature` header | `StatusResponse` |
| POST | `/payments/gateway/configure` | `ConfigureGatewayRequest` | `GatewayConfigResponse` (non-production only) |

### Invoice Endpoints (`tags=["invoices"]`)
| Method | Path | Request Body | Response |
|--------|------|-------------|----------|
| POST | `/invoices` | `GenerateInvoiceRequest` | `InvoiceIdResponse` (201) |
| PUT | `/invoices/{invoice_id}/void` | `VoidInvoiceRequest` | `StatusResponse` |
