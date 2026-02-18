"""Identity domain load test scenarios.

Three stateful SequentialTaskSet journeys covering customer registration,
account lifecycle, and tier progression. Steps execute in order — each
depends on the previous step succeeding.
"""

from locust import HttpUser, SequentialTaskSet, between, task

from loadtests.data_generators import (
    address_data,
    customer_name,
    date_of_birth,
    unique_external_id,
    valid_email,
    valid_phone,
)
from loadtests.helpers.response import extract_error_detail
from loadtests.helpers.state import CustomerState


class NewCustomerJourney(SequentialTaskSet):
    """Register -> Update Profile -> Add Addresses -> Upgrade Tier.

    Generates 5 events: CustomerRegistered, ProfileUpdated,
    AddressAdded (x2), TierUpgraded.
    """

    def on_start(self):
        self.state = CustomerState()

    @task
    def register(self):
        first, last = customer_name()
        payload = {
            "external_id": unique_external_id(),
            "email": valid_email(),
            "first_name": first,
            "last_name": last,
            "phone": valid_phone(),
            "date_of_birth": date_of_birth(),
        }
        with self.client.post(
            "/customers",
            json=payload,
            catch_response=True,
            name="POST /customers",
        ) as resp:
            if resp.status_code == 201:
                self.state.customer_id = resp.json()["customer_id"]
            else:
                resp.failure(f"Registration failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def update_profile(self):
        first, last = customer_name()
        payload = {
            "first_name": first,
            "last_name": last,
            "phone": valid_phone(),
            "date_of_birth": date_of_birth(),
        }
        with self.client.put(
            f"/customers/{self.state.customer_id}/profile",
            json=payload,
            catch_response=True,
            name="PUT /customers/{id}/profile",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Update profile failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def add_first_address(self):
        with self.client.post(
            f"/customers/{self.state.customer_id}/addresses",
            json=address_data(),
            catch_response=True,
            name="POST /customers/{id}/addresses",
        ) as resp:
            if resp.status_code == 201:
                self.state.address_count += 1
            else:
                resp.failure(f"Add address failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def add_second_address(self):
        with self.client.post(
            f"/customers/{self.state.customer_id}/addresses",
            json=address_data(),
            catch_response=True,
            name="POST /customers/{id}/addresses",
        ) as resp:
            if resp.status_code == 201:
                self.state.address_count += 1
            else:
                resp.failure(f"Add second address failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def upgrade_to_silver(self):
        with self.client.put(
            f"/customers/{self.state.customer_id}/tier",
            json={"new_tier": "Silver"},
            catch_response=True,
            name="PUT /customers/{id}/tier",
        ) as resp:
            if resp.status_code == 200:
                self.state.current_tier = "Silver"
            else:
                resp.failure(f"Tier upgrade failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def done(self):
        self.interrupt()


class AccountLifecycleJourney(SequentialTaskSet):
    """Register -> Suspend -> Reactivate -> Close.

    Tests the full account state machine:
    Active -> Suspended -> Active -> Closed.
    Generates 4 events: CustomerRegistered, AccountSuspended,
    AccountReactivated, AccountClosed.
    """

    def on_start(self):
        self.state = CustomerState()

    @task
    def register(self):
        first, last = customer_name()
        payload = {
            "external_id": unique_external_id(),
            "email": valid_email(),
            "first_name": first,
            "last_name": last,
        }
        with self.client.post(
            "/customers",
            json=payload,
            catch_response=True,
            name="POST /customers",
        ) as resp:
            if resp.status_code == 201:
                self.state.customer_id = resp.json()["customer_id"]
            else:
                resp.failure(f"Registration failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def suspend(self):
        with self.client.put(
            f"/customers/{self.state.customer_id}/suspend",
            json={"reason": "Load test suspension"},
            catch_response=True,
            name="PUT /customers/{id}/suspend",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Suspend failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def reactivate(self):
        with self.client.put(
            f"/customers/{self.state.customer_id}/reactivate",
            catch_response=True,
            name="PUT /customers/{id}/reactivate",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Reactivate failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def close(self):
        with self.client.put(
            f"/customers/{self.state.customer_id}/close",
            catch_response=True,
            name="PUT /customers/{id}/close",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Close failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def done(self):
        self.interrupt()


class TierProgressionJourney(SequentialTaskSet):
    """Register -> Silver -> Gold -> Platinum.

    Exercises tier upgrade validation (no downgrades, must follow order).
    Generates 4 events: CustomerRegistered + 3x TierUpgraded.
    """

    def on_start(self):
        self.state = CustomerState()

    @task
    def register(self):
        first, last = customer_name()
        payload = {
            "external_id": unique_external_id(),
            "email": valid_email(),
            "first_name": first,
            "last_name": last,
        }
        with self.client.post(
            "/customers",
            json=payload,
            catch_response=True,
            name="POST /customers",
        ) as resp:
            if resp.status_code == 201:
                self.state.customer_id = resp.json()["customer_id"]
            else:
                resp.failure(f"Registration failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def upgrade_silver(self):
        self._upgrade("Silver")

    @task
    def upgrade_gold(self):
        self._upgrade("Gold")

    @task
    def upgrade_platinum(self):
        self._upgrade("Platinum")

    def _upgrade(self, tier: str):
        with self.client.put(
            f"/customers/{self.state.customer_id}/tier",
            json={"new_tier": tier},
            catch_response=True,
            name="PUT /customers/{id}/tier",
        ) as resp:
            if resp.status_code == 200:
                self.state.current_tier = tier
            else:
                resp.failure(f"Upgrade to {tier} failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def done(self):
        self.interrupt()


class IdentityUser(HttpUser):
    """Locust user simulating Identity domain interactions.

    Weighted task distribution:
    - 50% New Customer Journey (most common)
    - 30% Account Lifecycle
    - 20% Tier Progression
    """

    wait_time = between(0.5, 2.0)
    tasks = {
        NewCustomerJourney: 5,
        AccountLifecycleJourney: 3,
        TierProgressionJourney: 2,
    }
