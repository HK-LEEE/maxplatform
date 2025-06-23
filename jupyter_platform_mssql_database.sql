-- =============================================
-- Jupyter Data Platform - SQL Server Database Script
-- DDL (Data Definition Language) + DML (Data Manipulation Language)
-- =============================================

-- 데이터베이스 생성 (필요한 경우)
-- CREATE DATABASE jupyter_platform;
-- USE jupyter_platform;

-- =============================================
-- TABLE CREATION (DDL)
-- =============================================

-- 1. 역할(Roles) 테이블
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='roles' AND xtype='U')
CREATE TABLE roles (
    id int IDENTITY(1,1) PRIMARY KEY,
    name nvarchar(50) NOT NULL UNIQUE,
    description ntext NULL,
    is_active bit NOT NULL DEFAULT 1,
    created_at datetime2 NOT NULL DEFAULT GETDATE()
);

-- 2. 그룹(Groups) 테이블 - 사용자 테이블보다 먼저 생성
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='groups' AND xtype='U')
CREATE TABLE groups (
    id int IDENTITY(1,1) PRIMARY KEY,
    name nvarchar(100) NOT NULL UNIQUE,
    description ntext NULL,
    is_active bit NOT NULL DEFAULT 1,
    created_at datetime2 NOT NULL DEFAULT GETDATE(),
    created_by char(36) NULL -- 나중에 FK 추가
);

-- 3. 사용자(Users) 테이블
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='users' AND xtype='U')
CREATE TABLE users (
    id char(36) PRIMARY KEY DEFAULT NEWID(),
    real_name nvarchar(100) NOT NULL,
    display_name nvarchar(50) NULL,
    email nvarchar(100) NOT NULL UNIQUE,
    phone_number nvarchar(20) NULL,
    hashed_password nvarchar(255) NOT NULL,
    is_active bit NOT NULL DEFAULT 1,
    is_admin bit NOT NULL DEFAULT 0,
    is_verified bit NOT NULL DEFAULT 0,
    approval_status nvarchar(20) NOT NULL DEFAULT 'pending',
    approval_note ntext NULL,
    approved_by char(36) NULL,
    approved_at datetime2 NULL,
    role_id int NULL,
    group_id int NULL,
    department nvarchar(100) NULL,
    position nvarchar(100) NULL,
    bio ntext NULL,
    created_at datetime2 NOT NULL DEFAULT GETDATE(),
    updated_at datetime2 NOT NULL DEFAULT GETDATE(),
    last_login_at datetime2 NULL,
    login_count int NOT NULL DEFAULT 0,
    
    -- Foreign Key 제약조건
    CONSTRAINT FK_users_role FOREIGN KEY (role_id) REFERENCES roles(id),
    CONSTRAINT FK_users_group FOREIGN KEY (group_id) REFERENCES groups(id),
    CONSTRAINT FK_users_approved_by FOREIGN KEY (approved_by) REFERENCES users(id)
);

-- groups 테이블에 FK 추가
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_groups_created_by')
ALTER TABLE groups ADD CONSTRAINT FK_groups_created_by FOREIGN KEY (created_by) REFERENCES users(id);

-- 4. 워크스페이스(Workspaces) 테이블
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='workspaces' AND xtype='U')
CREATE TABLE workspaces (
    id int IDENTITY(1,1) PRIMARY KEY,
    name nvarchar(100) NOT NULL,
    description ntext NULL,
    owner_id char(36) NOT NULL,
    is_active bit NOT NULL DEFAULT 1,
    is_public bit NOT NULL DEFAULT 0,
    jupyter_port int NULL,
    jupyter_token nvarchar(255) NULL,
    jupyter_status nvarchar(20) NOT NULL DEFAULT 'stopped',
    path nvarchar(500) NULL,
    max_storage_mb int NOT NULL DEFAULT 1000,
    created_at datetime2 NOT NULL DEFAULT GETDATE(),
    updated_at datetime2 NOT NULL DEFAULT GETDATE(),
    last_accessed datetime2 NULL,
    
    -- Foreign Key 제약조건
    CONSTRAINT FK_workspaces_owner FOREIGN KEY (owner_id) REFERENCES users(id)
);

