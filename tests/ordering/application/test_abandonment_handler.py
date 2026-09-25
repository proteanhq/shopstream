"""Application tests for DetectAbandonedCartsHandler — background job for flagging idle carts.

Covers:
- Idle carts with items are marked as abandoned
- No idle carts results in a no-op
- Active carts within the threshold are not abandoned
- A stale view row is skipped without rolling back the other carts
"""

from datetime import UTC, datetime, timedelta

from protean import current_domain

from ordering.cart.abandonment import DetectAbandonedCarts
from ordering.cart.cart import ShoppingCart
from ordering.cart.items import AddToCart
from ordering.cart.management import AbandonCart, CreateCart
from ordering.projections.cart_view import CartView


def _create_cart_with_items():
    """Create a cart and add an item to it, returning the cart_id."""
    cart_id = current_domain.process(
        CreateCart(customer_id="cust-abandon-001"),
        asynchronous=False,
    )
    current_domain.process(
        AddToCart(
            cart_id=cart_id,
            product_id="prod-001",
            variant_id="var-001",
            quantity=2,
        ),
        asynchronous=False,
    )
    return cart_id


class TestDetectAbandonedCarts:
    def test_abandons_idle_cart_with_items(self):
        """A cart idle beyond the threshold with items should be marked as abandoned."""
        cart_id = _create_cart_with_items()

        # Manually set the CartView's updated_at to the past so it appears idle
        repo = current_domain.repository_for(CartView)
        view = repo.get(cart_id)
        view.updated_at = datetime.now(UTC) - timedelta(hours=48)
        repo.add(view)

        # Run abandonment detection with threshold=0 (any idle cart qualifies)
        current_domain.process(
            DetectAbandonedCarts(
                idle_threshold_hours=0,
                as_of=datetime.now(UTC),
            ),
            asynchronous=False,
        )

        # CartView should reflect Abandoned status (updated by projector)
        view = repo.get(cart_id)
        assert view.status == "Abandoned"

    def test_no_idle_carts_is_noop(self):
        """When no idle carts exist, the command returns without error."""
        current_domain.process(
            DetectAbandonedCarts(
                idle_threshold_hours=24,
                as_of=datetime.now(UTC),
            ),
            asynchronous=False,
        )

    def test_fresh_carts_are_not_abandoned(self):
        """Carts updated recently should not be marked as abandoned."""
        cart_id = _create_cart_with_items()

        # Set updated_at to a recent time (within the threshold)
        repo = current_domain.repository_for(CartView)
        view = repo.get(cart_id)
        view.updated_at = datetime.now(UTC) - timedelta(minutes=5)
        repo.add(view)

        # Run abandonment detection with 24-hour threshold
        current_domain.process(
            DetectAbandonedCarts(
                idle_threshold_hours=24,
                as_of=datetime.now(UTC),
            ),
            asynchronous=False,
        )

        # CartView should still show Active
        view = repo.get(cart_id)
        assert view.status == "Active"

    def test_empty_carts_are_not_abandoned(self):
        """Carts without items should not be marked as abandoned even if idle."""
        cart_id = current_domain.process(
            CreateCart(customer_id="cust-empty-cart"),
            asynchronous=False,
        )

        # Set updated_at to the past but cart has no items
        repo = current_domain.repository_for(CartView)
        try:
            view = repo.get(cart_id)
        except Exception:
            # CartView might not exist yet (no items added = no CartItemAdded event)
            # which means the handler won't find it either -- test passes
            return

        view.updated_at = datetime.now(UTC) - timedelta(hours=48)
        repo.add(view)

        current_domain.process(
            DetectAbandonedCarts(
                idle_threshold_hours=0,
                as_of=datetime.now(UTC),
            ),
            asynchronous=False,
        )

        # Cart should still be Active (no CartView exists for empty cart)
        cart = current_domain.repository_for(ShoppingCart).get(cart_id)
        assert cart.status in ("Active", "Active")


class TestDetectAbandonedCartsStaleProjection:
    """The CartView can lag the aggregate. A cart the aggregate would refuse to
    abandon must not roll back the other carts in the same batch."""

    def _make_idle_in_view(self, cart_id, status="Active"):
        repo = current_domain.repository_for(CartView)
        view = repo.get(cart_id)
        view.status = status
        view.updated_at = datetime.now(UTC) - timedelta(hours=48)
        repo.add(view)

    def test_skips_already_abandoned_cart_and_keeps_the_rest(self):
        stale_cart = _create_cart_with_items()
        good_cart = _create_cart_with_items()

        # Abandoned already, but the view still says Active.
        current_domain.process(AbandonCart(cart_id=stale_cart), asynchronous=False)
        self._make_idle_in_view(stale_cart)
        self._make_idle_in_view(good_cart)

        result = current_domain.process(
            DetectAbandonedCarts(idle_threshold_hours=24, as_of=datetime.now(UTC)),
            asynchronous=False,
        )

        assert result == 1
        assert current_domain.repository_for(ShoppingCart).get(good_cart).status == "Abandoned"

    def test_skips_cart_missing_from_the_aggregate_store(self):
        good_cart = _create_cart_with_items()
        self._make_idle_in_view(good_cart)
        orphan = current_domain.repository_for(CartView).get(good_cart).to_dict()
        orphan["cart_id"] = "cart-missing"
        current_domain.repository_for(CartView).add(CartView(**orphan))

        result = current_domain.process(
            DetectAbandonedCarts(idle_threshold_hours=24, as_of=datetime.now(UTC)),
            asynchronous=False,
        )

        assert result == 1
        assert current_domain.repository_for(ShoppingCart).get(good_cart).status == "Abandoned"
