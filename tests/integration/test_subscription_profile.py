"""Every context's engine subscriptions resolve to the custom `shopstream` subscription profile.

Each `domain.toml` sets `default_subscription_profile = "shopstream"`, a profile that inherits
Protean's built-in `production` profile and lowers `retention_maxlen` to 50000. Notifications
also overrides the circuit breaker for `NotificationDispatcher` alone.

`ConfigResolver` is what the engine's subscription factory calls to build each subscription's
config. It reads only `domain.config` and the handler's `Meta`, so these tests need no database
and give the same result under `--protean-env memory` and `--protean-env test`.
"""

import importlib

import pytest
from protean.server.subscription.config_resolver import ConfigResolver
from protean.server.subscription.profiles import PROFILE_DEFAULTS, SubscriptionProfile, SubscriptionType

RETENTION_MAXLEN = 50000
PRODUCTION = PROFILE_DEFAULTS[SubscriptionProfile.PRODUCTION]

# One handler module per context. Importing it registers at least one handler with the domain,
# so the registry is never empty, whatever else this session has imported.
CONTEXTS = {
    "identity": "identity.projections.customer_card",
    "catalogue": "catalogue.projections.category_tree",
    "ordering": "ordering.projections.order_detail",
    "inventory": "inventory.projections.warehouse_stock",
    "payments": "payments.projections.daily_revenue",
    "fulfillment": "fulfillment.projections.fulfillment_status",
    "reviews": "reviews.projections.customer_reviews",
    "notifications": "notifications.projections.customer_preferences",
    "loyalty": "loyalty.projections.redemption_view",
}

# Handlers whose `[server.subscriptions.<Handler>]` table overrides the profile.
OVERRIDDEN = {"NotificationDispatcher"}


def _domain(context: str):
    importlib.import_module(CONTEXTS[context])
    module = importlib.import_module(f"{context}.domain")
    return getattr(module, context)


def _subscribed_handlers(domain) -> list[type]:
    registry = domain.registry
    records = [*registry.event_handlers.values(), *registry.projectors.values(), *registry.process_managers.values()]
    return [record.cls for record in records]


@pytest.mark.fast
@pytest.mark.parametrize("context", list(CONTEXTS))
def test_context_handlers_resolve_to_the_shopstream_profile(context):
    domain = _domain(context)
    handlers = [cls for cls in _subscribed_handlers(domain) if cls.__name__ not in OVERRIDDEN]
    assert handlers, f"no event handlers or projectors registered for {context}"

    resolver = ConfigResolver(domain)
    for handler in handlers:
        config = resolver.resolve(handler)
        assert config.subscription_type == SubscriptionType.STREAM, handler.__name__
        assert config.retention_maxlen == RETENTION_MAXLEN, handler.__name__
        # Inherited from the production profile, not the hardcoded defaults (10 messages a tick).
        assert config.messages_per_tick == PRODUCTION["messages_per_tick"], handler.__name__
        assert config.circuit_breaker_threshold == PRODUCTION["circuit_breaker_threshold"], handler.__name__
        assert config.circuit_breaker_reset_seconds == PRODUCTION["circuit_breaker_reset_seconds"], handler.__name__


@pytest.mark.fast
def test_notification_dispatcher_overrides_the_breaker_and_keeps_the_profile_retention():
    from notifications.notification.dispatch import NotificationDispatcher

    config = ConfigResolver(_domain("notifications")).resolve(NotificationDispatcher)

    assert config.circuit_breaker_threshold == 5
    assert config.circuit_breaker_reset_seconds == 30
    assert config.retention_maxlen == RETENTION_MAXLEN
    assert config.messages_per_tick == PRODUCTION["messages_per_tick"]
