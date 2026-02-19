"""FastAPI routes for the Inventory domain — stock and warehouses."""

import json
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter
from protean.utils.globals import current_domain

from inventory.api.schemas import (
    AddZoneRequest,
    AdjustStockRequest,
    CreateWarehouseRequest,
    InitializeStockRequest,
    InventoryItemIdResponse,
    MarkDamagedRequest,
    ReceiveStockRequest,
    RecordStockCheckRequest,
    ReleaseReservationRequest,
    ReserveStockRequest,
    ReturnToStockRequest,
    StatusResponse,
    UpdateWarehouseRequest,
    WarehouseIdResponse,
    WriteOffDamagedRequest,
)
from inventory.stock.adjustment import AdjustStock, RecordStockCheck
from inventory.stock.damage import MarkDamaged, WriteOffDamaged
from inventory.stock.initialization import InitializeStock
from inventory.stock.receiving import ReceiveStock
from inventory.stock.reservation import ConfirmReservation, ReleaseReservation, ReserveStock
from inventory.stock.returns import ReturnToStock
from inventory.stock.shipping import CommitStock
from inventory.warehouse.management import (
    AddZone,
    CreateWarehouse,
    DeactivateWarehouse,
    RemoveZone,
    UpdateWarehouse,
)

# ---------------------------------------------------------------------------
# Inventory Router
# ---------------------------------------------------------------------------
inventory_router = APIRouter(prefix="/inventory", tags=["inventory"])


@inventory_router.post("", status_code=201, response_model=InventoryItemIdResponse)
async def initialize_stock(body: InitializeStockRequest) -> InventoryItemIdResponse:
    command = InitializeStock(
        product_id=body.product_id,
        variant_id=body.variant_id,
        warehouse_id=body.warehouse_id,
        sku=body.sku,
        initial_quantity=body.initial_quantity,
        reorder_point=body.reorder_point,
        reorder_quantity=body.reorder_quantity,
    )
    result = current_domain.process(command, asynchronous=False)
    return InventoryItemIdResponse(inventory_item_id=result)


@inventory_router.put("/{inventory_item_id}/receive", response_model=StatusResponse)
async def receive_stock(inventory_item_id: str, body: ReceiveStockRequest) -> StatusResponse:
    command = ReceiveStock(
        inventory_item_id=inventory_item_id,
        quantity=body.quantity,
        reference=body.reference,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@inventory_router.post("/{inventory_item_id}/reserve", status_code=201, response_model=StatusResponse)
async def reserve_stock(inventory_item_id: str, body: ReserveStockRequest) -> StatusResponse:
    expires_at = None
    if body.expires_in_minutes:
        expires_at = datetime.now(UTC) + timedelta(minutes=body.expires_in_minutes)
    command = ReserveStock(
        inventory_item_id=inventory_item_id,
        order_id=body.order_id,
        quantity=body.quantity,
        expires_at=expires_at,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@inventory_router.put(
    "/{inventory_item_id}/reservations/{reservation_id}/release",
    response_model=StatusResponse,
)
async def release_reservation(
    inventory_item_id: str, reservation_id: str, body: ReleaseReservationRequest
) -> StatusResponse:
    command = ReleaseReservation(
        inventory_item_id=inventory_item_id,
        reservation_id=reservation_id,
        reason=body.reason,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@inventory_router.put(
    "/{inventory_item_id}/reservations/{reservation_id}/confirm",
    response_model=StatusResponse,
)
async def confirm_reservation(inventory_item_id: str, reservation_id: str) -> StatusResponse:
    command = ConfirmReservation(
        inventory_item_id=inventory_item_id,
        reservation_id=reservation_id,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@inventory_router.put("/{inventory_item_id}/commit/{reservation_id}", response_model=StatusResponse)
async def commit_stock(inventory_item_id: str, reservation_id: str) -> StatusResponse:
    command = CommitStock(
        inventory_item_id=inventory_item_id,
        reservation_id=reservation_id,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@inventory_router.put("/{inventory_item_id}/adjust", response_model=StatusResponse)
async def adjust_stock(inventory_item_id: str, body: AdjustStockRequest) -> StatusResponse:
    command = AdjustStock(
        inventory_item_id=inventory_item_id,
        quantity_change=body.quantity_change,
        adjustment_type=body.adjustment_type,
        reason=body.reason,
        adjusted_by=body.adjusted_by,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@inventory_router.put("/{inventory_item_id}/damage", response_model=StatusResponse)
async def mark_damaged(inventory_item_id: str, body: MarkDamagedRequest) -> StatusResponse:
    command = MarkDamaged(
        inventory_item_id=inventory_item_id,
        quantity=body.quantity,
        reason=body.reason,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@inventory_router.put("/{inventory_item_id}/damage/write-off", response_model=StatusResponse)
async def write_off_damaged(inventory_item_id: str, body: WriteOffDamagedRequest) -> StatusResponse:
    command = WriteOffDamaged(
        inventory_item_id=inventory_item_id,
        quantity=body.quantity,
        approved_by=body.approved_by,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@inventory_router.put("/{inventory_item_id}/return", response_model=StatusResponse)
async def return_to_stock(inventory_item_id: str, body: ReturnToStockRequest) -> StatusResponse:
    command = ReturnToStock(
        inventory_item_id=inventory_item_id,
        quantity=body.quantity,
        order_id=body.order_id,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@inventory_router.put("/{inventory_item_id}/stock-check", response_model=StatusResponse)
async def record_stock_check(inventory_item_id: str, body: RecordStockCheckRequest) -> StatusResponse:
    command = RecordStockCheck(
        inventory_item_id=inventory_item_id,
        counted_quantity=body.counted_quantity,
        checked_by=body.checked_by,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


# ---------------------------------------------------------------------------
# Warehouse Router
# ---------------------------------------------------------------------------
warehouse_router = APIRouter(prefix="/warehouses", tags=["warehouses"])


@warehouse_router.post("", status_code=201, response_model=WarehouseIdResponse)
async def create_warehouse(body: CreateWarehouseRequest) -> WarehouseIdResponse:
    command = CreateWarehouse(
        name=body.name,
        address=json.dumps(body.address.model_dump()),
        capacity=body.capacity,
    )
    result = current_domain.process(command, asynchronous=False)
    return WarehouseIdResponse(warehouse_id=result)


@warehouse_router.put("/{warehouse_id}", response_model=StatusResponse)
async def update_warehouse(warehouse_id: str, body: UpdateWarehouseRequest) -> StatusResponse:
    command = UpdateWarehouse(
        warehouse_id=warehouse_id,
        name=body.name,
        capacity=body.capacity,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@warehouse_router.post("/{warehouse_id}/zones", status_code=201, response_model=StatusResponse)
async def add_zone(warehouse_id: str, body: AddZoneRequest) -> StatusResponse:
    command = AddZone(
        warehouse_id=warehouse_id,
        zone_name=body.zone_name,
        zone_type=body.zone_type,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@warehouse_router.delete("/{warehouse_id}/zones/{zone_id}", response_model=StatusResponse)
async def remove_zone(warehouse_id: str, zone_id: str) -> StatusResponse:
    command = RemoveZone(
        warehouse_id=warehouse_id,
        zone_id=zone_id,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@warehouse_router.put("/{warehouse_id}/deactivate", response_model=StatusResponse)
async def deactivate_warehouse(warehouse_id: str) -> StatusResponse:
    command = DeactivateWarehouse(warehouse_id=warehouse_id)
    current_domain.process(command, asynchronous=False)
    return StatusResponse()
