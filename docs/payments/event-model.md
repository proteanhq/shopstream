## Event Model: Invoice

> **Given** Invoice
> **When** GenerateInvoice, VoidInvoice
> **Then** InvoiceGenerated, InvoiceIssued, InvoicePaid, InvoiceVoided

```mermaid
flowchart LR
    subgraph payments_invoice_invoice_Invoice[Invoice]
        cmd_payments_invoice_generation_GenerateInvoice[/GenerateInvoice/]
        cmd_payments_invoice_voiding_VoidInvoice[/VoidInvoice/]
        agg_payments_invoice_invoice_Invoice[Invoice]
        evt_payments_invoice_events_InvoiceGenerated([InvoiceGenerated])
        evt_payments_invoice_events_InvoiceIssued([InvoiceIssued])
        evt_payments_invoice_events_InvoicePaid([InvoicePaid])
        evt_payments_invoice_events_InvoiceVoided([InvoiceVoided])
        rm_payments_invoice_invoice_Invoice_payments_projections_invoice_status_InvoiceStatusProjector[(InvoiceStatusProjector → InvoiceStatusView)]
    end
    cmd_payments_invoice_generation_GenerateInvoice --> agg_payments_invoice_invoice_Invoice
    cmd_payments_invoice_voiding_VoidInvoice --> agg_payments_invoice_invoice_Invoice
    agg_payments_invoice_invoice_Invoice --> evt_payments_invoice_events_InvoiceGenerated
    evt_payments_invoice_events_InvoiceGenerated --> rm_payments_invoice_invoice_Invoice_payments_projections_invoice_status_InvoiceStatusProjector
    agg_payments_invoice_invoice_Invoice --> evt_payments_invoice_events_InvoiceIssued
    evt_payments_invoice_events_InvoiceIssued --> rm_payments_invoice_invoice_Invoice_payments_projections_invoice_status_InvoiceStatusProjector
    agg_payments_invoice_invoice_Invoice --> evt_payments_invoice_events_InvoicePaid
    evt_payments_invoice_events_InvoicePaid --> rm_payments_invoice_invoice_Invoice_payments_projections_invoice_status_InvoiceStatusProjector
    agg_payments_invoice_invoice_Invoice --> evt_payments_invoice_events_InvoiceVoided
    evt_payments_invoice_events_InvoiceVoided --> rm_payments_invoice_invoice_Invoice_payments_projections_invoice_status_InvoiceStatusProjector
```

## Event Model: Payment

> **Given** Payment
> **When** InitiatePayment, ProcessRefundWebhook, RequestRefund, RetryPayment, ProcessPaymentWebhook
> **Then** PaymentFailed, PaymentInitiated, PaymentProcessing, PaymentRetryInitiated, PaymentSucceeded, RefundCompleted, RefundRequested

