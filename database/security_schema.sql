-- Security Events Database Schema
-- 보안 이벤트 로깅 및 모니터링을 위한 데이터베이스 스키마

-- ============================================================================
-- 1. 보안 이벤트 메인 테이블
-- ============================================================================

CREATE TABLE IF NOT EXISTS security_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 기본 이벤트 정보
    event_id VARCHAR(100) NOT NULL UNIQUE,          -- 클라이언트에서 생성한 고유 ID
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,    -- 이벤트 발생 시간
    event_type VARCHAR(50) NOT NULL,                 -- 이벤트 유형 (예: auth_login_failed)
    severity VARCHAR(20) NOT NULL,                   -- 심각도 (low/medium/high/critical)
    
    -- 사용자 및 세션 정보
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    session_id VARCHAR(100),                         -- 세션 ID
    username VARCHAR(100),                           -- 로그인 시도한 사용자명 (실패 시에도 기록)
    
    -- 네트워크 및 클라이언트 정보
    ip_address INET,                                 -- 클라이언트 IP 주소
    user_agent TEXT,                                 -- 브라우저 User-Agent
    url TEXT,                                        -- 이벤트 발생 URL
    referrer TEXT,                                   -- 이전 페이지 URL
    browser_fingerprint VARCHAR(255),               -- 브라우저 지문
    
    -- 상세 정보 (JSON 형태)
    details JSONB,                                   -- 이벤트별 상세 정보
    
    -- 처리 상태
    processed BOOLEAN DEFAULT FALSE,                 -- 처리 완료 여부
    processed_at TIMESTAMP,                          -- 처리 완료 시간
    
    -- 메타데이터
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- 2. 보안 위협 탐지 규칙 테이블
-- ============================================================================

CREATE TABLE IF NOT EXISTS security_threat_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 규칙 정보
    rule_name VARCHAR(100) NOT NULL UNIQUE,          -- 규칙 이름
    rule_type VARCHAR(50) NOT NULL,                  -- 규칙 유형 (brute_force, anomaly, etc.)
    description TEXT,                                -- 규칙 설명
    
    -- 규칙 조건 (JSON)
    conditions JSONB NOT NULL,                       -- 탐지 조건
    threshold_count INTEGER DEFAULT 5,               -- 임계값 (횟수)
    threshold_window INTEGER DEFAULT 300,            -- 시간 창 (초)
    
    -- 대응 액션
    action_type VARCHAR(50) NOT NULL,                -- 대응 유형 (alert, block, lockout)
    action_config JSONB,                             -- 대응 설정
    
    -- 상태
    is_active BOOLEAN DEFAULT TRUE,
    severity VARCHAR(20) DEFAULT 'medium',
    
    -- 메타데이터
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL
);

-- ============================================================================
-- 3. 보안 알림 테이블
-- ============================================================================

CREATE TABLE IF NOT EXISTS security_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 알림 정보
    alert_type VARCHAR(50) NOT NULL,                 -- 알림 유형
    title VARCHAR(200) NOT NULL,                     -- 알림 제목
    message TEXT NOT NULL,                           -- 알림 메시지
    severity VARCHAR(20) NOT NULL,                   -- 심각도
    
    -- 연관 정보
    rule_id UUID REFERENCES security_threat_rules(id) ON DELETE SET NULL,
    event_ids JSONB,                                 -- 관련 이벤트 ID들
    affected_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    source_ip INET,                                  -- 발생 IP
    
    -- 상태
    status VARCHAR(20) DEFAULT 'new',                -- new, investigating, resolved, false_positive
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by UUID REFERENCES users(id) ON DELETE SET NULL,
    acknowledged_at TIMESTAMP,
    
    -- 해결 정보
    resolution TEXT,                                 -- 해결 방법
    resolved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    resolved_at TIMESTAMP,
    
    -- 메타데이터
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- 4. IP 차단 목록 테이블
-- ============================================================================

CREATE TABLE IF NOT EXISTS security_blocked_ips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- IP 정보
    ip_address INET NOT NULL UNIQUE,                 -- 차단된 IP 주소
    ip_range CIDR,                                   -- IP 대역 (선택사항)
    
    -- 차단 정보
    block_reason VARCHAR(100) NOT NULL,              -- 차단 사유
    block_type VARCHAR(20) NOT NULL,                 -- 차단 유형 (temporary, permanent)
    severity VARCHAR(20) NOT NULL,                   -- 심각도
    
    -- 관련 정보
    related_event_ids JSONB,                         -- 관련 보안 이벤트 ID들
    related_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- 시간 정보
    blocked_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,                            -- 임시 차단 만료 시간
    last_attempt_at TIMESTAMP,                       -- 마지막 시도 시간
    attempt_count INTEGER DEFAULT 0,                 -- 차단 후 시도 횟수
    
    -- 상태
    is_active BOOLEAN DEFAULT TRUE,
    
    -- 메타데이터
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- 5. 보안 통계 집계 테이블 (성능 최적화용)
-- ============================================================================

