# Context Map

> How ShopStream's bounded contexts relate to each other.

## Overview

ShopStream is decomposed into six bounded contexts, each owning a distinct
area of business responsibility. The contexts share **no domain objects** --
they communicate only through opaque identifiers and asynchronous domain events.

This separation exists because each context has fundamentally different
consistency requirements, change rates, and scalability needs:

- **Identity** changes slowly (customers register once, update profiles occasionally)
  and demands strong consistency on account status.
- **Catalogue** changes at a medium pace (products added/updated by sellers) and
  tolerates eventual consistency for search and browse views.
- **Ordering** changes rapidly (orders placed, paid, shipped throughout the day) and
  requires both strong consistency for financial transactions and a complete audit
  trail for disputes.
- **Inventory** changes at high frequency during peak sales (reservations, shipments,
  adjustments) and requires event sourcing for a complete audit trail of every stock
  movement, enabling financial reconciliation and shrinkage analysis.
- **Payments** handles financial transactions with strict audit requirements and
  demands event sourcing for complete charge/refund traceability. Changes correlate
  with order confirmations and are typically low-frequency per order.
- **Fulfillment** bridges the gap between payment and delivery. It operates at
  warehouse pace -- fulfillments progress linearly through pick/pack/ship/deliver
  and use standard CQRS since carriers own the tracking state of truth.

```mermaid
graph TB
    subgraph ShopStream["ShopStream Platform"]
        identity["<b>Identity</b><br/>Customer accounts, profiles,<br/>addresses, loyalty tiers<br/><i>1 aggregate &middot; 10 events</i>"]
        catalogue["<b>Catalogue</b><br/>Products, variants, categories,<br/>pricing, images<br/><i>2 aggregates &middot; 13 events</i>"]
        ordering["<b>Ordering</b><br/>Shopping carts, orders,<br/>fulfillment, returns<br/><i>2 aggregates &middot; 25 events</i>"]
        inventory["<b>Inventory</b><br/>Stock levels, reservations,<br/>warehouses, damage tracking<br/><i>2 aggregates &middot; 18 events</i>"]
        payments["<b>Payments</b><br/>Charges, refunds, invoices,<br/>gateway integration<br/><i>2 aggregates &middot; 10 events</i>"]
        fulfillment_ctx["<b>Fulfillment</b><br/>Picking, packing, shipping,<br/>tracking, delivery<br/><i>1 aggregate &middot; 11 events</i>"]
    end

    ordering -- "customer_id" --> identity
    ordering -- "product_id, variant_id, sku" --> catalogue
    inventory -- "product_id, variant_id" --> catalogue
    inventory -. "order_id (reservations)" .-> ordering
    payments -- "order_id, customer_id" --> ordering
    fulfillment_ctx -- "order_id, customer_id" --> ordering
    fulfillment_ctx -. "ShipmentHandedOff" .-> ordering
    fulfillment_ctx -. "DeliveryConfirmed" .-> ordering
    fulfillment_ctx -. "ShipmentHandedOff" .-> inventory
    ordering -. "OrderCancelled" .-> fulfillment_ctx

    style identity fill:#4a90d9,color:#fff,stroke:#2a6cb0
    style catalogue fill:#7bc96f,color:#fff,stroke:#4a9e3f
    style ordering fill:#e8a838,color:#fff,stroke:#c08020
    style inventory fill:#d94a8a,color:#fff,stroke:#b02a6c
    style payments fill:#9b59b6,color:#fff,stroke:#7d3c98
    style fulfillment_ctx fill:#1abc9c,color:#fff,stroke:#16a085
```

## Context Relationships

### Ordering &rarr; Identity

The Ordering context references customers by their `customer_id` -- an opaque
identifier. When an order is created, the customer ID is stored on the Order aggregate,
but the Ordering context never loads, queries, or validates the Customer aggregate.

This is a **conformist** relationship: Ordering accepts Identity's ID format without
interpretation. If a customer is suspended or closed in Identity, existing orders
continue unaffected -- the Ordering context does not subscribe to Identity events
(in this version of ShopStream).

In a production system, you might add a subscriber that reacts to `AccountSuspended`
or `AccountClosed` events to prevent new orders from suspended accounts.

### Ordering &rarr; Catalogue

The Ordering context references products by `product_id`, `variant_id`, and snapshots
the `sku`, `title`, and `unit_price` at order creation time. This snapshot is critical:
if a product's price or title changes after an order is placed, the order retains the
values that were in effect when the customer committed.

This is a **customer-supplier** relationship: the Catalogue context supplies product
data, and the Ordering context consumes a snapshot of it. The Ordering context is
insulated from changes to the product after the order is placed.

Shopping Carts store only `product_id` and `variant_id` (no price snapshot) because
prices are resolved at checkout time, not when items are added to the cart.

### Inventory &rarr; Catalogue

