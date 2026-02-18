"""Application tests for order modification commands."""

import json

from ordering.order.creation import CreateOrder
from ordering.order.modification import AddItem, ApplyCoupon, RemoveItem, UpdateItemQuantity
from ordering.order.order import Order
from protean import current_domain


def _create_order():
    command = CreateOrder(
        customer_id="cust-001",
        items=json.dumps(
            [
                {
                    "product_id": "prod-001",
                    "variant_id": "var-001",
                    "sku": "SKU-001",
                    "title": "Widget",
                    "quantity": 2,
                    "unit_price": 25.0,
                },
            ]
        ),
        shipping_address=json.dumps(
            {"street": "123 Main", "city": "Town", "state": "CA", "postal_code": "90210", "country": "US"}
        ),
        billing_address=json.dumps(
            {"street": "123 Main", "city": "Town", "state": "CA", "postal_code": "90210", "country": "US"}
        ),
        subtotal=50.0,
        grand_total=55.0,
    )
    return current_domain.process(command, asynchronous=False)


class TestAddItemCommand:
    def test_add_item_persists(self):
        order_id = _create_order()
        command = AddItem(
            order_id=order_id,
            product_id="prod-002",
            variant_id="var-002",
            sku="SKU-002",
            title="Gadget",
            quantity=1,
            unit_price=30.0,
        )
        current_domain.process(command, asynchronous=False)

        order = current_domain.repository_for(Order).get(order_id)
        assert len(order.items) == 2


class TestRemoveItemCommand:
    def test_remove_item_persists(self):
        order_id = _create_order()

        # Add a second item to remove
        current_domain.process(
            AddItem(
                order_id=order_id,
                product_id="prod-002",
                variant_id="var-002",
                sku="SKU-002",
                title="Gadget",
                quantity=1,
                unit_price=10.0,
            ),
            asynchronous=False,
        )
        order = current_domain.repository_for(Order).get(order_id)
        item_id = str(order.items[1].id)

        current_domain.process(
            RemoveItem(order_id=order_id, item_id=item_id),
            asynchronous=False,
        )

        order = current_domain.repository_for(Order).get(order_id)
        assert len(order.items) == 1


class TestUpdateItemQuantityCommand:
    def test_update_quantity_persists(self):
        order_id = _create_order()
        order = current_domain.repository_for(Order).get(order_id)
        item_id = str(order.items[0].id)

        current_domain.process(
            UpdateItemQuantity(
                order_id=order_id,
                item_id=item_id,
                new_quantity=5,
            ),
            asynchronous=False,
        )

        order = current_domain.repository_for(Order).get(order_id)
        assert order.items[0].quantity == 5


class TestApplyCouponCommand:
    def test_apply_coupon_persists(self):
        order_id = _create_order()
        current_domain.process(
            ApplyCoupon(order_id=order_id, coupon_code="SAVE10"),
            asynchronous=False,
        )

        order = current_domain.repository_for(Order).get(order_id)
        assert order.coupon_code == "SAVE10"