-- 5. 권한(Permissions) 테이블
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='permissions' AND xtype='U')
CREATE TABLE permissions (
    id int IDENTITY(1,1) PRIMARY KEY,
    name nvarchar(100) NOT NULL UNIQUE,
    display_name nvarchar(200) NOT NULL,
    description ntext NULL,
    category nvarchar(50) NOT NULL,
    is_active bit NOT NULL DEFAULT 1
);

-- 6. 기능(Features) 테이블
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='features' AND xtype='U')
CREATE TABLE features (
    id int IDENTITY(1,1) PRIMARY KEY,
    name nvarchar(100) NOT NULL UNIQUE,
    display_name nvarchar(200) NOT NULL,
    description ntext NULL,
    category nvarchar(50) NOT NULL,
    icon nvarchar(50) NULL,
    url_path nvarchar(200) NULL,
    is_external bit NOT NULL DEFAULT 0,
    open_in_new_tab bit NOT NULL DEFAULT 0,
    auto_grant bit NOT NULL DEFAULT 0,
    requires_approval bit NOT NULL DEFAULT 1,
    is_active bit NOT NULL DEFAULT 1
);

-- 7. 서비스(Services) 테이블
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='services' AND xtype='U')
CREATE TABLE services (
    id int IDENTITY(1,1) PRIMARY KEY,
    name nvarchar(100) NOT NULL UNIQUE,
    display_name nvarchar(100) NOT NULL,
    description ntext NULL,
    url nvarchar(500) NOT NULL,
    icon_url nvarchar(500) NULL,
    thumbnail_url nvarchar(500) NULL,
    is_active bit NOT NULL DEFAULT 1,
    is_external bit NOT NULL DEFAULT 0,
    requires_auth bit NOT NULL DEFAULT 1,
    open_in_new_tab bit NOT NULL DEFAULT 0,
    sort_order int NOT NULL DEFAULT 0,
    category nvarchar(50) NULL,
    created_at datetime2 NOT NULL DEFAULT GETDATE(),
    updated_at datetime2 NOT NULL DEFAULT GETDATE(),
    created_by char(36) NOT NULL,
    
    -- Foreign Key 제약조건
    CONSTRAINT FK_services_created_by FOREIGN KEY (created_by) REFERENCES users(id)
);

-- 8. 서비스 카테고리(Service Categories) 테이블
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='service_categories' AND xtype='U')
CREATE TABLE service_categories (
    id int IDENTITY(1,1) PRIMARY KEY,
    name nvarchar(50) NOT NULL UNIQUE,
    display_name nvarchar(100) NOT NULL,
    description ntext NULL,
    sort_order int NOT NULL DEFAULT 0,
    is_active bit NOT NULL DEFAULT 1,
    created_at datetime2 NOT NULL DEFAULT GETDATE()
);

-- =============================================
-- ASSOCIATION TABLES (Many-to-Many relationships)
-- =============================================

-- 9. 사용자-권한 연결 테이블
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='user_permissions' AND xtype='U')
CREATE TABLE user_permissions (
    user_id char(36) NOT NULL,
    permission_id int NOT NULL,
    PRIMARY KEY (user_id, permission_id),
    
    CONSTRAINT FK_user_permissions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT FK_user_permissions_permission FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
);

-- 10. 사용자-기능 연결 테이블
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='user_features' AND xtype='U')
CREATE TABLE user_features (
    user_id char(36) NOT NULL,
    feature_id int NOT NULL,
    PRIMARY KEY (user_id, feature_id),
    
    CONSTRAINT FK_user_features_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT FK_user_features_feature FOREIGN KEY (feature_id) REFERENCES features(id) ON DELETE CASCADE
);

