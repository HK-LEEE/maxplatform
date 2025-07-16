-- Graceful Token Rotation을 위한 스키마 확장
-- 기존 oauth_refresh_tokens 테이블에 추가 필드

-- 토큰 상태 필드 추가
ALTER TABLE oauth_refresh_tokens 
ADD COLUMN IF NOT EXISTS token_status VARCHAR(20) DEFAULT 'active' 
CHECK (token_status IN ('active', 'rotating', 'revoked', 'expired'));

-- 토큰 패밀리 추적을 위한 필드들
ALTER TABLE oauth_refresh_tokens 
ADD COLUMN IF NOT EXISTS parent_token_hash VARCHAR(255);

ALTER TABLE oauth_refresh_tokens 
ADD COLUMN IF NOT EXISTS rotation_grace_expires_at TIMESTAMP;

-- 토큰 패밀리 추적을 위한 인덱스
CREATE INDEX IF NOT EXISTS idx_oauth_refresh_tokens_parent 
ON oauth_refresh_tokens(parent_token_hash);

CREATE INDEX IF NOT EXISTS idx_oauth_refresh_tokens_status_grace 
ON oauth_refresh_tokens(token_status, rotation_grace_expires_at);

-- 토큰 상태별 인덱스
CREATE INDEX IF NOT EXISTS idx_oauth_refresh_tokens_status 
ON oauth_refresh_tokens(token_status);

-- 만료된 grace period 토큰 정리를 위한 함수
CREATE OR REPLACE FUNCTION cleanup_expired_grace_tokens()
RETURNS INTEGER AS $$
DECLARE
    cleaned_count INTEGER;
BEGIN
    -- Grace period가 만료된 'rotating' 상태 토큰들을 'revoked'로 변경
    UPDATE oauth_refresh_tokens 
    SET token_status = 'revoked',
        revoked_at = NOW()
    WHERE token_status = 'rotating' 
    AND rotation_grace_expires_at < NOW();
    
    GET DIAGNOSTICS cleaned_count = ROW_COUNT;
    
    RETURN cleaned_count;
END;
$$ LANGUAGE plpgsql;

-- 토큰 패밀리 조회 함수
CREATE OR REPLACE FUNCTION get_token_family(input_token_hash VARCHAR(255))
RETURNS TABLE (
    token_hash VARCHAR(255),
    token_status VARCHAR(20),
    created_at TIMESTAMP,
    revoked_at TIMESTAMP,
    rotation_count INTEGER,
    parent_token_hash VARCHAR(255)
) AS $$
BEGIN
    -- 주어진 토큰과 관련된 모든 토큰 패밀리 반환
    RETURN QUERY
    WITH RECURSIVE token_family AS (
        -- 시작점: 주어진 토큰
        SELECT rt.token_hash, rt.token_status, rt.created_at, rt.revoked_at, 
               rt.rotation_count, rt.parent_token_hash
        FROM oauth_refresh_tokens rt
        WHERE rt.token_hash = input_token_hash
        
        UNION ALL
        
        -- 자식 토큰들
        SELECT rt.token_hash, rt.token_status, rt.created_at, rt.revoked_at,
               rt.rotation_count, rt.parent_token_hash
        FROM oauth_refresh_tokens rt
        INNER JOIN token_family tf ON rt.parent_token_hash = tf.token_hash
        
        UNION ALL
        
        -- 부모 토큰들
        SELECT rt.token_hash, rt.token_status, rt.created_at, rt.revoked_at,
               rt.rotation_count, rt.parent_token_hash
        FROM oauth_refresh_tokens rt
        INNER JOIN token_family tf ON rt.token_hash = tf.parent_token_hash
    )
    SELECT DISTINCT tf.token_hash, tf.token_status, tf.created_at, 
           tf.revoked_at, tf.rotation_count, tf.parent_token_hash
    FROM token_family tf
    ORDER BY tf.created_at DESC;
END;
$$ LANGUAGE plpgsql;

-- 자동 정리를 위한 예약 작업 (PostgreSQL cron extension 필요 시)
-- SELECT cron.schedule('cleanup-grace-tokens', '*/1 * * * *', 'SELECT cleanup_expired_grace_tokens();');