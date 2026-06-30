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
    CampaignIdResponse,
    CampaignResponse,
    EarnPointsRequest,
    EnrollRewardAccountRequest,
    LaunchCampaignRequest,
    LeaderboardEntryResponse,
    PauseCampaignRequest,
    RedeemPointsRequest,
    RedemptionIdResponse,
    RedemptionResponse,
    RequestRedemptionRequest,
    RewardAccountResponse,
    StatusResponse,
    TransferPointsRequest,
    TransferResponse,
)
from loyalty.campaign.management import (
    ActivateCampaign,
    ExpireCampaign,
    LaunchCampaign,
    PauseCampaign,
)
from loyalty.projections.campaign_catalog_queries import GetCampaign, ListCampaigns
from loyalty.projections.points_leaderboard_queries import GetLeaderboardStanding
from loyalty.projections.redemption_view_queries import GetRedemption
from loyalty.projections.reward_account_view_queries import GetRewardAccount
from loyalty.redemption.commands import RequestRedemption
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
# Campaign Endpoints (event-sourced PromoCampaign)
# ---------------------------------------------------------------------------
@loyalty_router.post("/campaigns", status_code=201, response_model=CampaignIdResponse)
async def launch_campaign(body: LaunchCampaignRequest) -> CampaignIdResponse:
    """Launch a promotional campaign (starts in 'draft')."""
    campaign_id = current_domain.process(
        LaunchCampaign(
            campaign_code=body.campaign_code,
            name=body.name,
            discount_type=body.discount_type,
            discount_value=body.discount_value,
            starts_on=body.starts_on,
            ends_on=body.ends_on,
        ),
        asynchronous=False,
    )
    return CampaignIdResponse(campaign_id=str(campaign_id))


@loyalty_router.post("/campaigns/{campaign_id}/activate", response_model=StatusResponse)
async def activate_campaign(campaign_id: str) -> StatusResponse:
    """Activate a draft or paused campaign."""
    current_domain.process(ActivateCampaign(campaign_id=campaign_id), asynchronous=False)
    return StatusResponse()


@loyalty_router.post("/campaigns/{campaign_id}/pause", response_model=StatusResponse)
async def pause_campaign(campaign_id: str, body: PauseCampaignRequest) -> StatusResponse:
    """Pause an active campaign."""
    current_domain.process(PauseCampaign(campaign_id=campaign_id, reason=body.reason), asynchronous=False)
    return StatusResponse()


@loyalty_router.post("/campaigns/{campaign_id}/expire", response_model=StatusResponse)
async def expire_campaign(campaign_id: str) -> StatusResponse:
    """Expire a campaign (terminal)."""
    current_domain.process(ExpireCampaign(campaign_id=campaign_id), asynchronous=False)
    return StatusResponse()


# ---------------------------------------------------------------------------
# Redemption Endpoints (kicks off the RedemptionSaga)
# ---------------------------------------------------------------------------
@loyalty_router.post("/redemptions", status_code=201, response_model=RedemptionIdResponse)
async def request_redemption(body: RequestRedemptionRequest) -> RedemptionIdResponse:
    """Request a points-for-voucher redemption.

    Raises `RedemptionRequested`; the `RedemptionSaga` (under the loyalty engine) then reserves
    points, issues the voucher, and either completes or compensates (refunds the points).
    """
    redemption_id = current_domain.process(
        RequestRedemption(
            account_id=body.account_id,
            points=body.points,
            reward_code=body.reward_code,
        ),
        asynchronous=False,
    )
    return RedemptionIdResponse(redemption_id=str(redemption_id))


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


@loyalty_router.get("/campaigns", response_model=list[CampaignResponse])
async def list_campaigns(status: str | None = None) -> list[CampaignResponse]:
    """List campaigns from the catalog, optionally filtered by status."""
    entries = current_domain.dispatch(ListCampaigns(status=status))
    return [CampaignResponse(**e.to_dict()) for e in entries]


@loyalty_router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(campaign_id: str) -> CampaignResponse:
    """Read a single campaign from the catalog (database-backed projection)."""
    entry = current_domain.dispatch(GetCampaign(campaign_id=campaign_id))
    if entry is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return CampaignResponse(**entry.to_dict())


@loyalty_router.get("/redemptions/{redemption_id}", response_model=RedemptionResponse)
async def get_redemption(redemption_id: str) -> RedemptionResponse:
    """Read a redemption's progress (database-backed projection)."""
    view = current_domain.dispatch(GetRedemption(redemption_id=redemption_id))
    if view is None:
        raise HTTPException(status_code=404, detail="Redemption not found")
    return RedemptionResponse(**view.to_dict())
