"""Loyalty domain load scenario — event-driven (Loyalty has no HTTP API).

Loyalty never receives HTTP traffic of its own; it reacts to cross-domain events:

  - ``identity::customer`` / ``CustomerRegistered`` → ``CustomerRegisteredSubscriber``
    auto-enrols a reward account (subscriber pattern A).
  - ``ordering::order`` / ``OrderDelivered`` → ``OrderDeliveredSubscriber`` awards a
    delivery bonus directly on the account (subscriber pattern B).

So we generate loyalty load *indirectly* by driving the full order lifecycle to delivery
(which also registers a customer). With the Loyalty engine running (``make engine-loyalty``),
each iteration enrols an account and awards points, exercising the ``RewardAccountView``
(database) and ``PointsLeaderboard`` (Redis cache) projections plus both loyalty subscribers
under load.

This reuses the canonical end-to-end order journey. Like ``CrossDomainUser``, that lifecycle
can race the ``OrderCheckoutSaga`` and produce the same *expected* ordering payment-handler
failures — those are about ordering's saga, not loyalty. It is therefore a **specialty**
scenario, run explicitly:

    locust -f loadtests/scenarios/loyalty.py LoyaltyRewardsUser
    make loadtest-loyalty

Loyalty's effects are observed via the **Observatory** (loyalty Redis streams + cache and the
``protean_*`` metrics), not asserted over HTTP — loyalty exposes no read endpoints.
"""

from locust import HttpUser, between

from loadtests.scenarios.cross_domain import EndToEndOrderJourney


class LoyaltyRewardsUser(HttpUser):
    """Drives end-to-end orders to delivery so Loyalty enrols accounts and awards points."""

    wait_time = between(0.5, 2.0)
    tasks = [EndToEndOrderJourney]
