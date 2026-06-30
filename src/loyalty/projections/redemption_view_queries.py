"""Queries for the RedemptionView projection."""

from protean import read
from protean.fields import Identifier
from protean.utils.globals import current_domain

from loyalty.domain import loyalty
from loyalty.projections.redemption_view import RedemptionView


@loyalty.query(part_of=RedemptionView)
class GetRedemption:
    redemption_id = Identifier(required=True)


@loyalty.query_handler(part_of=RedemptionView)
class RedemptionViewQueryHandler:
    @read(GetRedemption)
    def get_redemption(self, query):
        return current_domain.view_for(RedemptionView).get(query.redemption_id)