CREATE TABLE IF NOT EXISTS security_statistics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 집계 정보
    date_hour TIMESTAMP NOT NULL,                    -- 시간별 집계 (YYYY-MM-DD HH:00:00)
    event_type VARCHAR(50) NOT NULL,                 -- 이벤트 유형
    severity VARCHAR(20) NOT NULL,                   -- 심각도
    
    -- 통계 데이터
    event_count INTEGER DEFAULT 0,                   -- 이벤트 발생 횟수
    unique_users INTEGER DEFAULT 0,                  -- 고유 사용자 수
    unique_ips INTEGER DEFAULT 0,                    -- 고유 IP 수
    
    -- 메타데이터
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- 복합 기본키로 중복 방지
    UNIQUE(date_hour, event_type, severity)
);

-- ============================================================================
-- 인덱스 생성
-- ============================================================================

-- security_events 테이블 인덱스
CREATE INDEX IF NOT EXISTS idx_security_events_timestamp ON security_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_security_events_event_type ON security_events(event_type);
CREATE INDEX IF NOT EXISTS idx_security_events_severity ON security_events(severity);
CREATE INDEX IF NOT EXISTS idx_security_events_user_id ON security_events(user_id);
CREATE INDEX IF NOT EXISTS idx_security_events_session_id ON security_events(session_id);
CREATE INDEX IF NOT EXISTS idx_security_events_ip_address ON security_events(ip_address);
CREATE INDEX IF NOT EXISTS idx_security_events_processed ON security_events(processed, timestamp);
CREATE INDEX IF NOT EXISTS idx_security_events_event_id ON security_events(event_id);

