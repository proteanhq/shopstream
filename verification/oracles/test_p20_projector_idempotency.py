"""P20 - projector idempotency under redelivery.

WHAT THIS CHECKS
    Protean delivers events to projectors at least once (a message can be
    delivered more than once: after publish-then-crash the engine re-publishes
    it). Protean dedupes on the consume side only for projectors that opt in with
    `idempotent=True`. So a projector that is not idempotent will apply the same
    event twice and corrupt its read model.

    Property P20: delivering one event N times must leave the read model in the
    same state as delivering it once.

WHY THIS CHECK IS DIFFERENT FROM "projection == fold(events)"
    The usual convergence check folds the event stream and compares it to the
    projection. If the stream contains the duplicate, BOTH sides see the
    duplicate, so they agree and the check passes even though the read model is
    wrong. That check shares the bug.

    This check does NOT share the bug: each expected value (1 review, 1
    transaction, 5 reserved) is computed by hand, independently of the event
    stream. That independence is the whole point - it can catch a bug the
    convergence check is blind to.

HOW A CASE REDELIVERS
    Each case drives the real commands, so the projector sees the event once.
    It then reads that event back from the event store and hands it to the
    projector's `_handle` (the dispatch path the engine uses) REDELIVERIES more
    times. The stored event carries its message id (`headers.id`), which is the
    key Protean's dedup looks up. An event built by hand in the test has no id,
    so it would skip the dedup and prove nothing.

STATUS
    Two kinds of protection are checked here:
    - The projectors marked `idempotent=True` rely on Protean's processed-message
      marker (proteanhq/protean#1042). Each one has a case below that redelivers
      to a handler that adds to a stored value or inserts a new row. Two more
      cases on DailyRevenueProjector check that the dedup is keyed on the
      message: a second payment on the same day still counts, and a handler
      that fails leaves no marker, so its retry applies once.
    - ProductRatingProjector is not marked. It records which reviews it has
      counted (counted_reviews) and treats a redelivered ReviewApproved as a
      no-op (ticket T0.3).

RUN (no Docker):
    .venv/bin/python -m pytest \
        verification/oracles/test_p20_projector_idempotency.py --protean-env memory -q
"""

from collections.abc import Callable
from typing import Any

import pytest
from protean import current_domain

from shared.money import to_money

pytestmark = pytest.mark.protean_bug(
    issue=1042,
    state="fixed",
    bug=(
        "No consume-side idempotency → projector double-counts. Guarded by one redelivery case per projector marked "
        "`idempotent=True`, plus ShopStream's own dedup in `ProductRatingProjector`."
    ),
)

REDELIVERIES = 3


def _stored_event(aggregate_cls: Any, aggregate_id: str, event_cls: Any) -> Any:
    """The one stored `event_cls` on the aggregate's stream, as a domain event."""
    stream = f"{aggregate_cls.meta_.stream_category}-{aggregate_id}"
    messages = [
        m for m in current_domain.event_store.store.read(stream) if m.metadata.headers.type == event_cls.__type__
    ]
    assert len(messages) == 1, f"expected one {event_cls.__name__} on {stream}, found {len(messages)}"
    event = messages[0].to_domain_object()
    # Without a message id the dedup is skipped, and a case would pass or fail
    # for the wrong reason.
    assert event._metadata.headers.id, "stored event has no message id"
    return event


def _redeliver(projector_cls: Any, event: Any, check: Callable[[], None]) -> None:
    """Run `check` after the live delivery, then again after REDELIVERIES more.

    The first run shows the live delivery reached the projector. Without it, a
    projector that never saw the live event would get its one application from
    the first redelivery and the case would still pass.
    """
    check()
    for _ in range(REDELIVERIES):
        projector_cls._handle(event)
    check()


