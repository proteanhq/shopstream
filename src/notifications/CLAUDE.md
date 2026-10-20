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
- `NotificationType` (15): WELCOME, ORDER_CONFIRMATION, PAYMENT_RECEIPT, SHIPPING_UPDATE,
  DELIVERY_CONFIRMATION, DELIVERY_EXCEPTION, REVIEW_PROMPT, CART_RECOVERY, LOW_STOCK_ALERT,
  REVIEW_PUBLISHED, REVIEW_REJECTED, REFUND_NOTIFICATION, ORDER_CANCELLATION, TIER_UPGRADED,
  POINTS_REDEEMED
- `NotificationChannel`: EMAIL, SMS, PUSH, SLACK
- `NotificationStatus`: PENDING, DISPATCHING, SENT, DELIVERED, FAILED, BOUNCED, CANCELLED
- `RecipientType`: CUSTOMER, INTERNAL

### State Machine: Notification Status
PENDING → {DISPATCHING, CANCELLED}; DISPATCHING → {SENT, FAILED}; SENT → {DELIVERED, FAILED,
BOUNCED}; FAILED → {PENDING} (via retry). DISPATCHING means the dispatcher has claimed the
notification for a send, so it can no longer be cancelled or claimed again.

### Aggregate Methods
| Method | Behavior |
|--------|----------|
| `Notification.create(...)` | Factory; raises `NotificationCreated`, plus `NotificationDispatchRequested` when `scheduled_for` is None |
| `request_dispatch()` | PENDING only; raises `NotificationDispatchRequested` (v2, the notification id only) |
| `claim_dispatch()` | PENDING → DISPATCHING; raises `NotificationDispatchStarted` carrying channel, recipient, subject, body and `retry_count` |
| `mark_sent()` | DISPATCHING → SENT; raises `NotificationSent` |
| `mark_delivered()` | SENT → DELIVERED; raises `NotificationDelivered` |
| `mark_failed(reason)` | DISPATCHING or SENT → FAILED; keeps at most 500 characters of `reason`; increments `retry_count`; raises `NotificationFailed` |
| `expire_dispatch()` | DISPATCHING → FAILED through `mark_failed(STALE_DISPATCH_REASON)`; never sends |
| `mark_bounced()` | SENT → BOUNCED; raises `NotificationBounced` |
| `cancel()` | PENDING → CANCELLED; raises `NotificationCancelled` |
| `retry()` | Only FAILED and under `max_retries`; raises `NotificationRetried`, then requests dispatch again |

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

**Notification events** (`notification/events.py`): `NotificationCreated`,
`NotificationDispatchRequested` (v2; `notification/upcasters.py` drops the v1 send payload),
`NotificationDispatchStarted`, `NotificationSent`,
`NotificationDelivered`, `NotificationFailed`, `NotificationBounced`, `NotificationCancelled`,
`NotificationRetried`.

**Preference events** (`preference/events.py`): `PreferencesCreated`, `ChannelsUpdated`,
`QuietHoursSet`, `QuietHoursCleared`, `TypeUnsubscribed`, `TypeResubscribed`.

## Commands & Handlers

| File | Commands | Handler |
|------|---------|---------|
| `notification/cancellation.py` | `CancelNotification` | `CancelNotificationHandler` |
| `notification/dispatch.py` | `RecordDispatchResult` | `RecordDispatchResultHandler` |
| `notification/dispatch_expiry.py` | `ExpireStaleDispatches` | `ExpireStaleDispatchesHandler` |
| `notification/retry.py` | `RetryNotification` | `RetryNotificationHandler` |
| `notification/scheduler.py` | `ProcessScheduledNotifications` | `ProcessScheduledNotificationsHandler` |
| `preference/management.py` | `UpdateNotificationPreferences`, `SetQuietHours`, `ClearQuietHours` | `ManagePreferencesHandler` |
| `preference/subscription.py` | `UnsubscribeFromType`, `ResubscribeToType` | `ManageSubscriptionsHandler` |

## Event Handler (internal)

**File:** `notification/dispatch.py` — `NotificationDispatcher` (`part_of=Notification`), two
methods, each in its own unit of work:

1. On `NotificationDispatchRequested` (raised by `create()` for an immediate notification, by
   `request_dispatch()` from the scheduler, and by `retry()`), it loads the notification and,
   while it is PENDING, calls `claim_dispatch()`. A cancelled or already-claimed notification is
   skipped, so a redelivered or duplicate request sends nothing.
2. On `NotificationDispatchStarted`, it calls the channel adapter, then processes
   `RecordDispatchResult`, whose handler calls `mark_sent()` / `mark_failed(...)` on a
   DISPATCHING notification whose `retry_count` matches the claim's. A claim older than
   `SEND_DEADLINE` (10 minutes, shorter than the sweep's 15) is not sent and records nothing,
   so a claim the sweep can expire, and then retry, is never sent.

The send reaches no repository first, so no transaction is open during it; the fake adapters
raise `SendInsideTransactionError` (`channel/transaction_guard.py`) if one is.

Known gaps: the record step joins the send's unit of work, so a version conflict on it either
sends again (memory, proteanhq/protean#1915) or loses the result (Postgres,
proteanhq/protean#1914); `tests/notifications/application/test_record_step_conflict.py` is a
strict xfail for it. A redelivered `NotificationDispatchStarted` after a crash between the send
and the record also sends again, within the send deadline.

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
| `notification/loyalty_subscriber.py` | `loyalty::reward_account` | TierUpgraded → TIER_UPGRADED; PointsRedeemed → POINTS_REDEEMED |

Nine subscribers across eight streams — `identity::customer` is consumed by two
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
| `notification_log.py` | `NotificationLog` | Audit trail of the lifecycle events, including `NotificationDispatchStarted` (status `Dispatching`); not `NotificationDispatchRequested` |
| `notification_stats.py` | `NotificationStats` | Daily counts by type + channel |

## Scheduler

There is no resident daemon; scheduling is command-driven. `ProcessScheduledNotifications`
(triggered via the maintenance endpoint, e.g. by cron) loads the PENDING notifications whose
`scheduled_for <= as_of` (`as_of` defaults to the domain clock) and calls `request_dispatch()` on
each; the dispatcher claims and sends them after the scheduler commits. Scheduled notifications originate from the
ordering subscriber (review prompt) and cart subscriber (cart recovery); `create()` does not
request their dispatch. A retried scheduled notification is requested by `retry()` and may be
requested again by the scheduler; only one request can claim it, so it is sent once.

`ExpireStaleDispatches` (`notification/dispatch_expiry.py`, run by the same endpoint after the
scheduler) marks FAILED every notification still DISPATCHING `STALE_DISPATCH_AFTER` (15 minutes)
after its claim, with `STALE_DISPATCH_REASON`. Its `as_of` is capped at the domain clock, which
the claim time and the send deadline also read, so a future `as_of` cannot expire a claim the
send step would still send. It does not send: the send may already have
gone out, so a retry decides. A result recorded after the sweep finds FAILED and is skipped.

## API

**Package:** `api/` — `APIRouter(prefix="/notifications", tags=["notifications"])`. Preference
CRUD + quiet-hours + (un)subscribe, notification history (via `view_for(CustomerNotifications)`),
retry/cancel, and a `maintenance/process-scheduled` job endpoint that runs
`ProcessScheduledNotifications` and then `ExpireStaleDispatches`.

## Tests

`tests/notifications/{domain,application,integration,bdd}/` — aggregate/state-machine/template/
channel unit tests, handler + per-subscriber application tests, API/projection integration
tests, and BDD lifecycle/preference features.
