"""Tests for the EventAudit read model — the @handle("$any") wildcard event handler.

Verifies that a single event handler with one wildcard handler method records an audit
row for every kind of InventoryItem event, without a per-event-type method.

Covers both the direct-dispatch path and the sync-command-processing path (the latter was
proteanhq/protean#1023, fixed on main: handlers_for now resolves "$any" handlers).
"""

from datetime import UTC, datetime

from protean import current_domain

from inventory.projections.event_audit import EventAudit, EventAuditHandler
from inventory.stock.events import StockInitialized
from inventory.stock.initialization import InitializeStock
from inventory.stock.receiving import ReceiveStock
from inventory.stock.reservation import ReserveStock


def _audits_for(item_id):
    return current_domain.view_for(EventAudit).query.filter(inventory_item_id=item_id).all().items


class TestEventAuditWildcardHandler:
    def test_wildcard_handler_records_audit_row_via_direct_dispatch(self):
        """The $any handler builds a uniform audit row for any event type.

        Exercises the handler the same way the async Engine path does — by invoking
        the handler with the event — so it is independent of the sync-dispatch bug.
        """
        event = StockInitialized(
            inventory_item_id="item-1",
            product_id="prod-001",
            variant_id="var-001",
            warehouse_id="wh-001",
            sku="TSHIRT-BLK-M",
            initial_quantity=100,
            reorder_point=10,
            reorder_quantity=50,
            initialized_at=datetime.now(UTC),
        )

        EventAuditHandler._handle(event)

        audits = _audits_for("item-1")
        assert len(audits) == 1
        assert audits[0].event_type == "StockInitialized"
        assert audits[0].qualified_type and "StockInitialized" in audits[0].qualified_type
        assert audits[0].recorded_at is not None

    def test_audit_populated_through_sync_command_processing(self):
        """The wildcard handler fires during sync command processing and every event from
        a command flow lands an audit row (proteanhq/protean#1023, fixed on main)."""
        item_id = current_domain.process(
            InitializeStock(
                product_id="prod-001",
                variant_id="var-001",
                warehouse_id="wh-001",
                sku="TSHIRT-BLK-M",
                initial_quantity=100,
                reorder_point=10,
                reorder_quantity=50,
            ),
            asynchronous=False,
        )
        current_domain.process(ReceiveStock(inventory_item_id=item_id, quantity=20), asynchronous=False)
        current_domain.process(
            ReserveStock(inventory_item_id=item_id, order_id="ord-001", quantity=5),
            asynchronous=False,
        )

        event_types = {a.event_type for a in _audits_for(item_id)}
        assert {"StockInitialized", "StockReceived", "StockReserved"} <= event_types
