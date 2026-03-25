## Command Handlers: Review

```mermaid
flowchart LR
    subgraph command_handlers["Command Handlers"]
        ch_reviews_review_editing_EditReviewHandler[EditReviewHandler]
        ch_reviews_review_moderation_ModerateReviewHandler[ModerateReviewHandler]
        ch_reviews_review_removal_RemoveReviewHandler[RemoveReviewHandler]
        ch_reviews_review_reply_AddSellerReplyHandler[AddSellerReplyHandler]
        ch_reviews_review_reporting_ReportReviewHandler[ReportReviewHandler]
        ch_reviews_review_submission_SubmitReviewHandler[SubmitReviewHandler]
        ch_reviews_review_voting_VoteOnReviewHandler[VoteOnReviewHandler]
    end
    cmd_reviews_review_editing_EditReview[/EditReview/] --> ch_reviews_review_editing_EditReviewHandler
    ch_reviews_review_editing_EditReviewHandler --> agg_reviews_review_review_Review[Review]
    cmd_reviews_review_moderation_ModerateReview[/ModerateReview/] --> ch_reviews_review_moderation_ModerateReviewHandler
    ch_reviews_review_moderation_ModerateReviewHandler --> agg_reviews_review_review_Review[Review]
    cmd_reviews_review_removal_RemoveReview[/RemoveReview/] --> ch_reviews_review_removal_RemoveReviewHandler
    ch_reviews_review_removal_RemoveReviewHandler --> agg_reviews_review_review_Review[Review]
    cmd_reviews_review_reply_AddSellerReply[/AddSellerReply/] --> ch_reviews_review_reply_AddSellerReplyHandler
    ch_reviews_review_reply_AddSellerReplyHandler --> agg_reviews_review_review_Review[Review]
    cmd_reviews_review_reporting_ReportReview[/ReportReview/] --> ch_reviews_review_reporting_ReportReviewHandler
    ch_reviews_review_reporting_ReportReviewHandler --> agg_reviews_review_review_Review[Review]
    cmd_reviews_review_submission_SubmitReview[/SubmitReview/] --> ch_reviews_review_submission_SubmitReviewHandler
    ch_reviews_review_submission_SubmitReviewHandler --> agg_reviews_review_review_Review[Review]
    cmd_reviews_review_voting_VoteOnReview[/VoteOnReview/] --> ch_reviews_review_voting_VoteOnReviewHandler
    ch_reviews_review_voting_VoteOnReviewHandler --> agg_reviews_review_review_Review[Review]
```

## Subscribers

```mermaid
flowchart TD
    subgraph subscribers["Subscribers"]
        sub_reviews_review_ordering_subscriber_OrderDeliveredSubscriber[OrderDeliveredSubscriber\nstream: ordering::order]
    end
```

## Projector: CustomerReviews

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_reviews_projections_customer_reviews_CustomerReviewsProjector[CustomerReviewsProjector → CustomerReviews]
    end
    evt_reviews_review_events_ReviewApproved([ReviewApproved]) --> proj_reviews_projections_customer_reviews_CustomerReviewsProjector
    evt_reviews_review_events_ReviewEdited([ReviewEdited]) --> proj_reviews_projections_customer_reviews_CustomerReviewsProjector
    evt_reviews_review_events_ReviewRejected([ReviewRejected]) --> proj_reviews_projections_customer_reviews_CustomerReviewsProjector
    evt_reviews_review_events_ReviewRemoved([ReviewRemoved]) --> proj_reviews_projections_customer_reviews_CustomerReviewsProjector
    evt_reviews_review_events_ReviewSubmitted([ReviewSubmitted]) --> proj_reviews_projections_customer_reviews_CustomerReviewsProjector
```

## Projector: ModerationQueue

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_reviews_projections_moderation_queue_ModerationQueueProjector[ModerationQueueProjector → ModerationQueue]
    end
    evt_reviews_review_events_ReviewApproved([ReviewApproved]) --> proj_reviews_projections_moderation_queue_ModerationQueueProjector
    evt_reviews_review_events_ReviewRejected([ReviewRejected]) --> proj_reviews_projections_moderation_queue_ModerationQueueProjector
    evt_reviews_review_events_ReviewRemoved([ReviewRemoved]) --> proj_reviews_projections_moderation_queue_ModerationQueueProjector
    evt_reviews_review_events_ReviewReported([ReviewReported]) --> proj_reviews_projections_moderation_queue_ModerationQueueProjector
    evt_reviews_review_events_ReviewSubmitted([ReviewSubmitted]) --> proj_reviews_projections_moderation_queue_ModerationQueueProjector
```

## Projector: ProductRating

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_reviews_projections_product_rating_ProductRatingProjector[ProductRatingProjector → ProductRating]
    end
    evt_reviews_review_events_ReviewApproved([ReviewApproved]) --> proj_reviews_projections_product_rating_ProductRatingProjector
    evt_reviews_review_events_ReviewRemoved([ReviewRemoved]) --> proj_reviews_projections_product_rating_ProductRatingProjector
```

## Projector: ProductReviews

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_reviews_projections_product_reviews_ProductReviewsProjector[ProductReviewsProjector → ProductReviews]
    end
    evt_reviews_review_events_HelpfulVoteRecorded([HelpfulVoteRecorded]) --> proj_reviews_projections_product_reviews_ProductReviewsProjector
    evt_reviews_review_events_ReviewApproved([ReviewApproved]) --> proj_reviews_projections_product_reviews_ProductReviewsProjector
    evt_reviews_review_events_ReviewRemoved([ReviewRemoved]) --> proj_reviews_projections_product_reviews_ProductReviewsProjector
    evt_reviews_review_events_SellerReplyAdded([SellerReplyAdded]) --> proj_reviews_projections_product_reviews_ProductReviewsProjector
```

## Projector: ReviewDetail

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_reviews_projections_review_detail_ReviewDetailProjector[ReviewDetailProjector → ReviewDetail]
    end
    evt_reviews_review_events_HelpfulVoteRecorded([HelpfulVoteRecorded]) --> proj_reviews_projections_review_detail_ReviewDetailProjector
    evt_reviews_review_events_ReviewApproved([ReviewApproved]) --> proj_reviews_projections_review_detail_ReviewDetailProjector
    evt_reviews_review_events_ReviewEdited([ReviewEdited]) --> proj_reviews_projections_review_detail_ReviewDetailProjector
    evt_reviews_review_events_ReviewRejected([ReviewRejected]) --> proj_reviews_projections_review_detail_ReviewDetailProjector
    evt_reviews_review_events_ReviewRemoved([ReviewRemoved]) --> proj_reviews_projections_review_detail_ReviewDetailProjector
    evt_reviews_review_events_ReviewReported([ReviewReported]) --> proj_reviews_projections_review_detail_ReviewDetailProjector
    evt_reviews_review_events_ReviewSubmitted([ReviewSubmitted]) --> proj_reviews_projections_review_detail_ReviewDetailProjector
    evt_reviews_review_events_SellerReplyAdded([SellerReplyAdded]) --> proj_reviews_projections_review_detail_ReviewDetailProjector
```
