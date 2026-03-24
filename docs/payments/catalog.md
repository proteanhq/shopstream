# Event & Command Catalog

## DefaultOutbox (`abc.DefaultOutbox`)

## MemoryOutbox (`abc.MemoryOutbox`)

## Invoice (`payments.invoice.invoice.Invoice`)

### Events

#### InvoiceGenerated

- **Type**: `Payments.InvoiceGenerated.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| customer_id | Identifier | Yes | min_length=1 |
| generated_at | DateTime | Yes | — |
| invoice_id | Identifier | Yes | min_length=1 |
| invoice_number | String | Yes | max_length=255, min_length=1 |
| order_id | Identifier | Yes | min_length=1 |
| total | Float | Yes | — |

#### InvoiceIssued

- **Type**: `Payments.InvoiceIssued.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| invoice_id | Identifier | Yes | min_length=1 |
| invoice_number | String | Yes | max_length=255, min_length=1 |
| issued_at | DateTime | Yes | — |
| order_id | Identifier | Yes | min_length=1 |

#### InvoicePaid

- **Type**: `Payments.InvoicePaid.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| invoice_id | Identifier | Yes | min_length=1 |
| order_id | Identifier | Yes | min_length=1 |
| paid_at | DateTime | Yes | — |

#### InvoiceVoided

- **Type**: `Payments.InvoiceVoided.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| invoice_id | Identifier | Yes | min_length=1 |
| order_id | Identifier | Yes | min_length=1 |
| reason | String | Yes | max_length=255, min_length=1 |
| voided_at | DateTime | Yes | — |

### Commands

#### GenerateInvoice

- **Type**: `Payments.GenerateInvoice.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| customer_id | Identifier | Yes | min_length=1 |
| line_items | List[dict] | Yes | — |
| order_id | Identifier | Yes | min_length=1 |
| tax | Float | No | — |

#### VoidInvoice

- **Type**: `Payments.VoidInvoice.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| invoice_id | Identifier | Yes | min_length=1 |
| reason | String | Yes | max_length=500, min_length=1 |

## Payment (`payments.payment.payment.Payment`)

### Events

#### PaymentFailed

- **Type**: `Payments.PaymentFailed.v1`
- **Version**: 1
- **Published**: Yes
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| attempt_number | Integer | Yes | — |
| can_retry | Boolean | Yes | — |
| customer_id | Identifier | Yes | min_length=1 |
| failed_at | DateTime | Yes | — |
| order_id | Identifier | Yes | min_length=1 |
| payment_id | Identifier | Yes | min_length=1 |
| reason | String | Yes | max_length=255, min_length=1 |

#### PaymentInitiated

- **Type**: `Payments.PaymentInitiated.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| amount | Float | Yes | — |
| currency | String | Yes | max_length=255, min_length=1 |
| customer_id | Identifier | Yes | min_length=1 |
| gateway_name | String | Yes | max_length=255, min_length=1 |
| idempotency_key | String | Yes | max_length=255, min_length=1 |
| initiated_at | DateTime | Yes | — |
| last4 | String | No | max_length=255 |
| order_id | Identifier | Yes | min_length=1 |
| payment_id | Identifier | Yes | min_length=1 |
| payment_method_type | String | Yes | max_length=255, min_length=1 |

#### PaymentProcessing

- **Type**: `Payments.PaymentProcessing.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| order_id | Identifier | Yes | min_length=1 |
| payment_id | Identifier | Yes | min_length=1 |
| processing_at | DateTime | Yes | — |

#### PaymentRetryInitiated

- **Type**: `Payments.PaymentRetryInitiated.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| attempt_number | Integer | Yes | — |
| order_id | Identifier | Yes | min_length=1 |
| payment_id | Identifier | Yes | min_length=1 |
| retried_at | DateTime | Yes | — |

#### PaymentSucceeded

- **Type**: `Payments.PaymentSucceeded.v1`
- **Version**: 1
- **Published**: Yes
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| amount | Float | Yes | — |
| currency | String | Yes | max_length=255, min_length=1 |
| customer_id | Identifier | Yes | min_length=1 |
| gateway_transaction_id | String | Yes | max_length=255, min_length=1 |
| order_id | Identifier | Yes | min_length=1 |
| payment_id | Identifier | Yes | min_length=1 |
| succeeded_at | DateTime | Yes | — |

#### RefundCompleted

- **Type**: `Payments.RefundCompleted.v1`
- **Version**: 1
- **Published**: Yes
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| amount | Float | Yes | — |
| completed_at | DateTime | Yes | — |
| gateway_refund_id | String | Yes | max_length=255, min_length=1 |
| order_id | Identifier | Yes | min_length=1 |
| payment_id | Identifier | Yes | min_length=1 |
| refund_id | Identifier | Yes | min_length=1 |

#### RefundRequested

- **Type**: `Payments.RefundRequested.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| amount | Float | Yes | — |
| order_id | Identifier | Yes | min_length=1 |
| payment_id | Identifier | Yes | min_length=1 |
| reason | String | Yes | max_length=255, min_length=1 |
| refund_id | Identifier | Yes | min_length=1 |
| requested_at | DateTime | Yes | — |

### Commands

#### InitiatePayment

- **Type**: `Payments.InitiatePayment.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| amount | Float | Yes | — |
| currency | String | No | max_length=3 |
| customer_id | Identifier | Yes | min_length=1 |
| idempotency_key | String | Yes | max_length=255, min_length=1 |
| last4 | String | No | max_length=4 |
| order_id | Identifier | Yes | min_length=1 |
| payment_method_type | String | Yes | max_length=50, min_length=1 |

#### ProcessRefundWebhook

- **Type**: `Payments.ProcessRefundWebhook.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| gateway_refund_id | String | Yes | max_length=255, min_length=1 |
| payment_id | Identifier | Yes | min_length=1 |
| refund_id | Identifier | Yes | min_length=1 |

#### RequestRefund

- **Type**: `Payments.RequestRefund.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| amount | Float | Yes | — |
| payment_id | Identifier | Yes | min_length=1 |
| reason | String | Yes | max_length=500, min_length=1 |

#### RetryPayment

- **Type**: `Payments.RetryPayment.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| payment_id | Identifier | Yes | min_length=1 |

#### ProcessPaymentWebhook

- **Type**: `Payments.ProcessPaymentWebhook.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| failure_reason | String | No | max_length=500 |
| gateway_status | String | Yes | max_length=50, min_length=1 |
| gateway_transaction_id | String | No | max_length=255 |
| payment_id | Identifier | Yes | min_length=1 |

---

## Published Event Contracts

| Event | Type | Version |
|-------|------|---------|
| PaymentFailed | `Payments.PaymentFailed.v1` | 1 |
| PaymentSucceeded | `Payments.PaymentSucceeded.v1` | 1 |
| RefundCompleted | `Payments.RefundCompleted.v1` | 1 |
