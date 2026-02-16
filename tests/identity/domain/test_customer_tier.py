"""Tests for Customer.upgrade_tier() behavior."""

import pytest
from identity.customer.customer import Customer, CustomerTier
from identity.customer.events import TierUpgraded
from protean.exceptions import ValidationError


def _make_customer():
    return Customer.register(
        external_id="EXT-001",
        email="test@example.com",
        first_name="John",
        last_name="Doe",
    )


class TestUpgradeTier:
    def test_upgrade_standard_to_silver(self):
        customer = _make_customer()
        customer._events.clear()

        customer.upgrade_tier(CustomerTier.SILVER.value)
        assert customer.tier == CustomerTier.SILVER.value

    def test_upgrade_silver_to_gold(self):
        customer = _make_customer()
        customer.upgrade_tier(CustomerTier.SILVER.value)
        customer._events.clear()

        customer.upgrade_tier(CustomerTier.GOLD.value)
        assert customer.tier == CustomerTier.GOLD.value

    def test_upgrade_gold_to_platinum(self):
        customer = _make_customer()
        customer.upgrade_tier(CustomerTier.SILVER.value)
        customer.upgrade_tier(CustomerTier.GOLD.value)
        customer._events.clear()

        customer.upgrade_tier(CustomerTier.PLATINUM.value)
        assert customer.tier == CustomerTier.PLATINUM.value

    def test_upgrade_standard_to_platinum(self):
        customer = _make_customer()
        customer._events.clear()

        customer.upgrade_tier(CustomerTier.PLATINUM.value)
        assert customer.tier == CustomerTier.PLATINUM.value

    def test_upgrade_raises_event(self):
        customer = _make_customer()
        customer._events.clear()

        customer.upgrade_tier(CustomerTier.SILVER.value)
        assert len(customer._events) == 1
        event = customer._events[0]
        assert isinstance(event, TierUpgraded)
        assert event.customer_id == str(customer.id)
        assert event.previous_tier == CustomerTier.STANDARD.value
        assert event.new_tier == CustomerTier.SILVER.value
        assert event.upgraded_at is not None

    def test_cannot_downgrade_tier(self):
        customer = _make_customer()
        customer.upgrade_tier(CustomerTier.GOLD.value)

        with pytest.raises(ValidationError) as exc:
            customer.upgrade_tier(CustomerTier.SILVER.value)
        assert "Cannot downgrade" in str(exc.value)

    def test_cannot_set_same_tier(self):
        customer = _make_customer()
        with pytest.raises(ValidationError) as exc:
            customer.upgrade_tier(CustomerTier.STANDARD.value)
        assert "Cannot downgrade" in str(exc.value)

    def test_cannot_downgrade_to_standard(self):
        customer = _make_customer()
        customer.upgrade_tier(CustomerTier.PLATINUM.value)

        with pytest.raises(ValidationError) as exc:
            customer.upgrade_tier(CustomerTier.STANDARD.value)
        assert "Cannot downgrade" in str(exc.value)
