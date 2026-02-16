"""Integration tests for FastAPI endpoints (api.py)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from identity.api import router
from identity.customer.customer import Customer, CustomerStatus, CustomerTier
from protean import current_domain


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestRegisterCustomerEndpoint:
    def test_register_customer(self, client):
        response = client.post(
            "/customers",
            json={
                "external_id": "EXT-API-001",
                "email": "api@example.com",
                "first_name": "Api",
                "last_name": "User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "customer_id" in data

        customer = current_domain.repository_for(Customer).get(data["customer_id"])
        assert customer.external_id == "EXT-API-001"

    def test_register_customer_with_optional_fields(self, client):
        response = client.post(
            "/customers",
            json={
                "external_id": "EXT-API-002",
                "email": "api2@example.com",
                "first_name": "Jane",
                "last_name": "Doe",
                "phone": "+1-555-000-1111",
                "date_of_birth": "1985-03-20",
            },
        )
        assert response.status_code == 201


class TestUpdateProfileEndpoint:
    def _register(self, client):
        resp = client.post(
            "/customers",
            json={
                "external_id": "EXT-API-010",
                "email": "profile@example.com",
                "first_name": "Old",
                "last_name": "Name",
            },
        )
        return resp.json()["customer_id"]

    def test_update_profile(self, client):
        customer_id = self._register(client)

        response = client.put(
            f"/customers/{customer_id}/profile",
            json={
                "first_name": "New",
                "last_name": "Name",
            },
        )
        assert response.status_code == 200

        customer = current_domain.repository_for(Customer).get(customer_id)
        assert customer.profile.first_name == "New"

    def test_update_profile_with_optional_fields(self, client):
        customer_id = self._register(client)

        response = client.put(
            f"/customers/{customer_id}/profile",
            json={
                "first_name": "New",
                "last_name": "Name",
                "phone": "+1-555-222-3333",
                "date_of_birth": "1990-01-01",
            },
        )
        assert response.status_code == 200


class TestAddressEndpoints:
    def _register_with_address(self, client):
        resp = client.post(
            "/customers",
            json={
                "external_id": "EXT-API-020",
                "email": "addr-api@example.com",
                "first_name": "Addr",
                "last_name": "Test",
            },
        )
        customer_id = resp.json()["customer_id"]

        client.post(
            f"/customers/{customer_id}/addresses",
            json={
                "street": "100 Main St",
                "city": "Springfield",
                "postal_code": "62701",
                "country": "US",
            },
        )
        return customer_id

    def test_add_address(self, client):
        resp = client.post(
            "/customers",
            json={
                "external_id": "EXT-API-021",
                "email": "addaddr@example.com",
                "first_name": "Add",
                "last_name": "Addr",
            },
        )
        customer_id = resp.json()["customer_id"]

        response = client.post(
            f"/customers/{customer_id}/addresses",
            json={
                "street": "100 Main St",
                "city": "Springfield",
                "postal_code": "62701",
                "country": "US",
            },
        )
        assert response.status_code == 201

    def test_add_address_with_optional_fields(self, client):
        resp = client.post(
            "/customers",
            json={
                "external_id": "EXT-API-022",
                "email": "addaddr2@example.com",
                "first_name": "Add",
                "last_name": "Addr",
            },
        )
        customer_id = resp.json()["customer_id"]

        response = client.post(
            f"/customers/{customer_id}/addresses",
            json={
                "label": "Work",
                "street": "200 Office Blvd",
                "city": "Chicago",
                "state": "IL",
                "postal_code": "60601",
                "country": "US",
                "geo_lat": "41.8781",
                "geo_lng": "-87.6298",
            },
        )
        assert response.status_code == 201

    def test_update_address(self, client):
        customer_id = self._register_with_address(client)
        customer = current_domain.repository_for(Customer).get(customer_id)
        address_id = str(customer.addresses[0].id)

        response = client.put(
            f"/customers/{customer_id}/addresses/{address_id}",
            json={"street": "200 Updated St"},
        )
        assert response.status_code == 200

    def test_remove_address(self, client):
        customer_id = self._register_with_address(client)

        # Add a second address so we can remove one
        client.post(
            f"/customers/{customer_id}/addresses",
            json={
                "street": "200 Second St",
                "city": "Chicago",
                "postal_code": "60601",
                "country": "US",
            },
        )

        customer = current_domain.repository_for(Customer).get(customer_id)
        non_default = next(a for a in customer.addresses if not a.is_default)
        address_id = str(non_default.id)

        response = client.delete(
            f"/customers/{customer_id}/addresses/{address_id}",
        )
        assert response.status_code == 200

    def test_set_default_address(self, client):
        customer_id = self._register_with_address(client)

        # Add a second address
        client.post(
            f"/customers/{customer_id}/addresses",
            json={
                "street": "200 Second St",
                "city": "Chicago",
                "postal_code": "60601",
                "country": "US",
            },
        )

        customer = current_domain.repository_for(Customer).get(customer_id)
        second_id = str(customer.addresses[1].id)

        response = client.put(
            f"/customers/{customer_id}/addresses/{second_id}/default",
        )
        assert response.status_code == 200


class TestAccountLifecycleEndpoints:
    def _register(self, client, ext_id="EXT-API-030"):
        resp = client.post(
            "/customers",
            json={
                "external_id": ext_id,
                "email": f"{ext_id}@example.com",
                "first_name": "Acct",
                "last_name": "Test",
            },
        )
        return resp.json()["customer_id"]

    def test_suspend_account(self, client):
        customer_id = self._register(client, "EXT-API-031")

        response = client.put(
            f"/customers/{customer_id}/suspend",
            json={"reason": "Fraud review"},
        )
        assert response.status_code == 200

        customer = current_domain.repository_for(Customer).get(customer_id)
        assert customer.status == CustomerStatus.SUSPENDED.value

    def test_reactivate_account(self, client):
        customer_id = self._register(client, "EXT-API-032")
        client.put(
            f"/customers/{customer_id}/suspend",
            json={"reason": "Review"},
        )

        response = client.put(f"/customers/{customer_id}/reactivate")
        assert response.status_code == 200

        customer = current_domain.repository_for(Customer).get(customer_id)
        assert customer.status == CustomerStatus.ACTIVE.value

    def test_close_account(self, client):
        customer_id = self._register(client, "EXT-API-033")

        response = client.put(f"/customers/{customer_id}/close")
        assert response.status_code == 200

        customer = current_domain.repository_for(Customer).get(customer_id)
        assert customer.status == CustomerStatus.CLOSED.value

    def test_upgrade_tier(self, client):
        customer_id = self._register(client, "EXT-API-034")

        response = client.put(
            f"/customers/{customer_id}/tier",
            json={"new_tier": CustomerTier.SILVER.value},
        )
        assert response.status_code == 200

        customer = current_domain.repository_for(Customer).get(customer_id)
        assert customer.tier == CustomerTier.SILVER.value
