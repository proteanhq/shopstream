"""Tests for Reservation entity."""

from datetime import UTC, datetime, timedelta

import pytest
from inventory.stock.stock import Reservation, ReservationStatus
from protean.exceptions import ValidationError


class TestReservationConstruction:
    def test_construction(self):
        now = datetime.now(UTC)
        reservation = Reservation(
            order_id="ord-001",
            quantity=5,
            reserved_at=now,
            expires_at=now + timedelta(minutes=15),
        )
        assert str(reservation.order_id) == "ord-001"
        assert reservation.quantity == 5
        assert reservation.status == ReservationStatus.ACTIVE.value
        assert reservation.reserved_at == now

    def test_default_status_is_active(self):
        now = datetime.now(UTC)
        reservation = Reservation(
            order_id="ord-001",
            quantity=3,
            reserved_at=now,
            expires_at=now + timedelta(minutes=15),
        )
        assert reservation.status == ReservationStatus.ACTIVE.value

    def test_requires_order_id(self):
        now = datetime.now(UTC)
        with pytest.raises(ValidationError):
            Reservation(
                quantity=5,
                reserved_at=now,
                expires_at=now + timedelta(minutes=15),
            )

    def test_requires_positive_quantity(self):
        now = datetime.now(UTC)
        with pytest.raises(ValidationError):
            Reservation(
                order_id="ord-001",
                quantity=0,
                reserved_at=now,
                expires_at=now + timedelta(minutes=15),
            )
