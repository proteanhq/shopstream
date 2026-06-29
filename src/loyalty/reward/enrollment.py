"""Enroll a customer into the loyalty program."""

from protean.fields import String
from protean.utils.globals import current_domain
from protean.utils.mixins import handle

from loyalty.domain import loyalty
from loyalty.reward.reward_account import RewardAccount


@loyalty.command(part_of="RewardAccount")
class EnrollRewardAccount:
    customer_id = String(required=True, max_length=255)
    member_code = String(max_length=12)


@loyalty.command_handler(part_of=RewardAccount)
class EnrollRewardAccountHandler:
    @handle(EnrollRewardAccount)
    def enroll(self, command: EnrollRewardAccount):
        account = RewardAccount.enroll(
            customer_id=command.customer_id,
            member_code=command.member_code or None,
        )
        current_domain.repository_for(RewardAccount).add(account)
        return account.id
