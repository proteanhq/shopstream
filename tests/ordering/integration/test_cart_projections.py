"""Integration tests for Cart projections — verify CartView projector."""

from protean import current_domain

from ordering.cart.coupons import ApplyCouponToCart
from ordering.cart.items import AddToCart, RemoveFromCart
from ordering.cart.management import AbandonCart, CreateCart
from ordering.projections.cart_view import CartView


def _create_cart(customer_id="cust-cv-001"):
    return current_domain.process(CreateCart(customer_id=customer_id), asynchronous=False)


class TestCartViewProjection:
    def test_cart_view_created_on_item_added(self):
        cart_id = _create_cart()
        current_domain.process(
            AddToCart(cart_id=cart_id, product_id="prod-001", variant_id="var-001", quantity=2),
            asynchronous=False,
        )

        view = current_domain.repository_for(CartView).get(cart_id)
        assert view.cart_id == cart_id
        assert view.status == "Active"
        assert view.item_count == 1

        assert len(view.items) == 1
        assert view.items[0]["product_id"] == "prod-001"
        assert view.items[0]["quantity"] == 2

    def test_cart_view_tracks_multiple_items(self):
        cart_id = _create_cart()
        current_domain.process(
            AddToCart(cart_id=cart_id, product_id="prod-001", variant_id="var-001", quantity=1),
            asynchronous=False,
        )
        current_domain.process(
            AddToCart(cart_id=cart_id, product_id="prod-002", variant_id="var-002", quantity=3),
            asynchronous=False,
        )

        view = current_domain.repository_for(CartView).get(cart_id)
        assert view.item_count == 2

    def test_cart_view_coupon_applied(self):
        cart_id = _create_cart()
        current_domain.process(
            AddToCart(cart_id=cart_id, product_id="prod-001", variant_id="var-001", quantity=1),
            asynchronous=False,
        )
        current_domain.process(
            ApplyCouponToCart(cart_id=cart_id, coupon_code="SAVE10"),
            asynchronous=False,
        )

        view = current_domain.repository_for(CartView).get(cart_id)
        assert "SAVE10" in view.applied_coupons

    def test_cart_view_abandoned(self):
        cart_id = _create_cart()
        current_domain.process(AbandonCart(cart_id=cart_id), asynchronous=False)

        view = current_domain.repository_for(CartView).get(cart_id)
        assert view.status == "Abandoned"

    def test_cart_view_item_removed(self):
        cart_id = _create_cart()
        current_domain.process(
            AddToCart(cart_id=cart_id, product_id="prod-001", variant_id="var-001", quantity=1),
            asynchronous=False,
        )
        current_domain.process(
            AddToCart(cart_id=cart_id, product_id="prod-002", variant_id="var-002", quantity=1),
            asynchronous=False,
        )

        # Get item_id to remove
        from ordering.cart.cart import ShoppingCart

        cart = current_domain.repository_for(ShoppingCart).get(cart_id)
        item_id = str(cart.items[0].id)

        current_domain.process(RemoveFromCart(cart_id=cart_id, item_id=item_id), asynchronous=False)

        view = current_domain.repository_for(CartView).get(cart_id)
        assert view.item_count == 1


class TestCartViewGetOrNone:
    def test_hit_returns_projected_items(self):
        cart_id = _create_cart(customer_id="cust-cv-gon")
        current_domain.process(
            AddToCart(cart_id=cart_id, product_id="prod-gon-1", variant_id="var-gon-1", quantity=2),
            asynchronous=False,
        )
        current_domain.process(
            AddToCart(cart_id=cart_id, product_id="prod-gon-2", variant_id="var-gon-2", quantity=5),
            asynchronous=False,
        )

        view = current_domain.repository_for(CartView).get_or_none(cart_id)

        assert view is not None
        assert view.cart_id == cart_id
        assert view.item_count == 2
        assert [(i["product_id"], i["variant_id"], i["quantity"]) for i in view.items] == [
            ("prod-gon-1", "var-gon-1", 2),
            ("prod-gon-2", "var-gon-2", 5),
        ]

    def test_miss_returns_none(self):
        assert current_domain.repository_for(CartView).get_or_none("missing-cart-id") is None
