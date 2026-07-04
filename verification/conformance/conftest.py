"""Conformance harness fixtures — override Protean's adapter-conformance plugin.

Protean ships `protean.integrations.pytest.adapter_conformance` (auto-registered),
which gives `--db MEMORY|POSTGRESQL|SQLITE`, a `test_domain` fixture, a `db`
fixture (create/drop artifacts), capability markers, and per-test resets. Its
`test_domain` builds a throwaway domain but registers NO elements, and its
default Postgres URI is `:5432`. We override two fixtures:

  * `db_config`  — point Postgres at ShopStream's instance (:15432) and SQLite at
    a temp file (a file, not `:memory:`, so it survives SQLite's SingletonThreadPool).
  * `test_domain` — register the conformance elements before init.

Run one provider per invocation:

    PYTHONPATH=src pytest verification/conformance/ --db MEMORY -q
    PYTHONPATH=src pytest verification/conformance/ --db SQLITE -q
    PYTHONPATH=src pytest verification/conformance/ --db POSTGRESQL -q

(or `make conformance`, which runs all three and prints the skip-rate).
"""

import pytest
from protean import Domain
from protean.integrations.pytest.adapter_conformance import resolve_db_config

from verification.conformance.elements import CONFORMANCE_ELEMENTS

# ShopStream infra (matches docker-compose): Postgres on :15432, a temp SQLite file.
_SHOPSTREAM_POSTGRES_URI = "postgresql://postgres:postgres@localhost:15432/postgres"
_SQLITE_URI = "sqlite:////tmp/shopstream_conformance.db"


@pytest.fixture(scope="session")
def db_config(request):
    """Resolve the provider config, pointing SQL adapters at ShopStream's infra."""
    key = request.config.getoption("--db", default="MEMORY")
    explicit_uri = request.config.getoption("--db-uri", default=None)
    cfg = dict(
        resolve_db_config(
            db_key=key,
            db_provider=request.config.getoption("--db-provider", default=None),
            db_uri=explicit_uri,
            db_extra=request.config.getoption("--db-extra", default=None),
        )
    )
    if explicit_uri is None:
        if cfg.get("provider") == "postgresql":
            cfg["database_uri"] = _SHOPSTREAM_POSTGRES_URI
        elif cfg.get("provider") == "sqlite":
            cfg["database_uri"] = _SQLITE_URI
    return cfg


@pytest.fixture(autouse=True)
def test_domain(db_config, store_config, broker_config, request):
    """Like the plugin's fixture, but with the conformance elements registered."""
    if "no_test_domain" in request.keywords:
        yield
        return

    domain = Domain(name="ShopStreamConformance")
    domain.config["databases"]["default"] = db_config
    domain.config["event_store"] = store_config
    domain.config["brokers"]["default"] = broker_config
    domain.config["command_processing"] = "sync"
    domain.config["event_processing"] = "sync"
    domain.config["message_processing"] = "sync"

    for element in CONFORMANCE_ELEMENTS:
        domain.register(element)
    domain._initialize()

    with domain.domain_context():
        yield domain
