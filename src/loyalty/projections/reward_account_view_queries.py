"""Queries for the RewardAccountView projection."""

from protean import read
from protean.fields import Identifier
from protean.utils.globals import current_domain

from loyalty.domain import loyalty
from loyalty.projections.reward_account_view import RewardAccountView


@loyalty.query(part_of=RewardAccountView)
class GetRewardAccount:
    account_id = Identifier(required=True)


@loyalty.query_handler(part_of=RewardAccountView)
class RewardAccountViewQueryHandler:
    @read(GetRewardAccount)
    def get_reward_account(self, query):
        return current_domain.view_for(RewardAccountView).get(query.account_id)
