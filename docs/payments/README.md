# Payments & Billing Domain

## Business Context

The Payments & Billing domain handles all financial transactions for ShopStream. It provides:

- **Complete audit trail** via event sourcing on the Payment aggregate
- **Gateway abstraction** for swapping payment processors without domain changes
- **Idempotent payment processing** via idempotency keys
- **Multi-attempt retry** with configurable limits (max 3 attempts)
- **Partial and full refund** support with cumulative amount guards
- **Invoice generation** for completed orders

The Payment aggregate is **event-sourced** (like Order and InventoryItem) because financial data requires:
- Immutable record of every charge attempt, gateway interaction, and refund
- Temporal queries ("what was the payment state at 3pm?")
- Natural alignment with the multi-step payment lifecycle

## Ubiquitous Language

| Term | Definition |
|------|-----------|
| Payment | A financial transaction for an order, tracking charge attempts and refunds |
| Payment Attempt | A single try to charge the customer's payment method |
| Refund | A return of funds to the customer (partial or full) |
| Gateway | External payment processor (Stripe, etc.) abstracted behind a port |
| Idempotency Key | Unique key ensuring the same payment isn't processed twice |
| Invoice | A billing document generated after successful payment |
| Webhook | Asynchronous notification from the gateway about payment status |

## Domain Model

### Payment Aggregate (Event-Sourced)

```
Payment (aggregate root)
  |-- Money (value object: currency + value)
  |-- PaymentMethod (value object: type, last4, expiry)
  |-- GatewayInfo (value object: gateway_name, transaction_id, status)
  |-- PaymentAttempt (entity: attempted_at, status, failure_reason)
  |-- Refund (entity: amount, reason, status, gateway_refund_id)
```

**State Machine:**
```
PENDING --> PROCESSING --> SUCCEEDED --> REFUNDED
                |                  |
                v                  +--> PARTIALLY_REFUNDED --> REFUNDED
              FAILED --> PENDING (retry, max 3)
```

### Invoice Aggregate (CQRS)

```
Invoice (aggregate root)
  |-- InvoiceLineItem (entity: description, quantity, unit_price, total)
```

**State Machine:**
```
DRAFT --> ISSUED --> PAID
  |         |
  +----+----+
       v
     VOIDED
```

### Enums

| Enum | Values |
|------|--------|
| `PaymentStatus` | Pending, Processing, Succeeded, Failed, Refunded, Partially_Refunded |
| `RefundStatus` | Requested, Processing, Completed, Failed |
| `InvoiceStatus` | Draft, Issued, Paid, Voided |

## Events

### Payment Events (6)

| Event | Description | Key Fields |
|-------|------------|-----------|
| `PaymentInitiated` | New payment created | payment_id, order_id, amount, currency, gateway_name |
| `PaymentSucceeded` | Gateway confirmed charge | payment_id, gateway_transaction_id |
| `PaymentFailed` | Gateway rejected charge | payment_id, reason, attempt_number, can_retry |
| `PaymentRetryInitiated` | Failed payment retried | payment_id, attempt_number |
| `RefundRequested` | Refund requested | payment_id, refund_id, amount, reason |
| `RefundCompleted` | Gateway confirmed refund | payment_id, refund_id, gateway_refund_id |

### Invoice Events (4)

| Event | Description |
|-------|------------|
| `InvoiceGenerated` | New invoice created for an order |
| `InvoiceIssued` | Invoice sent to customer |
| `InvoicePaid` | Invoice marked as paid |
| `InvoiceVoided` | Invoice cancelled |

## Command Flows

| Command | Handler | Action |
|---------|---------|--------|
| `InitiatePayment` | `InitiatePaymentHandler` | Create Payment aggregate via gateway |
| `ProcessPaymentWebhook` | `ProcessWebhookHandler` | Record success/failure from gateway |
| `RetryPayment` | `RetryPaymentHandler` | Retry failed payment (max 3 attempts) |
| `RequestRefund` | `RefundHandler` | Request refund with amount + reason |
| `ProcessRefundWebhook` | `RefundHandler` | Complete refund from gateway confirmation |
| `GenerateInvoice` | `GenerateInvoiceHandler` | Create invoice with line items |
| `VoidInvoice` | `VoidInvoiceHandler` | Cancel an invoice |

## Read Models (Projections)

| Projection | Purpose | Updated By |
|-----------|---------|-----------|
| `PaymentStatusView` | Real-time payment state | All payment events |
| `CustomerPayment` | Payment history per customer | Initiated, Succeeded, Failed, Refunded |
| `DailyRevenue` | Revenue totals per day | Succeeded, RefundCompleted |
| `FailedPayment` | Operations monitoring | Failed, RetryInitiated, Succeeded |
| `RefundReport` | Finance reconciliation | RefundRequested, RefundCompleted |

