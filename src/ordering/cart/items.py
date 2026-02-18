"""Cart item management — commands and handler."""

from protean import handle
from protean.fields import Identifier, Integer
from protean.utils.globals import current_domain

from ordering.cart.cart import ShoppingCart
from ordering.domain import ordering


@ordering.command(part_of="ShoppingCart")
class AddToCart:
    cart_id = Identifier(required=True)
    product_id = Identifier(required=True)
    variant_id = Identifier(required=True)
    quantity = Integer(required=True, min_value=1)


@ordering.command(part_of="ShoppingCart")
class UpdateCartQuantity:
    cart_id = Identifier(required=True)
    item_id = Identifier(required=True)
    new_quantity = Integer(required=True, min_value=1)


@ordering.command(part_of="ShoppingCart")
class RemoveFromCart:
    cart_id = Identifier(required=True)
    item_id = Identifier(required=True)


@ordering.command_handler(part_of=ShoppingCart)
class ManageCartItemsHandler:
    @handle(AddToCart)
    def add_to_cart(self, command):
        repo = current_domain.repository_for(ShoppingCart)
        cart = repo.get(command.cart_id)
        cart.add_item(
            product_id=command.product_id,
            variant_id=command.variant_id,
            quantity=command.quantity,
        )
        repo.add(cart)

    @handle(UpdateCartQuantity)
    def update_cart_quantity(self, command):
        repo = current_domain.repository_for(ShoppingCart)
        cart = repo.get(command.cart_id)
        cart.update_item_quantity(
            item_id=command.item_id,
            new_quantity=command.new_quantity,
        )
        repo.add(cart)

    @handle(RemoveFromCart)
    def remove_from_cart(self, command):
        repo = current_domain.repository_for(ShoppingCart)
        cart = repo.get(command.cart_id)
        cart.remove_item(item_id=command.item_id)
        repo.add(cart)
