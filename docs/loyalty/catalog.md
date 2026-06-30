# Event & Command Catalog

## PromoCampaign (`loyalty.campaign.campaign.PromoCampaign`)

### Events

#### PromoCampaignFactEvent

- **Type**: `Loyalty.PromoCampaignFactEvent.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: Yes

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| campaign_code | String | Yes | — |
| discount_type | String | Yes | — |
| discount_value | Integer | Yes | — |
| ends_on | Date | No | — |
| id | String | No | — |
| launched_at | DateTime | No | — |
| name | String | Yes | — |
| starts_on | Date | No | — |
| status | String | No | — |

#### CampaignActivated

- **Type**: `Loyalty.CampaignActivated.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| activated_at | DateTime | Yes | — |
| campaign_id | String | Yes | max_length=255, min_length=1 |

#### CampaignExpired

- **Type**: `Loyalty.CampaignExpired.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| campaign_id | String | Yes | max_length=255, min_length=1 |
| expired_at | DateTime | Yes | — |

#### CampaignLaunched

- **Type**: `Loyalty.CampaignLaunched.v3`
- **Version**: 3
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| campaign_code | String | Yes | max_length=255, min_length=1 |
| campaign_id | String | Yes | max_length=255, min_length=1 |
| discount_type | String | Yes | max_length=255, min_length=1 |
| discount_value | Integer | Yes | — |
| ends_on | Date | No | — |
| launched_at | DateTime | Yes | — |
| name | String | Yes | max_length=255, min_length=1 |
| starts_on | Date | No | — |

#### CampaignPaused

- **Type**: `Loyalty.CampaignPaused.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| campaign_id | String | Yes | max_length=255, min_length=1 |
| paused_at | DateTime | Yes | — |
| reason | String | No | max_length=255 |

### Commands

#### ActivateCampaign

- **Type**: `Loyalty.ActivateCampaign.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| campaign_id | Identifier | Yes | min_length=1 |

#### ExpireCampaign

- **Type**: `Loyalty.ExpireCampaign.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| campaign_id | Identifier | Yes | min_length=1 |

#### LaunchCampaign

- **Type**: `Loyalty.LaunchCampaign.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| campaign_code | String | Yes | max_length=20, min_length=1 |
| discount_type | String | Yes | max_length=255, min_length=1 |
| discount_value | Integer | Yes | — |
| ends_on | Date | No | — |
| name | String | Yes | max_length=255, min_length=1 |
| starts_on | Date | No | — |

#### PauseCampaign

- **Type**: `Loyalty.PauseCampaign.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| campaign_id | Identifier | Yes | min_length=1 |
| reason | String | No | max_length=255 |

## Auditable (`loyalty.reward.reward_account.Auditable`)

## RewardAccount (`loyalty.reward.reward_account.RewardAccount`)

### Events

#### MembershipCardIssued

- **Type**: `Loyalty.MembershipCardIssued.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| account_id | String | Yes | max_length=255, min_length=1 |
| card_number | String | Yes | max_length=255, min_length=1 |
| issued_on | String | Yes | max_length=255, min_length=1 |

#### PointsEarned

- **Type**: `Loyalty.PointsEarned.v1`
- **Version**: 1
- **Published**: Yes
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| account_id | String | Yes | max_length=255, min_length=1 |
| amount | Integer | Yes | — |
| balance_after | Integer | Yes | — |
| customer_id | String | No | max_length=255 |
| occurred_at | DateTime | Yes | — |
| reason | String | No | max_length=255 |

#### PointsRedeemed

- **Type**: `Loyalty.PointsRedeemed.v1`
- **Version**: 1
- **Published**: Yes
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| account_id | String | Yes | max_length=255, min_length=1 |
| amount | Integer | Yes | — |
| balance_after | Integer | Yes | — |
| customer_id | String | No | max_length=255 |
| occurred_at | DateTime | Yes | — |
| reason | String | No | max_length=255 |

#### RewardAccountClosed

- **Type**: `Loyalty.RewardAccountClosed.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| account_id | String | Yes | max_length=255, min_length=1 |
| closed_at | DateTime | Yes | — |

#### RewardAccountEnrolled

- **Type**: `Loyalty.RewardAccountEnrolled.v1`
- **Version**: 1
- **Published**: Yes
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| account_id | String | Yes | max_length=255, min_length=1 |
| customer_id | String | Yes | max_length=255, min_length=1 |
| enrolled_at | DateTime | Yes | — |
| member_code | String | Yes | max_length=255, min_length=1 |
| tier | String | Yes | max_length=255, min_length=1 |

#### TierUpgraded

- **Type**: `Loyalty.TierUpgraded.v1`
- **Version**: 1
- **Published**: Yes
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| account_id | String | Yes | max_length=255, min_length=1 |
| customer_id | String | Yes | max_length=255, min_length=1 |
| lifetime_points | Integer | Yes | — |
| new_tier | String | Yes | max_length=255, min_length=1 |
| occurred_at | DateTime | Yes | — |
| old_tier | String | Yes | max_length=255, min_length=1 |

### Commands

#### EnrollRewardAccount

- **Type**: `Loyalty.EnrollRewardAccount.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| customer_id | String | Yes | max_length=255, min_length=1 |
| member_code | String | No | max_length=12 |

#### EarnPoints

- **Type**: `Loyalty.EarnPoints.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| account_id | Identifier | Yes | min_length=1 |
| amount | Integer | Yes | — |
| reason | String | No | max_length=255 |

#### RedeemPoints

- **Type**: `Loyalty.RedeemPoints.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| account_id | Identifier | Yes | min_length=1 |
| amount | Integer | Yes | — |
| reason | String | No | max_length=255 |

---

## Published Event Contracts

| Event | Type | Version |
|-------|------|---------|
| PointsEarned | `Loyalty.PointsEarned.v1` | 1 |
| PointsRedeemed | `Loyalty.PointsRedeemed.v1` | 1 |
| RewardAccountEnrolled | `Loyalty.RewardAccountEnrolled.v1` | 1 |
| TierUpgraded | `Loyalty.TierUpgraded.v1` | 1 |
