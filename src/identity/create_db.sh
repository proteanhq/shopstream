#!/bin/bash

# Variables for database connection
DB_HOST="localhost"
DB_PORT="5432"
DB_ADMIN="postgres"  # The database admin user (e.g., 'postgres')
DB_ADMIN_PASSWORD="postgres"

# Variables for the new user and database
DB_NAME="identity_local"
DB_USER="identity_local"
DB_USER_PASSWORD="identity_local"

# SQL commands to create the user
SQL_CREATE_USER=$(cat <<EOF
CREATE USER $DB_USER WITH PASSWORD '$DB_USER_PASSWORD';
EOF
)

# SQL commands to create the database
SQL_CREATE_DB=$(cat <<EOF
CREATE DATABASE $DB_NAME WITH OWNER $DB_USER;
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

# Execute the SQL command to create the database separately
PGPASSWORD="$DB_ADMIN_PASSWORD" psql -v ON_ERROR_STOP=1 -h "$DB_HOST" -p "$DB_PORT" -U "$DB_ADMIN" -d postgres -c "$SQL_CREATE_DB"

# Execute the SQL commands to grant schema-level privileges by connecting to the newly created database
PGPASSWORD="$DB_ADMIN_PASSWORD" psql -v ON_ERROR_STOP=1 -h "$DB_HOST" -p "$DB_PORT" -U "$DB_ADMIN" -d "$DB_NAME" -c "$SQL_GRANT_PRIVILEGES"