# ---------------------------------------------------------------------------
# Reviews: guarded by hand (counted_reviews), not by the marker
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("reviews_ctx")
def test_product_rating_projector_is_idempotent_under_redelivery():
    from reviews.projections.product_rating import ProductRating, ProductRatingProjector
    from reviews.review.events import ReviewApproved
    from reviews.review.moderation import ModerateReview
    from reviews.review.review import Review
    from reviews.review.submission import SubmitReview

    assert not ProductRatingProjector.meta_.idempotent

    product_id = "prod-p20"
    review_id = current_domain.process(
        SubmitReview(
            product_id=product_id,
            customer_id="cust-p20",
            rating=5,
            title="Solid product",
            body="This held up well over months of regular use, would buy again.",
        ),
        asynchronous=False,
    )
    current_domain.process(
        ModerateReview(review_id=review_id, moderator_id="mod-1", action="Approve"),
        asynchronous=False,
    )

    repo = current_domain.repository_for(ProductRating)

    def check() -> None:
        # Independent expected value: one review was approved, so the count is 1,
        # no matter how many times the event was delivered.
        rating = repo.get(product_id)
        assert rating.total_reviews == 1
        assert rating.rating_distribution["5"] == 1

    _redeliver(ProductRatingProjector, _stored_event(Review, review_id, ReviewApproved), check)


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------


def _succeeded_payment(amount: float, idempotency_key: str) -> str:
    from payments.payment.initiation import InitiatePayment
    from payments.payment.webhook import ProcessPaymentWebhook

    payment_id = current_domain.process(
        InitiatePayment(
            order_id=f"ord-{idempotency_key}",
            customer_id="cust-p20",
            amount=amount,
            currency="USD",
            payment_method_type="credit_card",
            last4="4242",
            idempotency_key=idempotency_key,
        ),
        asynchronous=False,
    )
    current_domain.process(
        ProcessPaymentWebhook(
            payment_id=payment_id,
            gateway_transaction_id=f"txn-{payment_id}",
            gateway_status="succeeded",
        ),
        asynchronous=False,
    )
    return payment_id


def _refund(payment_id: str, amount: float) -> None:
    from payments.payment.payment import Payment
    from payments.payment.refund import ProcessRefundWebhook, RequestRefund

    current_domain.process(RequestRefund(payment_id=payment_id, amount=amount, reason="P20"), asynchronous=False)
    refund_id = str(current_domain.repository_for(Payment).get(payment_id).refunds[0].id)
    current_domain.process(
        ProcessRefundWebhook(payment_id=payment_id, refund_id=refund_id, gateway_refund_id=f"gw-{payment_id}"),
        asynchronous=False,
    )


@pytest.mark.usefixtures("payments_ctx")
def test_daily_revenue_projector_is_idempotent_under_redelivery():
    from payments.payment.events import PaymentSucceeded
    from payments.payment.payment import Payment
    from payments.projections.daily_revenue import DailyRevenue, DailyRevenueProjector

    payment_id = _succeeded_payment(75.00, "p20-revenue")
    event = _stored_event(Payment, payment_id, PaymentSucceeded)

    def check() -> None:
        record = current_domain.repository_for(DailyRevenue).get(event.succeeded_at.date().isoformat())
        assert record.transaction_count == 1
        assert record.total_revenue == to_money(75)
        assert record.net_revenue == to_money(75)

    _redeliver(DailyRevenueProjector, event, check)


@pytest.mark.usefixtures("payments_ctx")
def test_payment_status_projector_is_idempotent_under_redelivery():
    from payments.payment.events import RefundCompleted
    from payments.payment.payment import Payment
    from payments.projections.payment_status import PaymentStatusProjector, PaymentStatusView

    payment_id = _succeeded_payment(100.00, "p20-status")
    _refund(payment_id, 30.00)

    def check() -> None:
        view = current_domain.repository_for(PaymentStatusView).get(payment_id)
        assert view.total_refunded == to_money(30)
        assert view.status == "Partially_Refunded"

    _redeliver(PaymentStatusProjector, _stored_event(Payment, payment_id, RefundCompleted), check)


