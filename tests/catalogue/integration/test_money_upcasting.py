"""Catalogue events stored as v1, with float prices, load as v2 ``Decimal`` events.

Each test writes a raw v1 payload to the event store and reads it back through
``to_domain_object``, which runs the upcaster chain.
"""

from decimal import Decimal

from protean import current_domain

from catalogue.product.events import TierPriceSet, VariantAdded, VariantPriceChanged

_TIME = "2025-01-01T00:00:00+00:00"


def _load_v1(event_name, data):
    stream = f"catalogue::product-{data['product_id']}"
    type_string = f"Catalogue.{event_name}.v1"
    current_domain.event_store.store._write(
        stream,
        type_string,
        data,
        {
            "headers": {"id": f"evt-{event_name}", "type": type_string, "time": _TIME, "stream": stream},
            "envelope": {"specversion": "1.0"},
            "domain": {"kind": "EVENT", "stream_category": "catalogue::product", "version": 1},
        },
    )
    messages = current_domain.event_store.store.read(stream)
    assert len(messages) == 1
    return messages[0].to_domain_object()


class TestProductEventsUpcastFromV1:
    def test_variant_added_price_becomes_a_4_place_decimal(self):
        event = _load_v1(
            "VariantAdded",
            {
                "product_id": "prod-v1",
                "variant_id": "var-v1",
                "variant_sku": "SKU-V1",
                "price_amount": 0.1 + 0.2,
                "price_currency": "USD",
                "created_at": _TIME,
            },
        )
        assert isinstance(event, VariantAdded)
        assert event.price_amount == Decimal("0.3000")

    def test_variant_price_changed_prices_become_decimals(self):
        event = _load_v1(
            "VariantPriceChanged",
            {
                "product_id": "prod-v1",
                "variant_id": "var-v1",
                "previous_price": 0.7 + 0.1,
                "new_price": 3 * 1.1,
                "currency": "USD",
            },
        )
        assert isinstance(event, VariantPriceChanged)
        assert (event.previous_price, event.new_price) == (Decimal("0.8000"), Decimal("3.3000"))

    def test_tier_price_set_price_becomes_a_decimal(self):
        event = _load_v1(
            "TierPriceSet",
            {"product_id": "prod-v1", "variant_id": "var-v1", "tier": "Gold", "price": 0.1 * 3, "currency": "USD"},
        )
        assert isinstance(event, TierPriceSet)
        assert event.price == Decimal("0.3000")
