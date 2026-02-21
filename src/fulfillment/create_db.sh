#!/bin/bash

# Variables for database connection
DB_HOST="localhost"
DB_PORT="5432"
DB_ADMIN="postgres"  # The database admin user (e.g., 'postgres')
DB_ADMIN_PASSWORD="postgres"

# Databases to create: dev and test
DATABASES=("fulfillment_local" "fulfillment_test")

for DB_NAME in "${DATABASES[@]}"; do
    DB_USER="$DB_NAME"
    DB_USER_PASSWORD="$DB_NAME"

    # SQL commands to create the user (idempotent)
    SQL_CREATE_USER=$(cat <<EOF
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$DB_USER') THEN
        CREATE USER $DB_USER WITH PASSWORD '$DB_USER_PASSWORD';
    END IF;
END
\$\$;
EOF
    )

    # SQL commands to grant schema-level privileges
    SQL_GRANT_PRIVILEGES=$(cat <<EOF
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
GRANT ALL PRIVILEGES ON SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO $DB_USER;
EOF
    )

    # Execute the SQL command to create the user
    PGPASSWORD="$DB_ADMIN_PASSWORD" psql -v ON_ERROR_STOP=1 -h "$DB_HOST" -p "$DB_PORT" -U "$DB_ADMIN" -d postgres -c "$SQL_CREATE_USER"

    # Create the database if it doesn't exist
    if ! PGPASSWORD="$DB_ADMIN_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_ADMIN" -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
        PGPASSWORD="$DB_ADMIN_PASSWORD" psql -v ON_ERROR_STOP=1 -h "$DB_HOST" -p "$DB_PORT" -U "$DB_ADMIN" -d postgres -c "CREATE DATABASE $DB_NAME WITH OWNER $DB_USER;"
    fi

    # Execute the SQL commands to grant schema-level privileges by connecting to the newly created database
    PGPASSWORD="$DB_ADMIN_PASSWORD" psql -v ON_ERROR_STOP=1 -h "$DB_HOST" -p "$DB_PORT" -U "$DB_ADMIN" -d "$DB_NAME" -c "$SQL_GRANT_PRIVILEGES"
done
