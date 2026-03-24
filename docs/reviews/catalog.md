# Event & Command Catalog

## DefaultOutbox (`abc.DefaultOutbox`)

## MemoryOutbox (`abc.MemoryOutbox`)

## Review (`reviews.review.review.Review`)

### Events

#### HelpfulVoteRecorded

- **Type**: `Reviews.HelpfulVoteRecorded.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| helpful_count | Integer | Yes | — |
| review_id | Identifier | Yes | min_length=1 |
| unhelpful_count | Integer | Yes | — |
| vote_type | String | Yes | max_length=255, min_length=1 |
| voted_at | DateTime | Yes | — |
| voter_id | Identifier | Yes | min_length=1 |

#### ReviewApproved

- **Type**: `Reviews.ReviewApproved.v1`
- **Version**: 1
- **Published**: Yes
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| approved_at | DateTime | Yes | — |
| customer_id | Identifier | Yes | min_length=1 |
| moderator_id | Identifier | Yes | min_length=1 |
| product_id | Identifier | Yes | min_length=1 |
| rating | Integer | Yes | — |
| review_id | Identifier | Yes | min_length=1 |

#### ReviewEdited

- **Type**: `Reviews.ReviewEdited.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| body | Text | No | — |
| edited_at | DateTime | Yes | — |
| rating | Integer | No | — |
| review_id | Identifier | Yes | min_length=1 |
| title | String | No | max_length=255 |

#### ReviewRejected

- **Type**: `Reviews.ReviewRejected.v1`
- **Version**: 1
- **Published**: Yes
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| customer_id | Identifier | Yes | min_length=1 |
| moderator_id | Identifier | Yes | min_length=1 |
| product_id | Identifier | Yes | min_length=1 |
| reason | String | Yes | max_length=255, min_length=1 |
| rejected_at | DateTime | Yes | — |
| review_id | Identifier | Yes | min_length=1 |

#### ReviewRemoved

- **Type**: `Reviews.ReviewRemoved.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| customer_id | Identifier | Yes | min_length=1 |
| product_id | Identifier | Yes | min_length=1 |
| rating | Integer | Yes | — |
| reason | String | Yes | max_length=255, min_length=1 |
| removed_at | DateTime | Yes | — |
| removed_by | String | Yes | max_length=255, min_length=1 |
| review_id | Identifier | Yes | min_length=1 |

#### ReviewReported

- **Type**: `Reviews.ReviewReported.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| detail | String | No | max_length=255 |
| reason | String | Yes | max_length=255, min_length=1 |
| report_count | Integer | Yes | — |
| reported_at | DateTime | Yes | — |
| reporter_id | Identifier | Yes | min_length=1 |
| review_id | Identifier | Yes | min_length=1 |

#### ReviewSubmitted

- **Type**: `Reviews.ReviewSubmitted.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| body | Text | Yes | min_length=1 |
| cons | List[String] | No | — |
| customer_id | Identifier | Yes | min_length=1 |
| image_count | Integer | No | — |
| order_id | Identifier | No | — |
| product_id | Identifier | Yes | min_length=1 |
| pros | List[String] | No | — |
| rating | Integer | Yes | — |
| review_id | Identifier | Yes | min_length=1 |
| submitted_at | DateTime | Yes | — |
| title | String | Yes | max_length=255, min_length=1 |
| variant_id | Identifier | No | — |
| verified_purchase | String | Yes | max_length=255, min_length=1 |

#### SellerReplyAdded

- **Type**: `Reviews.SellerReplyAdded.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| body | Text | Yes | min_length=1 |
| replied_at | DateTime | Yes | — |
| review_id | Identifier | Yes | min_length=1 |
| seller_id | Identifier | Yes | min_length=1 |

### Commands

#### EditReview

- **Type**: `Reviews.EditReview.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| body | Text | No | — |
| cons | List[String] | No | — |
| customer_id | Identifier | Yes | min_length=1 |
| pros | List[String] | No | — |
| rating | Integer | No | — |
| review_id | Identifier | Yes | min_length=1 |
| title | String | No | max_length=200 |

#### ModerateReview

- **Type**: `Reviews.ModerateReview.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| action | String | Yes | max_length=255, min_length=1 |
| moderator_id | Identifier | Yes | min_length=1 |
| reason | String | No | max_length=255 |
| review_id | Identifier | Yes | min_length=1 |

#### RemoveReview

- **Type**: `Reviews.RemoveReview.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| reason | String | Yes | max_length=255, min_length=1 |
| removed_by | String | Yes | max_length=255, min_length=1 |
| review_id | Identifier | Yes | min_length=1 |

#### AddSellerReply

- **Type**: `Reviews.AddSellerReply.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| body | Text | Yes | min_length=1 |
| review_id | Identifier | Yes | min_length=1 |
| seller_id | Identifier | Yes | min_length=1 |

#### ReportReview

- **Type**: `Reviews.ReportReview.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| customer_id | Identifier | Yes | min_length=1 |
| detail | String | No | max_length=500 |
| reason | String | Yes | max_length=255, min_length=1 |
| review_id | Identifier | Yes | min_length=1 |

#### SubmitReview

- **Type**: `Reviews.SubmitReview.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| body | Text | Yes | min_length=1 |
| cons | List[String] | No | — |
| customer_id | Identifier | Yes | min_length=1 |
| images | List[dict] | No | — |
| product_id | Identifier | Yes | min_length=1 |
| pros | List[String] | No | — |
| rating | Integer | Yes | — |
| title | String | Yes | max_length=200, min_length=1 |
| variant_id | Identifier | No | — |

#### VoteOnReview

- **Type**: `Reviews.VoteOnReview.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| customer_id | Identifier | Yes | min_length=1 |
| review_id | Identifier | Yes | min_length=1 |
| vote_type | String | Yes | max_length=255, min_length=1 |

---

## Published Event Contracts

| Event | Type | Version |
|-------|------|---------|
| ReviewApproved | `Reviews.ReviewApproved.v1` | 1 |
| ReviewRejected | `Reviews.ReviewRejected.v1` | 1 |
