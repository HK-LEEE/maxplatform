-- OAuth 2.0 Database Schema for MAX Platform
-- Central Authentication Server Tables

-- OAuth 클라이언트 등록 테이블
CREATE TABLE IF NOT EXISTS oauth_clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id VARCHAR(50) UNIQUE NOT NULL,
    client_secret VARCHAR(255) NOT NULL,
    client_name VARCHAR(100) NOT NULL,
    description TEXT,
    redirect_uris TEXT[] NOT NULL,
    allowed_scopes TEXT[] DEFAULT ARRAY['read:profile', 'read:features'],
    is_confidential BOOLEAN DEFAULT true,
    is_active BOOLEAN DEFAULT true,
    logo_url VARCHAR(255),
    homepage_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- OAuth 인증 코드 테이블 (5분 TTL)
CREATE TABLE IF NOT EXISTS authorization_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(128) UNIQUE NOT NULL,
    client_id VARCHAR(50) NOT NULL REFERENCES oauth_clients(client_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    redirect_uri TEXT NOT NULL,
    scope TEXT,
    code_challenge VARCHAR(128),
    code_challenge_method VARCHAR(10) CHECK (code_challenge_method IN ('S256', 'plain')),
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- OAuth 액세스 토큰 테이블
CREATE TABLE IF NOT EXISTS oauth_access_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    client_id VARCHAR(50) NOT NULL REFERENCES oauth_clients(client_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    scope TEXT,
    expires_at TIMESTAMP NOT NULL,
    revoked_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- OAuth 세션 관리 (사용자가 클라이언트에 부여한 권한 추적)
CREATE TABLE IF NOT EXISTS oauth_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    client_id VARCHAR(50) NOT NULL REFERENCES oauth_clients(client_id) ON DELETE CASCADE,
    granted_scopes TEXT[],
    last_used_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, client_id)
);

-- OAuth 리프레시 토큰 테이블 (RFC 6749 준수)
CREATE TABLE IF NOT EXISTS oauth_refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    client_id VARCHAR(50) NOT NULL REFERENCES oauth_clients(client_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    scope TEXT,
    access_token_hash VARCHAR(255), -- 현재 연결된 액세스 토큰
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    revoked_at TIMESTAMP,
    last_used_at TIMESTAMP,
    -- 보안을 위한 추가 정보
    client_ip INET,
    user_agent TEXT,
    rotation_count INTEGER DEFAULT 0 -- 토큰 회전 횟수 추적
);

-- OAuth 감사 로그 테이블
CREATE TABLE IF NOT EXISTS oauth_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action VARCHAR(50) NOT NULL, -- 'authorize', 'token', 'revoke', 'introspect'
    client_id VARCHAR(50),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    ip_address INET,
    user_agent TEXT,
    success BOOLEAN NOT NULL,
    error_code VARCHAR(50),
    error_description TEXT,
    additional_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_authorization_codes_code ON authorization_codes(code);
CREATE INDEX IF NOT EXISTS idx_authorization_codes_expires_at ON authorization_codes(expires_at);
CREATE INDEX IF NOT EXISTS idx_oauth_access_tokens_token_hash ON oauth_access_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_oauth_access_tokens_expires_at ON oauth_access_tokens(expires_at);
CREATE INDEX IF NOT EXISTS idx_oauth_sessions_user_client ON oauth_sessions(user_id, client_id);
CREATE INDEX IF NOT EXISTS idx_oauth_refresh_tokens_token_hash ON oauth_refresh_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_oauth_refresh_tokens_expires_at ON oauth_refresh_tokens(expires_at);
CREATE INDEX IF NOT EXISTS idx_oauth_refresh_tokens_user_client ON oauth_refresh_tokens(user_id, client_id);
CREATE INDEX IF NOT EXISTS idx_oauth_refresh_tokens_access_token ON oauth_refresh_tokens(access_token_hash);
CREATE INDEX IF NOT EXISTS idx_oauth_audit_logs_created_at ON oauth_audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_oauth_audit_logs_client_id ON oauth_audit_logs(client_id);

-- 만료된 코드 및 토큰 정리를 위한 함수
CREATE OR REPLACE FUNCTION cleanup_expired_oauth_data()
RETURNS void AS $$
BEGIN
    -- 만료된 인증 코드 삭제 (5분 후)
    DELETE FROM authorization_codes 
    WHERE expires_at < NOW() - INTERVAL '5 minutes';
    
    -- 만료된 액세스 토큰 삭제 (1일 후)
    DELETE FROM oauth_access_tokens 
    WHERE expires_at < NOW() - INTERVAL '1 day';
    
    -- 만료된 리프레시 토큰 삭제 (1일 후)
    DELETE FROM oauth_refresh_tokens 
    WHERE expires_at < NOW() - INTERVAL '1 day' 
    OR revoked_at < NOW() - INTERVAL '1 day';
    
    -- 오래된 감사 로그 삭제 (90일 후)
    DELETE FROM oauth_audit_logs 
    WHERE created_at < NOW() - INTERVAL '90 days';
