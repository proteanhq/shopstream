## Event Model: ShoppingCart

> **Given** ShoppingCart
> **When** DetectAbandonedCarts, ConvertToOrder, ApplyCouponToCart, AddToCart, RemoveFromCart, UpdateCartQuantity, AbandonCart, CreateCart, MergeGuestCart
> **Then** CartAbandoned, CartConverted, CartCouponApplied, CartItemAdded, CartItemRemoved, CartQuantityUpdated, CartsMerged

```mermaid
flowchart LR
    subgraph ordering_cart_cart_ShoppingCart[ShoppingCart]
        cmd_ordering_cart_abandonment_DetectAbandonedCarts[/DetectAbandonedCarts/]
        cmd_ordering_cart_conversion_ConvertToOrder[/ConvertToOrder/]
        cmd_ordering_cart_coupons_ApplyCouponToCart[/ApplyCouponToCart/]
        cmd_ordering_cart_items_AddToCart[/AddToCart/]
        cmd_ordering_cart_items_RemoveFromCart[/RemoveFromCart/]
        cmd_ordering_cart_items_UpdateCartQuantity[/UpdateCartQuantity/]
        cmd_ordering_cart_management_AbandonCart[/AbandonCart/]
        cmd_ordering_cart_management_CreateCart[/CreateCart/]
        cmd_ordering_cart_management_MergeGuestCart[/MergeGuestCart/]
        agg_ordering_cart_cart_ShoppingCart[ShoppingCart]
        evt_ordering_cart_events_CartAbandoned([CartAbandoned])
        evt_ordering_cart_events_CartConverted([CartConverted])
        evt_ordering_cart_events_CartCouponApplied([CartCouponApplied])
        evt_ordering_cart_events_CartItemAdded([CartItemAdded])
        evt_ordering_cart_events_CartItemRemoved([CartItemRemoved])
        evt_ordering_cart_events_CartQuantityUpdated([CartQuantityUpdated])
        evt_ordering_cart_events_CartsMerged([CartsMerged])
        rm_ordering_cart_cart_ShoppingCart_ordering_projections_cart_view_CartViewProjector[(CartViewProjector → CartView)]
    end
    cmd_ordering_cart_abandonment_DetectAbandonedCarts --> agg_ordering_cart_cart_ShoppingCart
    cmd_ordering_cart_conversion_ConvertToOrder --> agg_ordering_cart_cart_ShoppingCart
    cmd_ordering_cart_coupons_ApplyCouponToCart --> agg_ordering_cart_cart_ShoppingCart
    cmd_ordering_cart_items_AddToCart --> agg_ordering_cart_cart_ShoppingCart
    cmd_ordering_cart_items_RemoveFromCart --> agg_ordering_cart_cart_ShoppingCart
    cmd_ordering_cart_items_UpdateCartQuantity --> agg_ordering_cart_cart_ShoppingCart
    cmd_ordering_cart_management_AbandonCart --> agg_ordering_cart_cart_ShoppingCart
    cmd_ordering_cart_management_CreateCart --> agg_ordering_cart_cart_ShoppingCart
    cmd_ordering_cart_management_MergeGuestCart --> agg_ordering_cart_cart_ShoppingCart
    agg_ordering_cart_cart_ShoppingCart --> evt_ordering_cart_events_CartAbandoned
    evt_ordering_cart_events_CartAbandoned --> rm_ordering_cart_cart_ShoppingCart_ordering_projections_cart_view_CartViewProjector
    agg_ordering_cart_cart_ShoppingCart --> evt_ordering_cart_events_CartConverted
    evt_ordering_cart_events_CartConverted --> rm_ordering_cart_cart_ShoppingCart_ordering_projections_cart_view_CartViewProjector
    agg_ordering_cart_cart_ShoppingCart --> evt_ordering_cart_events_CartCouponApplied
    evt_ordering_cart_events_CartCouponApplied --> rm_ordering_cart_cart_ShoppingCart_ordering_projections_cart_view_CartViewProjector
    agg_ordering_cart_cart_ShoppingCart --> evt_ordering_cart_events_CartItemAdded
    evt_ordering_cart_events_CartItemAdded --> rm_ordering_cart_cart_ShoppingCart_ordering_projections_cart_view_CartViewProjector
    agg_ordering_cart_cart_ShoppingCart --> evt_ordering_cart_events_CartItemRemoved
    evt_ordering_cart_events_CartItemRemoved --> rm_ordering_cart_cart_ShoppingCart_ordering_projections_cart_view_CartViewProjector
    agg_ordering_cart_cart_ShoppingCart --> evt_ordering_cart_events_CartQuantityUpdated
    evt_ordering_cart_events_CartQuantityUpdated --> rm_ordering_cart_cart_ShoppingCart_ordering_projections_cart_view_CartViewProjector
    agg_ordering_cart_cart_ShoppingCart --> evt_ordering_cart_events_CartsMerged
    evt_ordering_cart_events_CartsMerged --> rm_ordering_cart_cart_ShoppingCart_ordering_projections_cart_view_CartViewProjector
```

