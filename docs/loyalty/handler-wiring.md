## Command Handlers: PromoCampaign

```mermaid
flowchart LR
    subgraph command_handlers["Command Handlers"]
        ch_loyalty_campaign_management_PromoCampaignHandler[PromoCampaignHandler]
    end
    cmd_loyalty_campaign_management_ActivateCampaign[/ActivateCampaign/] --> ch_loyalty_campaign_management_PromoCampaignHandler
    cmd_loyalty_campaign_management_ExpireCampaign[/ExpireCampaign/] --> ch_loyalty_campaign_management_PromoCampaignHandler
    cmd_loyalty_campaign_management_LaunchCampaign[/LaunchCampaign/] --> ch_loyalty_campaign_management_PromoCampaignHandler
    cmd_loyalty_campaign_management_PauseCampaign[/PauseCampaign/] --> ch_loyalty_campaign_management_PromoCampaignHandler
    ch_loyalty_campaign_management_PromoCampaignHandler --> agg_loyalty_campaign_campaign_PromoCampaign[PromoCampaign]
```

## Command Handlers: Redemption

```mermaid
flowchart LR
    subgraph command_handlers["Command Handlers"]
        ch_loyalty_redemption_commands_RedemptionHandler[RedemptionHandler]
    end
    cmd_loyalty_redemption_commands_CompensateRedemption[/CompensateRedemption/] --> ch_loyalty_redemption_commands_RedemptionHandler
    cmd_loyalty_redemption_commands_CompleteRedemption[/CompleteRedemption/] --> ch_loyalty_redemption_commands_RedemptionHandler
    cmd_loyalty_redemption_commands_IssueRedemptionVoucher[/IssueRedemptionVoucher/] --> ch_loyalty_redemption_commands_RedemptionHandler
    cmd_loyalty_redemption_commands_RequestRedemption[/RequestRedemption/] --> ch_loyalty_redemption_commands_RedemptionHandler
    cmd_loyalty_redemption_commands_ReserveRedemptionPoints[/ReserveRedemptionPoints/] --> ch_loyalty_redemption_commands_RedemptionHandler
    ch_loyalty_redemption_commands_RedemptionHandler --> agg_loyalty_redemption_redemption_Redemption[Redemption]
```

## Command Handlers: RewardAccount

```mermaid
flowchart LR
    subgraph command_handlers["Command Handlers"]
        ch_loyalty_reward_enrollment_EnrollRewardAccountHandler[EnrollRewardAccountHandler]
        ch_loyalty_reward_points_PointsHandler[PointsHandler]
    end
    cmd_loyalty_reward_enrollment_EnrollRewardAccount[/EnrollRewardAccount/] --> ch_loyalty_reward_enrollment_EnrollRewardAccountHandler
    ch_loyalty_reward_enrollment_EnrollRewardAccountHandler --> agg_loyalty_reward_reward_account_RewardAccount[RewardAccount]
    cmd_loyalty_reward_points_EarnPoints[/EarnPoints/] --> ch_loyalty_reward_points_PointsHandler
    cmd_loyalty_reward_points_RedeemPoints[/RedeemPoints/] --> ch_loyalty_reward_points_PointsHandler
    ch_loyalty_reward_points_PointsHandler --> agg_loyalty_reward_reward_account_RewardAccount[RewardAccount]
```

## Process Managers

```mermaid
flowchart TD
    subgraph process_managers["Process Managers"]
        pm_loyalty_redemption_saga_RedemptionSaga["RedemptionSaga (start, end)"]
    end
    evt_loyalty_redemption_events_PointsReserved([PointsReserved]) --> pm_loyalty_redemption_saga_RedemptionSaga
    evt_loyalty_redemption_events_RedemptionRequested([RedemptionRequested]) -->|start| pm_loyalty_redemption_saga_RedemptionSaga
    evt_loyalty_redemption_events_VoucherIssuanceFailed([VoucherIssuanceFailed]) -->|end| pm_loyalty_redemption_saga_RedemptionSaga
    evt_loyalty_redemption_events_VoucherIssued([VoucherIssued]) --> pm_loyalty_redemption_saga_RedemptionSaga
```

## Subscribers

