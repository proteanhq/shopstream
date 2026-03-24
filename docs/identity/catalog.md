# Event & Command Catalog

## DefaultOutbox (`abc.DefaultOutbox`)

## MemoryOutbox (`abc.MemoryOutbox`)

## Customer (`identity.customer.customer.Customer`)

### Events

#### AccountClosed

- **Type**: `Identity.AccountClosed.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| closed_at | DateTime | Yes | — |
| customer_id | Identifier | Yes | min_length=1 |

#### AccountReactivated

- **Type**: `Identity.AccountReactivated.v1`
- **Version**: 1
- **Published**: Yes
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| customer_id | Identifier | Yes | min_length=1 |
| reactivated_at | DateTime | Yes | — |

#### AccountSuspended

- **Type**: `Identity.AccountSuspended.v1`
- **Version**: 1
- **Published**: Yes
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| customer_id | Identifier | Yes | min_length=1 |
| reason | String | Yes | max_length=255, min_length=1 |
| suspended_at | DateTime | Yes | — |

#### AddressAdded

- **Type**: `Identity.AddressAdded.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| address_id | Identifier | Yes | min_length=1 |
| city | String | Yes | max_length=255, min_length=1 |
| country | String | Yes | max_length=255, min_length=1 |
| customer_id | Identifier | Yes | min_length=1 |
| is_default | Boolean | Yes | — |
| label | String | Yes | max_length=255, min_length=1 |
| postal_code | String | Yes | max_length=255, min_length=1 |
| state | String | No | max_length=255 |
| street | String | Yes | max_length=255, min_length=1 |

#### AddressRemoved

- **Type**: `Identity.AddressRemoved.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| address_id | Identifier | Yes | min_length=1 |
| customer_id | Identifier | Yes | min_length=1 |

#### AddressUpdated

- **Type**: `Identity.AddressUpdated.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| address_id | Identifier | Yes | min_length=1 |
| city | String | No | max_length=255 |
| country | String | No | max_length=255 |
| customer_id | Identifier | Yes | min_length=1 |
| label | String | No | max_length=255 |
| postal_code | String | No | max_length=255 |
| state | String | No | max_length=255 |
| street | String | No | max_length=255 |

#### CustomerRegistered

- **Type**: `Identity.CustomerRegistered.v1`
- **Version**: 1
- **Published**: Yes
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| customer_id | Identifier | Yes | min_length=1 |
| email | String | Yes | max_length=255, min_length=1 |
| external_id | String | Yes | max_length=255, min_length=1 |
| first_name | String | Yes | max_length=255, min_length=1 |
| last_name | String | Yes | max_length=255, min_length=1 |
| registered_at | DateTime | Yes | — |

#### DefaultAddressChanged

- **Type**: `Identity.DefaultAddressChanged.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| address_id | Identifier | Yes | min_length=1 |
| customer_id | Identifier | Yes | min_length=1 |
| previous_default_address_id | Identifier | No | — |

#### ProfileUpdated

- **Type**: `Identity.ProfileUpdated.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| customer_id | Identifier | Yes | min_length=1 |
| date_of_birth | String | No | max_length=10 |
| first_name | String | Yes | max_length=255, min_length=1 |
| last_name | String | Yes | max_length=255, min_length=1 |
| phone | String | No | max_length=255 |

#### TierUpgraded

- **Type**: `Identity.TierUpgraded.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| customer_id | Identifier | Yes | min_length=1 |
| new_tier | String | Yes | max_length=255, min_length=1 |
| previous_tier | String | Yes | max_length=255, min_length=1 |
| upgraded_at | DateTime | Yes | — |

### Commands

#### CloseAccount

- **Type**: `Identity.CloseAccount.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| customer_id | Identifier | Yes | min_length=1 |

#### ReactivateAccount

- **Type**: `Identity.ReactivateAccount.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| customer_id | Identifier | Yes | min_length=1 |

#### SuspendAccount

- **Type**: `Identity.SuspendAccount.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| customer_id | Identifier | Yes | min_length=1 |
| reason | String | Yes | max_length=500, min_length=1 |

#### AddAddress

- **Type**: `Identity.AddAddress.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| city | String | Yes | max_length=100, min_length=1 |
| country | String | Yes | max_length=100, min_length=1 |
| customer_id | Identifier | Yes | min_length=1 |
| geo_lat | String | No | max_length=255 |
| geo_lng | String | No | max_length=255 |
| label | String | No | max_length=20 |
| postal_code | String | Yes | max_length=20, min_length=1 |
| state | String | No | max_length=100 |
| street | String | Yes | max_length=255, min_length=1 |

#### RemoveAddress

- **Type**: `Identity.RemoveAddress.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| address_id | Identifier | Yes | min_length=1 |
| customer_id | Identifier | Yes | min_length=1 |

#### SetDefaultAddress

- **Type**: `Identity.SetDefaultAddress.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| address_id | Identifier | Yes | min_length=1 |
| customer_id | Identifier | Yes | min_length=1 |

#### UpdateAddress

- **Type**: `Identity.UpdateAddress.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| address_id | Identifier | Yes | min_length=1 |
| city | String | No | max_length=100 |
| country | String | No | max_length=100 |
| customer_id | Identifier | Yes | min_length=1 |
| label | String | No | max_length=20 |
| postal_code | String | No | max_length=20 |
| state | String | No | max_length=100 |
| street | String | No | max_length=255 |

#### UpdateProfile

- **Type**: `Identity.UpdateProfile.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| customer_id | Identifier | Yes | min_length=1 |
| date_of_birth | String | No | max_length=10 |
| first_name | String | No | max_length=100 |
| last_name | String | No | max_length=100 |
| phone | String | No | max_length=20 |

#### RegisterCustomer

- **Type**: `Identity.RegisterCustomer.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| date_of_birth | String | No | max_length=10 |
| email | String | Yes | max_length=254, min_length=1 |
| external_id | String | Yes | max_length=255, min_length=1 |
| first_name | String | Yes | max_length=100, min_length=1 |
| last_name | String | Yes | max_length=100, min_length=1 |
| phone | String | No | max_length=20 |

#### UpgradeTier

- **Type**: `Identity.UpgradeTier.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| customer_id | Identifier | Yes | min_length=1 |
| new_tier | String | Yes | max_length=20, min_length=1 |

---

## Published Event Contracts

| Event | Type | Version |
|-------|------|---------|
| AccountReactivated | `Identity.AccountReactivated.v1` | 1 |
| AccountSuspended | `Identity.AccountSuspended.v1` | 1 |
| CustomerRegistered | `Identity.CustomerRegistered.v1` | 1 |
