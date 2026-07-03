# Event & Command Catalog

## ShoppingCart (`ordering.cart.cart.ShoppingCart`)

### Events

#### CartAbandoned

- **Type**: `Ordering.CartAbandoned.v1`
- **Version**: 1
- **Published**: Yes
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| abandoned_at | DateTime | Yes | — |
| cart_id | Identifier | Yes | min_length=1 |

#### CartConverted

- **Type**: `Ordering.CartConverted.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| cart_id | Identifier | Yes | min_length=1 |
| customer_id | Identifier | No | — |
| items | List[dict] | Yes | — |

#### CartCouponApplied

- **Type**: `Ordering.CartCouponApplied.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| cart_id | Identifier | Yes | min_length=1 |
| coupon_code | String | Yes | max_length=255, min_length=1 |

#### CartItemAdded

- **Type**: `Ordering.CartItemAdded.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| cart_id | Identifier | Yes | min_length=1 |
| item_id | Identifier | Yes | min_length=1 |
| product_id | Identifier | Yes | min_length=1 |
| quantity | Integer | Yes | — |
| variant_id | Identifier | Yes | min_length=1 |

#### CartItemRemoved

- **Type**: `Ordering.CartItemRemoved.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| cart_id | Identifier | Yes | min_length=1 |
| item_id | Identifier | Yes | min_length=1 |

#### CartQuantityUpdated

- **Type**: `Ordering.CartQuantityUpdated.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| cart_id | Identifier | Yes | min_length=1 |
| item_id | Identifier | Yes | min_length=1 |
| new_quantity | Integer | Yes | — |
| previous_quantity | Integer | Yes | — |

#### CartsMerged

- **Type**: `Ordering.CartsMerged.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| cart_id | Identifier | Yes | min_length=1 |
| items_merged_count | Integer | Yes | — |
| source_session_id | String | No | max_length=255 |

### Commands

#### DetectAbandonedCarts

- **Type**: `Ordering.DetectAbandonedCarts.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| as_of | DateTime | No | — |
| idle_threshold_hours | Integer | No | — |

#### ConvertToOrder

- **Type**: `Ordering.ConvertToOrder.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| cart_id | Identifier | Yes | min_length=1 |

#### ApplyCouponToCart

- **Type**: `Ordering.ApplyCouponToCart.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| cart_id | Identifier | Yes | min_length=1 |
| coupon_code | String | Yes | max_length=100, min_length=1 |

#### AddToCart

- **Type**: `Ordering.AddToCart.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| cart_id | Identifier | Yes | min_length=1 |
| product_id | Identifier | Yes | min_length=1 |
| quantity | Integer | Yes | min_value=1 |
| variant_id | Identifier | Yes | min_length=1 |

#### RemoveFromCart

- **Type**: `Ordering.RemoveFromCart.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| cart_id | Identifier | Yes | min_length=1 |
| item_id | Identifier | Yes | min_length=1 |

#### UpdateCartQuantity

- **Type**: `Ordering.UpdateCartQuantity.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| cart_id | Identifier | Yes | min_length=1 |
| item_id | Identifier | Yes | min_length=1 |
| new_quantity | Integer | Yes | min_value=1 |

#### AbandonCart

- **Type**: `Ordering.AbandonCart.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| cart_id | Identifier | Yes | min_length=1 |

#### CreateCart

- **Type**: `Ordering.CreateCart.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| customer_id | Identifier | No | — |
| session_id | String | No | max_length=255 |

#### MergeGuestCart

- **Type**: `Ordering.MergeGuestCart.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| cart_id | Identifier | Yes | min_length=1 |
| guest_cart_items | List[dict] | Yes | — |

## Order (`ordering.order.order.Order`)

### Events

#### CouponApplied

- **Type**: `Ordering.CouponApplied.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| applied_at | DateTime | Yes | — |
| coupon_code | String | Yes | max_length=255, min_length=1 |
| order_id | Identifier | Yes | min_length=1 |

