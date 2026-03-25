## Command Handlers: Notification

```mermaid
flowchart LR
    subgraph command_handlers["Command Handlers"]
        ch_notifications_notification_cancellation_CancelNotificationHandler[CancelNotificationHandler]
        ch_notifications_notification_retry_RetryNotificationHandler[RetryNotificationHandler]
        ch_notifications_notification_scheduler_ProcessScheduledNotificationsHandler[ProcessScheduledNotificationsHandler]
    end
    cmd_notifications_notification_cancellation_CancelNotification[/CancelNotification/] --> ch_notifications_notification_cancellation_CancelNotificationHandler
    ch_notifications_notification_cancellation_CancelNotificationHandler --> agg_notifications_notification_notification_Notification[Notification]
    cmd_notifications_notification_retry_RetryNotification[/RetryNotification/] --> ch_notifications_notification_retry_RetryNotificationHandler
    ch_notifications_notification_retry_RetryNotificationHandler --> agg_notifications_notification_notification_Notification[Notification]
    cmd_notifications_notification_scheduler_ProcessScheduledNotifications[/ProcessScheduledNotifications/] --> ch_notifications_notification_scheduler_ProcessScheduledNotificationsHandler
    ch_notifications_notification_scheduler_ProcessScheduledNotificationsHandler --> agg_notifications_notification_notification_Notification[Notification]
```

## Command Handlers: NotificationPreference

```mermaid
flowchart LR
    subgraph command_handlers["Command Handlers"]
        ch_notifications_preference_management_ManagePreferencesHandler[ManagePreferencesHandler]
        ch_notifications_preference_subscription_ManageSubscriptionsHandler[ManageSubscriptionsHandler]
    end
    cmd_notifications_preference_management_ClearQuietHours[/ClearQuietHours/] --> ch_notifications_preference_management_ManagePreferencesHandler
    cmd_notifications_preference_management_SetQuietHours[/SetQuietHours/] --> ch_notifications_preference_management_ManagePreferencesHandler
    cmd_notifications_preference_management_UpdateNotificationPreferences[/UpdateNotificationPreferences/] --> ch_notifications_preference_management_ManagePreferencesHandler
    ch_notifications_preference_management_ManagePreferencesHandler --> agg_notifications_preference_preference_NotificationPreference[NotificationPreference]
    cmd_notifications_preference_subscription_ResubscribeToType[/ResubscribeToType/] --> ch_notifications_preference_subscription_ManageSubscriptionsHandler
    cmd_notifications_preference_subscription_UnsubscribeFromType[/UnsubscribeFromType/] --> ch_notifications_preference_subscription_ManageSubscriptionsHandler
    ch_notifications_preference_subscription_ManageSubscriptionsHandler --> agg_notifications_preference_preference_NotificationPreference[NotificationPreference]
```

## Event Handlers

```mermaid
flowchart TD
    subgraph event_handlers["Event Handlers"]
        eh_notifications_notification_dispatch_NotificationDispatcher[NotificationDispatcher]
    end
    evt_notifications_notification_events_NotificationCreated([NotificationCreated]) --> eh_notifications_notification_dispatch_NotificationDispatcher
```

## Subscribers

```mermaid
flowchart TD
    subgraph subscribers["Subscribers"]
        sub_notifications_notification_cart_subscriber_CartEventsSubscriber[CartEventsSubscriber\nstream: ordering::cart]
        sub_notifications_notification_fulfillment_subscriber_FulfillmentEventsSubscriber[FulfillmentEventsSubscriber\nstream: fulfillment::fulfillment]
        sub_notifications_notification_identity_subscriber_IdentityEventsSubscriber[IdentityEventsSubscriber\nstream: identity::customer]
        sub_notifications_notification_inventory_subscriber_InventoryEventsSubscriber[InventoryEventsSubscriber\nstream: inventory::inventory_item]
        sub_notifications_notification_ordering_subscriber_OrderingEventsSubscriber[OrderingEventsSubscriber\nstream: ordering::order]
        sub_notifications_notification_payment_subscriber_PaymentEventsSubscriber[PaymentEventsSubscriber\nstream: payments::payment]
        sub_notifications_notification_review_subscriber_ReviewEventsSubscriber[ReviewEventsSubscriber\nstream: reviews::review]
        sub_notifications_preference_identity_subscriber_PreferenceIdentitySubscriber[PreferenceIdentitySubscriber\nstream: identity::customer]
    end
```