The Inventory context references products by `product_id` and `variant_id` --
opaque identifiers from the Catalogue context. Each InventoryItem tracks stock
for one specific product variant at one warehouse. The Inventory context never
loads or queries the Product aggregate -- it only stores the IDs for correlation.

This is a **conformist** relationship: Inventory accepts Catalogue's ID format
without interpretation. If a product is discontinued in Catalogue, existing
InventoryItems are unaffected -- the Inventory context does not subscribe to
Catalogue events (in this version).

### Inventory &harr; Ordering

The Inventory context has a bidirectional relationship with Ordering:

- **Ordering &rarr; Inventory**: When an order is placed, the Ordering context
  issues a `ReserveStock` command to hold inventory. After payment, it issues
  `ConfirmReservation`. After shipping, `CommitStock`. If cancelled,
  `ReleaseReservation`. The `order_id` is stored on Reservation entities.
- **Inventory &rarr; Ordering**: Inventory's `StockReserved`, `ReservationReleased`,
  and `LowStockDetected` events inform the Ordering context about stock
  availability and reservation outcomes.

Currently, these interactions happen via API calls (synchronous commands). In a
production system, the Ordering context would subscribe to Inventory events to
react asynchronously to reservation outcomes.

### Payments &rarr; Ordering

The Payments context references orders by `order_id` and `customer_id` -- opaque
identifiers from the Ordering context. When a payment is initiated, it stores the
order ID for correlation. Payment events (`PaymentSucceeded`, `PaymentFailed`) are
consumed by the `OrderCheckoutSaga` in the Ordering domain via `register_external_event()`.

This is a **customer-supplier** relationship: Ordering supplies the order ID and
consumes payment outcome events. The saga coordinates the multi-step checkout flow:
reserve stock &rarr; charge payment &rarr; update order status.

### Fulfillment &harr; Ordering

The Fulfillment context has a bidirectional event-driven relationship with Ordering:

- **Ordering &rarr; Fulfillment**: When an order is cancelled, the Ordering context
  raises `OrderCancelled`. The Fulfillment domain subscribes to the `ordering::order`
  stream and cancels in-progress fulfillments (if still cancellable).
- **Fulfillment &rarr; Ordering**: When a shipment is handed to the carrier,
  `ShipmentHandedOff` triggers `RecordShipment` on the Order (status &rarr; Shipped).
  When delivery is confirmed, `DeliveryConfirmed` triggers `RecordDelivery` (status
  &rarr; Delivered).

Cross-domain events flow via the shared events module (`src/shared/events/`) and
`register_external_event()`. Each domain subscribes to the other's event stream.

### Fulfillment &rarr; Inventory

The Fulfillment context triggers stock commitment in Inventory:

- When `ShipmentHandedOff` is raised, the Inventory domain's
  `FulfillmentInventoryEventHandler` subscribes to the `fulfillment::fulfillment`
  stream. It finds active reservations for the shipped order and issues `CommitStock`
  commands, reducing on-hand and clearing reservations.

This is a one-way **event-driven** relationship. Fulfillment does not know about
Inventory -- it simply raises `ShipmentHandedOff`. Inventory independently reacts.

## Communication Patterns

| Pattern | Where Used | Why |
|---------|-----------|-----|
| **Opaque IDs** (no shared objects) | All cross-context references | Keeps bounded contexts decoupled. Each context has its own data model. |
| **Data snapshots** | Order Items capture sku, title, unit_price from Catalogue | Orders must be immutable once placed, even if product data changes later. |
| **Domain events via outbox + Redis Streams** | All async reactions within each context | Events are written atomically with aggregate state changes. Engine workers consume them and update projections. |
| **Cross-domain events via shared contracts** | Fulfillment &harr; Ordering, Fulfillment &rarr; Inventory, Payments &harr; Ordering | Events defined in `src/shared/events/`, registered via `register_external_event()`, consumed from other domains' streams. |
| **Synchronous command processing** | All write operations within each context | Commands are processed in the same request. The API returns only after the aggregate state change is committed. |

## What This Context Map Does NOT Show (Yet)

ShopStream has cross-context event subscriptions for the checkout saga (Payments
&harr; Ordering), fulfillment lifecycle (Fulfillment &harr; Ordering, Fulfillment
&rarr; Inventory), and order cancellation (Ordering &rarr; Fulfillment). In a
production e-commerce system, you would likely add:

- **Ordering subscribes to Catalogue's `ProductDiscontinued`** -- to prevent new orders
  for discontinued products.
- **Ordering subscribes to Identity's `AccountSuspended`** -- to block new orders from
  suspended customers.
- **A Purchasing context subscribes to Inventory's `LowStockDetected`** -- to generate
  reorder requests automatically.
- **A Notification context** -- subscribing to `OrderShipped`, `OrderDelivered`,
  `ReturnApproved`, `LowStockDetected`, and `DeliveryException` events to send emails
  and push notifications.
- **A Returns context** -- handling post-delivery returns, restock, and refund coordination
  across Ordering, Inventory, and Payments.

These extensions would be natural additions as ShopStream evolves.
