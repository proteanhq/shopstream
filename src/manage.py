"""ShopStream database management CLI.

Provides commands to create and drop database schemas for all domains.
Uses Protean's public domain.setup_database() / domain.drop_database() API.

Usage:
    python src/manage.py setup-db   # Create all tables
    python src/manage.py drop-db    # Drop all tables
"""

import argparse
import sys


def setup_databases(domains=None):
    """Create database schemas for the specified (or all) domains."""
    from catalogue.domain import catalogue
    from identity.domain import identity

    all_domains = {"identity": identity, "catalogue": catalogue}
    targets = {d: all_domains[d] for d in domains} if domains else all_domains

    for name, domain in targets.items():
        print(f"Initializing {name} domain...")
        domain.init()
        print(f"Creating {name} database schema...")
        with domain.domain_context():
            domain.setup_database()
        print(f"  {name} schema ready.")

    print("Done.")


def drop_databases(domains=None):
    """Drop database schemas for the specified (or all) domains."""
    from catalogue.domain import catalogue
    from identity.domain import identity

    all_domains = {"identity": identity, "catalogue": catalogue}
    targets = {d: all_domains[d] for d in domains} if domains else all_domains

    for name, domain in targets.items():
        print(f"Initializing {name} domain...")
        domain.init()
        print(f"Dropping {name} database schema...")
        with domain.domain_context():
            domain.drop_database()
        print(f"  {name} schema dropped.")

    print("Done.")


def main():
    parser = argparse.ArgumentParser(description="ShopStream database management")
    subparsers = parser.add_subparsers(dest="command", required=True)

    setup_parser = subparsers.add_parser("setup-db", help="Create all database tables")
    setup_parser.add_argument(
        "--domain",
        choices=["identity", "catalogue"],
        nargs="*",
        help="Specific domain(s) to set up (default: all)",
    )

    drop_parser = subparsers.add_parser("drop-db", help="Drop all database tables")
    drop_parser.add_argument(
        "--domain",
        choices=["identity", "catalogue"],
        nargs="*",
        help="Specific domain(s) to drop (default: all)",
    )

    args = parser.parse_args()

    if args.command == "setup-db":
        setup_databases(args.domain)
    elif args.command == "drop-db":
        drop_databases(args.domain)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
