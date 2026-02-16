from protean.domain import Domain
from sqlalchemy import create_engine


def setup_db(domain: Domain):
    """Setup database schema"""
    with domain.domain_context():
        for _, provider in domain.providers.items():
            if provider.conn_info["provider"] in ("sqlite", "postgresql"):
                engine = create_engine(provider.conn_info["database_uri"])

                for _, aggregate_record in domain.registry.aggregates.items():
                    if aggregate_record.cls.meta_.provider == provider.name:
                        domain.repository_for(aggregate_record.cls)._dao  # noqa: B018

                for _, entity_record in domain.registry.entities.items():
                    if entity_record.cls.meta_.provider == provider.name:
                        domain.repository_for(entity_record.cls)._dao  # noqa: B018

                for _, entity_record in domain.registry.projections.items():
                    if entity_record.cls.meta_.provider == provider.name:
                        domain.repository_for(entity_record.cls)._dao  # noqa: B018

                # Force DAO creation for outbox tables (registered as internal)
                if hasattr(domain, "_outbox_repos") and provider.name in domain._outbox_repos:
                    domain._outbox_repos[provider.name]._dao  # noqa: B018

                provider._metadata.create_all(engine)


def drop_db(domain: Domain):
    """Drop database schema"""
    with domain.domain_context():
        for _, provider in domain.providers.items():
            if provider.conn_info["provider"] in ("sqlite", "postgresql"):
                engine = create_engine(provider.conn_info["database_uri"])
                provider._metadata.drop_all(engine)
