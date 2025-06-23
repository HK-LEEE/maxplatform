-- =================================================================
-- MySQL to MSSQL Migration Script
-- GenbaX Platform Database Migration
-- =================================================================

-- =================================================================
-- 1. DATABASE CREATION
-- =================================================================
USE master;
GO

-- Drop database if exists
IF EXISTS (SELECT name FROM sys.databases WHERE name = 'jupyter_platform_mssql')
BEGIN
    ALTER DATABASE jupyter_platform_mssql SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE jupyter_platform_mssql;
END
GO

-- Create new database
CREATE DATABASE jupyter_platform_mssql
COLLATE SQL_Latin1_General_CP1_CI_AS;
GO

USE jupyter_platform_mssql;
GO

-- =================================================================
-- 2. SCHEMA CREATION
-- =================================================================

-- Users table
CREATE TABLE users (
    id CHAR(36) NOT NULL PRIMARY KEY,
    real_name NVARCHAR(100) NOT NULL,
    display_name NVARCHAR(50) NULL,
    email NVARCHAR(100) NOT NULL UNIQUE,
    phone_number NVARCHAR(20) NULL,
    hashed_password NVARCHAR(255) NOT NULL,
    is_active BIT NOT NULL DEFAULT 1,
    is_admin BIT NOT NULL DEFAULT 0,
    is_verified BIT NOT NULL DEFAULT 0,
    approval_status NVARCHAR(20) NOT NULL DEFAULT 'pending',
    approval_note NTEXT NULL,
    approved_by CHAR(36) NULL,
    approved_at DATETIME2 NULL,
    role_id INT NULL,
    group_id INT NULL,
    department NVARCHAR(100) NULL,
    position NVARCHAR(100) NULL,
    bio NTEXT NULL,
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    last_login_at DATETIME2 NULL,
    login_count INT NOT NULL DEFAULT 0
);

-- Roles table
CREATE TABLE roles (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(50) NOT NULL UNIQUE,
    description NTEXT NULL,
    is_active BIT NOT NULL DEFAULT 1,
    created_at DATETIME2 NOT NULL DEFAULT GETDATE()
);

-- Groups table
CREATE TABLE groups (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100) NOT NULL UNIQUE,
    description NTEXT NULL,
    is_active BIT NOT NULL DEFAULT 1,
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    created_by CHAR(36) NOT NULL
);

-- Workspaces table
CREATE TABLE workspaces (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100) NOT NULL,
    description NTEXT NULL,
    owner_id CHAR(36) NOT NULL,
    is_active BIT NOT NULL DEFAULT 1,
    is_public BIT NOT NULL DEFAULT 0,
    jupyter_port INT NULL,
    jupyter_token NVARCHAR(255) NULL,
    jupyter_status NVARCHAR(20) NOT NULL DEFAULT 'stopped',
    path NVARCHAR(500) NULL,
    max_storage_mb INT NOT NULL DEFAULT 1000,
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    last_accessed DATETIME2 NULL
);

-- Services table
CREATE TABLE services (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100) NOT NULL UNIQUE,
    display_name NVARCHAR(100) NOT NULL,
    description NTEXT NULL,
    url NVARCHAR(500) NOT NULL,
    icon_url NVARCHAR(500) NULL,
    thumbnail_url NVARCHAR(500) NULL,
    is_active BIT NOT NULL DEFAULT 1,
    is_external BIT NOT NULL DEFAULT 0,
    requires_auth BIT NOT NULL DEFAULT 1,
    open_in_new_tab BIT NOT NULL DEFAULT 0,
    sort_order INT NOT NULL DEFAULT 0,
    category NVARCHAR(50) NULL,
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    created_by CHAR(36) NOT NULL
);

-- Service Categories table
CREATE TABLE service_categories (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(50) NOT NULL UNIQUE,
    display_name NVARCHAR(100) NOT NULL,
    description NTEXT NULL,
    sort_order INT NOT NULL DEFAULT 0,
    is_active BIT NOT NULL DEFAULT 1,
    created_at DATETIME2 NOT NULL DEFAULT GETDATE()
);

-- User Service Permissions table
CREATE TABLE user_service_permissions (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id CHAR(36) NOT NULL,
    service_id INT NOT NULL,
    permission_level NVARCHAR(20) NOT NULL DEFAULT 'read',
    custom_permissions NTEXT NULL,
    granted_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    granted_by CHAR(36) NOT NULL,
    expires_at DATETIME2 NULL,
    is_active BIT NOT NULL DEFAULT 1
);

