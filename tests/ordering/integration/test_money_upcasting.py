"""Order streams written before the ``Decimal`` change rebuild with exact money.

Each test writes raw old-version payloads, with float money, straight to the
event store, the way such a stream sits there today. Loading the aggregate or
the message runs the upcaster chain, so the floats arrive as 4-place
``Decimal`` amounts. Some floats carry arithmetic error (``3 * 1.1`` is
``3.3000000000000003``) that a scale-4 field would reject without the upcaster.
"""

from decimal import Decimal

from protean import current_domain

from ordering.order.events import OrderRefunded
from ordering.order.order import Order, OrderStatus

_TIME = "2025-01-01T00:00:00+00:00"
_ADDRESS = {"street": "1 St", "city": "C", "state": "S", "postal_code": "00000", "country": "US"}


class _RawStream:
    def __init__(self, order_id):
        self.order_id = order_id
        self.stream = f"ordering::order-{order_id}"
        self.position = 0

    def write(self, event_name, version, data):
        type_string = f"Ordering.{event_name}.v{version}"
        current_domain.event_store.store._write(
            self.stream,
            type_string,
            {"order_id": self.order_id, **data},
            {
                "headers": {
                    "id": f"evt-{self.order_id}-{self.position}",
                    "type": type_string,
                    "time": _TIME,
                    "stream": self.stream,
                },
                "envelope": {"specversion": "1.0"},
                "domain": {"kind": "EVENT", "stream_category": "ordering::order", "version": version},
            },
            self.position - 1,
        )
        self.position += 1
        return self


def _order_created(version, **overrides):
    data = {
        "customer_id": "cust-v1",
        "items": [
            {
                "id": "item-001",
                "product_id": "prod-001",
                "variant_id": "var-001",
                "sku": "SKU-001",
                "title": "Widget",
                "quantity": 1,
                "unit_price": 3 * 1.1,
                "discount": 0.1 + 0.2,
                "tax_amount": 0.1 * 3,
            }
        ],
        "shipping_address": _ADDRESS,
        "billing_address": _ADDRESS,
        "subtotal": 3 * 1.1,
        "shipping_cost": 0.1 + 0.2,
        "tax_total": 0.1 * 3,
        "discount_total": 0.7 + 0.1,
        "grand_total": 3 * 1.1 + (0.1 + 0.2) + 0.1 * 3 - (0.7 + 0.1),
        "currency": "USD",
        "created_at": _TIME,
    }
    if version >= 2:
        data["order_source"] = "mobile"
    data.update(overrides)
    return data


def _assert_exact_pricing_and_items(order):
    pricing = order.pricing
    assert (
        pricing.subtotal,
        pricing.shipping_cost,
        pricing.tax_total,
        pricing.discount_total,
        pricing.grand_total,
    ) == (Decimal("3.3000"), Decimal("0.3000"), Decimal("0.3000"), Decimal("0.8000"), Decimal("3.1000"))
    assert len(order.items) == 1
    item = order.items[0]
    assert (item.unit_price, item.discount, item.tax_amount) == (
        Decimal("3.3000"),
        Decimal("0.3000"),
        Decimal("0.3000"),
    )


class TestOrderCreatedUpcastsToV3:
    def test_v1_order_rebuilds_with_decimal_pricing_and_items(self):
        _RawStream("ord-money-v1").write("OrderCreated", 1, _order_created(1))

        order = current_domain.repository_for(Order).get("ord-money-v1")

        assert order.order_source == "web"
        _assert_exact_pricing_and_items(order)

    def test_v2_order_rebuilds_with_decimal_pricing_and_items(self):
        _RawStream("ord-money-v2").write("OrderCreated", 2, _order_created(2))

        order = current_domain.repository_for(Order).get("ord-money-v2")

        assert order.order_source == "mobile"
        _assert_exact_pricing_and_items(order)

    def test_v2_event_items_hold_4_place_money_strings(self):
        # OrderDetail copies event.items as they are, so the event itself must
        # carry the rewritten item money, not only the rebuilt aggregate.
        _RawStream("ord-money-v2-items").write("OrderCreated", 2, _order_created(2))

        message = current_domain.event_store.store.read("ordering::order-ord-money-v2-items")[0]
        items = message.to_domain_object().items

        assert len(items) == 1
        assert (items[0]["unit_price"], items[0]["discount"], items[0]["tax_amount"]) == (
            "3.3000",
            "0.3000",
            "0.3000",
        )

    def test_missing_optional_pricing_stays_missing(self):
        data = _order_created(2)
        for key in ("shipping_cost", "tax_total", "discount_total"):
            del data[key]
        _RawStream("ord-money-opt").write("OrderCreated", 2, data)

        message = current_domain.event_store.store.read("ordering::order-ord-money-opt")[0]
        event = message.to_domain_object()

        assert (event.shipping_cost, event.tax_total, event.discount_total) == (None, None, None)
        assert event.subtotal == Decimal("3.3000")


