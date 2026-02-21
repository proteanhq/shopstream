"""Fulfillment aggregate (CQRS) — the core of the fulfillment domain.

The Fulfillment aggregate manages the warehouse-to-delivery pipeline for a
single order. It uses CQRS (not event sourcing) because workflows are largely
linear and external carriers own tracking state.

State Machine:
    PENDING → PICKING → PACKING → READY_TO_SHIP → SHIPPED → IN_TRANSIT → DELIVERED
    IN_TRANSIT → EXCEPTION → {IN_TRANSIT, DELIVERED}
    {PENDING, PICKING, PACKING, READY_TO_SHIP} → CANCELLED
"""

import json
from datetime import UTC, datetime
from enum import Enum

from protean.exceptions import ValidationError
from protean.fields import (
    DateTime,
    Float,
    HasMany,
    Identifier,
    Integer,
    String,
    Text,
    ValueObject,
)

from fulfillment.domain import fulfillment
from fulfillment.fulfillment.events import (
    DeliveryConfirmed,
    DeliveryException,
    FulfillmentCancelled,
    FulfillmentCreated,
    ItemPicked,
    PackingCompleted,
    PickerAssigned,
    PickingCompleted,
    ShipmentHandedOff,
    ShippingLabelGenerated,
    TrackingEventReceived,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class FulfillmentStatus(Enum):
    PENDING = "Pending"
    PICKING = "Picking"
    PACKING = "Packing"
    READY_TO_SHIP = "Ready_To_Ship"
    SHIPPED = "Shipped"
    IN_TRANSIT = "In_Transit"
    DELIVERED = "Delivered"
    EXCEPTION = "Exception"
    CANCELLED = "Cancelled"


class FulfillmentItemStatus(Enum):
    PENDING = "Pending"
    PICKED = "Picked"
    PACKED = "Packed"


class ServiceLevel(Enum):
    STANDARD = "Standard"
    EXPRESS = "Express"
    OVERNIGHT = "Overnight"


_VALID_TRANSITIONS = {
    FulfillmentStatus.PENDING: {FulfillmentStatus.PICKING, FulfillmentStatus.CANCELLED},
    FulfillmentStatus.PICKING: {FulfillmentStatus.PACKING, FulfillmentStatus.CANCELLED},
    FulfillmentStatus.PACKING: {FulfillmentStatus.READY_TO_SHIP, FulfillmentStatus.CANCELLED},
    FulfillmentStatus.READY_TO_SHIP: {FulfillmentStatus.SHIPPED, FulfillmentStatus.CANCELLED},
    FulfillmentStatus.SHIPPED: {FulfillmentStatus.IN_TRANSIT},
    FulfillmentStatus.IN_TRANSIT: {FulfillmentStatus.DELIVERED, FulfillmentStatus.EXCEPTION},
    FulfillmentStatus.EXCEPTION: {FulfillmentStatus.IN_TRANSIT, FulfillmentStatus.DELIVERED},
    FulfillmentStatus.DELIVERED: set(),  # terminal
    FulfillmentStatus.CANCELLED: set(),  # terminal
}

_CANCELLABLE_STATUSES = {
    FulfillmentStatus.PENDING,
    FulfillmentStatus.PICKING,
    FulfillmentStatus.PACKING,
    FulfillmentStatus.READY_TO_SHIP,
}


# ---------------------------------------------------------------------------
# Value Objects
# ---------------------------------------------------------------------------
@fulfillment.value_object(part_of="Fulfillment")
class PickList:
    """Picking assignment details."""

    assigned_to = String(max_length=100)
    assigned_at = DateTime()
    completed_at = DateTime()


@fulfillment.value_object(part_of="Fulfillment")
class PackingInfo:
    """Packing completion details."""

    packed_by = String(max_length=100)
    packed_at = DateTime()
    shipping_label_url = String(max_length=500)


@fulfillment.value_object(part_of="Fulfillment")
class ShipmentInfo:
    """Carrier shipment details."""

    carrier = String(max_length=100)
    service_level = String(max_length=50, choices=ServiceLevel)
    tracking_number = String(max_length=255)
    estimated_delivery = DateTime()
    actual_delivery = DateTime()


@fulfillment.value_object(part_of="Fulfillment")
class PackageDimensions:
    """Physical dimensions and weight of a package."""

    weight = Float()
    length = Float()
    width = Float()
    height = Float()


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------
@fulfillment.entity(part_of="Fulfillment")
class FulfillmentItem:
    """A single line item being fulfilled."""

    order_item_id = Identifier(required=True)
    product_id = Identifier(required=True)
    sku = String(required=True, max_length=100)
    quantity = Integer(required=True, min_value=1)
    pick_location = String(max_length=100)
    status = String(
        max_length=50,
        choices=FulfillmentItemStatus,
        default=FulfillmentItemStatus.PENDING.value,
    )


@fulfillment.entity(part_of="Fulfillment")
class Package:
    """A physical package in the shipment."""

    weight = Float()
    dimensions = ValueObject(PackageDimensions)
    item_ids = Text()  # JSON list of FulfillmentItem IDs


@fulfillment.entity(part_of="Fulfillment")
class TrackingEvent:
    """A carrier tracking event."""

    status = String(required=True, max_length=100)
    location = String(max_length=200)
    description = String(max_length=500)
    occurred_at = DateTime(required=True)


# ---------------------------------------------------------------------------
# Aggregate Root (CQRS)
# ---------------------------------------------------------------------------
@fulfillment.aggregate
class Fulfillment:
    order_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    warehouse_id = Identifier()
    status = String(
        choices=FulfillmentStatus,
        default=FulfillmentStatus.PENDING.value,
    )
    items = HasMany(FulfillmentItem)
    pick_list = ValueObject(PickList)
    packing_info = ValueObject(PackingInfo)
    packages = HasMany(Package)
    shipment = ValueObject(ShipmentInfo)
    tracking_events = HasMany(TrackingEvent)
    cancellation_reason = String(max_length=500)
    created_at = DateTime()
    updated_at = DateTime()

    # -------------------------------------------------------------------
    # Factory method
    # -------------------------------------------------------------------
    @classmethod
    def create(
        cls,
        order_id: str,
        customer_id: str,
        items_data: list[dict],
        warehouse_id: str | None = None,
    ):
        """Create a new fulfillment for a paid order."""
        now = datetime.now(UTC)
        ff = cls(
            order_id=order_id,
            customer_id=customer_id,
            warehouse_id=warehouse_id,
            status=FulfillmentStatus.PENDING.value,
            created_at=now,
            updated_at=now,
        )
        for item_data in items_data:
            ff.add_items(FulfillmentItem(**item_data))
        ff.raise_(
            FulfillmentCreated(
                fulfillment_id=str(ff.id),
                order_id=order_id,
                customer_id=customer_id,
                warehouse_id=warehouse_id or "",
                items=json.dumps(items_data),
                item_count=len(items_data),
                created_at=now,
            )
        )
        return ff

    # -------------------------------------------------------------------
    # State transition helper
    # -------------------------------------------------------------------
    def _assert_can_transition(self, target_status: FulfillmentStatus) -> None:
        current = FulfillmentStatus(self.status)
        if target_status not in _VALID_TRANSITIONS.get(current, set()):
            raise ValidationError({"status": [f"Cannot transition from {current.value} to {target_status.value}"]})

    # -------------------------------------------------------------------
    # Picking
    # -------------------------------------------------------------------
    def assign_picker(self, picker_name: str) -> None:
        """Assign a warehouse picker and begin the picking process."""
        self._assert_can_transition(FulfillmentStatus.PICKING)
        now = datetime.now(UTC)
        self.status = FulfillmentStatus.PICKING.value
        self.pick_list = PickList(assigned_to=picker_name, assigned_at=now)
        self.updated_at = now
        self.raise_(
            PickerAssigned(
                fulfillment_id=str(self.id),
                assigned_to=picker_name,
                assigned_at=now,
            )
        )

    def record_item_picked(self, item_id: str, pick_location: str) -> None:
        """Record that a single item has been picked from its location."""
        if FulfillmentStatus(self.status) != FulfillmentStatus.PICKING:
            raise ValidationError({"status": ["Items can only be picked during PICKING phase"]})

        item = next((i for i in (self.items or []) if str(i.id) == item_id), None)
        if item is None:
            raise ValidationError({"item_id": ["Item not found in this fulfillment"]})
        if item.status != FulfillmentItemStatus.PENDING.value:
            raise ValidationError({"item_id": ["Item has already been picked"]})

        now = datetime.now(UTC)
        item.status = FulfillmentItemStatus.PICKED.value
        item.pick_location = pick_location
        self.updated_at = now
        self.raise_(
            ItemPicked(
                fulfillment_id=str(self.id),
                item_id=item_id,
                pick_location=pick_location,
                picked_at=now,
            )
        )

    def complete_pick_list(self) -> None:
        """Complete the pick list — all items must be picked."""
        if FulfillmentStatus(self.status) != FulfillmentStatus.PICKING:
            raise ValidationError({"status": ["Pick list can only be completed during PICKING phase"]})

        unpicked = [i for i in (self.items or []) if i.status != FulfillmentItemStatus.PICKED.value]
        if unpicked:
            raise ValidationError({"items": [f"{len(unpicked)} item(s) have not been picked yet"]})

        now = datetime.now(UTC)
        self.status = FulfillmentStatus.PACKING.value
        self.pick_list = PickList(
            assigned_to=self.pick_list.assigned_to if self.pick_list else "",
            assigned_at=self.pick_list.assigned_at if self.pick_list else None,
            completed_at=now,
        )
        self.updated_at = now
        self.raise_(
            PickingCompleted(
                fulfillment_id=str(self.id),
                completed_at=now,
            )
        )

    # -------------------------------------------------------------------
    # Packing
    # -------------------------------------------------------------------
    def record_packing(self, packed_by: str, packages_data: list[dict]) -> None:
        """Record that items have been packed into packages."""
        if FulfillmentStatus(self.status) != FulfillmentStatus.PACKING:
            raise ValidationError({"status": ["Packing can only be recorded during PACKING phase"]})

        now = datetime.now(UTC)
        for pkg_data in packages_data:
            self.add_packages(Package(**pkg_data))

        # Mark all items as packed
        for item in self.items or []:
            item.status = FulfillmentItemStatus.PACKED.value

        self.packing_info = PackingInfo(packed_by=packed_by, packed_at=now)
        self.updated_at = now
        self.raise_(
            PackingCompleted(
                fulfillment_id=str(self.id),
                packed_by=packed_by,
                package_count=len(packages_data),
                packed_at=now,
            )
        )

    def generate_shipping_label(self, label_url: str, carrier: str, service_level: str) -> None:
        """Record that a shipping label has been generated."""
        if FulfillmentStatus(self.status) != FulfillmentStatus.PACKING:
            raise ValidationError({"status": ["Shipping label can only be generated during PACKING phase"]})
        if not self.packing_info or not self.packing_info.packed_at:
            raise ValidationError({"packing_info": ["Items must be packed before generating a shipping label"]})

        now = datetime.now(UTC)
        self.status = FulfillmentStatus.READY_TO_SHIP.value
        self.packing_info = PackingInfo(
            packed_by=self.packing_info.packed_by,
            packed_at=self.packing_info.packed_at,
            shipping_label_url=label_url,
        )
        self.shipment = ShipmentInfo(carrier=carrier, service_level=service_level)
        self.updated_at = now
        self.raise_(
            ShippingLabelGenerated(
                fulfillment_id=str(self.id),
                label_url=label_url,
                carrier=carrier,
                service_level=service_level,
                generated_at=now,
            )
        )

    # -------------------------------------------------------------------
    # Shipping
    # -------------------------------------------------------------------
    def record_handoff(self, tracking_number: str, estimated_delivery: datetime | None = None) -> None:
        """Record carrier handoff — the shipment has left the warehouse."""
        self._assert_can_transition(FulfillmentStatus.SHIPPED)
        now = datetime.now(UTC)
        self.status = FulfillmentStatus.SHIPPED.value
        self.shipment = ShipmentInfo(
            carrier=self.shipment.carrier if self.shipment else "",
            service_level=self.shipment.service_level if self.shipment else "",
            tracking_number=tracking_number,
            estimated_delivery=estimated_delivery,
        )
        self.updated_at = now

        # Collect shipped item IDs for cross-domain events
        shipped_item_ids = [str(i.order_item_id) for i in (self.items or [])]

        self.raise_(
            ShipmentHandedOff(
                fulfillment_id=str(self.id),
                order_id=str(self.order_id),
                carrier=self.shipment.carrier,
                tracking_number=tracking_number,
                shipped_item_ids=json.dumps(shipped_item_ids),
                estimated_delivery=estimated_delivery,
                shipped_at=now,
            )
        )

    # -------------------------------------------------------------------
    # Tracking
    # -------------------------------------------------------------------
    def add_tracking_event(self, status: str, location: str | None = None, description: str | None = None) -> None:
        """Record a tracking event from the carrier."""
        current = FulfillmentStatus(self.status)
        if current not in (
            FulfillmentStatus.SHIPPED,
            FulfillmentStatus.IN_TRANSIT,
            FulfillmentStatus.EXCEPTION,
        ):
            raise ValidationError({"status": ["Tracking events can only be added after shipment"]})

        now = datetime.now(UTC)

        # Auto-transition to IN_TRANSIT on first tracking event after SHIPPED
        if current == FulfillmentStatus.SHIPPED:
            self.status = FulfillmentStatus.IN_TRANSIT.value

        # Re-enter IN_TRANSIT from EXCEPTION if carrier reports movement
        if current == FulfillmentStatus.EXCEPTION:
            self.status = FulfillmentStatus.IN_TRANSIT.value

        self.add_tracking_events(
            TrackingEvent(
                status=status,
                location=location or "",
                description=description or "",
                occurred_at=now,
            )
        )
        self.updated_at = now
        self.raise_(
            TrackingEventReceived(
                fulfillment_id=str(self.id),
                status=status,
                location=location or "",
                description=description or "",
                occurred_at=now,
            )
        )

    # -------------------------------------------------------------------
    # Delivery
    # -------------------------------------------------------------------
    def record_delivery(self) -> None:
        """Record confirmed delivery from the carrier."""
        self._assert_can_transition(FulfillmentStatus.DELIVERED)
        now = datetime.now(UTC)
        self.status = FulfillmentStatus.DELIVERED.value
        if self.shipment:
            self.shipment = ShipmentInfo(
                carrier=self.shipment.carrier,
                service_level=self.shipment.service_level,
                tracking_number=self.shipment.tracking_number,
                estimated_delivery=self.shipment.estimated_delivery,
                actual_delivery=now,
            )
        self.updated_at = now
        self.raise_(
            DeliveryConfirmed(
                fulfillment_id=str(self.id),
                order_id=str(self.order_id),
                actual_delivery=now,
                delivered_at=now,
            )
        )

    def record_exception(self, reason: str, location: str | None = None) -> None:
        """Record a delivery exception from the carrier."""
        self._assert_can_transition(FulfillmentStatus.EXCEPTION)
        now = datetime.now(UTC)
        self.status = FulfillmentStatus.EXCEPTION.value
        self.add_tracking_events(
            TrackingEvent(
                status="EXCEPTION",
                location=location or "",
                description=reason,
                occurred_at=now,
            )
        )
        self.updated_at = now
        self.raise_(
            DeliveryException(
                fulfillment_id=str(self.id),
                order_id=str(self.order_id),
                reason=reason,
                location=location or "",
                occurred_at=now,
            )
        )

    # -------------------------------------------------------------------
    # Cancellation
    # -------------------------------------------------------------------
    def cancel(self, reason: str) -> None:
        """Cancel the fulfillment (only before shipment)."""
        current = FulfillmentStatus(self.status)
        if current not in _CANCELLABLE_STATUSES:
            raise ValidationError({"status": [f"Cannot cancel fulfillment in {current.value} state"]})

        now = datetime.now(UTC)
        self.status = FulfillmentStatus.CANCELLED.value
        self.cancellation_reason = reason
        self.updated_at = now
        self.raise_(
            FulfillmentCancelled(
                fulfillment_id=str(self.id),
                order_id=str(self.order_id),
                reason=reason,
                cancelled_at=now,
            )
        )
