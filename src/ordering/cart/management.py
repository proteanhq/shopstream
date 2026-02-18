"""Cart management — commands and handler.

Handles cart creation, guest cart merging, and abandonment.
"""

import json

from protean import handle
from protean.fields import Identifier, String, Text
from protean.utils.globals import current_domain

from ordering.cart.cart import ShoppingCart
from ordering.domain import ordering


@ordering.command(part_of="ShoppingCart")
class CreateCart:
    """Create a new shopping cart for a registered customer or guest session."""

    customer_id = Identifier()  # Optional for guest carts
    session_id = String(max_length=255)


@ordering.command(part_of="ShoppingCart")
class MergeGuestCart:
    """Merge items from a guest session cart into a registered customer's cart."""

    cart_id = Identifier(required=True)
    guest_cart_items = Text(required=True)  # JSON: list of {product_id, variant_id, quantity}


@ordering.command(part_of="ShoppingCart")
class AbandonCart:
    """Mark a cart as abandoned due to inactivity."""

    cart_id = Identifier(required=True)


@ordering.command_handler(part_of=ShoppingCart)
class ManageCartHandler:
    @handle(CreateCart)
    def create_cart(self, command):
        cart = ShoppingCart.create(
            customer_id=command.customer_id,
            session_id=command.session_id,
        )
        current_domain.repository_for(ShoppingCart).add(cart)
        return str(cart.id)

    @handle(MergeGuestCart)
    def merge_guest_cart(self, command):
        repo = current_domain.repository_for(ShoppingCart)
        cart = repo.get(command.cart_id)

        guest_items = (
            json.loads(command.guest_cart_items)
            if isinstance(command.guest_cart_items, str)
            else command.guest_cart_items
        )

        cart.merge_guest_cart(guest_cart_items=guest_items)
        repo.add(cart)

    @handle(AbandonCart)
    def abandon_cart(self, command):
        repo = current_domain.repository_for(ShoppingCart)
        cart = repo.get(command.cart_id)
        cart.abandon()
        repo.add(cart)
