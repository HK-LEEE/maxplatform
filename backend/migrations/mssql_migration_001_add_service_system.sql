-- MSSQL Migration: Add Service System for Mother Page
-- Created: 2024-12-19
-- Description: Add service management tables and enhance permission system

BEGIN TRANSACTION;

-- 1. 서비스 카테고리 테이블 생성
CREATE TABLE service_categories (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(50) NOT NULL UNIQUE,
    display_name NVARCHAR(100) NOT NULL,
    description NTEXT NULL,
    sort_order INT DEFAULT 0,
    is_active BIT DEFAULT 1,
    created_at DATETIME2 DEFAULT GETDATE()
);

-- 서비스 카테고리 인덱스
CREATE NONCLUSTERED INDEX IX_service_categories_name ON service_categories(name);
CREATE NONCLUSTERED INDEX IX_service_categories_active ON service_categories(is_active);
CREATE NONCLUSTERED INDEX IX_service_categories_sort ON service_categories(sort_order);

-- 2. 서비스 테이블 생성
CREATE TABLE services (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100) NOT NULL UNIQUE,
    display_name NVARCHAR(100) NOT NULL,
    description NTEXT NULL,
    
    -- 서비스 접근 정보
    url NVARCHAR(500) NOT NULL,
    icon_url NVARCHAR(500) NULL,
    thumbnail_url NVARCHAR(500) NULL,
    
    -- 서비스 상태 및 설정
    is_active BIT DEFAULT 1,
    is_external BIT DEFAULT 0,
    requires_auth BIT DEFAULT 1,
    open_in_new_tab BIT DEFAULT 0,
    
    -- 정렬 및 그룹화
    sort_order INT DEFAULT 0,
    category NVARCHAR(50) NULL,
    
    -- 시스템 정보
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE(),
    created_by NCHAR(36) NOT NULL,
    
    CONSTRAINT FK_services_created_by FOREIGN KEY (created_by) REFERENCES users(id)
);

-- 서비스 테이블 인덱스
CREATE NONCLUSTERED INDEX IX_services_name ON services(name);
CREATE NONCLUSTERED INDEX IX_services_active ON services(is_active);
CREATE NONCLUSTERED INDEX IX_services_category ON services(category);
CREATE NONCLUSTERED INDEX IX_services_sort ON services(sort_order);
CREATE NONCLUSTERED INDEX IX_services_creator ON services(created_by);

-- 3. 사용자-서비스 다대다 관계 테이블
CREATE TABLE user_services (
    user_id NCHAR(36) NOT NULL,
    service_id INT NOT NULL,
    granted_at DATETIME2 DEFAULT GETDATE(),
    granted_by NCHAR(36) NULL,
    
    CONSTRAINT PK_user_services PRIMARY KEY (user_id, service_id),
    CONSTRAINT FK_user_services_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT FK_user_services_service FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE,
    CONSTRAINT FK_user_services_granted_by FOREIGN KEY (granted_by) REFERENCES users(id)
);

-- 사용자-서비스 인덱스
CREATE NONCLUSTERED INDEX IX_user_services_user ON user_services(user_id);
CREATE NONCLUSTERED INDEX IX_user_services_service ON user_services(service_id);
CREATE NONCLUSTERED INDEX IX_user_services_granted_by ON user_services(granted_by);

-- 4. 역할-서비스 다대다 관계 테이블
CREATE TABLE role_services (
    role_id INT NOT NULL,
    service_id INT NOT NULL,
    granted_at DATETIME2 DEFAULT GETDATE(),
    granted_by NCHAR(36) NULL,
    
    CONSTRAINT PK_role_services PRIMARY KEY (role_id, service_id),
    CONSTRAINT FK_role_services_role FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    CONSTRAINT FK_role_services_service FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE,
    CONSTRAINT FK_role_services_granted_by FOREIGN KEY (granted_by) REFERENCES users(id)
);

-- 역할-서비스 인덱스
CREATE NONCLUSTERED INDEX IX_role_services_role ON role_services(role_id);
CREATE NONCLUSTERED INDEX IX_role_services_service ON role_services(service_id);
CREATE NONCLUSTERED INDEX IX_role_services_granted_by ON role_services(granted_by);

-- 5. 사용자 서비스 권한 상세 테이블
CREATE TABLE user_service_permissions (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id NCHAR(36) NOT NULL,
    service_id INT NOT NULL,
    
    -- 권한 세부사항
    permission_level NVARCHAR(20) DEFAULT 'read',
    custom_permissions NTEXT NULL,
    
    -- 권한 부여 정보
    granted_at DATETIME2 DEFAULT GETDATE(),
    granted_by NCHAR(36) NOT NULL,
    expires_at DATETIME2 NULL,
    
    -- 상태
    is_active BIT DEFAULT 1,
    
    CONSTRAINT FK_user_service_permissions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT FK_user_service_permissions_service FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE,
    CONSTRAINT FK_user_service_permissions_granted_by FOREIGN KEY (granted_by) REFERENCES users(id)
);

-- 사용자 서비스 권한 인덱스
CREATE NONCLUSTERED INDEX IX_user_permissions_user ON user_service_permissions(user_id);
CREATE NONCLUSTERED INDEX IX_user_permissions_service ON user_service_permissions(service_id);
CREATE NONCLUSTERED INDEX IX_user_permissions_level ON user_service_permissions(permission_level);
CREATE NONCLUSTERED INDEX IX_user_permissions_active ON user_service_permissions(is_active);
CREATE NONCLUSTERED INDEX IX_user_permissions_expires ON user_service_permissions(expires_at);

