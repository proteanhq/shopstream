"""Integration tests for Invoice API endpoints."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from payments.api.routes import invoice_router
from payments.invoice.invoice import Invoice, InvoiceStatus
from protean import current_domain


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(invoice_router)
    return TestClient(app)


class TestGenerateInvoiceAPI:
    def test_generate_returns_201(self, client):
        response = client.post(
            "/invoices",
            json={
                "order_id": "ord-inv-001",
                "customer_id": "cust-inv-001",
                "line_items": [
                    {"description": "Widget", "quantity": 2, "unit_price": 25.0},
                ],
                "tax": 4.00,
            },
        )
        assert response.status_code == 201
        assert "invoice_id" in response.json()

    def test_generate_persists(self, client):
        response = client.post(
            "/invoices",
            json={
                "order_id": "ord-inv-002",
                "customer_id": "cust-inv-002",
                "line_items": [
                    {"description": "Gadget", "quantity": 1, "unit_price": 50.0},
                ],
                "tax": 4.00,
            },
        )
        invoice_id = response.json()["invoice_id"]
        invoice = current_domain.repository_for(Invoice).get(invoice_id)
        assert invoice.status == InvoiceStatus.DRAFT.value


class TestVoidInvoiceAPI:
    def test_void_returns_200(self, client):
        # Create invoice first
        response = client.post(
            "/invoices",
            json={
                "order_id": "ord-inv-003",
                "customer_id": "cust-inv-003",
                "line_items": [
                    {"description": "Item", "quantity": 1, "unit_price": 10.0},
                ],
            },
        )
        invoice_id = response.json()["invoice_id"]

        # Void it
        response = client.put(
            f"/invoices/{invoice_id}/void",
            json={"reason": "Order cancelled"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "voided"