@pytest.mark.usefixtures("payments_ctx")
def test_daily_revenue_projector_counts_a_second_payment_on_the_same_day():
    # A dedup keyed on the handler or the day, not the message, would pass the
    # single-event cases above and drop this second payment.
    from payments.payment.events import PaymentSucceeded
    from payments.payment.payment import Payment
    from payments.projections.daily_revenue import DailyRevenue, DailyRevenueProjector

    events = [
        _stored_event(Payment, _succeeded_payment(amount, key), PaymentSucceeded)
        for amount, key in [(75.00, "p20-day-1"), (25.00, "p20-day-2")]
    ]
    date_key = events[0].succeeded_at.date().isoformat()
    if events[1].succeeded_at.date().isoformat() != date_key:
        pytest.skip("the two payments fell on either side of midnight")

    def check() -> None:
        record = current_domain.repository_for(DailyRevenue).get(date_key)
        assert record.transaction_count == 2
        assert record.total_revenue == to_money(100)

    for event in events:
        _redeliver(DailyRevenueProjector, event, check)


@pytest.mark.usefixtures("payments_ctx")
def test_daily_revenue_projector_failed_delivery_leaves_no_marker(monkeypatch):
    # The marker and the read-model write must share one transaction. If they
    # did not, a failed marker write would keep the revenue row, and the retry
    # would count the payment a second time.
    from payments.payment.events import PaymentSucceeded
    from payments.payment.payment import Payment
    from payments.projections.daily_revenue import DailyRevenue, DailyRevenueProjector

    event = _stored_event(Payment, _succeeded_payment(75.00, "p20-failed"), PaymentSucceeded)
    message_id = event._metadata.headers.id
    handler = f"{DailyRevenueProjector.__module__}.DailyRevenueProjector.on_payment_succeeded"
    date_key = event.succeeded_at.date().isoformat()
    revenue = current_domain.repository_for(DailyRevenue)
    markers = current_domain._get_processed_message_repo("default")

    # Undo the live delivery, so the next delivery is the first one.
    if not markers.is_processed(message_id, handler):
        pytest.fail(f"precondition: the live delivery marked {message_id} for {handler}")
    for marker in markers._dao.query.filter(message_id=message_id, handler=handler).all().items:
        markers._dao.delete(marker)
    revenue._dao.delete(revenue.get(date_key))

    # Protean builds a marker repository class per database provider, so the seam is
    # that class, not ProcessedMessageRepository.
    marker_repo_cls = type(markers)
    real_mark = marker_repo_cls.mark
    mark_calls: list[str] = []

    def mark_failing_once(self: Any, message_id: str, handler: str) -> None:
        mark_calls.append(message_id)
        if len(mark_calls) == 1:
            raise RuntimeError("marker write failed")
        real_mark(self, message_id, handler)

    monkeypatch.setattr(marker_repo_cls, "mark", mark_failing_once)

    with pytest.raises(RuntimeError, match="marker write failed"):
        DailyRevenueProjector._handle(event)

    assert revenue.get_or_none(date_key) is None
    assert not markers.is_processed(message_id, handler)

    DailyRevenueProjector._handle(event)  # the retry after the failure

    def check() -> None:
        assert revenue.get(date_key).transaction_count == 1

    _redeliver(DailyRevenueProjector, event, check)


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------


def _stock_item(initial_quantity: int = 100) -> str:
    from inventory.stock.initialization import InitializeStock

    return current_domain.process(
        InitializeStock(
            product_id="prod-p20",
            variant_id="var-p20",
            warehouse_id="wh-p20",
            sku="P20-SKU",
            initial_quantity=initial_quantity,
            reorder_point=10,
            reorder_quantity=50,
        ),
        asynchronous=False,
    )


def _reserved_item(quantity: int) -> str:
    from inventory.stock.reservation import ReserveStock

    item_id = _stock_item()
    current_domain.process(
        ReserveStock(inventory_item_id=item_id, order_id="ord-p20", quantity=quantity),
        asynchronous=False,
    )
    return item_id


@pytest.mark.usefixtures("inventory_ctx")
def test_product_availability_projector_is_idempotent_under_redelivery():
    from inventory.projections.product_availability import ProductAvailability, ProductAvailabilityProjector
    from inventory.stock.events import StockReserved
    from inventory.stock.stock import InventoryItem

    item_id = _reserved_item(5)

    def check() -> None:
        pa = current_domain.repository_for(ProductAvailability).get("prod-p20::var-p20")
        assert pa.total_reserved == 5
        assert pa.total_available == 95
        assert pa.total_on_hand == 100

    _redeliver(ProductAvailabilityProjector, _stored_event(InventoryItem, item_id, StockReserved), check)


