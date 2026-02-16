"""Tests for Customer address management behavior methods."""

import pytest
from identity.customer.customer import AddressLabel, Customer
from identity.customer.events import (
    AddressAdded,
    AddressRemoved,
    AddressUpdated,
    DefaultAddressChanged,
)
from protean.exceptions import ValidationError


def _make_customer():
    return Customer.register(
        external_id="EXT-001",
        email="test@example.com",
        first_name="John",
        last_name="Doe",
    )


class TestAddAddress:
    def test_add_first_address(self):
        customer = _make_customer()
        customer._events.clear()

        addr = customer.add_address(
            street="123 Main St",
            city="Springfield",
            postal_code="62701",
            country="US",
        )
        assert len(customer.addresses) == 1
        assert customer.addresses[0].street == "123 Main St"
        assert addr.id is not None

    def test_first_address_becomes_default(self):
        customer = _make_customer()
        customer.add_address(
            street="123 Main St",
            city="Springfield",
            postal_code="62701",
            country="US",
        )
        assert customer.addresses[0].is_default is True

    def test_second_address_not_default_by_default(self):
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
        )
        assert customer.addresses[0].is_default is True
        assert customer.addresses[1].is_default is False

    def test_add_address_with_label(self):
        customer = _make_customer()
        customer.add_address(
            label=AddressLabel.WORK.value,
            street="789 Office Blvd",
            city="Chicago",
            postal_code="60601",
            country="US",
        )
        assert customer.addresses[0].label == AddressLabel.WORK.value

    def test_add_address_as_new_default(self):
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
        assert customer.addresses[0].is_default is False
        assert customer.addresses[1].is_default is True

    def test_add_address_as_new_default_with_multiple_existing(self):
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
        )
        # Adding a third address as default forces the loop to iterate over
        # both existing addresses (covering branch 191->190)
        customer.add_address(
            street="789 Third St",
            city="Denver",
            postal_code="80201",
            country="US",
            is_default=True,
        )
        assert customer.addresses[0].is_default is False
        assert customer.addresses[1].is_default is False
        assert customer.addresses[2].is_default is True

    def test_add_address_raises_event(self):
        customer = _make_customer()
        customer._events.clear()

        customer.add_address(
            street="123 Main St",
            city="Springfield",
            postal_code="62701",
            country="US",
        )
        assert len(customer._events) == 1
        event = customer._events[0]
        assert isinstance(event, AddressAdded)
        assert event.street == "123 Main St"
        assert event.city == "Springfield"

    def test_cannot_add_more_than_10_addresses(self):
        customer = _make_customer()
        for i in range(10):
            customer.add_address(
                street=f"{i} Street",
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


class TestUpdateAddress:
    def test_update_address_street(self):
        customer = _make_customer()
        addr = customer.add_address(
            street="123 Main St",
            city="Springfield",
            postal_code="62701",
            country="US",
        )
        customer._events.clear()

        customer.update_address(addr.id, street="456 Elm St")
        assert customer.addresses[0].street == "456 Elm St"

    def test_update_address_raises_event(self):
        customer = _make_customer()
        addr = customer.add_address(
            street="123 Main St",
            city="Springfield",
            postal_code="62701",
            country="US",
        )
        customer._events.clear()

        customer.update_address(addr.id, street="456 Elm St", city="Denver")
        assert len(customer._events) == 1
        event = customer._events[0]
        assert isinstance(event, AddressUpdated)
        assert event.address_id == str(addr.id)
        assert event.street == "456 Elm St"
        assert event.city == "Denver"

    def test_update_nonexistent_address_fails(self):
        customer = _make_customer()
        with pytest.raises(ValidationError) as exc:
            customer.update_address("nonexistent-id", street="456 Elm St")
        assert "not found" in str(exc.value)


class TestRemoveAddress:
    def test_remove_address(self):
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

        customer._events.clear()
        customer.remove_address(addr1.id)
        assert len(customer.addresses) == 1
        assert customer.addresses[0].street == "456 Oak Ave"

    def test_remove_default_address_reassigns_default(self):
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
        assert customer.addresses[0].is_default is True

        customer.remove_address(addr1.id)
        assert customer.addresses[0].is_default is True

    def test_remove_address_raises_event(self):
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
        customer._events.clear()

        customer.remove_address(addr1.id)
        assert len(customer._events) == 1
        event = customer._events[0]
        assert isinstance(event, AddressRemoved)
        assert event.address_id == str(addr1.id)

    def test_cannot_remove_last_address(self):
        customer = _make_customer()
        addr = customer.add_address(
            street="123 Main St",
            city="Springfield",
            postal_code="62701",
            country="US",
        )
        with pytest.raises(ValidationError) as exc:
            customer.remove_address(addr.id)
        assert "Cannot remove the last address" in str(exc.value)

    def test_remove_nonexistent_address_fails(self):
        customer = _make_customer()
        customer.add_address(
            street="123 Main St",
            city="Springfield",
            postal_code="62701",
            country="US",
        )
        with pytest.raises(ValidationError) as exc:
            customer.remove_address("nonexistent-id")
        assert "not found" in str(exc.value)


class TestSetDefaultAddress:
    def test_set_default_address(self):
        customer = _make_customer()
        customer.add_address(
            street="123 Main St",
            city="Springfield",
            postal_code="62701",
            country="US",
        )
        addr2 = customer.add_address(
            street="456 Oak Ave",
            city="Chicago",
            postal_code="60601",
            country="US",
        )

        customer._events.clear()
        customer.set_default_address(addr2.id)
        assert customer.addresses[0].is_default is False
        assert customer.addresses[1].is_default is True

    def test_set_default_raises_event(self):
        customer = _make_customer()
        addr1 = customer.add_address(
            street="123 Main St",
            city="Springfield",
            postal_code="62701",
            country="US",
        )
        addr2 = customer.add_address(
            street="456 Oak Ave",
            city="Chicago",
            postal_code="60601",
            country="US",
        )
        customer._events.clear()

        customer.set_default_address(addr2.id)
        assert len(customer._events) == 1
        event = customer._events[0]
        assert isinstance(event, DefaultAddressChanged)
        assert event.address_id == str(addr2.id)
        assert event.previous_default_address_id == str(addr1.id)

    def test_set_default_nonexistent_address_fails(self):
        customer = _make_customer()
        customer.add_address(
            street="123 Main St",
            city="Springfield",
            postal_code="62701",
            country="US",
        )
        with pytest.raises(ValidationError) as exc:
            customer.set_default_address("nonexistent-id")
        assert "not found" in str(exc.value)
