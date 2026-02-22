"""Inbound cross-domain event handler — Inventory reacts to Ordering events.

Listens for OrderCancelled and OrderReturned events from the Ordering domain
to release reservations (on cancellation) or restock items (on return).

Cross-domain events are imported from shared.events.ordering and registered
as external events via inventory.register_external_event().
"""

import json

import structlog
from protean.utils.globals import current_domain
from protean.utils.mixins import handle
from shared.events.ordering import OrderCancelled, OrderReturned

from inventory.domain import inventory
from inventory.projections.reservation_status import ReservationStatus
from inventory.stock.stock import InventoryItem

logger = structlog.get_logger(__name__)

# Register external events so Protean can deserialize them
inventory.register_external_event(OrderCancelled, "Ordering.OrderCancelled.v1")
inventory.register_external_event(OrderReturned, "Ordering.OrderReturned.v1")


@inventory.event_handler(part_of=InventoryItem, stream_category="ordering::order")
class OrderingInventoryEventHandler:
    """Reacts to Ordering domain events to manage stock reservations and returns."""

    @handle(OrderCancelled)
    def on_order_cancelled(self, event: OrderCancelled) -> None:
        """Release active/confirmed reservations when an order is cancelled."""
        logger.info(
            "Releasing reservations for cancelled order",
            order_id=str(event.order_id),
            reason=event.reason,
        )

        # Find active or confirmed reservations for this order
        reservations = (
            current_domain.repository_for(ReservationStatus)._dao.query.filter(order_id=str(event.order_id)).all().items
        )

        releasable = [r for r in reservations if r.status in ("Active", "Confirmed")]

        if not releasable:
            logger.info(
                "No releasable reservations for cancelled order",
                order_id=str(event.order_id),
            )
            return

        from inventory.stock.reservation import ReleaseReservation

        for reservation in releasable:
            current_domain.process(
                ReleaseReservation(
                    inventory_item_id=str(reservation.inventory_item_id),
                    reservation_id=str(reservation.reservation_id),
                    reason=f"order_cancelled: {event.reason}",
                ),
                asynchronous=False,
            )
            logger.info(
                "Released reservation for cancelled order",
                reservation_id=str(reservation.reservation_id),
                inventory_item_id=str(reservation.inventory_item_id),
                order_id=str(event.order_id),
            )

    @handle(OrderReturned)
    def on_order_returned(self, event: OrderReturned) -> None:
        """Return items to stock when an order is returned."""
        logger.info(
            "Restocking items for returned order",
            order_id=str(event.order_id),
        )

        # Parse items to get product/variant info for stock lookup
        items = []
        if event.items:
            items = json.loads(event.items) if isinstance(event.items, str) else event.items

        if not items:
            logger.info(
                "No item details in return event — cannot restock",
                order_id=str(event.order_id),
            )
            return

        from inventory.projections.inventory_level import InventoryLevel
        from inventory.stock.returns import ReturnToStock

        for item in items:
            product_id = item.get("product_id")
            variant_id = item.get("variant_id")
            quantity = item.get("quantity", 1)

            # Find the inventory item for this variant
            inv_records = (
                current_domain.repository_for(InventoryLevel)
                ._dao.query.filter(
                    product_id=str(product_id),
                    variant_id=str(variant_id),
                )
                .all()
                .items
            )

            if not inv_records:
                logger.warning(
                    "No inventory record found for returned item",
                    product_id=str(product_id),
                    variant_id=str(variant_id),
                )
                continue

            inv_record = inv_records[0]
            current_domain.process(
                ReturnToStock(
                    inventory_item_id=str(inv_record.inventory_item_id),
                    quantity=quantity,
                    order_id=event.order_id,
                ),
                asynchronous=False,
            )
            logger.info(
                "Restocked returned item",
                inventory_item_id=str(inv_record.inventory_item_id),
                quantity=quantity,
                order_id=str(event.order_id),
            )
