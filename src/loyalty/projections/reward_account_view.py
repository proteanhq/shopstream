"""RewardAccountView — a database-backed read model of each reward account."""

from protean.core.projector import on
from protean.fields import DateTime, Identifier, Integer, String
from protean.utils.globals import current_domain

from loyalty.domain import loyalty
from loyalty.reward.events import (
    PointsEarned,
    PointsRedeemed,
    RewardAccountClosed,
    RewardAccountEnrolled,
)
from loyalty.reward.reward_account import RewardAccount


@loyalty.projection
class RewardAccountView:
    account_id = Identifier(identifier=True, required=True)
    customer_id = String(required=True)
    member_code = String()
    tier = String()
    status = String()
    points_balance = Integer(default=0)
    lifetime_points = Integer(default=0)
    updated_at = DateTime()


@loyalty.projector(projector_for=RewardAccountView, aggregates=[RewardAccount])
class RewardAccountViewProjector:
    @on(RewardAccountEnrolled)
    def on_enrolled(self, event):
        current_domain.repository_for(RewardAccountView).add(
            RewardAccountView(
                account_id=event.account_id,
                customer_id=event.customer_id,
                member_code=event.member_code,
                tier=event.tier,
                status="Active",
                points_balance=0,
                lifetime_points=0,
                updated_at=event.enrolled_at,
            )
        )

    @on(PointsEarned)
    def on_earned(self, event):
        repo = current_domain.repository_for(RewardAccountView)
        view = repo.get(event.account_id)
        view.points_balance = event.balance_after
        view.lifetime_points = view.lifetime_points + event.amount
        view.updated_at = event.occurred_at
        repo.add(view)

    @on(PointsRedeemed)
    def on_redeemed(self, event):
        repo = current_domain.repository_for(RewardAccountView)
        view = repo.get(event.account_id)
        view.points_balance = event.balance_after
        view.updated_at = event.occurred_at
        repo.add(view)

    @on(RewardAccountClosed)
    def on_closed(self, event):
        repo = current_domain.repository_for(RewardAccountView)
        view = repo.get(event.account_id)
        view.status = "Closed"
        view.updated_at = event.closed_at
        repo.add(view)
