"""ShopStream FastAPI application.

Multi-domain web server that processes commands synchronously via HTTP.
Each request is wrapped in the correct domain context based on URL prefix.

Usage:
    uvicorn app:app --host 0.0.0.0 --port 8000 --reload --app-dir src
"""

from catalogue.api import category_router, product_router
from catalogue.domain import catalogue
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from identity.api import router as identity_router
from identity.domain import identity
from scalar_fastapi import get_scalar_api_reference

# ---------------------------------------------------------------------------
# Domain initialization
# ---------------------------------------------------------------------------
identity.init()
catalogue.init()

# ---------------------------------------------------------------------------
# Route-to-domain mapping
# ---------------------------------------------------------------------------
_ROUTE_DOMAIN_MAP = {
    "/customers": identity,
    "/products": catalogue,
    "/categories": catalogue,
}


def _resolve_domain(path: str):
    """Return the domain for the given request path, or None."""
    for prefix, domain in _ROUTE_DOMAIN_MAP.items():
        if path.startswith(prefix):
            return domain
    return None


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


@app.middleware("http")
async def domain_context_middleware(request: Request, call_next):
    """Push the correct Protean domain context for each request."""
    domain = _resolve_domain(request.url.path)
    if domain is not None:
        with domain.domain_context():
            response = await call_next(request)
        return response
    return await call_next(request)


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
