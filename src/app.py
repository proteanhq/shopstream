"""ShopStream FastAPI application.

Multi-domain web server that processes commands synchronously via HTTP.
Each request is wrapped in the correct domain context based on URL prefix.

Usage:
    uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload
"""

# ---------------------------------------------------------------------------
# Domain initialization
# ---------------------------------------------------------------------------
# Domains are initialized at module level so uvicorn workers share them.
# PROTEAN_ENV controls which config overlay is applied:
#   - "test"       → event_processing = "sync"  (projectors fire in UoW)
#   - "production" → event_processing = "async" (projectors fire via Engine)
from catalogue.domain import catalogue  # noqa: E402
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from identity.domain import identity  # noqa: E402

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
    description="E-commerce platform — Identity & Catalogue domains",
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
    # No domain match — pass through (health check, docs, etc.)
    return await call_next(request)


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
from catalogue.api import category_router, product_router  # noqa: E402
from identity.api import router as identity_router  # noqa: E402

app.include_router(identity_router)
app.include_router(product_router)
app.include_router(category_router)


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