@pytest.mark.usefixtures("inventory_ctx")
def test_warehouse_stock_projector_is_idempotent_under_redelivery():
    from inventory.projections.warehouse_stock import WarehouseStock, WarehouseStockProjector
    from inventory.stock.events import StockReserved
    from inventory.stock.stock import InventoryItem

    item_id = _reserved_item(5)

    def check() -> None:
        assert current_domain.repository_for(WarehouseStock).get(item_id).reserved == 5

    _redeliver(WarehouseStockProjector, _stored_event(InventoryItem, item_id, StockReserved), check)


@pytest.mark.usefixtures("inventory_ctx")
def test_inventory_level_projector_is_idempotent_under_redelivery():
    from inventory.projections.inventory_level import InventoryLevel, InventoryLevelProjector
    from inventory.stock.events import StockReserved
    from inventory.stock.stock import InventoryItem

    item_id = _reserved_item(5)

    def check() -> None:
        assert current_domain.repository_for(InventoryLevel).get(item_id).reserved == 5

    _redeliver(InventoryLevelProjector, _stored_event(InventoryItem, item_id, StockReserved), check)


@pytest.mark.usefixtures("inventory_ctx")
def test_shrinkage_report_projector_is_idempotent_under_redelivery():
    from inventory.projections.shrinkage_report import ShrinkageReport, ShrinkageReportProjector
    from inventory.stock.adjustment import AdjustStock
    from inventory.stock.events import StockAdjusted
    from inventory.stock.stock import AdjustmentType, InventoryItem

    item_id = _stock_item()
    current_domain.process(
        AdjustStock(
            inventory_item_id=item_id,
            quantity_change=-10,
            adjustment_type=AdjustmentType.SHRINKAGE.value,
            reason="P20 shrinkage",
            adjusted_by="mgr-p20",
        ),
        asynchronous=False,
    )

    def check() -> None:
        report = current_domain.repository_for(ShrinkageReport).get(item_id)
        assert report.total_adjustments == 10
        assert report.adjustment_reasons == [f"{AdjustmentType.SHRINKAGE.value}: P20 shrinkage"]

    _redeliver(ShrinkageReportProjector, _stored_event(InventoryItem, item_id, StockAdjusted), check)


@pytest.mark.usefixtures("inventory_ctx")
def test_stock_movement_log_projector_is_idempotent_under_redelivery():
    from inventory.projections.stock_movement_log import StockMovementLog, StockMovementLogProjector
    from inventory.stock.events import StockReserved
    from inventory.stock.stock import InventoryItem

    item_id = _reserved_item(5)

    def check() -> None:
        entries = current_domain.repository_for(StockMovementLog).query.filter(inventory_item_id=item_id).all().items
        assert sorted(e.event_type for e in entries) == ["StockInitialized", "StockReserved"]

    _redeliver(StockMovementLogProjector, _stored_event(InventoryItem, item_id, StockReserved), check)


@pytest.mark.usefixtures("inventory_ctx")
def test_warehouse_directory_projector_is_idempotent_under_redelivery():
    from inventory.projections.warehouse_directory import WarehouseDirectory, WarehouseDirectoryProjector
    from inventory.warehouse.events import ZoneAdded
    from inventory.warehouse.management import AddZone, CreateWarehouse
    from inventory.warehouse.warehouse import Warehouse

    warehouse_id = current_domain.process(
        CreateWarehouse(
            name="P20 Warehouse",
            address={
                "street": "100 Industrial Blvd",
                "city": "Chicago",
                "state": "IL",
                "postal_code": "60601",
                "country": "US",
            },
            capacity=10000,
        ),
        asynchronous=False,
    )
    current_domain.process(
        AddZone(warehouse_id=warehouse_id, zone_name="Cold Storage", zone_type="Cold"),
        asynchronous=False,
    )

    def check() -> None:
        assert current_domain.repository_for(WarehouseDirectory).get(warehouse_id).zone_count == 1

    _redeliver(WarehouseDirectoryProjector, _stored_event(Warehouse, warehouse_id, ZoneAdded), check)


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------

