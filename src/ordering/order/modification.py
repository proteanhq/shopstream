"""Order modification — commands and handler.

Handles item additions, removals, quantity updates, and coupon application.
All modifications are only allowed in CREATED state.
"""

from decimal import Decimal as D

from protean import handle
from protean.fields import Decimal, Identifier, Integer, String
from protean.utils.globals import current_domain

from ordering.domain import ordering
from ordering.order.order import Order


@ordering.command(part_of="Order")
class AddItem:
    """Add a new line item to an order (only allowed in Created state)."""

    order_id: str = Identifier(required=True)
    product_id: str = Identifier(required=True)
    variant_id: str = Identifier(required=True)
    sku: str = String(required=True, max_length=50)
    title: str = String(required=True, max_length=255)
    quantity: int = Integer(required=True, min_value=1)
    unit_price: D = Decimal(precision=19, scale=4, required=True, min_value=D("0.0"))


@ordering.command(part_of="Order")
class RemoveItem:
    """Remove a line item from an order (only allowed in Created state)."""

    order_id: str = Identifier(required=True)
    item_id: str = Identifier(required=True)


@ordering.command(part_of="Order")
class UpdateItemQuantity:
    """Change the quantity of an existing order line item."""

    order_id: str = Identifier(required=True)
    item_id: str = Identifier(required=True)
    new_quantity: int = Integer(required=True, min_value=1)


@ordering.command(part_of="Order")
class ApplyCoupon:
    """Apply a coupon code to an order for a discount."""

    order_id: str = Identifier(required=True)
    coupon_code: str = String(required=True, max_length=100)


@ordering.command_handler(part_of=Order)
class ModifyOrderHandler:
    @handle(AddItem)
    def add_item(self, command: AddItem) -> None:
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
    def remove_item(self, command: RemoveItem) -> None:
        repo = current_domain.repository_for(Order)
        order = repo.get(command.order_id)
        order.remove_item(item_id=command.item_id)
        repo.add(order)

    @handle(UpdateItemQuantity)
    def update_item_quantity(self, command: UpdateItemQuantity) -> None:
        repo = current_domain.repository_for(Order)
        order = repo.get(command.order_id)
        order.update_item_quantity(
            item_id=command.item_id,
            new_quantity=command.new_quantity,
        )
        repo.add(order)

    @handle(ApplyCoupon)
    def apply_coupon(self, command: ApplyCoupon) -> None:
        repo = current_domain.repository_for(Order)
        order = repo.get(command.order_id)
        order.apply_coupon(coupon_code=command.coupon_code)
        repo.add(order)
