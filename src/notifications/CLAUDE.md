# Notifications Domain

Multi-channel customer and operational notifications (CQRS). Notifications is ShopStream's
**event-consumer hub**: it subscribes to events from across the platform and fans them out to
Email / SMS / Push / Slack via pluggable channel adapters, honoring per-customer preferences.
See `docs/notifications/` for the domain narrative + scenarios.

## Domain Composition Root

`domain.py` — `notifications = Domain(name="notifications")`. Registers `enrich_command` /
`enrich_event` via `register_command_enricher` / `register_event_enricher`.

## Configuration

`domain.toml` — PostgreSQL database, Redis broker (DB 7), Message DB event store, health port
8088. Priority lanes enabled. Environment overlays for test (`notifications_test` DB),
production (async + telemetry), and memory (in-memory/inline adapters). No cache section —
projections are database-backed.

## Aggregate: Notification (CQRS)

**File:** `notification/notification.py`

Root fields: `recipient_id`, `recipient_type` (`RecipientType`), `notification_type`
(`NotificationType`), `channel` (`NotificationChannel`), `subject`, `body` (Text),
`template_name`, `source_event_type`, `source_event_id`, `context_data` (Dict), `status`
(`Status` field with transitions), `scheduled_for`, `sent_at`, `delivered_at`,
`failure_reason`, `retry_count` (default 0), `max_retries` (default 3), `created_at`,
`updated_at`.

### Enums
- `NotificationType` (13): WELCOME, ORDER_CONFIRMATION, PAYMENT_RECEIPT, SHIPPING_UPDATE,
  DELIVERY_CONFIRMATION, DELIVERY_EXCEPTION, REVIEW_PROMPT, CART_RECOVERY, LOW_STOCK_ALERT,
  REVIEW_PUBLISHED, REVIEW_REJECTED, REFUND_NOTIFICATION, ORDER_CANCELLATION
- `NotificationChannel`: EMAIL, SMS, PUSH, SLACK
- `NotificationStatus`: PENDING, SENT, DELIVERED, FAILED, BOUNCED, CANCELLED
- `RecipientType`: CUSTOMER, INTERNAL

### State Machine: Notification Status
PENDING → {SENT, FAILED, CANCELLED}; SENT → {DELIVERED, FAILED, BOUNCED}; FAILED → {PENDING}
(via retry).

### Aggregate Methods
| Method | Behavior |
|--------|----------|
| `Notification.create(...)` | Factory; raises `NotificationCreated` |
| `mark_sent()` | PENDING → SENT; raises `NotificationSent` |
| `mark_delivered()` | SENT → DELIVERED; raises `NotificationDelivered` |
| `mark_failed(reason)` | Increments `retry_count`; raises `NotificationFailed` |
| `mark_bounced()` | SENT → BOUNCED; raises `NotificationBounced` |
| `cancel()` | PENDING → CANCELLED; raises `NotificationCancelled` |
| `retry()` | Only FAILED and under `max_retries`; raises `NotificationRetried` |

## Aggregate: NotificationPreference (CQRS)

**File:** `preference/preference.py`

Root fields: `customer_id` (unique), `email_enabled` (default True), `sms_enabled`,
`push_enabled`, `quiet_hours_start`/`quiet_hours_end` (`HH:MM`), `unsubscribed_types`
(List), `created_at`, `updated_at`.

### Aggregate Methods
| Method | Behavior |
|--------|----------|
| `NotificationPreference.create_default(customer_id)` | Factory; raises `PreferencesCreated` |
| `update_channels(...)` | Raises `ChannelsUpdated` |
| `set_quiet_hours(start, end)` / `clear_quiet_hours()` | Raises `QuietHoursSet` / `QuietHoursCleared` |
| `unsubscribe_from(type)` / `resubscribe_to(type)` | Raises `TypeUnsubscribed` / `TypeResubscribed` |

Query helpers: `is_subscribed_to`, `get_enabled_channels`.

Neither aggregate has child entities or value objects; the enums are plain `choices`.

## Events

**Notification events** (`notification/events.py`): `NotificationCreated`, `NotificationSent`,
`NotificationDelivered`, `NotificationFailed`, `NotificationBounced`, `NotificationCancelled`,
`NotificationRetried`.

**Preference events** (`preference/events.py`): `PreferencesCreated`, `ChannelsUpdated`,
`QuietHoursSet`, `QuietHoursCleared`, `TypeUnsubscribed`, `TypeResubscribed`.

## Commands & Handlers

