"""Low stock report — items below reorder point for purchasing alerts."""

from datetime import datetime
from typing import TypedDict

from protean.core.projector import on
from protean.exceptions import TransactionError, ValidationError
from protean.fields import Boolean, DateTime, Identifier, Integer, String
from protean.utils.globals import current_domain

from inventory.domain import inventory
from inventory.stock.events import LowStockDetected, StockReceived, StockReturned
from inventory.stock.stock import InventoryItem

_UPSERT_RETRIES = 5  # bounded reload-and-retry for the create-create race


@inventory.projection
class LowStockReport:
    inventory_item_id: str = Identifier(identifier=True, required=True)
    product_id: str = Identifier(required=True)
    variant_id: str = Identifier(required=True)
    sku: str = String(required=True)
    current_available: int = Integer(default=0)
    reorder_point: int = Integer(default=10)
    is_critical: bool = Boolean(default=False)  # True when nothing is available
    detected_at: datetime | None = DateTime()


class _LowStockCreateFields(TypedDict):
    product_id: str
    variant_id: str
    sku: str
    reorder_point: int


def _upsert_low_stock(
    item_id: str,
    *,
    current_available: int,
    detected_at: datetime,
    create_kwargs: _LowStockCreateFields,
) -> None:
    """Upsert the single LowStockReport row: update it if present, else create it.

    Concurrent movements on the same item can both miss on `get_or_none` and both try to
    CREATE. The loser's primary-key conflict surfaces at the projector's commit,
    or at `repo.add` when the winner has already committed. The projector's
    transient retry (see below) runs the handler again in a fresh UnitOfWork;
    by then the row exists and the lookup takes the update path.
    """
    repo = current_domain.repository_for(LowStockReport)
    report = repo.get_or_none(item_id)

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
#
# `TransactionError` is the conflict on PostgreSQL when both writers are still
# uncommitted; it raises at commit. `ValidationError` ("already present") is the
# same conflict when the other row is already visible: always on the memory
# adapter, and on PostgreSQL once the winner has committed, raised at `repo.add`.
# With `TransactionError` alone the memory-mode race test fails. The cost: a genuine `ValidationError`
# in any of these handlers is also retried 5 times before it surfaces.
@inventory.projector(
    projector_for=LowStockReport,
    aggregates=[InventoryItem],
    retries=_UPSERT_RETRIES,
    backoff="fixed",
    retry_exceptions=[TransactionError, ValidationError],
    idempotent=True,
)
class LowStockReportProjector:
    @on(LowStockDetected)
    def on_low_stock_detected(self, event: LowStockDetected) -> None:
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
    def on_stock_received(self, event: StockReceived) -> None:
        """Remove from low stock report if restocked above threshold."""
        repo = current_domain.repository_for(LowStockReport)
        report = repo.get_or_none(event.inventory_item_id)
        if report is None:
            return  # Not in the report

        # Use event's new_available and report's stored reorder_point
        if event.new_available > report.reorder_point:
            repo.query.filter(inventory_item_id=event.inventory_item_id).delete()
        else:
            report.current_available = event.new_available
            report.is_critical = event.new_available == 0
            repo.add(report)

    @on(StockReturned)
    def on_stock_returned(self, event: StockReturned) -> None:
        """Remove from low stock report if returns bring stock above threshold."""
        repo = current_domain.repository_for(LowStockReport)
        report = repo.get_or_none(event.inventory_item_id)
        if report is None:
            return

        if event.new_available > report.reorder_point:
            repo.query.filter(inventory_item_id=event.inventory_item_id).delete()
        else:
            report.current_available = event.new_available
            report.is_critical = event.new_available == 0
            repo.add(report)
