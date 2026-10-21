#!/bin/bash
# Install Message DB into message_store_test, the database PROTEAN_ENV=test uses.
# Protean's test fixtures truncate the event store between tests, so the tests
# need a database of their own, apart from the dev stack's message_store.
#
# Runs inside the message-db container. The compose file mounts it into
# /docker-entrypoint-initdb.d/, so it runs when the container starts on an
# empty data volume. For a container started before that, run
# `make setup-test-event-store`. It does nothing when the database exists.
set -euo pipefail

DATABASE_NAME=message_store_test
export PGUSER="${POSTGRES_USER:-postgres}"

if [ "$(psql -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$DATABASE_NAME'")" = "1" ]; then
    if [ "$(psql -d "$DATABASE_NAME" -tAc "SELECT to_regclass('message_store.messages') IS NOT NULL")" = "t" ]; then
        echo "Message DB database $DATABASE_NAME already exists"
        exit 0
    fi
    # An install that stopped after createdb. The database holds only test data,
    # so drop it and install again.
    psql -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE $DATABASE_NAME"
fi

# The image ships the Message DB install scripts under a versioned directory.
# install.sh creates the database, the schema, the functions and the
# message_store role's grants; it skips the role when it already exists.
cd /usr/src/eventide/message-db-*/database
DATABASE_NAME="$DATABASE_NAME" ./install.sh
