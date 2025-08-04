-- Add OIDC fields to existing OAuth tables

-- 1. Add OIDC fields to authorization_codes table
ALTER TABLE authorization_codes 
ADD COLUMN IF NOT EXISTS nonce VARCHAR(255),
ADD COLUMN IF NOT EXISTS auth_time TIMESTAMP;

COMMENT ON COLUMN authorization_codes.nonce IS 'OIDC nonce value for replay attack prevention';
COMMENT ON COLUMN authorization_codes.auth_time IS 'Time when user authenticated for max_age validation';

-- 2. Add OIDC fields to oauth_clients table
ALTER TABLE oauth_clients
ADD COLUMN IF NOT EXISTS oidc_enabled BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS id_token_signed_response_alg VARCHAR(10) DEFAULT 'RS256',
ADD COLUMN IF NOT EXISTS userinfo_signed_response_alg VARCHAR(10),
ADD COLUMN IF NOT EXISTS default_max_age INTEGER,
ADD COLUMN IF NOT EXISTS require_auth_time BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS oidc_migration_date TIMESTAMP;

COMMENT ON COLUMN oauth_clients.oidc_enabled IS 'Whether this client supports OIDC';
COMMENT ON COLUMN oauth_clients.id_token_signed_response_alg IS 'Algorithm for signing ID tokens';
COMMENT ON COLUMN oauth_clients.userinfo_signed_response_alg IS 'Algorithm for signing userinfo responses';
COMMENT ON COLUMN oauth_clients.default_max_age IS 'Default max authentication age in seconds';
COMMENT ON COLUMN oauth_clients.require_auth_time IS 'Whether to always include auth_time claim';
COMMENT ON COLUMN oauth_clients.oidc_migration_date IS 'When client migrated to OIDC';

-- 3. Add OIDC scopes to oauth_scopes table
INSERT INTO oauth_scopes (scope, description, category, is_sensitive) VALUES
('openid', 'OpenID Connect authentication', 'oidc', false),
('profile', 'Basic profile information', 'oidc', false),
('email', 'Email address and verification status', 'oidc', false),
('address', 'Physical address', 'oidc', false),
('phone', 'Phone number and verification status', 'oidc', false),
('offline_access', 'Maintain access while user is offline', 'oidc', false)
ON CONFLICT (scope) DO UPDATE SET
    description = EXCLUDED.description,
    category = EXCLUDED.category,
    is_sensitive = EXCLUDED.is_sensitive;

-- 4. Update allowed_scopes for existing clients to include OIDC scopes
UPDATE oauth_clients 
SET allowed_scopes = array_cat(
    allowed_scopes, 
    ARRAY['openid', 'profile', 'email', 'offline_access']::text[]
)
WHERE client_id IN ('maxflowstudio', 'maxteamsync', 'maxlab', 'maxworkspace', 'maxapa', 'maxmlops')
AND NOT (allowed_scopes @> ARRAY['openid']::text[]);

-- 5. Add refresh token fields for improved rotation tracking
ALTER TABLE oauth_refresh_tokens
ADD COLUMN IF NOT EXISTS token_status VARCHAR(20) DEFAULT 'active',
ADD COLUMN IF NOT EXISTS parent_token_hash VARCHAR(255),
ADD COLUMN IF NOT EXISTS rotation_grace_expires_at TIMESTAMP;

COMMENT ON COLUMN oauth_refresh_tokens.token_status IS 'Token status: active, rotating, revoked';
COMMENT ON COLUMN oauth_refresh_tokens.parent_token_hash IS 'Previous token in rotation chain';
COMMENT ON COLUMN oauth_refresh_tokens.rotation_grace_expires_at IS 'Grace period expiration for rotation';

-- 6. Create migration tracking table
CREATE TABLE IF NOT EXISTS oidc_migration_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id VARCHAR(50) NOT NULL REFERENCES oauth_clients(client_id),
    migration_phase VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL, -- planning, in_progress, completed, rolled_back
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE oidc_migration_status IS 'Track OIDC migration progress for each client';