"""ShopStream FastAPI application.

Multi-domain web server that processes commands synchronously via HTTP.
Each request is wrapped in the correct domain context based on URL prefix.

Usage:
    uvicorn app:app --host 0.0.0.0 --port 8000 --reload --app-dir src
"""

import contextlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from protean import g
from protean.integrations.fastapi import (
    DomainContextMiddleware,
    instrument_app,
    register_exception_handlers,
)
from protean.integrations.logging import protean_correlation_processor
from protean.utils.logging import configure_logging
from scalar_fastapi import get_scalar_api_reference

from catalogue.api import category_router, product_router
from catalogue.domain import catalogue
from fulfillment.api import fulfillment_router
from fulfillment.domain import fulfillment
from identity.api import router as identity_router
from identity.domain import identity
from inventory.api import inventory_maintenance_router, inventory_router, warehouse_router
from inventory.domain import inventory
from notifications.api import notification_router
from notifications.domain import notifications
from ordering.api import cart_router, order_router, ordering_maintenance_router
from ordering.domain import ordering
from payments.api import invoice_router, payment_router
from payments.domain import payments
from reviews.api import review_router
from reviews.domain import reviews

# ---------------------------------------------------------------------------
# Structured logging — environment-aware, with automatic correlation context
# ---------------------------------------------------------------------------
configure_logging(extra_processors=[protean_correlation_processor])

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
notifications.init()

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
        "/notifications": notifications,
    },
)


# ---------------------------------------------------------------------------
# User context middleware — populates Protean's `g` with user identity
# Correlation IDs are handled automatically by DomainContextMiddleware.
# ---------------------------------------------------------------------------
class UserContextMiddleware:
    """Extract user_id from headers into Protean's thread-local g."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            user_id = headers.get(b"x-user-id", b"").decode() or None

            with contextlib.suppress(AttributeError):
                g.user_id = user_id  # No-op when no domain context is active

        await self.app(scope, receive, send)


app.add_middleware(UserContextMiddleware)

# ---------------------------------------------------------------------------
# OpenTelemetry instrumentation (opt-in via [telemetry] in domain.toml)
# Safe to call even without opentelemetry installed — returns False silently.
# Uses the first domain's tracer/meter providers for HTTP span creation.
# ---------------------------------------------------------------------------
instrument_app(app, ordering, excluded_urls="/health,/docs")

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
app.include_router(notification_router)

# Maintenance routers (background job endpoints)
app.include_router(inventory_maintenance_router)
app.include_router(ordering_maintenance_router)


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
                "notifications": {"name": notifications.name},
            },
        }
    )
