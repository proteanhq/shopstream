"""Application tests for fulfillment creation via domain.process()."""

import json

from fulfillment.fulfillment.creation import CreateFulfillment
from fulfillment.fulfillment.fulfillment import Fulfillment, FulfillmentStatus
from protean import current_domain


def _items_json():
    return json.dumps(
        [
            {"order_item_id": "oi-1", "product_id": "prod-1", "sku": "SKU-001", "quantity": 2},
            {"order_item_id": "oi-2", "product_id": "prod-2", "sku": "SKU-002", "quantity": 1},
        ]
    )


def _create_fulfillment(**overrides):
    defaults = {
        "order_id": "ord-001",
        "customer_id": "cust-001",
        "items": _items_json(),
    }
    defaults.update(overrides)
    command = CreateFulfillment(**defaults)
    return current_domain.process(command, asynchronous=False)


class TestCreateFulfillmentFlow:
    def test_returns_fulfillment_id(self):
        ff_id = _create_fulfillment()
        assert ff_id is not None

    def test_persists_fulfillment(self):
        ff_id = _create_fulfillment()
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert str(ff.id) == ff_id

    def test_sets_order_id(self):
        ff_id = _create_fulfillment(order_id="ord-999")
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert str(ff.order_id) == "ord-999"

    def test_sets_status_pending(self):
        ff_id = _create_fulfillment()
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert ff.status == FulfillmentStatus.PENDING.value

    def test_creates_items(self):
        ff_id = _create_fulfillment()
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert len(ff.items) == 2

    def test_sets_warehouse_id(self):
        ff_id = _create_fulfillment(warehouse_id="wh-001")
        ff = current_domain.repository_for(Fulfillment).get(ff_id)
        assert str(ff.warehouse_id) == "wh-001"
