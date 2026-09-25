"""Low stock report — items below reorder point for purchasing alerts."""

from protean.core.projector import on
from protean.exceptions import ObjectNotFoundError, TransactionError, ValidationError
from protean.fields import Boolean, DateTime, Identifier, Integer, String
from protean.utils.globals import current_domain

from inventory.domain import inventory
from inventory.stock.events import LowStockDetected, StockReceived, StockReturned
from inventory.stock.stock import InventoryItem

_UPSERT_RETRIES = 5  # bounded reload-and-retry for the create-create race


@inventory.projection
class LowStockReport:
    inventory_item_id = Identifier(identifier=True, required=True)
    product_id = Identifier(required=True)
    variant_id = Identifier(required=True)
    sku = String(required=True)
    current_available = Integer(default=0)
    reorder_point = Integer(default=10)
    is_critical = Boolean(default=False)  # available == 0
    detected_at = DateTime()


def _upsert_low_stock(item_id, *, current_available, detected_at, create_kwargs):
    """Upsert the single LowStockReport row: update it if present, else create it.

    Concurrent movements on the same item can both miss on `get` and both try to
    CREATE. The loser's primary-key conflict surfaces when the projector's
    UnitOfWork commits. The projector's transient retry (see below) runs the
    handler again in a fresh UnitOfWork; by then the row exists and the `get`
    takes the update path.
    """
    repo = current_domain.repository_for(LowStockReport)
    try:
        report = repo.get(item_id)
    except ObjectNotFoundError:
        report = None

    if report is not None:
        report.current_available = current_available
        report.is_critical = current_available == 0
        report.detected_at = detected_at
        repo.add(report)
        return

    repo.add(
        LowStockReport(
            inventory_item_id=item_id,
            current_available=current_available,
            is_critical=current_available == 0,
            detected_at=detected_at,
            **create_kwargs,
        )
    )


# `LowStockDetected` is level-triggered: every stock movement that leaves an item
# at/below its reorder point fires it, so concurrent movements on the SAME item can
# both find "no report yet" and both try to CREATE the single (inventory_item_id)
# row. The loser hits the primary key, a conflict the version (OCC) retry does NOT
# cover, which under sync event processing would abort an otherwise-valid command.
#
# The fix is a per-projector transient retry on that conflict. A nested
# UnitOfWork inside the handler cannot catch it: nesting joins the handler's own
# UnitOfWork, so the conflict only raises at the handler's commit.
@inventory.projector(
    projector_for=LowStockReport,
    aggregates=[InventoryItem],
    retries=_UPSERT_RETRIES,
    backoff="fixed",
    retry_exceptions=[TransactionError, ValidationError],
)
class LowStockReportProjector:
    @on(LowStockDetected)
    def on_low_stock_detected(self, event):
        _upsert_low_stock(
            event.inventory_item_id,
            current_available=event.current_available,
            detected_at=event.detected_at,
            create_kwargs={
                "product_id": event.product_id,
                "variant_id": event.variant_id,
                "sku": event.sku,
                "reorder_point": event.reorder_point,
            },
        )

    @on(StockReceived)
    def on_stock_received(self, event):
        """Remove from low stock report if restocked above threshold."""
        repo = current_domain.repository_for(LowStockReport)
        try:
            report = repo.get(event.inventory_item_id)
        except Exception:
            return  # Not in the report

        # Use event's new_available and report's stored reorder_point
        if event.new_available > report.reorder_point:
            repo.query.filter(inventory_item_id=event.inventory_item_id).delete()
        else:
            report.current_available = event.new_available
            report.is_critical = event.new_available == 0
            repo.add(report)

    @on(StockReturned)
    def on_stock_returned(self, event):
        """Remove from low stock report if returns bring stock above threshold."""
        repo = current_domain.repository_for(LowStockReport)
        try:
            report = repo.get(event.inventory_item_id)
        except Exception:
            return

        if event.new_available > report.reorder_point:
            repo.query.filter(inventory_item_id=event.inventory_item_id).delete()
        else:
            report.current_available = event.new_available
            report.is_critical = event.new_available == 0
            repo.add(report)