#### ItemAdded

- **Type**: `Ordering.ItemAdded.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| added_at | DateTime | Yes | — |
| item_id | Identifier | Yes | min_length=1 |
| new_grand_total | Float | Yes | — |
| new_subtotal | Float | Yes | — |
| order_id | Identifier | Yes | min_length=1 |
| product_id | Identifier | Yes | min_length=1 |
| quantity | String | Yes | max_length=255, min_length=1 |
| sku | String | Yes | max_length=255, min_length=1 |
| title | String | Yes | max_length=255, min_length=1 |
| unit_price | String | Yes | max_length=255, min_length=1 |
| variant_id | Identifier | Yes | min_length=1 |

#### ItemQuantityUpdated

- **Type**: `Ordering.ItemQuantityUpdated.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| item_id | Identifier | Yes | min_length=1 |
| new_grand_total | Float | Yes | — |
| new_quantity | String | Yes | max_length=255, min_length=1 |
| new_subtotal | Float | Yes | — |
| order_id | Identifier | Yes | min_length=1 |
| previous_quantity | String | Yes | max_length=255, min_length=1 |
| updated_at | DateTime | Yes | — |

#### ItemRemoved

- **Type**: `Ordering.ItemRemoved.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| item_id | Identifier | Yes | min_length=1 |
| new_grand_total | Float | Yes | — |
| new_subtotal | Float | Yes | — |
| order_id | Identifier | Yes | min_length=1 |
| removed_at | DateTime | Yes | — |

#### OrderCancelled

- **Type**: `Ordering.OrderCancelled.v1`
- **Version**: 1
- **Published**: Yes
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| cancelled_at | DateTime | Yes | — |
| cancelled_by | String | Yes | max_length=255, min_length=1 |
| order_id | Identifier | Yes | min_length=1 |
| reason | String | Yes | max_length=255, min_length=1 |

#### OrderCompleted

- **Type**: `Ordering.OrderCompleted.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| completed_at | DateTime | Yes | — |
| order_id | Identifier | Yes | min_length=1 |

#### OrderConfirmed

- **Type**: `Ordering.OrderConfirmed.v1`
- **Version**: 1
- **Published**: Yes
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| confirmed_at | DateTime | Yes | — |
| order_id | Identifier | Yes | min_length=1 |

#### OrderCreated

- **Type**: `Ordering.OrderCreated.v2`
- **Version**: 2
- **Published**: Yes
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| billing_address | Dict | Yes | — |
| created_at | DateTime | Yes | — |
| currency | String | No | max_length=255 |
| customer_id | Identifier | Yes | min_length=1 |
| discount_total | Float | No | — |
| grand_total | Float | Yes | — |
| items | List[dict] | Yes | — |
| order_id | Identifier | Yes | min_length=1 |
| order_source | String | No | max_length=255 |
| shipping_address | Dict | Yes | — |
| shipping_cost | Float | No | — |
| subtotal | Float | Yes | — |
| tax_total | Float | No | — |

#### OrderDelivered

- **Type**: `Ordering.OrderDelivered.v1`
- **Version**: 1
- **Published**: Yes
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| customer_id | Identifier | Yes | min_length=1 |
| delivered_at | DateTime | Yes | — |
| order_id | Identifier | Yes | min_length=1 |

#### OrderPartiallyShipped

- **Type**: `Ordering.OrderPartiallyShipped.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| carrier | String | Yes | max_length=255, min_length=1 |
| order_id | Identifier | Yes | min_length=1 |
| shipment_id | String | Yes | max_length=255, min_length=1 |
| shipped_at | DateTime | Yes | — |
| shipped_item_ids | List[String] | No | — |
| tracking_number | String | Yes | max_length=255, min_length=1 |

#### OrderProcessing

- **Type**: `Ordering.OrderProcessing.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| order_id | Identifier | Yes | min_length=1 |
| started_at | DateTime | Yes | — |

