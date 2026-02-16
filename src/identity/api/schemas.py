"""Pydantic request/response schemas for the Identity API."""

from __future__ import annotations

from pydantic import BaseModel, Field

# --- Request Schemas ---


class RegisterCustomerRequest(BaseModel):
    external_id: str = Field(..., max_length=255)
    email: str = Field(..., max_length=254)
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    phone: str | None = Field(None, max_length=20)
    date_of_birth: str | None = Field(None, max_length=10)


class UpdateProfileRequest(BaseModel):
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    phone: str | None = Field(None, max_length=20)
    date_of_birth: str | None = Field(None, max_length=10)


class AddAddressRequest(BaseModel):
    label: str | None = Field(None, max_length=20)
    street: str = Field(..., max_length=255)
    city: str = Field(..., max_length=100)
    state: str | None = Field(None, max_length=100)
    postal_code: str = Field(..., max_length=20)
    country: str = Field(..., max_length=100)
    geo_lat: str | None = None
    geo_lng: str | None = None


class UpdateAddressRequest(BaseModel):
    label: str | None = Field(None, max_length=20)
    street: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    country: str | None = Field(None, max_length=100)


class SuspendAccountRequest(BaseModel):
    reason: str = Field(..., max_length=500)


class UpgradeTierRequest(BaseModel):
    new_tier: str = Field(..., max_length=20)


# --- Response Schemas ---


class CustomerIdResponse(BaseModel):
    customer_id: str


class StatusResponse(BaseModel):
    status: str = "ok"
