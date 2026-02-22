"""FastAPI routes for the Notifications domain.

Thin adapters that translate HTTP requests into domain commands.
No business logic — just schema→command→response translation.
"""

import json
from datetime import datetime as dt_datetime

from fastapi import APIRouter
from notifications.api.schemas import (
    CancelNotificationRequest,
    NotificationListResponse,
    NotificationResponse,
    PreferencesResponse,
    ResubscribeRequest,
    SetQuietHoursRequest,
    StatusResponse,
    UnsubscribeRequest,
    UpdatePreferencesRequest,
)
from notifications.notification.cancellation import CancelNotification
from notifications.notification.retry import RetryNotification
from notifications.preference.management import (
    ClearQuietHours,
    SetQuietHours,
    UpdateNotificationPreferences,
)
from notifications.preference.preference import NotificationPreference
from notifications.preference.subscription import ResubscribeToType, UnsubscribeFromType
from notifications.projections.customer_notifications import CustomerNotifications
from protean.utils.globals import current_domain
from pydantic import BaseModel as PydanticBaseModel

router = APIRouter(prefix="/notifications", tags=["notifications"])


# ---------------------------------------------------------------------------
# Preferences
# ---------------------------------------------------------------------------
@router.get("/preferences/{customer_id}", response_model=PreferencesResponse)
async def get_preferences(customer_id: str) -> PreferencesResponse:
    """Get a customer's notification preferences."""
    repo = current_domain.repository_for(NotificationPreference)
    prefs = repo._dao.query.filter(customer_id=customer_id).all().items
    if not prefs:
        # Return defaults if no preferences exist
        return PreferencesResponse(
            preference_id="",
            customer_id=customer_id,
            email_enabled=True,
            sms_enabled=False,
            push_enabled=False,
            unsubscribed_types=[],
        )
    pref = prefs[0]
    unsub = json.loads(pref.unsubscribed_types) if pref.unsubscribed_types else []
    return PreferencesResponse(
        preference_id=str(pref.id),
        customer_id=str(pref.customer_id),
        email_enabled=pref.email_enabled,
        sms_enabled=pref.sms_enabled,
        push_enabled=pref.push_enabled,
        quiet_hours_start=pref.quiet_hours_start,
        quiet_hours_end=pref.quiet_hours_end,
        unsubscribed_types=unsub,
    )


@router.put("/preferences/{customer_id}", response_model=StatusResponse)
async def update_preferences(customer_id: str, body: UpdatePreferencesRequest) -> StatusResponse:
    """Update a customer's notification channel preferences."""
    command = UpdateNotificationPreferences(
        customer_id=customer_id,
        email_enabled=body.email_enabled,
        sms_enabled=body.sms_enabled,
        push_enabled=body.push_enabled,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@router.put("/preferences/{customer_id}/quiet-hours", response_model=StatusResponse)
async def set_quiet_hours(customer_id: str, body: SetQuietHoursRequest) -> StatusResponse:
    """Set a customer's do-not-disturb window."""
    command = SetQuietHours(
        customer_id=customer_id,
        start=body.start,
        end=body.end,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@router.delete("/preferences/{customer_id}/quiet-hours", response_model=StatusResponse)
async def clear_quiet_hours(customer_id: str) -> StatusResponse:
    """Remove a customer's do-not-disturb window."""
    command = ClearQuietHours(customer_id=customer_id)
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@router.post(
    "/preferences/{customer_id}/unsubscribe",
    status_code=201,
    response_model=StatusResponse,
)
async def unsubscribe(customer_id: str, body: UnsubscribeRequest) -> StatusResponse:
    """Unsubscribe from a specific notification type."""
    command = UnsubscribeFromType(
        customer_id=customer_id,
        notification_type=body.notification_type,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@router.post(
    "/preferences/{customer_id}/resubscribe",
    status_code=201,
    response_model=StatusResponse,
)
async def resubscribe(customer_id: str, body: ResubscribeRequest) -> StatusResponse:
    """Resubscribe to a previously unsubscribed notification type."""
    command = ResubscribeToType(
        customer_id=customer_id,
        notification_type=body.notification_type,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


# ---------------------------------------------------------------------------
# Notification history
# ---------------------------------------------------------------------------
@router.get("/{customer_id}", response_model=NotificationListResponse)
async def get_customer_notifications(
    customer_id: str,
) -> NotificationListResponse:
    """Get a customer's notification history."""
    repo = current_domain.repository_for(CustomerNotifications)
    try:
        results = repo._dao.query.filter(customer_id=customer_id).all().items
    except Exception:
        results = []

    return NotificationListResponse(
        notifications=[
            NotificationResponse(
                notification_id=str(n.notification_id),
                notification_type=n.notification_type,
                channel=n.channel,
                subject=n.subject,
                status=n.status,
                created_at=str(n.created_at) if n.created_at else None,
            )
            for n in results
        ]
    )


# ---------------------------------------------------------------------------
# Notification lifecycle
# ---------------------------------------------------------------------------
@router.post("/{notification_id}/retry", status_code=201, response_model=StatusResponse)
async def retry_notification(notification_id: str) -> StatusResponse:
    """Retry a failed notification."""
    command = RetryNotification(notification_id=notification_id)
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@router.put("/{notification_id}/cancel", response_model=StatusResponse)
async def cancel_notification(notification_id: str, body: CancelNotificationRequest) -> StatusResponse:
    """Cancel a pending notification."""
    command = CancelNotification(
        notification_id=notification_id,
        reason=body.reason,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


# ---------------------------------------------------------------------------
# Maintenance — periodic background job endpoints
# ---------------------------------------------------------------------------


class ProcessScheduledRequest(PydanticBaseModel):
    as_of: dt_datetime | None = None


class ProcessScheduledResponse(PydanticBaseModel):
    status: str = "ok"


@router.post("/maintenance/process-scheduled", response_model=ProcessScheduledResponse)
async def process_scheduled_notifications(
    body: ProcessScheduledRequest | None = None,
) -> ProcessScheduledResponse:
    """Dispatch due scheduled notifications.

    Designed to be called periodically by an external scheduler (e.g., every 15 minutes).
    Idempotent: already-sent notifications are skipped.
    """
    from notifications.notification.scheduler import ProcessScheduledNotifications

    command = ProcessScheduledNotifications(as_of=body.as_of if body else None)
    current_domain.process(command, asynchronous=False)
    return ProcessScheduledResponse()
