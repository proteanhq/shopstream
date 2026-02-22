"""Pydantic request/response models for the Notifications API.

API schemas are separate from Protean commands (anti-corruption pattern).
"""

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------
class UpdatePreferencesRequest(BaseModel):
    email_enabled: bool | None = None
    sms_enabled: bool | None = None
    push_enabled: bool | None = None


class SetQuietHoursRequest(BaseModel):
    start: str = Field(..., pattern=r"^\d{2}:\d{2}$", examples=["22:00"])
    end: str = Field(..., pattern=r"^\d{2}:\d{2}$", examples=["08:00"])


class UnsubscribeRequest(BaseModel):
    notification_type: str = Field(
        ...,
        examples=["CartRecovery"],
        description="NotificationType enum value to unsubscribe from",
    )


class ResubscribeRequest(BaseModel):
    notification_type: str = Field(
        ...,
        examples=["CartRecovery"],
        description="NotificationType enum value to resubscribe to",
    )


class RetryNotificationRequest(BaseModel):
    pass  # No body needed — notification_id comes from path


class CancelNotificationRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------
class StatusResponse(BaseModel):
    status: str = "ok"


class PreferencesResponse(BaseModel):
    preference_id: str
    customer_id: str
    email_enabled: bool
    sms_enabled: bool
    push_enabled: bool
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    unsubscribed_types: list[str] = []


class NotificationResponse(BaseModel):
    notification_id: str
    notification_type: str
    channel: str
    subject: str | None = None
    status: str
    created_at: str | None = None


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]
