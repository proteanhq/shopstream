"""Order modification — commands and handler.

Handles item additions, removals, quantity updates, and coupon application.
All modifications are only allowed in CREATED state.
"""

from protean import handle
from protean.fields import Float, Identifier, Integer, String
from protean.utils.globals import current_domain

from ordering.domain import ordering
from ordering.order.order import Order


@ordering.command(part_of="Order")
class AddItem:
    """Add a new line item to an order (only allowed in Created state)."""

    order_id = Identifier(required=True)
    product_id = Identifier(required=True)
    variant_id = Identifier(required=True)
    sku = String(required=True, max_length=50)
    title = String(required=True, max_length=255)
    quantity = Integer(required=True, min_value=1)
    unit_price = Float(required=True, min_value=0.0)


@ordering.command(part_of="Order")
class RemoveItem:
    """Remove a line item from an order (only allowed in Created state)."""

    order_id = Identifier(required=True)
    item_id = Identifier(required=True)


@ordering.command(part_of="Order")
class UpdateItemQuantity:
    """Change the quantity of an existing order line item."""

    order_id = Identifier(required=True)
    item_id = Identifier(required=True)
    new_quantity = Integer(required=True, min_value=1)


@ordering.command(part_of="Order")
class ApplyCoupon:
    """Apply a coupon code to an order for a discount."""

    order_id = Identifier(required=True)
    coupon_code = String(required=True, max_length=100)


@ordering.command_handler(part_of=Order)
class ModifyOrderHandler:
    @handle(AddItem)
    def add_item(self, command):
        repo = current_domain.repository_for(Order)
        order = repo.get(command.order_id)
        order.add_item(
            product_id=command.product_id,
            variant_id=command.variant_id,
            sku=command.sku,
            title=command.title,
            quantity=command.quantity,
            unit_price=command.unit_price,
        )
        repo.add(order)

    @handle(RemoveItem)
    def remove_item(self, command):
        repo = current_domain.repository_for(Order)
        order = repo.get(command.order_id)
        order.remove_item(item_id=command.item_id)
        repo.add(order)

    @handle(UpdateItemQuantity)
    def update_item_quantity(self, command):
        repo = current_domain.repository_for(Order)
        order = repo.get(command.order_id)
        order.update_item_quantity(
            item_id=command.item_id,
            new_quantity=command.new_quantity,
        )
        repo.add(order)

    @handle(ApplyCoupon)
    def apply_coupon(self, command):
        repo = current_domain.repository_for(Order)
        order = repo.get(command.order_id)
        order.apply_coupon(coupon_code=command.coupon_code)
        repo.add(order)
