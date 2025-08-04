#!/usr/bin/env python3
"""
OIDC Migration Runner for MAX Platform

This script applies the OIDC database migrations to enable OpenID Connect support.
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from datetime import datetime
from app.config import settings
from urllib.parse import urlparse


def parse_database_url(database_url):
    """Parse database URL into connection parameters"""
    result = urlparse(database_url)
    return {
        'host': result.hostname,
        'port': result.port or 5432,
        'database': result.path[1:],
        'user': result.username,
        'password': result.password
    }


def ensure_migration_table_exists(conn):
    """Ensure the migration tracking table exists"""
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS oidc_migrations (
                    id SERIAL PRIMARY KEY,
                    migration_name VARCHAR(255) UNIQUE NOT NULL,
                    applied_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
            """)
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        print(f"✗ Failed to create migration table: {str(e)}")
        return False


def run_migration(conn, migration_file, migration_name):
    """Run a single migration file"""
    try:
        with open(migration_file, 'r') as f:
            sql_content = f.read()
        
        with conn.cursor() as cursor:
            # Check if migration was already applied
            cursor.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name = 'oidc_migrations'"
            )
            if cursor.fetchone():
                cursor.execute(
                    "SELECT 1 FROM oidc_migrations WHERE migration_name = %s",
                    (migration_name,)
                )
                if cursor.fetchone():
                    print(f"✓ Migration {migration_name} already applied")
                    return True
            
            # Run the migration
            print(f"→ Applying migration: {migration_name}")
            cursor.execute(sql_content)
            
            # Record the migration
            cursor.execute("""
                INSERT INTO oidc_migrations (migration_name, applied_at)
                VALUES (%s, %s)
                ON CONFLICT (migration_name) DO NOTHING
            """, (migration_name, datetime.utcnow()))
            
            conn.commit()
            print(f"✓ Successfully applied: {migration_name}")
            return True
            
    except Exception as e:
        conn.rollback()
        print(f"✗ Failed to apply {migration_name}: {str(e)}")
        return False


def main():
    """Main migration runner"""
    print("MAX Platform OIDC Migration Runner")
    print("=" * 50)
    
    # Parse database connection
    db_params = parse_database_url(settings.database_url)
    
    try:
        # Connect to database
        print(f"Connecting to database: {db_params['database']} at {db_params['host']}:{db_params['port']}")
        conn = psycopg2.connect(**db_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        # Get migration files
        migration_dir = os.path.join(os.path.dirname(__file__), 'migrations')
        migration_files = [
            ('001_add_oauth_signing_keys.sql', 'add_oauth_signing_keys'),
            ('002_add_oauth_nonces.sql', 'add_oauth_nonces'),
            ('003_add_oidc_fields.sql', 'add_oidc_fields')
        ]
        
        print(f"\nFound {len(migration_files)} migrations to process")
        print("=" * 50)
        
        # Ensure migration tracking table exists
        if not ensure_migration_table_exists(conn):
            print("Failed to create migration tracking table")
            return 1
        
        # Run migrations in order
        success_count = 0
        for filename, migration_name in migration_files:
            filepath = os.path.join(migration_dir, filename)
            if os.path.exists(filepath):
                if run_migration(conn, filepath, migration_name):
                    success_count += 1
            else:
                print(f"✗ Migration file not found: {filename}")
        
        # Summary
        print("\n" + "=" * 50)
        print(f"Migration Summary: {success_count}/{len(migration_files)} migrations successful")
        
        if success_count == len(migration_files):
            print("\n✓ All OIDC migrations completed successfully!")
            print("\nNext steps:")
            print("1. Restart the MAX Platform backend")
            print("2. The JWKS service will automatically generate signing keys")
            print("3. Test OIDC endpoints at:")
            print(f"   - Discovery: {settings.max_platform_api_url}/.well-known/openid-configuration")
            print(f"   - JWKS: {settings.max_platform_api_url}/api/oauth/jwks")
            return 0
        else:
            print("\n✗ Some migrations failed. Please check the errors above.")
            return 1
            
    except psycopg2.Error as e:
        print(f"\n✗ Database connection error: {str(e)}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {str(e)}")
        return 1
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    sys.exit(main())
