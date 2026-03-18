# Fulfillment Domain

Warehouse fulfillment lifecycle — picking, packing, shipping, tracking, and delivery.

## Domain Composition Root

`domain.py` — `fulfillment = Domain(name="fulfillment")`

All elements register via `@fulfillment.<element_type>` decorators.

## Configuration

`domain.toml` — PostgreSQL database, Redis broker, Message DB event store. Priority lanes enabled. Environment overlays for test (`fulfillment_test` DB) and production (`fulfillment` DB, async events).

## Aggregate: Fulfillment (CQRS)

**File:** `fulfillment/fulfillment.py`

Root fields: `order_id`, `customer_id`, `warehouse_id`, `status` (FulfillmentStatus enum), `items` (HasMany FulfillmentItem), `pick_list` (PickList VO), `packing_info` (PackingInfo VO), `packages` (HasMany Package), `shipment` (ShipmentInfo VO), `tracking_events` (HasMany TrackingEvent), `cancellation_reason`, `created_at`, `updated_at`.

### Enums
- `FulfillmentStatus`: Pending, Picking, Packing, Ready_To_Ship, Shipped, In_Transit, Delivered, Exception, Cancelled
- `FulfillmentItemStatus`: Pending, Picked, Packed
- `ServiceLevel`: Standard, Express, Overnight

### State Machine
```
Pending       → Picking, Cancelled
Picking       → Packing, Cancelled
Packing       → Ready_To_Ship, Cancelled
Ready_To_Ship → Shipped, Cancelled
Shipped       → In_Transit
In_Transit    → Delivered, Exception
Exception     → In_Transit (carrier reports movement), Delivered
Delivered     → (terminal)
Cancelled     → (terminal)
```

Cancellable statuses: Pending, Picking, Packing, Ready_To_Ship.

### Value Objects (part_of="Fulfillment")
- `PickList` — assigned_to, assigned_at, completed_at
- `PackingInfo` — packed_by, packed_at, shipping_label_url
- `ShipmentInfo` — carrier, service_level (ServiceLevel), tracking_number, estimated_delivery, actual_delivery
- `PackageDimensions` — weight, length, width, height

### Entities (part_of="Fulfillment")
- `FulfillmentItem` — order_item_id, product_id, sku, quantity (min 1), pick_location, status (FulfillmentItemStatus)
- `Package` — weight, dimensions (PackageDimensions VO), item_ids (JSON text)
- `TrackingEvent` — status, location, description, occurred_at

### Aggregate Methods
| Method | Behavior |
|--------|----------|
| `Fulfillment.create(order_id, customer_id, items_data, warehouse_id?)` | Factory, creates in Pending, raises `FulfillmentCreated` |
| `assign_picker(picker_name)` | Pending → Picking, creates PickList, raises `PickerAssigned` |
| `record_item_picked(item_id, pick_location)` | Picking only, marks item Picked, raises `ItemPicked` |
| `complete_pick_list()` | Picking only, all items must be Picked, → Packing, raises `PickingCompleted` |
| `record_packing(packed_by, packages_data)` | Packing only, creates Packages, marks all items Packed, raises `PackingCompleted` |
| `generate_shipping_label(label_url, carrier, service_level)` | Packing only (after packed), → Ready_To_Ship, raises `ShippingLabelGenerated` |
| `record_handoff(tracking_number, estimated_delivery?)` | → Shipped, sets tracking info, raises `ShipmentHandedOff` |
| `add_tracking_event(status, location?, description?)` | Shipped/In_Transit/Exception only, auto-transitions Shipped → In_Transit, raises `TrackingEventReceived` |
| `record_delivery()` | → Delivered, sets actual_delivery, raises `DeliveryConfirmed` |
| `record_exception(reason, location?)` | → Exception, appends TrackingEvent, raises `DeliveryException` |
| `cancel(reason)` | Only from cancellable statuses, raises `FulfillmentCancelled` |

## Events

**File:** `fulfillment/events.py` — All versioned (`__version__ = "v1"`), past tense names.

`FulfillmentCreated`, `PickerAssigned`, `ItemPicked`, `PickingCompleted`, `PackingCompleted`, `ShippingLabelGenerated`, `ShipmentHandedOff`, `TrackingEventReceived`, `DeliveryConfirmed`, `DeliveryException`, `FulfillmentCancelled`

## Commands & Handlers

One file per use case group, command + handler in same file:

