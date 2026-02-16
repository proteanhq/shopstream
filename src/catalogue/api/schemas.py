"""Pydantic request/response schemas for the Catalogue API."""

from __future__ import annotations

from pydantic import BaseModel, Field

# --- Product Request Schemas ---


class CreateProductRequest(BaseModel):
    sku: str = Field(..., max_length=50)
    seller_id: str | None = None
    title: str = Field(..., max_length=255)
    description: str | None = None
    category_id: str | None = None
    brand: str | None = Field(None, max_length=100)
    attributes: str | None = None
    visibility: str | None = Field(None, max_length=20)
    meta_title: str | None = Field(None, max_length=70)
    meta_description: str | None = Field(None, max_length=160)
    slug: str | None = Field(None, max_length=200)


class UpdateProductDetailsRequest(BaseModel):
    title: str | None = Field(None, max_length=255)
    description: str | None = None
    brand: str | None = Field(None, max_length=100)
    attributes: str | None = None
    meta_title: str | None = Field(None, max_length=70)
    meta_description: str | None = Field(None, max_length=160)
    slug: str | None = Field(None, max_length=200)


class AddVariantRequest(BaseModel):
    variant_sku: str = Field(..., max_length=50)
    attributes: str | None = None
    base_price: float
    currency: str = Field("USD", max_length=3)
    weight_value: float | None = None
    weight_unit: str | None = Field(None, max_length=2)
    length: float | None = None
    width: float | None = None
    height: float | None = None
    dimension_unit: str | None = Field(None, max_length=2)


class UpdateVariantPriceRequest(BaseModel):
    base_price: float
    currency: str = Field("USD", max_length=3)


class SetTierPriceRequest(BaseModel):
    tier: str = Field(..., max_length=50)
    price: float


class AddProductImageRequest(BaseModel):
    url: str = Field(..., max_length=500)
    alt_text: str | None = Field(None, max_length=255)
    is_primary: bool = False


# --- Category Request Schemas ---


class CreateCategoryRequest(BaseModel):
    name: str = Field(..., max_length=100)
    parent_category_id: str | None = None
    attributes: str | None = None


class UpdateCategoryRequest(BaseModel):
    name: str | None = Field(None, max_length=100)
    attributes: str | None = None


class ReorderCategoryRequest(BaseModel):
    new_display_order: int


# --- Response Schemas ---


class ProductIdResponse(BaseModel):
    product_id: str


class CategoryIdResponse(BaseModel):
    category_id: str


class StatusResponse(BaseModel):
    status: str = "ok"
