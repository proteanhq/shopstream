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
from identity.api import router as identity_router
from identity.domain import identity
from protean.integrations.fastapi import (
    DomainContextMiddleware,
    register_exception_handlers,
)
from scalar_fastapi import get_scalar_api_reference

# ---------------------------------------------------------------------------
# Domain initialization
# ---------------------------------------------------------------------------
identity.init()
catalogue.init()

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
            },
        }
    )
