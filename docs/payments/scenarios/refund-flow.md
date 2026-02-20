# Refund Flow Scenarios

## Full Refund

```
Prerequisites: Payment in Succeeded state

1. API: POST /payments/{id}/refund
   └─ RequestRefund(amount=100.00, reason="Defective product")
   └─ Refund entity created (status: Requested)
   └─ RefundRequested event raised

2. Gateway processes refund (simulated via webhook)
   └─ API: POST /payments/refund/webhook
   └─ ProcessRefundWebhook(refund_id, gateway_refund_id)
   └─ Refund entity updated (status: Completed)
   └─ RefundCompleted event raised

3. Payment aggregate state:
   └─ total_refunded: 100.00
   └─ status: Refunded (total_refunded >= amount)
```

## Partial Refund

```
Prerequisites: Payment of $100.00 in Succeeded state

1. First refund: $40.00
   └─ POST /payments/{id}/refund (amount=40.00, reason="Partial return")
   └─ RefundRequested event

2. Gateway confirms first refund
   └─ POST /payments/refund/webhook
   └─ RefundCompleted event
   └─ Payment status: Partially_Refunded
   └─ total_refunded: 40.00

3. Second refund: $60.00
   └─ POST /payments/{id}/refund (amount=60.00, reason="Remaining items")
   └─ RefundRequested event

4. Gateway confirms second refund
   └─ POST /payments/refund/webhook
   └─ RefundCompleted event
   └─ Payment status: Refunded
   └─ total_refunded: 100.00
```

## Refund Guards

- **Amount exceeds payment**: Attempting to refund more than the payment amount raises a ValidationError
- **Cumulative check**: Sum of all completed refunds + pending refund cannot exceed original payment amount
- **State check**: Refunds only allowed from Succeeded or Partially_Refunded states
- **Idempotent**: Each refund has a unique refund_id, preventing duplicate processing

## Manual Testing via API

```bash
# 1. Create and succeed a payment
curl -X POST http://localhost:8000/payments \
  -d '{"order_id":"ord-1","customer_id":"cust-1","amount":100.00,"payment_method_type":"credit_card","idempotency_key":"test-1"}'
# Returns: {"payment_id": "pay-xxx"}

curl -X POST http://localhost:8000/payments/webhook \
  -H "X-Gateway-Signature: test-signature" \
  -d '{"payment_id":"pay-xxx","gateway_transaction_id":"txn-1","gateway_status":"succeeded"}'

# 2. Request partial refund
curl -X POST http://localhost:8000/payments/pay-xxx/refund \
  -d '{"amount": 40.00, "reason": "Partial return"}'

# 3. Complete refund via webhook
curl -X POST http://localhost:8000/payments/refund/webhook \
  -H "X-Gateway-Signature: test-signature" \
  -d '{"payment_id":"pay-xxx","refund_id":"<refund-id>","gateway_refund_id":"gw-ref-1"}'
```
