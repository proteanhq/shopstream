## Event Flows

```mermaid
flowchart LR
    subgraph ordering_cart_cart_ShoppingCart[ShoppingCart]
        agg_ordering_cart_cart_ShoppingCart[ShoppingCart]
        cmd_ordering_cart_abandonment_DetectAbandonedCarts[/DetectAbandonedCarts/]
        cmd_ordering_cart_conversion_ConvertToOrder[/ConvertToOrder/]
        cmd_ordering_cart_coupons_ApplyCouponToCart[/ApplyCouponToCart/]
        cmd_ordering_cart_items_AddToCart[/AddToCart/]
        cmd_ordering_cart_items_RemoveFromCart[/RemoveFromCart/]
        cmd_ordering_cart_items_UpdateCartQuantity[/UpdateCartQuantity/]
        cmd_ordering_cart_management_AbandonCart[/AbandonCart/]
        cmd_ordering_cart_management_CreateCart[/CreateCart/]
        cmd_ordering_cart_management_MergeGuestCart[/MergeGuestCart/]
        evt_ordering_cart_events_CartAbandoned([CartAbandoned])
        evt_ordering_cart_events_CartConverted([CartConverted])
        evt_ordering_cart_events_CartCouponApplied([CartCouponApplied])
        evt_ordering_cart_events_CartItemAdded([CartItemAdded])
        evt_ordering_cart_events_CartItemRemoved([CartItemRemoved])
        evt_ordering_cart_events_CartQuantityUpdated([CartQuantityUpdated])
        evt_ordering_cart_events_CartsMerged([CartsMerged])
        hdlr_ordering_cart_abandonment_DetectAbandonedCartsHandler[DetectAbandonedCartsHandler]
        hdlr_ordering_cart_conversion_ConvertCartHandler[ConvertCartHandler]
        hdlr_ordering_cart_coupons_ApplyCouponHandler[ApplyCouponHandler]
        hdlr_ordering_cart_items_ManageCartItemsHandler[ManageCartItemsHandler]
        hdlr_ordering_cart_management_ManageCartHandler[ManageCartHandler]
    end
    subgraph ordering_order_order_Order[Order]
        agg_ordering_order_order_Order[Order]
        cmd_ordering_order_cancellation_CancelOrder[/CancelOrder/]
        cmd_ordering_order_cancellation_RefundOrder[/RefundOrder/]
        cmd_ordering_order_completion_CompleteOrder[/CompleteOrder/]
        cmd_ordering_order_confirmation_ConfirmOrder[/ConfirmOrder/]
        cmd_ordering_order_creation_CreateOrder[/CreateOrder/]
        cmd_ordering_order_fulfillment_MarkProcessing[/MarkProcessing/]
        cmd_ordering_order_fulfillment_RecordDelivery[/RecordDelivery/]
        cmd_ordering_order_fulfillment_RecordPartialShipment[/RecordPartialShipment/]
        cmd_ordering_order_fulfillment_RecordShipment[/RecordShipment/]
        cmd_ordering_order_modification_AddItem[/AddItem/]
        cmd_ordering_order_modification_ApplyCoupon[/ApplyCoupon/]
        cmd_ordering_order_modification_RemoveItem[/RemoveItem/]
        cmd_ordering_order_modification_UpdateItemQuantity[/UpdateItemQuantity/]
        cmd_ordering_order_payment_RecordPaymentFailure[/RecordPaymentFailure/]
        cmd_ordering_order_payment_RecordPaymentPending[/RecordPaymentPending/]
        cmd_ordering_order_payment_RecordPaymentSuccess[/RecordPaymentSuccess/]
        cmd_ordering_order_returns_ApproveReturn[/ApproveReturn/]
        cmd_ordering_order_returns_RecordReturn[/RecordReturn/]
        cmd_ordering_order_returns_RequestReturn[/RequestReturn/]
        evt_ordering_order_events_CouponApplied([CouponApplied])
        evt_ordering_order_events_ItemAdded([ItemAdded])
        evt_ordering_order_events_ItemQuantityUpdated([ItemQuantityUpdated])
        evt_ordering_order_events_ItemRemoved([ItemRemoved])
        evt_ordering_order_events_OrderCancelled([OrderCancelled])
        evt_ordering_order_events_OrderCompleted([OrderCompleted])
        evt_ordering_order_events_OrderConfirmed([OrderConfirmed])
        evt_ordering_order_events_OrderCreated([OrderCreated])
        evt_ordering_order_events_OrderDelivered([OrderDelivered])
        evt_ordering_order_events_OrderPartiallyShipped([OrderPartiallyShipped])
        evt_ordering_order_events_OrderProcessing([OrderProcessing])
        evt_ordering_order_events_OrderRefunded([OrderRefunded])
        evt_ordering_order_events_OrderReturned([OrderReturned])
        evt_ordering_order_events_OrderShipped([OrderShipped])
        evt_ordering_order_events_PaymentFailed([PaymentFailed])
        evt_ordering_order_events_PaymentPending([PaymentPending])
        evt_ordering_order_events_PaymentSucceeded([PaymentSucceeded])
        evt_ordering_order_events_ReturnApproved([ReturnApproved])
        evt_ordering_order_events_ReturnRequested([ReturnRequested])
        hdlr_ordering_order_cancellation_CancelOrderHandler[CancelOrderHandler]
        hdlr_ordering_order_completion_CompleteOrderHandler[CompleteOrderHandler]
        hdlr_ordering_order_confirmation_ConfirmOrderHandler[ConfirmOrderHandler]
        hdlr_ordering_order_creation_CreateOrderHandler[CreateOrderHandler]
        hdlr_ordering_order_fulfillment_RecordFulfillmentHandler[RecordFulfillmentHandler]
        hdlr_ordering_order_modification_ModifyOrderHandler[ModifyOrderHandler]
        hdlr_ordering_order_payment_RecordPaymentHandler[RecordPaymentHandler]
        hdlr_ordering_order_returns_ManageReturnsHandler[ManageReturnsHandler]
    end
    cmd_ordering_cart_abandonment_DetectAbandonedCarts --> hdlr_ordering_cart_abandonment_DetectAbandonedCartsHandler
    hdlr_ordering_cart_abandonment_DetectAbandonedCartsHandler --> agg_ordering_cart_cart_ShoppingCart
    cmd_ordering_cart_conversion_ConvertToOrder --> hdlr_ordering_cart_conversion_ConvertCartHandler
    hdlr_ordering_cart_conversion_ConvertCartHandler --> agg_ordering_cart_cart_ShoppingCart
    cmd_ordering_cart_coupons_ApplyCouponToCart --> hdlr_ordering_cart_coupons_ApplyCouponHandler
    hdlr_ordering_cart_coupons_ApplyCouponHandler --> agg_ordering_cart_cart_ShoppingCart
    cmd_ordering_cart_items_AddToCart --> hdlr_ordering_cart_items_ManageCartItemsHandler
    cmd_ordering_cart_items_RemoveFromCart --> hdlr_ordering_cart_items_ManageCartItemsHandler
    cmd_ordering_cart_items_UpdateCartQuantity --> hdlr_ordering_cart_items_ManageCartItemsHandler
    hdlr_ordering_cart_items_ManageCartItemsHandler --> agg_ordering_cart_cart_ShoppingCart
    cmd_ordering_cart_management_AbandonCart --> hdlr_ordering_cart_management_ManageCartHandler
    cmd_ordering_cart_management_CreateCart --> hdlr_ordering_cart_management_ManageCartHandler
    cmd_ordering_cart_management_MergeGuestCart --> hdlr_ordering_cart_management_ManageCartHandler
    hdlr_ordering_cart_management_ManageCartHandler --> agg_ordering_cart_cart_ShoppingCart
    agg_ordering_cart_cart_ShoppingCart --> evt_ordering_cart_events_CartAbandoned
    agg_ordering_cart_cart_ShoppingCart --> evt_ordering_cart_events_CartConverted
    agg_ordering_cart_cart_ShoppingCart --> evt_ordering_cart_events_CartCouponApplied
    agg_ordering_cart_cart_ShoppingCart --> evt_ordering_cart_events_CartItemAdded
    agg_ordering_cart_cart_ShoppingCart --> evt_ordering_cart_events_CartItemRemoved
    agg_ordering_cart_cart_ShoppingCart --> evt_ordering_cart_events_CartQuantityUpdated
    agg_ordering_cart_cart_ShoppingCart --> evt_ordering_cart_events_CartsMerged
    cmd_ordering_order_cancellation_CancelOrder --> hdlr_ordering_order_cancellation_CancelOrderHandler
    cmd_ordering_order_cancellation_RefundOrder --> hdlr_ordering_order_cancellation_CancelOrderHandler
    hdlr_ordering_order_cancellation_CancelOrderHandler --> agg_ordering_order_order_Order
    cmd_ordering_order_completion_CompleteOrder --> hdlr_ordering_order_completion_CompleteOrderHandler
    hdlr_ordering_order_completion_CompleteOrderHandler --> agg_ordering_order_order_Order
    cmd_ordering_order_confirmation_ConfirmOrder --> hdlr_ordering_order_confirmation_ConfirmOrderHandler
    hdlr_ordering_order_confirmation_ConfirmOrderHandler --> agg_ordering_order_order_Order
    cmd_ordering_order_creation_CreateOrder --> hdlr_ordering_order_creation_CreateOrderHandler
    hdlr_ordering_order_creation_CreateOrderHandler --> agg_ordering_order_order_Order
    cmd_ordering_order_fulfillment_MarkProcessing --> hdlr_ordering_order_fulfillment_RecordFulfillmentHandler
    cmd_ordering_order_fulfillment_RecordDelivery --> hdlr_ordering_order_fulfillment_RecordFulfillmentHandler
    cmd_ordering_order_fulfillment_RecordPartialShipment --> hdlr_ordering_order_fulfillment_RecordFulfillmentHandler
    cmd_ordering_order_fulfillment_RecordShipment --> hdlr_ordering_order_fulfillment_RecordFulfillmentHandler
    hdlr_ordering_order_fulfillment_RecordFulfillmentHandler --> agg_ordering_order_order_Order
    cmd_ordering_order_modification_AddItem --> hdlr_ordering_order_modification_ModifyOrderHandler
    cmd_ordering_order_modification_ApplyCoupon --> hdlr_ordering_order_modification_ModifyOrderHandler
    cmd_ordering_order_modification_RemoveItem --> hdlr_ordering_order_modification_ModifyOrderHandler
    cmd_ordering_order_modification_UpdateItemQuantity --> hdlr_ordering_order_modification_ModifyOrderHandler
    hdlr_ordering_order_modification_ModifyOrderHandler --> agg_ordering_order_order_Order
    cmd_ordering_order_payment_RecordPaymentFailure --> hdlr_ordering_order_payment_RecordPaymentHandler
    cmd_ordering_order_payment_RecordPaymentPending --> hdlr_ordering_order_payment_RecordPaymentHandler
    cmd_ordering_order_payment_RecordPaymentSuccess --> hdlr_ordering_order_payment_RecordPaymentHandler
    hdlr_ordering_order_payment_RecordPaymentHandler --> agg_ordering_order_order_Order
    cmd_ordering_order_returns_ApproveReturn --> hdlr_ordering_order_returns_ManageReturnsHandler
    cmd_ordering_order_returns_RecordReturn --> hdlr_ordering_order_returns_ManageReturnsHandler
    cmd_ordering_order_returns_RequestReturn --> hdlr_ordering_order_returns_ManageReturnsHandler
    hdlr_ordering_order_returns_ManageReturnsHandler --> agg_ordering_order_order_Order
    agg_ordering_order_order_Order --> evt_ordering_order_events_CouponApplied
    agg_ordering_order_order_Order --> evt_ordering_order_events_ItemAdded
    agg_ordering_order_order_Order --> evt_ordering_order_events_ItemQuantityUpdated
    agg_ordering_order_order_Order --> evt_ordering_order_events_ItemRemoved
    agg_ordering_order_order_Order --> evt_ordering_order_events_OrderCancelled
    agg_ordering_order_order_Order --> evt_ordering_order_events_OrderCompleted
    agg_ordering_order_order_Order --> evt_ordering_order_events_OrderConfirmed
    agg_ordering_order_order_Order --> evt_ordering_order_events_OrderCreated
    agg_ordering_order_order_Order --> evt_ordering_order_events_OrderDelivered
    agg_ordering_order_order_Order --> evt_ordering_order_events_OrderPartiallyShipped
    agg_ordering_order_order_Order --> evt_ordering_order_events_OrderProcessing
    agg_ordering_order_order_Order --> evt_ordering_order_events_OrderRefunded
    agg_ordering_order_order_Order --> evt_ordering_order_events_OrderReturned
    agg_ordering_order_order_Order --> evt_ordering_order_events_OrderShipped
    agg_ordering_order_order_Order --> evt_ordering_order_events_PaymentFailed
    agg_ordering_order_order_Order --> evt_ordering_order_events_PaymentPending
    agg_ordering_order_order_Order --> evt_ordering_order_events_PaymentSucceeded
    agg_ordering_order_order_Order --> evt_ordering_order_events_ReturnApproved
    agg_ordering_order_order_Order --> evt_ordering_order_events_ReturnRequested
    pm_ordering_checkout_saga_OrderCheckoutSaga["OrderCheckoutSaga (start, end)"]
    evt_ordering_order_events_OrderCancelled -->|end| pm_ordering_checkout_saga_OrderCheckoutSaga
    evt_ordering_order_events_OrderConfirmed -->|start| pm_ordering_checkout_saga_OrderCheckoutSaga
    evt_ordering_order_events_PaymentFailed --> pm_ordering_checkout_saga_OrderCheckoutSaga
    evt_ordering_order_events_PaymentPending --> pm_ordering_checkout_saga_OrderCheckoutSaga
    evt_ordering_order_events_PaymentSucceeded --> pm_ordering_checkout_saga_OrderCheckoutSaga
    proj_ordering_projections_abandoned_checkouts_AbandonedCheckoutProjector[AbandonedCheckoutProjector → AbandonedCheckout]
    evt_ordering_order_events_OrderCancelled --> proj_ordering_projections_abandoned_checkouts_AbandonedCheckoutProjector
    evt_ordering_order_events_OrderConfirmed --> proj_ordering_projections_abandoned_checkouts_AbandonedCheckoutProjector
    evt_ordering_order_events_OrderCreated --> proj_ordering_projections_abandoned_checkouts_AbandonedCheckoutProjector
    proj_ordering_projections_cart_view_CartViewProjector[CartViewProjector → CartView]
    evt_ordering_cart_events_CartAbandoned --> proj_ordering_projections_cart_view_CartViewProjector
    evt_ordering_cart_events_CartConverted --> proj_ordering_projections_cart_view_CartViewProjector
    evt_ordering_cart_events_CartCouponApplied --> proj_ordering_projections_cart_view_CartViewProjector
    evt_ordering_cart_events_CartItemAdded --> proj_ordering_projections_cart_view_CartViewProjector
    evt_ordering_cart_events_CartItemRemoved --> proj_ordering_projections_cart_view_CartViewProjector
    evt_ordering_cart_events_CartQuantityUpdated --> proj_ordering_projections_cart_view_CartViewProjector
    evt_ordering_cart_events_CartsMerged --> proj_ordering_projections_cart_view_CartViewProjector
    proj_ordering_projections_customer_orders_CustomerOrdersProjector[CustomerOrdersProjector → CustomerOrders]
    evt_ordering_order_events_OrderCancelled --> proj_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_OrderCompleted --> proj_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_OrderConfirmed --> proj_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_OrderCreated --> proj_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_OrderDelivered --> proj_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_OrderPartiallyShipped --> proj_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_OrderProcessing --> proj_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_OrderRefunded --> proj_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_OrderReturned --> proj_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_OrderShipped --> proj_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_PaymentFailed --> proj_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_PaymentPending --> proj_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_PaymentSucceeded --> proj_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_ReturnApproved --> proj_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_ReturnRequested --> proj_ordering_projections_customer_orders_CustomerOrdersProjector
    proj_ordering_projections_daily_order_stats_DailyOrderStatsProjector[DailyOrderStatsProjector → DailyOrderStats]
    evt_ordering_order_events_OrderCancelled --> proj_ordering_projections_daily_order_stats_DailyOrderStatsProjector
    evt_ordering_order_events_OrderCompleted --> proj_ordering_projections_daily_order_stats_DailyOrderStatsProjector
    evt_ordering_order_events_OrderCreated --> proj_ordering_projections_daily_order_stats_DailyOrderStatsProjector
    evt_ordering_order_events_OrderRefunded --> proj_ordering_projections_daily_order_stats_DailyOrderStatsProjector
    proj_ordering_projections_order_detail_OrderDetailProjector[OrderDetailProjector → OrderDetail]
    evt_ordering_order_events_CouponApplied --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_ItemAdded --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_ItemQuantityUpdated --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_ItemRemoved --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_OrderCancelled --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_OrderCompleted --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_OrderConfirmed --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_OrderCreated --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_OrderDelivered --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_OrderPartiallyShipped --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_OrderProcessing --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_OrderRefunded --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_OrderReturned --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_OrderShipped --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_PaymentFailed --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_PaymentPending --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_PaymentSucceeded --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_ReturnApproved --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_ReturnRequested --> proj_ordering_projections_order_detail_OrderDetailProjector
    proj_ordering_projections_order_summary_OrderSummaryProjector[OrderSummaryProjector → OrderSummary]
    evt_ordering_order_events_ItemAdded --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_ItemQuantityUpdated --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_ItemRemoved --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_OrderCancelled --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_OrderCompleted --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_OrderConfirmed --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_OrderCreated --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_OrderDelivered --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_OrderPartiallyShipped --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_OrderProcessing --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_OrderRefunded --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_OrderReturned --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_OrderShipped --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_PaymentFailed --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_PaymentPending --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_PaymentSucceeded --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_ReturnApproved --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_ReturnRequested --> proj_ordering_projections_order_summary_OrderSummaryProjector
    proj_ordering_projections_order_timeline_OrderTimelineProjector[OrderTimelineProjector → OrderTimeline]
    evt_ordering_order_events_CouponApplied --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_ItemAdded --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_ItemQuantityUpdated --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_ItemRemoved --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_OrderCancelled --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_OrderCompleted --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_OrderConfirmed --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_OrderCreated --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_OrderDelivered --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_OrderPartiallyShipped --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_OrderProcessing --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_OrderRefunded --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_OrderReturned --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_OrderShipped --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_PaymentFailed --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_PaymentPending --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_PaymentSucceeded --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_ReturnApproved --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_ReturnRequested --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    proj_ordering_projections_orders_by_status_OrdersByStatusProjector[OrdersByStatusProjector → OrdersByStatus]
    evt_ordering_order_events_OrderCancelled --> proj_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_OrderCompleted --> proj_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_OrderConfirmed --> proj_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_OrderCreated --> proj_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_OrderDelivered --> proj_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_OrderPartiallyShipped --> proj_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_OrderProcessing --> proj_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_OrderRefunded --> proj_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_OrderReturned --> proj_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_OrderShipped --> proj_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_PaymentFailed --> proj_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_PaymentPending --> proj_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_PaymentSucceeded --> proj_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_ReturnApproved --> proj_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_ReturnRequested --> proj_ordering_projections_orders_by_status_OrdersByStatusProjector
```
