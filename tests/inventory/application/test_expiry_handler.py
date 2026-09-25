"""Application tests for ExpireStaleReservationsHandler — background job for releasing timed-out reservations.

Covers:
- Stale reservations (past expiry) are released when the command runs
- No stale reservations results in a no-op
- Fresh reservations (not yet expired) are not released
- A stale view row is skipped without rolling back the other releases
"""

from datetime import UTC, datetime, timedelta

from protean import current_domain

from inventory.projections.reservation_status import ReservationStatus
from inventory.stock.expiry import ExpireStaleReservations
from inventory.stock.initialization import InitializeStock
from inventory.stock.reservation import ReleaseReservation, ReserveStock
from inventory.stock.stock import InventoryItem


def _initialize_stock(**overrides):
    defaults = {
        "product_id": "prod-001",
        "variant_id": "var-001",
        "warehouse_id": "wh-001",
        "sku": "TSHIRT-BLK-M",
        "initial_quantity": 100,
        "reorder_point": 10,
        "reorder_quantity": 50,
    }
    defaults.update(overrides)
    return current_domain.process(InitializeStock(**defaults), asynchronous=False)


class TestExpireStaleReservations:
    def test_expires_stale_reservation(self):
        """A reservation past its expiry time should be released."""
        item_id = _initialize_stock(initial_quantity=100)

        # Reserve with an expiry in the past (already expired)
        past_expiry = datetime.now(UTC) - timedelta(minutes=30)
        current_domain.process(
            ReserveStock(
                inventory_item_id=item_id,
                order_id="ord-expire-001",
                quantity=10,
                expires_at=past_expiry,
            ),
            asynchronous=False,
        )

        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.reserved == 10
        assert item.levels.available == 90

        # Run expiry with older_than_minutes=0 so all expired reservations qualify
        current_domain.process(
            ExpireStaleReservations(
                older_than_minutes=0,
                as_of=datetime.now(UTC),
            ),
            asynchronous=False,
        )

        # Reservation should be released
        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.reserved == 0
        assert item.levels.available == 100

    def test_no_stale_reservations_is_noop(self):
        """When no stale reservations exist, the command returns without error."""
        # Run expiry with no inventory at all
        current_domain.process(
            ExpireStaleReservations(
                older_than_minutes=15,
                as_of=datetime.now(UTC),
            ),
            asynchronous=False,
        )

    def test_fresh_reservations_are_not_expired(self):
        """Reservations that have not yet expired should be left alone."""
        item_id = _initialize_stock(initial_quantity=100)

        # Reserve with an expiry far in the future
        future_expiry = datetime.now(UTC) + timedelta(hours=1)
        current_domain.process(
            ReserveStock(
                inventory_item_id=item_id,
                order_id="ord-fresh-001",
                quantity=15,
                expires_at=future_expiry,
            ),
            asynchronous=False,
        )

        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.reserved == 15

        # Run expiry -- the reservation's expiry is in the future, so it should not be released
        current_domain.process(
            ExpireStaleReservations(
                older_than_minutes=0,
                as_of=datetime.now(UTC),
            ),
            asynchronous=False,
        )

        # Reservation should still be active
        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.reserved == 15
        assert item.levels.available == 85


class TestExpireStaleReservationsStaleProjection:
    """The ReservationStatus view can lag the aggregate. A release the aggregate would
    reject must not roll back the good releases in the same batch."""

    def _reserve_expired(self, item_id, order_id, quantity):
        current_domain.process(
            ReserveStock(
                inventory_item_id=item_id,
                order_id=order_id,
                quantity=quantity,
                expires_at=datetime.now(UTC) - timedelta(minutes=30),
            ),
            asynchronous=False,
        )
        return str(current_domain.repository_for(InventoryItem).get(item_id).reservations[-1].id)

    def _mark_active_in_view(self, reservation_id):
        view_repo = current_domain.repository_for(ReservationStatus)
        view = view_repo.get(reservation_id)
        view.status = "Active"
        view_repo.add(view)

    def test_skips_already_released_reservation_and_keeps_the_rest(self):
        released_item = _initialize_stock(sku="SKU-RELEASED")
        good_item = _initialize_stock(sku="SKU-GOOD")
        released_id = self._reserve_expired(released_item, "ord-released", 5)
        self._reserve_expired(good_item, "ord-good", 5)

        # Released already, but the view still says Active.
        current_domain.process(
            ReleaseReservation(inventory_item_id=released_item, reservation_id=released_id, reason="manual"),
            asynchronous=False,
        )
        self._mark_active_in_view(released_id)

        result = current_domain.process(
            ExpireStaleReservations(older_than_minutes=0, as_of=datetime.now(UTC)),
            asynchronous=False,
        )

        assert result == 1
        good = current_domain.repository_for(InventoryItem).get(good_item)
        assert good.levels.reserved == 0
        assert good.levels.available == 100

    def test_skips_reservation_whose_item_is_missing(self):
        good_item = _initialize_stock(sku="SKU-GOOD")
        self._reserve_expired(good_item, "ord-good", 5)
        current_domain.repository_for(ReservationStatus).add(
            ReservationStatus(
                reservation_id="res-orphan",
                inventory_item_id="item-missing",
                order_id="ord-orphan",
                quantity=3,
                status="Active",
                expires_at=datetime.now(UTC) - timedelta(minutes=30),
            )
        )

        result = current_domain.process(
            ExpireStaleReservations(older_than_minutes=0, as_of=datetime.now(UTC)),
            asynchronous=False,
        )

        assert result == 1
        assert current_domain.repository_for(InventoryItem).get(good_item).levels.reserved == 0