```mermaid
flowchart LR
    subgraph payments_payment_payment_Payment[Payment]
        cmd_payments_payment_initiation_InitiatePayment[/InitiatePayment/]
        cmd_payments_payment_refund_ProcessRefundWebhook[/ProcessRefundWebhook/]
        cmd_payments_payment_refund_RequestRefund[/RequestRefund/]
        cmd_payments_payment_retry_RetryPayment[/RetryPayment/]
        cmd_payments_payment_webhook_ProcessPaymentWebhook[/ProcessPaymentWebhook/]
        agg_payments_payment_payment_Payment[Payment]
        evt_payments_payment_events_PaymentFailed([PaymentFailed])
        evt_payments_payment_events_PaymentInitiated([PaymentInitiated])
        evt_payments_payment_events_PaymentProcessing([PaymentProcessing])
        evt_payments_payment_events_PaymentRetryInitiated([PaymentRetryInitiated])
        evt_payments_payment_events_PaymentSucceeded([PaymentSucceeded])
        evt_payments_payment_events_RefundCompleted([RefundCompleted])
        evt_payments_payment_events_RefundRequested([RefundRequested])
        rm_payments_payment_payment_Payment_payments_projections_customer_payments_CustomerPaymentProjector[(CustomerPaymentProjector → CustomerPayment)]
        rm_payments_payment_payment_Payment_payments_projections_daily_revenue_DailyRevenueProjector[(DailyRevenueProjector → DailyRevenue)]
        rm_payments_payment_payment_Payment_payments_projections_failed_payments_FailedPaymentProjector[(FailedPaymentProjector → FailedPayment)]
        rm_payments_payment_payment_Payment_payments_projections_payment_status_PaymentStatusProjector[(PaymentStatusProjector → PaymentStatusView)]
        rm_payments_payment_payment_Payment_payments_projections_refund_report_RefundReportProjector[(RefundReportProjector → RefundReport)]
    end
    cmd_payments_payment_initiation_InitiatePayment --> agg_payments_payment_payment_Payment
    cmd_payments_payment_refund_ProcessRefundWebhook --> agg_payments_payment_payment_Payment
    cmd_payments_payment_refund_RequestRefund --> agg_payments_payment_payment_Payment
    cmd_payments_payment_retry_RetryPayment --> agg_payments_payment_payment_Payment
    cmd_payments_payment_webhook_ProcessPaymentWebhook --> agg_payments_payment_payment_Payment
    agg_payments_payment_payment_Payment --> evt_payments_payment_events_PaymentFailed
    evt_payments_payment_events_PaymentFailed --> rm_payments_payment_payment_Payment_payments_projections_customer_payments_CustomerPaymentProjector
    evt_payments_payment_events_PaymentFailed --> rm_payments_payment_payment_Payment_payments_projections_failed_payments_FailedPaymentProjector
    evt_payments_payment_events_PaymentFailed --> rm_payments_payment_payment_Payment_payments_projections_payment_status_PaymentStatusProjector
    agg_payments_payment_payment_Payment --> evt_payments_payment_events_PaymentInitiated
    evt_payments_payment_events_PaymentInitiated --> rm_payments_payment_payment_Payment_payments_projections_customer_payments_CustomerPaymentProjector
    evt_payments_payment_events_PaymentInitiated --> rm_payments_payment_payment_Payment_payments_projections_payment_status_PaymentStatusProjector
    agg_payments_payment_payment_Payment --> evt_payments_payment_events_PaymentProcessing
    evt_payments_payment_events_PaymentProcessing --> rm_payments_payment_payment_Payment_payments_projections_payment_status_PaymentStatusProjector
    agg_payments_payment_payment_Payment --> evt_payments_payment_events_PaymentRetryInitiated
    evt_payments_payment_events_PaymentRetryInitiated --> rm_payments_payment_payment_Payment_payments_projections_failed_payments_FailedPaymentProjector
    evt_payments_payment_events_PaymentRetryInitiated --> rm_payments_payment_payment_Payment_payments_projections_payment_status_PaymentStatusProjector
    agg_payments_payment_payment_Payment --> evt_payments_payment_events_PaymentSucceeded
    evt_payments_payment_events_PaymentSucceeded --> rm_payments_payment_payment_Payment_payments_projections_customer_payments_CustomerPaymentProjector
    evt_payments_payment_events_PaymentSucceeded --> rm_payments_payment_payment_Payment_payments_projections_daily_revenue_DailyRevenueProjector
    evt_payments_payment_events_PaymentSucceeded --> rm_payments_payment_payment_Payment_payments_projections_failed_payments_FailedPaymentProjector
    evt_payments_payment_events_PaymentSucceeded --> rm_payments_payment_payment_Payment_payments_projections_payment_status_PaymentStatusProjector
    agg_payments_payment_payment_Payment --> evt_payments_payment_events_RefundCompleted
    evt_payments_payment_events_RefundCompleted --> rm_payments_payment_payment_Payment_payments_projections_customer_payments_CustomerPaymentProjector
    evt_payments_payment_events_RefundCompleted --> rm_payments_payment_payment_Payment_payments_projections_daily_revenue_DailyRevenueProjector
    evt_payments_payment_events_RefundCompleted --> rm_payments_payment_payment_Payment_payments_projections_payment_status_PaymentStatusProjector
    evt_payments_payment_events_RefundCompleted --> rm_payments_payment_payment_Payment_payments_projections_refund_report_RefundReportProjector
    agg_payments_payment_payment_Payment --> evt_payments_payment_events_RefundRequested
    evt_payments_payment_events_RefundRequested --> rm_payments_payment_payment_Payment_payments_projections_payment_status_PaymentStatusProjector
    evt_payments_payment_events_RefundRequested --> rm_payments_payment_payment_Payment_payments_projections_refund_report_RefundReportProjector
```
