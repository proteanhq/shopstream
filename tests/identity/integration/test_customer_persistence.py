"""Integration tests for Customer persistence - full aggregate graph."""

from identity.customer.addresses import AddAddress
from identity.customer.customer import Customer
from identity.customer.profile import UpdateProfile
from identity.customer.registration import RegisterCustomer
from protean import current_domain


class TestCustomerPersistence:
    def test_persist_and_retrieve_customer(self):
        customer_id = current_domain.process(
            RegisterCustomer(
                external_id="EXT-P01",
                email="persist@example.com",
                first_name="Persist",
                last_name="Test",
            ),
            asynchronous=False,
        )

        customer = current_domain.repository_for(Customer).get(customer_id)
        assert customer.external_id == "EXT-P01"
        assert customer.email.address == "persist@example.com"
        assert customer.profile.first_name == "Persist"

    def test_persist_customer_with_profile_update(self):
        customer_id = current_domain.process(
            RegisterCustomer(
                external_id="EXT-P02",
                email="profile@example.com",
                first_name="Original",
                last_name="Name",
            ),
            asynchronous=False,
        )

        current_domain.process(
            UpdateProfile(
                customer_id=customer_id,
                first_name="Updated",
                last_name="Name",
                phone="+1-555-000-1111",
            ),
            asynchronous=False,
        )

        customer = current_domain.repository_for(Customer).get(customer_id)
        assert customer.profile.first_name == "Updated"
        assert customer.profile.phone.number == "+1-555-000-1111"

    def test_persist_customer_with_addresses(self):
        customer_id = current_domain.process(
            RegisterCustomer(
                external_id="EXT-P03",
                email="addresses@example.com",
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
        current_domain.process(
            AddAddress(
                customer_id=customer_id,
                street="456 Oak Ave",
                city="Chicago",
                postal_code="60601",
                country="US",
            ),
            asynchronous=False,
        )

        customer = current_domain.repository_for(Customer).get(customer_id)
        assert len(customer.addresses) == 2
        streets = {a.street for a in customer.addresses}
        assert "123 Main St" in streets
        assert "456 Oak Ave" in streets
