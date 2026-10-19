"""Reservation status — active reservations view for order status checks."""

from datetime import datetime

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
    reservation_id: str = Identifier(identifier=True, required=True)
    inventory_item_id: str = Identifier(required=True)
    order_id: str = Identifier(required=True)
    quantity: int = Integer(required=True)
    status: str = String(required=True)
    reserved_at: datetime | None = DateTime()
    expires_at: datetime | None = DateTime()
    updated_at: datetime | None = DateTime()


@inventory.projector(projector_for=ReservationStatus, aggregates=[InventoryItem])
class ReservationStatusProjector:
    @on(StockReserved)
    def on_stock_reserved(self, event: StockReserved) -> None:
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
    def on_reservation_released(self, event: ReservationReleased) -> None:
        repo = current_domain.repository_for(ReservationStatus)
        reservation = repo.get(event.reservation_id)
        reservation.status = "Released"
        reservation.updated_at = event.released_at
        repo.add(reservation)

    @on(ReservationConfirmed)
    def on_reservation_confirmed(self, event: ReservationConfirmed) -> None:
        repo = current_domain.repository_for(ReservationStatus)
        reservation = repo.get(event.reservation_id)
        reservation.status = "Confirmed"
        reservation.updated_at = event.confirmed_at
        repo.add(reservation)

    @on(StockCommitted)
    def on_stock_committed(self, event: StockCommitted) -> None:
        repo = current_domain.repository_for(ReservationStatus)
        reservation = repo.get(event.reservation_id)
        reservation.status = "Committed"
        reservation.updated_at = event.committed_at
        repo.add(reservation)
