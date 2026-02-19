"""Tests for inventory business rule invariants."""

import pytest
from inventory.stock.stock import InventoryItem
from protean.exceptions import ValidationError


def _make_item(**overrides):
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
    return InventoryItem.create(**defaults)


class TestInventoryInvariants:
    def test_available_cannot_be_negative(self):
        """Attempting to reserve more than available should fail."""
        item = _make_item(initial_quantity=10)
        with pytest.raises(ValidationError):
            item.reserve(order_id="ord-001", quantity=15)

    def test_reserved_cannot_exceed_on_hand(self):
        """Reserving the full amount is fine; exceeding it raises error."""
        item = _make_item(initial_quantity=50)
        item.reserve(order_id="ord-001", quantity=50)
        assert item.levels.reserved == 50
        assert item.levels.on_hand == 50
        # Try to reserve more
        with pytest.raises(ValidationError):
            item.reserve(order_id="ord-002", quantity=1)

    def test_damaged_cannot_be_negative(self):
        """Cannot write off more damaged stock than exists."""
        item = _make_item(initial_quantity=100)
        item.mark_damaged(quantity=5, reason="Water damage")
        with pytest.raises(ValidationError):
            item.write_off_damaged(quantity=10, approved_by="manager-001")

    def test_on_hand_cannot_go_negative_via_adjustment(self):
        item = _make_item(initial_quantity=10)
        with pytest.raises(ValidationError):
            item.adjust_stock(
                quantity_change=-20,
                adjustment_type="Correction",
                reason="Bad data",
                adjusted_by="admin",
            )

    def test_cannot_damage_reserved_stock(self):
        """Cannot mark reserved stock as damaged."""
        item = _make_item(initial_quantity=100)
        item.reserve(order_id="ord-001", quantity=90)
        # Only 10 unreserved
        with pytest.raises(ValidationError):
            item.mark_damaged(quantity=15, reason="Flood damage")
