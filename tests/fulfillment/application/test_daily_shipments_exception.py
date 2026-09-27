"""DailyShipmentsView projector: a miss on the day's row creates a fresh view.

Covers the miss branch in _get_or_create, where `get_or_none` finds no row for
the date and a new DailyShipmentsView is built instead. Uses the real repository.
"""

from datetime import UTC, datetime

from protean import current_domain

from fulfillment.fulfillment.events import (
    DeliveryConfirmed,
    DeliveryException,
    FulfillmentCreated,
    ShipmentHandedOff,
)
from fulfillment.projections.daily_shipments import (
    DailyShipmentsProjector,
    DailyShipmentsView,
    _get_or_create,
)

_DAY = datetime(2026, 2, 15, 12, 0, tzinfo=UTC)


def _saved_view():
    view = current_domain.repository_for(DailyShipmentsView).get_or_none("2026-02-15")
    assert view is not None, "Expected the projector to persist a view for 2026-02-15"
    return view


class TestDailyShipmentsGetOrCreate:
    """When no row exists for the date, _get_or_create builds a new, unsaved view."""

    def test_creates_new_view_when_not_found(self):
        view = _get_or_create("2026-02-15", _DAY)

        assert view.date == "2026-02-15"
        assert view.total_created == 0
        assert view.total_shipped == 0
        assert view.total_delivered == 0
        assert view.total_exceptions == 0
        assert view.updated_at == _DAY
        # _get_or_create does not persist; the handler does
        assert current_domain.repository_for(DailyShipmentsView).get_or_none("2026-02-15") is None

    def test_on_fulfillment_created_creates_view_when_not_found(self):
        DailyShipmentsProjector().on_fulfillment_created(
            FulfillmentCreated(
                fulfillment_id="ful-new-001",
                order_id="ord-001",
                customer_id="cust-001",
                items=[],
                item_count=2,
                created_at=_DAY,
            )
        )
        assert _saved_view().total_created == 1

    def test_on_shipment_handed_off_creates_view_when_not_found(self):
        DailyShipmentsProjector().on_shipment_handed_off(
            ShipmentHandedOff(
                fulfillment_id="ful-new-002",
                order_id="ord-002",
                carrier="UPS",
                tracking_number="1Z999AA10123456784",
                shipped_at=_DAY,
            )
        )
        assert _saved_view().total_shipped == 1

    def test_on_delivery_confirmed_creates_view_when_not_found(self):
        DailyShipmentsProjector().on_delivery_confirmed(
            DeliveryConfirmed(
                fulfillment_id="ful-new-003",
                order_id="ord-003",
                actual_delivery=_DAY,
                delivered_at=_DAY,
            )
        )
        assert _saved_view().total_delivered == 1

    def test_on_delivery_exception_creates_view_when_not_found(self):
        DailyShipmentsProjector().on_delivery_exception(
            DeliveryException(
                fulfillment_id="ful-new-004",
                order_id="ord-004",
                reason="Address not found",
                occurred_at=_DAY,
            )
        )
        assert _saved_view().total_exceptions == 1

    def test_second_event_updates_existing_view(self):
        projector = DailyShipmentsProjector()
        for n in (1, 2):
            projector.on_delivery_exception(
                DeliveryException(
                    fulfillment_id=f"ful-upd-{n}",
                    order_id=f"ord-upd-{n}",
                    reason="Address not found",
                    occurred_at=_DAY,
                )
            )
        assert _saved_view().total_exceptions == 2
