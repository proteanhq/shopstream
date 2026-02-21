"""ShopStream FastAPI application.

Multi-domain web server that processes commands synchronously via HTTP.
Each request is wrapped in the correct domain context based on URL prefix.

Usage:
    uvicorn app:app --host 0.0.0.0 --port 8000 --reload --app-dir src
"""

from catalogue.api import category_router, product_router
from catalogue.domain import catalogue
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fulfillment.api import fulfillment_router
from fulfillment.domain import fulfillment
from identity.api import router as identity_router
from identity.domain import identity
from inventory.api import inventory_router, warehouse_router
from inventory.domain import inventory
from ordering.api import cart_router, order_router
from ordering.domain import ordering
from payments.api import invoice_router, payment_router
from payments.domain import payments
from protean.integrations.fastapi import (
    DomainContextMiddleware,
    register_exception_handlers,
)
from reviews.api import review_router
from reviews.domain import reviews
from scalar_fastapi import get_scalar_api_reference

# ---------------------------------------------------------------------------
# Domain initialization
# ---------------------------------------------------------------------------
identity.init()
catalogue.init()
ordering.init()
inventory.init()
payments.init()
fulfillment.init()
reviews.init()

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="ShopStream API",
    description="E-Commerce Platform API built on Protean",
    version="0.1.0",
    docs_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    DomainContextMiddleware,
    route_domain_map={
        "/customers": identity,
        "/products": catalogue,
        "/categories": catalogue,
        "/carts": ordering,
        "/orders": ordering,
        "/inventory": inventory,
        "/warehouses": inventory,
        "/payments": payments,
        "/invoices": payments,
        "/fulfillments": fulfillment,
        "/reviews": reviews,
    },
)

# ---------------------------------------------------------------------------
# Exception handlers (from Protean)
# ---------------------------------------------------------------------------
register_exception_handlers(app)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(identity_router)
app.include_router(product_router)
app.include_router(category_router)
app.include_router(cart_router)
app.include_router(order_router)
app.include_router(inventory_router)
app.include_router(warehouse_router)
app.include_router(payment_router)
app.include_router(invoice_router)
app.include_router(fulfillment_router)
app.include_router(review_router)


# ---------------------------------------------------------------------------
# API Documentation (Scalar)
# ---------------------------------------------------------------------------
@app.get("/docs", include_in_schema=False)
async def scalar_docs():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=app.title,
    )


# ---------------------------------------------------------------------------
# Health / root
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return JSONResponse(
        content={
            "status": "ok",
            "domains": {
                "identity": {"name": identity.name},
                "catalogue": {"name": catalogue.name},
                "ordering": {"name": ordering.name},
                "inventory": {"name": inventory.name},
                "payments": {"name": payments.name},
                "fulfillment": {"name": fulfillment.name},
                "reviews": {"name": reviews.name},
            },
        }
    )
