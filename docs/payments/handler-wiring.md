## Command Handlers: Invoice

```mermaid
flowchart LR
    subgraph command_handlers["Command Handlers"]
        ch_payments_invoice_generation_GenerateInvoiceHandler[GenerateInvoiceHandler]
        ch_payments_invoice_voiding_VoidInvoiceHandler[VoidInvoiceHandler]
    end
    cmd_payments_invoice_generation_GenerateInvoice[/GenerateInvoice/] --> ch_payments_invoice_generation_GenerateInvoiceHandler
    ch_payments_invoice_generation_GenerateInvoiceHandler --> agg_payments_invoice_invoice_Invoice[Invoice]
    cmd_payments_invoice_voiding_VoidInvoice[/VoidInvoice/] --> ch_payments_invoice_voiding_VoidInvoiceHandler
    ch_payments_invoice_voiding_VoidInvoiceHandler --> agg_payments_invoice_invoice_Invoice[Invoice]
```

## Command Handlers: Payment

```mermaid
flowchart LR
    subgraph command_handlers["Command Handlers"]
        ch_payments_payment_initiation_InitiatePaymentHandler[InitiatePaymentHandler]
        ch_payments_payment_refund_RefundHandler[RefundHandler]
        ch_payments_payment_retry_RetryPaymentHandler[RetryPaymentHandler]
        ch_payments_payment_webhook_ProcessWebhookHandler[ProcessWebhookHandler]
    end
    cmd_payments_payment_initiation_InitiatePayment[/InitiatePayment/] --> ch_payments_payment_initiation_InitiatePaymentHandler
    ch_payments_payment_initiation_InitiatePaymentHandler --> agg_payments_payment_payment_Payment[Payment]
    cmd_payments_payment_refund_ProcessRefundWebhook[/ProcessRefundWebhook/] --> ch_payments_payment_refund_RefundHandler
    cmd_payments_payment_refund_RequestRefund[/RequestRefund/] --> ch_payments_payment_refund_RefundHandler
    ch_payments_payment_refund_RefundHandler --> agg_payments_payment_payment_Payment[Payment]
    cmd_payments_payment_retry_RetryPayment[/RetryPayment/] --> ch_payments_payment_retry_RetryPaymentHandler
    ch_payments_payment_retry_RetryPaymentHandler --> agg_payments_payment_payment_Payment[Payment]
    cmd_payments_payment_webhook_ProcessPaymentWebhook[/ProcessPaymentWebhook/] --> ch_payments_payment_webhook_ProcessWebhookHandler
    ch_payments_payment_webhook_ProcessWebhookHandler --> agg_payments_payment_payment_Payment[Payment]
```

## Subscribers

```mermaid
flowchart TD
    subgraph subscribers["Subscribers"]
        sub_payments_payment_ordering_subscriber_OrderReturnedSubscriber[OrderReturnedSubscriber\nstream: ordering::order]
    end
```

## Projector: CustomerPayment

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_payments_projections_customer_payments_CustomerPaymentProjector[CustomerPaymentProjector → CustomerPayment]
    end
    evt_payments_payment_events_PaymentFailed([PaymentFailed]) --> proj_payments_projections_customer_payments_CustomerPaymentProjector
    evt_payments_payment_events_PaymentInitiated([PaymentInitiated]) --> proj_payments_projections_customer_payments_CustomerPaymentProjector
    evt_payments_payment_events_PaymentSucceeded([PaymentSucceeded]) --> proj_payments_projections_customer_payments_CustomerPaymentProjector
    evt_payments_payment_events_RefundCompleted([RefundCompleted]) --> proj_payments_projections_customer_payments_CustomerPaymentProjector
```

## Projector: DailyRevenue

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_payments_projections_daily_revenue_DailyRevenueProjector[DailyRevenueProjector → DailyRevenue]
    end
    evt_payments_payment_events_PaymentSucceeded([PaymentSucceeded]) --> proj_payments_projections_daily_revenue_DailyRevenueProjector
    evt_payments_payment_events_RefundCompleted([RefundCompleted]) --> proj_payments_projections_daily_revenue_DailyRevenueProjector
```

## Projector: FailedPayment

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_payments_projections_failed_payments_FailedPaymentProjector[FailedPaymentProjector → FailedPayment]
    end
    evt_payments_payment_events_PaymentFailed([PaymentFailed]) --> proj_payments_projections_failed_payments_FailedPaymentProjector
    evt_payments_payment_events_PaymentRetryInitiated([PaymentRetryInitiated]) --> proj_payments_projections_failed_payments_FailedPaymentProjector
    evt_payments_payment_events_PaymentSucceeded([PaymentSucceeded]) --> proj_payments_projections_failed_payments_FailedPaymentProjector
```

## Projector: InvoiceStatusView

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_payments_projections_invoice_status_InvoiceStatusProjector[InvoiceStatusProjector → InvoiceStatusView]
    end
    evt_payments_invoice_events_InvoiceGenerated([InvoiceGenerated]) --> proj_payments_projections_invoice_status_InvoiceStatusProjector
    evt_payments_invoice_events_InvoiceIssued([InvoiceIssued]) --> proj_payments_projections_invoice_status_InvoiceStatusProjector
    evt_payments_invoice_events_InvoicePaid([InvoicePaid]) --> proj_payments_projections_invoice_status_InvoiceStatusProjector
    evt_payments_invoice_events_InvoiceVoided([InvoiceVoided]) --> proj_payments_projections_invoice_status_InvoiceStatusProjector
```

## Projector: PaymentStatusView

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_payments_projections_payment_status_PaymentStatusProjector[PaymentStatusProjector → PaymentStatusView]
    end
    evt_payments_payment_events_PaymentFailed([PaymentFailed]) --> proj_payments_projections_payment_status_PaymentStatusProjector
    evt_payments_payment_events_PaymentInitiated([PaymentInitiated]) --> proj_payments_projections_payment_status_PaymentStatusProjector
    evt_payments_payment_events_PaymentProcessing([PaymentProcessing]) --> proj_payments_projections_payment_status_PaymentStatusProjector
    evt_payments_payment_events_PaymentRetryInitiated([PaymentRetryInitiated]) --> proj_payments_projections_payment_status_PaymentStatusProjector
    evt_payments_payment_events_PaymentSucceeded([PaymentSucceeded]) --> proj_payments_projections_payment_status_PaymentStatusProjector
    evt_payments_payment_events_RefundCompleted([RefundCompleted]) --> proj_payments_projections_payment_status_PaymentStatusProjector
    evt_payments_payment_events_RefundRequested([RefundRequested]) --> proj_payments_projections_payment_status_PaymentStatusProjector
```

## Projector: RefundReport

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_payments_projections_refund_report_RefundReportProjector[RefundReportProjector → RefundReport]
    end
    evt_payments_payment_events_RefundCompleted([RefundCompleted]) --> proj_payments_projections_refund_report_RefundReportProjector
    evt_payments_payment_events_RefundRequested([RefundRequested]) --> proj_payments_projections_refund_report_RefundReportProjector
```
