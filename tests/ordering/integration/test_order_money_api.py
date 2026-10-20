"""The order API takes money as a JSON number or a string and sends it back as a 4-place string."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from protean import current_domain

from ordering.api.routes import order_router
from ordering.order.order import Order

_ADDRESS = {"street": "1 Main", "city": "Town", "state": "CA", "postal_code": "90210", "country": "US"}


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(order_router)
    return TestClient(app)


def _post_order(client, unit_price, shipping_cost):
    return client.post(
        "/orders",
        json={
            "customer_id": "cust-money-api",
            "items": [
                {
                    "product_id": "prod-001",
                    "variant_id": "var-001",
                    "sku": "SKU-001",
                    "title": "Widget",
                    "quantity": 2,
                    "unit_price": unit_price,
                }
            ],
            "shipping_address": _ADDRESS,
            "billing_address": _ADDRESS,
            "shipping_cost": shipping_cost,
        },
    )


class TestOrderMoneyIn:
    @pytest.mark.parametrize(("unit_price", "shipping_cost"), [(19.99, 5.0), ("19.99", "5"), ("19.9900", "5.0000")])
    def test_number_and_string_amounts_price_the_order_the_same(self, client, unit_price, shipping_cost):
        response = _post_order(client, unit_price, shipping_cost)
        assert response.status_code == 201

        order = current_domain.repository_for(Order).get(response.json()["order_id"])
        assert str(order.items[0].unit_price) == "19.9900"
        assert str(order.pricing.grand_total) == "44.9800"

    @pytest.mark.parametrize("unit_price", ["19.99001", "19.99000001", "123456789012.00001"])
    def test_unit_price_with_a_fifth_place_is_rejected(self, client, unit_price):
        response = _post_order(client, unit_price, 5.0)
        assert response.status_code == 422


class TestOrderMoneyOut:
    def test_order_detail_sends_money_as_4_place_strings(self, client):
        order_id = _post_order(client, 19.99, 5.0).json()["order_id"]

        response = client.get(f"/orders/{order_id}")

        assert response.status_code == 200
        body = response.json()
        assert (body["subtotal"], body["shipping_cost"], body["grand_total"]) == ("39.9800", "5.0000", "44.9800")

    def test_order_summary_sends_grand_total_as_a_4_place_string(self, client):
        order_id = _post_order(client, 19.99, 5.0).json()["order_id"]

        response = client.get(f"/orders/{order_id}/summary")

        assert response.status_code == 200
        assert response.json()["grand_total"] == "44.9800"

    @pytest.mark.parametrize("model", ["OrderDetailResponse", "OrderSummaryResponse"])
    def test_openapi_publishes_grand_total_as_a_string(self, client, model):
        properties = client.app.openapi()["components"]["schemas"][model]["properties"]
        assert properties["grand_total"]["anyOf"] == [{"type": "string"}, {"type": "null"}]