-- 11. 역할-권한 연결 테이블
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='role_permissions' AND xtype='U')
CREATE TABLE role_permissions (
    role_id int NOT NULL,
    permission_id int NOT NULL,
    PRIMARY KEY (role_id, permission_id),
    
    CONSTRAINT FK_role_permissions_role FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    CONSTRAINT FK_role_permissions_permission FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
);

-- 12. 역할-기능 연결 테이블
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='role_features' AND xtype='U')
CREATE TABLE role_features (
    role_id int NOT NULL,
    feature_id int NOT NULL,
    PRIMARY KEY (role_id, feature_id),
    
    CONSTRAINT FK_role_features_role FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    CONSTRAINT FK_role_features_feature FOREIGN KEY (feature_id) REFERENCES features(id) ON DELETE CASCADE
);

-- 13. 그룹-권한 연결 테이블
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='group_permissions' AND xtype='U')
CREATE TABLE group_permissions (
    group_id int NOT NULL,
    permission_id int NOT NULL,
    PRIMARY KEY (group_id, permission_id),
    
    CONSTRAINT FK_group_permissions_group FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
    CONSTRAINT FK_group_permissions_permission FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
);

-- 14. 그룹-기능 연결 테이블
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='group_features' AND xtype='U')
CREATE TABLE group_features (
    group_id int NOT NULL,
    feature_id int NOT NULL,
    PRIMARY KEY (group_id, feature_id),
    
    CONSTRAINT FK_group_features_group FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
    CONSTRAINT FK_group_features_feature FOREIGN KEY (feature_id) REFERENCES features(id) ON DELETE CASCADE
);

-- 15. 사용자-서비스 연결 테이블
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='user_services' AND xtype='U')
CREATE TABLE user_services (
    user_id char(36) NOT NULL,
    service_id int NOT NULL,
    granted_at datetime2 NOT NULL DEFAULT GETDATE(),
    granted_by char(36) NULL,
    PRIMARY KEY (user_id, service_id),
    
    CONSTRAINT FK_user_services_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT FK_user_services_service FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE,
    CONSTRAINT FK_user_services_granted_by FOREIGN KEY (granted_by) REFERENCES users(id)
);

-- 16. 역할-서비스 연결 테이블
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='role_services' AND xtype='U')
CREATE TABLE role_services (
    role_id int NOT NULL,
    service_id int NOT NULL,
    granted_at datetime2 NOT NULL DEFAULT GETDATE(),
    granted_by char(36) NULL,
    PRIMARY KEY (role_id, service_id),
    
    CONSTRAINT FK_role_services_role FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    CONSTRAINT FK_role_services_service FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE,
    CONSTRAINT FK_role_services_granted_by FOREIGN KEY (granted_by) REFERENCES users(id)
);

-- 17. 사용자 서비스 권한 상세 테이블
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='user_service_permissions' AND xtype='U')
CREATE TABLE user_service_permissions (
    id int IDENTITY(1,1) PRIMARY KEY,
    user_id char(36) NOT NULL,
    service_id int NOT NULL,
    permission_level nvarchar(20) NOT NULL DEFAULT 'read',
    custom_permissions ntext NULL,
    granted_at datetime2 NOT NULL DEFAULT GETDATE(),
    granted_by char(36) NOT NULL,
    expires_at datetime2 NULL,
    is_active bit NOT NULL DEFAULT 1,
    
    CONSTRAINT FK_user_service_permissions_user FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT FK_user_service_permissions_service FOREIGN KEY (service_id) REFERENCES services(id),
    CONSTRAINT FK_user_service_permissions_granted_by FOREIGN KEY (granted_by) REFERENCES users(id)
);

-- =============================================
-- INDEXES for performance
-- =============================================

-- 사용자 테이블 인덱스
CREATE INDEX IX_users_email ON users(email);
CREATE INDEX IX_users_role_id ON users(role_id);
CREATE INDEX IX_users_group_id ON users(group_id);
CREATE INDEX IX_users_approval_status ON users(approval_status);
CREATE INDEX IX_users_is_active ON users(is_active);