| File | Commands |
|------|---------|
| `fulfillment/creation.py` | `CreateFulfillment` → `CreateFulfillmentHandler` |
| `fulfillment/picking.py` | `AssignPicker`, `RecordItemPicked`, `CompletePickList` → `PickingHandler` |
| `fulfillment/packing.py` | `RecordPacking`, `GenerateShippingLabel` → `PackingHandler` |
| `fulfillment/shipping.py` | `RecordHandoff` → `ShippingHandler` |
| `fulfillment/tracking.py` | `UpdateTrackingEvent` → `TrackingHandler` |
| `fulfillment/delivery.py` | `RecordDeliveryConfirmation`, `RecordDeliveryException` → `DeliveryHandler` |
| `fulfillment/cancellation.py` | `CancelFulfillment` → `CancelFulfillmentHandler` |

Handler pattern: load aggregate from repo → call aggregate method → `repo.add(fulfillment)` → return ID if creation.

## Cross-Domain Integration

### Inbound: Ordering → Fulfillment
**File:** `fulfillment/order_subscriber.py`

`@fulfillment.subscriber(broker="global", stream="ordering::order")` — receives raw dict payloads (ACL pattern).

Subscriber `OrderEventsSubscriber`:
- `OrderCancelled` → queries for fulfillment matching order_id, cancels if still in cancellable status, logs warning if already shipped

### Inbound: Payments → Fulfillment
**File:** `fulfillment/payment_subscriber.py`

`@fulfillment.subscriber(broker="global", stream="payments::payment")` — receives raw dict payloads (ACL pattern).

Subscriber `PaymentEventsSubscriber`:
- `PaymentSucceeded` → logs (fulfillment creation requires order item details from API/saga)

### Outbound: Fulfillment → Ordering, Inventory
Events marked `published=True` (`ShipmentHandedOff`, `DeliveryConfirmed`, `FulfillmentCancelled`) are dual-written to the external bus for consumption by Ordering and Inventory subscribers.

## Carrier Abstraction

**Directory:** `carrier/`

| File | Contents |
|------|----------|
| `carrier/port.py` | `CarrierPort` ABC — `create_shipment()`, `get_tracking()`, `cancel_shipment()`, `verify_webhook_signature()` |
| `carrier/fake_adapter.py` | `FakeCarrier` — configurable success/failure, deterministic tracking numbers, estimated delivery by service level |
| `carrier/__init__.py` | `get_carrier()` / `reset_carrier()` — singleton factory |

## Projections

**Directory:** `projections/`

| File | Projection | Projector | Purpose |
|------|-----------|-----------|---------|
| `fulfillment_status.py` | `FulfillmentStatusView` | `FulfillmentStatusProjector` | Status tracking with carrier/tracking info (handles all 10 status events) |
| `shipment_tracking.py` | `ShipmentTrackingView` | `ShipmentTrackingProjector` | Tracking event timeline with current status/location |
| `warehouse_queue.py` | `WarehouseQueueView` | `WarehouseQueueProjector` | Warehouse work queue (picking → packing → shipped) |
| `daily_shipments.py` | `DailyShipmentsView` | `DailyShipmentsProjector` | Daily shipment/delivery/exception counts (keyed by YYYY-MM-DD) |
| `delivery_performance.py` | `DeliveryPerformanceView` | `DeliveryPerformanceProjector` | Per-carrier per-day performance metrics |

## API

**Package:** `api/`

| File | Contents |
|------|----------|
| `api/__init__.py` | Re-exports `fulfillment_router` |
| `api/schemas.py` | Pydantic request/response models (external contract) |
| `api/routes.py` | 12 endpoints on `APIRouter(prefix="/fulfillments", tags=["fulfillments"])` |

### Endpoints
| Method | Path | Request Body | Response |
|--------|------|-------------|----------|
| POST | `/fulfillments` | `CreateFulfillmentRequest` | `FulfillmentIdResponse` (201) |
| PUT | `/fulfillments/{id}/assign-picker` | `AssignPickerRequest` | `StatusResponse` |
| PUT | `/fulfillments/{id}/items/{item_id}/pick` | `RecordItemPickedRequest` | `StatusResponse` |
| PUT | `/fulfillments/{id}/pick-list/complete` | — | `StatusResponse` |
| PUT | `/fulfillments/{id}/pack` | `RecordPackingRequest` | `StatusResponse` |
| PUT | `/fulfillments/{id}/label` | `GenerateShippingLabelRequest` | `StatusResponse` |
| PUT | `/fulfillments/{id}/handoff` | `RecordHandoffRequest` | `StatusResponse` |
| POST | `/fulfillments/tracking/webhook` | `UpdateTrackingRequest` + `X-Carrier-Signature` header | `StatusResponse` |
| PUT | `/fulfillments/{id}/deliver` | — | `StatusResponse` |
| PUT | `/fulfillments/{id}/exception` | `RecordExceptionRequest` | `StatusResponse` |
| PUT | `/fulfillments/{id}/cancel` | `CancelFulfillmentRequest` | `StatusResponse` |
| POST | `/fulfillments/carrier/configure` | `ConfigureCarrierRequest` | `CarrierConfigResponse` (non-production only) |
