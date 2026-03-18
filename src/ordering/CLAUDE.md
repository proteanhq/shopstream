# Ordering Domain

Shopping carts, order lifecycle (event-sourced), checkout flow, and the checkout saga.

## Domain Composition Root

`domain.py` — `ordering = Domain(name="ordering")`

All elements register via `@ordering.<element_type>` decorators.

## Configuration

`domain.toml` — PostgreSQL database, Redis broker, Message DB event store. Priority lanes enabled (priority < 0 routes to backfill lane). Environment overlays for test (`ordering_test` DB) and production (`ordering` DB, async events).

## Aggregate: ShoppingCart (CQRS)

**File:** `cart/cart.py`

Root fields: `customer_id` (optional, nullable for guest carts), `session_id`, `items` (HasMany CartItem), `applied_coupons` (JSON text), `status` (CartStatus enum), `created_at`, `updated_at`.

### Enums
- `CartStatus`: Active, Converted, Abandoned

### Entity (part_of="ShoppingCart")
- `CartItem` — product_id, variant_id, quantity (min 1), added_at. Does not store prices — prices are resolved from Catalogue at checkout time.

### Invariants
- `cart_must_have_items_to_convert` — cannot convert empty cart to order

### Aggregate Methods
| Method | Behavior |
|--------|----------|
| `ShoppingCart.create(customer_id?, session_id?)` | Class method, creates Active cart, returns instance |
| `add_item(product_id, variant_id, quantity)` | Active only, increments existing or creates new CartItem, raises `CartItemAdded` |
| `update_item_quantity(item_id, new_quantity)` | Active only, raises `CartQuantityUpdated` |
| `remove_item(item_id)` | Active only, raises `CartItemRemoved` |
| `apply_coupon(coupon_code)` | Active only, no duplicate coupons, raises `CartCouponApplied` |
| `merge_guest_cart(guest_cart_items)` | Active only, merges guest items into customer cart, raises `CartsMerged` |
| `convert_to_order()` | Active only, must have items, snapshots items as JSON, raises `CartConverted` |
| `abandon()` | Active only, raises `CartAbandoned` |

## Aggregate: Order (Event-Sourced)

**File:** `order/order.py`

Root fields: `customer_id`, `status` (OrderStatus enum), `items` (HasMany OrderItem), `shipping_address` (ShippingAddress VO), `billing_address` (ShippingAddress VO), `pricing` (OrderPricing VO), `payment_id`, `payment_method`, `payment_status`, `shipment_id`, `carrier`, `tracking_number`, `estimated_delivery`, `cancellation_reason`, `cancelled_by`, `coupon_code`, `created_at`, `updated_at`.

### Enums
- `OrderStatus`: Created, Confirmed, Payment_Pending, Paid, Processing, Partially_Shipped, Shipped, Delivered, Completed, Return_Requested, Return_Approved, Returned, Cancelled, Refunded (14 states)
- `ItemStatus`: Pending, Reserved, Shipped, Delivered, Returned
- `CancellationActor`: Customer, System, Admin

### State Machine
```
Created          → Confirmed, Cancelled
Confirmed        → Payment_Pending, Cancelled
Payment_Pending  → Paid, Confirmed (retry on failure), Cancelled
Paid             → Processing, Cancelled
Processing       → Shipped, Partially_Shipped
Partially_Shipped → Shipped
Shipped          → Delivered
Delivered        → Completed, Return_Requested
Return_Requested → Return_Approved
Return_Approved  → Returned
Returned         → Refunded
Cancelled        → Refunded
Completed        → (terminal)
Refunded         → (terminal)
```

Cancellable states: Created, Confirmed, Payment_Pending, Paid.

### Value Objects (part_of="Order")
- `ShippingAddress` — street, city, state, postal_code, country (immutable once recorded)
- `OrderPricing` — subtotal, shipping_cost, tax_total, discount_total, grand_total, currency (locked at checkout)

### Entity (part_of="Order")
- `OrderItem` — product_id, variant_id, sku, title, quantity (min 1), unit_price (min 0), discount, tax_amount, item_status (tracks individual fulfillment lifecycle)

