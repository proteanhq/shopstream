"""Application tests for address management via domain.process()."""

import pytest
from identity.customer.addresses import (
    AddAddress,
    RemoveAddress,
    SetDefaultAddress,
    UpdateAddress,
)
from identity.customer.customer import Customer
from identity.customer.registration import RegisterCustomer
from protean import current_domain
from protean.exceptions import ValidationError


class TestAddressManagementFlow:
    def _register_customer(self):
        command = RegisterCustomer(
            external_id="EXT-001",
            email="test@example.com",
            first_name="John",
            last_name="Doe",
        )
        return current_domain.process(command, asynchronous=False)

    def test_add_first_address(self):
        customer_id = self._register_customer()

        command = AddAddress(
            customer_id=customer_id,
            street="123 Main St",
            city="Springfield",
            postal_code="62701",
            country="US",
        )
        current_domain.process(command, asynchronous=False)

        customer = current_domain.repository_for(Customer).get(customer_id)
        assert len(customer.addresses) == 1
        assert customer.addresses[0].street == "123 Main St"
        assert customer.addresses[0].is_default is True

    def test_add_multiple_addresses(self):
        customer_id = self._register_customer()

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

    def test_update_address(self):
        customer_id = self._register_customer()

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

        customer = current_domain.repository_for(Customer).get(customer_id)
        address_id = str(customer.addresses[0].id)

        current_domain.process(
            UpdateAddress(
                customer_id=customer_id,
                address_id=address_id,
                street="456 Elm St",
            ),
            asynchronous=False,
        )

        customer = current_domain.repository_for(Customer).get(customer_id)
        assert customer.addresses[0].street == "456 Elm St"

    def test_remove_address(self):
        customer_id = self._register_customer()

        # Add two addresses
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
        # Remove the second (non-default) address
        non_default = next(a for a in customer.addresses if not a.is_default)
        address_id = str(non_default.id)

        current_domain.process(
            RemoveAddress(
                customer_id=customer_id,
                address_id=address_id,
            ),
            asynchronous=False,
        )

        customer = current_domain.repository_for(Customer).get(customer_id)
        assert len(customer.addresses) == 1

    def test_set_default_address(self):
        customer_id = self._register_customer()

        # Add two addresses
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
        second_address_id = str(customer.addresses[1].id)

        current_domain.process(
            SetDefaultAddress(
                customer_id=customer_id,
                address_id=second_address_id,
            ),
            asynchronous=False,
        )

        customer = current_domain.repository_for(Customer).get(customer_id)
        defaults = [a for a in customer.addresses if a.is_default]
        assert len(defaults) == 1
        assert str(defaults[0].id) == second_address_id

    def test_add_address_with_optional_fields(self):
        """Cover addresses.py lines 25, 37, 39, 41: label, state, geo_coordinates."""
        customer_id = self._register_customer()

        command = AddAddress(
            customer_id=customer_id,
            label="Work",
            street="789 Office Blvd",
            city="Chicago",
            state="IL",
            postal_code="60601",
            country="US",
            geo_lat="41.8781",
            geo_lng="-87.6298",
        )
        current_domain.process(command, asynchronous=False)

        customer = current_domain.repository_for(Customer).get(customer_id)
        assert len(customer.addresses) == 1
        assert customer.addresses[0].label == "Work"
        assert customer.addresses[0].state == "IL"
        assert customer.addresses[0].geo_coordinates is not None
        assert customer.addresses[0].geo_coordinates.latitude == 41.8781

    def test_cannot_add_11th_address(self):
        customer_id = self._register_customer()

        for i in range(10):
            current_domain.process(
                AddAddress(
                    customer_id=customer_id,
                    street=f"{i+1} Street",
                    city="City",
                    postal_code="12345",
                    country="US",
                ),
                asynchronous=False,
            )

        with pytest.raises(ValidationError):
            current_domain.process(
                AddAddress(
                    customer_id=customer_id,
                    street="11th Street",
                    city="City",
                    postal_code="12345",
                    country="US",
                ),
                asynchronous=False,
            )
