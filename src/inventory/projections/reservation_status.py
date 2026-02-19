"""Reservation status — active reservations view for order status checks."""

from protean.core.projector import on
from protean.fields import DateTime, Identifier, Integer, String
from protean.utils.globals import current_domain

from inventory.domain import inventory
from inventory.stock.events import (
    ReservationConfirmed,
    ReservationReleased,
    StockCommitted,
    StockReserved,
)
from inventory.stock.stock import InventoryItem


@inventory.projection
class ReservationStatus:
    reservation_id = Identifier(identifier=True, required=True)
    inventory_item_id = Identifier(required=True)
    order_id = Identifier(required=True)
    quantity = Integer(required=True)
    status = String(required=True)
    reserved_at = DateTime()
    expires_at = DateTime()
    updated_at = DateTime()


@inventory.projector(projector_for=ReservationStatus, aggregates=[InventoryItem])
class ReservationStatusProjector:
    @on(StockReserved)
    def on_stock_reserved(self, event):
        current_domain.repository_for(ReservationStatus).add(
            ReservationStatus(
                reservation_id=event.reservation_id,
                inventory_item_id=event.inventory_item_id,
                order_id=event.order_id,
                quantity=event.quantity,
                status="Active",
                reserved_at=event.reserved_at,
                expires_at=event.expires_at,
                updated_at=event.reserved_at,
            )
        )

    @on(ReservationReleased)
    def on_reservation_released(self, event):
        repo = current_domain.repository_for(ReservationStatus)
        reservation = repo.get(event.reservation_id)
        reservation.status = "Released"
        reservation.updated_at = event.released_at
        repo.add(reservation)

    @on(ReservationConfirmed)
    def on_reservation_confirmed(self, event):
        repo = current_domain.repository_for(ReservationStatus)
        reservation = repo.get(event.reservation_id)
        reservation.status = "Confirmed"
        reservation.updated_at = event.confirmed_at
        repo.add(reservation)

    @on(StockCommitted)
    def on_stock_committed(self, event):
        repo = current_domain.repository_for(ReservationStatus)
        reservation = repo.get(event.reservation_id)
        reservation.status = "Committed"
        reservation.updated_at = event.committed_at
        repo.add(reservation)
