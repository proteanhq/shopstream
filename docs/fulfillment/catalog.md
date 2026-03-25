# Event & Command Catalog

## Fulfillment (`fulfillment.fulfillment.fulfillment.Fulfillment`)

### Events

#### DeliveryConfirmed

- **Type**: `Fulfillment.DeliveryConfirmed.v1`
- **Version**: 1
- **Published**: Yes
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| actual_delivery | DateTime | Yes | — |
| delivered_at | DateTime | Yes | — |
| fulfillment_id | Identifier | Yes | min_length=1 |
| order_id | Identifier | Yes | min_length=1 |

#### DeliveryException

- **Type**: `Fulfillment.DeliveryException.v1`
- **Version**: 1
- **Published**: Yes
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| fulfillment_id | Identifier | Yes | min_length=1 |
| location | String | No | max_length=255 |
| occurred_at | DateTime | Yes | — |
| order_id | Identifier | Yes | min_length=1 |
| reason | String | Yes | max_length=255, min_length=1 |

#### FulfillmentCancelled

- **Type**: `Fulfillment.FulfillmentCancelled.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| cancelled_at | DateTime | Yes | — |
| fulfillment_id | Identifier | Yes | min_length=1 |
| order_id | Identifier | Yes | min_length=1 |
| reason | String | Yes | max_length=255, min_length=1 |

#### FulfillmentCreated

- **Type**: `Fulfillment.FulfillmentCreated.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| created_at | DateTime | Yes | — |
| customer_id | Identifier | Yes | min_length=1 |
| fulfillment_id | Identifier | Yes | min_length=1 |
| item_count | Integer | Yes | — |
| items | List[dict] | Yes | — |
| order_id | Identifier | Yes | min_length=1 |
| warehouse_id | String | No | max_length=255 |

#### ItemPicked

- **Type**: `Fulfillment.ItemPicked.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| fulfillment_id | Identifier | Yes | min_length=1 |
| item_id | Identifier | Yes | min_length=1 |
| pick_location | String | Yes | max_length=255, min_length=1 |
| picked_at | DateTime | Yes | — |

#### PackingCompleted

- **Type**: `Fulfillment.PackingCompleted.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| fulfillment_id | Identifier | Yes | min_length=1 |
| package_count | Integer | Yes | — |
| packed_at | DateTime | Yes | — |
| packed_by | String | Yes | max_length=255, min_length=1 |

#### PickerAssigned

- **Type**: `Fulfillment.PickerAssigned.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| assigned_at | DateTime | Yes | — |
| assigned_to | String | Yes | max_length=255, min_length=1 |
| fulfillment_id | Identifier | Yes | min_length=1 |

#### PickingCompleted

- **Type**: `Fulfillment.PickingCompleted.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| completed_at | DateTime | Yes | — |
| fulfillment_id | Identifier | Yes | min_length=1 |

#### ShipmentHandedOff

- **Type**: `Fulfillment.ShipmentHandedOff.v1`
- **Version**: 1
- **Published**: Yes
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| carrier | String | Yes | max_length=255, min_length=1 |
| estimated_delivery | DateTime | No | — |
| fulfillment_id | Identifier | Yes | min_length=1 |
| order_id | Identifier | Yes | min_length=1 |
| shipped_at | DateTime | Yes | — |
| shipped_item_ids | List[String] | No | — |
| tracking_number | String | Yes | max_length=255, min_length=1 |

#### ShippingLabelGenerated

- **Type**: `Fulfillment.ShippingLabelGenerated.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| carrier | String | Yes | max_length=255, min_length=1 |
| fulfillment_id | Identifier | Yes | min_length=1 |
| generated_at | DateTime | Yes | — |
| label_url | String | Yes | max_length=255, min_length=1 |
| service_level | String | Yes | max_length=255, min_length=1 |

#### TrackingEventReceived

- **Type**: `Fulfillment.TrackingEventReceived.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| description | String | No | max_length=255 |
| fulfillment_id | Identifier | Yes | min_length=1 |
| location | String | No | max_length=255 |
| occurred_at | DateTime | Yes | — |
| status | String | Yes | max_length=255, min_length=1 |

### Commands

#### CancelFulfillment

- **Type**: `Fulfillment.CancelFulfillment.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| fulfillment_id | Identifier | Yes | min_length=1 |
| reason | String | Yes | max_length=500, min_length=1 |

#### CreateFulfillment

- **Type**: `Fulfillment.CreateFulfillment.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| customer_id | Identifier | Yes | min_length=1 |
| items | List[dict] | Yes | — |
| order_id | Identifier | Yes | min_length=1 |
| warehouse_id | Identifier | No | — |

#### RecordDeliveryConfirmation

- **Type**: `Fulfillment.RecordDeliveryConfirmation.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| fulfillment_id | Identifier | Yes | min_length=1 |

#### RecordDeliveryException

- **Type**: `Fulfillment.RecordDeliveryException.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| fulfillment_id | Identifier | Yes | min_length=1 |
| location | String | No | max_length=200 |
| reason | String | Yes | max_length=500, min_length=1 |

#### GenerateShippingLabel

- **Type**: `Fulfillment.GenerateShippingLabel.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| carrier | String | Yes | max_length=100, min_length=1 |
| fulfillment_id | Identifier | Yes | min_length=1 |
| label_url | String | Yes | max_length=500, min_length=1 |
| service_level | String | Yes | max_length=50, min_length=1 |

#### RecordPacking

- **Type**: `Fulfillment.RecordPacking.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| fulfillment_id | Identifier | Yes | min_length=1 |
| packages | List[dict] | Yes | — |
| packed_by | String | Yes | max_length=100, min_length=1 |

#### AssignPicker

- **Type**: `Fulfillment.AssignPicker.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| fulfillment_id | Identifier | Yes | min_length=1 |
| picker_name | String | Yes | max_length=100, min_length=1 |

#### CompletePickList

- **Type**: `Fulfillment.CompletePickList.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| fulfillment_id | Identifier | Yes | min_length=1 |

#### RecordItemPicked

- **Type**: `Fulfillment.RecordItemPicked.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| fulfillment_id | Identifier | Yes | min_length=1 |
| item_id | Identifier | Yes | min_length=1 |
| pick_location | String | Yes | max_length=100, min_length=1 |

#### RecordHandoff

- **Type**: `Fulfillment.RecordHandoff.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| estimated_delivery | DateTime | No | — |
| fulfillment_id | Identifier | Yes | min_length=1 |
| tracking_number | String | Yes | max_length=255, min_length=1 |

#### UpdateTrackingEvent

- **Type**: `Fulfillment.UpdateTrackingEvent.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| description | String | No | max_length=500 |
| fulfillment_id | Identifier | Yes | min_length=1 |
| location | String | No | max_length=200 |
| status | String | Yes | max_length=100, min_length=1 |

---

## Published Event Contracts

| Event | Type | Version |
|-------|------|---------|
| DeliveryConfirmed | `Fulfillment.DeliveryConfirmed.v1` | 1 |
| DeliveryException | `Fulfillment.DeliveryException.v1` | 1 |
| ShipmentHandedOff | `Fulfillment.ShipmentHandedOff.v1` | 1 |