## Gateway Abstraction

The `PaymentGateway` port defines the interface:

```python
class PaymentGateway(ABC):
    def create_charge(...) -> ChargeResult
    def create_refund(...) -> RefundResult
    def verify_webhook_signature(...) -> bool
```

### Adapters

| Adapter | Environment | Description |
|---------|------------|-------------|
| `FakeGateway` | dev, test | Configurable success/failure, call logging |
| `StripeGateway` | production | Stub for Stripe SDK integration |

### Real-Time API Testing

The FakeGateway + configure endpoint enables manual API testing:

```bash
# 1. Configure gateway to succeed (default)
curl -X POST http://localhost:8000/payments/gateway/configure \
  -H "Content-Type: application/json" \
  -d '{"should_succeed": true}'

# 2. Initiate payment
curl -X POST http://localhost:8000/payments \
  -H "Content-Type: application/json" \
  -d '{"order_id":"ord-1","customer_id":"cust-1","amount":59.99,...}'

# 3. Simulate webhook success
curl -X POST http://localhost:8000/payments/webhook \
  -H "Content-Type: application/json" \
  -H "X-Gateway-Signature: test-signature" \
  -d '{"payment_id":"pay-xxx","gateway_transaction_id":"txn-1","gateway_status":"succeeded"}'

# 4. Test failure flow
curl -X POST http://localhost:8000/payments/gateway/configure \
  -d '{"should_succeed": false, "failure_reason": "Insufficient funds"}'
```

## Cross-Context Relationships

### Order Checkout Saga (ProcessManager)

The `OrderCheckoutSaga` in the ordering domain coordinates:

```
OrderConfirmed --> [await inventory] --> StockReserved --> [issue RecordPaymentPending]
  --> PaymentSucceeded --> [issue RecordPaymentSuccess] --> COMPLETED
  --> PaymentFailed (can retry) --> RETRYING
  --> PaymentFailed (max retries) --> [issue CancelOrder] --> FAILED
  --> ReservationReleased --> [issue CancelOrder] --> FAILED
```

Cross-domain events are consumed via `shared.events` module and registered
with `ordering.register_external_event()`.

### Shared Events Module

```
src/shared/events/
  inventory.py  -- StockReserved, ReservationReleased
  payments.py   -- PaymentSucceeded, PaymentFailed
```

## Design Decisions

1. **Event Sourcing for Payment** - Financial data needs complete audit trail; every attempt, gateway response, and refund is captured as an immutable event.

2. **CQRS for Invoice** - Invoices are simpler documents that don't need temporal queries or event replay. Standard CQRS is sufficient.

3. **FakeGateway for Development** - Follows Stripe's test mode pattern. The configure endpoint allows toggling success/failure behavior for realistic manual testing without real gateway credentials.

4. **Idempotency Keys** - Every payment carries a unique idempotency key to prevent duplicate charges. This is standard practice for payment systems.

5. **Max 3 Attempts** - Payment retries are capped at 3 to prevent infinite retry loops. After exhaustion, the saga cancels the order.

6. **Saga in Ordering Domain** - The OrderCheckoutSaga lives in ordering because it primarily coordinates order state changes and dispatches ordering commands.

## Source Code Map

```
src/payments/
  domain.py                     # Domain composition root
  domain.toml                   # Config (DB, broker, event store)
  payment/
    payment.py                  # Aggregate + VOs + entities + enums + @apply
    events.py                   # 6 domain events
    initiation.py               # InitiatePayment command + handler
    webhook.py                  # ProcessPaymentWebhook command + handler
    retry.py                    # RetryPayment command + handler
    refund.py                   # RequestRefund + ProcessRefundWebhook + handler
  invoice/
    invoice.py                  # Aggregate + entity + enums
    events.py                   # 4 domain events
    generation.py               # GenerateInvoice command + handler
    voiding.py                  # VoidInvoice command + handler
  projections/
    payment_status.py           # Real-time payment state
    customer_payments.py        # Payment history by customer
    daily_revenue.py            # Revenue analytics
    failed_payments.py          # Operations monitoring
    refund_report.py            # Finance reconciliation
  gateway/
    __init__.py                 # get_gateway()/set_gateway() factory
    port.py                     # PaymentGateway ABC
    fake_adapter.py             # Configurable fake for dev/test
    stripe_adapter.py           # Production stub
  api/
    schemas.py                  # Pydantic request/response models
    routes.py                   # FastAPI endpoints (9 routes)

src/shared/events/
  inventory.py                  # StockReserved, ReservationReleased
  payments.py                   # PaymentSucceeded, PaymentFailed

src/ordering/checkout/
  saga.py                       # OrderCheckoutSaga ProcessManager
```