## Projector: CustomerNotifications

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_notifications_projections_customer_notifications_CustomerNotificationsProjector[CustomerNotificationsProjector → CustomerNotifications]
    end
    evt_notifications_notification_events_NotificationCreated([NotificationCreated]) --> proj_notifications_projections_customer_notifications_CustomerNotificationsProjector
    evt_notifications_notification_events_NotificationDelivered([NotificationDelivered]) --> proj_notifications_projections_customer_notifications_CustomerNotificationsProjector
    evt_notifications_notification_events_NotificationFailed([NotificationFailed]) --> proj_notifications_projections_customer_notifications_CustomerNotificationsProjector
    evt_notifications_notification_events_NotificationSent([NotificationSent]) --> proj_notifications_projections_customer_notifications_CustomerNotificationsProjector
```

## Projector: CustomerPreferences

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_notifications_projections_customer_preferences_CustomerPreferencesProjector[CustomerPreferencesProjector → CustomerPreferences]
    end
    evt_notifications_preference_events_ChannelsUpdated([ChannelsUpdated]) --> proj_notifications_projections_customer_preferences_CustomerPreferencesProjector
    evt_notifications_preference_events_PreferencesCreated([PreferencesCreated]) --> proj_notifications_projections_customer_preferences_CustomerPreferencesProjector
    evt_notifications_preference_events_QuietHoursCleared([QuietHoursCleared]) --> proj_notifications_projections_customer_preferences_CustomerPreferencesProjector
    evt_notifications_preference_events_QuietHoursSet([QuietHoursSet]) --> proj_notifications_projections_customer_preferences_CustomerPreferencesProjector
    evt_notifications_preference_events_TypeResubscribed([TypeResubscribed]) --> proj_notifications_projections_customer_preferences_CustomerPreferencesProjector
    evt_notifications_preference_events_TypeUnsubscribed([TypeUnsubscribed]) --> proj_notifications_projections_customer_preferences_CustomerPreferencesProjector
```

## Projector: FailedNotifications

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_notifications_projections_failed_notifications_FailedNotificationsProjector[FailedNotificationsProjector → FailedNotifications]
    end
    evt_notifications_notification_events_NotificationFailed([NotificationFailed]) --> proj_notifications_projections_failed_notifications_FailedNotificationsProjector
    evt_notifications_notification_events_NotificationRetried([NotificationRetried]) --> proj_notifications_projections_failed_notifications_FailedNotificationsProjector
    evt_notifications_notification_events_NotificationSent([NotificationSent]) --> proj_notifications_projections_failed_notifications_FailedNotificationsProjector
```

## Projector: NotificationLog

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_notifications_projections_notification_log_NotificationLogProjector[NotificationLogProjector → NotificationLog]
    end
    evt_notifications_notification_events_NotificationBounced([NotificationBounced]) --> proj_notifications_projections_notification_log_NotificationLogProjector
    evt_notifications_notification_events_NotificationCancelled([NotificationCancelled]) --> proj_notifications_projections_notification_log_NotificationLogProjector
    evt_notifications_notification_events_NotificationCreated([NotificationCreated]) --> proj_notifications_projections_notification_log_NotificationLogProjector
    evt_notifications_notification_events_NotificationDelivered([NotificationDelivered]) --> proj_notifications_projections_notification_log_NotificationLogProjector
    evt_notifications_notification_events_NotificationFailed([NotificationFailed]) --> proj_notifications_projections_notification_log_NotificationLogProjector
    evt_notifications_notification_events_NotificationRetried([NotificationRetried]) --> proj_notifications_projections_notification_log_NotificationLogProjector
    evt_notifications_notification_events_NotificationSent([NotificationSent]) --> proj_notifications_projections_notification_log_NotificationLogProjector
```

## Projector: NotificationStats

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_notifications_projections_notification_stats_NotificationStatsProjector[NotificationStatsProjector → NotificationStats]
    end
    evt_notifications_notification_events_NotificationSent([NotificationSent]) --> proj_notifications_projections_notification_stats_NotificationStatsProjector
```
