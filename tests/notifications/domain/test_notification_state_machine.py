"""Tests for Notification state machine — valid transitions and invalid transition guards."""

import pytest
from notifications.notification.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)
from protean.exceptions import ValidationError


def _make_notification(**overrides):
    defaults = {
        "recipient_id": "cust-001",
        "notification_type": NotificationType.WELCOME.value,
        "channel": NotificationChannel.EMAIL.value,
        "body": "Welcome to ShopStream!",
    }
    defaults.update(overrides)
    return Notification.create(**defaults)


def _notification_at_state(target_status):
    """Create a notification and advance it to the desired state."""
    n = _make_notification()
    n._events.clear()

    if target_status == NotificationStatus.PENDING:
        return n

    if target_status == NotificationStatus.SENT:
        n.mark_sent()
        n._events.clear()
        return n

    if target_status == NotificationStatus.DELIVERED:
        n.mark_sent()
        n._events.clear()
        n.mark_delivered()
        n._events.clear()
        return n

    if target_status == NotificationStatus.FAILED:
        n.mark_failed("Delivery error")
        n._events.clear()
        return n

    if target_status == NotificationStatus.BOUNCED:
        n.mark_sent()
        n._events.clear()
        n.mark_bounced("Invalid address")
        n._events.clear()
        return n

    if target_status == NotificationStatus.CANCELLED:
        n.cancel("No longer needed")
        n._events.clear()
        return n

    raise ValueError(f"Cannot create notification at state {target_status}")


# ---------------------------------------------------------------
# Happy path transitions
# ---------------------------------------------------------------
class TestValidTransitions:
    def test_pending_to_sent(self):
        n = _notification_at_state(NotificationStatus.PENDING)
        n.mark_sent()
        assert n.status == NotificationStatus.SENT.value

    def test_pending_to_failed(self):
        n = _notification_at_state(NotificationStatus.PENDING)
        n.mark_failed("Connection timeout")
        assert n.status == NotificationStatus.FAILED.value

    def test_pending_to_cancelled(self):
        n = _notification_at_state(NotificationStatus.PENDING)
        n.cancel("User opted out")
        assert n.status == NotificationStatus.CANCELLED.value

    def test_sent_to_delivered(self):
        n = _notification_at_state(NotificationStatus.SENT)
        n.mark_delivered()
        assert n.status == NotificationStatus.DELIVERED.value

    def test_sent_to_failed(self):
        n = _notification_at_state(NotificationStatus.SENT)
        n.mark_failed("Recipient rejected")
        assert n.status == NotificationStatus.FAILED.value

    def test_sent_to_bounced(self):
        n = _notification_at_state(NotificationStatus.SENT)
        n.mark_bounced("Address not found")
        assert n.status == NotificationStatus.BOUNCED.value

    def test_failed_to_pending_via_retry(self):
        n = _notification_at_state(NotificationStatus.FAILED)
        n.retry()
        assert n.status == NotificationStatus.PENDING.value


# ---------------------------------------------------------------
# Invalid transitions
# ---------------------------------------------------------------
class TestInvalidTransitions:
    def test_cannot_send_already_sent(self):
        n = _notification_at_state(NotificationStatus.SENT)
        with pytest.raises(ValidationError) as exc:
            n.mark_sent()
        assert "Cannot transition" in str(exc.value)

    def test_cannot_deliver_pending(self):
        n = _notification_at_state(NotificationStatus.PENDING)
        with pytest.raises(ValidationError) as exc:
            n.mark_delivered()
        assert "Cannot transition" in str(exc.value)

    def test_cannot_cancel_sent(self):
        n = _notification_at_state(NotificationStatus.SENT)
        with pytest.raises(ValidationError) as exc:
            n.cancel("Too late")
        assert "Cannot transition" in str(exc.value)

    def test_cannot_bounce_pending(self):
        n = _notification_at_state(NotificationStatus.PENDING)
        with pytest.raises(ValidationError) as exc:
            n.mark_bounced("Bad address")
        assert "Cannot transition" in str(exc.value)

    def test_delivered_is_terminal(self):
        n = _notification_at_state(NotificationStatus.DELIVERED)
        with pytest.raises(ValidationError):
            n.mark_sent()

    def test_bounced_is_terminal(self):
        n = _notification_at_state(NotificationStatus.BOUNCED)
        with pytest.raises(ValidationError):
            n.mark_sent()

    def test_cancelled_is_terminal(self):
        n = _notification_at_state(NotificationStatus.CANCELLED)
        with pytest.raises(ValidationError):
            n.mark_sent()

    def test_cannot_cancel_failed(self):
        n = _notification_at_state(NotificationStatus.FAILED)
        with pytest.raises(ValidationError) as exc:
            n.cancel("Giving up")
        assert "Cannot transition" in str(exc.value)

    def test_cannot_deliver_failed(self):
        n = _notification_at_state(NotificationStatus.FAILED)
        with pytest.raises(ValidationError) as exc:
            n.mark_delivered()
        assert "Cannot transition" in str(exc.value)

    def test_cannot_bounce_failed(self):
        n = _notification_at_state(NotificationStatus.FAILED)
        with pytest.raises(ValidationError) as exc:
            n.mark_bounced("Bad address")
        assert "Cannot transition" in str(exc.value)