END;
$$ LANGUAGE plpgsql;

-- 정기적인 정리 작업을 위한 트리거 함수
CREATE OR REPLACE FUNCTION trigger_cleanup_oauth_data()
RETURNS trigger AS $$
BEGIN
    PERFORM cleanup_expired_oauth_data();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 사전 등록된 MAX 플랫폼 클라이언트 데이터
INSERT INTO oauth_clients (client_id, client_secret, client_name, description, redirect_uris, allowed_scopes, homepage_url) VALUES
('maxflowstudio', 'secret_flowstudio_2025_dev', 'MAX FlowStudio', '비주얼 워크플로우 디자인 플랫폼', ARRAY['http://localhost:3001/oauth/callback', 'http://localhost:3001/auth/callback'], ARRAY['read:profile', 'read:features', 'read:groups', 'manage:workflows'], 'http://localhost:3001'),

('maxteamsync', 'secret_teamsync_2025_dev', 'MAX TeamSync', '팀 협업 및 동기화 플랫폼', ARRAY['http://localhost:3002/oauth/callback'], ARRAY['read:profile', 'read:features', 'read:groups', 'manage:teams'], 'http://localhost:3002'),

('maxlab', 'secret_lab_2025_dev', 'MAX Lab', '실험 및 연구개발 플랫폼', ARRAY['http://localhost:3003/oauth/callback'], ARRAY['read:profile', 'read:features', 'read:groups', 'manage:experiments'], 'http://localhost:3003'),

('maxworkspace', 'secret_workspace_2025_dev', 'MAX Workspace', '통합 작업공간 플랫폼', ARRAY['http://localhost:3004/oauth/callback'], ARRAY['read:profile', 'read:features', 'read:groups', 'manage:workspaces'], 'http://localhost:3004'),

('maxapa', 'secret_apa_2025_dev', 'MAX APA', 'API 관리 및 자동화 플랫폼', ARRAY['http://localhost:3005/oauth/callback'], ARRAY['read:profile', 'read:features', 'read:groups', 'manage:apis'], 'http://localhost:3005'),

('maxmlops', 'secret_mlops_2025_dev', 'MAX MLOps', '머신러닝 운영 및 배포 플랫폼', ARRAY['http://localhost:3006/oauth/callback'], ARRAY['read:profile', 'read:features', 'read:groups', 'manage:models'], 'http://localhost:3006')

ON CONFLICT (client_id) DO UPDATE SET
    client_name = EXCLUDED.client_name,
    description = EXCLUDED.description,
    redirect_uris = EXCLUDED.redirect_uris,
    allowed_scopes = EXCLUDED.allowed_scopes,
    homepage_url = EXCLUDED.homepage_url,
    updated_at = NOW();

-- Scope 정의 테이블 (참조용)
CREATE TABLE IF NOT EXISTS oauth_scopes (
    scope VARCHAR(50) PRIMARY KEY,
    description TEXT NOT NULL,
    category VARCHAR(30) NOT NULL DEFAULT 'general',
    is_sensitive BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 기본 Scope 정의
INSERT INTO oauth_scopes (scope, description, category, is_sensitive) VALUES
('read:profile', '사용자 프로필 정보 읽기', 'profile', false),
('read:features', '기능 목록 및 권한 정보 읽기', 'features', false),
('read:groups', '그룹 정보 읽기', 'groups', false),
('manage:workflows', '워크플로우 생성, 편집, 삭제', 'workflows', false),
('manage:teams', '팀 관리 및 멤버 관리', 'teams', false),
('manage:experiments', '실험 및 연구 데이터 관리', 'experiments', false),
('manage:workspaces', '작업공간 관리', 'workspaces', false),
('manage:apis', 'API 관리 및 자동화', 'apis', false),
('manage:models', '머신러닝 모델 관리', 'models', false),
('admin:full', '전체 관리자 권한', 'admin', true),
('admin:oauth', 'OAuth 클라이언트 및 토큰 관리', 'admin', true),
('admin:users', '사용자 관리 및 계정 제어', 'admin', true),
('admin:system', '시스템 설정 및 구성 관리', 'admin', true)

ON CONFLICT (scope) DO UPDATE SET
    description = EXCLUDED.description,
    category = EXCLUDED.category,
    is_sensitive = EXCLUDED.is_sensitive;

COMMENT ON TABLE oauth_clients IS 'OAuth 2.0 클라이언트 등록 정보';
COMMENT ON TABLE authorization_codes IS 'OAuth 2.0 인증 코드 (5분 TTL)';
COMMENT ON TABLE oauth_access_tokens IS 'OAuth 2.0 액세스 토큰';
COMMENT ON TABLE oauth_sessions IS 'OAuth 2.0 사용자-클라이언트 세션';
COMMENT ON TABLE oauth_audit_logs IS 'OAuth 2.0 감사 로그';
COMMENT ON TABLE oauth_scopes IS 'OAuth 2.0 스코프 정의';