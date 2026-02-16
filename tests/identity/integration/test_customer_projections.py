"""Integration tests for customer projections via domain.process()."""

import json

from identity.customer.account import SuspendAccount
from identity.customer.addresses import AddAddress, UpdateAddress
from identity.customer.customer import CustomerTier
from identity.customer.registration import RegisterCustomer
from identity.customer.tier import UpgradeTier
from identity.projections.address_book import AddressBook
from identity.projections.customer_card import CustomerCard
from identity.projections.customer_lookup import CustomerLookup
from identity.projections.customer_segments import CustomerSegments
from protean import current_domain


class TestCustomerCardProjection:
    def test_projection_created_on_registration(self):
        customer_id = current_domain.process(
            RegisterCustomer(
                external_id="EXT-001",
                email="john@example.com",
                first_name="John",
                last_name="Doe",
            ),
            asynchronous=False,
        )

        profile = current_domain.repository_for(CustomerCard).get(customer_id)
        assert profile.external_id == "EXT-001"
        assert profile.email == "john@example.com"
        assert profile.first_name == "John"
        assert profile.last_name == "Doe"
        assert profile.status == "Active"
        assert profile.tier == "Standard"

    def test_projection_updated_on_suspend(self):
        customer_id = current_domain.process(
            RegisterCustomer(
                external_id="EXT-002",
                email="jane@example.com",
                first_name="Jane",
                last_name="Smith",
            ),
            asynchronous=False,
        )
        current_domain.process(
            SuspendAccount(customer_id=customer_id, reason="Review"),
            asynchronous=False,
        )

        profile = current_domain.repository_for(CustomerCard).get(customer_id)
        assert profile.status == "Suspended"

    def test_projection_updated_on_tier_upgrade(self):
        customer_id = current_domain.process(
            RegisterCustomer(
                external_id="EXT-003",
                email="bob@example.com",
                first_name="Bob",
                last_name="Jones",
            ),
            asynchronous=False,
        )
        current_domain.process(
            UpgradeTier(customer_id=customer_id, new_tier=CustomerTier.GOLD.value),
            asynchronous=False,
        )

        profile = current_domain.repository_for(CustomerCard).get(customer_id)
        assert profile.tier == "Gold"


class TestCustomerLookupProjection:
    def test_lookup_created_on_registration(self):
        customer_id = current_domain.process(
            RegisterCustomer(
                external_id="EXT-010",
                email="lookup@example.com",
                first_name="Lookup",
                last_name="Test",
            ),
            asynchronous=False,
        )

        lookup = current_domain.repository_for(CustomerLookup).get("lookup@example.com")
        assert lookup.customer_id == customer_id


class TestCustomerSegmentsProjection:
    def test_record_created_on_registration(self):
        customer_id = current_domain.process(
            RegisterCustomer(
                external_id="EXT-020",
                email="tier@example.com",
                first_name="Tier",
                last_name="Test",
            ),
            asynchronous=False,
        )

        record = current_domain.repository_for(CustomerSegments).get(customer_id)
        assert record.tier == "Standard"
        assert record.email == "tier@example.com"

    def test_record_updated_on_tier_upgrade(self):
        customer_id = current_domain.process(
            RegisterCustomer(
                external_id="EXT-021",
                email="tierup@example.com",
                first_name="Tier",
                last_name="Upgrade",
            ),
            asynchronous=False,
        )
        current_domain.process(
            UpgradeTier(
                customer_id=customer_id,
                new_tier=CustomerTier.PLATINUM.value,
            ),
            asynchronous=False,
        )

        record = current_domain.repository_for(CustomerSegments).get(customer_id)
        assert record.tier == "Platinum"


class TestAddressBookProjection:
    def test_address_book_created_on_first_address(self):
        customer_id = current_domain.process(
            RegisterCustomer(
                external_id="EXT-030",
                email="addr@example.com",
                first_name="Address",
                last_name="Test",
            ),
            asynchronous=False,
        )
        current_domain.process(
            AddAddress(
                customer_id=customer_id,
                street="123 Main St",
                city="Springfield",
                postal_code="62701",
                country="US",
            ),
            asynchronous=False,
        )

        book = current_domain.repository_for(AddressBook).get(customer_id)
        entries = json.loads(book.addresses)
        assert len(entries) == 1
        assert entries[0]["street"] == "123 Main St"

    def test_address_book_updated_on_address_update(self):
        """Cover projector branches: loop skips non-matching entry (62->61)
        and continues to the next iteration (61->69)."""
        customer_id = current_domain.process(
            RegisterCustomer(
                external_id="EXT-031",
                email="addrbook@example.com",
                first_name="Book",
                last_name="Test",
            ),
            asynchronous=False,
        )

        current_domain.process(
            AddAddress(
                customer_id=customer_id,
                street="111 First St",
                city="City1",
                postal_code="11111",
                country="US",
            ),
            asynchronous=False,
        )
        current_domain.process(
            AddAddress(
                customer_id=customer_id,
                street="222 Second St",
                city="City2",
                postal_code="22222",
                country="US",
            ),
            asynchronous=False,
        )

        from identity.customer.customer import Customer

        customer = current_domain.repository_for(Customer).get(customer_id)
        second_addr_id = str(customer.addresses[1].id)

        current_domain.process(
            UpdateAddress(
                customer_id=customer_id,
                address_id=second_addr_id,
                street="222 Updated St",
            ),
            asynchronous=False,
        )

        book = current_domain.repository_for(AddressBook).get(customer_id)
        entries = json.loads(book.addresses)
        assert len(entries) == 2
        updated = next(e for e in entries if e["address_id"] == second_addr_id)
        assert updated["street"] == "222 Updated St"
