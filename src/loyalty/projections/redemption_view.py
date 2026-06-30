"""RedemptionView — a database-backed read model tracking each redemption's progress.

Projects the Redemption aggregate's events so the API (and operators) can observe where a
redemption is in the saga: requested → points_reserved → voucher_issued → completed, or the
compensated branch.
"""

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
    redemption_id = Identifier(identifier=True, required=True)
    account_id = Identifier(required=True)
    points = Integer(default=0)
    reward_code = String()
    status = String()
    voucher_code = String()
    failure_reason = String()
    updated_at = DateTime()


@loyalty.projector(projector_for=RedemptionView, aggregates=[Redemption])
class RedemptionViewProjector:
    @on(RedemptionRequested)
    def on_requested(self, event):
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
    def on_points_reserved(self, event):
        self._set(event.redemption_id, status="points_reserved", updated_at=event.reserved_at)

    @on(VoucherIssued)
    def on_voucher_issued(self, event):
        self._set(
            event.redemption_id,
            status="voucher_issued",
            voucher_code=event.voucher_code,
            updated_at=event.issued_at,
        )

    @on(VoucherIssuanceFailed)
    def on_voucher_failed(self, event):
        self._set(event.redemption_id, failure_reason=event.reason, updated_at=event.failed_at)

    @on(RedemptionCompleted)
    def on_completed(self, event):
        self._set(event.redemption_id, status="completed", updated_at=event.completed_at)

    @on(RedemptionCompensated)
    def on_compensated(self, event):
        self._set(
            event.redemption_id,
            status="compensated",
            failure_reason=event.reason,
            updated_at=event.compensated_at,
        )

    def _set(self, redemption_id, **changes):
        repo = current_domain.repository_for(RedemptionView)
        view = repo.get(redemption_id)
        for field, value in changes.items():
            setattr(view, field, value)
        repo.add(view)
