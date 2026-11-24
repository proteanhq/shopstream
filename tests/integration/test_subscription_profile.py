"""Every context's engine subscriptions resolve to the custom `shopstream` subscription profile.

Each `domain.toml` sets `default_subscription_profile = "shopstream"`, a profile that inherits
Protean's built-in `production` profile and lowers `retention_maxlen` to 50000. Notifications
also overrides the circuit breaker for `NotificationDispatcher` alone. Loyalty's
`PoisonEventStoreHandler` overrides the subscription type and reads the event store, so the
profile's Redis stream retention does not apply to it.

`ConfigResolver` is what the engine's subscription factory calls to build each subscription's
config. It reads only `domain.config` and the handler's `Meta`, so these tests need no database
and give the same result under `--protean-env memory` and `--protean-env test`.
"""

import importlib
import pkgutil

import pytest
from protean.server.subscription.config_resolver import ConfigResolver
from protean.server.subscription.profiles import PROFILE_DEFAULTS, SubscriptionProfile, SubscriptionType

RETENTION_MAXLEN = 50000
PRODUCTION = PROFILE_DEFAULTS[SubscriptionProfile.PRODUCTION]

CONTEXTS = [
    "identity",
    "catalogue",
    "ordering",
    "inventory",
    "payments",
    "fulfillment",
    "reviews",
    "notifications",
    "loyalty",
]

# Handlers whose `[server.subscriptions.<Handler>]` table overrides the profile.
OVERRIDDEN = {"NotificationDispatcher"}
# Handlers whose `subscription_type` option moves them to the event store.
EVENT_STORE = {"PoisonEventStoreHandler"}


def _domain(context: str):
    """Import every module of the context, as `domain.init()` does, so every handler is registered.

    Importing the modules registers the handlers without `domain.init()`, which would also connect
    the providers and brokers.
    """
    package = importlib.import_module(context)
    for module in pkgutil.walk_packages(package.__path__, prefix=f"{context}."):
        importlib.import_module(module.name)
    return getattr(importlib.import_module(f"{context}.domain"), context)


def _subscribed_handlers(domain) -> list[type]:
    registry = domain.registry
    records = [*registry.event_handlers.values(), *registry.projectors.values(), *registry.process_managers.values()]
    return [record.cls for record in records]


@pytest.mark.fast
@pytest.mark.parametrize("context", CONTEXTS)
def test_context_handlers_resolve_to_the_shopstream_profile(context):
    domain = _domain(context)
    # A misspelt key would be ignored and leave every handler on the hardcoded defaults.
    assert domain.config["server"]["default_subscription_profile"] == "shopstream"
    handlers = [cls for cls in _subscribed_handlers(domain) if cls.__name__ not in OVERRIDDEN | EVENT_STORE]
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


@pytest.mark.fast
def test_poison_event_store_handler_reads_the_event_store_with_the_profile_breaker():
    from loyalty.dlq.poison import PoisonEventStoreHandler

    config = ConfigResolver(_domain("loyalty")).resolve(PoisonEventStoreHandler)

    assert config.subscription_type == SubscriptionType.EVENT_STORE
    # Stream retention is a Redis setting, so the event-store subscription has none.
    assert config.retention_maxlen is None
    assert config.messages_per_tick == PRODUCTION["messages_per_tick"]
    assert config.circuit_breaker_threshold == PRODUCTION["circuit_breaker_threshold"]
