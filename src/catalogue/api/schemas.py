"""Pydantic request/response schemas for the Catalogue API."""

from __future__ import annotations

from pydantic import BaseModel, Field

# --- Product Request Schemas ---


class CreateProductRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "sku": "TSHIRT-BLK-M",
                    "seller_id": "seller-042",
                    "title": "Classic Black T-Shirt",
                    "description": "Premium cotton crew-neck tee in black.",
                    "category_id": "cat-apparel-001",
                    "brand": "Acme Apparel",
                    "attributes": "color=black,material=cotton",
                    "visibility": "VISIBLE",
                    "meta_title": "Classic Black T-Shirt | Acme Apparel",
                    "meta_description": "Premium cotton crew-neck tee available in multiple sizes.",
                    "slug": "classic-black-tshirt",
                }
            ]
        }
    }

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
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "title": "Classic Black T-Shirt (Updated)",
                    "description": "Premium organic cotton crew-neck tee in black.",
                    "brand": "Acme Apparel",
                    "meta_title": "Classic Black T-Shirt | Acme",
                    "slug": "classic-black-tshirt-v2",
                }
            ]
        }
    }

    title: str | None = Field(None, max_length=255)
    description: str | None = None
    brand: str | None = Field(None, max_length=100)
    attributes: str | None = None
    meta_title: str | None = Field(None, max_length=70)
    meta_description: str | None = Field(None, max_length=160)
    slug: str | None = Field(None, max_length=200)


class AddVariantRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "variant_sku": "TSHIRT-BLK-L",
                    "attributes": "size=L",
                    "base_price": 29.99,
                    "currency": "USD",
                    "weight_value": 0.25,
                    "weight_unit": "kg",
                    "length": 30.0,
                    "width": 22.0,
                    "height": 2.0,
                    "dimension_unit": "cm",
                }
            ]
        }
    }

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
    model_config = {"json_schema_extra": {"examples": [{"base_price": 24.99, "currency": "USD"}]}}

    base_price: float
    currency: str = Field("USD", max_length=3)


class SetTierPriceRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": [{"tier": "GOLD", "price": 22.49}]}}

    tier: str = Field(..., max_length=50)
    price: float


class AddProductImageRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "url": "https://cdn.example.com/images/tshirt-blk-front.jpg",
                    "alt_text": "Classic Black T-Shirt front view",
                    "is_primary": True,
                }
            ]
        }
    }

    url: str = Field(..., max_length=500)
    alt_text: str | None = Field(None, max_length=255)
    is_primary: bool = False


# --- Category Request Schemas ---


class CreateCategoryRequest(BaseModel):
    model_config = {
        "json_schema_extra": {"examples": [{"name": "Apparel", "parent_category_id": None, "attributes": "season=all"}]}
    }

    name: str = Field(..., max_length=100)
    parent_category_id: str | None = None
    attributes: str | None = None


class UpdateCategoryRequest(BaseModel):
    model_config = {
        "json_schema_extra": {"examples": [{"name": "Men's Apparel", "attributes": "season=spring,gender=men"}]}
    }

    name: str | None = Field(None, max_length=100)
    attributes: str | None = None


class ReorderCategoryRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": [{"new_display_order": 3}]}}

    new_display_order: int


# --- Response Schemas ---


class ProductIdResponse(BaseModel):
    model_config = {"json_schema_extra": {"examples": [{"product_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901"}]}}

    product_id: str


class CategoryIdResponse(BaseModel):
    model_config = {"json_schema_extra": {"examples": [{"category_id": "c3d4e5f6-a7b8-9012-cdef-123456789012"}]}}

    category_id: str


class StatusResponse(BaseModel):
    model_config = {"json_schema_extra": {"examples": [{"status": "ok"}]}}

    status: str = "ok"