```mermaid
flowchart TD
    subgraph subscribers["Subscribers"]
        sub_loyalty_reward_identity_subscriber_CustomerRegisteredSubscriber[CustomerRegisteredSubscriber\nstream: identity::customer]
        sub_loyalty_reward_ordering_subscriber_OrderDeliveredSubscriber[OrderDeliveredSubscriber\nstream: ordering::order]
        sub_loyalty_reward_payments_subscriber_PaymentRefundedSubscriber[PaymentRefundedSubscriber\nstream: payments::payment]
        sub_loyalty_reward_reviews_subscriber_ReviewApprovedSubscriber[ReviewApprovedSubscriber\nstream: reviews::review]
    end
```

## Projector: CampaignCatalog

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_loyalty_projections_campaign_catalog_CampaignCatalogProjector[CampaignCatalogProjector → CampaignCatalog]
    end
    evt_loyalty_campaign_events_CampaignActivated([CampaignActivated]) --> proj_loyalty_projections_campaign_catalog_CampaignCatalogProjector
    evt_loyalty_campaign_events_CampaignExpired([CampaignExpired]) --> proj_loyalty_projections_campaign_catalog_CampaignCatalogProjector
    evt_loyalty_campaign_events_CampaignLaunched([CampaignLaunched]) --> proj_loyalty_projections_campaign_catalog_CampaignCatalogProjector
    evt_loyalty_campaign_events_CampaignPaused([CampaignPaused]) --> proj_loyalty_projections_campaign_catalog_CampaignCatalogProjector
```

## Projector: PointsLeaderboard

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_loyalty_projections_points_leaderboard_PointsLeaderboardProjector[PointsLeaderboardProjector → PointsLeaderboard]
    end
    evt_loyalty_reward_events_PointsEarned([PointsEarned]) --> proj_loyalty_projections_points_leaderboard_PointsLeaderboardProjector
    evt_loyalty_reward_events_PointsRedeemed([PointsRedeemed]) --> proj_loyalty_projections_points_leaderboard_PointsLeaderboardProjector
    evt_loyalty_reward_events_RewardAccountEnrolled([RewardAccountEnrolled]) --> proj_loyalty_projections_points_leaderboard_PointsLeaderboardProjector
```

## Projector: RedemptionView

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_loyalty_projections_redemption_view_RedemptionViewProjector[RedemptionViewProjector → RedemptionView]
    end
    evt_loyalty_redemption_events_PointsReserved([PointsReserved]) --> proj_loyalty_projections_redemption_view_RedemptionViewProjector
    evt_loyalty_redemption_events_RedemptionCompensated([RedemptionCompensated]) --> proj_loyalty_projections_redemption_view_RedemptionViewProjector
    evt_loyalty_redemption_events_RedemptionCompleted([RedemptionCompleted]) --> proj_loyalty_projections_redemption_view_RedemptionViewProjector
    evt_loyalty_redemption_events_RedemptionRequested([RedemptionRequested]) --> proj_loyalty_projections_redemption_view_RedemptionViewProjector
    evt_loyalty_redemption_events_VoucherIssuanceFailed([VoucherIssuanceFailed]) --> proj_loyalty_projections_redemption_view_RedemptionViewProjector
    evt_loyalty_redemption_events_VoucherIssued([VoucherIssued]) --> proj_loyalty_projections_redemption_view_RedemptionViewProjector
```

## Projector: RewardAccountView

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_loyalty_projections_reward_account_view_RewardAccountViewProjector[RewardAccountViewProjector → RewardAccountView]
    end
    evt_loyalty_reward_events_PointsEarned([PointsEarned]) --> proj_loyalty_projections_reward_account_view_RewardAccountViewProjector
    evt_loyalty_reward_events_PointsRedeemed([PointsRedeemed]) --> proj_loyalty_projections_reward_account_view_RewardAccountViewProjector
    evt_loyalty_reward_events_RewardAccountClosed([RewardAccountClosed]) --> proj_loyalty_projections_reward_account_view_RewardAccountViewProjector
    evt_loyalty_reward_events_RewardAccountEnrolled([RewardAccountEnrolled]) --> proj_loyalty_projections_reward_account_view_RewardAccountViewProjector
    evt_loyalty_reward_events_TierUpgraded([TierUpgraded]) --> proj_loyalty_projections_reward_account_view_RewardAccountViewProjector
```