-- Permissions table
CREATE TABLE permissions (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100) NOT NULL UNIQUE,
    display_name NVARCHAR(200) NOT NULL,
    description NTEXT NULL,
    category NVARCHAR(50) NOT NULL,
    is_active BIT NOT NULL DEFAULT 1
);

-- Features table
CREATE TABLE features (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100) NOT NULL UNIQUE,
    display_name NVARCHAR(200) NOT NULL,
    description NTEXT NULL,
    category NVARCHAR(50) NOT NULL,
    icon NVARCHAR(50) NULL,
    url_path NVARCHAR(200) NULL,
    is_external BIT NOT NULL DEFAULT 0,
    open_in_new_tab BIT NOT NULL DEFAULT 0,
    auto_grant BIT NOT NULL DEFAULT 0,
    requires_approval BIT NOT NULL DEFAULT 1,
    is_active BIT NOT NULL DEFAULT 1
);

-- Association tables (Many-to-Many)
CREATE TABLE user_permissions (
    user_id CHAR(36) NOT NULL,
    permission_id INT NOT NULL,
    PRIMARY KEY (user_id, permission_id)
);

CREATE TABLE user_features (
    user_id CHAR(36) NOT NULL,
    feature_id INT NOT NULL,
    PRIMARY KEY (user_id, feature_id)
);