_ADDRESS = {"street": "123 Main", "city": "Town", "state": "CA", "postal_code": "90210", "country": "US"}


def _order() -> str:
    from ordering.order.creation import CreateOrder

    return current_domain.process(
        CreateOrder(
            customer_id="cust-p20",
            items=[
                {
                    "product_id": "prod-001",
                    "variant_id": "var-001",
                    "sku": "SKU-001",
                    "title": "Widget",
                    "quantity": 2,
                    "unit_price": 25.0,
                }
            ],
            shipping_address=_ADDRESS,
            billing_address=_ADDRESS,
            subtotal=50.0,
            grand_total=55.0,
        ),
        asynchronous=False,
    )


def _order_with_added_item() -> str:
    from ordering.order.modification import AddItem

    order_id = _order()
    current_domain.process(
        AddItem(
            order_id=order_id,
            product_id="prod-002",
            variant_id="var-002",
            sku="SKU-002",
            title="Gadget",
            quantity=1,
            unit_price=10.0,
        ),
        asynchronous=False,
    )
    return order_id


@pytest.mark.usefixtures("ordering_ctx")
def test_daily_order_stats_projector_is_idempotent_under_redelivery():
    from ordering.order.events import OrderCreated
    from ordering.order.order import Order
    from ordering.projections.daily_order_stats import DailyOrderStats, DailyOrderStatsProjector

    order_id = _order()
    event = _stored_event(Order, order_id, OrderCreated)

    def check() -> None:
        stats = current_domain.repository_for(DailyOrderStats).get(event.created_at.date().isoformat())
        assert stats.orders_created == 1
        assert stats.total_revenue == to_money(55)

    _redeliver(DailyOrderStatsProjector, event, check)


@pytest.mark.usefixtures("ordering_ctx")
def test_order_summary_projector_is_idempotent_under_redelivery():
    from ordering.order.events import ItemAdded
    from ordering.order.order import Order
    from ordering.projections.order_summary import OrderSummary, OrderSummaryProjector

    order_id = _order_with_added_item()

    def check() -> None:
        assert current_domain.repository_for(OrderSummary).get(order_id).item_count == 2

    _redeliver(OrderSummaryProjector, _stored_event(Order, order_id, ItemAdded), check)


@pytest.mark.usefixtures("ordering_ctx")
def test_order_detail_projector_is_idempotent_under_redelivery():
    from ordering.order.events import ItemAdded
    from ordering.order.order import Order
    from ordering.projections.order_detail import OrderDetail, OrderDetailProjector

    order_id = _order_with_added_item()

    def check() -> None:
        items = current_domain.repository_for(OrderDetail).get(order_id).items
        assert sorted(i["sku"] for i in items) == ["SKU-001", "SKU-002"]

    _redeliver(OrderDetailProjector, _stored_event(Order, order_id, ItemAdded), check)


@pytest.mark.usefixtures("ordering_ctx")
def test_order_timeline_projector_is_idempotent_under_redelivery():
    from ordering.order.events import OrderCreated
    from ordering.order.order import Order
    from ordering.projections.order_timeline import OrderTimeline, OrderTimelineProjector

    order_id = _order()

    def check() -> None:
        entries = current_domain.repository_for(OrderTimeline).query.filter(order_id=order_id).all().items
        assert [e.event_type for e in entries] == ["OrderCreated"]

    _redeliver(OrderTimelineProjector, _stored_event(Order, order_id, OrderCreated), check)


@pytest.mark.usefixtures("ordering_ctx")
def test_cart_view_projector_is_idempotent_under_redelivery():
    from ordering.cart.cart import ShoppingCart
    from ordering.cart.events import CartItemAdded
    from ordering.cart.items import AddToCart
    from ordering.cart.management import CreateCart
    from ordering.projections.cart_view import CartView, CartViewProjector

    cart_id = current_domain.process(CreateCart(customer_id="cust-p20"), asynchronous=False)
    current_domain.process(
        AddToCart(cart_id=cart_id, product_id="prod-001", variant_id="var-001", quantity=2),
        asynchronous=False,
    )

    def check() -> None:
        view = current_domain.repository_for(CartView).get(cart_id)
        assert view.item_count == 1
        assert [i["quantity"] for i in view.items] == [2]

    _redeliver(CartViewProjector, _stored_event(ShoppingCart, cart_id, CartItemAdded), check)