# ---------------------------------------------------------------
# mark_sent details
# ---------------------------------------------------------------
class TestMarkSent:
    def test_sets_sent_at(self):
        n = _notification_at_state(NotificationStatus.PENDING)
        n.mark_sent()
        assert n.sent_at is not None

    def test_updates_updated_at(self):
        n = _notification_at_state(NotificationStatus.PENDING)
        old_updated = n.updated_at
        n.mark_sent()
        assert n.updated_at >= old_updated

    def test_raises_notification_sent_event(self):
        n = _notification_at_state(NotificationStatus.PENDING)
        n.mark_sent()
        assert len(n._events) == 1
        event = n._events[0]
        assert event.__class__.__name__ == "NotificationSent"
        assert str(event.notification_id) == str(n.id)
        assert event.sent_at is not None


# ---------------------------------------------------------------
# mark_delivered details
# ---------------------------------------------------------------
class TestMarkDelivered:
    def test_sets_delivered_at(self):
        n = _notification_at_state(NotificationStatus.SENT)
        n.mark_delivered()
        assert n.delivered_at is not None

    def test_raises_notification_delivered_event(self):
        n = _notification_at_state(NotificationStatus.SENT)
        n.mark_delivered()
        assert len(n._events) == 1
        event = n._events[0]
        assert event.__class__.__name__ == "NotificationDelivered"
        assert event.delivered_at is not None


# ---------------------------------------------------------------
# mark_failed details
# ---------------------------------------------------------------
class TestMarkFailed:
    def test_sets_failure_reason(self):
        n = _notification_at_state(NotificationStatus.PENDING)
        n.mark_failed("SMTP error 550")
        assert n.failure_reason == "SMTP error 550"

    def test_increments_retry_count(self):
        n = _notification_at_state(NotificationStatus.PENDING)
        assert n.retry_count == 0
        n.mark_failed("First failure")
        assert n.retry_count == 1

    def test_raises_notification_failed_event(self):
        n = _notification_at_state(NotificationStatus.PENDING)
        n.mark_failed("Connection refused")
        assert len(n._events) == 1
        event = n._events[0]
        assert event.__class__.__name__ == "NotificationFailed"
        assert event.reason == "Connection refused"
        assert event.retry_count == 1
        assert event.max_retries == 3


# ---------------------------------------------------------------
# mark_bounced details
# ---------------------------------------------------------------
class TestMarkBounced:
    def test_sets_failure_reason(self):
        n = _notification_at_state(NotificationStatus.SENT)
        n.mark_bounced("Hard bounce: address invalid")
        assert n.failure_reason == "Hard bounce: address invalid"

    def test_raises_notification_bounced_event(self):
        n = _notification_at_state(NotificationStatus.SENT)
        n.mark_bounced("Hard bounce")
        assert len(n._events) == 1
        event = n._events[0]
        assert event.__class__.__name__ == "NotificationBounced"
        assert event.reason == "Hard bounce"


# ---------------------------------------------------------------
# cancel details
# ---------------------------------------------------------------
class TestCancel:
    def test_sets_failure_reason_to_cancel_reason(self):
        n = _notification_at_state(NotificationStatus.PENDING)
        n.cancel("Customer unsubscribed")
        assert n.failure_reason == "Customer unsubscribed"

    def test_raises_notification_cancelled_event(self):
        n = _notification_at_state(NotificationStatus.PENDING)
        n.cancel("No longer needed")
        assert len(n._events) == 1
        event = n._events[0]
        assert event.__class__.__name__ == "NotificationCancelled"
        assert event.reason == "No longer needed"


# ---------------------------------------------------------------
# retry details
# ---------------------------------------------------------------
class TestRetry:
    def test_retry_resets_to_pending(self):
        n = _notification_at_state(NotificationStatus.FAILED)
        n.retry()
        assert n.status == NotificationStatus.PENDING.value

    def test_retry_clears_failure_reason(self):
        n = _notification_at_state(NotificationStatus.FAILED)
        assert n.failure_reason is not None
        n.retry()
        assert n.failure_reason is None

    def test_retry_raises_notification_retried_event(self):
        n = _notification_at_state(NotificationStatus.FAILED)
        n.retry()
        assert len(n._events) == 1
        event = n._events[0]
        assert event.__class__.__name__ == "NotificationRetried"
        assert event.retry_count == 1  # Failed once = retry_count 1

    def test_cannot_retry_non_failed_notification(self):
        n = _notification_at_state(NotificationStatus.PENDING)
        with pytest.raises(ValidationError) as exc:
            n.retry()
        assert "Only failed notifications can be retried" in str(exc.value)

    def test_cannot_retry_beyond_max_retries(self):
        n = _make_notification(max_retries=2)
        n._events.clear()
        # Fail and retry twice
        n.mark_failed("Attempt 1")
        n._events.clear()
        n.retry()
        n._events.clear()
        n.mark_failed("Attempt 2")
        n._events.clear()
        # Third retry should fail (retry_count == 2, max_retries == 2)
        with pytest.raises(ValidationError) as exc:
            n.retry()
        assert "Maximum retry attempts exceeded" in str(exc.value)

    def test_retry_preserves_retry_count(self):
        n = _make_notification()
        n._events.clear()
        n.mark_failed("First failure")
        n._events.clear()
        assert n.retry_count == 1
        n.retry()
        # retry doesn't change retry_count — mark_failed does
        assert n.retry_count == 1