CREATE TABLE role_permissions (
    role_id INT NOT NULL,
    permission_id INT NOT NULL,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE role_features (
    role_id INT NOT NULL,
    feature_id INT NOT NULL,
    PRIMARY KEY (role_id, feature_id)
);

CREATE TABLE group_permissions (
    group_id INT NOT NULL,
    permission_id INT NOT NULL,
    PRIMARY KEY (group_id, permission_id)
);

CREATE TABLE group_features (
    group_id INT NOT NULL,
    feature_id INT NOT NULL,
    PRIMARY KEY (group_id, feature_id)
);

CREATE TABLE user_services (
    user_id CHAR(36) NOT NULL,
    service_id INT NOT NULL,
    granted_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    granted_by CHAR(36) NULL,
    PRIMARY KEY (user_id, service_id)
);

CREATE TABLE role_services (
    role_id INT NOT NULL,
    service_id INT NOT NULL,
    granted_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    granted_by CHAR(36) NULL,
    PRIMARY KEY (role_id, service_id)
);

-- =================================================================
-- 3. INDEXES CREATION
-- =================================================================

-- Users table indexes
CREATE INDEX IX_users_email ON users(email);
CREATE INDEX IX_users_role_id ON users(role_id);
CREATE INDEX IX_users_group_id ON users(group_id);
CREATE INDEX IX_users_approved_by ON users(approved_by);
CREATE INDEX IX_users_created_at ON users(created_at);

-- Workspaces table indexes
CREATE INDEX IX_workspaces_owner_id ON workspaces(owner_id);
CREATE INDEX IX_workspaces_created_at ON workspaces(created_at);

-- Services table indexes
CREATE INDEX IX_services_category ON services(category);
CREATE INDEX IX_services_created_by ON services(created_by);
CREATE INDEX IX_services_sort_order ON services(sort_order);

-- User Service Permissions indexes
CREATE INDEX IX_user_service_permissions_user_id ON user_service_permissions(user_id);
CREATE INDEX IX_user_service_permissions_service_id ON user_service_permissions(service_id);
CREATE INDEX IX_user_service_permissions_granted_by ON user_service_permissions(granted_by);

-- =================================================================
-- 4. FOREIGN KEY CONSTRAINTS
-- =================================================================

-- Users table foreign keys
ALTER TABLE users ADD CONSTRAINT FK_users_approved_by FOREIGN KEY (approved_by) REFERENCES users(id);
ALTER TABLE users ADD CONSTRAINT FK_users_role_id FOREIGN KEY (role_id) REFERENCES roles(id);
ALTER TABLE users ADD CONSTRAINT FK_users_group_id FOREIGN KEY (group_id) REFERENCES groups(id);

-- Groups table foreign keys
ALTER TABLE groups ADD CONSTRAINT FK_groups_created_by FOREIGN KEY (created_by) REFERENCES users(id);

-- Workspaces table foreign keys
ALTER TABLE workspaces ADD CONSTRAINT FK_workspaces_owner_id FOREIGN KEY (owner_id) REFERENCES users(id);

-- Services table foreign keys
ALTER TABLE services ADD CONSTRAINT FK_services_created_by FOREIGN KEY (created_by) REFERENCES users(id);

-- User Service Permissions foreign keys
ALTER TABLE user_service_permissions ADD CONSTRAINT FK_user_service_permissions_user_id FOREIGN KEY (user_id) REFERENCES users(id);
ALTER TABLE user_service_permissions ADD CONSTRAINT FK_user_service_permissions_service_id FOREIGN KEY (service_id) REFERENCES services(id);
ALTER TABLE user_service_permissions ADD CONSTRAINT FK_user_service_permissions_granted_by FOREIGN KEY (granted_by) REFERENCES users(id);

-- Association tables foreign keys
ALTER TABLE user_permissions ADD CONSTRAINT FK_user_permissions_user_id FOREIGN KEY (user_id) REFERENCES users(id);
ALTER TABLE user_permissions ADD CONSTRAINT FK_user_permissions_permission_id FOREIGN KEY (permission_id) REFERENCES permissions(id);

ALTER TABLE user_features ADD CONSTRAINT FK_user_features_user_id FOREIGN KEY (user_id) REFERENCES users(id);
ALTER TABLE user_features ADD CONSTRAINT FK_user_features_feature_id FOREIGN KEY (feature_id) REFERENCES features(id);

ALTER TABLE role_permissions ADD CONSTRAINT FK_role_permissions_role_id FOREIGN KEY (role_id) REFERENCES roles(id);
ALTER TABLE role_permissions ADD CONSTRAINT FK_role_permissions_permission_id FOREIGN KEY (permission_id) REFERENCES permissions(id);

ALTER TABLE role_features ADD CONSTRAINT FK_role_features_role_id FOREIGN KEY (role_id) REFERENCES roles(id);
ALTER TABLE role_features ADD CONSTRAINT FK_role_features_feature_id FOREIGN KEY (feature_id) REFERENCES features(id);

ALTER TABLE group_permissions ADD CONSTRAINT FK_group_permissions_group_id FOREIGN KEY (group_id) REFERENCES groups(id);
ALTER TABLE group_permissions ADD CONSTRAINT FK_group_permissions_permission_id FOREIGN KEY (permission_id) REFERENCES permissions(id);

ALTER TABLE group_features ADD CONSTRAINT FK_group_features_group_id FOREIGN KEY (group_id) REFERENCES groups(id);
ALTER TABLE group_features ADD CONSTRAINT FK_group_features_feature_id FOREIGN KEY (feature_id) REFERENCES features(id);

ALTER TABLE user_services ADD CONSTRAINT FK_user_services_user_id FOREIGN KEY (user_id) REFERENCES users(id);
ALTER TABLE user_services ADD CONSTRAINT FK_user_services_service_id FOREIGN KEY (service_id) REFERENCES services(id);
ALTER TABLE user_services ADD CONSTRAINT FK_user_services_granted_by FOREIGN KEY (granted_by) REFERENCES users(id);

ALTER TABLE role_services ADD CONSTRAINT FK_role_services_role_id FOREIGN KEY (role_id) REFERENCES roles(id);
ALTER TABLE role_services ADD CONSTRAINT FK_role_services_service_id FOREIGN KEY (service_id) REFERENCES services(id);
ALTER TABLE role_services ADD CONSTRAINT FK_role_services_granted_by FOREIGN KEY (granted_by) REFERENCES users(id);

-- =================================================================
-- 5. DATA MIGRATION SCRIPT TEMPLATE
-- =================================================================

/*
-- NOTE: 다음 스크립트들은 MySQL 데이터베이스에서 실행하여 데이터를 추출하고
-- MSSQL로 이관할 때 사용하는 템플릿입니다.

-- Step 1: MySQL에서 데이터 추출 (MySQL에서 실행)
SELECT 'ROLES DATA:' as section;
SELECT id, name, description, is_active, created_at FROM roles ORDER BY id;

SELECT 'GROUPS DATA:' as section;
SELECT id, name, description, is_active, created_at, created_by FROM groups ORDER BY id;

SELECT 'USERS DATA:' as section;
SELECT id, real_name, display_name, email, phone_number, hashed_password, 
       is_active, is_admin, is_verified, approval_status, approval_note, 
       approved_by, approved_at, role_id, group_id, department, position, 
       bio, created_at, updated_at, last_login_at, login_count 
FROM users ORDER BY created_at;

SELECT 'WORKSPACES DATA:' as section;
SELECT id, name, description, owner_id, is_active, is_public, jupyter_port, 
       jupyter_token, jupyter_status, path, max_storage_mb, created_at, 
       updated_at, last_accessed 
FROM workspaces ORDER BY id;

SELECT 'SERVICE_CATEGORIES DATA:' as section;
SELECT id, name, display_name, description, sort_order, is_active, created_at 
FROM service_categories ORDER BY id;

SELECT 'SERVICES DATA:' as section;
SELECT id, name, display_name, description, url, icon_url, thumbnail_url, 
       is_active, is_external, requires_auth, open_in_new_tab, sort_order, 
       category, created_at, updated_at, created_by 
FROM services ORDER BY id;

SELECT 'PERMISSIONS DATA:' as section;
SELECT id, name, display_name, description, category, is_active 
FROM permissions ORDER BY id;

SELECT 'FEATURES DATA:' as section;
SELECT id, name, display_name, description, category, icon, url_path, 
       is_external, open_in_new_tab, auto_grant, requires_approval, is_active 
FROM features ORDER BY id;

SELECT 'USER_SERVICE_PERMISSIONS DATA:' as section;
SELECT id, user_id, service_id, permission_level, custom_permissions, 
       granted_at, granted_by, expires_at, is_active 
FROM user_service_permissions ORDER BY id;

-- Association tables
SELECT 'USER_PERMISSIONS DATA:' as section;
SELECT user_id, permission_id FROM user_permissions ORDER BY user_id, permission_id;

SELECT 'USER_FEATURES DATA:' as section;
SELECT user_id, feature_id FROM user_features ORDER BY user_id, feature_id;

SELECT 'ROLE_PERMISSIONS DATA:' as section;
SELECT role_id, permission_id FROM role_permissions ORDER BY role_id, permission_id;

SELECT 'ROLE_FEATURES DATA:' as section;
SELECT role_id, feature_id FROM role_features ORDER BY role_id, feature_id;

SELECT 'GROUP_PERMISSIONS DATA:' as section;
SELECT group_id, permission_id FROM group_permissions ORDER BY group_id, permission_id;

SELECT 'GROUP_FEATURES DATA:' as section;
SELECT group_id, feature_id FROM group_features ORDER BY group_id, feature_id;

SELECT 'USER_SERVICES DATA:' as section;
SELECT user_id, service_id, granted_at, granted_by FROM user_services ORDER BY user_id, service_id;

SELECT 'ROLE_SERVICES DATA:' as section;
SELECT role_id, service_id, granted_at, granted_by FROM role_services ORDER BY role_id, service_id;
*/

-- =================================================================
-- 6. SAMPLE DATA INSERTION TEMPLATE
-- =================================================================

-- Sample roles insertion
SET IDENTITY_INSERT roles ON;
INSERT INTO roles (id, name, description, is_active, created_at) VALUES
(1, 'admin', 'System Administrator', 1, GETDATE()),
(2, 'user', 'Regular User', 1, GETDATE()),
(3, 'viewer', 'Read-only User', 1, GETDATE());
SET IDENTITY_INSERT roles OFF;

-- Sample groups insertion
SET IDENTITY_INSERT groups ON;
INSERT INTO groups (id, name, description, is_active, created_at, created_by) VALUES
(1, 'Default Users', 'Default user group', 1, GETDATE(), 'system-generated-id'),
(2, 'Administrators', 'System administrators', 1, GETDATE(), 'system-generated-id'),
(3, 'Developers', 'Development team', 1, GETDATE(), 'system-generated-id');
SET IDENTITY_INSERT groups OFF;

-- Sample permissions insertion
SET IDENTITY_INSERT permissions ON;
INSERT INTO permissions (id, name, display_name, description, category, is_active) VALUES
(1, 'workspace_create', 'Create Workspace', 'Create new workspaces', 'workspace', 1),
(2, 'workspace_read', 'View Workspace', 'View workspace content', 'workspace', 1),
(3, 'workspace_update', 'Edit Workspace', 'Edit workspace settings', 'workspace', 1),
(4, 'workspace_delete', 'Delete Workspace', 'Delete workspaces', 'workspace', 1),
(5, 'file_upload', 'File Upload', 'Upload files to workspace', 'file', 1),
(6, 'file_download', 'File Download', 'Download files from workspace', 'file', 1),
(7, 'jupyter_start', 'Start Jupyter', 'Start Jupyter server', 'jupyter', 1),
(8, 'jupyter_stop', 'Stop Jupyter', 'Stop Jupyter server', 'jupyter', 1),
(9, 'llm_access', 'LLM Access', 'Access LLM services', 'llm', 1),
(10, 'admin_panel', 'Admin Panel', 'Access admin panel', 'admin', 1);
SET IDENTITY_INSERT permissions OFF;

-- Sample features insertion
SET IDENTITY_INSERT features ON;
INSERT INTO features (id, name, display_name, description, category, icon, url_path, is_external, open_in_new_tab, auto_grant, requires_approval, is_active) VALUES
(1, 'workspace_manager', 'Workspace Manager', 'Manage your workspaces', 'core', '🗂️', '/workspaces', 0, 0, 1, 0, 1),
(2, 'jupyter_lab', 'Jupyter Lab', 'Interactive notebook environment', 'analysis', '📓', '/jupyter', 0, 1, 1, 0, 1),
(3, 'file_manager', 'File Manager', 'Manage files and folders', 'utility', '📁', '/files', 0, 0, 1, 0, 1),
(4, 'llm_chat', 'LLM Chat', 'AI-powered chat interface', 'ai', '🤖', '/llm/chat', 0, 0, 0, 1, 1),
(5, 'llmops_platform', 'LLMOps Platform', 'LLM Operations Management', 'ai', '🧪', '/llmops', 0, 0, 0, 1, 1),
(6, 'admin_dashboard', 'Admin Dashboard', 'System administration', 'admin', '⚙️', '/admin', 0, 0, 0, 1, 1);
SET IDENTITY_INSERT features OFF;

-- =================================================================
-- 7. UPDATE TRIGGERS (for updated_at columns)
-- =================================================================

-- Users table update trigger
CREATE TRIGGER tr_users_updated_at
ON users
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE users 
    SET updated_at = GETDATE()
    FROM users u
    INNER JOIN inserted i ON u.id = i.id;
END;
GO

-- Workspaces table update trigger
CREATE TRIGGER tr_workspaces_updated_at
ON workspaces
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE workspaces 
    SET updated_at = GETDATE()
    FROM workspaces w
    INNER JOIN inserted i ON w.id = i.id;
END;
GO

-- Services table update trigger
CREATE TRIGGER tr_services_updated_at
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
GO

-- =================================================================
-- 8. VERIFICATION QUERIES
-- =================================================================

/*
-- Run these queries after migration to verify data integrity

SELECT 'Table Counts' as verification_type;
SELECT 'users' as table_name, COUNT(*) as row_count FROM users
UNION ALL
SELECT 'roles', COUNT(*) FROM roles
UNION ALL
SELECT 'groups', COUNT(*) FROM groups
UNION ALL
SELECT 'workspaces', COUNT(*) FROM workspaces
UNION ALL
SELECT 'services', COUNT(*) FROM services
UNION ALL
SELECT 'service_categories', COUNT(*) FROM service_categories
UNION ALL
SELECT 'permissions', COUNT(*) FROM permissions
UNION ALL
SELECT 'features', COUNT(*) FROM features
UNION ALL
SELECT 'user_service_permissions', COUNT(*) FROM user_service_permissions
UNION ALL
SELECT 'user_permissions', COUNT(*) FROM user_permissions
UNION ALL
SELECT 'user_features', COUNT(*) FROM user_features
UNION ALL
SELECT 'role_permissions', COUNT(*) FROM role_permissions
UNION ALL
SELECT 'role_features', COUNT(*) FROM role_features
UNION ALL
SELECT 'group_permissions', COUNT(*) FROM group_permissions
UNION ALL
SELECT 'group_features', COUNT(*) FROM group_features
UNION ALL
SELECT 'user_services', COUNT(*) FROM user_services
UNION ALL
SELECT 'role_services', COUNT(*) FROM role_services;

SELECT 'Foreign Key Validation' as verification_type;
-- Check for orphaned records
SELECT 'Orphaned users (invalid role_id)' as check_type, COUNT(*) as count
FROM users u LEFT JOIN roles r ON u.role_id = r.id 
WHERE u.role_id IS NOT NULL AND r.id IS NULL
UNION ALL
SELECT 'Orphaned users (invalid group_id)', COUNT(*)
FROM users u LEFT JOIN groups g ON u.group_id = g.id 
WHERE u.group_id IS NOT NULL AND g.id IS NULL
UNION ALL
SELECT 'Orphaned workspaces (invalid owner_id)', COUNT(*)
FROM workspaces w LEFT JOIN users u ON w.owner_id = u.id 
WHERE u.id IS NULL;
*/

PRINT 'MySQL to MSSQL migration script completed successfully.';
PRINT 'Remember to:';
PRINT '1. Export data from MySQL using the template queries';
PRINT '2. Insert the exported data into MSSQL tables';
PRINT '3. Run verification queries to ensure data integrity';
PRINT '4. Update connection strings in your application';
GO 