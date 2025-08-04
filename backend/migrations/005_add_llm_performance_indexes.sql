-- Migration 005: LLM Model Performance Indexes - Wave 2 Optimization
-- Addresses database timeout issues with model permission queries
-- Target: Model ID 4a807dd5-d62a-45e2-a6b2-45b40c39903f and similar timeouts

-- Add composite indexes for permission queries
-- These indexes optimize the complex joins used in permission checking

-- 1. Composite index for model permissions by model_id and grantee_type/grantee_id
-- Optimizes: SELECT * FROM maxllm_model_permissions WHERE model_id = ? AND grantee_type = ? AND grantee_id = ?
CREATE INDEX IF NOT EXISTS idx_model_permissions_composite 
ON maxllm_model_permissions (model_id, grantee_type, grantee_id);

-- 2. Index for permission queries by grantee (user or group lookups)
-- Optimizes: SELECT model_id FROM maxllm_model_permissions WHERE grantee_type = ? AND grantee_id = ?
CREATE INDEX IF NOT EXISTS idx_model_permissions_grantee 
ON maxllm_model_permissions (grantee_type, grantee_id);

-- 3. Index for model ownership queries
-- Optimizes: SELECT * FROM maxllm_models WHERE owner_type = ? AND owner_id = ?
CREATE INDEX IF NOT EXISTS idx_models_owner 
ON maxllm_models (owner_type, owner_id);

-- 4. Index for active models
-- Optimizes: SELECT * FROM maxllm_models WHERE is_active = true
CREATE INDEX IF NOT EXISTS idx_models_active 
ON maxllm_models (is_active) WHERE is_active = true;

-- 5. Composite index for model type and active status
-- Optimizes filtered queries by model type
CREATE INDEX IF NOT EXISTS idx_models_type_active 
ON maxllm_models (model_type, is_active);

-- 6. Index for permission granted_by queries (for audit trails)
-- Optimizes: SELECT * FROM maxllm_model_permissions WHERE granted_by = ?
CREATE INDEX IF NOT EXISTS idx_model_permissions_granted_by 
ON maxllm_model_permissions (granted_by);

-- 7. Covering index for permission response data
-- Optimizes the full permission response without additional table lookups
CREATE INDEX IF NOT EXISTS idx_model_permissions_response_covering 
ON maxllm_model_permissions (model_id, grantee_type, grantee_id, granted_by, created_at, updated_at);

-- 8. Index for model search by name (for admin search functionality)
-- Optimizes: SELECT * FROM maxllm_models WHERE model_name LIKE ?
CREATE INDEX IF NOT EXISTS idx_models_name_search 
ON maxllm_models (model_name);

-- 9. Partial index for user-owned models only
-- Optimizes queries for models owned by users (excludes system/group models)
CREATE INDEX IF NOT EXISTS idx_models_user_owned 
ON maxllm_models (owner_id, created_at) WHERE owner_type = 'USER';

-- 10. Partial index for group-owned models only
-- Optimizes queries for models owned by groups
CREATE INDEX IF NOT EXISTS idx_models_group_owned 
ON maxllm_models (owner_id, created_at) WHERE owner_type = 'GROUP';

-- Statistics update to ensure query planner uses new indexes efficiently
-- Note: Syntax varies by database type
-- PostgreSQL:
-- ANALYZE maxllm_models;
-- ANALYZE maxllm_model_permissions;

-- SQLite (if used):
-- ANALYZE;

-- Performance monitoring queries (for verification)
/*
-- Query to check index usage (PostgreSQL):
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes 
WHERE tablename IN ('maxllm_models', 'maxllm_model_permissions')
ORDER BY idx_scan DESC;

-- Query to check slow queries related to models:
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements 
WHERE query LIKE '%maxllm_model%'
ORDER BY total_time DESC
LIMIT 10;
*/

-- Migration verification
-- These queries should run significantly faster after index creation:

-- Test Query 1: Permission lookup for specific model (was timing out)
-- SELECT * FROM maxllm_model_permissions WHERE model_id = '4a807dd5-d62a-45e2-a6b2-45b40c39903f';

-- Test Query 2: User permission check across all models
-- SELECT m.*, p.grantee_type, p.grantee_id 
-- FROM maxllm_models m 
-- LEFT JOIN maxllm_model_permissions p ON m.id = p.model_id 
-- WHERE p.grantee_type = 'USER' AND p.grantee_id = 'some-user-id';

-- Test Query 3: Active models by type
-- SELECT * FROM maxllm_models WHERE model_type = 'AZURE_OPENAI' AND is_active = true;

-- Expected performance improvements:
-- - Permission queries: 80-95% reduction in execution time
-- - Model listing: 60-80% reduction in execution time  
-- - Complex permission joins: 70-90% reduction in execution time
-- - Admin queries: 50-70% reduction in execution time