#### OrderRefunded

- **Type**: `Ordering.OrderRefunded.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| order_id | Identifier | Yes | min_length=1 |
| refund_amount | Float | Yes | — |
| refunded_at | DateTime | Yes | — |

#### OrderReturned

- **Type**: `Ordering.OrderReturned.v1`
- **Version**: 1
- **Published**: Yes
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| order_id | Identifier | Yes | min_length=1 |
| returned_at | DateTime | Yes | — |
| returned_item_ids | List[String] | No | — |

#### OrderShipped

- **Type**: `Ordering.OrderShipped.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| carrier | String | Yes | max_length=255, min_length=1 |
| estimated_delivery | String | No | max_length=255 |
| order_id | Identifier | Yes | min_length=1 |
| shipment_id | String | Yes | max_length=255, min_length=1 |
| shipped_at | DateTime | Yes | — |
| shipped_item_ids | List[String] | No | — |
| tracking_number | String | Yes | max_length=255, min_length=1 |

#### PaymentFailed

- **Type**: `Ordering.PaymentFailed.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| failed_at | DateTime | Yes | — |
| order_id | Identifier | Yes | min_length=1 |
| payment_id | String | Yes | max_length=255, min_length=1 |
| reason | String | Yes | max_length=255, min_length=1 |

#### PaymentPending

- **Type**: `Ordering.PaymentPending.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| initiated_at | DateTime | Yes | — |
| order_id | Identifier | Yes | min_length=1 |
| payment_id | String | Yes | max_length=255, min_length=1 |
| payment_method | String | Yes | max_length=255, min_length=1 |

#### PaymentSucceeded

- **Type**: `Ordering.PaymentSucceeded.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| amount | Float | Yes | — |
| order_id | Identifier | Yes | min_length=1 |
| paid_at | DateTime | Yes | — |
| payment_id | String | Yes | max_length=255, min_length=1 |
| payment_method | String | Yes | max_length=255, min_length=1 |

#### ReturnApproved

- **Type**: `Ordering.ReturnApproved.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| approved_at | DateTime | Yes | — |
| order_id | Identifier | Yes | min_length=1 |

#### ReturnRequested

- **Type**: `Ordering.ReturnRequested.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| order_id | Identifier | Yes | min_length=1 |
| reason | String | Yes | max_length=255, min_length=1 |
| requested_at | DateTime | Yes | — |

### Commands

#### CancelOrder

- **Type**: `Ordering.CancelOrder.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| cancelled_by | String | Yes | max_length=50, min_length=1 |
| order_id | Identifier | Yes | min_length=1 |
| reason | String | Yes | max_length=500, min_length=1 |

#### RefundOrder

- **Type**: `Ordering.RefundOrder.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| order_id | Identifier | Yes | min_length=1 |
| refund_amount | Float | No | — |

#### CompleteOrder

- **Type**: `Ordering.CompleteOrder.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| order_id | Identifier | Yes | min_length=1 |

#### ConfirmOrder

- **Type**: `Ordering.ConfirmOrder.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| order_id | Identifier | Yes | min_length=1 |

#### CreateOrder

- **Type**: `Ordering.CreateOrder.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| billing_address | Dict | Yes | — |
| currency | String | No | max_length=3 |
| customer_id | Identifier | Yes | min_length=1 |
| discount_total | Float | No | — |
| grand_total | Float | Yes | — |
| items | List[dict] | Yes | — |
| order_source | String | No | max_length=20 |
| shipping_address | Dict | Yes | — |
| shipping_cost | Float | No | — |
| subtotal | Float | Yes | — |
| tax_total | Float | No | — |

#### MarkProcessing

- **Type**: `Ordering.MarkProcessing.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| order_id | Identifier | Yes | min_length=1 |

#### RecordDelivery

- **Type**: `Ordering.RecordDelivery.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| order_id | Identifier | Yes | min_length=1 |

