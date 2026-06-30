"""Loyalty domain load scenarios.

Two flavours:

  * ``LoyaltyUser`` (default) — drives the Loyalty **HTTP API** directly: enrol an account,
    earn/redeem points, transfer between accounts, and run the full promo-campaign lifecycle
    (launch → activate → earn-with-multiplier), reading back the account view (DB projection),
    points standing (Redis cache projection), and campaign catalog. Pure happy-path, so it is a
    safe default scenario with no expected failures. With the Loyalty engine running
    (``make engine-loyalty``) this exercises both projections, the cross-aggregate points
    multiplier, the application-service transfer path, and the published producer events
    (PointsEarned/PointsRedeemed/TierUpgraded) flowing to the external bus.

  * ``LoyaltyRewardsUser`` (specialty) — generates loyalty load *indirectly* by driving the
    full order lifecycle to delivery (CustomerRegistered → auto-enrol; OrderDelivered → delivery
    bonus). Like ``CrossDomainUser``, that lifecycle can race the ``OrderCheckoutSaga`` and
    produce the same *expected* ordering payment-handler failures, so it is run explicitly:

        locust -f loadtests/scenarios/loyalty.py LoyaltyRewardsUser
        make loadtest-loyalty
"""

from locust import HttpUser, SequentialTaskSet, between, task

from loadtests.data_generators import campaign_data, loyalty_customer_id
from loadtests.helpers.response import extract_error_detail
from loadtests.helpers.state import LoyaltyState
from loadtests.scenarios.cross_domain import EndToEndOrderJourney


class RewardsAccountJourney(SequentialTaskSet):
    """Enrol → earn → read account/points → redeem.

    Generates RewardAccountEnrolled, PointsEarned, PointsRedeemed and updates the
    RewardAccountView (DB) and PointsLeaderboard (cache) projections.
    """

    def on_start(self):
        self.state = LoyaltyState()

    @task
    def enroll(self):
        with self.client.post(
            "/loyalty/accounts",
            json={"customer_id": loyalty_customer_id()},
            catch_response=True,
            name="POST /loyalty/accounts",
        ) as resp:
            if resp.status_code == 201:
                self.state.account_id = resp.json()["account_id"]
            else:
                resp.failure(f"Enroll failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def earn(self):
        with self.client.post(
            f"/loyalty/accounts/{self.state.account_id}/earn",
            json={"amount": 150, "reason": "order"},
            catch_response=True,
            name="POST /loyalty/accounts/{id}/earn",
        ) as resp:
            if resp.status_code == 200:
                self.state.points_earned += 150
            else:
                resp.failure(f"Earn failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def read_account_view(self):
        """Verify the RewardAccountView (DB projection) is populated."""
        with self.client.get(
            f"/loyalty/accounts/{self.state.account_id}",
            catch_response=True,
            name="GET /loyalty/accounts/{id}",
        ) as resp:
            if resp.status_code in (200, 404):
                resp.success()
            else:
                resp.failure(f"Get account failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def read_points_standing(self):
        """Verify the PointsLeaderboard (cache projection) is populated."""
        with self.client.get(
            f"/loyalty/accounts/{self.state.account_id}/points",
            catch_response=True,
            name="GET /loyalty/accounts/{id}/points",
        ) as resp:
            if resp.status_code in (200, 404):
                resp.success()
            else:
                resp.failure(f"Get points failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def redeem(self):
        with self.client.post(
            f"/loyalty/accounts/{self.state.account_id}/redeem",
            json={"amount": 50, "reason": "voucher"},
            catch_response=True,
            name="POST /loyalty/accounts/{id}/redeem",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Redeem failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def done(self):
        self.interrupt()


class CampaignMultiplierJourney(SequentialTaskSet):
    """Launch a points_multiplier campaign, activate it, then enrol + earn so the boost applies.

    Exercises the event-sourced PromoCampaign lifecycle, the CampaignCatalog projection, and
    the cross-aggregate multiplier read inside the earn handler.
    """

    def on_start(self):
        self.state = LoyaltyState()

    @task
    def launch_campaign(self):
        with self.client.post(
            "/loyalty/campaigns",
            json=campaign_data(),
            catch_response=True,
            name="POST /loyalty/campaigns",
        ) as resp:
            if resp.status_code == 201:
                self.state.campaign_id = resp.json()["campaign_id"]
            else:
                resp.failure(f"Launch campaign failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def activate_campaign(self):
        with self.client.post(
            f"/loyalty/campaigns/{self.state.campaign_id}/activate",
            catch_response=True,
            name="POST /loyalty/campaigns/{id}/activate",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Activate campaign failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def enroll_and_earn(self):
        with self.client.post(
            "/loyalty/accounts",
            json={"customer_id": loyalty_customer_id()},
            catch_response=True,
            name="POST /loyalty/accounts",
        ) as resp:
            if resp.status_code == 201:
                self.state.account_id = resp.json()["account_id"]
            else:
                resp.failure(f"Enroll failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()
                return

        with self.client.post(
            f"/loyalty/accounts/{self.state.account_id}/earn",
            json={"amount": 100, "reason": "order"},
            catch_response=True,
            name="POST /loyalty/accounts/{id}/earn",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Earn failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def list_active_campaigns(self):
        with self.client.get(
            "/loyalty/campaigns",
            params={"status": "active"},
            catch_response=True,
            name="GET /loyalty/campaigns?status=active",
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"List campaigns failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def done(self):
        self.interrupt()


class TransferJourney(SequentialTaskSet):
    """Enrol two accounts, fund one, then transfer points (application-service path)."""

    def on_start(self):
        self.state = LoyaltyState()
        self.target_account_id = None

    def _enroll(self):
        resp = self.client.post(
            "/loyalty/accounts",
            json={"customer_id": loyalty_customer_id()},
            name="POST /loyalty/accounts",
        )
        return resp.json()["account_id"] if resp.status_code == 201 else None

    @task
    def setup_accounts(self):
        self.state.account_id = self._enroll()
        self.target_account_id = self._enroll()
        if not self.state.account_id or not self.target_account_id:
            self.interrupt()
            return
        self.client.post(
            f"/loyalty/accounts/{self.state.account_id}/earn",
            json={"amount": 200, "reason": "order"},
            name="POST /loyalty/accounts/{id}/earn",
        )

    @task
    def transfer(self):
        with self.client.post(
            "/loyalty/transfers",
            json={
                "source_account_id": self.state.account_id,
                "target_account_id": self.target_account_id,
                "amount": 75,
            },
            catch_response=True,
            name="POST /loyalty/transfers",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Transfer failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def done(self):
        self.interrupt()


class LoyaltyUser(HttpUser):
    """Drives the Loyalty HTTP API directly (default scenario).

    Weighted task distribution:
    - 50% Rewards account journey (enrol/earn/redeem + projection reads)
    - 30% Campaign multiplier journey
    - 20% Points transfer
    """

    wait_time = between(0.5, 2.0)
    tasks = {
        RewardsAccountJourney: 5,
        CampaignMultiplierJourney: 3,
        TransferJourney: 2,
    }


class LoyaltyRewardsUser(HttpUser):
    """Specialty: drives end-to-end orders to delivery so Loyalty enrols + awards via events."""

    wait_time = between(0.5, 2.0)
    tasks = [EndToEndOrderJourney]