# ---------------------------------------------------------------------------
# Fulfillment
# ---------------------------------------------------------------------------


def _shipped_fulfillment() -> str:
    from fulfillment.fulfillment.creation import CreateFulfillment
    from fulfillment.fulfillment.fulfillment import Fulfillment
    from fulfillment.fulfillment.packing import GenerateShippingLabel, RecordPacking
    from fulfillment.fulfillment.picking import AssignPicker, CompletePickList, RecordItemPicked
    from fulfillment.fulfillment.shipping import RecordHandoff

    ff_id = current_domain.process(
        CreateFulfillment(
            order_id="ord-p20",
            customer_id="cust-p20",
            items=[{"order_item_id": "oi-1", "product_id": "prod-1", "sku": "SKU-001", "quantity": 1}],
        ),
        asynchronous=False,
    )
    current_domain.process(AssignPicker(fulfillment_id=ff_id, picker_name="Alice"), asynchronous=False)
    item_id = str(current_domain.repository_for(Fulfillment).get(ff_id).items[0].id)
    current_domain.process(
        RecordItemPicked(fulfillment_id=ff_id, item_id=item_id, pick_location="A-1"), asynchronous=False
    )
    current_domain.process(CompletePickList(fulfillment_id=ff_id), asynchronous=False)
    current_domain.process(
        RecordPacking(fulfillment_id=ff_id, packed_by="Bob", packages=[{"weight": 1.0}]), asynchronous=False
    )
    current_domain.process(
        GenerateShippingLabel(
            fulfillment_id=ff_id,
            label_url="https://labels.example.com/p20.pdf",
            carrier="FakeCarrier",
            service_level="Standard",
        ),
        asynchronous=False,
    )
    current_domain.process(RecordHandoff(fulfillment_id=ff_id, tracking_number="TRACK-P20"), asynchronous=False)
    return ff_id


@pytest.mark.usefixtures("fulfillment_ctx")
def test_daily_shipments_projector_is_idempotent_under_redelivery():
    from fulfillment.fulfillment.events import ShipmentHandedOff
    from fulfillment.fulfillment.fulfillment import Fulfillment
    from fulfillment.projections.daily_shipments import DailyShipmentsProjector, DailyShipmentsView

    ff_id = _shipped_fulfillment()
    event = _stored_event(Fulfillment, ff_id, ShipmentHandedOff)

    def check() -> None:
        view = current_domain.repository_for(DailyShipmentsView).get(event.shipped_at.strftime("%Y-%m-%d"))
        assert view.total_shipped == 1
        assert view.total_created == 1

    _redeliver(DailyShipmentsProjector, event, check)


@pytest.mark.usefixtures("fulfillment_ctx")
def test_delivery_performance_projector_is_idempotent_under_redelivery():
    from fulfillment.fulfillment.events import ShipmentHandedOff
    from fulfillment.fulfillment.fulfillment import Fulfillment
    from fulfillment.projections.delivery_performance import DeliveryPerformanceProjector, DeliveryPerformanceView

    ff_id = _shipped_fulfillment()
    event = _stored_event(Fulfillment, ff_id, ShipmentHandedOff)

    def check() -> None:
        record_id = f"{event.carrier}-{event.shipped_at.strftime('%Y-%m-%d')}"
        assert current_domain.repository_for(DeliveryPerformanceView).get(record_id).total_shipments == 1

    _redeliver(DeliveryPerformanceProjector, event, check)