### Aggregate Methods
| Method | Behavior |
|--------|----------|
| `Order.create(customer_id, items_data, shipping_address, billing_address, pricing)` | Factory, event-sourced `_create_new()`, raises `OrderCreated` |
| `add_item(...)` | Created only, raises `ItemAdded` |
| `remove_item(item_id)` | Created only, raises `ItemRemoved` |
| `update_item_quantity(item_id, new_quantity)` | Created only, raises `ItemQuantityUpdated` |
| `apply_coupon(coupon_code)` | Created only, raises `CouponApplied` |
| `confirm()` | Created → Confirmed, raises `OrderConfirmed` |
| `record_payment_pending(payment_id, payment_method)` | Confirmed → Payment_Pending, raises `PaymentPending` |
| `record_payment_success(payment_id, amount, payment_method)` | Payment_Pending → Paid, raises `PaymentSucceeded` |
| `record_payment_failure(payment_id, reason)` | Payment_Pending → Confirmed (retry), raises `PaymentFailed` |
| `mark_processing()` | Paid → Processing, raises `OrderProcessing` |
| `record_shipment(shipment_id, carrier, tracking_number, shipped_item_ids?, estimated_delivery?)` | From Paid/Processing/Partially_Shipped, raises `OrderShipped` |
| `record_partial_shipment(shipment_id, carrier, tracking_number, shipped_item_ids)` | Processing only, raises `OrderPartiallyShipped` |
| `record_delivery()` | Shipped → Delivered, raises `OrderDelivered` |
| `complete()` | Delivered → Completed, raises `OrderCompleted` |
| `request_return(reason)` | Delivered → Return_Requested, raises `ReturnRequested` |
| `approve_return()` | Return_Requested → Return_Approved, raises `ReturnApproved` |
| `record_return(returned_item_ids?)` | Return_Approved → Returned, raises `OrderReturned` |
| `cancel(reason, cancelled_by)` | Only from cancellable states, raises `OrderCancelled` |
| `refund(refund_amount?)` | From Cancelled/Returned, defaults to grand_total, raises `OrderRefunded` |

All state changes are applied via `@apply` handlers for event-sourcing replay.

## Events

**Cart events** (`cart/events.py`): `CartItemAdded`, `CartQuantityUpdated`, `CartItemRemoved`, `CartCouponApplied`, `CartsMerged`, `CartConverted`, `CartAbandoned`

**Order events** (`order/events.py`): `OrderCreated`, `ItemAdded`, `ItemRemoved`, `ItemQuantityUpdated`, `CouponApplied`, `OrderConfirmed`, `PaymentPending`, `PaymentSucceeded`, `PaymentFailed`, `OrderProcessing`, `OrderShipped`, `OrderPartiallyShipped`, `OrderDelivered`, `OrderCompleted`, `ReturnRequested`, `ReturnApproved`, `OrderReturned`, `OrderCancelled`, `OrderRefunded`

## Commands & Handlers

### Cart Commands

| File | Commands |
|------|---------|
| `cart/management.py` | `CreateCart`, `MergeGuestCart`, `AbandonCart` → `ManageCartHandler` |
| `cart/items.py` | `AddToCart`, `UpdateCartQuantity`, `RemoveFromCart` → `ManageCartItemsHandler` |
| `cart/coupons.py` | `ApplyCouponToCart` → `ApplyCouponHandler` |
| `cart/conversion.py` | `ConvertToOrder` → `ConvertCartHandler` |

### Order Commands

| File | Commands |
|------|---------|
| `order/creation.py` | `CreateOrder` → `CreateOrderHandler` |
| `order/confirmation.py` | `ConfirmOrder` → `ConfirmOrderHandler` |
| `order/payment.py` | `RecordPaymentPending`, `RecordPaymentSuccess`, `RecordPaymentFailure` → `RecordPaymentHandler` |
| `order/modification.py` | `AddItem`, `RemoveItem`, `UpdateItemQuantity`, `ApplyCoupon` → `ModifyOrderHandler` |
| `order/fulfillment.py` | `MarkProcessing`, `RecordShipment`, `RecordPartialShipment`, `RecordDelivery` → `RecordFulfillmentHandler` |
| `order/completion.py` | `CompleteOrder` → `CompleteOrderHandler` |
| `order/cancellation.py` | `CancelOrder`, `RefundOrder` → `CancelOrderHandler` |
| `order/returns.py` | `RequestReturn`, `ApproveReturn`, `RecordReturn` → `ManageReturnsHandler` |

## Cross-Domain Integration

### Inbound: Fulfillment → Ordering
**File:** `order/fulfillment_subscriber.py`

`@ordering.subscriber(broker="global", stream="fulfillment::fulfillment")` — receives raw dict payloads (ACL pattern).

Subscriber `FulfillmentEventsSubscriber`:
- `ShipmentHandedOff` → dispatches `RecordShipment` command
- `DeliveryConfirmed` → dispatches `RecordDelivery` command

### Inbound: Identity → Ordering
**File:** `order/identity_subscriber.py`

`@ordering.subscriber(broker="global", stream="identity::customer")` — receives raw dict payloads (ACL pattern).

Subscriber `IdentityEventsSubscriber`:
- `AccountSuspended` → handles account suspension impact on orders
- `AccountReactivated` → handles account reactivation

### Inbound: Catalogue → Ordering
**File:** `cart/catalogue_subscriber.py`

`@ordering.subscriber(broker="global", stream="catalogue::product")` — receives raw dict payloads (ACL pattern).

Subscriber `CatalogueEventsSubscriber`:
- `ProductDiscontinued` → handles discontinued product impact on active carts

### Checkout Saga (Process Manager)
**File:** `checkout/saga.py`

`OrderCheckoutSaga` — event-sourced process manager that orchestrates the checkout flow across Ordering, Inventory, and Payments domains.

Listens on streams: `ordering::order`.

