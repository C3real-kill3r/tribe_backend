#!/bin/bash
# Script to set up PostgreSQL user for testing

set -e

echo "Setting up PostgreSQL user for Tribe backend..."

# Check if running in Docker
if [ -f /.dockerenv ]; then
    # Inside Docker container
    PGHOST=postgres
else
    # Local development
    PGHOST=localhost
fi

PGUSER=${PGUSER:-postgres}
PGPASSWORD=${PGPASSWORD:-postgres}
DB_NAME=tribe_db
DB_USER=tribe_user
DB_PASSWORD=tribe_password

echo "Creating database and user..."

# Create user and database (using psql)
PGPASSWORD=$PGPASSWORD psql -h $PGHOST -U $PGUSER -d postgres <<EOF
-- Create user if not exists
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_user WHERE usename = '$DB_USER') THEN
        CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
        RAISE NOTICE 'User $DB_USER created';
    ELSE
        RAISE NOTICE 'User $DB_USER already exists';
    END IF;
END
\$\$;

-- Create database if not exists
SELECT 'CREATE DATABASE $DB_NAME OWNER $DB_USER'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF

echo "✅ PostgreSQL user '$DB_USER' and database '$DB_NAME' are ready!"
echo "   User: $DB_USER"
echo "   Password: $DB_PASSWORD"
echo "   Database: $DB_NAME"

