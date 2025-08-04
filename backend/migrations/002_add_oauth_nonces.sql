-- OAuth Nonces Table for OIDC
-- This table stores nonces for replay attack prevention

CREATE TABLE IF NOT EXISTS oauth_nonces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nonce_hash VARCHAR(255) NOT NULL,  -- SHA256 hash of nonce
    client_id VARCHAR(50) NOT NULL,
    user_id UUID,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create index for fast lookup
CREATE INDEX IF NOT EXISTS idx_oauth_nonces_lookup ON oauth_nonces(nonce_hash, client_id, expires_at);

-- Comments
COMMENT ON TABLE oauth_nonces IS 'Nonce tracking for OIDC replay attack prevention';
COMMENT ON COLUMN oauth_nonces.nonce_hash IS 'SHA256 hash of the nonce value';
COMMENT ON COLUMN oauth_nonces.client_id IS 'OAuth client that generated the nonce';
COMMENT ON COLUMN oauth_nonces.user_id IS 'User associated with the nonce (optional)';
COMMENT ON COLUMN oauth_nonces.expires_at IS 'Expiration time for automatic cleanup';
COMMENT ON COLUMN oauth_nonces.used_at IS 'Timestamp when nonce was consumed';

-- Cleanup function for expired nonces
CREATE OR REPLACE FUNCTION cleanup_expired_nonces()
RETURNS void AS $$
BEGIN
    DELETE FROM oauth_nonces
    WHERE expires_at < NOW()
    OR used_at < NOW() - INTERVAL '1 hour';
END;
$$ LANGUAGE plpgsql;