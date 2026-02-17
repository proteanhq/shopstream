"""ShopStream Observatory — real-time message flow observability.

Uses Protean's built-in Observatory server to provide a live dashboard,
Prometheus metrics, and REST API for monitoring the event pipeline
across both Identity and Catalogue domains.

Usage:
    uvicorn src.observatory:app --host 0.0.0.0 --port 9000
"""

from catalogue.domain import catalogue
from identity.domain import identity
from protean.server.observatory import create_observatory_app

identity.init()
catalogue.init()

app = create_observatory_app(
    domains=[identity, catalogue],
    title="ShopStream Observatory",
)
