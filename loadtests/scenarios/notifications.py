"""Notifications domain load test scenarios.

Four stateful SequentialTaskSet journeys covering preference management,
quiet hours configuration, and notification lifecycle (unsubscribe/resubscribe).

Each journey registers a customer via the Identity API first, which triggers
the CustomerRegistered cross-domain event that auto-creates notification
preferences.
"""

import random
import time

from locust import HttpUser, SequentialTaskSet, between, task

from loadtests.data_generators import (
    customer_name,
    date_of_birth,
    notification_preferences_data,
    notification_type,
    quiet_hours_data,
    unique_external_id,
    valid_email,
    valid_phone,
)
from loadtests.helpers.response import extract_error_detail
from loadtests.helpers.state import NotificationState


def _register_customer(client):
    """Register a customer and return the customer_id, or None on failure."""
    first, last = customer_name()
    payload = {
        "external_id": unique_external_id(),
        "email": valid_email(),
        "first_name": first,
        "last_name": last,
        "phone": valid_phone(),
        "date_of_birth": date_of_birth(),
    }
    with client.post(
        "/customers",
        json=payload,
        catch_response=True,
        name="POST /customers",
    ) as resp:
        if resp.status_code == 201:
            return resp.json()["customer_id"]
        resp.failure(f"Registration failed: {resp.status_code} — {extract_error_detail(resp)}")
        return None


