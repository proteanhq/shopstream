"""Protean Engine runner for all ShopStream domains.

Starts one Engine per domain. Each engine runs:
- OutboxProcessor: polls outbox table, publishes events to Redis Streams
- BrokerSubscriptions: reads Redis Streams, invokes subscribers (Phase 2+)
"""

import asyncio

from protean.server.engine import Engine


async def run():
    from catalogue.domain import catalogue
    from identity.domain import identity

    identity.init()
    catalogue.init()

    identity_engine = Engine(identity)
    catalogue_engine = Engine(catalogue)

    await asyncio.gather(
        identity_engine.run(),
        catalogue_engine.run(),
    )


if __name__ == "__main__":
    asyncio.run(run())
