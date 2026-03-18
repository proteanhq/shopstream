# Reviews Domain

Product reviews, ratings, moderation, voting, reporting, seller replies.

## Domain Composition Root

`domain.py` — `reviews = Domain(name="reviews")`

All elements register via `@reviews.<element_type>` decorators.

## Configuration

`domain.toml` — PostgreSQL database, Redis broker, Message DB event store. Environment overlays for test (`reviews_test` DB) and production (`reviews` DB, async events). CQRS (not event sourced).

## Aggregate: Review

**File:** `review/review.py`

Root fields: `product_id`, `variant_id`, `customer_id`, `order_id`, `rating` (Rating VO), `title`, `body`, `pros` (JSON text), `cons` (JSON text), `images` (HasMany ReviewImage), `verified_purchase`, `status` (ReviewStatus enum), `moderation_notes`, `votes` (HasMany HelpfulVote), `helpful_count`, `unhelpful_count`, `report_count`, `reported_reasons` (JSON text), `reply` (HasMany SellerReply), `is_edited`, `edited_at`, `created_at`, `updated_at`.

### Enums
- `ReviewStatus`: Pending, Published, Rejected, Removed (state machine)
- `VoteType`: Helpful, Unhelpful
- `ReportReason`: Spam, Offensive, Irrelevant, Fake, Other
- `ModerationAction`: Approve, Reject

### State Machine
```
PENDING  → PUBLISHED | REJECTED
REJECTED → PENDING  (re-submit after edit)
PUBLISHED → REMOVED
REMOVED  → (terminal)
```

### Value Objects (part_of="Review")
- `Rating` — score (Integer, 1-5), invariant enforces range

### Entities (part_of="Review")
- `ReviewImage` — url, alt_text, display_order
- `HelpfulVote` — customer_id, vote_type, voted_at
- `SellerReply` — seller_id, body, replied_at

### Invariants
- `images_cannot_exceed_maximum` — max 5 images
- `at_most_one_seller_reply` — max 1 reply
- `body_minimum_length` — body must be at least 20 chars
- `title_must_not_be_empty` — title cannot be whitespace-only

### Aggregate Methods
| Method | Behavior |
|--------|----------|
| `Review.submit(...)` | Class method, creates review in PENDING, raises `ReviewSubmitted` |
| `edit(...)` | Partial update via `_UNSET` sentinel, only PENDING/REJECTED, uses `atomic_change`, raises `ReviewEdited`. Re-submits rejected reviews to PENDING. |
| `approve(moderator_id, notes?)` | PENDING → PUBLISHED, raises `ReviewApproved` |
| `reject(moderator_id, reason)` | PENDING → REJECTED, raises `ReviewRejected` |
| `vote(customer_id, vote_type)` | No self-vote, no duplicate, raises `HelpfulVoteRecorded` |
| `report(customer_id, reason, detail?)` | No self-report, tracks in JSON, raises `ReviewReported` |
| `remove(removed_by, reason)` | PUBLISHED → REMOVED, raises `ReviewRemoved` |
| `add_seller_reply(seller_id, body)` | Only on PUBLISHED, max 1 reply, raises `SellerReplyAdded` |

## Events

**File:** `review/events.py` — All versioned (`__version__ = "v1"`), past tense names.

`ReviewSubmitted`, `ReviewEdited`, `ReviewApproved`, `ReviewRejected`, `HelpfulVoteRecorded`, `ReviewReported`, `ReviewRemoved`, `SellerReplyAdded`

## Commands & Handlers

One file per use case, command + handler in same file:

