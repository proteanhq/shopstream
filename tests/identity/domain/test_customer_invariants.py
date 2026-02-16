"""Tests for Customer aggregate invariants."""

import pytest
from identity.customer.customer import Customer
from protean.exceptions import ValidationError


def _make_customer():
    return Customer.register(
        external_id="EXT-001",
        email="test@example.com",
        first_name="John",
        last_name="Doe",
    )


class TestMaxAddressesInvariant:
    def test_can_have_10_addresses(self):
        customer = _make_customer()
        for i in range(10):
            customer.add_address(
                street=f"{i+1} Street",
                city="City",
                postal_code="12345",
                country="US",
            )
        assert len(customer.addresses) == 10

    def test_11th_address_rejected(self):
        customer = _make_customer()
        for i in range(10):
            customer.add_address(
                street=f"{i+1} Street",
                city="City",
                postal_code="12345",
                country="US",
            )
        with pytest.raises(ValidationError) as exc:
            customer.add_address(
                street="11th Street",
                city="City",
                postal_code="12345",
                country="US",
            )
        assert "Cannot have more than 10 addresses" in str(exc.value)


class TestDefaultAddressInvariant:
    def test_first_address_auto_default(self):
        customer = _make_customer()
        customer.add_address(
            street="123 Main St",
            city="Springfield",
            postal_code="62701",
            country="US",
        )
        defaults = [a for a in customer.addresses if a.is_default]
        assert len(defaults) == 1

    def test_adding_new_default_unsets_previous(self):
        customer = _make_customer()
        customer.add_address(
            street="123 Main St",
            city="Springfield",
            postal_code="62701",
            country="US",
        )
        customer.add_address(
            street="456 Oak Ave",
            city="Chicago",
            postal_code="60601",
            country="US",
            is_default=True,
        )
        defaults = [a for a in customer.addresses if a.is_default]
        assert len(defaults) == 1
        assert defaults[0].street == "456 Oak Ave"

    def test_removing_default_reassigns(self):
        customer = _make_customer()
        addr1 = customer.add_address(
            street="123 Main St",
            city="Springfield",
            postal_code="62701",
            country="US",
        )
        customer.add_address(
            street="456 Oak Ave",
            city="Chicago",
            postal_code="60601",
            country="US",
        )
        customer.remove_address(addr1.id)
        defaults = [a for a in customer.addresses if a.is_default]
        assert len(defaults) == 1
