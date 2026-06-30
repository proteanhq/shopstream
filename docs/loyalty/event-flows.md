## Event Flow: PromoCampaign

```mermaid
flowchart TD
    subgraph loyalty_campaign_campaign_PromoCampaign[PromoCampaign]
        agg_loyalty_campaign_campaign_PromoCampaign[PromoCampaign]
        cmd_loyalty_campaign_management_ActivateCampaign[/ActivateCampaign/]
        cmd_loyalty_campaign_management_ExpireCampaign[/ExpireCampaign/]
        cmd_loyalty_campaign_management_LaunchCampaign[/LaunchCampaign/]
        cmd_loyalty_campaign_management_PauseCampaign[/PauseCampaign/]
        evt_loyalty_campaign_events_CampaignActivated([CampaignActivated])
        evt_loyalty_campaign_events_CampaignExpired([CampaignExpired])
        evt_loyalty_campaign_events_CampaignLaunched([CampaignLaunched])
        evt_loyalty_campaign_events_CampaignPaused([CampaignPaused])
        hdlr_loyalty_campaign_management_PromoCampaignHandler[PromoCampaignHandler]
    end
    cmd_loyalty_campaign_management_ActivateCampaign --> hdlr_loyalty_campaign_management_PromoCampaignHandler
    cmd_loyalty_campaign_management_ExpireCampaign --> hdlr_loyalty_campaign_management_PromoCampaignHandler
    cmd_loyalty_campaign_management_LaunchCampaign --> hdlr_loyalty_campaign_management_PromoCampaignHandler
    cmd_loyalty_campaign_management_PauseCampaign --> hdlr_loyalty_campaign_management_PromoCampaignHandler
    hdlr_loyalty_campaign_management_PromoCampaignHandler --> agg_loyalty_campaign_campaign_PromoCampaign
    agg_loyalty_campaign_campaign_PromoCampaign --> evt_loyalty_campaign_events_CampaignActivated
    agg_loyalty_campaign_campaign_PromoCampaign --> evt_loyalty_campaign_events_CampaignExpired
    agg_loyalty_campaign_campaign_PromoCampaign --> evt_loyalty_campaign_events_CampaignLaunched
    agg_loyalty_campaign_campaign_PromoCampaign --> evt_loyalty_campaign_events_CampaignPaused
```

## Event Flow: Auditable

```mermaid
flowchart TD
    subgraph loyalty_reward_reward_account_Auditable[Auditable]
        agg_loyalty_reward_reward_account_Auditable[Auditable]
    end
```

## Event Flow: RewardAccount

```mermaid
flowchart TD
    subgraph loyalty_reward_reward_account_RewardAccount[RewardAccount]
        agg_loyalty_reward_reward_account_RewardAccount[RewardAccount]
        cmd_loyalty_reward_enrollment_EnrollRewardAccount[/EnrollRewardAccount/]
        cmd_loyalty_reward_points_EarnPoints[/EarnPoints/]
        cmd_loyalty_reward_points_RedeemPoints[/RedeemPoints/]
        evt_loyalty_reward_events_MembershipCardIssued([MembershipCardIssued])
        evt_loyalty_reward_events_PointsEarned([PointsEarned])
        evt_loyalty_reward_events_PointsRedeemed([PointsRedeemed])
        evt_loyalty_reward_events_RewardAccountClosed([RewardAccountClosed])
        evt_loyalty_reward_events_RewardAccountEnrolled([RewardAccountEnrolled])
        evt_loyalty_reward_events_TierUpgraded([TierUpgraded])
        hdlr_loyalty_reward_enrollment_EnrollRewardAccountHandler[EnrollRewardAccountHandler]
        hdlr_loyalty_reward_points_PointsHandler[PointsHandler]
    end
    cmd_loyalty_reward_enrollment_EnrollRewardAccount --> hdlr_loyalty_reward_enrollment_EnrollRewardAccountHandler
    hdlr_loyalty_reward_enrollment_EnrollRewardAccountHandler --> agg_loyalty_reward_reward_account_RewardAccount
    cmd_loyalty_reward_points_EarnPoints --> hdlr_loyalty_reward_points_PointsHandler
    cmd_loyalty_reward_points_RedeemPoints --> hdlr_loyalty_reward_points_PointsHandler
    hdlr_loyalty_reward_points_PointsHandler --> agg_loyalty_reward_reward_account_RewardAccount
    agg_loyalty_reward_reward_account_RewardAccount --> evt_loyalty_reward_events_MembershipCardIssued
    agg_loyalty_reward_reward_account_RewardAccount --> evt_loyalty_reward_events_PointsEarned
    agg_loyalty_reward_reward_account_RewardAccount --> evt_loyalty_reward_events_PointsRedeemed
    agg_loyalty_reward_reward_account_RewardAccount --> evt_loyalty_reward_events_RewardAccountClosed
    agg_loyalty_reward_reward_account_RewardAccount --> evt_loyalty_reward_events_RewardAccountEnrolled
    agg_loyalty_reward_reward_account_RewardAccount --> evt_loyalty_reward_events_TierUpgraded
```

