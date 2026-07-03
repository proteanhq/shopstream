"""Low stock report — items below reorder point for purchasing alerts."""

from protean.core.projector import on
from protean.core.unit_of_work import UnitOfWork
from protean.exceptions import ObjectNotFoundError, TransactionError, ValidationError
from protean.fields import Boolean, DateTime, Identifier, Integer, String
from protean.utils.globals import current_domain

from inventory.domain import inventory
from inventory.stock.events import LowStockDetected, StockReceived, StockReturned
from inventory.stock.stock import InventoryItem

_UPSERT_ATTEMPTS = 10  # bounded reload-and-retry for the create-create race


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
    """Idempotent, concurrency-safe upsert of the single LowStockReport row.

    Concurrent movements on the same item can both miss on `get` and both try to
    CREATE. Doing the create in its OWN UnitOfWork makes the primary-key conflict
    surface HERE (rather than at the caller's outer commit), so we can catch it and
    reload — on the retry the row exists and we take the update path. Bounded.

    The cleaner form would be a per-projector transient retry
    (`retries=..., retry_exceptions=[TransactionError]`), but projectors reject
    those options today (proteanhq/protean#1076); this is the self-contained
    workaround until that lands.
    """
    repo = current_domain.repository_for(LowStockReport)
    for _ in range(_UPSERT_ATTEMPTS):
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

        try:
            with UnitOfWork():
                repo.add(
                    LowStockReport(
                        inventory_item_id=item_id,
                        current_available=current_available,
                        is_critical=current_available == 0,
                        detected_at=detected_at,
                        **create_kwargs,
                    )
                )
            return
        except (TransactionError, ValidationError):
            continue  # lost the create race — loop back to the update path


# `LowStockDetected` is level-triggered: every stock movement that leaves an item
# at/below its reorder point fires it, so concurrent movements on the SAME item can
# both find "no report yet" and both try to CREATE the single (inventory_item_id)
# row. The loser hits the primary key — a conflict the version (OCC) retry does NOT
# cover — which under sync event processing would abort an otherwise-valid command.
# The projector is made idempotent + concurrency-safe below.
@inventory.projector(projector_for=LowStockReport, aggregates=[InventoryItem])
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
