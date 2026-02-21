"""Pydantic request/response schemas for the Reviews API.

These are separate from Protean commands (anti-corruption pattern).
The API layer is the external contract; commands are internal domain concepts.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------
class ReviewImageSchema(BaseModel):
    url: str
    alt_text: str | None = None


class SubmitReviewRequest(BaseModel):
    product_id: str
    customer_id: str
    rating: int = Field(ge=1, le=5)
    title: str = Field(max_length=200)
    body: str = Field(min_length=20)
    variant_id: str | None = None
    pros: list[str] | None = None
    cons: list[str] | None = None
    images: list[ReviewImageSchema] | None = None


class EditReviewRequest(BaseModel):
    customer_id: str
    title: str | None = Field(default=None, max_length=200)
    body: str | None = Field(default=None, min_length=20)
    rating: int | None = Field(default=None, ge=1, le=5)
    pros: list[str] | None = None
    cons: list[str] | None = None


class ModerateReviewRequest(BaseModel):
    moderator_id: str
    action: str  # "Approve" or "Reject"
    reason: str | None = None


class VoteOnReviewRequest(BaseModel):
    customer_id: str
    vote_type: str  # "Helpful" or "Unhelpful"


class ReportReviewRequest(BaseModel):
    customer_id: str
    reason: str
    detail: str | None = None


class RemoveReviewRequest(BaseModel):
    removed_by: str
    reason: str


class AddSellerReplyRequest(BaseModel):
    seller_id: str
    body: str


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------
class ReviewIdResponse(BaseModel):
    review_id: str


class StatusResponse(BaseModel):
    status: str = "ok"