-- 6. 업데이트 트리거 생성 (updated_at 자동 갱신)
CREATE TRIGGER TR_services_updated_at
    ON services
    AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE services 
    SET updated_at = GETDATE()
    FROM services s
    INNER JOIN inserted i ON s.id = i.id;
END;

-- 7. 기본 서비스 카테고리 데이터 삽입
INSERT INTO service_categories (name, display_name, description, sort_order) VALUES
(N'analytics', N'데이터 분석', N'데이터 분석 관련 서비스', 1),
(N'development', N'개발 도구', N'개발 관련 도구 및 서비스', 2),
(N'management', N'관리 도구', N'시스템 관리 및 운영 도구', 3),
(N'collaboration', N'협업 도구', N'팀 협업 및 커뮤니케이션 도구', 4);

-- 8. 기본 서비스 데이터 삽입 (관리자 계정 필요)
DECLARE @admin_user_id NCHAR(36);
SET @admin_user_id = (SELECT TOP 1 id FROM users WHERE is_admin = 1);

IF @admin_user_id IS NOT NULL
BEGIN
    INSERT INTO services (name, display_name, description, url, category, sort_order, created_by) VALUES
    (N'jupyter_workspace', N'쥬피터 워크스페이스', N'데이터 분석을 위한 쥬피터 노트북 환경', N'/dashboard', N'analytics', 1, @admin_user_id),
    (N'file_manager', N'파일 관리자', N'워크스페이스 파일 관리 도구', N'/files', N'development', 2, @admin_user_id);
    
    -- 기본 역할에 서비스 권한 부여
    -- 일반 사용자 역할에 쥬피터 워크스페이스 접근 권한 부여
    INSERT INTO role_services (role_id, service_id, granted_by)
    SELECT r.id, s.id, @admin_user_id
    FROM roles r
    CROSS JOIN services s 
    WHERE r.name = N'user' AND s.name = N'jupyter_workspace';
    
    -- 관리자 역할에 모든 서비스 접근 권한 부여
    INSERT INTO role_services (role_id, service_id, granted_by)
    SELECT r.id, s.id, @admin_user_id
    FROM roles r
    CROSS JOIN services s 
    WHERE r.name = N'admin';
END;

-- 9. 최적화 인덱스
CREATE NONCLUSTERED INDEX IX_services_active_sort ON services(is_active, sort_order);
CREATE NONCLUSTERED INDEX IX_user_services_composite ON user_services(user_id, service_id);
CREATE NONCLUSTERED INDEX IX_role_services_composite ON role_services(role_id, service_id);

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
INNER JOIN roles r ON u.role_id = r.id
INNER JOIN role_services rs ON r.id = rs.role_id
INNER JOIN services s ON rs.service_id = s.id
WHERE u.is_active = 1 
  AND r.is_active = 1 
  AND s.is_active = 1

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
INNER JOIN user_services us ON u.id = us.user_id
INNER JOIN services s ON us.service_id = s.id
WHERE u.is_active = 1 
  AND s.is_active = 1;

-- 11. 저장 프로시저: 사용자 접근 가능한 서비스 조회
CREATE PROCEDURE sp_GetUserAccessibleServices
    @user_id NCHAR(36)
AS
BEGIN
    SET NOCOUNT ON;
    
    SELECT 
        service_id,
        service_name,
        service_display_name,
        description,
        url,
        icon_url,
        thumbnail_url,
        is_external,
        open_in_new_tab,
        category,
        sort_order
    FROM user_accessible_services
    WHERE user_id = @user_id
    ORDER BY sort_order, service_display_name;
END;

-- 12. 저장 프로시저: 서비스 권한 부여
CREATE PROCEDURE sp_GrantServicePermission
    @user_id NCHAR(36),
    @service_id INT,
    @granted_by NCHAR(36),
    @permission_level NVARCHAR(20) = 'read'
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        BEGIN TRANSACTION;
        
        -- 기존 권한 확인
        IF NOT EXISTS (SELECT 1 FROM user_services WHERE user_id = @user_id AND service_id = @service_id)
        BEGIN
            -- user_services 테이블에 권한 추가
            INSERT INTO user_services (user_id, service_id, granted_by)
            VALUES (@user_id, @service_id, @granted_by);
        END;
        
        -- 상세 권한 추가/업데이트
        IF EXISTS (SELECT 1 FROM user_service_permissions WHERE user_id = @user_id AND service_id = @service_id)
        BEGIN
            UPDATE user_service_permissions 
            SET permission_level = @permission_level,
                granted_at = GETDATE(),
                granted_by = @granted_by,
                is_active = 1
            WHERE user_id = @user_id AND service_id = @service_id;
        END
        ELSE
        BEGIN
            INSERT INTO user_service_permissions (user_id, service_id, permission_level, granted_by)
            VALUES (@user_id, @service_id, @permission_level, @granted_by);
        END;
        
        COMMIT TRANSACTION;
        
        SELECT 'SUCCESS' as result, 'Permission granted successfully' as message;
    END TRY
    BEGIN CATCH
        ROLLBACK TRANSACTION;
        SELECT 'ERROR' as result, ERROR_MESSAGE() as message;
    END CATCH;
END;

COMMIT TRANSACTION;

PRINT 'Service System Migration completed successfully.'; 