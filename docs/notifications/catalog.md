# Event & Command Catalog

## Notification (`notifications.notification.notification.Notification`)

### Events

#### NotificationBounced

- **Type**: `Notifications.NotificationBounced.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| bounced_at | DateTime | Yes | — |
| channel | String | Yes | max_length=255, min_length=1 |
| notification_id | Identifier | Yes | min_length=1 |
| reason | String | Yes | max_length=255, min_length=1 |
| recipient_id | Identifier | Yes | min_length=1 |

#### NotificationCancelled

- **Type**: `Notifications.NotificationCancelled.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| cancelled_at | DateTime | Yes | — |
| channel | String | Yes | max_length=255, min_length=1 |
| notification_id | Identifier | Yes | min_length=1 |
| reason | String | Yes | max_length=255, min_length=1 |
| recipient_id | Identifier | Yes | min_length=1 |

#### NotificationCreated

- **Type**: `Notifications.NotificationCreated.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| channel | String | Yes | max_length=255, min_length=1 |
| created_at | DateTime | Yes | — |
| notification_id | Identifier | Yes | min_length=1 |
| notification_type | String | Yes | max_length=255, min_length=1 |
| recipient_id | Identifier | Yes | min_length=1 |
| recipient_type | String | Yes | max_length=255, min_length=1 |
| scheduled_for | DateTime | No | — |
| source_event_type | String | No | max_length=255 |
| subject | String | No | max_length=255 |
| template_name | String | No | max_length=255 |

#### NotificationDelivered

- **Type**: `Notifications.NotificationDelivered.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| channel | String | Yes | max_length=255, min_length=1 |
| delivered_at | DateTime | Yes | — |
| notification_id | Identifier | Yes | min_length=1 |
| recipient_id | Identifier | Yes | min_length=1 |

#### NotificationFailed

- **Type**: `Notifications.NotificationFailed.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| channel | String | Yes | max_length=255, min_length=1 |
| failed_at | DateTime | Yes | — |
| max_retries | Integer | Yes | — |
| notification_id | Identifier | Yes | min_length=1 |
| reason | String | Yes | max_length=255, min_length=1 |
| recipient_id | Identifier | Yes | min_length=1 |
| retry_count | Integer | Yes | — |

#### NotificationRetried

- **Type**: `Notifications.NotificationRetried.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| channel | String | Yes | max_length=255, min_length=1 |
| notification_id | Identifier | Yes | min_length=1 |
| recipient_id | Identifier | Yes | min_length=1 |
| retried_at | DateTime | Yes | — |
| retry_count | Integer | Yes | — |

#### NotificationSent

- **Type**: `Notifications.NotificationSent.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| channel | String | Yes | max_length=255, min_length=1 |
| notification_id | Identifier | Yes | min_length=1 |
| recipient_id | Identifier | Yes | min_length=1 |
| sent_at | DateTime | Yes | — |

### Commands

#### CancelNotification

- **Type**: `Notifications.CancelNotification.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| notification_id | Identifier | Yes | min_length=1 |
| reason | String | Yes | max_length=500, min_length=1 |

#### RetryNotification

- **Type**: `Notifications.RetryNotification.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| notification_id | Identifier | Yes | min_length=1 |

#### ProcessScheduledNotifications

- **Type**: `Notifications.ProcessScheduledNotifications.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| as_of | DateTime | No | — |

## NotificationPreference (`notifications.preference.preference.NotificationPreference`)

### Events

#### ChannelsUpdated

- **Type**: `Notifications.ChannelsUpdated.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| customer_id | Identifier | Yes | min_length=1 |
| email_enabled | Boolean | Yes | — |
| preference_id | Identifier | Yes | min_length=1 |
| push_enabled | Boolean | Yes | — |
| sms_enabled | Boolean | Yes | — |
| updated_at | DateTime | Yes | — |

#### PreferencesCreated

- **Type**: `Notifications.PreferencesCreated.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| created_at | DateTime | Yes | — |
| customer_id | Identifier | Yes | min_length=1 |
| email_enabled | Boolean | Yes | — |
| preference_id | Identifier | Yes | min_length=1 |
| push_enabled | Boolean | Yes | — |
| sms_enabled | Boolean | Yes | — |

#### QuietHoursCleared

- **Type**: `Notifications.QuietHoursCleared.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| cleared_at | DateTime | Yes | — |
| customer_id | Identifier | Yes | min_length=1 |
| preference_id | Identifier | Yes | min_length=1 |

#### QuietHoursSet

- **Type**: `Notifications.QuietHoursSet.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| customer_id | Identifier | Yes | min_length=1 |
| end | String | Yes | max_length=255, min_length=1 |
| preference_id | Identifier | Yes | min_length=1 |
| start | String | Yes | max_length=255, min_length=1 |
| updated_at | DateTime | Yes | — |

#### TypeResubscribed

- **Type**: `Notifications.TypeResubscribed.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| customer_id | Identifier | Yes | min_length=1 |
| notification_type | String | Yes | max_length=255, min_length=1 |
| preference_id | Identifier | Yes | min_length=1 |
| resubscribed_at | DateTime | Yes | — |

#### TypeUnsubscribed

- **Type**: `Notifications.TypeUnsubscribed.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| customer_id | Identifier | Yes | min_length=1 |
| notification_type | String | Yes | max_length=255, min_length=1 |
| preference_id | Identifier | Yes | min_length=1 |
| unsubscribed_at | DateTime | Yes | — |

### Commands

#### ClearQuietHours

- **Type**: `Notifications.ClearQuietHours.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| customer_id | Identifier | Yes | min_length=1 |

#### SetQuietHours

- **Type**: `Notifications.SetQuietHours.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| customer_id | Identifier | Yes | min_length=1 |
| end | String | Yes | max_length=5, min_length=1 |
| start | String | Yes | max_length=5, min_length=1 |

#### UpdateNotificationPreferences

- **Type**: `Notifications.UpdateNotificationPreferences.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| customer_id | Identifier | Yes | min_length=1 |
| email_enabled | Boolean | No | — |
| push_enabled | Boolean | No | — |
| sms_enabled | Boolean | No | — |

#### ResubscribeToType

- **Type**: `Notifications.ResubscribeToType.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| customer_id | Identifier | Yes | min_length=1 |
| notification_type | String | Yes | max_length=100, min_length=1 |

#### UnsubscribeFromType

- **Type**: `Notifications.UnsubscribeFromType.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| customer_id | Identifier | Yes | min_length=1 |
| notification_type | String | Yes | max_length=100, min_length=1 |
