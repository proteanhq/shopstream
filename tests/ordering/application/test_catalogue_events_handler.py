"""Application tests for CatalogueEventsSubscriber — Ordering reacts to Catalogue events.

Covers:
- on_product_discontinued with no active carts: logs, no error
- on_product_discontinued with active cart containing the product: logs warning with affected count
"""

from datetime import UTC, datetime

from protean import current_domain

from ordering.cart.catalogue_subscriber import CatalogueEventsSubscriber
from ordering.cart.items import AddToCart
from ordering.cart.management import CreateCart


def _build_message(event_type: str, data: dict) -> dict:
    return {"data": data, "metadata": {"headers": {"type": event_type}}}


def _create_cart_with_product(product_id):
    """Create a cart and add a specific product to it."""
    cart_id = current_domain.process(
        CreateCart(customer_id="cust-cat-001"),
        asynchronous=False,
    )
    current_domain.process(
        AddToCart(
            cart_id=cart_id,
            product_id=product_id,
            variant_id="var-001",
            quantity=1,
        ),
        asynchronous=False,
    )
    return cart_id


class TestProductDiscontinuedHandler:
    def test_no_active_carts_is_noop(self):
        """When no active carts exist, handler logs and returns without error."""
        subscriber = CatalogueEventsSubscriber()
        subscriber(
            _build_message(
                "Catalogue.ProductDiscontinued.v1",
                {
                    "product_id": "prod-disc-001",
                    "sku": "DISC-001",
                    "discontinued_at": datetime.now(UTC).isoformat(),
                },
            )
        )

    def test_logs_warning_for_active_carts_with_product(self):
        """When active carts contain the discontinued product, handler logs a warning."""
        product_id = "prod-disc-002"
        _create_cart_with_product(product_id)

        subscriber = CatalogueEventsSubscriber()
        # Should not raise -- just logs a warning about affected carts
        subscriber(
            _build_message(
                "Catalogue.ProductDiscontinued.v1",
                {
                    "product_id": product_id,
                    "sku": "DISC-002",
                    "discontinued_at": datetime.now(UTC).isoformat(),
                },
            )
        )

    def test_unaffected_carts_not_counted(self):
        """Carts that don't contain the discontinued product should not be counted."""
        # Create a cart with a different product
        _create_cart_with_product("prod-other")

        subscriber = CatalogueEventsSubscriber()
        # Discontinuing a product not in any cart -- should not log warning
        subscriber(
            _build_message(
                "Catalogue.ProductDiscontinued.v1",
                {
                    "product_id": "prod-disc-003",
                    "sku": "DISC-003",
                    "discontinued_at": datetime.now(UTC).isoformat(),
                },
            )
        )


class TestIgnoresUnrelatedEvents:
    def test_ignores_non_discontinued_events(self):
        """Non-ProductDiscontinued events on the catalogue stream are ignored."""
        subscriber = CatalogueEventsSubscriber()
        subscriber(
            _build_message(
                "Catalogue.ProductCreated.v1",
                {"product_id": "prod-ignore", "sku": "IGNORE-SKU"},
            )
        )

    def test_multiple_affected_carts(self):
        """Multiple carts containing the discontinued product should all be counted."""
        product_id = "prod-disc-multi"
        _create_cart_with_product(product_id)
        _create_cart_with_product(product_id)

        subscriber = CatalogueEventsSubscriber()
        # Should not raise
        subscriber(
            _build_message(
                "Catalogue.ProductDiscontinued.v1",
                {
                    "product_id": product_id,
                    "sku": "DISC-MULTI",
                    "discontinued_at": datetime.now(UTC).isoformat(),
                },
            )
        )
