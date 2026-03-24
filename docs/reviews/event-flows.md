## Event Flows

```mermaid
flowchart LR
    subgraph abc_DefaultOutbox[DefaultOutbox]
        agg_abc_DefaultOutbox[DefaultOutbox]
    end
    subgraph abc_MemoryOutbox[MemoryOutbox]
        agg_abc_MemoryOutbox[MemoryOutbox]
    end
    subgraph reviews_review_review_Review[Review]
        agg_reviews_review_review_Review[Review]
        cmd_reviews_review_editing_EditReview[/EditReview/]
        cmd_reviews_review_moderation_ModerateReview[/ModerateReview/]
        cmd_reviews_review_removal_RemoveReview[/RemoveReview/]
        cmd_reviews_review_reply_AddSellerReply[/AddSellerReply/]
        cmd_reviews_review_reporting_ReportReview[/ReportReview/]
        cmd_reviews_review_submission_SubmitReview[/SubmitReview/]
        cmd_reviews_review_voting_VoteOnReview[/VoteOnReview/]
        evt_reviews_review_events_HelpfulVoteRecorded([HelpfulVoteRecorded])
        evt_reviews_review_events_ReviewApproved([ReviewApproved])
        evt_reviews_review_events_ReviewEdited([ReviewEdited])
        evt_reviews_review_events_ReviewRejected([ReviewRejected])
        evt_reviews_review_events_ReviewRemoved([ReviewRemoved])
        evt_reviews_review_events_ReviewReported([ReviewReported])
        evt_reviews_review_events_ReviewSubmitted([ReviewSubmitted])
        evt_reviews_review_events_SellerReplyAdded([SellerReplyAdded])
        hdlr_reviews_review_editing_EditReviewHandler[EditReviewHandler]
        hdlr_reviews_review_moderation_ModerateReviewHandler[ModerateReviewHandler]
        hdlr_reviews_review_removal_RemoveReviewHandler[RemoveReviewHandler]
        hdlr_reviews_review_reply_AddSellerReplyHandler[AddSellerReplyHandler]
        hdlr_reviews_review_reporting_ReportReviewHandler[ReportReviewHandler]
        hdlr_reviews_review_submission_SubmitReviewHandler[SubmitReviewHandler]
        hdlr_reviews_review_voting_VoteOnReviewHandler[VoteOnReviewHandler]
    end
    cmd_reviews_review_editing_EditReview --> hdlr_reviews_review_editing_EditReviewHandler
    hdlr_reviews_review_editing_EditReviewHandler --> agg_reviews_review_review_Review
    cmd_reviews_review_moderation_ModerateReview --> hdlr_reviews_review_moderation_ModerateReviewHandler
    hdlr_reviews_review_moderation_ModerateReviewHandler --> agg_reviews_review_review_Review
    cmd_reviews_review_removal_RemoveReview --> hdlr_reviews_review_removal_RemoveReviewHandler
    hdlr_reviews_review_removal_RemoveReviewHandler --> agg_reviews_review_review_Review
    cmd_reviews_review_reply_AddSellerReply --> hdlr_reviews_review_reply_AddSellerReplyHandler
    hdlr_reviews_review_reply_AddSellerReplyHandler --> agg_reviews_review_review_Review
    cmd_reviews_review_reporting_ReportReview --> hdlr_reviews_review_reporting_ReportReviewHandler
    hdlr_reviews_review_reporting_ReportReviewHandler --> agg_reviews_review_review_Review
    cmd_reviews_review_submission_SubmitReview --> hdlr_reviews_review_submission_SubmitReviewHandler
    hdlr_reviews_review_submission_SubmitReviewHandler --> agg_reviews_review_review_Review
    cmd_reviews_review_voting_VoteOnReview --> hdlr_reviews_review_voting_VoteOnReviewHandler
    hdlr_reviews_review_voting_VoteOnReviewHandler --> agg_reviews_review_review_Review
    agg_reviews_review_review_Review --> evt_reviews_review_events_HelpfulVoteRecorded
    agg_reviews_review_review_Review --> evt_reviews_review_events_ReviewApproved
    agg_reviews_review_review_Review --> evt_reviews_review_events_ReviewEdited
    agg_reviews_review_review_Review --> evt_reviews_review_events_ReviewRejected
    agg_reviews_review_review_Review --> evt_reviews_review_events_ReviewRemoved
    agg_reviews_review_review_Review --> evt_reviews_review_events_ReviewReported
    agg_reviews_review_review_Review --> evt_reviews_review_events_ReviewSubmitted
    agg_reviews_review_review_Review --> evt_reviews_review_events_SellerReplyAdded
    proj_reviews_projections_customer_reviews_CustomerReviewsProjector[CustomerReviewsProjector → CustomerReviews]
    evt_reviews_review_events_ReviewApproved --> proj_reviews_projections_customer_reviews_CustomerReviewsProjector
    evt_reviews_review_events_ReviewEdited --> proj_reviews_projections_customer_reviews_CustomerReviewsProjector
    evt_reviews_review_events_ReviewRejected --> proj_reviews_projections_customer_reviews_CustomerReviewsProjector
    evt_reviews_review_events_ReviewRemoved --> proj_reviews_projections_customer_reviews_CustomerReviewsProjector
    evt_reviews_review_events_ReviewSubmitted --> proj_reviews_projections_customer_reviews_CustomerReviewsProjector
    proj_reviews_projections_moderation_queue_ModerationQueueProjector[ModerationQueueProjector → ModerationQueue]
    evt_reviews_review_events_ReviewApproved --> proj_reviews_projections_moderation_queue_ModerationQueueProjector
    evt_reviews_review_events_ReviewRejected --> proj_reviews_projections_moderation_queue_ModerationQueueProjector
    evt_reviews_review_events_ReviewRemoved --> proj_reviews_projections_moderation_queue_ModerationQueueProjector
    evt_reviews_review_events_ReviewReported --> proj_reviews_projections_moderation_queue_ModerationQueueProjector
    evt_reviews_review_events_ReviewSubmitted --> proj_reviews_projections_moderation_queue_ModerationQueueProjector
    proj_reviews_projections_product_rating_ProductRatingProjector[ProductRatingProjector → ProductRating]
    evt_reviews_review_events_ReviewApproved --> proj_reviews_projections_product_rating_ProductRatingProjector
    evt_reviews_review_events_ReviewRemoved --> proj_reviews_projections_product_rating_ProductRatingProjector
    proj_reviews_projections_product_reviews_ProductReviewsProjector[ProductReviewsProjector → ProductReviews]
    evt_reviews_review_events_HelpfulVoteRecorded --> proj_reviews_projections_product_reviews_ProductReviewsProjector
    evt_reviews_review_events_ReviewApproved --> proj_reviews_projections_product_reviews_ProductReviewsProjector
    evt_reviews_review_events_ReviewRemoved --> proj_reviews_projections_product_reviews_ProductReviewsProjector
    evt_reviews_review_events_SellerReplyAdded --> proj_reviews_projections_product_reviews_ProductReviewsProjector
    proj_reviews_projections_review_detail_ReviewDetailProjector[ReviewDetailProjector → ReviewDetail]
    evt_reviews_review_events_HelpfulVoteRecorded --> proj_reviews_projections_review_detail_ReviewDetailProjector
    evt_reviews_review_events_ReviewApproved --> proj_reviews_projections_review_detail_ReviewDetailProjector
    evt_reviews_review_events_ReviewEdited --> proj_reviews_projections_review_detail_ReviewDetailProjector
    evt_reviews_review_events_ReviewRejected --> proj_reviews_projections_review_detail_ReviewDetailProjector
    evt_reviews_review_events_ReviewRemoved --> proj_reviews_projections_review_detail_ReviewDetailProjector
    evt_reviews_review_events_ReviewReported --> proj_reviews_projections_review_detail_ReviewDetailProjector
    evt_reviews_review_events_ReviewSubmitted --> proj_reviews_projections_review_detail_ReviewDetailProjector
    evt_reviews_review_events_SellerReplyAdded --> proj_reviews_projections_review_detail_ReviewDetailProjector
```
