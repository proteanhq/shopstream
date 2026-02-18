"""Integration tests for Cart API endpoints via TestClient."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from ordering.api.routes import cart_router, order_router
from ordering.cart.cart import CartStatus, ShoppingCart
from ordering.order.order import Order
from protean import current_domain


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(cart_router)
    app.include_router(order_router)
    return TestClient(app)


def _create_cart(client, customer_id="cust-cart-001"):
    """Helper: POST /carts and return the cart_id."""
    response = client.post("/carts", json={"customer_id": customer_id})
    assert response.status_code == 201
    return response.json()["cart_id"]


def _add_item(client, cart_id, product_id="prod-001", variant_id="var-001", quantity=1):
    """Helper: POST /carts/{cart_id}/items."""
    response = client.post(
        f"/carts/{cart_id}/items",
        json={
            "product_id": product_id,
            "variant_id": variant_id,
            "quantity": quantity,
        },
    )
    assert response.status_code == 200
    return response


class TestCreateCartEndpoint:
    def test_create_cart(self, client):
        cart_id = _create_cart(client)
        assert cart_id is not None

        cart = current_domain.repository_for(ShoppingCart).get(cart_id)
        assert cart.customer_id == "cust-cart-001"
        assert cart.status == CartStatus.ACTIVE.value

    def test_create_guest_cart(self, client):
        response = client.post("/carts", json={"session_id": "sess-001"})
        assert response.status_code == 201
        cart_id = response.json()["cart_id"]

        cart = current_domain.repository_for(ShoppingCart).get(cart_id)
        assert cart.session_id == "sess-001"


class TestCartItemEndpoints:
    def test_add_item_to_cart(self, client):
        cart_id = _create_cart(client)
        _add_item(client, cart_id, "prod-001", "var-001", 2)

        cart = current_domain.repository_for(ShoppingCart).get(cart_id)
        assert len(cart.items) == 1
        assert cart.items[0].quantity == 2

    def test_add_multiple_items(self, client):
        cart_id = _create_cart(client)
        _add_item(client, cart_id, "prod-001", "var-001")
        _add_item(client, cart_id, "prod-002", "var-002")

        cart = current_domain.repository_for(ShoppingCart).get(cart_id)
        assert len(cart.items) == 2

    def test_update_item_quantity(self, client):
        cart_id = _create_cart(client)
        _add_item(client, cart_id)

        cart = current_domain.repository_for(ShoppingCart).get(cart_id)
        item_id = str(cart.items[0].id)

        response = client.put(
            f"/carts/{cart_id}/items/{item_id}",
            json={"new_quantity": 5},
        )
        assert response.status_code == 200

        cart = current_domain.repository_for(ShoppingCart).get(cart_id)
        assert cart.items[0].quantity == 5

    def test_remove_item(self, client):
        cart_id = _create_cart(client)
        _add_item(client, cart_id, "prod-001", "var-001")
        _add_item(client, cart_id, "prod-002", "var-002")

        cart = current_domain.repository_for(ShoppingCart).get(cart_id)
        item_id = str(cart.items[0].id)

        response = client.delete(f"/carts/{cart_id}/items/{item_id}")
        assert response.status_code == 200

        cart = current_domain.repository_for(ShoppingCart).get(cart_id)
        assert len(cart.items) == 1


class TestCartCouponEndpoint:
    def test_apply_coupon(self, client):
        cart_id = _create_cart(client)
        response = client.post(
            f"/carts/{cart_id}/coupons",
            json={"coupon_code": "WELCOME10"},
        )
        assert response.status_code == 200

        cart = current_domain.repository_for(ShoppingCart).get(cart_id)
        assert "WELCOME10" in cart.applied_coupons


class TestCartCheckoutEndpoint:
    def test_checkout_creates_order(self, client):
        cart_id = _create_cart(client)
        _add_item(client, cart_id, "prod-001", "var-001", 2)

        response = client.post(
            f"/carts/{cart_id}/checkout",
            json={
                "shipping": {
                    "street": "123 Main",
                    "city": "Town",
                    "state": "CA",
                    "postal_code": "90210",
                    "country": "US",
                },
                "billing": {
                    "street": "123 Main",
                    "city": "Town",
                    "state": "CA",
                    "postal_code": "90210",
                    "country": "US",
                },
            },
        )
        assert response.status_code == 201
        order_id = response.json()["order_id"]
        assert order_id is not None

        # Verify order was created
        order = current_domain.repository_for(Order).get(order_id)
        assert order.customer_id == "cust-cart-001"

        # Verify cart was converted
        cart = current_domain.repository_for(ShoppingCart).get(cart_id)
        assert cart.status == CartStatus.CONVERTED.value


class TestCartAbandonEndpoint:
    def test_abandon_cart(self, client):
        cart_id = _create_cart(client)
        response = client.put(f"/carts/{cart_id}/abandon")
        assert response.status_code == 200

        cart = current_domain.repository_for(ShoppingCart).get(cart_id)
        assert cart.status == CartStatus.ABANDONED.value
