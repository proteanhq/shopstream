"""Fulfillment domain load test scenarios.

Four stateful SequentialTaskSet journeys covering fulfillment creation
and picker assignment, cancellation, tracking webhook processing, and
exception recording.

Note: The full pick → pack → label → handoff → deliver lifecycle cannot
be exercised via load tests because the API doesn't expose FulfillmentItem
internal IDs (POST /fulfillments returns only fulfillment_id). The pick
endpoint requires these internal IDs. A GET /fulfillments/{id} endpoint
would be needed to close this gap.
"""

import random
import uuid

from locust import HttpUser, SequentialTaskSet, between, task

from loadtests.data_generators import fulfillment_data
from loadtests.helpers.response import extract_error_detail
from loadtests.helpers.state import FulfillmentState


class FulfillmentCreationJourney(SequentialTaskSet):
    """Create -> Assign Picker -> Get Tracking.

    Exercises: CreateFulfillment, AssignPicker commands and the
    ShipmentTracking read model query.
    """

    def on_start(self):
        self.state = FulfillmentState()

    @task
    def create_fulfillment(self):
        payload = fulfillment_data()
        self.state.order_id = payload["order_id"]
        with self.client.post(
            "/fulfillments",
            json=payload,
            catch_response=True,
            name="POST /fulfillments",
        ) as resp:
            if resp.status_code == 201:
                self.state.fulfillment_id = resp.json()["fulfillment_id"]
                self.state.item_count = len(payload["items"])
            else:
                resp.failure(f"Create fulfillment failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def assign_picker(self):
        with self.client.put(
            f"/fulfillments/{self.state.fulfillment_id}/assign-picker",
            json={"picker_name": f"Picker-{uuid.uuid4().hex[:4]}"},
            catch_response=True,
            name="PUT /fulfillments/{id}/assign-picker",
        ) as resp:
            if resp.status_code == 200:
                self.state.current_status = "Picking"
            else:
                resp.failure(f"Assign picker failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def get_tracking(self):
        """Query the ShipmentTracking read model."""
        with self.client.get(
            f"/fulfillments/{self.state.order_id}/tracking",
            catch_response=True,
            name="GET /fulfillments/{order_id}/tracking",
        ) as resp:
            if resp.status_code in (200, 404):
                # 404 = projection not yet populated (async)
                resp.success()
            else:
                resp.failure(f"Get tracking failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def done(self):
        self.interrupt()


class FulfillmentCancellationJourney(SequentialTaskSet):
    """Create -> Assign Picker -> Cancel.

    Models a fulfillment that gets cancelled during the picking phase.
    Generates events: FulfillmentCreated, PickerAssigned, FulfillmentCancelled.
    """

    def on_start(self):
        self.state = FulfillmentState()

    @task
    def create_fulfillment(self):
        payload = fulfillment_data()
        with self.client.post(
            "/fulfillments",
            json=payload,
            catch_response=True,
            name="POST /fulfillments",
        ) as resp:
            if resp.status_code == 201:
                self.state.fulfillment_id = resp.json()["fulfillment_id"]
            else:
                resp.failure(f"Create fulfillment failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def assign_picker(self):
        with self.client.put(
            f"/fulfillments/{self.state.fulfillment_id}/assign-picker",
            json={"picker_name": "CancelPicker"},
            catch_response=True,
            name="PUT /fulfillments/{id}/assign-picker",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Assign picker failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def cancel_fulfillment(self):
        reasons = [
            "Customer cancelled order",
            "Out of stock",
            "Quality issue detected",
            "Address undeliverable",
        ]
        with self.client.put(
            f"/fulfillments/{self.state.fulfillment_id}/cancel",
            json={"reason": random.choice(reasons)},
            catch_response=True,
            name="PUT /fulfillments/{id}/cancel",
        ) as resp:
            if resp.status_code == 200:
                self.state.current_status = "Cancelled"
            else:
                resp.failure(f"Cancel failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def done(self):
        self.interrupt()


class FulfillmentPickerCancelJourney(SequentialTaskSet):
    """Create -> Assign Picker -> Cancel.

    Models a fulfillment that gets cancelled during picking due to
    operational issues (item unavailable, quality issues detected).

    Note: The Exception state is only reachable from IN_TRANSIT (carrier
    delivery exceptions), not from PICKING. Since the full pick → pack →
    ship flow requires internal item IDs not exposed by the API, this
    journey exercises the alternative cancel-during-picking path.
    """

    def on_start(self):
        self.state = FulfillmentState()

    @task
    def create_fulfillment(self):
        payload = fulfillment_data(num_items=1)
        with self.client.post(
            "/fulfillments",
            json=payload,
            catch_response=True,
            name="POST /fulfillments",
        ) as resp:
            if resp.status_code == 201:
                self.state.fulfillment_id = resp.json()["fulfillment_id"]
            else:
                resp.failure(f"Create failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def assign_picker(self):
        with self.client.put(
            f"/fulfillments/{self.state.fulfillment_id}/assign-picker",
            json={"picker_name": f"ExcPicker-{uuid.uuid4().hex[:4]}"},
            catch_response=True,
            name="PUT /fulfillments/{id}/assign-picker",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Assign picker failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def cancel_during_picking(self):
        reasons = [
            "Item not found at expected location",
            "Damaged item discovered during picking",
            "Wrong SKU on shelf — inventory mismatch",
            "Quantity insufficient for fulfillment",
        ]
        with self.client.put(
            f"/fulfillments/{self.state.fulfillment_id}/cancel",
            json={"reason": random.choice(reasons)},
            catch_response=True,
            name="PUT /fulfillments/{id}/cancel",
        ) as resp:
            if resp.status_code == 200:
                self.state.current_status = "Cancelled"
            else:
                resp.failure(f"Cancel failed: {extract_error_detail(resp)}")

    @task
    def done(self):
        self.interrupt()


class FulfillmentTrackingWebhookJourney(SequentialTaskSet):
    """Create -> Multiple Tracking Webhooks -> Get Tracking.

    Models carrier tracking webhook updates flowing in for a fulfillment.
    Exercises the tracking webhook endpoint and read model queries.

    Note: These tracking updates may not advance fulfillment state correctly
    since the fulfillment isn't in Shipped state, but they exercise the
    webhook endpoint and tracking event processing.
    """

    def on_start(self):
        self.state = FulfillmentState()

    @task
    def create_fulfillment(self):
        payload = fulfillment_data()
        self.state.order_id = payload["order_id"]
        with self.client.post(
            "/fulfillments",
            json=payload,
            catch_response=True,
            name="POST /fulfillments",
        ) as resp:
            if resp.status_code == 201:
                self.state.fulfillment_id = resp.json()["fulfillment_id"]
            else:
                resp.failure(f"Create failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def tracking_update_1(self):
        with self.client.post(
            "/fulfillments/tracking/webhook",
            json={
                "fulfillment_id": self.state.fulfillment_id,
                "status": "picked_up",
                "location": "Warehouse, TX",
                "description": "Package picked up by carrier",
            },
            headers={"X-Carrier-Signature": "loadtest-sig"},
            catch_response=True,
            name="POST /fulfillments/tracking/webhook",
        ) as resp:
            if resp.status_code in (200, 400, 422):
                # 400/422 = not in shipped state — acceptable in load tests
                resp.success()
            else:
                resp.failure(f"Tracking update failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def tracking_update_2(self):
        with self.client.post(
            "/fulfillments/tracking/webhook",
            json={
                "fulfillment_id": self.state.fulfillment_id,
                "status": "in_transit",
                "location": "Distribution Hub, IL",
                "description": "In transit to destination",
            },
            headers={"X-Carrier-Signature": "loadtest-sig"},
            catch_response=True,
            name="POST /fulfillments/tracking/webhook",
        ) as resp:
            if resp.status_code in (200, 400, 422):
                resp.success()
            else:
                resp.failure(f"Tracking update 2 failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def get_tracking(self):
        with self.client.get(
            f"/fulfillments/{self.state.order_id}/tracking",
            catch_response=True,
            name="GET /fulfillments/{order_id}/tracking",
        ) as resp:
            if resp.status_code in (200, 404):
                resp.success()
            else:
                resp.failure(f"Get tracking failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def done(self):
        self.interrupt()


class FulfillmentUser(HttpUser):
    """Locust user simulating Fulfillment domain interactions.

    Weighted distribution:
    - 30% Creation + picker assignment (exercises create + assign)
    - 25% Cancellation journey (during picking)
    - 25% Tracking webhook journey (carrier updates)
    - 20% Exception journey (exception + cancel)
    """

    wait_time = between(0.5, 2.0)
    tasks = {
        FulfillmentCreationJourney: 6,
        FulfillmentCancellationJourney: 5,
        FulfillmentTrackingWebhookJourney: 5,
        FulfillmentPickerCancelJourney: 4,
    }
