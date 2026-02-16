"""FastAPI endpoints for the Catalogue domain."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from protean.utils.globals import current_domain

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


@product_router.post("", status_code=201)
async def create_product(request: Request):
    payload = await request.json()
    command = CreateProduct(
        sku=payload["sku"],
        seller_id=payload.get("seller_id"),
        title=payload["title"],
        description=payload.get("description"),
        category_id=payload.get("category_id"),
        brand=payload.get("brand"),
        attributes=payload.get("attributes"),
        visibility=payload.get("visibility"),
        meta_title=payload.get("meta_title"),
        meta_description=payload.get("meta_description"),
        slug=payload.get("slug"),
    )
    result = current_domain.process(command, asynchronous=False)
    return JSONResponse(status_code=201, content={"product_id": result})


@product_router.put("/{product_id}/details")
async def update_product_details(product_id: str, request: Request):
    payload = await request.json()
    command = UpdateProductDetails(
        product_id=product_id,
        title=payload.get("title"),
        description=payload.get("description"),
        brand=payload.get("brand"),
        attributes=payload.get("attributes"),
        meta_title=payload.get("meta_title"),
        meta_description=payload.get("meta_description"),
        slug=payload.get("slug"),
    )
    current_domain.process(command, asynchronous=False)
    return JSONResponse(status_code=200, content={"status": "ok"})


@product_router.post("/{product_id}/variants", status_code=201)
async def add_variant(product_id: str, request: Request):
    payload = await request.json()
    command = AddVariant(
        product_id=product_id,
        variant_sku=payload["variant_sku"],
        attributes=payload.get("attributes"),
        base_price=payload["base_price"],
        currency=payload.get("currency", "USD"),
        weight_value=payload.get("weight_value"),
        weight_unit=payload.get("weight_unit"),
        length=payload.get("length"),
        width=payload.get("width"),
        height=payload.get("height"),
        dimension_unit=payload.get("dimension_unit"),
    )
    current_domain.process(command, asynchronous=False)
    return JSONResponse(status_code=201, content={"status": "ok"})


@product_router.put("/{product_id}/variants/{variant_id}/price")
async def update_variant_price(product_id: str, variant_id: str, request: Request):
    payload = await request.json()
    command = UpdateVariantPrice(
        product_id=product_id,
        variant_id=variant_id,
        base_price=payload["base_price"],
        currency=payload.get("currency", "USD"),
    )
    current_domain.process(command, asynchronous=False)
    return JSONResponse(status_code=200, content={"status": "ok"})


@product_router.put("/{product_id}/variants/{variant_id}/tier-price")
async def set_tier_price(product_id: str, variant_id: str, request: Request):
    payload = await request.json()
    command = SetTierPrice(
        product_id=product_id,
        variant_id=variant_id,
        tier=payload["tier"],
        price=payload["price"],
    )
    current_domain.process(command, asynchronous=False)
    return JSONResponse(status_code=200, content={"status": "ok"})


@product_router.post("/{product_id}/images", status_code=201)
async def add_product_image(product_id: str, request: Request):
    payload = await request.json()
    command = AddProductImage(
        product_id=product_id,
        url=payload["url"],
        alt_text=payload.get("alt_text"),
        is_primary=payload.get("is_primary", False),
    )
    current_domain.process(command, asynchronous=False)
    return JSONResponse(status_code=201, content={"status": "ok"})


@product_router.delete("/{product_id}/images/{image_id}")
async def remove_product_image(product_id: str, image_id: str):
    command = RemoveProductImage(
        product_id=product_id,
        image_id=image_id,
    )
    current_domain.process(command, asynchronous=False)
    return JSONResponse(status_code=200, content={"status": "ok"})


@product_router.put("/{product_id}/activate")
async def activate_product(product_id: str):
    command = ActivateProduct(product_id=product_id)
    current_domain.process(command, asynchronous=False)
    return JSONResponse(status_code=200, content={"status": "ok"})


@product_router.put("/{product_id}/discontinue")
async def discontinue_product(product_id: str):
    command = DiscontinueProduct(product_id=product_id)
    current_domain.process(command, asynchronous=False)
    return JSONResponse(status_code=200, content={"status": "ok"})


@product_router.put("/{product_id}/archive")
async def archive_product(product_id: str):
    command = ArchiveProduct(product_id=product_id)
    current_domain.process(command, asynchronous=False)
    return JSONResponse(status_code=200, content={"status": "ok"})


# --- Category endpoints ---


@category_router.post("", status_code=201)
async def create_category(request: Request):
    payload = await request.json()
    command = CreateCategory(
        name=payload["name"],
        parent_category_id=payload.get("parent_category_id"),
        attributes=payload.get("attributes"),
    )
    result = current_domain.process(command, asynchronous=False)
    return JSONResponse(status_code=201, content={"category_id": result})


@category_router.put("/{category_id}")
async def update_category(category_id: str, request: Request):
    payload = await request.json()
    command = UpdateCategory(
        category_id=category_id,
        name=payload.get("name"),
        attributes=payload.get("attributes"),
    )
    current_domain.process(command, asynchronous=False)
    return JSONResponse(status_code=200, content={"status": "ok"})


@category_router.put("/{category_id}/reorder")
async def reorder_category(category_id: str, request: Request):
    payload = await request.json()
    command = ReorderCategory(
        category_id=category_id,
        new_display_order=payload["new_display_order"],
    )
    current_domain.process(command, asynchronous=False)
    return JSONResponse(status_code=200, content={"status": "ok"})


@category_router.put("/{category_id}/deactivate")
async def deactivate_category(category_id: str):
    command = DeactivateCategory(category_id=category_id)
    current_domain.process(command, asynchronous=False)
    return JSONResponse(status_code=200, content={"status": "ok"})
