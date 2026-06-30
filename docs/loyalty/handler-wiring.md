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

## Subscribers

```mermaid
flowchart TD
    subgraph subscribers["Subscribers"]
        sub_loyalty_reward_ordering_subscriber_OrderDeliveredSubscriber[OrderDeliveredSubscriber\nstream: ordering::order]
    end
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
```
