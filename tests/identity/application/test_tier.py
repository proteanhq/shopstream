"""Application tests for tier management via domain.process()."""

import pytest
from identity.customer.customer import Customer, CustomerTier
from identity.customer.registration import RegisterCustomer
from identity.customer.tier import UpgradeTier
from protean import current_domain
from protean.exceptions import ValidationError


class TestTierManagementFlow:
    def _register_customer(self):
        command = RegisterCustomer(
            external_id="EXT-001",
            email="test@example.com",
            first_name="John",
            last_name="Doe",
        )
        return current_domain.process(command, asynchronous=False)

    def test_upgrade_to_silver(self):
        customer_id = self._register_customer()

        current_domain.process(
            UpgradeTier(customer_id=customer_id, new_tier=CustomerTier.SILVER.value),
            asynchronous=False,
        )

        customer = current_domain.repository_for(Customer).get(customer_id)
        assert customer.tier == CustomerTier.SILVER.value

    def test_upgrade_to_platinum(self):
        customer_id = self._register_customer()

        current_domain.process(
            UpgradeTier(customer_id=customer_id, new_tier=CustomerTier.PLATINUM.value),
            asynchronous=False,
        )

        customer = current_domain.repository_for(Customer).get(customer_id)
        assert customer.tier == CustomerTier.PLATINUM.value

    def test_cannot_downgrade(self):
        customer_id = self._register_customer()

        current_domain.process(
            UpgradeTier(customer_id=customer_id, new_tier=CustomerTier.GOLD.value),
            asynchronous=False,
        )

        with pytest.raises(ValidationError):
            current_domain.process(
                UpgradeTier(customer_id=customer_id, new_tier=CustomerTier.SILVER.value),
                asynchronous=False,
            )

    def test_progressive_upgrade(self):
        customer_id = self._register_customer()

        for tier in [
            CustomerTier.SILVER.value,
            CustomerTier.GOLD.value,
            CustomerTier.PLATINUM.value,
        ]:
            current_domain.process(
                UpgradeTier(customer_id=customer_id, new_tier=tier),
                asynchronous=False,
            )

        customer = current_domain.repository_for(Customer).get(customer_id)
        assert customer.tier == CustomerTier.PLATINUM.value
