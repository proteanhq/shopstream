## Handler Wiring

```mermaid
flowchart TD
    subgraph command_handlers["Command Handlers"]
        ch_ordering_cart_abandonment_DetectAbandonedCartsHandler[DetectAbandonedCartsHandler]
        ch_ordering_cart_conversion_ConvertCartHandler[ConvertCartHandler]
        ch_ordering_cart_coupons_ApplyCouponHandler[ApplyCouponHandler]
        ch_ordering_cart_items_ManageCartItemsHandler[ManageCartItemsHandler]
        ch_ordering_cart_management_ManageCartHandler[ManageCartHandler]
        ch_ordering_order_cancellation_CancelOrderHandler[CancelOrderHandler]
        ch_ordering_order_completion_CompleteOrderHandler[CompleteOrderHandler]
        ch_ordering_order_confirmation_ConfirmOrderHandler[ConfirmOrderHandler]
        ch_ordering_order_creation_CreateOrderHandler[CreateOrderHandler]
        ch_ordering_order_fulfillment_RecordFulfillmentHandler[RecordFulfillmentHandler]
        ch_ordering_order_modification_ModifyOrderHandler[ModifyOrderHandler]
        ch_ordering_order_payment_RecordPaymentHandler[RecordPaymentHandler]
        ch_ordering_order_returns_ManageReturnsHandler[ManageReturnsHandler]
    end
    subgraph process_managers["Process Managers"]
        pm_ordering_checkout_saga_OrderCheckoutSaga["OrderCheckoutSaga (start, end)"]
    end
    subgraph projectors["Projectors"]
        proj_ordering_projections_abandoned_checkouts_AbandonedCheckoutProjector[AbandonedCheckoutProjector → AbandonedCheckout]
        proj_ordering_projections_cart_view_CartViewProjector[CartViewProjector → CartView]
        proj_ordering_projections_customer_orders_CustomerOrdersProjector[CustomerOrdersProjector → CustomerOrders]
        proj_ordering_projections_daily_order_stats_DailyOrderStatsProjector[DailyOrderStatsProjector → DailyOrderStats]
        proj_ordering_projections_order_detail_OrderDetailProjector[OrderDetailProjector → OrderDetail]
        proj_ordering_projections_order_summary_OrderSummaryProjector[OrderSummaryProjector → OrderSummary]
        proj_ordering_projections_order_timeline_OrderTimelineProjector[OrderTimelineProjector → OrderTimeline]
        proj_ordering_projections_orders_by_status_OrdersByStatusProjector[OrdersByStatusProjector → OrdersByStatus]
    end
    subgraph subscribers["Subscribers"]
        sub_ordering_cart_catalogue_subscriber_CatalogueEventsSubscriber[CatalogueEventsSubscriber\nstream: catalogue::product]
        sub_ordering_checkout_inventory_subscriber_InventoryEventsSubscriber[InventoryEventsSubscriber\nstream: inventory::inventory_item]
        sub_ordering_checkout_payment_subscriber_PaymentEventsSubscriber[PaymentEventsSubscriber\nstream: payments::payment]
        sub_ordering_order_fulfillment_subscriber_FulfillmentEventsSubscriber[FulfillmentEventsSubscriber\nstream: fulfillment::fulfillment]
        sub_ordering_order_identity_subscriber_IdentityEventsSubscriber[IdentityEventsSubscriber\nstream: identity::customer]
    end
    cmd_ordering_cart_abandonment_DetectAbandonedCarts[/DetectAbandonedCarts/] --> ch_ordering_cart_abandonment_DetectAbandonedCartsHandler
    ch_ordering_cart_abandonment_DetectAbandonedCartsHandler --> agg_ordering_cart_cart_ShoppingCart[ShoppingCart]
    cmd_ordering_cart_conversion_ConvertToOrder[/ConvertToOrder/] --> ch_ordering_cart_conversion_ConvertCartHandler
    ch_ordering_cart_conversion_ConvertCartHandler --> agg_ordering_cart_cart_ShoppingCart[ShoppingCart]
    cmd_ordering_cart_coupons_ApplyCouponToCart[/ApplyCouponToCart/] --> ch_ordering_cart_coupons_ApplyCouponHandler
    ch_ordering_cart_coupons_ApplyCouponHandler --> agg_ordering_cart_cart_ShoppingCart[ShoppingCart]
    cmd_ordering_cart_items_AddToCart[/AddToCart/] --> ch_ordering_cart_items_ManageCartItemsHandler
    cmd_ordering_cart_items_RemoveFromCart[/RemoveFromCart/] --> ch_ordering_cart_items_ManageCartItemsHandler
    cmd_ordering_cart_items_UpdateCartQuantity[/UpdateCartQuantity/] --> ch_ordering_cart_items_ManageCartItemsHandler
    ch_ordering_cart_items_ManageCartItemsHandler --> agg_ordering_cart_cart_ShoppingCart[ShoppingCart]
    cmd_ordering_cart_management_AbandonCart[/AbandonCart/] --> ch_ordering_cart_management_ManageCartHandler
    cmd_ordering_cart_management_CreateCart[/CreateCart/] --> ch_ordering_cart_management_ManageCartHandler
    cmd_ordering_cart_management_MergeGuestCart[/MergeGuestCart/] --> ch_ordering_cart_management_ManageCartHandler
    ch_ordering_cart_management_ManageCartHandler --> agg_ordering_cart_cart_ShoppingCart[ShoppingCart]
    cmd_ordering_order_cancellation_CancelOrder[/CancelOrder/] --> ch_ordering_order_cancellation_CancelOrderHandler
    cmd_ordering_order_cancellation_RefundOrder[/RefundOrder/] --> ch_ordering_order_cancellation_CancelOrderHandler
    ch_ordering_order_cancellation_CancelOrderHandler --> agg_ordering_order_order_Order[Order]
    cmd_ordering_order_completion_CompleteOrder[/CompleteOrder/] --> ch_ordering_order_completion_CompleteOrderHandler
    ch_ordering_order_completion_CompleteOrderHandler --> agg_ordering_order_order_Order[Order]
    cmd_ordering_order_confirmation_ConfirmOrder[/ConfirmOrder/] --> ch_ordering_order_confirmation_ConfirmOrderHandler
    ch_ordering_order_confirmation_ConfirmOrderHandler --> agg_ordering_order_order_Order[Order]
    cmd_ordering_order_creation_CreateOrder[/CreateOrder/] --> ch_ordering_order_creation_CreateOrderHandler
    ch_ordering_order_creation_CreateOrderHandler --> agg_ordering_order_order_Order[Order]
    cmd_ordering_order_fulfillment_MarkProcessing[/MarkProcessing/] --> ch_ordering_order_fulfillment_RecordFulfillmentHandler
    cmd_ordering_order_fulfillment_RecordDelivery[/RecordDelivery/] --> ch_ordering_order_fulfillment_RecordFulfillmentHandler
    cmd_ordering_order_fulfillment_RecordPartialShipment[/RecordPartialShipment/] --> ch_ordering_order_fulfillment_RecordFulfillmentHandler
    cmd_ordering_order_fulfillment_RecordShipment[/RecordShipment/] --> ch_ordering_order_fulfillment_RecordFulfillmentHandler
    ch_ordering_order_fulfillment_RecordFulfillmentHandler --> agg_ordering_order_order_Order[Order]
    cmd_ordering_order_modification_AddItem[/AddItem/] --> ch_ordering_order_modification_ModifyOrderHandler
    cmd_ordering_order_modification_ApplyCoupon[/ApplyCoupon/] --> ch_ordering_order_modification_ModifyOrderHandler
    cmd_ordering_order_modification_RemoveItem[/RemoveItem/] --> ch_ordering_order_modification_ModifyOrderHandler
    cmd_ordering_order_modification_UpdateItemQuantity[/UpdateItemQuantity/] --> ch_ordering_order_modification_ModifyOrderHandler
    ch_ordering_order_modification_ModifyOrderHandler --> agg_ordering_order_order_Order[Order]
    cmd_ordering_order_payment_RecordPaymentFailure[/RecordPaymentFailure/] --> ch_ordering_order_payment_RecordPaymentHandler
    cmd_ordering_order_payment_RecordPaymentPending[/RecordPaymentPending/] --> ch_ordering_order_payment_RecordPaymentHandler
    cmd_ordering_order_payment_RecordPaymentSuccess[/RecordPaymentSuccess/] --> ch_ordering_order_payment_RecordPaymentHandler
    ch_ordering_order_payment_RecordPaymentHandler --> agg_ordering_order_order_Order[Order]
    cmd_ordering_order_returns_ApproveReturn[/ApproveReturn/] --> ch_ordering_order_returns_ManageReturnsHandler
    cmd_ordering_order_returns_RecordReturn[/RecordReturn/] --> ch_ordering_order_returns_ManageReturnsHandler
    cmd_ordering_order_returns_RequestReturn[/RequestReturn/] --> ch_ordering_order_returns_ManageReturnsHandler
    ch_ordering_order_returns_ManageReturnsHandler --> agg_ordering_order_order_Order[Order]
    evt_ordering_order_events_OrderCancelled([OrderCancelled]) -->|end| pm_ordering_checkout_saga_OrderCheckoutSaga
    evt_ordering_order_events_OrderConfirmed([OrderConfirmed]) -->|start| pm_ordering_checkout_saga_OrderCheckoutSaga
    evt_ordering_order_events_PaymentFailed([PaymentFailed]) --> pm_ordering_checkout_saga_OrderCheckoutSaga
    evt_ordering_order_events_PaymentPending([PaymentPending]) --> pm_ordering_checkout_saga_OrderCheckoutSaga
    evt_ordering_order_events_PaymentSucceeded([PaymentSucceeded]) --> pm_ordering_checkout_saga_OrderCheckoutSaga
    evt_ordering_order_events_OrderCancelled([OrderCancelled]) --> proj_ordering_projections_abandoned_checkouts_AbandonedCheckoutProjector
    evt_ordering_order_events_OrderConfirmed([OrderConfirmed]) --> proj_ordering_projections_abandoned_checkouts_AbandonedCheckoutProjector
    evt_ordering_order_events_OrderCreated([OrderCreated]) --> proj_ordering_projections_abandoned_checkouts_AbandonedCheckoutProjector
    evt_ordering_cart_events_CartAbandoned([CartAbandoned]) --> proj_ordering_projections_cart_view_CartViewProjector
    evt_ordering_cart_events_CartConverted([CartConverted]) --> proj_ordering_projections_cart_view_CartViewProjector
    evt_ordering_cart_events_CartCouponApplied([CartCouponApplied]) --> proj_ordering_projections_cart_view_CartViewProjector
    evt_ordering_cart_events_CartItemAdded([CartItemAdded]) --> proj_ordering_projections_cart_view_CartViewProjector
    evt_ordering_cart_events_CartItemRemoved([CartItemRemoved]) --> proj_ordering_projections_cart_view_CartViewProjector
    evt_ordering_cart_events_CartQuantityUpdated([CartQuantityUpdated]) --> proj_ordering_projections_cart_view_CartViewProjector
    evt_ordering_cart_events_CartsMerged([CartsMerged]) --> proj_ordering_projections_cart_view_CartViewProjector
    evt_ordering_order_events_OrderCancelled([OrderCancelled]) --> proj_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_OrderCompleted([OrderCompleted]) --> proj_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_OrderConfirmed([OrderConfirmed]) --> proj_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_OrderCreated([OrderCreated]) --> proj_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_OrderDelivered([OrderDelivered]) --> proj_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_OrderPartiallyShipped([OrderPartiallyShipped]) --> proj_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_OrderProcessing([OrderProcessing]) --> proj_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_OrderRefunded([OrderRefunded]) --> proj_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_OrderReturned([OrderReturned]) --> proj_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_OrderShipped([OrderShipped]) --> proj_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_PaymentFailed([PaymentFailed]) --> proj_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_PaymentPending([PaymentPending]) --> proj_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_PaymentSucceeded([PaymentSucceeded]) --> proj_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_ReturnApproved([ReturnApproved]) --> proj_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_ReturnRequested([ReturnRequested]) --> proj_ordering_projections_customer_orders_CustomerOrdersProjector
    evt_ordering_order_events_OrderCancelled([OrderCancelled]) --> proj_ordering_projections_daily_order_stats_DailyOrderStatsProjector
    evt_ordering_order_events_OrderCompleted([OrderCompleted]) --> proj_ordering_projections_daily_order_stats_DailyOrderStatsProjector
    evt_ordering_order_events_OrderCreated([OrderCreated]) --> proj_ordering_projections_daily_order_stats_DailyOrderStatsProjector
    evt_ordering_order_events_OrderRefunded([OrderRefunded]) --> proj_ordering_projections_daily_order_stats_DailyOrderStatsProjector
    evt_ordering_order_events_CouponApplied([CouponApplied]) --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_ItemAdded([ItemAdded]) --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_ItemQuantityUpdated([ItemQuantityUpdated]) --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_ItemRemoved([ItemRemoved]) --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_OrderCancelled([OrderCancelled]) --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_OrderCompleted([OrderCompleted]) --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_OrderConfirmed([OrderConfirmed]) --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_OrderCreated([OrderCreated]) --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_OrderDelivered([OrderDelivered]) --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_OrderPartiallyShipped([OrderPartiallyShipped]) --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_OrderProcessing([OrderProcessing]) --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_OrderRefunded([OrderRefunded]) --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_OrderReturned([OrderReturned]) --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_OrderShipped([OrderShipped]) --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_PaymentFailed([PaymentFailed]) --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_PaymentPending([PaymentPending]) --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_PaymentSucceeded([PaymentSucceeded]) --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_ReturnApproved([ReturnApproved]) --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_ReturnRequested([ReturnRequested]) --> proj_ordering_projections_order_detail_OrderDetailProjector
    evt_ordering_order_events_ItemAdded([ItemAdded]) --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_ItemQuantityUpdated([ItemQuantityUpdated]) --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_ItemRemoved([ItemRemoved]) --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_OrderCancelled([OrderCancelled]) --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_OrderCompleted([OrderCompleted]) --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_OrderConfirmed([OrderConfirmed]) --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_OrderCreated([OrderCreated]) --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_OrderDelivered([OrderDelivered]) --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_OrderPartiallyShipped([OrderPartiallyShipped]) --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_OrderProcessing([OrderProcessing]) --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_OrderRefunded([OrderRefunded]) --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_OrderReturned([OrderReturned]) --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_OrderShipped([OrderShipped]) --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_PaymentFailed([PaymentFailed]) --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_PaymentPending([PaymentPending]) --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_PaymentSucceeded([PaymentSucceeded]) --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_ReturnApproved([ReturnApproved]) --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_ReturnRequested([ReturnRequested]) --> proj_ordering_projections_order_summary_OrderSummaryProjector
    evt_ordering_order_events_CouponApplied([CouponApplied]) --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_ItemAdded([ItemAdded]) --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_ItemQuantityUpdated([ItemQuantityUpdated]) --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_ItemRemoved([ItemRemoved]) --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_OrderCancelled([OrderCancelled]) --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_OrderCompleted([OrderCompleted]) --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_OrderConfirmed([OrderConfirmed]) --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_OrderCreated([OrderCreated]) --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_OrderDelivered([OrderDelivered]) --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_OrderPartiallyShipped([OrderPartiallyShipped]) --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_OrderProcessing([OrderProcessing]) --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_OrderRefunded([OrderRefunded]) --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_OrderReturned([OrderReturned]) --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_OrderShipped([OrderShipped]) --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_PaymentFailed([PaymentFailed]) --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_PaymentPending([PaymentPending]) --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_PaymentSucceeded([PaymentSucceeded]) --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_ReturnApproved([ReturnApproved]) --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_ReturnRequested([ReturnRequested]) --> proj_ordering_projections_order_timeline_OrderTimelineProjector
    evt_ordering_order_events_OrderCancelled([OrderCancelled]) --> proj_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_OrderCompleted([OrderCompleted]) --> proj_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_OrderConfirmed([OrderConfirmed]) --> proj_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_OrderCreated([OrderCreated]) --> proj_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_OrderDelivered([OrderDelivered]) --> proj_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_OrderPartiallyShipped([OrderPartiallyShipped]) --> proj_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_OrderProcessing([OrderProcessing]) --> proj_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_OrderRefunded([OrderRefunded]) --> proj_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_OrderReturned([OrderReturned]) --> proj_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_OrderShipped([OrderShipped]) --> proj_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_PaymentFailed([PaymentFailed]) --> proj_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_PaymentPending([PaymentPending]) --> proj_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_PaymentSucceeded([PaymentSucceeded]) --> proj_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_ReturnApproved([ReturnApproved]) --> proj_ordering_projections_orders_by_status_OrdersByStatusProjector
    evt_ordering_order_events_ReturnRequested([ReturnRequested]) --> proj_ordering_projections_orders_by_status_OrdersByStatusProjector
```
