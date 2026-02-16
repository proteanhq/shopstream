"""FastAPI endpoints for the Catalogue domain."""

from fastapi import APIRouter
from protean.utils.globals import current_domain

from catalogue.api.schemas import (
    AddProductImageRequest,
    AddVariantRequest,
    CategoryIdResponse,
    CreateCategoryRequest,
    CreateProductRequest,
    ProductIdResponse,
    ReorderCategoryRequest,
    SetTierPriceRequest,
    StatusResponse,
    UpdateCategoryRequest,
    UpdateProductDetailsRequest,
    UpdateVariantPriceRequest,
)
from catalogue.category.management import (
    CreateCategory,
    DeactivateCategory,
    ReorderCategory,
    UpdateCategory,
)
from catalogue.product.creation import CreateProduct
from catalogue.product.details import UpdateProductDetails
from catalogue.product.images import AddProductImage, RemoveProductImage
from catalogue.product.lifecycle import ActivateProduct, ArchiveProduct, DiscontinueProduct
from catalogue.product.variants import AddVariant, SetTierPrice, UpdateVariantPrice

product_router = APIRouter(prefix="/products", tags=["products"])
category_router = APIRouter(prefix="/categories", tags=["categories"])


# --- Product endpoints ---


@product_router.post("", status_code=201, response_model=ProductIdResponse)
async def create_product(body: CreateProductRequest) -> ProductIdResponse:
    command = CreateProduct(
        sku=body.sku,
        seller_id=body.seller_id,
        title=body.title,
        description=body.description,
        category_id=body.category_id,
        brand=body.brand,
        attributes=body.attributes,
        visibility=body.visibility,
        meta_title=body.meta_title,
        meta_description=body.meta_description,
        slug=body.slug,
    )
    result = current_domain.process(command, asynchronous=False)
    return ProductIdResponse(product_id=result)


@product_router.put("/{product_id}/details", response_model=StatusResponse)
async def update_product_details(product_id: str, body: UpdateProductDetailsRequest) -> StatusResponse:
    command = UpdateProductDetails(
        product_id=product_id,
        title=body.title,
        description=body.description,
        brand=body.brand,
        attributes=body.attributes,
        meta_title=body.meta_title,
        meta_description=body.meta_description,
        slug=body.slug,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@product_router.post("/{product_id}/variants", status_code=201, response_model=StatusResponse)
async def add_variant(product_id: str, body: AddVariantRequest) -> StatusResponse:
    command = AddVariant(
        product_id=product_id,
        variant_sku=body.variant_sku,
        attributes=body.attributes,
        base_price=body.base_price,
        currency=body.currency,
        weight_value=body.weight_value,
        weight_unit=body.weight_unit,
        length=body.length,
        width=body.width,
        height=body.height,
        dimension_unit=body.dimension_unit,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@product_router.put("/{product_id}/variants/{variant_id}/price", response_model=StatusResponse)
async def update_variant_price(product_id: str, variant_id: str, body: UpdateVariantPriceRequest) -> StatusResponse:
    command = UpdateVariantPrice(
        product_id=product_id,
        variant_id=variant_id,
        base_price=body.base_price,
        currency=body.currency,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@product_router.put("/{product_id}/variants/{variant_id}/tier-price", response_model=StatusResponse)
async def set_tier_price(product_id: str, variant_id: str, body: SetTierPriceRequest) -> StatusResponse:
    command = SetTierPrice(
        product_id=product_id,
        variant_id=variant_id,
        tier=body.tier,
        price=body.price,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@product_router.post("/{product_id}/images", status_code=201, response_model=StatusResponse)
async def add_product_image(product_id: str, body: AddProductImageRequest) -> StatusResponse:
    command = AddProductImage(
        product_id=product_id,
        url=body.url,
        alt_text=body.alt_text,
        is_primary=body.is_primary,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@product_router.delete("/{product_id}/images/{image_id}", response_model=StatusResponse)
async def remove_product_image(product_id: str, image_id: str) -> StatusResponse:
    command = RemoveProductImage(
        product_id=product_id,
        image_id=image_id,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@product_router.put("/{product_id}/activate", response_model=StatusResponse)
async def activate_product(product_id: str) -> StatusResponse:
    command = ActivateProduct(product_id=product_id)
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@product_router.put("/{product_id}/discontinue", response_model=StatusResponse)
async def discontinue_product(product_id: str) -> StatusResponse:
    command = DiscontinueProduct(product_id=product_id)
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@product_router.put("/{product_id}/archive", response_model=StatusResponse)
async def archive_product(product_id: str) -> StatusResponse:
    command = ArchiveProduct(product_id=product_id)
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


# --- Category endpoints ---


@category_router.post("", status_code=201, response_model=CategoryIdResponse)
async def create_category(body: CreateCategoryRequest) -> CategoryIdResponse:
    command = CreateCategory(
        name=body.name,
        parent_category_id=body.parent_category_id,
        attributes=body.attributes,
    )
    result = current_domain.process(command, asynchronous=False)
    return CategoryIdResponse(category_id=result)


@category_router.put("/{category_id}", response_model=StatusResponse)
async def update_category(category_id: str, body: UpdateCategoryRequest) -> StatusResponse:
    command = UpdateCategory(
        category_id=category_id,
        name=body.name,
        attributes=body.attributes,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@category_router.put("/{category_id}/reorder", response_model=StatusResponse)
async def reorder_category(category_id: str, body: ReorderCategoryRequest) -> StatusResponse:
    command = ReorderCategory(
        category_id=category_id,
        new_display_order=body.new_display_order,
    )
    current_domain.process(command, asynchronous=False)
    return StatusResponse()


@category_router.put("/{category_id}/deactivate", response_model=StatusResponse)
async def deactivate_category(category_id: str) -> StatusResponse:
    command = DeactivateCategory(category_id=category_id)
    current_domain.process(command, asynchronous=False)
    return StatusResponse()
