#!/usr/bin/env python3
"""
Script to set up PostgreSQL user and database for testing.
"""
import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Configuration
DB_NAME = "tribe_db"
DB_USER = "tribe_user"
DB_PASSWORD = "tribe_password"

# Connection settings
# For Docker: use 'postgres' as the service name, for local use 'localhost'
PGHOST = os.getenv("PGHOST", "localhost")
PGPORT = os.getenv("PGPORT", "5432")
# Try tribe_user first (Docker), fallback to postgres (local)
PGUSER = os.getenv("PGUSER", "tribe_user")
PGPASSWORD = os.getenv("PGPASSWORD", "tribe_password")


def setup_database():
    """Create database and user if they don't exist."""
    try:
        # Connect to PostgreSQL server (default postgres database)
        conn = psycopg2.connect(
            host=PGHOST,
            port=PGPORT,
            user=PGUSER,
            password=PGPASSWORD,
            database="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Create user if not exists
        cursor.execute(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT FROM pg_user WHERE usename = '{DB_USER}') THEN
                    CREATE USER {DB_USER} WITH PASSWORD '{DB_PASSWORD}';
                    RAISE NOTICE 'User {DB_USER} created';
                ELSE
                    RAISE NOTICE 'User {DB_USER} already exists';
                END IF;
            END
            $$;
            """
        )

        # Create database if not exists
        cursor.execute(
            f"""
            SELECT 'CREATE DATABASE {DB_NAME} OWNER {DB_USER}'
            WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '{DB_NAME}');
            """
        )
        result = cursor.fetchone()
        if result and result[0]:
            cursor.execute(result[0])
            print(f"✅ Database '{DB_NAME}' created")
        else:
            print(f"ℹ️  Database '{DB_NAME}' already exists")

        # Grant privileges
        cursor.execute(f"GRANT ALL PRIVILEGES ON DATABASE {DB_NAME} TO {DB_USER};")

        cursor.close()
        conn.close()

        print(f"✅ PostgreSQL user '{DB_USER}' and database '{DB_NAME}' are ready!")
        print(f"   User: {DB_USER}")
        print(f"   Password: {DB_PASSWORD}")
        print(f"   Database: {DB_NAME}")
        print(f"   Connection string: postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{PGHOST}:{PGPORT}/{DB_NAME}")

    except psycopg2.OperationalError as e:
        print(f"❌ Error connecting to PostgreSQL: {e}")
        print(f"   Make sure PostgreSQL is running and accessible at {PGHOST}:{PGPORT}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error setting up database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("Setting up PostgreSQL user and database for Tribe backend...")
    setup_database()