## Event Model: Order

> **Given** Order
> **When** CancelOrder, RefundOrder, CompleteOrder, ConfirmOrder, CreateOrder, MarkProcessing, RecordDelivery, RecordPartialShipment, RecordShipment, AddItem, ApplyCoupon, RemoveItem, UpdateItemQuantity, RecordPaymentFailure, RecordPaymentPending, RecordPaymentSuccess, ApproveReturn, RecordReturn, RequestReturn
> **Then** CouponApplied, ItemAdded, ItemQuantityUpdated, ItemRemoved, OrderCancelled, OrderCompleted, OrderConfirmed, OrderCreated, OrderDelivered, OrderPartiallyShipped, OrderProcessing, OrderRefunded, OrderReturned, OrderShipped, PaymentFailed, PaymentPending, PaymentSucceeded, ReturnApproved, ReturnRequested

```mermaid
flowchart LR
    subgraph ordering_order_order_Order[Order]
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
        agg_ordering_order_order_Order[Order]
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
        auto_ordering_order_order_Order_ordering_checkout_saga_OrderCheckoutSaga{{"OrderCheckoutSaga (start, end)"}}
        rm_ordering_order_order_Order_ordering_projections_abandoned_checkouts_AbandonedCheckoutProjector[(AbandonedCheckoutProjector → AbandonedCheckout)]
        rm_ordering_order_order_Order_ordering_projections_customer_orders_CustomerOrdersProjector[(CustomerOrdersProjector → CustomerOrders)]
        rm_ordering_order_order_Order_ordering_projections_daily_order_stats_DailyOrderStatsProjector[(DailyOrderStatsProjector → DailyOrderStats)]
        rm_ordering_order_order_Order_ordering_projections_order_detail_OrderDetailProjector[(OrderDetailProjector → OrderDetail)]
        rm_ordering_order_order_Order_ordering_projections_order_summary_OrderSummaryProjector[(OrderSummaryProjector → OrderSummary)]
        rm_ordering_order_order_Order_ordering_projections_order_timeline_OrderTimelineProjector[(OrderTimelineProjector → OrderTimeline)]
        rm_ordering_order_order_Order_ordering_projections_orders_by_status_OrdersByStatusProjector[(OrdersByStatusProjector → OrdersByStatus)]
    end
    cmd_ordering_order_cancellation_CancelOrder --> agg_ordering_order_order_Order
    cmd_ordering_order_cancellation_RefundOrder --> agg_ordering_order_order_Order
    cmd_ordering_order_completion_CompleteOrder --> agg_ordering_order_order_Order
    cmd_ordering_order_confirmation_ConfirmOrder --> agg_ordering_order_order_Order
    cmd_ordering_order_creation_CreateOrder --> agg_ordering_order_order_Order
    cmd_ordering_order_fulfillment_MarkProcessing --> agg_ordering_order_order_Order
    cmd_ordering_order_fulfillment_RecordDelivery --> agg_ordering_order_order_Order
    cmd_ordering_order_fulfillment_RecordPartialShipment --> agg_ordering_order_order_Order
    cmd_ordering_order_fulfillment_RecordShipment --> agg_ordering_order_order_Order
    cmd_ordering_order_modification_AddItem --> agg_ordering_order_order_Order
    cmd_ordering_order_modification_ApplyCoupon --> agg_ordering_order_order_Order
    cmd_ordering_order_modification_RemoveItem --> agg_ordering_order_order_Order
    cmd_ordering_order_modification_UpdateItemQuantity --> agg_ordering_order_order_Order
    cmd_ordering_order_payment_RecordPaymentFailure --> agg_ordering_order_order_Order
    cmd_ordering_order_payment_RecordPaymentPending --> agg_ordering_order_order_Order
    cmd_ordering_order_payment_RecordPaymentSuccess --> agg_ordering_order_order_Order
    cmd_ordering_order_returns_ApproveReturn --> agg_ordering_order_order_Order
    cmd_ordering_order_returns_RecordReturn --> agg_ordering_order_order_Order
    cmd_ordering_order_returns_RequestReturn --> agg_ordering_order_order_Order
    agg_ordering_order_order_Order --> evt_ordering_order_events_CouponApplied
    evt_ordering_order_events_CouponApplied --> rm_ordering_order_order_Order_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_CouponApplied --> rm_ordering_order_order_Order_ordering_projections_order_timeline_OrderTimelineProjector
    agg_ordering_order_order_Order --> evt_ordering_order_events_ItemAdded
    evt_ordering_order_events_ItemAdded --> rm_ordering_order_order_Order_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_ItemAdded --> rm_ordering_order_order_Order_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_ItemAdded --> rm_ordering_order_order_Order_ordering_projections_order_timeline_OrderTimelineProjector
    agg_ordering_order_order_Order --> evt_ordering_order_events_ItemQuantityUpdated
    evt_ordering_order_events_ItemQuantityUpdated --> rm_ordering_order_order_Order_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_ItemQuantityUpdated --> rm_ordering_order_order_Order_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_ItemQuantityUpdated --> rm_ordering_order_order_Order_ordering_projections_order_timeline_OrderTimelineProjector
    agg_ordering_order_order_Order --> evt_ordering_order_events_ItemRemoved
    evt_ordering_order_events_ItemRemoved --> rm_ordering_order_order_Order_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_ItemRemoved --> rm_ordering_order_order_Order_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_ItemRemoved --> rm_ordering_order_order_Order_ordering_projections_order_timeline_OrderTimelineProjector
    agg_ordering_order_order_Order --> evt_ordering_order_events_OrderCancelled
    evt_ordering_order_events_OrderCancelled --> rm_ordering_order_order_Order_ordering_projections_abandoned_checkouts_AbandonedCheckoutProjector
    evt_ordering_order_events_OrderCancelled --> rm_ordering_order_order_Order_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_OrderCancelled --> rm_ordering_order_order_Order_ordering_projections_daily_order_stats_DailyOrderStatsProjector
    evt_ordering_order_events_OrderCancelled --> rm_ordering_order_order_Order_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_OrderCancelled --> rm_ordering_order_order_Order_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_OrderCancelled --> rm_ordering_order_order_Order_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_OrderCancelled --> rm_ordering_order_order_Order_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_OrderCancelled -->|end| auto_ordering_order_order_Order_ordering_checkout_saga_OrderCheckoutSaga
    agg_ordering_order_order_Order --> evt_ordering_order_events_OrderCompleted
    evt_ordering_order_events_OrderCompleted --> rm_ordering_order_order_Order_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_OrderCompleted --> rm_ordering_order_order_Order_ordering_projections_daily_order_stats_DailyOrderStatsProjector
    evt_ordering_order_events_OrderCompleted --> rm_ordering_order_order_Order_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_OrderCompleted --> rm_ordering_order_order_Order_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_OrderCompleted --> rm_ordering_order_order_Order_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_OrderCompleted --> rm_ordering_order_order_Order_ordering_projections_orders_by_status_OrdersByStatusProjector
    agg_ordering_order_order_Order --> evt_ordering_order_events_OrderConfirmed
    evt_ordering_order_events_OrderConfirmed --> rm_ordering_order_order_Order_ordering_projections_abandoned_checkouts_AbandonedCheckoutProjector
    evt_ordering_order_events_OrderConfirmed --> rm_ordering_order_order_Order_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_OrderConfirmed --> rm_ordering_order_order_Order_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_OrderConfirmed --> rm_ordering_order_order_Order_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_OrderConfirmed --> rm_ordering_order_order_Order_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_OrderConfirmed --> rm_ordering_order_order_Order_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_OrderConfirmed -->|start| auto_ordering_order_order_Order_ordering_checkout_saga_OrderCheckoutSaga
    agg_ordering_order_order_Order --> evt_ordering_order_events_OrderCreated
    evt_ordering_order_events_OrderCreated --> rm_ordering_order_order_Order_ordering_projections_abandoned_checkouts_AbandonedCheckoutProjector
    evt_ordering_order_events_OrderCreated --> rm_ordering_order_order_Order_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_OrderCreated --> rm_ordering_order_order_Order_ordering_projections_daily_order_stats_DailyOrderStatsProjector
    evt_ordering_order_events_OrderCreated --> rm_ordering_order_order_Order_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_OrderCreated --> rm_ordering_order_order_Order_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_OrderCreated --> rm_ordering_order_order_Order_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_OrderCreated --> rm_ordering_order_order_Order_ordering_projections_orders_by_status_OrdersByStatusProjector
    agg_ordering_order_order_Order --> evt_ordering_order_events_OrderDelivered
    evt_ordering_order_events_OrderDelivered --> rm_ordering_order_order_Order_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_OrderDelivered --> rm_ordering_order_order_Order_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_OrderDelivered --> rm_ordering_order_order_Order_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_OrderDelivered --> rm_ordering_order_order_Order_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_OrderDelivered --> rm_ordering_order_order_Order_ordering_projections_orders_by_status_OrdersByStatusProjector
    agg_ordering_order_order_Order --> evt_ordering_order_events_OrderPartiallyShipped
    evt_ordering_order_events_OrderPartiallyShipped --> rm_ordering_order_order_Order_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_OrderPartiallyShipped --> rm_ordering_order_order_Order_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_OrderPartiallyShipped --> rm_ordering_order_order_Order_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_OrderPartiallyShipped --> rm_ordering_order_order_Order_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_OrderPartiallyShipped --> rm_ordering_order_order_Order_ordering_projections_orders_by_status_OrdersByStatusProjector
    agg_ordering_order_order_Order --> evt_ordering_order_events_OrderProcessing
    evt_ordering_order_events_OrderProcessing --> rm_ordering_order_order_Order_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_OrderProcessing --> rm_ordering_order_order_Order_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_OrderProcessing --> rm_ordering_order_order_Order_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_OrderProcessing --> rm_ordering_order_order_Order_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_OrderProcessing --> rm_ordering_order_order_Order_ordering_projections_orders_by_status_OrdersByStatusProjector
    agg_ordering_order_order_Order --> evt_ordering_order_events_OrderRefunded
    evt_ordering_order_events_OrderRefunded --> rm_ordering_order_order_Order_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_OrderRefunded --> rm_ordering_order_order_Order_ordering_projections_daily_order_stats_DailyOrderStatsProjector
    evt_ordering_order_events_OrderRefunded --> rm_ordering_order_order_Order_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_OrderRefunded --> rm_ordering_order_order_Order_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_OrderRefunded --> rm_ordering_order_order_Order_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_OrderRefunded --> rm_ordering_order_order_Order_ordering_projections_orders_by_status_OrdersByStatusProjector
    agg_ordering_order_order_Order --> evt_ordering_order_events_OrderReturned
    evt_ordering_order_events_OrderReturned --> rm_ordering_order_order_Order_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_OrderReturned --> rm_ordering_order_order_Order_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_OrderReturned --> rm_ordering_order_order_Order_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_OrderReturned --> rm_ordering_order_order_Order_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_OrderReturned --> rm_ordering_order_order_Order_ordering_projections_orders_by_status_OrdersByStatusProjector
    agg_ordering_order_order_Order --> evt_ordering_order_events_OrderShipped
    evt_ordering_order_events_OrderShipped --> rm_ordering_order_order_Order_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_OrderShipped --> rm_ordering_order_order_Order_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_OrderShipped --> rm_ordering_order_order_Order_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_OrderShipped --> rm_ordering_order_order_Order_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_OrderShipped --> rm_ordering_order_order_Order_ordering_projections_orders_by_status_OrdersByStatusProjector
    agg_ordering_order_order_Order --> evt_ordering_order_events_PaymentFailed
    evt_ordering_order_events_PaymentFailed --> rm_ordering_order_order_Order_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_PaymentFailed --> rm_ordering_order_order_Order_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_PaymentFailed --> rm_ordering_order_order_Order_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_PaymentFailed --> rm_ordering_order_order_Order_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_PaymentFailed --> rm_ordering_order_order_Order_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_PaymentFailed --> auto_ordering_order_order_Order_ordering_checkout_saga_OrderCheckoutSaga
    agg_ordering_order_order_Order --> evt_ordering_order_events_PaymentPending
    evt_ordering_order_events_PaymentPending --> rm_ordering_order_order_Order_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_PaymentPending --> rm_ordering_order_order_Order_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_PaymentPending --> rm_ordering_order_order_Order_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_PaymentPending --> rm_ordering_order_order_Order_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_PaymentPending --> rm_ordering_order_order_Order_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_PaymentPending --> auto_ordering_order_order_Order_ordering_checkout_saga_OrderCheckoutSaga
    agg_ordering_order_order_Order --> evt_ordering_order_events_PaymentSucceeded
    evt_ordering_order_events_PaymentSucceeded --> rm_ordering_order_order_Order_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_PaymentSucceeded --> rm_ordering_order_order_Order_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_PaymentSucceeded --> rm_ordering_order_order_Order_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_PaymentSucceeded --> rm_ordering_order_order_Order_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_PaymentSucceeded --> rm_ordering_order_order_Order_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_PaymentSucceeded --> auto_ordering_order_order_Order_ordering_checkout_saga_OrderCheckoutSaga
    agg_ordering_order_order_Order --> evt_ordering_order_events_ReturnApproved
    evt_ordering_order_events_ReturnApproved --> rm_ordering_order_order_Order_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_ReturnApproved --> rm_ordering_order_order_Order_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_ReturnApproved --> rm_ordering_order_order_Order_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_ReturnApproved --> rm_ordering_order_order_Order_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_ReturnApproved --> rm_ordering_order_order_Order_ordering_projections_orders_by_status_OrdersByStatusProjector
    agg_ordering_order_order_Order --> evt_ordering_order_events_ReturnRequested
    evt_ordering_order_events_ReturnRequested --> rm_ordering_order_order_Order_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_ReturnRequested --> rm_ordering_order_order_Order_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_ReturnRequested --> rm_ordering_order_order_Order_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_ReturnRequested --> rm_ordering_order_order_Order_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_ReturnRequested --> rm_ordering_order_order_Order_ordering_projections_orders_by_status_OrdersByStatusProjector
```