"""FastAPI routes for the Fulfillment domain."""

import json
import os
from datetime import datetime

from fastapi import APIRouter, Header, HTTPException
from protean.utils.globals import current_domain

from fulfillment.api.schemas import (
    AssignPickerRequest,
    CancelFulfillmentRequest,
    CarrierConfigResponse,
    ConfigureCarrierRequest,
    CreateFulfillmentRequest,
    FulfillmentIdResponse,
    GenerateShippingLabelRequest,
    RecordExceptionRequest,
    RecordHandoffRequest,
    RecordItemPickedRequest,
    RecordPackingRequest,
    StatusResponse,
    UpdateTrackingRequest,
)
from fulfillment.carrier import get_carrier
from fulfillment.carrier.fake_adapter import FakeCarrier
from fulfillment.fulfillment.cancellation import CancelFulfillment
from fulfillment.fulfillment.creation import CreateFulfillment
from fulfillment.fulfillment.delivery import RecordDeliveryConfirmation, RecordDeliveryException
from fulfillment.fulfillment.packing import GenerateShippingLabel, RecordPacking
from fulfillment.fulfillment.picking import AssignPicker, CompletePickList, RecordItemPicked
from fulfillment.fulfillment.shipping import RecordHandoff
from fulfillment.fulfillment.tracking import UpdateTrackingEvent

# ---------------------------------------------------------------------------
# Fulfillment Router
# ---------------------------------------------------------------------------
fulfillment_router = APIRouter(prefix="/fulfillments", tags=["fulfillments"])


@fulfillment_router.post("", status_code=201, response_model=FulfillmentIdResponse)
async def create_fulfillment(body: CreateFulfillmentRequest) -> FulfillmentIdResponse:
    """Create a new fulfillment for a paid order."""
    items_json = json.dumps([item.model_dump() for item in body.items])
    command = CreateFulfillment(
        order_id=body.order_id,
        customer_id=body.customer_id,
        warehouse_id=body.warehouse_id,
        items=items_json,
    )
    result = current_domain.process(command, asynchronous=False)
    return FulfillmentIdResponse(fulfillment_id=result)


@fulfillment_router.put("/{fulfillment_id}/assign-picker", response_model=StatusResponse)
async def assign_picker(fulfillment_id: str, body: AssignPickerRequest) -> StatusResponse:
    """Assign a warehouse picker to begin the picking process."""
    command = AssignPicker(
        fulfillment_id=fulfillment_id,
        picker_name=body.picker_name,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse(status="picker_assigned")


@fulfillment_router.put("/{fulfillment_id}/items/{item_id}/pick", response_model=StatusResponse)
async def record_item_picked(fulfillment_id: str, item_id: str, body: RecordItemPickedRequest) -> StatusResponse:
    """Record that a single item has been picked."""
    command = RecordItemPicked(
        fulfillment_id=fulfillment_id,
        item_id=item_id,
        pick_location=body.pick_location,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse(status="item_picked")


@fulfillment_router.put("/{fulfillment_id}/pick-list/complete", response_model=StatusResponse)
async def complete_pick_list(fulfillment_id: str) -> StatusResponse:
    """Complete the pick list — all items must have been picked."""
    command = CompletePickList(fulfillment_id=fulfillment_id)
    current_domain.process(command, asynchronous=False)
    return StatusResponse(status="picking_completed")


@fulfillment_router.put("/{fulfillment_id}/pack", response_model=StatusResponse)
async def record_packing(fulfillment_id: str, body: RecordPackingRequest) -> StatusResponse:
    """Record that items have been packed into shipping packages."""
    command = RecordPacking(
        fulfillment_id=fulfillment_id,
        packed_by=body.packed_by,
        packages=json.dumps(body.packages),
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse(status="packing_completed")


@fulfillment_router.put("/{fulfillment_id}/label", response_model=StatusResponse)
async def generate_shipping_label(fulfillment_id: str, body: GenerateShippingLabelRequest) -> StatusResponse:
    """Generate a shipping label for the fulfillment."""
    command = GenerateShippingLabel(
        fulfillment_id=fulfillment_id,
        label_url=body.label_url,
        carrier=body.carrier,
        service_level=body.service_level,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse(status="label_generated")


@fulfillment_router.put("/{fulfillment_id}/handoff", response_model=StatusResponse)
async def record_handoff(fulfillment_id: str, body: RecordHandoffRequest) -> StatusResponse:
    """Record carrier handoff — the shipment has left the warehouse."""
    estimated_delivery = None
    if body.estimated_delivery:
        estimated_delivery = datetime.fromisoformat(body.estimated_delivery)

    command = RecordHandoff(
        fulfillment_id=fulfillment_id,
        tracking_number=body.tracking_number,
        estimated_delivery=estimated_delivery,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse(status="shipment_handed_off")


@fulfillment_router.post("/tracking/webhook", response_model=StatusResponse)
async def tracking_webhook(
    body: UpdateTrackingRequest,
    x_carrier_signature: str = Header(default=""),
) -> StatusResponse:
    """Process a carrier tracking webhook callback."""
    carrier = get_carrier()
    if not carrier.verify_webhook_signature(json.dumps(body.model_dump()), x_carrier_signature):
        raise HTTPException(status_code=401, detail="Invalid carrier webhook signature")

    command = UpdateTrackingEvent(
        fulfillment_id=body.fulfillment_id,
        status=body.status,
        location=body.location,
        description=body.description,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse(status="tracking_updated")


@fulfillment_router.put("/{fulfillment_id}/deliver", response_model=StatusResponse)
async def record_delivery(fulfillment_id: str) -> StatusResponse:
    """Record confirmed delivery from the carrier."""
    command = RecordDeliveryConfirmation(fulfillment_id=fulfillment_id)
    current_domain.process(command, asynchronous=False)
    return StatusResponse(status="delivery_confirmed")


@fulfillment_router.put("/{fulfillment_id}/exception", response_model=StatusResponse)
async def record_exception(fulfillment_id: str, body: RecordExceptionRequest) -> StatusResponse:
    """Record a delivery exception from the carrier."""
    command = RecordDeliveryException(
        fulfillment_id=fulfillment_id,
        reason=body.reason,
        location=body.location,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse(status="exception_recorded")


@fulfillment_router.put("/{fulfillment_id}/cancel", response_model=StatusResponse)
async def cancel_fulfillment(fulfillment_id: str, body: CancelFulfillmentRequest) -> StatusResponse:
    """Cancel a fulfillment before it has been shipped."""
    command = CancelFulfillment(
        fulfillment_id=fulfillment_id,
        reason=body.reason,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse(status="cancelled")


@fulfillment_router.post("/carrier/configure", response_model=CarrierConfigResponse)
async def configure_carrier(body: ConfigureCarrierRequest) -> CarrierConfigResponse:
    """Configure the FakeCarrier behavior (non-production only)."""
    if os.environ.get("PROTEAN_ENV") == "production":
        raise HTTPException(status_code=403, detail="Carrier configuration not available in production")

    carrier = get_carrier()
    if not isinstance(carrier, FakeCarrier):
        raise HTTPException(status_code=400, detail="Carrier configuration only available for FakeCarrier")

    carrier.configure(
        should_succeed=body.should_succeed,
        failure_reason=body.failure_reason,
    )
    return CarrierConfigResponse(
        carrier=type(carrier).__name__,
        should_succeed=carrier.should_succeed,
        failure_reason=carrier.failure_reason,
    )
