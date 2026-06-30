"""FastAPI routes for the Loyalty bounded context.

Each route translates between Pydantic schemas (external contract) and the internal domain:
write operations go through commands (`current_domain.process`) or the application service
(`LoyaltyService.transfer_points`, invoked directly), and reads go through query handlers
(`current_domain.dispatch`).
"""

from fastapi import APIRouter, HTTPException
from protean.utils.globals import current_domain

from loyalty.api.schemas import (
    AccountIdResponse,
    EarnPointsRequest,
    EnrollRewardAccountRequest,
    LeaderboardEntryResponse,
    RedeemPointsRequest,
    RewardAccountResponse,
    StatusResponse,
    TransferPointsRequest,
    TransferResponse,
)
from loyalty.projections.points_leaderboard_queries import GetLeaderboardStanding
from loyalty.projections.reward_account_view_queries import GetRewardAccount
from loyalty.reward.enrollment import EnrollRewardAccount
from loyalty.reward.points import EarnPoints, RedeemPoints
from loyalty.reward.services import LoyaltyService

loyalty_router = APIRouter(prefix="/loyalty", tags=["loyalty"])


# ---------------------------------------------------------------------------
# Write Endpoints
# ---------------------------------------------------------------------------
@loyalty_router.post("/accounts", status_code=201, response_model=AccountIdResponse)
async def enroll_reward_account(body: EnrollRewardAccountRequest) -> AccountIdResponse:
    """Enrol a customer into the rewards program."""
    account_id = current_domain.process(
        EnrollRewardAccount(
            customer_id=body.customer_id,
            member_code=body.member_code,
        ),
        asynchronous=False,
    )
    return AccountIdResponse(account_id=str(account_id))


@loyalty_router.post("/accounts/{account_id}/earn", response_model=StatusResponse)
async def earn_points(account_id: str, body: EarnPointsRequest) -> StatusResponse:
    """Credit points to a reward account."""
    current_domain.process(
        EarnPoints(account_id=account_id, amount=body.amount, reason=body.reason),
        asynchronous=False,
    )
    return StatusResponse()


@loyalty_router.post("/accounts/{account_id}/redeem", response_model=StatusResponse)
async def redeem_points(account_id: str, body: RedeemPointsRequest) -> StatusResponse:
    """Redeem points from a reward account."""
    current_domain.process(
        RedeemPoints(account_id=account_id, amount=body.amount, reason=body.reason),
        asynchronous=False,
    )
    return StatusResponse()


@loyalty_router.post("/transfers", response_model=TransferResponse)
async def transfer_points(body: TransferPointsRequest) -> TransferResponse:
    """Transfer points from one account to another (via the application service)."""
    result = LoyaltyService().transfer_points(body.source_account_id, body.target_account_id, body.amount)
    return TransferResponse(**result)


# ---------------------------------------------------------------------------
# Read Endpoints
# ---------------------------------------------------------------------------
@loyalty_router.get("/accounts/{account_id}", response_model=RewardAccountResponse)
async def get_reward_account(account_id: str) -> RewardAccountResponse:
    """Read a reward account's view (database-backed projection)."""
    view = current_domain.dispatch(GetRewardAccount(account_id=account_id))
    if view is None:
        raise HTTPException(status_code=404, detail="Reward account not found")
    return RewardAccountResponse(**view.to_dict())


@loyalty_router.get("/accounts/{account_id}/points", response_model=LeaderboardEntryResponse)
async def get_points_standing(account_id: str) -> LeaderboardEntryResponse:
    """Read a customer's live points standing (cache-backed projection)."""
    entry = current_domain.dispatch(GetLeaderboardStanding(account_id=account_id))
    if entry is None:
        raise HTTPException(status_code=404, detail="No points standing for account")
    return LeaderboardEntryResponse(**entry.to_dict())