| File | Command | Handler |
|------|---------|---------|
| `review/submission.py` | `SubmitReview` | `SubmitReviewHandler` — one-per-customer-per-product check (excludes removed), verified purchase lookup from `VerifiedPurchases` projection |
| `review/editing.py` | `EditReview` | `EditReviewHandler` — customer ownership check, partial update, re-submits rejected |
| `review/moderation.py` | `ModerateReview` | `ModerateReviewHandler` — approve or reject, reason required for rejection |
| `review/voting.py` | `VoteOnReview` | `VoteOnReviewHandler` — delegates to aggregate (self-vote/duplicate guards) |
| `review/reporting.py` | `ReportReview` | `ReportReviewHandler` — delegates to aggregate (self-report guard) |
| `review/removal.py` | `RemoveReview` | `RemoveReviewHandler` — delegates to aggregate (PUBLISHED-only guard) |
| `review/reply.py` | `AddSellerReply` | `AddSellerReplyHandler` — delegates to aggregate (PUBLISHED-only, max-1 guard) |

Handler pattern: load aggregate from repo → call aggregate method → `repo.add(review)` → return ID if creation.

## Cross-Domain Integration

**File:** `review/ordering_subscriber.py`

`@reviews.subscriber(broker="global", stream="ordering::order")` — receives raw dict payloads (ACL pattern).

Subscriber `OrderDeliveredSubscriber` — parses the payload's `items` JSON and creates one `VerifiedPurchases` record per product, populating the `VerifiedPurchases` projection used for verified purchase checks during review submission.

## Projections

**Directory:** `projections/`

| File | Projection | Projector | Events Handled |
|------|-----------|-----------|----------------|
| `product_reviews.py` | `ProductReviews` | `ProductReviewsProjector` | ReviewApproved (create), HelpfulVoteRecorded, ReviewRemoved (delete), SellerReplyAdded |
| `product_rating.py` | `ProductRating` | `ProductRatingProjector` | ReviewApproved (add to distribution), ReviewRemoved (subtract from distribution) |
| `customer_reviews.py` | `CustomerReviews` | `CustomerReviewsProjector` | ReviewSubmitted (create), ReviewEdited, ReviewApproved/Rejected/Removed (status updates) |
| `moderation_queue.py` | `ModerationQueue` | `ModerationQueueProjector` | ReviewSubmitted (add), ReviewApproved/Rejected (remove), ReviewReported (update/re-add with enrichment), ReviewRemoved (remove) |
| `verified_purchases.py` | `VerifiedPurchases` | — | Populated by `OrderingEventsHandler` (cross-domain) |
| `review_detail.py` | `ReviewDetail` | `ReviewDetailProjector` | All 8 events — full detail view of a single review |

Projector pattern:
```python
@reviews.projector(projector_for=ProductReviews, aggregates=[Review])
class ProductReviewsProjector:
    @on(ReviewApproved)
    def on_review_approved(self, event):
        review = current_domain.repository_for(Review).get(event.review_id)
        current_domain.repository_for(ProductReviews).add(
            ProductReviews(review_id=event.review_id, ...)
        )
```

## API

**Package:** `api/`

| File | Contents |
|------|----------|
| `api/__init__.py` | Re-exports `review_router` |
| `api/schemas.py` | Pydantic request/response models (external contract) |
| `api/routes.py` | 7 endpoints on `APIRouter(prefix="/reviews", tags=["reviews"])` |

### Endpoints
| Method | Path | Request Body | Response |
|--------|------|-------------|----------|
| POST | `/reviews` | `SubmitReviewRequest` | `ReviewIdResponse` (201) |
| PUT | `/reviews/{review_id}` | `EditReviewRequest` | `StatusResponse` |
| PUT | `/reviews/{review_id}/moderate` | `ModerateReviewRequest` | `StatusResponse` |
| POST | `/reviews/{review_id}/votes` | `VoteOnReviewRequest` | `StatusResponse` (201) |
| POST | `/reviews/{review_id}/reports` | `ReportReviewRequest` | `StatusResponse` (201) |
| PUT | `/reviews/{review_id}/remove` | `RemoveReviewRequest` | `StatusResponse` |
| POST | `/reviews/{review_id}/reply` | `AddSellerReplyRequest` | `StatusResponse` (201) |
