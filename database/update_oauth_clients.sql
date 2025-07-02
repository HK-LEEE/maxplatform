-- OAuth 2.0 클라이언트 포트 업데이트 및 신규 클라이언트 추가
-- MAX Platform OAuth Clients Port Update

-- 기존 클라이언트 업데이트
UPDATE oauth_clients SET
    redirect_uris = ARRAY['http://localhost:3005/oauth/callback', 'http://localhost:3005/auth/callback'],
    homepage_url = 'http://localhost:3005',
    updated_at = NOW()
WHERE client_id = 'maxflowstudio';

UPDATE oauth_clients SET
    redirect_uris = ARRAY['http://localhost:3010/oauth/callback', 'http://localhost:3010/auth/callback'],
    homepage_url = 'http://localhost:3010',
    updated_at = NOW()
WHERE client_id = 'maxlab';

UPDATE oauth_clients SET
    redirect_uris = ARRAY['http://localhost:3015/oauth/callback', 'http://localhost:3015/auth/callback'],
    homepage_url = 'http://localhost:3015',
    updated_at = NOW()
WHERE client_id = 'maxteamsync';

UPDATE oauth_clients SET
    redirect_uris = ARRAY['http://localhost:3020/oauth/callback', 'http://localhost:3020/auth/callback'],
    homepage_url = 'http://localhost:3020',
    updated_at = NOW()
WHERE client_id = 'maxworkspace';

UPDATE oauth_clients SET
    redirect_uris = ARRAY['http://localhost:3035/oauth/callback', 'http://localhost:3035/auth/callback'],
    homepage_url = 'http://localhost:3035',
    updated_at = NOW()
WHERE client_id = 'maxapa';

UPDATE oauth_clients SET
    redirect_uris = ARRAY['http://localhost:3040/oauth/callback', 'http://localhost:3040/auth/callback'],
    homepage_url = 'http://localhost:3040',
    updated_at = NOW()
WHERE client_id = 'maxmlops';

-- 신규 클라이언트 추가
INSERT INTO oauth_clients (client_id, client_secret, client_name, description, redirect_uris, allowed_scopes, homepage_url)
VALUES
('maxqueryhub', 'secret_queryhub_2025_dev', 'MAX QueryHub', '쿼리 관리 및 분석 플랫폼', 
 ARRAY['http://localhost:3025/oauth/callback', 'http://localhost:3025/auth/callback'], 
 ARRAY['read:profile', 'read:features', 'read:groups', 'manage:queries'], 
 'http://localhost:3025'),

('maxllm', 'secret_llm_2025_dev', 'MAX LLM', 'LLM 관리 및 운영 플랫폼', 
 ARRAY['http://localhost:3030/oauth/callback', 'http://localhost:3030/auth/callback'], 
 ARRAY['read:profile', 'read:features', 'read:groups', 'manage:llm'], 
 'http://localhost:3030')

ON CONFLICT (client_id) DO UPDATE SET
    client_name = EXCLUDED.client_name,
    description = EXCLUDED.description,
    redirect_uris = EXCLUDED.redirect_uris,
    allowed_scopes = EXCLUDED.allowed_scopes,
    homepage_url = EXCLUDED.homepage_url,
    updated_at = NOW();

-- 신규 스코프 추가
INSERT INTO oauth_scopes (scope, description, category, is_sensitive) 
VALUES
('manage:queries', '쿼리 생성, 편집, 실행 및 분석', 'queries', false),
('manage:llm', 'LLM 모델 관리 및 설정', 'llm', false)

ON CONFLICT (scope) DO UPDATE SET
    description = EXCLUDED.description,
    category = EXCLUDED.category,
    is_sensitive = EXCLUDED.is_sensitive;

-- 업데이트 확인
SELECT client_id, client_name, homepage_url, array_to_string(redirect_uris, ', ') as redirect_uris
FROM oauth_clients
ORDER BY client_id;