"""Notifications API — FastAPI router re-export."""

from notifications.api.routes import router as notification_router

__all__ = ["notification_router"]
