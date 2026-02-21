"""FastAPI routes for the Reviews & Ratings bounded context.

Each route translates between Pydantic schemas (external contract) and
Protean commands (internal domain concepts).
"""

import json

from fastapi import APIRouter
from protean.utils.globals import current_domain

from reviews.api.schemas import (
    AddSellerReplyRequest,
    EditReviewRequest,
    ModerateReviewRequest,
    RemoveReviewRequest,
    ReportReviewRequest,
    ReviewIdResponse,
    StatusResponse,
    SubmitReviewRequest,
    VoteOnReviewRequest,
)
from reviews.review.editing import EditReview
from reviews.review.moderation import ModerateReview
from reviews.review.removal import RemoveReview
from reviews.review.reply import AddSellerReply
from reviews.review.reporting import ReportReview
from reviews.review.submission import SubmitReview
from reviews.review.voting import VoteOnReview

review_router = APIRouter(prefix="/reviews", tags=["reviews"])


@review_router.post("", status_code=201, response_model=ReviewIdResponse)
async def submit_review(body: SubmitReviewRequest) -> ReviewIdResponse:
    """Submit a new product review."""
    command = SubmitReview(
        product_id=body.product_id,
        customer_id=body.customer_id,
        rating=body.rating,
        title=body.title,
        body=body.body,
        variant_id=body.variant_id,
        pros=json.dumps(body.pros) if body.pros else None,
        cons=json.dumps(body.cons) if body.cons else None,
        images=json.dumps([img.model_dump() for img in body.images]) if body.images else None,
    )
    review_id = current_domain.process(command, asynchronous=False)
    return ReviewIdResponse(review_id=review_id)


@review_router.put("/{review_id}", response_model=StatusResponse)
async def edit_review(review_id: str, body: EditReviewRequest) -> StatusResponse:
    """Edit an existing review."""
    command = EditReview(
        review_id=review_id,
        customer_id=body.customer_id,
        title=body.title,
        body=body.body,
        rating=body.rating,
        pros=json.dumps(body.pros) if body.pros else None,
        cons=json.dumps(body.cons) if body.cons else None,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@review_router.put("/{review_id}/moderate", response_model=StatusResponse)
async def moderate_review(review_id: str, body: ModerateReviewRequest) -> StatusResponse:
    """Approve or reject a review."""
    command = ModerateReview(
        review_id=review_id,
        moderator_id=body.moderator_id,
        action=body.action,
        reason=body.reason,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@review_router.post("/{review_id}/votes", status_code=201, response_model=StatusResponse)
async def vote_on_review(review_id: str, body: VoteOnReviewRequest) -> StatusResponse:
    """Vote on whether a review is helpful."""
    command = VoteOnReview(
        review_id=review_id,
        customer_id=body.customer_id,
        vote_type=body.vote_type,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@review_router.post("/{review_id}/reports", status_code=201, response_model=StatusResponse)
async def report_review(review_id: str, body: ReportReviewRequest) -> StatusResponse:
    """Report a review for moderation."""
    command = ReportReview(
        review_id=review_id,
        customer_id=body.customer_id,
        reason=body.reason,
        detail=body.detail,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@review_router.put("/{review_id}/remove", response_model=StatusResponse)
async def remove_review(review_id: str, body: RemoveReviewRequest) -> StatusResponse:
    """Remove a published review."""
    command = RemoveReview(
        review_id=review_id,
        removed_by=body.removed_by,
        reason=body.reason,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@review_router.post("/{review_id}/reply", status_code=201, response_model=StatusResponse)
async def add_seller_reply(review_id: str, body: AddSellerReplyRequest) -> StatusResponse:
    """Add a seller reply to a review."""
    command = AddSellerReply(
        review_id=review_id,
        seller_id=body.seller_id,
        body=body.body,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()
