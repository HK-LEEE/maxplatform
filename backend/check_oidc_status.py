#!/usr/bin/env python3
"""
OIDC Status Checker for MAX Platform

This script checks the current status of OIDC implementation.
"""

import psycopg2
from urllib.parse import urlparse
from app.config import settings
import sys


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


def check_table_exists(cursor, table_name):
    """Check if a table exists in the database"""
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = %s
        )
    """, (table_name,))
    return cursor.fetchone()[0]


def check_oidc_status():
    """Check OIDC implementation status"""
    print("MAX Platform OIDC Status Checker")
    print("=" * 50)
    
    db_params = parse_database_url(settings.database_url)
    
    try:
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()
        
        # Check critical tables
        tables = {
            'oauth_signing_keys': 'OIDC signing keys storage',
            'oauth_nonces': 'Nonce tracking for replay prevention',
            'oidc_migrations': 'Migration tracking table'
        }
        
        print("\nDatabase Tables:")
        print("-" * 30)
        all_exist = True
        for table, description in tables.items():
            exists = check_table_exists(cursor, table)
            status = "✓" if exists else "✗"
            print(f"{status} {table:<25} - {description}")
            if not exists:
                all_exist = False
        
        # Check OIDC fields in oauth_clients
        print("\nOIDC Fields in oauth_clients:")
        print("-" * 30)
        if check_table_exists(cursor, 'oauth_clients'):
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'oauth_clients' 
                AND column_name IN ('oidc_enabled', 'id_token_signed_response_alg')
            """)
            oidc_columns = [row[0] for row in cursor.fetchall()]
            
            required_columns = ['oidc_enabled', 'id_token_signed_response_alg']
            for col in required_columns:
                status = "✓" if col in oidc_columns else "✗"
                print(f"{status} {col}")
        
        # Check OIDC scopes
        print("\nOIDC Scopes:")
        print("-" * 30)
        if check_table_exists(cursor, 'oauth_scopes'):
            # First check what columns exist
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'oauth_scopes'
            """)
            columns = [row[0] for row in cursor.fetchall()]
            
            if 'scope' in columns:
                # Use 'scope' column name
                cursor.execute("""
                    SELECT scope, description 
                    FROM oauth_scopes 
                    WHERE scope IN ('openid', 'profile', 'email', 'address', 'phone')
                    ORDER BY scope
                """)
            elif 'name' in columns:
                # Use 'name' column name
                cursor.execute("""
                    SELECT name, description 
                    FROM oauth_scopes 
                    WHERE name IN ('openid', 'profile', 'email', 'address', 'phone')
                    ORDER BY name
                """)
            scopes = cursor.fetchall()
            if scopes:
                for name, desc in scopes:
                    print(f"✓ {name:<10} - {desc}")
            else:
                print("✗ No OIDC scopes found")
        
        # Check active signing keys
        print("\nSigning Keys:")
        print("-" * 30)
        if check_table_exists(cursor, 'oauth_signing_keys'):
            cursor.execute("""
                SELECT kid, algorithm, is_active, expires_at 
                FROM oauth_signing_keys 
                WHERE is_active = true
                ORDER BY created_at DESC
                LIMIT 5
            """)
            keys = cursor.fetchall()
            if keys:
                for kid, alg, active, expires in keys:
                    status = "✓" if active else "✗"
                    print(f"{status} {kid} ({alg}) - Expires: {expires}")
            else:
                print("✗ No active signing keys found")
        
        # Configuration status
        print("\nConfiguration:")
        print("-" * 30)
        print(f"✓ OIDC Issuer: {settings.oidc_issuer}")
        print(f"✓ Signing Algorithm: {settings.oidc_signing_algorithm}")
        print(f"✓ Key Rotation: {settings.oidc_key_rotation_days} days")
        print(f"✓ ID Token Expiry: {settings.oidc_id_token_expire_minutes} minutes")
        print(f"✓ Migration Mode: {'Dual' if settings.oidc_dual_mode else 'OIDC Only'}")
        
        # Summary
        print("\n" + "=" * 50)
        if all_exist:
            print("✓ OIDC implementation is ready!")
            print("\nTest endpoints:")
            print(f"  - Discovery: {settings.max_platform_api_url}/.well-known/openid-configuration")
            print(f"  - JWKS: {settings.max_platform_api_url}/api/oauth/jwks")
        else:
            print("✗ OIDC implementation is not ready")
            print("\nRun the migration script:")
            print("  python run_oidc_migrations.py")
        
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"\n✗ Database error: {str(e)}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(check_oidc_status())