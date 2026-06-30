"""RedemptionSaga — a process manager coordinating a points-for-voucher redemption.

This is ShopStream's **second** process manager, and it deliberately exercises the parts of
Protean's saga support that the ordering `OrderCheckoutSaga` does not:

  * **dict ``correlate``** — ``{"redemption_id": "redemption_id"}`` (the dict form, mapping a
    PM field to the event field) rather than the bare-string form;
  * a **compensation** path — when the voucher cannot be issued, the saga refunds the points
    it reserved (a compensating ``EarnPoints`` command) and records the compensation;
  * explicit **``end=True``** on the terminal compensation handler (the success branch ends via
    ``mark_as_complete()`` instead, so both finalisation styles are shown).

Forward flow:
    1. RedemptionRequested → reserve points (RedeemPoints on the RewardAccount), then advance
       the Redemption to ``points_reserved`` (ReserveRedemptionPoints).
    2. PointsReserved → issue the voucher (IssueRedemptionVoucher).
    3a. VoucherIssued → complete the redemption; saga done (mark_as_complete()).
    3b. VoucherIssuanceFailed → COMPENSATE: refund the reserved points and mark the redemption
        compensated; saga done (end=True).

The saga reacts only to events on the ``loyalty::redemption`` stream and threads work to the
RewardAccount aggregate via commands. If reserving points fails (insufficient balance) nothing
was deducted, so there is nothing to compensate — the redemption is simply abandoned.
"""

import logging

from protean.exceptions import ValidationError
from protean.fields import DateTime, Identifier, Integer, String
from protean.utils.globals import current_domain
from protean.utils.mixins import handle

from loyalty.domain import loyalty
from loyalty.redemption.events import (
    PointsReserved,
    RedemptionRequested,
    VoucherIssuanceFailed,
    VoucherIssued,
)

logger = logging.getLogger(__name__)


@loyalty.process_manager(stream_categories=["loyalty::redemption"])
class RedemptionSaga:
    """Coordinates reserve → issue → confirm, compensating on voucher failure."""

    redemption_id = Identifier()
    account_id = Identifier()
    points = Integer(default=0)
    reward_code = String()
    status = String(default="new")
    voucher_code = String()
    failure_reason = String()
    started_at = DateTime()

    @handle(RedemptionRequested, start=True, correlate={"redemption_id": "redemption_id"})
    def on_requested(self, event: RedemptionRequested) -> None:
        """Step 1: reserve the points on the RewardAccount, then advance the redemption."""
        self.redemption_id = event.redemption_id
        self.account_id = event.account_id
        self.points = event.points
        self.reward_code = event.reward_code
        self.started_at = event.requested_at

        from loyalty.redemption.commands import ReserveRedemptionPoints
        from loyalty.reward.points import RedeemPoints

        try:
            current_domain.process(
                RedeemPoints(
                    account_id=event.account_id,
                    amount=event.points,
                    reason=f"redemption:{event.redemption_id}",
                ),
                asynchronous=False,
            )
        except ValidationError as exc:
            # Insufficient balance (or closed account): nothing was deducted, so there is
            # nothing to compensate. Abandon the redemption.
            self.status = "rejected"
            self.failure_reason = str(exc)
            self.mark_as_complete()
            return

        self.status = "reserving"
        current_domain.process(
            ReserveRedemptionPoints(redemption_id=event.redemption_id),
            asynchronous=False,
        )

    @handle(PointsReserved, correlate={"redemption_id": "redemption_id"})
    def on_points_reserved(self, event: PointsReserved) -> None:
        """Step 2: points are held — ask the voucher port to issue a voucher."""
        from loyalty.redemption.commands import IssueRedemptionVoucher

        self.status = "issuing_voucher"
        current_domain.process(
            IssueRedemptionVoucher(redemption_id=event.redemption_id),
            asynchronous=False,
        )

    @handle(VoucherIssued, correlate={"redemption_id": "redemption_id"})
    def on_voucher_issued(self, event: VoucherIssued) -> None:
        """Step 3a: voucher issued — confirm the redemption. Saga complete."""
        from loyalty.redemption.commands import CompleteRedemption

        self.voucher_code = event.voucher_code
        self.status = "completed"
        current_domain.process(
            CompleteRedemption(redemption_id=event.redemption_id),
            asynchronous=False,
        )
        self.mark_as_complete()

    @handle(VoucherIssuanceFailed, correlate={"redemption_id": "redemption_id"}, end=True)
    def on_voucher_failed(self, event: VoucherIssuanceFailed) -> None:
        """Step 3b: COMPENSATE — refund the reserved points and mark compensated. Saga ends."""
        from loyalty.redemption.commands import CompensateRedemption
        from loyalty.reward.points import EarnPoints

        self.status = "compensated"
        self.failure_reason = event.reason

        # Compensating action: give back the points reserved in step 1.
        current_domain.process(
            EarnPoints(
                account_id=self.account_id,
                amount=self.points,
                reason=f"redemption_refund:{event.redemption_id}",
            ),
            asynchronous=False,
        )
        current_domain.process(
            CompensateRedemption(
                redemption_id=event.redemption_id,
                refunded_points=self.points,
                reason=event.reason,
            ),
            asynchronous=False,
        )
