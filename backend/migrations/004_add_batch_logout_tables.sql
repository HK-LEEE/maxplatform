-- Batch Logout Tables for MAX Platform
-- Supports tracking and managing batch logout operations

-- Create enum types if not exists
DO $$ BEGIN
    CREATE TYPE batch_logout_type AS ENUM (
        'group_based', 
        'client_based', 
        'time_based', 
        'conditional', 
        'emergency'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE batch_logout_status AS ENUM (
        'pending',
        'processing', 
        'completed', 
        'failed', 
        'cancelled'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE batch_logout_priority AS ENUM (
        'normal',
        'high', 
        'immediate'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Main batch logout jobs table
CREATE TABLE IF NOT EXISTS oauth_batch_logout_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type batch_logout_type NOT NULL,
    status batch_logout_status NOT NULL DEFAULT 'pending',
    initiated_by UUID NOT NULL REFERENCES users(id),
    reason TEXT NOT NULL,
    conditions JSONB NOT NULL, -- Stores job-specific conditions
    statistics JSONB, -- Stores result statistics
    error_details JSONB, -- Stores error information if failed
    dry_run BOOLEAN DEFAULT false,
    priority batch_logout_priority DEFAULT 'normal',
    progress INTEGER DEFAULT 0, -- Progress percentage (0-100)
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    cancelled_by UUID REFERENCES users(id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_batch_logout_status ON oauth_batch_logout_jobs(status, created_at);
CREATE INDEX IF NOT EXISTS idx_batch_logout_type ON oauth_batch_logout_jobs(job_type, status);
CREATE INDEX IF NOT EXISTS idx_batch_logout_priority ON oauth_batch_logout_jobs(priority, status) WHERE status IN ('pending', 'processing');

-- Table to track affected users in batch logout operations
CREATE TABLE IF NOT EXISTS oauth_batch_logout_affected_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES oauth_batch_logout_jobs(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    access_tokens_revoked INTEGER DEFAULT 0,
    refresh_tokens_revoked INTEGER DEFAULT 0,
    sessions_terminated INTEGER DEFAULT 0,
    notification_sent BOOLEAN DEFAULT false,
    notification_sent_at TIMESTAMP,
    notification_error TEXT,
    processed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Ensure unique constraint on job_id and user_id combination
ALTER TABLE oauth_batch_logout_affected_users 
ADD CONSTRAINT uq_batch_logout_job_user UNIQUE(job_id, user_id);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_affected_users_job ON oauth_batch_logout_affected_users(job_id);
CREATE INDEX IF NOT EXISTS idx_affected_users_user ON oauth_batch_logout_affected_users(user_id);
CREATE INDEX IF NOT EXISTS idx_affected_users_notification ON oauth_batch_logout_affected_users(job_id, notification_sent) 
WHERE notification_sent = false;

-- Comments for documentation
COMMENT ON TABLE oauth_batch_logout_jobs IS 'Tracks batch logout operations for audit and management';
COMMENT ON COLUMN oauth_batch_logout_jobs.job_type IS 'Type of batch logout operation';
COMMENT ON COLUMN oauth_batch_logout_jobs.conditions IS 'JSON object containing job-specific conditions like group_id, client_id, time ranges, etc.';
COMMENT ON COLUMN oauth_batch_logout_jobs.statistics IS 'JSON object containing result statistics like total tokens revoked, users affected, etc.';
COMMENT ON COLUMN oauth_batch_logout_jobs.dry_run IS 'If true, simulates the operation without actually revoking tokens';
COMMENT ON COLUMN oauth_batch_logout_jobs.priority IS 'Job priority for processing order';

COMMENT ON TABLE oauth_batch_logout_affected_users IS 'Tracks individual users affected by batch logout operations';
COMMENT ON COLUMN oauth_batch_logout_affected_users.notification_error IS 'Error message if notification sending failed';

-- Function to get batch logout job statistics
CREATE OR REPLACE FUNCTION get_batch_logout_statistics(job_uuid UUID)
RETURNS TABLE(
    total_users_affected BIGINT,
    total_access_tokens_revoked BIGINT,
    total_refresh_tokens_revoked BIGINT,
    total_sessions_terminated BIGINT,
    total_notifications_sent BIGINT,
    total_notification_failures BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(DISTINCT user_id) as total_users_affected,
        COALESCE(SUM(access_tokens_revoked), 0) as total_access_tokens_revoked,
        COALESCE(SUM(refresh_tokens_revoked), 0) as total_refresh_tokens_revoked,
        COALESCE(SUM(sessions_terminated), 0) as total_sessions_terminated,
        COUNT(*) FILTER (WHERE notification_sent = true) as total_notifications_sent,
        COUNT(*) FILTER (WHERE notification_error IS NOT NULL) as total_notification_failures
    FROM oauth_batch_logout_affected_users
    WHERE job_id = job_uuid;
END;
$$ LANGUAGE plpgsql;

-- Function to cancel a batch logout job
CREATE OR REPLACE FUNCTION cancel_batch_logout_job(
    job_uuid UUID,
    cancelled_by_user UUID
)
RETURNS BOOLEAN AS $$
DECLARE
    current_status batch_logout_status;
BEGIN
    -- Get current job status
    SELECT status INTO current_status
    FROM oauth_batch_logout_jobs
    WHERE id = job_uuid;
    
    -- Can only cancel pending or processing jobs
    IF current_status IN ('pending', 'processing') THEN
        UPDATE oauth_batch_logout_jobs
        SET 
            status = 'cancelled',
            cancelled_at = NOW(),
            cancelled_by = cancelled_by_user
        WHERE id = job_uuid;
        
        RETURN true;
    ELSE
        RETURN false;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Add batch logout related actions to audit log
-- This assumes oauth_audit_logs table exists
DO $$ 
BEGIN
    -- Add new audit actions if oauth_audit_logs exists
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'oauth_audit_logs') THEN
        -- Add constraint to check valid actions if not exists
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint 
            WHERE conname = 'oauth_audit_logs_action_check'
        ) THEN
            -- Log that we're skipping the constraint update
            RAISE NOTICE 'oauth_audit_logs table exists but action constraint not found';
        END IF;
    END IF;
END $$;

-- Grant necessary permissions (adjust based on your user setup)
-- GRANT SELECT, INSERT, UPDATE ON oauth_batch_logout_jobs TO your_app_user;
-- GRANT SELECT, INSERT, UPDATE ON oauth_batch_logout_affected_users TO your_app_user;
-- GRANT EXECUTE ON FUNCTION get_batch_logout_statistics TO your_app_user;
-- GRANT EXECUTE ON FUNCTION cancel_batch_logout_job TO your_app_user;