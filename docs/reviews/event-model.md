## Event Model: Review

> **Given** Review
> **When** EditReview, ModerateReview, RemoveReview, AddSellerReply, ReportReview, SubmitReview, VoteOnReview
> **Then** HelpfulVoteRecorded, ReviewApproved, ReviewEdited, ReviewRejected, ReviewRemoved, ReviewReported, ReviewSubmitted, SellerReplyAdded

```mermaid
flowchart LR
    subgraph reviews_review_review_Review[Review]
        cmd_reviews_review_editing_EditReview[/EditReview/]
        cmd_reviews_review_moderation_ModerateReview[/ModerateReview/]
        cmd_reviews_review_removal_RemoveReview[/RemoveReview/]
        cmd_reviews_review_reply_AddSellerReply[/AddSellerReply/]
        cmd_reviews_review_reporting_ReportReview[/ReportReview/]
        cmd_reviews_review_submission_SubmitReview[/SubmitReview/]
        cmd_reviews_review_voting_VoteOnReview[/VoteOnReview/]
        agg_reviews_review_review_Review[Review]
        evt_reviews_review_events_HelpfulVoteRecorded([HelpfulVoteRecorded])
        evt_reviews_review_events_ReviewApproved([ReviewApproved])
        evt_reviews_review_events_ReviewEdited([ReviewEdited])
        evt_reviews_review_events_ReviewRejected([ReviewRejected])
        evt_reviews_review_events_ReviewRemoved([ReviewRemoved])
        evt_reviews_review_events_ReviewReported([ReviewReported])
        evt_reviews_review_events_ReviewSubmitted([ReviewSubmitted])
        evt_reviews_review_events_SellerReplyAdded([SellerReplyAdded])
        rm_reviews_review_review_Review_reviews_projections_customer_reviews_CustomerReviewsProjector[(CustomerReviewsProjector → CustomerReviews)]
        rm_reviews_review_review_Review_reviews_projections_moderation_queue_ModerationQueueProjector[(ModerationQueueProjector → ModerationQueue)]
        rm_reviews_review_review_Review_reviews_projections_product_rating_ProductRatingProjector[(ProductRatingProjector → ProductRating)]
        rm_reviews_review_review_Review_reviews_projections_product_reviews_ProductReviewsProjector[(ProductReviewsProjector → ProductReviews)]
        rm_reviews_review_review_Review_reviews_projections_review_detail_ReviewDetailProjector[(ReviewDetailProjector → ReviewDetail)]
    end
    cmd_reviews_review_editing_EditReview --> agg_reviews_review_review_Review
    cmd_reviews_review_moderation_ModerateReview --> agg_reviews_review_review_Review
    cmd_reviews_review_removal_RemoveReview --> agg_reviews_review_review_Review
    cmd_reviews_review_reply_AddSellerReply --> agg_reviews_review_review_Review
    cmd_reviews_review_reporting_ReportReview --> agg_reviews_review_review_Review
    cmd_reviews_review_submission_SubmitReview --> agg_reviews_review_review_Review
    cmd_reviews_review_voting_VoteOnReview --> agg_reviews_review_review_Review
    agg_reviews_review_review_Review --> evt_reviews_review_events_HelpfulVoteRecorded
    evt_reviews_review_events_HelpfulVoteRecorded --> rm_reviews_review_review_Review_reviews_projections_product_reviews_ProductReviewsProjector
    evt_reviews_review_events_HelpfulVoteRecorded --> rm_reviews_review_review_Review_reviews_projections_review_detail_ReviewDetailProjector
    agg_reviews_review_review_Review --> evt_reviews_review_events_ReviewApproved
    evt_reviews_review_events_ReviewApproved --> rm_reviews_review_review_Review_reviews_projections_customer_reviews_CustomerReviewsProjector
    evt_reviews_review_events_ReviewApproved --> rm_reviews_review_review_Review_reviews_projections_moderation_queue_ModerationQueueProjector
    evt_reviews_review_events_ReviewApproved --> rm_reviews_review_review_Review_reviews_projections_product_rating_ProductRatingProjector
    evt_reviews_review_events_ReviewApproved --> rm_reviews_review_review_Review_reviews_projections_product_reviews_ProductReviewsProjector
    evt_reviews_review_events_ReviewApproved --> rm_reviews_review_review_Review_reviews_projections_review_detail_ReviewDetailProjector
    agg_reviews_review_review_Review --> evt_reviews_review_events_ReviewEdited
    evt_reviews_review_events_ReviewEdited --> rm_reviews_review_review_Review_reviews_projections_customer_reviews_CustomerReviewsProjector
    evt_reviews_review_events_ReviewEdited --> rm_reviews_review_review_Review_reviews_projections_moderation_queue_ModerationQueueProjector
    evt_reviews_review_events_ReviewEdited --> rm_reviews_review_review_Review_reviews_projections_review_detail_ReviewDetailProjector
    agg_reviews_review_review_Review --> evt_reviews_review_events_ReviewRejected
    evt_reviews_review_events_ReviewRejected --> rm_reviews_review_review_Review_reviews_projections_customer_reviews_CustomerReviewsProjector
    evt_reviews_review_events_ReviewRejected --> rm_reviews_review_review_Review_reviews_projections_moderation_queue_ModerationQueueProjector
    evt_reviews_review_events_ReviewRejected --> rm_reviews_review_review_Review_reviews_projections_review_detail_ReviewDetailProjector
    agg_reviews_review_review_Review --> evt_reviews_review_events_ReviewRemoved
    evt_reviews_review_events_ReviewRemoved --> rm_reviews_review_review_Review_reviews_projections_customer_reviews_CustomerReviewsProjector
    evt_reviews_review_events_ReviewRemoved --> rm_reviews_review_review_Review_reviews_projections_moderation_queue_ModerationQueueProjector
    evt_reviews_review_events_ReviewRemoved --> rm_reviews_review_review_Review_reviews_projections_product_rating_ProductRatingProjector
    evt_reviews_review_events_ReviewRemoved --> rm_reviews_review_review_Review_reviews_projections_product_reviews_ProductReviewsProjector
    evt_reviews_review_events_ReviewRemoved --> rm_reviews_review_review_Review_reviews_projections_review_detail_ReviewDetailProjector
    agg_reviews_review_review_Review --> evt_reviews_review_events_ReviewReported
    evt_reviews_review_events_ReviewReported --> rm_reviews_review_review_Review_reviews_projections_moderation_queue_ModerationQueueProjector
    evt_reviews_review_events_ReviewReported --> rm_reviews_review_review_Review_reviews_projections_review_detail_ReviewDetailProjector
    agg_reviews_review_review_Review --> evt_reviews_review_events_ReviewSubmitted
    evt_reviews_review_events_ReviewSubmitted --> rm_reviews_review_review_Review_reviews_projections_customer_reviews_CustomerReviewsProjector
    evt_reviews_review_events_ReviewSubmitted --> rm_reviews_review_review_Review_reviews_projections_moderation_queue_ModerationQueueProjector
    evt_reviews_review_events_ReviewSubmitted --> rm_reviews_review_review_Review_reviews_projections_review_detail_ReviewDetailProjector
    agg_reviews_review_review_Review --> evt_reviews_review_events_SellerReplyAdded
    evt_reviews_review_events_SellerReplyAdded --> rm_reviews_review_review_Review_reviews_projections_product_reviews_ProductReviewsProjector
    evt_reviews_review_events_SellerReplyAdded --> rm_reviews_review_review_Review_reviews_projections_review_detail_ReviewDetailProjector
```