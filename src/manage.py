"""ShopStream database management CLI.

Provides commands to create and drop database schemas for all domains.
Reuses the setup_db/drop_db utilities already defined in each domain.

Usage:
    python src/manage.py setup-db   # Create all tables
    python src/manage.py drop-db    # Drop all tables
"""

import argparse
import sys


def setup_databases(domains=None):
    """Create database schemas for the specified (or all) domains."""
    from catalogue.domain import catalogue
    from catalogue.utils.db import setup_db as setup_catalogue_db
    from identity.domain import identity
    from identity.utils.db import setup_db as setup_identity_db

    all_domains = {
        "identity": (identity, setup_identity_db),
        "catalogue": (catalogue, setup_catalogue_db),
    }

    targets = {d: all_domains[d] for d in domains} if domains else all_domains

    for name, (domain, setup_fn) in targets.items():
        print(f"Initializing {name} domain...")
        domain.init()
        print(f"Creating {name} database schema...")
        setup_fn(domain)
        print(f"  {name} schema ready.")

    print("Done.")


def drop_databases(domains=None):
    """Drop database schemas for the specified (or all) domains."""
    from catalogue.domain import catalogue
    from catalogue.utils.db import drop_db as drop_catalogue_db
    from identity.domain import identity
    from identity.utils.db import drop_db as drop_identity_db

    all_domains = {
        "identity": (identity, drop_identity_db),
        "catalogue": (catalogue, drop_catalogue_db),
    }

    targets = {d: all_domains[d] for d in domains} if domains else all_domains

    for name, (domain, drop_fn) in targets.items():
        print(f"Initializing {name} domain...")
        domain.init()
        print(f"Dropping {name} database schema...")
        drop_fn(domain)
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