-- 워크스페이스 테이블 인덱스
CREATE INDEX IX_workspaces_owner_id ON workspaces(owner_id);
CREATE INDEX IX_workspaces_is_active ON workspaces(is_active);

-- 권한/기능 테이블 인덱스
CREATE INDEX IX_permissions_name ON permissions(name);
CREATE INDEX IX_permissions_category ON permissions(category);
CREATE INDEX IX_features_name ON features(name);
CREATE INDEX IX_features_category ON features(category);

-- 서비스 테이블 인덱스
CREATE INDEX IX_services_name ON services(name);
CREATE INDEX IX_services_category ON services(category);
CREATE INDEX IX_services_is_active ON services(is_active);

-- =============================================
-- INITIAL DATA (DML)
-- =============================================

-- 1. 기본 역할 데이터
INSERT INTO roles (name, description, is_active) VALUES
('admin', '시스템 관리자 역할', 1),
('manager', '프로젝트 관리자 역할', 1),
('user', '일반 사용자 역할', 1),
('guest', '게스트 사용자 역할', 1);

-- 2. 기본 권한 데이터
INSERT INTO permissions (name, display_name, description, category, is_active) VALUES
('read', '읽기', '데이터 읽기 권한', 'basic', 1),
('write', '쓰기', '데이터 쓰기 권한', 'basic', 1),
('delete', '삭제', '데이터 삭제 권한', 'basic', 1),
('admin', '관리자', '시스템 관리 권한', 'admin', 1),
('create_workspace', '워크스페이스 생성', '새 워크스페이스 생성 권한', 'workspace', 1),
('manage_workspace', '워크스페이스 관리', '워크스페이스 관리 권한', 'workspace', 1),
('upload_file', '파일 업로드', '파일 업로드 권한', 'file', 1),
('download_file', '파일 다운로드', '파일 다운로드 권한', 'file', 1),
('run_jupyter', 'Jupyter 실행', 'Jupyter Lab 실행 권한', 'jupyter', 1),
('manage_users', '사용자 관리', '사용자 계정 관리 권한', 'admin', 1);

-- 3. 기본 기능 데이터
INSERT INTO features (name, display_name, description, category, icon, url_path, is_external, open_in_new_tab, auto_grant, requires_approval, is_active) VALUES
('dashboard', '대시보드', '데이터 분석 대시보드', 'core', '📊', '/dashboard', 0, 0, 1, 0, 1),
('jupyter', 'Jupyter Lab', '데이터 분석을 위한 Jupyter Lab', 'analysis', '🔬', '/jupyter', 0, 1, 0, 1, 1),
('file_manager', '파일 관리자', '파일 업로드 및 관리', 'utility', '📁', '/files', 0, 0, 1, 0, 1),
('user_management', '사용자 관리', '사용자 계정 관리', 'admin', '👥', '/admin/users', 0, 0, 0, 1, 1),
('workspace_management', '워크스페이스 관리', '워크스페이스 생성 및 관리', 'core', '🏗️', '/workspaces', 0, 0, 1, 0, 1),
('data_analysis', '데이터 분석', '데이터 분석 도구', 'analysis', '📈', '/analysis', 0, 0, 0, 1, 1),
('report_generator', '보고서 생성', '자동 보고서 생성 도구', 'reporting', '📋', '/reports', 0, 0, 0, 1, 1),
('chat_llm', 'AI 채팅', 'LLM 기반 대화형 AI', 'ai', '🤖', '/chat', 0, 0, 0, 1, 1);

-- 4. 서비스 카테고리 데이터
INSERT INTO service_categories (name, display_name, description, sort_order, is_active) VALUES
('analysis', '데이터 분석', '데이터 분석 관련 서비스', 1, 1),
('development', '개발 도구', '개발 관련 도구들', 2, 1),
('utility', '유틸리티', '편의 기능들', 3, 1),
('ai', 'AI 서비스', 'AI 및 머신러닝 서비스', 4, 1),
('external', '외부 서비스', '외부 연동 서비스', 5, 1);

