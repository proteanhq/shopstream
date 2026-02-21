"""Pydantic API schemas for the Fulfillment domain.

These are the external API contracts — separate from domain commands.
The API layer translates between these schemas and domain commands.
"""

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------
class FulfillmentItemRequest(BaseModel):
    order_item_id: str
    product_id: str
    sku: str
    quantity: int


class CreateFulfillmentRequest(BaseModel):
    order_id: str
    customer_id: str
    warehouse_id: str | None = None
    items: list[FulfillmentItemRequest]


class AssignPickerRequest(BaseModel):
    picker_name: str


class RecordItemPickedRequest(BaseModel):
    pick_location: str


class RecordPackingRequest(BaseModel):
    packed_by: str
    packages: list[dict]


class GenerateShippingLabelRequest(BaseModel):
    label_url: str
    carrier: str
    service_level: str


class RecordHandoffRequest(BaseModel):
    tracking_number: str
    estimated_delivery: str | None = None


class UpdateTrackingRequest(BaseModel):
    fulfillment_id: str
    status: str
    location: str | None = None
    description: str | None = None


class RecordExceptionRequest(BaseModel):
    reason: str
    location: str | None = None


class CancelFulfillmentRequest(BaseModel):
    reason: str


class ConfigureCarrierRequest(BaseModel):
    should_succeed: bool = True
    failure_reason: str = "Carrier unavailable"


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------
class FulfillmentIdResponse(BaseModel):
    fulfillment_id: str


class StatusResponse(BaseModel):
    status: str


class CarrierConfigResponse(BaseModel):
    carrier: str
    should_succeed: bool
    failure_reason: str