#### RecordPartialShipment

- **Type**: `Ordering.RecordPartialShipment.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| carrier | String | Yes | max_length=100, min_length=1 |
| order_id | Identifier | Yes | min_length=1 |
| shipment_id | String | Yes | max_length=255, min_length=1 |
| shipped_item_ids | List[String] | Yes | — |
| tracking_number | String | Yes | max_length=255, min_length=1 |

#### RecordShipment

- **Type**: `Ordering.RecordShipment.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| carrier | String | Yes | max_length=100, min_length=1 |
| estimated_delivery | String | No | max_length=10 |
| order_id | Identifier | Yes | min_length=1 |
| shipment_id | String | Yes | max_length=255, min_length=1 |
| shipped_item_ids | List[String] | No | — |
| tracking_number | String | Yes | max_length=255, min_length=1 |

#### AddItem

- **Type**: `Ordering.AddItem.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| order_id | Identifier | Yes | min_length=1 |
| product_id | Identifier | Yes | min_length=1 |
| quantity | Integer | Yes | min_value=1 |
| sku | String | Yes | max_length=50, min_length=1 |
| title | String | Yes | max_length=255, min_length=1 |
| unit_price | Float | Yes | min_value=0.0 |
| variant_id | Identifier | Yes | min_length=1 |

#### ApplyCoupon

- **Type**: `Ordering.ApplyCoupon.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| coupon_code | String | Yes | max_length=100, min_length=1 |
| order_id | Identifier | Yes | min_length=1 |

#### RemoveItem

- **Type**: `Ordering.RemoveItem.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| item_id | Identifier | Yes | min_length=1 |
| order_id | Identifier | Yes | min_length=1 |

#### UpdateItemQuantity

- **Type**: `Ordering.UpdateItemQuantity.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| item_id | Identifier | Yes | min_length=1 |
| new_quantity | Integer | Yes | min_value=1 |
| order_id | Identifier | Yes | min_length=1 |

#### RecordPaymentFailure

- **Type**: `Ordering.RecordPaymentFailure.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| order_id | Identifier | Yes | min_length=1 |
| payment_id | String | Yes | max_length=255, min_length=1 |
| reason | String | Yes | max_length=500, min_length=1 |

#### RecordPaymentPending

- **Type**: `Ordering.RecordPaymentPending.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| order_id | Identifier | Yes | min_length=1 |
| payment_id | String | Yes | max_length=255, min_length=1 |
| payment_method | String | Yes | max_length=50, min_length=1 |

#### RecordPaymentSuccess

- **Type**: `Ordering.RecordPaymentSuccess.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| amount | Float | Yes | — |
| order_id | Identifier | Yes | min_length=1 |
| payment_id | String | Yes | max_length=255, min_length=1 |
| payment_method | String | Yes | max_length=50, min_length=1 |

#### ApproveReturn

- **Type**: `Ordering.ApproveReturn.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| order_id | Identifier | Yes | min_length=1 |

#### RecordReturn

- **Type**: `Ordering.RecordReturn.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| order_id | Identifier | Yes | min_length=1 |
| returned_item_ids | List[String] | No | — |

#### RequestReturn

- **Type**: `Ordering.RequestReturn.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| order_id | Identifier | Yes | min_length=1 |
| reason | String | Yes | max_length=500, min_length=1 |

---

## Published Event Contracts

| Event | Type | Version |
|-------|------|---------|
| CartAbandoned | `Ordering.CartAbandoned.v1` | 1 |
| OrderCancelled | `Ordering.OrderCancelled.v1` | 1 |
| OrderConfirmed | `Ordering.OrderConfirmed.v1` | 1 |
| OrderCreated | `Ordering.OrderCreated.v2` | 2 |
| OrderDelivered | `Ordering.OrderDelivered.v1` | 1 |
| OrderReturned | `Ordering.OrderReturned.v1` | 1 |