| File | Commands | Handler |
|------|---------|---------|
| `notification/cancellation.py` | `CancelNotification` | `CancelNotificationHandler` |
| `notification/retry.py` | `RetryNotification` | `RetryNotificationHandler` |
| `notification/scheduler.py` | `ProcessScheduledNotifications` | `ProcessScheduledNotificationsHandler` |
| `preference/management.py` | `UpdateNotificationPreferences`, `SetQuietHours`, `ClearQuietHours` | `ManagePreferencesHandler` |
| `preference/subscription.py` | `UnsubscribeFromType`, `ResubscribeToType` | `ManageSubscriptionsHandler` |

## Event Handler (internal)

**File:** `notification/dispatch.py` — `NotificationDispatcher` (`part_of=Notification`). On
`NotificationCreated`, dispatches immediate (non-scheduled) PENDING notifications via the
channel adapter, then `mark_sent()` / `mark_failed(...)`.

## Cross-Domain Subscribers (the ACL hub)

All use the subscriber (ACL) pattern: `__call__(payload: dict)`, branch on
`payload["metadata"]["headers"]["type"]`, translate to notifications via the helpers in
`notification/helpers.py` (`create_notifications_for_customer` / `create_internal_notification`).

| File | stream | Reacts to |
|------|--------|-----------|
| `notification/identity_subscriber.py` | `identity::customer` | CustomerRegistered → WELCOME |
| `preference/identity_subscriber.py` | `identity::customer` | CustomerRegistered → default preferences |
| `notification/ordering_subscriber.py` | `ordering::order` | OrderCreated → ORDER_CONFIRMATION; OrderDelivered → REVIEW_PROMPT (+7d) |
| `notification/cart_subscriber.py` | `ordering::cart` | CartAbandoned → CART_RECOVERY (+24h) |
| `notification/payment_subscriber.py` | `payments::payment` | PaymentSucceeded → PAYMENT_RECEIPT; RefundCompleted → REFUND_NOTIFICATION |
| `notification/fulfillment_subscriber.py` | `fulfillment::fulfillment` | shipment/delivery events (logged; events lack customer_id) |
| `notification/inventory_subscriber.py` | `inventory::inventory_item` | LowStockDetected → internal LOW_STOCK_ALERT (Slack) |
| `notification/review_subscriber.py` | `reviews::review` | ReviewApproved → REVIEW_PUBLISHED; ReviewRejected → REVIEW_REJECTED |

Eight subscribers across seven streams — `identity::customer` is consumed by two
(welcome + preferences).

## Channels & Templates

- **Channels:** `channel/` — port/adapter per channel (`email_port.py`/`fake_email.py`,
  `sms_port.py`/`fake_sms.py`, `push_port.py`/`fake_push.py`, `slack_port.py`/`fake_slack.py`).
  `get_channel(channel_type)` returns a cached singleton adapter; `reset_channels()` is a test
  helper.
- **Templates:** `templates/` — one class per `NotificationType` with `default_channels` and
  `render(context) -> {subject, body}`; `get_template(notification_type)` looks them up.

## Projections

**Directory:** `projections/` — all database-backed.

| File | Projection | Purpose |
|------|-----------|---------|
| `customer_notifications.py` | `CustomerNotifications` | Per-customer notification feed |
| `customer_preferences.py` | `CustomerPreferences` | Per-customer preference view |
| `failed_notifications.py` | `FailedNotifications` | Retry queue |
| `notification_log.py` | `NotificationLog` | Full audit trail (all 7 events) |
| `notification_stats.py` | `NotificationStats` | Daily counts by type + channel |

## Scheduler

There is no resident daemon; scheduling is command-driven. `ProcessScheduledNotifications`
(triggered via the maintenance endpoint, e.g. by cron) dispatches PENDING notifications whose
`scheduled_for <= as_of`. Scheduled notifications originate from the ordering subscriber (review
prompt) and cart subscriber (cart recovery); the dispatch handler skips them at creation time.

## API

**Package:** `api/` — `APIRouter(prefix="/notifications", tags=["notifications"])`. Preference
CRUD + quiet-hours + (un)subscribe, notification history (via `view_for(CustomerNotifications)`),
retry/cancel, and a `maintenance/process-scheduled` job endpoint.

## Tests

`tests/notifications/{domain,application,integration,bdd}/` — aggregate/state-machine/template/
channel unit tests, handler + per-subscriber application tests, API/projection integration
tests, and BDD lifecycle/preference features.
