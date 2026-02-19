"""Tests for StockLevels value object."""

from inventory.stock.stock import StockLevels


class TestStockLevelsConstruction:
    def test_construction_with_defaults(self):
        levels = StockLevels()
        assert levels.on_hand == 0
        assert levels.reserved == 0
        assert levels.available == 0
        assert levels.in_transit == 0
        assert levels.damaged == 0

    def test_construction_with_values(self):
        levels = StockLevels(
            on_hand=100,
            reserved=20,
            available=80,
            in_transit=30,
            damaged=5,
        )
        assert levels.on_hand == 100
        assert levels.reserved == 20
        assert levels.available == 80
        assert levels.in_transit == 30
        assert levels.damaged == 5

    def test_available_consistency(self):
        levels = StockLevels(on_hand=100, reserved=20, available=80)
        assert levels.available == levels.on_hand - levels.reserved