-- 5. 기본 그룹 생성 (관리자 사용자 생성 전에 임시로 생성)
INSERT INTO groups (name, description, is_active, created_by) VALUES
('기본 그룹', '모든 사용자의 기본 그룹', 1, NULL),
('관리자 그룹', '시스템 관리자 그룹', 1, NULL),
('개발팀', '개발팀 그룹', 1, NULL),
('데이터팀', '데이터 사이언스 팀', 1, NULL);

-- 6. 관리자 사용자 생성
DECLARE @admin_id CHAR(36) = NEWID();
DECLARE @admin_group_id INT = (SELECT id FROM groups WHERE name = '관리자 그룹');
DECLARE @admin_role_id INT = (SELECT id FROM roles WHERE name = 'admin');

INSERT INTO users (id, real_name, display_name, email, phone_number, hashed_password, is_active, is_admin, is_verified, approval_status, role_id, group_id, department, position, login_count) VALUES
(@admin_id, '시스템 관리자', 'Admin', 'admin@jupyter-platform.com', '010-1234-5678', '$2b$12$8H1JYqXb8GjPvGYxY.pxJe5X.pX9PQS5R2K6hF9wBgYz4K6sJ2K6s', 1, 1, 1, 'approved', @admin_role_id, @admin_group_id, 'IT팀', '시스템 관리자', 0);

-- 그룹의 created_by 필드 업데이트
UPDATE groups SET created_by = @admin_id WHERE created_by IS NULL;

-- 7. 테스트 사용자들 생성
DECLARE @user_role_id INT = (SELECT id FROM roles WHERE name = 'user');
DECLARE @default_group_id INT = (SELECT id FROM groups WHERE name = '기본 그룹');

INSERT INTO users (real_name, display_name, email, hashed_password, is_active, is_verified, approval_status, role_id, group_id, department, position, login_count) VALUES
('김데이터', '데이터분석가', 'data.analyst@company.com', '$2b$12$8H1JYqXb8GjPvGYxY.pxJe5X.pX9PQS5R2K6hF9wBgYz4K6sJ2K6s', 1, 1, 'approved', @user_role_id, @default_group_id, '데이터팀', '데이터 분석가', 0),
('박개발', '개발자', 'developer@company.com', '$2b$12$8H1JYqXb8GjPvGYxY.pxJe5X.pX9PQS5R2K6hF9wBgYz4K6sJ2K6s', 1, 1, 'approved', @user_role_id, @default_group_id, '개발팀', '백엔드 개발자', 0),
('이연구', '연구원', 'researcher@company.com', '$2b$12$8H1JYqXb8GjPvGYxY.pxJe5X.pX9PQS5R2K6hF9wBgYz4K6sJ2K6s', 1, 1, 'pending', @user_role_id, @default_group_id, '연구소', '선임연구원', 0);


---관리자: admin@jupyter-platform.com / admin123
---테스트 사용자들: data.analyst@company.com, developer@company.com, researcher@company.com / admin123

-- 8. 기본 서비스 생성
INSERT INTO services (name, display_name, description, url, icon_url, is_active, is_external, requires_auth, open_in_new_tab, sort_order, category, created_by) VALUES
('jupyter_lab', 'Jupyter Lab', 'Interactive Python development environment', '/jupyter', '/static/icons/jupyter.png', 1, 0, 1, 1, 1, 'analysis', @admin_id),
('vscode', 'VS Code Server', 'Web-based VS Code editor', '/vscode', '/static/icons/vscode.png', 1, 0, 1, 1, 2, 'development', @admin_id),
('file_browser', 'File Browser', 'Web-based file manager', '/files', '/static/icons/files.png', 1, 0, 1, 0, 3, 'utility', @admin_id),
('git_web', 'Git Web Interface', 'Web-based Git repository browser', '/git', '/static/icons/git.png', 1, 0, 1, 1, 4, 'development', @admin_id);

