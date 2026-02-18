#!/bin/bash
set -e

# Create additional databases beyond the default (identity_local).
# This script runs automatically on first container startup via
# /docker-entrypoint-initdb.d/.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE catalogue_local;
    CREATE DATABASE ordering_local;
EOSQL
