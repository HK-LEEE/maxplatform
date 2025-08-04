-- OIDC Single Logout을 위한 OAuth Client redirect_uris 업데이트
-- post_logout_redirect_uri로 사용할 URL 추가

-- MAX Platform 메인 애플리케이션의 로그아웃 리다이렉트 URI 추가
UPDATE oauth_clients 
SET redirect_uris = array_append(redirect_uris, 'http://localhost:3000/login')
WHERE client_id = 'maxplatform' 
AND NOT ('http://localhost:3000/login' = ANY(redirect_uris));

-- 각 OAuth 클라이언트별 로그아웃 리다이렉트 URI 추가
-- FlowStudio
UPDATE oauth_clients 
SET redirect_uris = array_append(redirect_uris, 'http://localhost:3005/login')
WHERE client_id = 'maxflowstudio' 
AND NOT ('http://localhost:3005/login' = ANY(redirect_uris));

-- Lab
UPDATE oauth_clients 
SET redirect_uris = array_append(redirect_uris, 'http://localhost:3010/login')
WHERE client_id = 'maxlab' 
AND NOT ('http://localhost:3010/login' = ANY(redirect_uris));

-- TeamSync
UPDATE oauth_clients 
SET redirect_uris = array_append(redirect_uris, 'http://localhost:3015/login')
WHERE client_id = 'maxteamsync' 
AND NOT ('http://localhost:3015/login' = ANY(redirect_uris));

-- Workspace
UPDATE oauth_clients 
SET redirect_uris = array_append(redirect_uris, 'http://localhost:3020/login')
WHERE client_id = 'maxworkspace' 
AND NOT ('http://localhost:3020/login' = ANY(redirect_uris));

-- QueryHub
UPDATE oauth_clients 
SET redirect_uris = array_append(redirect_uris, 'http://localhost:3025/login')
WHERE client_id = 'maxqueryhub' 
AND NOT ('http://localhost:3025/login' = ANY(redirect_uris));

-- LLM
UPDATE oauth_clients 
SET redirect_uris = array_append(redirect_uris, 'http://localhost:3030/login')
WHERE client_id = 'maxllm' 
AND NOT ('http://localhost:3030/login' = ANY(redirect_uris));

-- APA
UPDATE oauth_clients 
SET redirect_uris = array_append(redirect_uris, 'http://localhost:3035/login')
WHERE client_id = 'maxapa' 
AND NOT ('http://localhost:3035/login' = ANY(redirect_uris));

-- MLOps
UPDATE oauth_clients 
SET redirect_uris = array_append(redirect_uris, 'http://localhost:3040/login')
WHERE client_id = 'maxmlops' 
AND NOT ('http://localhost:3040/login' = ANY(redirect_uris));

-- Production 환경을 위한 설정 (필요시 주석 해제)
/*
-- Production URLs
UPDATE oauth_clients 
SET redirect_uris = array_append(redirect_uris, 'https://maxplatform.com/login')
WHERE client_id = 'maxplatform' 
AND NOT ('https://maxplatform.com/login' = ANY(redirect_uris));

UPDATE oauth_clients 
SET redirect_uris = array_append(redirect_uris, 'https://flowstudio.maxplatform.com/login')
WHERE client_id = 'maxflowstudio' 
AND NOT ('https://flowstudio.maxplatform.com/login' = ANY(redirect_uris));

-- 다른 production URLs도 동일하게 추가...
*/

-- 확인용 쿼리
SELECT client_id, client_name, redirect_uris 
FROM oauth_clients 
ORDER BY client_id;