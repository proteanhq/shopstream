"""Application tests for cart item management commands."""

from ordering.cart.cart import ShoppingCart
from ordering.cart.items import AddToCart, RemoveFromCart, UpdateCartQuantity
from ordering.cart.management import CreateCart
from protean import current_domain


def _create_cart(**overrides):
    defaults = {"customer_id": "cust-001"}
    defaults.update(overrides)
    return current_domain.process(CreateCart(**defaults), asynchronous=False)


class TestAddToCartCommand:
    def test_add_item_persists(self):
        cart_id = _create_cart()
        current_domain.process(
            AddToCart(
                cart_id=cart_id,
                product_id="prod-001",
                variant_id="var-001",
                quantity=2,
            ),
            asynchronous=False,
        )
        cart = current_domain.repository_for(ShoppingCart).get(cart_id)
        assert len(cart.items) == 1
        assert cart.items[0].quantity == 2

    def test_add_multiple_items(self):
        cart_id = _create_cart()
        current_domain.process(
            AddToCart(cart_id=cart_id, product_id="prod-001", variant_id="var-001", quantity=1),
            asynchronous=False,
        )
        current_domain.process(
            AddToCart(cart_id=cart_id, product_id="prod-002", variant_id="var-002", quantity=3),
            asynchronous=False,
        )
        cart = current_domain.repository_for(ShoppingCart).get(cart_id)
        assert len(cart.items) == 2


class TestUpdateCartQuantityCommand:
    def test_update_quantity_persists(self):
        cart_id = _create_cart()
        current_domain.process(
            AddToCart(cart_id=cart_id, product_id="prod-001", variant_id="var-001", quantity=1),
            asynchronous=False,
        )
        cart = current_domain.repository_for(ShoppingCart).get(cart_id)
        item_id = str(cart.items[0].id)

        current_domain.process(
            UpdateCartQuantity(cart_id=cart_id, item_id=item_id, new_quantity=5),
            asynchronous=False,
        )
        cart = current_domain.repository_for(ShoppingCart).get(cart_id)
        assert cart.items[0].quantity == 5


class TestRemoveFromCartCommand:
    def test_remove_item_persists(self):
        cart_id = _create_cart()
        current_domain.process(
            AddToCart(cart_id=cart_id, product_id="prod-001", variant_id="var-001", quantity=1),
            asynchronous=False,
        )
        cart = current_domain.repository_for(ShoppingCart).get(cart_id)
        item_id = str(cart.items[0].id)

        current_domain.process(
            RemoveFromCart(cart_id=cart_id, item_id=item_id),
            asynchronous=False,
        )
        cart = current_domain.repository_for(ShoppingCart).get(cart_id)
        assert len(cart.items) == 0