@pytest.mark.usefixtures("fulfillment_ctx")
def test_shipment_tracking_projector_is_idempotent_under_redelivery():
    from fulfillment.fulfillment.events import TrackingEventReceived
    from fulfillment.fulfillment.fulfillment import Fulfillment
    from fulfillment.fulfillment.tracking import UpdateTrackingEvent
    from fulfillment.projections.shipment_tracking import ShipmentTrackingProjector, ShipmentTrackingView

    ff_id = _shipped_fulfillment()
    current_domain.process(
        UpdateTrackingEvent(fulfillment_id=ff_id, status="in_transit", location="Hub"), asynchronous=False
    )

    def check() -> None:
        events = current_domain.repository_for(ShipmentTrackingView).get(ff_id).events
        assert [(e["status"], e["location"]) for e in events] == [("in_transit", "Hub")]

    _redeliver(ShipmentTrackingProjector, _stored_event(Fulfillment, ff_id, TrackingEventReceived), check)


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------


def _product(category_id: str | None = None) -> str:
    from catalogue.product.creation import CreateProduct

    return current_domain.process(
        CreateProduct(sku="P20-001", title="P20 Product", seller_id="seller-p20", category_id=category_id),
        asynchronous=False,
    )


def _product_with_variant() -> str:
    from catalogue.product.variants import AddVariant

    product_id = _product()
    current_domain.process(
        AddVariant(product_id=product_id, variant_sku="P20-V1", base_price=29.99), asynchronous=False
    )
    return product_id


def _product_in_category() -> tuple[str, str]:
    from catalogue.category.management import CreateCategory

    category_id = current_domain.process(CreateCategory(name="P20 Category"), asynchronous=False)
    return category_id, _product(category_id)


@pytest.mark.usefixtures("catalogue_ctx")
def test_category_tree_projector_is_idempotent_under_redelivery():
    from catalogue.product.events import ProductCreated
    from catalogue.product.product import Product
    from catalogue.projections.category_tree import CategoryTree, CategoryTreeProjector

    category_id, product_id = _product_in_category()

    def check() -> None:
        assert current_domain.repository_for(CategoryTree).get(category_id).product_count == 1

    _redeliver(CategoryTreeProjector, _stored_event(Product, product_id, ProductCreated), check)


@pytest.mark.usefixtures("catalogue_ctx")
def test_category_products_projector_is_idempotent_under_redelivery():
    from catalogue.product.events import ProductCreated
    from catalogue.product.product import Product
    from catalogue.projections.category_products import CategoryProducts, CategoryProductsProjector

    category_id, product_id = _product_in_category()

    def check() -> None:
        view = current_domain.repository_for(CategoryProducts).get(category_id)
        assert view.product_count == 1
        assert [p["product_id"] for p in view.products] == [product_id]

    _redeliver(CategoryProductsProjector, _stored_event(Product, product_id, ProductCreated), check)


@pytest.mark.usefixtures("catalogue_ctx")
def test_seller_catalogue_projector_is_idempotent_under_redelivery():
    from catalogue.product.events import VariantAdded
    from catalogue.product.product import Product
    from catalogue.projections.seller_catalogue import SellerCatalogue, SellerCatalogueProjector

    product_id = _product_with_variant()

    def check() -> None:
        assert current_domain.repository_for(SellerCatalogue).get(product_id).variant_count == 1

    _redeliver(SellerCatalogueProjector, _stored_event(Product, product_id, VariantAdded), check)


@pytest.mark.usefixtures("catalogue_ctx")
def test_product_card_projector_is_idempotent_under_redelivery():
    from catalogue.product.events import VariantAdded
    from catalogue.product.product import Product
    from catalogue.projections.product_card import ProductCard, ProductCardProjector

    product_id = _product_with_variant()

    def check() -> None:
        assert current_domain.repository_for(ProductCard).get(product_id).variant_count == 1

    _redeliver(ProductCardProjector, _stored_event(Product, product_id, VariantAdded), check)


@pytest.mark.usefixtures("catalogue_ctx")
def test_product_detail_projector_is_idempotent_under_redelivery():
    from catalogue.product.events import VariantAdded
    from catalogue.product.product import Product
    from catalogue.projections.product_detail import ProductDetail, ProductDetailProjector

    product_id = _product_with_variant()

    def check() -> None:
        variants = current_domain.repository_for(ProductDetail).get(product_id).variants
        assert [v["variant_sku"] for v in variants] == ["P20-V1"]

    _redeliver(ProductDetailProjector, _stored_event(Product, product_id, VariantAdded), check)