class PreferenceManagementJourney(SequentialTaskSet):
    """Register Customer -> Update Preferences -> Get -> Set Quiet Hours -> Verify.

    Models a customer configuring their notification channels and quiet hours.
    Exercises: UpdatePreferences, SetQuietHours commands and preferences projection.
    """

    def on_start(self):
        self.state = NotificationState()

    @task
    def register_customer(self):
        customer_id = _register_customer(self.client)
        if not customer_id:
            self.interrupt()
            return
        self.state.customer_id = customer_id
        # Brief pause for Engine to process CustomerRegistered -> create preferences
        time.sleep(0.5)

    @task
    def update_preferences(self):
        with self.client.put(
            f"/notifications/preferences/{self.state.customer_id}",
            json=notification_preferences_data(),
            catch_response=True,
            name="PUT /notifications/preferences/{id}",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Update preferences failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def get_preferences(self):
        with self.client.get(
            f"/notifications/preferences/{self.state.customer_id}",
            catch_response=True,
            name="GET /notifications/preferences/{id}",
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                self.state.preference_id = data.get("preference_id")
            else:
                resp.failure(f"Get preferences failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def set_quiet_hours(self):
        with self.client.put(
            f"/notifications/preferences/{self.state.customer_id}/quiet-hours",
            json=quiet_hours_data(),
            catch_response=True,
            name="PUT /notifications/preferences/{id}/quiet-hours",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Set quiet hours failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def verify_preferences(self):
        with self.client.get(
            f"/notifications/preferences/{self.state.customer_id}",
            catch_response=True,
            name="GET /notifications/preferences/{id}",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Verify preferences failed: {resp.status_code}")

    @task
    def done(self):
        self.interrupt()


class QuietHoursLifecycleJourney(SequentialTaskSet):
    """Register Customer -> Update Preferences -> Set Quiet Hours -> Remove -> Verify.

    Models a customer setting then removing quiet hours.
    Exercises: SetQuietHours, RemoveQuietHours commands.
    """

    def on_start(self):
        self.state = NotificationState()

    @task
    def register_customer(self):
        customer_id = _register_customer(self.client)
        if not customer_id:
            self.interrupt()
            return
        self.state.customer_id = customer_id
        time.sleep(0.5)

    @task
    def update_preferences(self):
        with self.client.put(
            f"/notifications/preferences/{self.state.customer_id}",
            json=notification_preferences_data(),
            catch_response=True,
            name="PUT /notifications/preferences/{id}",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Update preferences failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def set_quiet_hours(self):
        with self.client.put(
            f"/notifications/preferences/{self.state.customer_id}/quiet-hours",
            json=quiet_hours_data(),
            catch_response=True,
            name="PUT /notifications/preferences/{id}/quiet-hours",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Set quiet hours failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def remove_quiet_hours(self):
        with self.client.delete(
            f"/notifications/preferences/{self.state.customer_id}/quiet-hours",
            catch_response=True,
            name="DELETE /notifications/preferences/{id}/quiet-hours",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Remove quiet hours failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def verify_no_quiet_hours(self):
        with self.client.get(
            f"/notifications/preferences/{self.state.customer_id}",
            catch_response=True,
            name="GET /notifications/preferences/{id}",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Verify preferences failed: {resp.status_code}")

    @task
    def done(self):
        self.interrupt()


class UnsubscribeResubscribeJourney(SequentialTaskSet):
    """Register Customer -> Update Preferences -> Unsubscribe -> History -> Resubscribe.

    Models a customer opting out of a notification type and then opting back in.
    Exercises: UnsubscribeFromType, ResubscribeToType commands and history query.
    """

    def on_start(self):
        self.state = NotificationState()
        self._unsub_type = notification_type()

    @task
    def register_customer(self):
        customer_id = _register_customer(self.client)
        if not customer_id:
            self.interrupt()
            return
        self.state.customer_id = customer_id
        time.sleep(0.5)

    @task
    def update_preferences(self):
        with self.client.put(
            f"/notifications/preferences/{self.state.customer_id}",
            json=notification_preferences_data(),
            catch_response=True,
            name="PUT /notifications/preferences/{id}",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Update preferences failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def unsubscribe(self):
        with self.client.post(
            f"/notifications/preferences/{self.state.customer_id}/unsubscribe",
            json={"notification_type": self._unsub_type},
            catch_response=True,
            name="POST /notifications/preferences/{id}/unsubscribe",
        ) as resp:
            if resp.status_code not in (200, 201):
                resp.failure(f"Unsubscribe failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def get_notification_history(self):
        with self.client.get(
            f"/notifications/{self.state.customer_id}",
            catch_response=True,
            name="GET /notifications/{customer_id}",
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                self.state.notification_ids = [n["notification_id"] for n in data.get("notifications", [])]
            elif resp.status_code != 404:
                resp.failure(f"Get history failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def resubscribe(self):
        with self.client.post(
            f"/notifications/preferences/{self.state.customer_id}/resubscribe",
            json={"notification_type": self._unsub_type},
            catch_response=True,
            name="POST /notifications/preferences/{id}/resubscribe",
        ) as resp:
            if resp.status_code not in (200, 201):
                resp.failure(f"Resubscribe failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def done(self):
        self.interrupt()


class NotificationCancelJourney(SequentialTaskSet):
    """Register Customer -> Update Preferences -> Process Scheduled -> Cancel.

    WARNING: This is a timing-sensitive scenario that generates expected
    CancelNotificationHandler failures. The process-scheduled endpoint
    transitions notifications from Scheduled → Sent. A subsequent cancel
    request may arrive after the notification is already Sent, causing
    "Cannot transition from Sent to Cancelled" at the handler level.

    The HTTP API handles this gracefully (400/409), but the async event
    handler still records a failure trace.

    This journey is excluded from default NotificationsUser discovery.
    Run explicitly via NotificationsCancelUser:

        locust -f loadtests/scenarios/notifications.py NotificationsCancelUser
    """

    def on_start(self):
        self.state = NotificationState()

    @task
    def register_customer(self):
        customer_id = _register_customer(self.client)
        if not customer_id:
            self.interrupt()
            return
        self.state.customer_id = customer_id
        time.sleep(0.5)

    @task
    def update_preferences(self):
        with self.client.put(
            f"/notifications/preferences/{self.state.customer_id}",
            json=notification_preferences_data(),
            catch_response=True,
            name="PUT /notifications/preferences/{id}",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Update preferences failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def process_scheduled(self):
        with self.client.post(
            "/notifications/maintenance/process-scheduled",
            json={},
            catch_response=True,
            name="POST /notifications/maintenance/process-scheduled",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Process scheduled failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def get_history_for_cancel(self):
        with self.client.get(
            f"/notifications/{self.state.customer_id}",
            catch_response=True,
            name="GET /notifications/{customer_id}",
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                self.state.notification_ids = [n["notification_id"] for n in data.get("notifications", [])]

    @task
    def cancel_notification(self):
        if not self.state.notification_ids:
            return  # No notifications to cancel
        notification_id = random.choice(self.state.notification_ids)
        reasons = [
            "Customer changed preferences",
            "Order cancelled",
            "Duplicate notification",
            "System maintenance",
        ]
        with self.client.put(
            f"/notifications/{notification_id}/cancel",
            json={"reason": random.choice(reasons)},
            catch_response=True,
            name="PUT /notifications/{id}/cancel",
        ) as resp:
            if resp.status_code in (200, 400, 409):
                # 400/409 = invalid state (already sent/cancelled) — acceptable
                resp.success()
            else:
                resp.failure(f"Cancel notification failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def done(self):
        self.interrupt()


class NotificationsUser(HttpUser):
    """Locust user simulating Notifications domain interactions.

    Weighted distribution:
    - 40% Preference management (most common)
    - 30% Unsubscribe/resubscribe flow
    - 30% Quiet hours lifecycle

    Note: NotificationCancelJourney is excluded — process-scheduled
    transitions to Sent, racing with cancel requests and generating
    expected CancelNotificationHandler failures. Run via NotificationsCancelUser.
    """

    wait_time = between(0.5, 2.0)
    tasks = {
        PreferenceManagementJourney: 4,
        UnsubscribeResubscribeJourney: 3,
        QuietHoursLifecycleJourney: 3,
    }


class NotificationsCancelUser(HttpUser):
    """Specialty scenario: notification cancel after processing.

    WARNING: Generates expected CancelNotificationHandler failures because
    process-scheduled moves notifications to Sent state, and the subsequent
    cancel request fails with "Cannot transition from Sent to Cancelled".

    Run explicitly:
        locust -f loadtests/scenarios/notifications.py NotificationsCancelUser --headless -u 5 -t 60s
    """

    wait_time = between(0.5, 2.0)
    tasks = {
        NotificationCancelJourney: 1,
    }
