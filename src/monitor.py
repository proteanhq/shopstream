"""ShopStream monitoring dashboard.

Lightweight FastAPI server for monitoring outbox queues, Redis streams,
and overall infrastructure health across both domains.

Usage:
    uvicorn src.monitor:app --host 0.0.0.0 --port 9000
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Domain initialization
# ---------------------------------------------------------------------------
from catalogue.domain import catalogue  # noqa: E402
from identity.domain import identity  # noqa: E402

identity.init()
catalogue.init()

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="ShopStream Monitor",
    description="Monitoring dashboard for outbox queues, Redis streams, and infrastructure health",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _outbox_status(domain):
    """Query outbox counts for a domain."""
    try:
        with domain.domain_context():
            outbox_repo = domain._get_outbox_repo("default")
            counts = outbox_repo.count_by_status()
            return {"status": "ok", "counts": counts}
    except Exception as e:
        logger.error(f"Error querying outbox for {domain.name}: {e}")
        return {"status": "error", "error": str(e)}


def _broker_health(domain):
    """Query Redis broker health stats for a domain."""
    try:
        with domain.domain_context():
            broker = domain.brokers.get("default")
            if broker is None:
                return {"status": "error", "error": "No default broker configured"}
            stats = broker._health_stats()
            return {"status": "ok", **stats}
    except Exception as e:
        logger.error(f"Error querying broker for {domain.name}: {e}")
        return {"status": "error", "error": str(e)}


def _broker_info(domain):
    """Query Redis broker consumer group info for a domain."""
    try:
        with domain.domain_context():
            broker = domain.brokers.get("default")
            if broker is None:
                return {"status": "error", "error": "No default broker configured"}
            info = broker._info()
            return {"status": "ok", **info}
    except Exception as e:
        logger.error(f"Error querying broker info for {domain.name}: {e}")
        return {"status": "error", "error": str(e)}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    """Overall system status."""
    return JSONResponse(
        content={
            "service": "ShopStream Monitor",
            "domains": ["identity", "catalogue"],
        }
    )


@app.get("/health")
async def health():
    """Health check for all infrastructure components."""
    identity_broker = _broker_health(identity)
    catalogue_broker = _broker_health(catalogue)

    # Both brokers point to the same Redis, but checking both validates connectivity
    all_healthy = identity_broker.get("healthy", False) and catalogue_broker.get("healthy", False)

    return JSONResponse(
        content={
            "status": "ok" if all_healthy else "degraded",
            "infrastructure": {
                "redis": {
                    "healthy": identity_broker.get("healthy", False),
                    "version": identity_broker.get("redis_version", "unknown"),
                    "connected_clients": identity_broker.get("connected_clients", 0),
                    "memory": identity_broker.get("used_memory_human", "0B"),
                    "uptime_seconds": identity_broker.get("uptime_in_seconds", 0),
                },
            },
        }
    )


@app.get("/identity/outbox")
async def identity_outbox():
    """Identity domain outbox queue depth."""
    return JSONResponse(content={"domain": "identity", **_outbox_status(identity)})


@app.get("/catalogue/outbox")
async def catalogue_outbox():
    """Catalogue domain outbox queue depth."""
    return JSONResponse(content={"domain": "catalogue", **_outbox_status(catalogue)})


@app.get("/outbox")
async def outbox_summary():
    """Combined outbox status for all domains."""
    return JSONResponse(
        content={
            "identity": _outbox_status(identity),
            "catalogue": _outbox_status(catalogue),
        }
    )


@app.get("/streams")
async def streams():
    """Redis stream lengths and consumer group info."""
    # Both domains share the same Redis instance, so query once
    broker_info = _broker_info(identity)
    broker_health = _broker_health(identity)

    return JSONResponse(
        content={
            "message_counts": broker_health.get("message_counts", {}),
            "streams": broker_health.get("streams", {}),
            "consumer_groups": broker_info.get("consumer_groups", {}),
        }
    )
