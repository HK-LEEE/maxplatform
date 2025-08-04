-- Migration: Add Session Tracking Columns
-- Version: 007
-- Description: Add missing ip_address and user_agent columns to oauth_sessions for better security tracking

-- Add missing columns to oauth_sessions table for security audit
ALTER TABLE oauth_sessions 
ADD COLUMN IF NOT EXISTS ip_address INET,
ADD COLUMN IF NOT EXISTS user_agent TEXT;

-- Add indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_oauth_sessions_ip_address 
ON oauth_sessions(ip_address) 
WHERE ip_address IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_oauth_sessions_user_agent 
ON oauth_sessions(user_agent) 
WHERE user_agent IS NOT NULL;

-- Add index for security analysis combining IP and time
CREATE INDEX IF NOT EXISTS idx_oauth_sessions_security_tracking 
ON oauth_sessions(ip_address, created_at DESC) 
WHERE ip_address IS NOT NULL;

-- Add comments for documentation
COMMENT ON COLUMN oauth_sessions.ip_address IS 'Client IP address for security tracking';
COMMENT ON COLUMN oauth_sessions.user_agent IS 'Client user agent for device identification';

-- Update existing rows with NULL values (they will be populated on next login)
UPDATE oauth_sessions 
SET ip_address = NULL, user_agent = NULL 
WHERE ip_address IS NULL AND user_agent IS NULL;