-- 9. 역할별 권한 할당
-- 관리자 역할에 모든 권한 부여
INSERT INTO role_permissions (role_id, permission_id)
SELECT @admin_role_id, id FROM permissions;

-- 일반 사용자 역할에 기본 권한 부여
INSERT INTO role_permissions (role_id, permission_id)
SELECT @user_role_id, id FROM permissions 
WHERE name IN ('read', 'write', 'create_workspace', 'manage_workspace', 'upload_file', 'download_file', 'run_jupyter');

-- 10. 역할별 기능 할당
-- 관리자 역할에 모든 기능 부여
INSERT INTO role_features (role_id, feature_id)
SELECT @admin_role_id, id FROM features;

-- 일반 사용자 역할에 기본 기능 부여
INSERT INTO role_features (role_id, feature_id)
SELECT @user_role_id, id FROM features 
WHERE name IN ('dashboard', 'jupyter', 'file_manager', 'workspace_management', 'data_analysis');

-- =============================================
-- TRIGGERS for automatic timestamp updates
-- =============================================

-- 사용자 테이블 업데이트 트리거
CREATE TRIGGER tr_users_update
ON users
AFTER UPDATE
AS
BEGIN
    UPDATE users 
    SET updated_at = GETDATE()
    FROM users u
    INNER JOIN inserted i ON u.id = i.id
END;

-- 워크스페이스 테이블 업데이트 트리거
CREATE TRIGGER tr_workspaces_update
ON workspaces
AFTER UPDATE
AS
BEGIN
    UPDATE workspaces 
    SET updated_at = GETDATE()
    FROM workspaces w
    INNER JOIN inserted i ON w.id = i.id
END;

-- 서비스 테이블 업데이트 트리거
CREATE TRIGGER tr_services_update
ON services
AFTER UPDATE
AS
BEGIN
    UPDATE services 
    SET updated_at = GETDATE()
    FROM services s
    INNER JOIN inserted i ON s.id = i.id
END;

-- =============================================
-- SAMPLE WORKSPACE DATA
-- =============================================

-- 샘플 워크스페이스 생성
DECLARE @data_analyst_id CHAR(36) = (SELECT id FROM users WHERE email = 'data.analyst@company.com');
DECLARE @developer_id CHAR(36) = (SELECT id FROM users WHERE email = 'developer@company.com');

INSERT INTO workspaces (name, description, owner_id, is_active, is_public, jupyter_status, path, max_storage_mb) VALUES
('데이터 분석 프로젝트', '고객 데이터 분석을 위한 워크스페이스', @data_analyst_id, 1, 0, 'stopped', '/workspaces/data_analysis', 2000),
('머신러닝 실험', '머신러닝 모델 개발 및 실험', @data_analyst_id, 1, 0, 'stopped', '/workspaces/ml_experiments', 5000),
('백엔드 개발', 'API 서버 개발 워크스페이스', @developer_id, 1, 0, 'stopped', '/workspaces/backend_dev', 1000),
('데이터 시각화', '대시보드 및 차트 개발', @developer_id, 1, 1, 'stopped', '/workspaces/visualization', 1500);

-- =============================================
-- COMPLETION MESSAGE
-- =============================================

PRINT '✅ Jupyter Data Platform 데이터베이스 초기화 완료!';
PRINT '';
PRINT '📊 생성된 테이블:';
PRINT '  - users (사용자)';
PRINT '  - roles (역할)';
PRINT '  - groups (그룹)';
PRINT '  - workspaces (워크스페이스)';
PRINT '  - permissions (권한)';
PRINT '  - features (기능)';
PRINT '  - services (서비스)';
PRINT '  - service_categories (서비스 카테고리)';
PRINT '  - Association tables for many-to-many relationships';
PRINT '';
PRINT '👤 기본 계정 정보:';
PRINT '  관리자: admin@jupyter-platform.com / admin123';
PRINT '  테스트 사용자들: data.analyst@company.com, developer@company.com, researcher@company.com / admin123';
PRINT '';
PRINT '🚀 시스템을 시작할 준비가 완료되었습니다!';