-- 복합 인덱스 (실시간 위협 탐지용)
CREATE INDEX IF NOT EXISTS idx_security_events_type_time ON security_events(event_type, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_security_events_ip_time ON security_events(ip_address, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_security_events_user_time ON security_events(user_id, timestamp DESC) WHERE user_id IS NOT NULL;

-- GIN 인덱스 (JSON 검색용)
CREATE INDEX IF NOT EXISTS idx_security_events_details_gin ON security_events USING GIN(details);

-- security_alerts 테이블 인덱스
CREATE INDEX IF NOT EXISTS idx_security_alerts_severity ON security_alerts(severity, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_security_alerts_status ON security_alerts(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_security_alerts_user ON security_alerts(affected_user_id);
CREATE INDEX IF NOT EXISTS idx_security_alerts_ip ON security_alerts(source_ip);

-- security_blocked_ips 테이블 인덱스
CREATE INDEX IF NOT EXISTS idx_security_blocked_ips_ip ON security_blocked_ips(ip_address);
CREATE INDEX IF NOT EXISTS idx_security_blocked_ips_active ON security_blocked_ips(is_active, expires_at);
CREATE INDEX IF NOT EXISTS idx_security_blocked_ips_expires ON security_blocked_ips(expires_at) WHERE expires_at IS NOT NULL;

-- security_statistics 테이블 인덱스
CREATE INDEX IF NOT EXISTS idx_security_statistics_date_hour ON security_statistics(date_hour DESC);
CREATE INDEX IF NOT EXISTS idx_security_statistics_type ON security_statistics(event_type, date_hour DESC);

-- ============================================================================
-- 기본 보안 위협 탐지 규칙 삽입
-- ============================================================================

INSERT INTO security_threat_rules (rule_name, rule_type, description, conditions, threshold_count, threshold_window, action_type, action_config, severity) VALUES
-- 브루트 포스 공격 탐지
('Brute Force Login Attempts', 'brute_force', '단시간 내 반복적인 로그인 실패 시도 탐지', 
 '{"event_types": ["auth_login_failed"], "same_ip": true}', 5, 300, 'block', 
 '{"block_duration": 3600, "alert_admins": true}', 'high'),

-- 계정 탈취 시도 탐지  
('Account Takeover Attempt', 'anomaly', '동일 계정으로 다른 IP에서 동시 로그인 시도', 
 '{"event_types": ["auth_login_success"], "different_ips": true, "same_user": true}', 2, 60, 'alert', 
 '{"alert_admins": true, "require_2fa": true}', 'critical'),

-- 토큰 도용 탐지
('Token Theft Detection', 'anomaly', '동일 토큰으로 다른 지역/디바이스에서 접근', 
 '{"event_types": ["token_used"], "location_anomaly": true}', 1, 300, 'alert', 
 '{"alert_admins": true, "invalidate_tokens": true}', 'high'),

-- 비정상적인 API 호출 패턴
('Abnormal API Usage', 'rate_limit', '단시간 내 비정상적으로 많은 API 호출', 
 '{"event_types": ["api_call"], "high_frequency": true}', 100, 60, 'throttle', 
 '{"rate_limit": "10/minute"}', 'medium'),

-- 권한 상승 시도
('Privilege Escalation Attempt', 'authorization', '권한 없는 리소스 접근 시도', 
 '{"event_types": ["auth_access_denied"], "admin_resources": true}', 3, 300, 'alert', 
 '{"alert_admins": true, "log_details": true}', 'high')

ON CONFLICT (rule_name) DO NOTHING;

-- ============================================================================
-- 자동 정리 함수 및 트리거
-- ============================================================================

-- 오래된 보안 이벤트 정리 함수 (90일 이상)
CREATE OR REPLACE FUNCTION cleanup_old_security_events()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- 90일 이상된 LOW 심각도 이벤트 삭제
    DELETE FROM security_events 
    WHERE created_at < NOW() - INTERVAL '90 days' 
    AND severity = 'low';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- 1년 이상된 MEDIUM 심각도 이벤트 삭제
    DELETE FROM security_events 
    WHERE created_at < NOW() - INTERVAL '1 year' 
    AND severity = 'medium';
    
    GET DIAGNOSTICS deleted_count = deleted_count + ROW_COUNT;
    
    -- 해결된 알림 정리 (30일 이상)
    DELETE FROM security_alerts 
    WHERE status = 'resolved' 
    AND resolved_at < NOW() - INTERVAL '30 days';
    
    GET DIAGNOSTICS deleted_count = deleted_count + ROW_COUNT;
    
    -- 만료된 IP 차단 해제
    UPDATE security_blocked_ips 
    SET is_active = FALSE 
    WHERE expires_at < NOW() AND is_active = TRUE;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- 통계 집계 함수
CREATE OR REPLACE FUNCTION aggregate_security_statistics()
RETURNS VOID AS $$
BEGIN
    -- 시간별 통계 집계 (마지막 2시간)
    INSERT INTO security_statistics (date_hour, event_type, severity, event_count, unique_users, unique_ips)
    SELECT 
        date_trunc('hour', timestamp) as date_hour,
        event_type,
        severity,
        COUNT(*) as event_count,
        COUNT(DISTINCT user_id) as unique_users,
        COUNT(DISTINCT ip_address) as unique_ips
    FROM security_events 
    WHERE timestamp >= NOW() - INTERVAL '2 hours'
    AND timestamp < date_trunc('hour', NOW())
    GROUP BY date_trunc('hour', timestamp), event_type, severity
    ON CONFLICT (date_hour, event_type, severity) 
    DO UPDATE SET 
        event_count = EXCLUDED.event_count,
        unique_users = EXCLUDED.unique_users,
        unique_ips = EXCLUDED.unique_ips,
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 스케줄링 (pg_cron 확장이 설치된 경우)
-- ============================================================================

-- 매일 자정에 오래된 데이터 정리
-- SELECT cron.schedule('security-cleanup', '0 0 * * *', 'SELECT cleanup_old_security_events();');

-- 매 시간마다 통계 집계
-- SELECT cron.schedule('security-stats', '0 * * * *', 'SELECT aggregate_security_statistics();');

-- ============================================================================
-- 코멘트 추가
-- ============================================================================

COMMENT ON TABLE security_events IS '보안 이벤트 로그 테이블';
COMMENT ON TABLE security_threat_rules IS '보안 위협 탐지 규칙 테이블';
COMMENT ON TABLE security_alerts IS '보안 알림 테이블';
COMMENT ON TABLE security_blocked_ips IS 'IP 차단 목록 테이블';
COMMENT ON TABLE security_statistics IS '보안 통계 집계 테이블';

COMMENT ON COLUMN security_events.event_id IS '클라이언트에서 생성한 고유 이벤트 ID';
COMMENT ON COLUMN security_events.details IS '이벤트별 상세 정보 (JSON 형태)';
COMMENT ON COLUMN security_events.browser_fingerprint IS '브라우저 지문 (보안 분석용)';

COMMENT ON COLUMN security_threat_rules.conditions IS '위협 탐지 조건 (JSON 형태)';
COMMENT ON COLUMN security_threat_rules.threshold_window IS '탐지 시간 창 (초 단위)';

COMMENT ON COLUMN security_blocked_ips.ip_range IS 'CIDR 표기법을 사용한 IP 대역';
COMMENT ON COLUMN security_blocked_ips.block_type IS 'temporary: 임시 차단, permanent: 영구 차단';