@pytest.mark.usefixtures("catalogue_ctx")
def test_price_history_projector_is_idempotent_under_redelivery():
    from catalogue.product.events import VariantPriceChanged
    from catalogue.product.product import Product
    from catalogue.product.variants import UpdateVariantPrice
    from catalogue.projections.price_history import PriceHistory, PriceHistoryProjector

    product_id = _product_with_variant()
    variant_id = current_domain.repository_for(Product).get(product_id).variants[0].id
    current_domain.process(
        UpdateVariantPrice(product_id=product_id, variant_id=variant_id, base_price=49.99), asynchronous=False
    )

    def check() -> None:
        entries = current_domain.repository_for(PriceHistory).query.filter(product_id=product_id).all().items
        assert [e.new_price for e in entries] == [to_money(49.99)]

    _redeliver(PriceHistoryProjector, _stored_event(Product, product_id, VariantPriceChanged), check)


# ---------------------------------------------------------------------------
# Notifications, Loyalty, Identity
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("notifications_ctx")
def test_notification_stats_projector_is_idempotent_under_redelivery():
    from notifications.channel import reset_channels
    from notifications.notification.events import NotificationSent
    from notifications.notification.notification import Notification, NotificationChannel, NotificationType
    from notifications.projections.notification_stats import NotificationStats, NotificationStatsProjector

    reset_channels()
    # An immediate notification is dispatched (and sent) as soon as it is saved.
    notification = Notification.create(
        recipient_id="cust-p20",
        notification_type=NotificationType.WELCOME.value,
        channel=NotificationChannel.EMAIL.value,
        subject="Welcome",
        body="Hello",
    )
    current_domain.repository_for(Notification).add(notification)
    event = _stored_event(Notification, str(notification.id), NotificationSent)

    def check() -> None:
        stat_key = f"{event.sent_at.strftime('%Y-%m-%d')}:{NotificationType.WELCOME.value}:{event.channel}"
        assert current_domain.repository_for(NotificationStats).get(stat_key).count == 1

    _redeliver(NotificationStatsProjector, event, check)


@pytest.mark.usefixtures("loyalty_ctx")
def test_reward_account_view_projector_is_idempotent_under_redelivery():
    from loyalty.projections.reward_account_view import RewardAccountView, RewardAccountViewProjector
    from loyalty.reward.enrollment import EnrollRewardAccount
    from loyalty.reward.events import PointsEarned
    from loyalty.reward.points import EarnPoints
    from loyalty.reward.reward_account import RewardAccount

    account_id = current_domain.process(EnrollRewardAccount(customer_id="cust-p20"), asynchronous=False)
    current_domain.process(EarnPoints(account_id=account_id, amount=50), asynchronous=False)

    def check() -> None:
        view = current_domain.repository_for(RewardAccountView).get(account_id)
        assert view.lifetime_points == 50
        assert view.points_balance == 50

    _redeliver(RewardAccountViewProjector, _stored_event(RewardAccount, account_id, PointsEarned), check)


@pytest.mark.usefixtures("identity_ctx")
def test_address_book_projector_is_idempotent_under_redelivery():
    from identity.customer.addresses import AddAddress
    from identity.customer.customer import Customer
    from identity.customer.events import AddressAdded
    from identity.customer.registration import RegisterCustomer
    from identity.projections.address_book import AddressBook, AddressBookProjector

    customer_id = current_domain.process(
        RegisterCustomer(external_id="EXT-P20", email="p20@example.com", first_name="Pat", last_name="Lee"),
        asynchronous=False,
    )
    current_domain.process(
        AddAddress(
            customer_id=customer_id, street="123 Main St", city="Springfield", postal_code="62701", country="US"
        ),
        asynchronous=False,
    )

    def check() -> None:
        addresses = current_domain.repository_for(AddressBook).get(customer_id).addresses
        assert [a["street"] for a in addresses] == ["123 Main St"]

    _redeliver(AddressBookProjector, _stored_event(Customer, customer_id, AddressAdded), check)
