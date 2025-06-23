-- MySQL Migration: Add Service System for Mother Page
-- Created: 2024-12-19
-- Description: Add service management tables and enhance permission system

-- 1. 서비스 카테고리 테이블 생성
CREATE TABLE service_categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE COMMENT '카테고리명',
    display_name VARCHAR(100) NOT NULL COMMENT '화면에 표시되는 카테고리명',
    description TEXT COMMENT '카테고리 설명',
    sort_order INT DEFAULT 0 COMMENT '정렬 순서',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_category_name (name),
    INDEX idx_category_active (is_active),
    INDEX idx_category_sort (sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='서비스 카테고리 관리';

-- 2. 서비스 테이블 생성
CREATE TABLE services (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE COMMENT '서비스명',
    display_name VARCHAR(100) NOT NULL COMMENT '화면에 표시되는 서비스명',
    description TEXT COMMENT '서비스 설명',
    
    -- 서비스 접근 정보
    url VARCHAR(500) NOT NULL COMMENT '서비스 URL 또는 라우트',
    icon_url VARCHAR(500) COMMENT '서비스 아이콘 URL',
    thumbnail_url VARCHAR(500) COMMENT '서비스 썸네일 이미지 URL',
    
    -- 서비스 상태 및 설정
    is_active BOOLEAN DEFAULT TRUE COMMENT '서비스 활성화 여부',
    is_external BOOLEAN DEFAULT FALSE COMMENT '외부 서비스 여부',
    requires_auth BOOLEAN DEFAULT TRUE COMMENT '인증 필요 여부',
    open_in_new_tab BOOLEAN DEFAULT FALSE COMMENT '새 탭에서 열기 여부',
    
    -- 정렬 및 그룹화
    sort_order INT DEFAULT 0 COMMENT '정렬 순서',
    category VARCHAR(50) COMMENT '서비스 카테고리',
    
    -- 시스템 정보
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by CHAR(36) NOT NULL COMMENT '생성자 UUID',
    
    INDEX idx_service_name (name),
    INDEX idx_service_active (is_active),
    INDEX idx_service_category (category),
    INDEX idx_service_sort (sort_order),
    INDEX idx_service_creator (created_by),
    
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='서비스 정보 관리';

-- 3. 사용자-서비스 다대다 관계 테이블
CREATE TABLE user_services (
    user_id CHAR(36) NOT NULL COMMENT '사용자 UUID',
    service_id INT NOT NULL COMMENT '서비스 ID',
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '권한 부여 시간',
    granted_by CHAR(36) COMMENT '권한 부여자 UUID',
    
    PRIMARY KEY (user_id, service_id),
    INDEX idx_user_services_user (user_id),
    INDEX idx_user_services_service (service_id),
    INDEX idx_user_services_granted_by (granted_by),
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE,
    FOREIGN KEY (granted_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='사용자별 서비스 접근 권한';

-- 4. 역할-서비스 다대다 관계 테이블
CREATE TABLE role_services (
    role_id INT NOT NULL COMMENT '역할 ID',
    service_id INT NOT NULL COMMENT '서비스 ID',
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '권한 부여 시간',
    granted_by CHAR(36) COMMENT '권한 부여자 UUID',
    
    PRIMARY KEY (role_id, service_id),
    INDEX idx_role_services_role (role_id),
    INDEX idx_role_services_service (service_id),
    INDEX idx_role_services_granted_by (granted_by),
    
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE,
    FOREIGN KEY (granted_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='역할별 서비스 접근 권한';

-- 5. 사용자 서비스 권한 상세 테이블
CREATE TABLE user_service_permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id CHAR(36) NOT NULL COMMENT '사용자 UUID',
    service_id INT NOT NULL COMMENT '서비스 ID',
    
    -- 권한 세부사항
    permission_level VARCHAR(20) DEFAULT 'read' COMMENT '권한 레벨: read, write, admin',
    custom_permissions TEXT COMMENT 'JSON 형태의 커스텀 권한',
    
    -- 권한 부여 정보
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '권한 부여 시간',
    granted_by CHAR(36) NOT NULL COMMENT '권한 부여자 UUID',
    expires_at TIMESTAMP NULL COMMENT '권한 만료일',
    
    -- 상태
    is_active BOOLEAN DEFAULT TRUE,
    
    INDEX idx_user_permissions_user (user_id),
    INDEX idx_user_permissions_service (service_id),
    INDEX idx_user_permissions_level (permission_level),
    INDEX idx_user_permissions_active (is_active),
    INDEX idx_user_permissions_expires (expires_at),
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE,
    FOREIGN KEY (granted_by) REFERENCES users(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='사용자별 서비스 권한 상세 관리';

-- 6. 기본 서비스 카테고리 데이터 삽입
INSERT INTO service_categories (name, display_name, description, sort_order) VALUES
('analytics', '데이터 분석', '데이터 분석 관련 서비스', 1),
('development', '개발 도구', '개발 관련 도구 및 서비스', 2),
('management', '관리 도구', '시스템 관리 및 운영 도구', 3),
('collaboration', '협업 도구', '팀 협업 및 커뮤니케이션 도구', 4);

-- 7. 기본 서비스 데이터 삽입 (관리자 계정 필요)
-- 관리자 계정 ID를 변수로 설정 (실제 운영 시 수정 필요)
SET @admin_user_id = (SELECT id FROM users WHERE is_admin = TRUE LIMIT 1);

INSERT INTO services (name, display_name, description, url, category, sort_order, created_by) VALUES
('jupyter_workspace', '쥬피터 워크스페이스', '데이터 분석을 위한 쥬피터 노트북 환경', '/dashboard', 'analytics', 1, @admin_user_id),
('file_manager', '파일 관리자', '워크스페이스 파일 관리 도구', '/files', 'development', 2, @admin_user_id);

-- 8. 기본 역할에 서비스 권한 부여
-- 일반 사용자 역할에 쥬피터 워크스페이스 접근 권한 부여
INSERT INTO role_services (role_id, service_id, granted_by)
SELECT r.id, s.id, @admin_user_id
FROM roles r, services s 
WHERE r.name = 'user' AND s.name = 'jupyter_workspace';

-- 관리자 역할에 모든 서비스 접근 권한 부여
INSERT INTO role_services (role_id, service_id, granted_by)
SELECT r.id, s.id, @admin_user_id
FROM roles r, services s 
WHERE r.name = 'admin';

-- 9. 인덱스 최적화를 위한 추가 인덱스
CREATE INDEX idx_services_active_sort ON services(is_active, sort_order);
CREATE INDEX idx_user_services_composite ON user_services(user_id, service_id);
CREATE INDEX idx_role_services_composite ON role_services(role_id, service_id);

-- 10. 권한 확인을 위한 뷰 생성
CREATE VIEW user_accessible_services AS
SELECT DISTINCT 
    u.id as user_id,
    u.real_name,
    u.display_name,
    s.id as service_id,
    s.name as service_name,
    s.display_name as service_display_name,
    s.description,
    s.url,
    s.icon_url,
    s.thumbnail_url,
    s.is_external,
    s.open_in_new_tab,
    s.category,
    s.sort_order
FROM users u
JOIN roles r ON u.role_id = r.id
JOIN role_services rs ON r.id = rs.role_id
JOIN services s ON rs.service_id = s.id
WHERE u.is_active = TRUE 
  AND r.is_active = TRUE 
  AND s.is_active = TRUE

UNION

SELECT DISTINCT 
    u.id as user_id,
    u.real_name,
    u.display_name,
    s.id as service_id,
    s.name as service_name,
    s.display_name as service_display_name,
    s.description,
    s.url,
    s.icon_url,
    s.thumbnail_url,
    s.is_external,
    s.open_in_new_tab,
    s.category,
    s.sort_order
FROM users u
JOIN user_services us ON u.id = us.user_id
JOIN services s ON us.service_id = s.id
WHERE u.is_active = TRUE 
  AND s.is_active = TRUE;

-- Migration 완료 로그
INSERT INTO migration_logs (version, description, executed_at) VALUES 
('001', 'Add Service System for Mother Page', NOW());

COMMIT; 