## Downstream Consumers

```mermaid
flowchart LR
    evt_loyalty_campaign_events_CampaignActivated([CampaignActivated])
    evt_loyalty_campaign_events_CampaignExpired([CampaignExpired])
    evt_loyalty_campaign_events_CampaignLaunched([CampaignLaunched])
    evt_loyalty_campaign_events_CampaignPaused([CampaignPaused])
    evt_loyalty_reward_events_PointsEarned([PointsEarned])
    evt_loyalty_reward_events_PointsRedeemed([PointsRedeemed])
    evt_loyalty_reward_events_RewardAccountClosed([RewardAccountClosed])
    evt_loyalty_reward_events_RewardAccountEnrolled([RewardAccountEnrolled])
    evt_loyalty_reward_events_TierUpgraded([TierUpgraded])
    subgraph projectors["Projectors"]
        proj_loyalty_projections_campaign_catalog_CampaignCatalogProjector[CampaignCatalogProjector → CampaignCatalog]
        proj_loyalty_projections_points_leaderboard_PointsLeaderboardProjector[PointsLeaderboardProjector → PointsLeaderboard]
        proj_loyalty_projections_reward_account_view_RewardAccountViewProjector[RewardAccountViewProjector → RewardAccountView]
    end
    evt_loyalty_campaign_events_CampaignActivated --> proj_loyalty_projections_campaign_catalog_CampaignCatalogProjector
    evt_loyalty_campaign_events_CampaignExpired --> proj_loyalty_projections_campaign_catalog_CampaignCatalogProjector
    evt_loyalty_campaign_events_CampaignLaunched --> proj_loyalty_projections_campaign_catalog_CampaignCatalogProjector
    evt_loyalty_campaign_events_CampaignPaused --> proj_loyalty_projections_campaign_catalog_CampaignCatalogProjector
    evt_loyalty_reward_events_PointsEarned --> proj_loyalty_projections_points_leaderboard_PointsLeaderboardProjector
    evt_loyalty_reward_events_PointsRedeemed --> proj_loyalty_projections_points_leaderboard_PointsLeaderboardProjector
    evt_loyalty_reward_events_RewardAccountEnrolled --> proj_loyalty_projections_points_leaderboard_PointsLeaderboardProjector
    evt_loyalty_reward_events_PointsEarned --> proj_loyalty_projections_reward_account_view_RewardAccountViewProjector
    evt_loyalty_reward_events_PointsRedeemed --> proj_loyalty_projections_reward_account_view_RewardAccountViewProjector
    evt_loyalty_reward_events_RewardAccountClosed --> proj_loyalty_projections_reward_account_view_RewardAccountViewProjector
    evt_loyalty_reward_events_RewardAccountEnrolled --> proj_loyalty_projections_reward_account_view_RewardAccountViewProjector
    evt_loyalty_reward_events_TierUpgraded --> proj_loyalty_projections_reward_account_view_RewardAccountViewProjector
```
