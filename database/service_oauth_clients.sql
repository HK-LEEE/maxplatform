-- MAX Platform Service OAuth Clients
-- 서비스 간 통신용 OAuth 클라이언트 등록

-- 서비스 전용 클라이언트 등록 (redirect_uris가 빈 배열인 것이 특징)
INSERT INTO oauth_clients (client_id, client_secret, client_name, description, redirect_uris, allowed_scopes, is_confidential, is_active) VALUES

-- MAX Platform 내부 서비스 토큰
('maxplatform-service', 'service_maxplatform_2025_dev_secret', 'MAX Platform Service Token', 
 'MAX Platform 내부 서비스 간 통신용 토큰', 
 ARRAY[]::TEXT[], -- 빈 배열로 서비스 클라이언트임을 표시
 ARRAY['admin:oauth', 'admin:users', 'admin:system', 'admin:full'], 
 true, true),

-- API Gateway 서비스
('maxapi-gateway', 'service_gateway_2025_dev_secret', 'MAX API Gateway Service', 
 'API Gateway 서비스 인증용', 
 ARRAY[]::TEXT[], 
 ARRAY['admin:oauth', 'admin:users', 'admin:system'], 
 true, true),

-- 모니터링 서비스
('maxmonitoring-service', 'service_monitoring_2025_dev_secret', 'MAX Monitoring Service', 
 '시스템 모니터링 및 헬스체크 서비스', 
 ARRAY[]::TEXT[], 
 ARRAY['admin:system', 'read:features'], 
 true, true),

-- 백업 서비스
('maxbackup-service', 'service_backup_2025_dev_secret', 'MAX Backup Service', 
 '데이터 백업 및 복구 서비스', 
 ARRAY[]::TEXT[], 
 ARRAY['admin:system', 'admin:users'], 
 true, true),

-- 알림 서비스
('maxnotification-service', 'service_notification_2025_dev_secret', 'MAX Notification Service', 
 '통합 알림 및 메시징 서비스', 
 ARRAY[]::TEXT[], 
 ARRAY['admin:users', 'read:profile'], 
 true, true)

ON CONFLICT (client_id) DO UPDATE SET
    client_name = EXCLUDED.client_name,
    description = EXCLUDED.description,
    redirect_uris = EXCLUDED.redirect_uris,
    allowed_scopes = EXCLUDED.allowed_scopes,
    is_confidential = EXCLUDED.is_confidential,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();

-- 서비스 클라이언트 확인
SELECT 
    client_id, 
    client_name, 
    description,
    CASE 
        WHEN array_length(redirect_uris, 1) IS NULL OR array_length(redirect_uris, 1) = 0 
        THEN '서비스 클라이언트' 
        ELSE '웹 클라이언트' 
    END as client_type,
    array_to_string(allowed_scopes, ', ') as allowed_scopes,
    is_confidential,
    is_active
FROM oauth_clients 
WHERE client_id LIKE '%service%' OR array_length(redirect_uris, 1) IS NULL OR array_length(redirect_uris, 1) = 0
ORDER BY client_id;