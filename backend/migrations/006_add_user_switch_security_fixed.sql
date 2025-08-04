-- Migration: Add User Switch Security Features (Fixed)
-- Version: 006
-- Description: Add tables and indexes for secure user switching and audit trail

-- Add revocation_reason column to oauth_access_tokens for better tracking
ALTER TABLE oauth_access_tokens 
ADD COLUMN IF NOT EXISTS revocation_reason VARCHAR(255);

-- Add index for revocation tracking
CREATE INDEX IF NOT EXISTS idx_oauth_access_tokens_revocation 
ON oauth_access_tokens(revoked_at, revocation_reason) 
WHERE revoked_at IS NOT NULL;

-- Create audit table for user switch events
CREATE TABLE IF NOT EXISTS oauth_user_switch_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id VARCHAR(255) NOT NULL,
    previous_user_id UUID,
    new_user_id UUID NOT NULL,
    switch_type VARCHAR(50) NOT NULL, -- 'user_change', 'first_login', 'same_user', 'error_detected'
    risk_level VARCHAR(20) NOT NULL, -- 'low', 'medium', 'high', 'critical'
    risk_factors JSONB DEFAULT '[]'::jsonb,
    request_ip INET,
    user_agent TEXT,
    cleanup_stats JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Add foreign key constraints for user switch audit
ALTER TABLE oauth_user_switch_audit
ADD CONSTRAINT IF NOT EXISTS fk_oauth_user_switch_audit_client_id 
FOREIGN KEY (client_id) REFERENCES oauth_clients(client_id) ON DELETE CASCADE;

ALTER TABLE oauth_user_switch_audit
ADD CONSTRAINT IF NOT EXISTS fk_oauth_user_switch_audit_previous_user 
FOREIGN KEY (previous_user_id) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE oauth_user_switch_audit
ADD CONSTRAINT IF NOT EXISTS fk_oauth_user_switch_audit_new_user 
FOREIGN KEY (new_user_id) REFERENCES users(id) ON DELETE CASCADE;

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_oauth_user_switch_audit_client_time 
ON oauth_user_switch_audit(client_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_oauth_user_switch_audit_risk_level 
ON oauth_user_switch_audit(risk_level, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_oauth_user_switch_audit_new_user 
ON oauth_user_switch_audit(new_user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_oauth_user_switch_audit_time_range 
ON oauth_user_switch_audit(created_at) 
WHERE created_at > NOW() - INTERVAL '30 days';

-- Add comments for documentation
COMMENT ON TABLE oauth_user_switch_audit IS 'Audit trail for user switching events in OAuth flow';
COMMENT ON COLUMN oauth_user_switch_audit.switch_type IS 'Type of user switch detected';
COMMENT ON COLUMN oauth_user_switch_audit.risk_level IS 'Security risk assessment level';
COMMENT ON COLUMN oauth_user_switch_audit.risk_factors IS 'Array of risk factors identified';
COMMENT ON COLUMN oauth_user_switch_audit.cleanup_stats IS 'Statistics of security cleanup performed';