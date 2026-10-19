"""RedemptionView — a database-backed read model tracking each redemption's progress.

Projects the Redemption aggregate's events so the API (and operators) can observe where a
redemption is in the saga: requested → points_reserved → voucher_issued → completed, or the
compensated branch.
"""

from datetime import datetime

from protean.core.projector import on
from protean.fields import DateTime, Identifier, Integer, String
from protean.utils.globals import current_domain

from loyalty.domain import loyalty
from loyalty.redemption.events import (
    PointsReserved,
    RedemptionCompensated,
    RedemptionCompleted,
    RedemptionRequested,
    VoucherIssuanceFailed,
    VoucherIssued,
)
from loyalty.redemption.redemption import Redemption


@loyalty.projection
class RedemptionView:
    redemption_id: str = Identifier(identifier=True, required=True)
    account_id: str = Identifier(required=True)
    points: int = Integer(default=0)
    reward_code: str | None = String()
    status: str | None = String()
    voucher_code: str | None = String()
    failure_reason: str | None = String()
    updated_at: datetime | None = DateTime()


@loyalty.projector(projector_for=RedemptionView, aggregates=[Redemption])
class RedemptionViewProjector:
    @on(RedemptionRequested)
    def on_requested(self, event: RedemptionRequested) -> None:
        current_domain.repository_for(RedemptionView).add(
            RedemptionView(
                redemption_id=event.redemption_id,
                account_id=event.account_id,
                points=event.points,
                reward_code=event.reward_code,
                status="requested",
                updated_at=event.requested_at,
            )
        )

    @on(PointsReserved)
    def on_points_reserved(self, event: PointsReserved) -> None:
        self._set(event.redemption_id, status="points_reserved", updated_at=event.reserved_at)

    @on(VoucherIssued)
    def on_voucher_issued(self, event: VoucherIssued) -> None:
        self._set(
            event.redemption_id,
            status="voucher_issued",
            voucher_code=event.voucher_code,
            updated_at=event.issued_at,
        )

    @on(VoucherIssuanceFailed)
    def on_voucher_failed(self, event: VoucherIssuanceFailed) -> None:
        self._set(event.redemption_id, failure_reason=event.reason, updated_at=event.failed_at)

    @on(RedemptionCompleted)
    def on_completed(self, event: RedemptionCompleted) -> None:
        self._set(event.redemption_id, status="completed", updated_at=event.completed_at)

    @on(RedemptionCompensated)
    def on_compensated(self, event: RedemptionCompensated) -> None:
        self._set(
            event.redemption_id,
            status="compensated",
            failure_reason=event.reason,
            updated_at=event.compensated_at,
        )

    def _set(self, redemption_id: str, **changes: object) -> None:
        repo = current_domain.repository_for(RedemptionView)
        view = repo.get_or_none(redemption_id)
        if view is None:
            # The create projector (on `RedemptionRequested`) has not run yet. Protean
            # now drains sync events breadth-first, so this should not happen under sync
            # processing. The skip stays as a guard against out-of-order delivery rather
            # than crashing the projector.
            return
        for field, value in changes.items():
            setattr(view, field, value)
        repo.add(view)
