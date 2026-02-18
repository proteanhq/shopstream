"""Pydantic request/response schemas for the Identity API."""

from __future__ import annotations

from pydantic import BaseModel, Field

# --- Request Schemas ---


class RegisterCustomerRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "external_id": "cust-ext-001",
                    "email": "jane.doe@example.com",
                    "first_name": "Jane",
                    "last_name": "Doe",
                    "phone": "+1-555-0123",
                    "date_of_birth": "1990-03-15",
                }
            ]
        }
    }

    external_id: str = Field(..., max_length=255)
    email: str = Field(..., max_length=254)
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    phone: str | None = Field(None, max_length=20)
    date_of_birth: str | None = Field(None, max_length=10)


class UpdateProfileRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {"first_name": "Jane", "last_name": "Smith", "phone": "+1-555-0456", "date_of_birth": "1990-03-15"}
            ]
        }
    }

    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=20)
    date_of_birth: str | None = Field(None, max_length=10)


class AddAddressRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "label": "Home",
                    "street": "123 Elm Street",
                    "city": "Springfield",
                    "state": "IL",
                    "postal_code": "62701",
                    "country": "US",
                    "geo_lat": "39.7817",
                    "geo_lng": "-89.6501",
                }
            ]
        }
    }

    label: str | None = Field(None, max_length=20)
    street: str = Field(..., max_length=255)
    city: str = Field(..., max_length=100)
    state: str | None = Field(None, max_length=100)
    postal_code: str = Field(..., max_length=20)
    country: str = Field(..., max_length=100)
    geo_lat: str | None = None
    geo_lng: str | None = None


class UpdateAddressRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "label": "Office",
                    "street": "456 Oak Avenue",
                    "city": "Springfield",
                    "state": "IL",
                    "postal_code": "62702",
                    "country": "US",
                }
            ]
        }
    }

    label: str | None = Field(None, max_length=20)
    street: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    country: str | None = Field(None, max_length=100)


class SuspendAccountRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": [{"reason": "Repeated policy violations"}]}}

    reason: str = Field(..., max_length=500)


class UpgradeTierRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": [{"new_tier": "Gold"}]}}

    new_tier: str = Field(..., max_length=20)


# --- Response Schemas ---


class CustomerIdResponse(BaseModel):
    model_config = {"json_schema_extra": {"examples": [{"customer_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"}]}}

    customer_id: str


class StatusResponse(BaseModel):
    model_config = {"json_schema_extra": {"examples": [{"status": "ok"}]}}

    status: str = "ok"
