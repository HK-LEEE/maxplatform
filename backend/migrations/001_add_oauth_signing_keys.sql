-- OAuth Signing Keys Table for OIDC
-- This table stores RSA key pairs for signing ID tokens

CREATE TABLE IF NOT EXISTS oauth_signing_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kid VARCHAR(255) UNIQUE NOT NULL,  -- Key ID for JWT header
    private_key TEXT NOT NULL,          -- Encrypted private key in PEM format
    public_key TEXT NOT NULL,           -- Public key in PEM format
    algorithm VARCHAR(10) DEFAULT 'RS256',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    rotated_at TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_oauth_signing_keys_kid ON oauth_signing_keys(kid);
CREATE INDEX IF NOT EXISTS idx_oauth_signing_keys_active ON oauth_signing_keys(is_active, expires_at);
CREATE INDEX IF NOT EXISTS idx_oauth_signing_keys_created ON oauth_signing_keys(created_at);

-- Comments
COMMENT ON TABLE oauth_signing_keys IS 'Cryptographic keys for OIDC token signing';
COMMENT ON COLUMN oauth_signing_keys.kid IS 'Key ID used in JWT header for key identification';
COMMENT ON COLUMN oauth_signing_keys.private_key IS 'Encrypted private key in PEM format for signing tokens';
COMMENT ON COLUMN oauth_signing_keys.public_key IS 'Public key in PEM format for token verification';
COMMENT ON COLUMN oauth_signing_keys.algorithm IS 'Signing algorithm (RS256, RS384, RS512)';
COMMENT ON COLUMN oauth_signing_keys.expires_at IS 'Key expiration time for automatic rotation';
COMMENT ON COLUMN oauth_signing_keys.rotated_at IS 'Timestamp when key was rotated';

-- Cleanup function for expired keys
CREATE OR REPLACE FUNCTION cleanup_expired_signing_keys()
RETURNS void AS $$
BEGIN
    DELETE FROM oauth_signing_keys 
    WHERE expires_at < NOW() - INTERVAL '30 days'
    OR (is_active = false AND rotated_at < NOW() - INTERVAL '30 days');
END;
$$ LANGUAGE plpgsql;