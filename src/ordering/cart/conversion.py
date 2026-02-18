"""Cart to order conversion — command and handler."""

from protean import handle
from protean.fields import Identifier
from protean.utils.globals import current_domain

from ordering.cart.cart import ShoppingCart
from ordering.domain import ordering


@ordering.command(part_of="ShoppingCart")
class ConvertToOrder:
    cart_id = Identifier(required=True)


@ordering.command_handler(part_of=ShoppingCart)
class ConvertCartHandler:
    @handle(ConvertToOrder)
    def convert_to_order(self, command):
        repo = current_domain.repository_for(ShoppingCart)
        cart = repo.get(command.cart_id)
        cart.convert_to_order()
        repo.add(cart)
