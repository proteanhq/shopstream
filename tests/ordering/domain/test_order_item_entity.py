"""Tests for OrderItem entity."""

from ordering.order.order import ItemStatus, OrderItem


class TestOrderItemConstruction:
    def test_basic_construction(self):
        item = OrderItem(
            product_id="prod-001",
            variant_id="var-001",
            sku="TSHIRT-BLK-M",
            title="Black T-Shirt (M)",
            quantity=2,
            unit_price=29.99,
        )
        assert item.sku == "TSHIRT-BLK-M"
        assert item.quantity == 2
        assert item.unit_price == 29.99

    def test_default_item_status(self):
        item = OrderItem(
            product_id="prod-001",
            variant_id="var-001",
            sku="SKU-001",
            title="Product",
            quantity=1,
            unit_price=10.0,
        )
        assert item.item_status == ItemStatus.PENDING.value

    def test_default_discount(self):
        item = OrderItem(
            product_id="prod-001",
            variant_id="var-001",
            sku="SKU-001",
            title="Product",
            quantity=1,
            unit_price=10.0,
        )
        assert item.discount == 0.0

    def test_default_tax_amount(self):
        item = OrderItem(
            product_id="prod-001",
            variant_id="var-001",
            sku="SKU-001",
            title="Product",
            quantity=1,
            unit_price=10.0,
        )
        assert item.tax_amount == 0.0

    def test_with_discount_and_tax(self):
        item = OrderItem(
            product_id="prod-001",
            variant_id="var-001",
            sku="SKU-001",
            title="Product",
            quantity=1,
            unit_price=100.0,
            discount=10.0,
            tax_amount=8.0,
        )
        assert item.discount == 10.0
        assert item.tax_amount == 8.0
