"""Earn and redeem points on a reward account."""

from protean.fields import Identifier, Integer, String
from protean.utils.globals import current_domain
from protean.utils.mixins import handle

from loyalty.domain import loyalty
from loyalty.reward.reward_account import RewardAccount


@loyalty.command(part_of="RewardAccount")
class EarnPoints:
    account_id = Identifier(required=True)
    amount = Integer(required=True)
    reason = String(max_length=255, default="order")


@loyalty.command(part_of="RewardAccount")
class RedeemPoints:
    account_id = Identifier(required=True)
    amount = Integer(required=True)
    reason = String(max_length=255, default="redemption")


@loyalty.command_handler(part_of=RewardAccount)
class PointsHandler:
    @handle(EarnPoints)
    def earn(self, command: EarnPoints):
        repo = current_domain.repository_for(RewardAccount)
        account = repo.get(command.account_id)
        account.earn_points(command.amount, reason=command.reason)
        repo.add(account)

    @handle(RedeemPoints)
    def redeem(self, command: RedeemPoints):
        repo = current_domain.repository_for(RewardAccount)
        account = repo.get(command.account_id)
        account.redeem_points(command.amount, reason=command.reason)
        repo.add(account)