class TestOrderItemEventsUpcastToV2:
    def test_v1_item_events_rebuild_with_decimal_money(self):
        (
            _RawStream("ord-money-items")
            .write("OrderCreated", 2, _order_created(2))
            .write(
                "ItemAdded",
                1,
                {
                    "item_id": "item-002",
                    "product_id": "prod-002",
                    "variant_id": "var-002",
                    "sku": "SKU-002",
                    "title": "Gadget",
                    "quantity": "2",
                    "unit_price": str(0.1 + 0.2),
                    "new_subtotal": 3 * 1.1 + 0.2,
                    "new_grand_total": 3 * 1.1 + 0.2,
                    "added_at": _TIME,
                },
            )
            .write(
                "ItemQuantityUpdated",
                1,
                {
                    "item_id": "item-002",
                    "previous_quantity": "2",
                    "new_quantity": "3",
                    "new_subtotal": 3 * 1.1 + 0.1 * 3,
                    "new_grand_total": 3 * 1.1 + 0.1 * 3,
                    "updated_at": _TIME,
                },
            )
            .write(
                "ItemRemoved",
                1,
                {
                    "item_id": "item-001",
                    "new_subtotal": 0.1 * 3,
                    "new_grand_total": 0.1 * 3,
                    "removed_at": _TIME,
                },
            )
        )

        order = current_domain.repository_for(Order).get("ord-money-items")

        assert [str(item.id) for item in order.items] == ["item-002"]
        assert order.items[0].unit_price == Decimal("0.3000")
        assert order.items[0].quantity == 3
        assert order.pricing.subtotal == Decimal("0.3000")
        assert order.pricing.grand_total == Decimal("0.3000")

        messages = current_domain.event_store.store.read("ordering::order-ord-money-items")
        item_added = [m for m in messages if m.metadata.headers.type == "Ordering.ItemAdded.v1"]
        assert len(item_added) == 1
        assert item_added[0].to_domain_object().unit_price == "0.3000"


class TestOrderPaymentEventsUpcastToV2:
    def test_v1_payment_succeeded_rebuilds_a_paid_order(self):
        (
            _RawStream("ord-money-paid")
            .write("OrderCreated", 2, _order_created(2))
            .write("OrderConfirmed", 1, {"confirmed_at": _TIME})
            .write(
                "PaymentPending",
                1,
                {"payment_id": "pay-001", "payment_method": "card", "initiated_at": _TIME},
            )
            .write(
                "PaymentSucceeded",
                1,
                {"payment_id": "pay-001", "amount": 3 * 1.1, "payment_method": "card", "paid_at": _TIME},
            )
        )

        order = current_domain.repository_for(Order).get("ord-money-paid")
        assert order.status == OrderStatus.PAID.value

        messages = current_domain.event_store.store.read("ordering::order-ord-money-paid")
        assert len(messages) == 4
        assert messages[-1].to_domain_object().amount == Decimal("3.3000")

    def test_v1_order_refunded_amount_becomes_a_decimal(self):
        _RawStream("ord-money-ref").write("OrderRefunded", 1, {"refund_amount": 100 - 99.99, "refunded_at": _TIME})

        message = current_domain.event_store.store.read("ordering::order-ord-money-ref")[0]
        event = message.to_domain_object()

        assert isinstance(event, OrderRefunded)
        assert event.refund_amount == Decimal("0.0100")
