"""Pydantic request/response schemas for the Inventory API.

These are external contracts (anti-corruption layer) — separate from
internal Protean commands.
"""

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared sub-models
# ---------------------------------------------------------------------------
class AddressSchema(BaseModel):
    street: str
    city: str
    state: str | None = None
    postal_code: str
    country: str


# ---------------------------------------------------------------------------
# Stock Request Schemas
# ---------------------------------------------------------------------------
class InitializeStockRequest(BaseModel):
    product_id: str
    variant_id: str
    warehouse_id: str
    sku: str
    initial_quantity: int = Field(ge=0, default=0)
    reorder_point: int = Field(ge=0, default=10)
    reorder_quantity: int = Field(ge=0, default=50)


class ReceiveStockRequest(BaseModel):
    quantity: int = Field(ge=1)
    reference: str | None = None


class ReserveStockRequest(BaseModel):
    order_id: str
    quantity: int = Field(ge=1)
    expires_in_minutes: int | None = Field(default=15, ge=1)


class ReleaseReservationRequest(BaseModel):
    reason: str


class AdjustStockRequest(BaseModel):
    quantity_change: int
    adjustment_type: str
    reason: str
    adjusted_by: str


class MarkDamagedRequest(BaseModel):
    quantity: int = Field(ge=1)
    reason: str


class WriteOffDamagedRequest(BaseModel):
    quantity: int = Field(ge=1)
    approved_by: str


class ReturnToStockRequest(BaseModel):
    quantity: int = Field(ge=1)
    order_id: str


class RecordStockCheckRequest(BaseModel):
    counted_quantity: int = Field(ge=0)
    checked_by: str


# ---------------------------------------------------------------------------
# Warehouse Request Schemas
# ---------------------------------------------------------------------------
class CreateWarehouseRequest(BaseModel):
    name: str
    address: AddressSchema
    capacity: int = Field(ge=0, default=0)


class UpdateWarehouseRequest(BaseModel):
    name: str | None = None
    capacity: int | None = None


class AddZoneRequest(BaseModel):
    zone_name: str
    zone_type: str = "Regular"


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------
class InventoryItemIdResponse(BaseModel):
    inventory_item_id: str


class WarehouseIdResponse(BaseModel):
    warehouse_id: str


class StatusResponse(BaseModel):
    status: str = "ok"
