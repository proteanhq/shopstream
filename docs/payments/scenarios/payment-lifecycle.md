# Payment Lifecycle Scenarios

## Happy Path: Successful Payment

```
1. Customer confirms order
   └─ OrderConfirmed event raised

2. Saga receives OrderConfirmed
   └─ Sets status: awaiting_reservation

3. Inventory reserves stock
   └─ StockReserved event raised

4. Saga receives StockReserved
   └─ Issues RecordPaymentPending command
   └─ Sets status: awaiting_payment

5. API: POST /payments
   └─ InitiatePayment command processed
   └─ Payment aggregate created (status: Pending)
   └─ PaymentInitiated event raised

6. Gateway processes charge (simulated via webhook)
   └─ API: POST /payments/webhook (gateway_status: succeeded)
   └─ ProcessPaymentWebhook command processed
   └─ Payment status: Succeeded
   └─ PaymentSucceeded event raised

7. Saga receives PaymentSucceeded
   └─ Issues RecordPaymentSuccess command
   └─ Order status: Paid
   └─ Saga status: completed (marked as complete)
```

## Failure Path: Payment Declined with Retry

```
1-4. Same as happy path (order confirmed, stock reserved)

5. API: POST /payments
   └─ Payment created (status: Pending)

6. Gateway declines charge
   └─ API: POST /payments/webhook (gateway_status: failed)
   └─ Payment status: Failed
   └─ PaymentFailed event (can_retry: true, attempt: 1)

7. Saga receives PaymentFailed (can_retry: true)
   └─ Saga status: retrying

8. API: POST /payments/{id}/retry
   └─ RetryPayment command processed
   └─ Payment status: Pending (attempt 2)
   └─ PaymentRetryInitiated event

9. Gateway succeeds on retry
   └─ API: POST /payments/webhook (succeeded)
   └─ Payment status: Succeeded
   └─ Flow continues as happy path step 7
```

## Failure Path: Payment Exhausts All Retries

```
1-4. Same as above

5-8. Payment fails and retries (3 times total)

9. Final attempt fails
   └─ PaymentFailed event (can_retry: false, attempt: 3)

10. Saga receives PaymentFailed (can_retry: false)
    └─ Issues CancelOrder command
    └─ Order status: Cancelled
    └─ Saga status: failed (marked as complete)
```

## Failure Path: Reservation Released (Timeout)

```
1-4. Same as above (order confirmed, awaiting payment)

5. Reservation times out before payment completes
   └─ ReservationReleased event (reason: timeout)

6. Saga receives ReservationReleased
   └─ Issues CancelOrder command
   └─ Order status: Cancelled
   └─ Saga status: failed (marked as complete)
```