The saga reacts only to internal ordering events: `OrderConfirmed`, `PaymentPending`, `PaymentSucceeded`, `PaymentFailed`, `OrderCancelled`. External events from Inventory and Payments are translated into internal ordering commands by `checkout/inventory_subscriber.py` and `checkout/payment_subscriber.py`.

Saga flow (max 3 payment retries):
1. `OrderConfirmed` → status=awaiting_reservation
2. `StockReserved` (translated to internal command) → status=awaiting_payment, dispatches `RecordPaymentPending`
3. `PaymentSucceeded` (translated to internal command) → dispatches `RecordPaymentSuccess`, completes saga
3b. `PaymentFailed` (translated to internal command) → retries up to 3x, then dispatches `CancelOrder(cancelled_by="System")`
4. `ReservationReleased` (translated to internal command) → dispatches `CancelOrder(cancelled_by="System")`

## Projections

**Directory:** `projections/`

| File | Projection | Projector | Purpose |
|------|-----------|-----------|---------|
| `cart_view.py` | `CartView` | `CartViewProjector` | Cart contents view with item counts and coupons |
| `order_detail.py` | `OrderDetail` | `OrderDetailProjector` | Full order view — handles all 19 Order events |
| `order_summary.py` | `OrderSummary` | `OrderSummaryProjector` | Lightweight order listing (status, total, item count) |
| `order_timeline.py` | `OrderTimeline` | `OrderTimelineProjector` | Append-only audit trail with human-readable descriptions |
| `customer_orders.py` | `CustomerOrders` | `CustomerOrdersProjector` | Per-customer order listing |
| `orders_by_status.py` | `OrdersByStatus` | `OrdersByStatusProjector` | Admin dashboard view for filtering by status |

## API

**Package:** `api/`

| File | Contents |
|------|----------|
| `api/__init__.py` | Re-exports `cart_router` and `order_router` |
| `api/schemas.py` | Pydantic request/response models (external contract) |
| `api/routes.py` | 27 endpoints (8 cart + 19 order) |

### Cart Endpoints (`tags=["carts"]`)
| Method | Path | Request Body | Response |
|--------|------|-------------|----------|
| POST | `/carts` | `CreateCartRequest` | `CartIdResponse` (201) |
| POST | `/carts/{cart_id}/items` | `AddToCartRequest` | `StatusResponse` |
| PUT | `/carts/{cart_id}/items/{item_id}` | `UpdateCartQuantityRequest` | `StatusResponse` |
| DELETE | `/carts/{cart_id}/items/{item_id}` | — | `StatusResponse` |
| POST | `/carts/{cart_id}/coupons` | `ApplyCouponToCartRequest` | `StatusResponse` |
| POST | `/carts/{cart_id}/checkout` | `CheckoutRequest` | `OrderIdResponse` (201) |
| PUT | `/carts/{cart_id}/abandon` | — | `StatusResponse` |
| POST | `/carts/{cart_id}/merge` | `MergeGuestCartRequest` | `StatusResponse` |

### Order Endpoints (`tags=["orders"]`)
| Method | Path | Request Body | Response |
|--------|------|-------------|----------|
| POST | `/orders` | `CreateOrderRequest` | `OrderIdResponse` (201) |
| POST | `/orders/{order_id}/items` | `AddItemRequest` | `StatusResponse` |
| DELETE | `/orders/{order_id}/items/{item_id}` | — | `StatusResponse` |
| PUT | `/orders/{order_id}/items/{item_id}/quantity` | `UpdateItemQuantityRequest` | `StatusResponse` |
| POST | `/orders/{order_id}/coupon` | `ApplyCouponRequest` | `StatusResponse` |
| PUT | `/orders/{order_id}/confirm` | — | `StatusResponse` |
| PUT | `/orders/{order_id}/payment/pending` | `RecordPaymentPendingRequest` | `StatusResponse` |
| PUT | `/orders/{order_id}/payment/success` | `RecordPaymentSuccessRequest` | `StatusResponse` |
| PUT | `/orders/{order_id}/payment/failure` | `RecordPaymentFailureRequest` | `StatusResponse` |
| PUT | `/orders/{order_id}/processing` | — | `StatusResponse` |
| PUT | `/orders/{order_id}/ship` | `RecordShipmentRequest` | `StatusResponse` |
| PUT | `/orders/{order_id}/ship/partial` | `RecordPartialShipmentRequest` | `StatusResponse` |
| PUT | `/orders/{order_id}/deliver` | — | `StatusResponse` |
| PUT | `/orders/{order_id}/complete` | — | `StatusResponse` |
| PUT | `/orders/{order_id}/return/request` | `RequestReturnRequest` | `StatusResponse` |
| PUT | `/orders/{order_id}/return/approve` | — | `StatusResponse` |
| PUT | `/orders/{order_id}/return/record` | `RecordReturnRequest` | `StatusResponse` |
| PUT | `/orders/{order_id}/cancel` | `CancelOrderRequest` | `StatusResponse` |
| PUT | `/orders/{order_id}/refund` | `RefundOrderRequest` | `StatusResponse` |
