from protean.domain import Domain
from sqlalchemy import create_engine


def setup_db(domain: Domain):
    """Setup database schema"""
    with domain.domain_context():
        # Setup databases before running tests
        for _, provider in domain.providers.items():
            if provider.conn_info["provider"] in ("sqlite", "postgresql"):
                engine = create_engine(provider.conn_info["database_uri"])

                # Ensure live entities are loaded and registered with SQLAlchemy
                #   We do this by accessing the _dao attribute of the repository, forcing
                #   the entity to be loaded and registered with SQLAlchemy.
                # noqa: B018 is used to suppress the warning about the _dao attribute
                for _, aggregate_record in domain.registry.aggregates.items():
                    if aggregate_record.cls.meta_.provider == provider.name:
                        domain.repository_for(aggregate_record.cls)._dao  # noqa: B018

                for _, entity_record in domain.registry.entities.items():
                    if entity_record.cls.meta_.provider == provider.name:
                        domain.repository_for(entity_record.cls)._dao  # noqa: B018

                for _, entity_record in domain.registry.projections.items():
                    if entity_record.cls.meta_.provider == provider.name:
                        domain.repository_for(entity_record.cls)._dao  # noqa: B018

                # Create RDBMS Tables
                provider._metadata.create_all(engine)


def drop_db(domain: Domain):
    """Drop database schema"""
    with domain.domain_context():
        # Setup databases before running tests
        for _, provider in domain.providers.items():
            if provider.conn_info["provider"] in ("sqlite", "postgresql"):
                engine = create_engine(provider.conn_info["database_uri"])

                # Destroy databases after running tests
                provider._metadata.drop_all(engine)
