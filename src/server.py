"""Protean Engine runner for ShopStream domains.

Starts Engine workers that process events asynchronously:
- OutboxProcessor: polls outbox table, publishes events to Redis Streams
- StreamSubscriptions: reads Redis Streams, invokes projectors and event handlers

Usage:
    python src/server.py                    # Run both domain engines
    python src/server.py --domain identity  # Run only identity engine
    python src/server.py --domain catalogue # Run only catalogue engine
"""

import argparse

from protean.server.engine import Engine


def _get_domain(name):
    """Import and initialize a domain by name."""
    if name == "identity":
        from identity.domain import identity

        identity.init()
        return identity
    elif name == "catalogue":
        from catalogue.domain import catalogue

        catalogue.init()
        return catalogue
    else:
        raise ValueError(f"Unknown domain: {name}")


def main():
    parser = argparse.ArgumentParser(description="ShopStream Engine runner")
    parser.add_argument(
        "--domain",
        choices=["identity", "catalogue"],
        help="Run a single domain engine (default: run all)",
    )
    args = parser.parse_args()

    domain_name = args.domain or "identity"
    domain = _get_domain(domain_name)
    engine = Engine(domain)
    engine.run()


if __name__ == "__main__":
    main()
