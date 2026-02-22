"""Application tests for ExpireStaleReservationsHandler — background job for releasing timed-out reservations.

Covers:
- Stale reservations (past expiry) are released when the command runs
- No stale reservations results in a no-op
- Fresh reservations (not yet expired) are not released
"""

from datetime import UTC, datetime, timedelta

from inventory.stock.expiry import ExpireStaleReservations
from inventory.stock.initialization import InitializeStock
from inventory.stock.reservation import ReserveStock
from inventory.stock.stock import InventoryItem
from protean import current_domain


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


class TestExpireStaleReservationsProcessFailure:
    """Mock-based: ValidationError/InvalidOperationError during reservation release is caught."""

    def test_continues_after_process_raises_validation_error(self):
        from unittest.mock import MagicMock, patch

        from inventory.stock.expiry import ExpireStaleReservationsHandler
        from protean.exceptions import ValidationError

        handler = ExpireStaleReservationsHandler()

        # Create a mock command
        as_of = datetime.now(UTC)
        mock_command = MagicMock()
        mock_command.as_of = as_of
        mock_command.older_than_minutes = 0

        # Create mock expired reservations
        mock_reservation = MagicMock()
        mock_reservation.reservation_id = "res-fail-001"
        mock_reservation.inventory_item_id = "item-fail-001"
        mock_reservation.order_id = "ord-fail-001"
        mock_reservation.expires_at = (as_of - timedelta(minutes=30)).replace(tzinfo=None)

        mock_query_result = MagicMock()
        mock_query_result.items = [mock_reservation]

        mock_repo = MagicMock()
        mock_repo._dao.query.filter.return_value.all.return_value = mock_query_result

        with patch("inventory.stock.expiry.current_domain") as mock_domain:
            mock_domain.repository_for = MagicMock(return_value=mock_repo)
            mock_domain.process = MagicMock(side_effect=ValidationError({"error": ["Reservation already released"]}))
            # Should not raise; catches the error, logs warning, and continues
            result = handler.expire_stale_reservations(mock_command)
            # expired_count should be 0 since all attempts failed
            assert result == 0
            # process was called once (for the one expired reservation)
            mock_domain.process.assert_called_once()

    def test_continues_after_process_raises_invalid_operation_error(self):
        from unittest.mock import MagicMock, patch

        from inventory.stock.expiry import ExpireStaleReservationsHandler
        from protean.exceptions import InvalidOperationError

        handler = ExpireStaleReservationsHandler()

        as_of = datetime.now(UTC)
        mock_command = MagicMock()
        mock_command.as_of = as_of
        mock_command.older_than_minutes = 0

        # Two expired reservations: first fails, second should still be attempted
        mock_res1 = MagicMock()
        mock_res1.reservation_id = "res-fail-002"
        mock_res1.inventory_item_id = "item-fail-002"
        mock_res1.order_id = "ord-fail-002"
        mock_res1.expires_at = (as_of - timedelta(minutes=30)).replace(tzinfo=None)

        mock_res2 = MagicMock()
        mock_res2.reservation_id = "res-ok-001"
        mock_res2.inventory_item_id = "item-ok-001"
        mock_res2.order_id = "ord-ok-001"
        mock_res2.expires_at = (as_of - timedelta(minutes=20)).replace(tzinfo=None)

        mock_query_result = MagicMock()
        mock_query_result.items = [mock_res1, mock_res2]

        mock_repo = MagicMock()
        mock_repo._dao.query.filter.return_value.all.return_value = mock_query_result

        with patch("inventory.stock.expiry.current_domain") as mock_domain:
            mock_domain.repository_for = MagicMock(return_value=mock_repo)
            # First call fails, second succeeds
            mock_domain.process = MagicMock(
                side_effect=[
                    InvalidOperationError("Reservation in wrong state"),
                    None,
                ]
            )
            result = handler.expire_stale_reservations(mock_command)
            # Only the second one succeeded
            assert result == 1
            assert mock_domain.process.call_count == 2
