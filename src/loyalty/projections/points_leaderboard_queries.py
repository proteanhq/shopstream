"""Queries for the cache-backed PointsLeaderboard projection.

Reads go through ``view_for`` (portable across the memory and Redis cache adapters);
``repository_for`` does not serve cache-backed projections.
"""

from protean import read
from protean.fields import Identifier
from protean.utils.globals import current_domain

from loyalty.domain import loyalty
from loyalty.projections.points_leaderboard import PointsLeaderboard


@loyalty.query(part_of=PointsLeaderboard)
class GetLeaderboardStanding:
    account_id = Identifier(required=True)


@loyalty.query_handler(part_of=PointsLeaderboard)
class PointsLeaderboardQueryHandler:
    @read(GetLeaderboardStanding)
    def get_standing(self, query):
        return current_domain.view_for(PointsLeaderboard).get(query.account_id)
