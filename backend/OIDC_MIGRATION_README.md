# OIDC Migration Guide for MAX Platform

## Overview

This guide explains how to apply the OIDC (OpenID Connect) database migrations to enable OIDC support in MAX Platform.

## Prerequisites

- PostgreSQL database running and accessible
- Python environment with psycopg2 installed
- Database credentials configured in `.env` file

## Migration Steps

### 1. Check Current Status

First, check if OIDC is already configured:

```bash
cd /home/lee/proejct/maxplatform/backend
python check_oidc_status.py
```

This will show:
- Which database tables exist
- Which OIDC features are enabled
- Current configuration status

### 2. Run Migrations

If the status check shows missing tables, run the migrations:

```bash
python run_oidc_migrations.py
```

This script will:
1. Create the `oauth_signing_keys` table for RSA key storage
2. Create the `oauth_nonces` table for replay attack prevention
3. Add OIDC fields to existing OAuth tables
4. Insert standard OIDC scopes (openid, profile, email, etc.)
5. Track migration status to prevent duplicate runs

### 3. Verify Migration

After running migrations, check the status again:

```bash
python check_oidc_status.py
```

You should see all tables with ✓ marks.

### 4. Restart Backend

After successful migration, restart the backend service:

```bash
# If running directly
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or if using a service manager
systemctl restart maxplatform-backend
```

### 5. Test OIDC Endpoints

Once the backend is running, test the OIDC endpoints:

1. **Discovery Endpoint**:
   ```bash
   curl http://localhost:8000/.well-known/openid-configuration
   ```

2. **JWKS Endpoint**:
   ```bash
   curl http://localhost:8000/api/oauth/jwks
   ```

3. **Test Authentication Flow**:
   ```bash
   # Get authorization code with OIDC scope
   http://localhost:8000/api/oauth/authorize?response_type=code&client_id=your-client&redirect_uri=http://localhost:3000/callback&scope=openid profile email&state=random&nonce=random
   ```

## Migration Details

### 001_add_oauth_signing_keys.sql
- Creates table for storing RSA key pairs
- Includes automatic cleanup for expired keys
- Supports key rotation with grace periods

### 002_add_oauth_nonces.sql
- Creates table for tracking nonces
- Prevents replay attacks
- Automatic cleanup of expired nonces

### 003_add_oidc_fields.sql
- Adds OIDC fields to oauth_clients table
- Inserts standard OIDC scopes
- Creates migration tracking table
- Updates service clients to support OIDC

## Troubleshooting

### Migration Fails

1. **Database Connection Error**:
   - Check DATABASE_URL in .env file
   - Verify PostgreSQL is running
   - Check network connectivity

2. **Permission Error**:
   - Ensure database user has CREATE TABLE permission
   - Check user has INSERT/UPDATE permissions

3. **Table Already Exists**:
   - This is normal if migrations were partially applied
   - The script handles existing tables gracefully

### Backend Won't Start

1. **Missing Tables Error**:
   ```
   sqlalchemy.exc.ProgrammingError: relation "oauth_signing_keys" does not exist
   ```
   - Run the migration script: `python run_oidc_migrations.py`

2. **Key Generation Error**:
   - Check cryptography package is installed: `pip install cryptography`
   - Verify sufficient system entropy for key generation

3. **Configuration Error**:
   - Check OIDC settings in .env file
   - Ensure OIDC_ISSUER is set correctly

## Rollback (if needed)

To rollback OIDC changes:

```sql
-- Connect to database
psql postgresql://user:pass@host:port/database

-- Drop OIDC tables
DROP TABLE IF EXISTS oauth_signing_keys CASCADE;
DROP TABLE IF EXISTS oauth_nonces CASCADE;
DROP TABLE IF EXISTS oidc_migrations CASCADE;

-- Remove OIDC columns from oauth_clients
ALTER TABLE oauth_clients 
DROP COLUMN IF EXISTS oidc_enabled,
DROP COLUMN IF EXISTS id_token_signed_response_alg,
DROP COLUMN IF EXISTS id_token_encrypted_response_alg,
DROP COLUMN IF EXISTS id_token_encrypted_response_enc;

-- Remove OIDC scopes
DELETE FROM oauth_scopes WHERE name IN ('openid', 'profile', 'email', 'address', 'phone');
```

## Next Steps

After successful migration:

1. Update client applications to use OIDC
2. Test ID token generation and validation
3. Configure key rotation schedule
4. Monitor signing key usage
5. Review security settings

## Support

For issues or questions:
1. Check application logs for detailed errors
2. Run status checker for current state
3. Review migration SQL files for details
4. Contact support with error messages and status output