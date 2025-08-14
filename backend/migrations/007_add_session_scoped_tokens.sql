-- Migration: Add session-scoped token management
-- Purpose: Enable session isolation for concurrent OAuth login scenarios
-- Date: 2025-08-14

-- Add session_id column to oauth_refresh_tokens for session-scoped token management
ALTER TABLE oauth_refresh_tokens 
ADD COLUMN IF NOT EXISTS session_id VARCHAR(255);

-- Add index for efficient session-based token queries
CREATE INDEX IF NOT EXISTS idx_oauth_refresh_tokens_session_scope 
ON oauth_refresh_tokens(user_id, client_id, session_id, token_status);

-- Add index for efficient session-based token cleanup
CREATE INDEX IF NOT EXISTS idx_oauth_refresh_tokens_session_id 
ON oauth_refresh_tokens(session_id);

-- Add comment for documentation
COMMENT ON COLUMN oauth_refresh_tokens.session_id IS 'Session identifier for session-scoped token isolation in concurrent login scenarios';

-- Also add session_id to oauth_access_tokens for consistency
ALTER TABLE oauth_access_tokens 
ADD COLUMN IF NOT EXISTS session_id VARCHAR(255);

-- Add index for access tokens
CREATE INDEX IF NOT EXISTS idx_oauth_access_tokens_session_scope 
ON oauth_access_tokens(user_id, client_id, session_id);

-- Add comment
COMMENT ON COLUMN oauth_access_tokens.session_id IS 'Session identifier for session-scoped access token management';

-- Record migration completion
INSERT INTO migration_log (migration_name, executed_at, description)
VALUES ('007_add_session_scoped_tokens', NOW(), 'Added session_id columns for session-scoped token management');