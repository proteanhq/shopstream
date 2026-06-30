"""Pydantic request/response schemas for the Loyalty API.

These are separate from Protean commands (anti-corruption pattern). The API layer is the
external contract; commands and the application service are internal domain concepts.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------
class EnrollRewardAccountRequest(BaseModel):
    customer_id: str
    member_code: str | None = Field(default=None, max_length=12)
    referral_code: str | None = Field(default=None, max_length=12)


class EarnPointsRequest(BaseModel):
    amount: int = Field(gt=0)
    reason: str = "order"


class RedeemPointsRequest(BaseModel):
    amount: int = Field(gt=0)
    reason: str = "redemption"


class TransferPointsRequest(BaseModel):
    source_account_id: str
    target_account_id: str
    amount: int = Field(gt=0)


class LaunchCampaignRequest(BaseModel):
    campaign_code: str = Field(max_length=20)
    name: str = Field(max_length=255)
    discount_type: str = Field(description="percentage | fixed | points_multiplier")
    discount_value: int = Field(gt=0)
    starts_on: date | None = None
    ends_on: date | None = None


class PauseCampaignRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=255)


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------
class AccountIdResponse(BaseModel):
    account_id: str


class StatusResponse(BaseModel):
    status: str = "ok"


class TransferResponse(BaseModel):
    source_balance: int
    target_balance: int


class RewardAccountResponse(BaseModel):
    account_id: str
    customer_id: str
    member_code: str | None = None
    tier: str | None = None
    status: str | None = None
    points_balance: int = 0
    lifetime_points: int = 0


class LeaderboardEntryResponse(BaseModel):
    account_id: str
    customer_id: str
    tier: str | None = None
    points_balance: int = 0


class CampaignIdResponse(BaseModel):
    campaign_id: str


class CampaignResponse(BaseModel):
    campaign_id: str
    campaign_code: str | None = None
    name: str | None = None
    discount_type: str | None = None
    discount_value: int = 0
    status: str | None = None
    starts_on: date | None = None
    ends_on: date | None = None
