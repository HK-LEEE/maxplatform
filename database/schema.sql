-- Central Authentication System with Full Backend Integration
-- PostgreSQL Database Schema

-- Drop existing tables if they exist (be careful in production!)
DROP TABLE IF EXISTS refresh_tokens CASCADE;
DROP TABLE IF EXISTS user_service_permissions CASCADE;
DROP TABLE IF EXISTS user_features CASCADE;
DROP TABLE IF EXISTS user_permissions CASCADE;
DROP TABLE IF EXISTS group_features CASCADE;
DROP TABLE IF EXISTS group_permissions CASCADE;
DROP TABLE IF EXISTS role_features CASCADE;
DROP TABLE IF EXISTS role_permissions CASCADE;
DROP TABLE IF EXISTS workspaces CASCADE;
DROP TABLE IF EXISTS services CASCADE;
DROP TABLE IF EXISTS service_categories CASCADE;
DROP TABLE IF EXISTS features CASCADE;
DROP TABLE IF EXISTS permissions CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS groups CASCADE;
DROP TABLE IF EXISTS roles CASCADE;

-- Create roles table
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create groups table
CREATE TABLE groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID -- Will be linked to users.id after users table is created
);

-- Create permissions table
CREATE TABLE permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL, -- basic, workspace, file, jupyter, llm, admin
    is_active BOOLEAN DEFAULT TRUE
);

-- Create features table
CREATE TABLE features (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL, -- core, analysis, utility, ai, reporting, collaboration, integration, admin
    icon VARCHAR(50),
    url_path VARCHAR(200),
    is_external BOOLEAN DEFAULT FALSE,
    open_in_new_tab BOOLEAN DEFAULT FALSE,
    auto_grant BOOLEAN DEFAULT FALSE,
    requires_approval BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE
);

-- Create users table with comprehensive fields
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Basic user information
    real_name VARCHAR(100) NOT NULL,
    display_name VARCHAR(50),
    email VARCHAR(100) UNIQUE NOT NULL,
    phone_number VARCHAR(20),
    hashed_password VARCHAR(255) NOT NULL,
    
    -- Account status
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    is_verified BOOLEAN DEFAULT FALSE,
    approval_status VARCHAR(20) DEFAULT 'pending', -- pending, approved, rejected
    approval_note TEXT,
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMP,
    
    -- Role and group assignments
    role_id INTEGER REFERENCES roles(id),
    group_id INTEGER REFERENCES groups(id),
    
    -- Additional information
    department VARCHAR(100),
    position VARCHAR(100),
    bio TEXT,
    
    -- System information
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP,
    login_count INTEGER DEFAULT 0
);

-- Create service_categories table
CREATE TABLE service_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    icon VARCHAR(50),
    color VARCHAR(20),
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create services table
CREATE TABLE services (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    category_id INTEGER REFERENCES service_categories(id),
    icon VARCHAR(50),
    url VARCHAR(500),
    port INTEGER,
    is_external BOOLEAN DEFAULT FALSE,
    open_in_new_tab BOOLEAN DEFAULT FALSE,
    requires_auth BOOLEAN DEFAULT TRUE,
    requires_approval BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id)
);

-- Create workspaces table
CREATE TABLE workspaces (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    owner_id UUID NOT NULL REFERENCES users(id),
    jupyter_port INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create refresh_tokens table for OAuth 2.0
CREATE TABLE refresh_tokens (
    id SERIAL PRIMARY KEY,
    token VARCHAR(255) UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked BOOLEAN DEFAULT FALSE,
    replaced_by_token VARCHAR(255)
);

-- Create association tables for many-to-many relationships

-- User permissions
CREATE TABLE user_permissions (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    permission_id INTEGER REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, permission_id)
);

-- User features
CREATE TABLE user_features (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    feature_id INTEGER REFERENCES features(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, feature_id)
);

-- Role permissions
CREATE TABLE role_permissions (
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INTEGER REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- Role features
CREATE TABLE role_features (
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    feature_id INTEGER REFERENCES features(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, feature_id)
);

-- Group permissions
CREATE TABLE group_permissions (
    group_id INTEGER REFERENCES groups(id) ON DELETE CASCADE,
    permission_id INTEGER REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (group_id, permission_id)
);

-- Group features
CREATE TABLE group_features (
    group_id INTEGER REFERENCES groups(id) ON DELETE CASCADE,
    feature_id INTEGER REFERENCES features(id) ON DELETE CASCADE,
    PRIMARY KEY (group_id, feature_id)
);

-- User service permissions
CREATE TABLE user_service_permissions (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    service_id INTEGER REFERENCES services(id) ON DELETE CASCADE,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    granted_by UUID REFERENCES users(id),
    PRIMARY KEY (user_id, service_id)
);

-- Create indexes for better performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role_id ON users(role_id);
CREATE INDEX idx_users_group_id ON users(group_id);
CREATE INDEX idx_users_is_active ON users(is_active);
CREATE INDEX idx_users_approval_status ON users(approval_status);
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_token ON refresh_tokens(token);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);
CREATE INDEX idx_workspaces_owner_id ON workspaces(owner_id);
CREATE INDEX idx_services_category_id ON services(category_id);

-- Add foreign key constraint for groups.created_by after users table is created
ALTER TABLE groups ADD CONSTRAINT fk_groups_created_by FOREIGN KEY (created_by) REFERENCES users(id);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_workspaces_updated_at BEFORE UPDATE ON workspaces
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default data

-- Insert default roles
INSERT INTO roles (name, description) VALUES 
('admin', 'System Administrator'),
('user', 'Regular User'),
('viewer', 'Read-only User'),
('analyst', 'Data Analyst'),
('developer', 'Developer');

-- Insert default groups
INSERT INTO groups (name, description) VALUES 
('Default Users', 'Default group for all users'),
('Administrators', 'System administrators'),
('IT Department', 'IT department members'),
('HR Department', 'HR department members'),
('Finance Department', 'Finance department members'),
('Data Analysts', 'Data analysis team'),
('Developers', 'Development team');

-- Insert default permissions
INSERT INTO permissions (name, display_name, description, category) VALUES 
-- Basic permissions
('basic.login', 'Login Access', 'Basic login access to the system', 'basic'),
('basic.profile', 'Profile Management', 'Manage own profile information', 'basic'),
('basic.password', 'Password Change', 'Change own password', 'basic'),

-- Workspace permissions
('workspace.create', 'Create Workspace', 'Create new workspaces', 'workspace'),
('workspace.read', 'View Workspaces', 'View own workspaces', 'workspace'),
('workspace.update', 'Edit Workspace', 'Edit own workspaces', 'workspace'),
('workspace.delete', 'Delete Workspace', 'Delete own workspaces', 'workspace'),
('workspace.admin', 'Workspace Admin', 'Manage all workspaces', 'workspace'),

-- File permissions
('file.upload', 'File Upload', 'Upload files to workspaces', 'file'),
('file.download', 'File Download', 'Download files from workspaces', 'file'),
('file.delete', 'File Delete', 'Delete files from workspaces', 'file'),
('file.admin', 'File Admin', 'Manage all files in system', 'file'),

-- Jupyter permissions
('jupyter.access', 'Jupyter Access', 'Access Jupyter notebooks', 'jupyter'),
('jupyter.create', 'Create Jupyter', 'Create new Jupyter instances', 'jupyter'),
('jupyter.manage', 'Manage Jupyter', 'Manage Jupyter instances', 'jupyter'),
('jupyter.admin', 'Jupyter Admin', 'Administer all Jupyter instances', 'jupyter'),

-- LLM permissions
('llm.chat', 'LLM Chat', 'Use LLM chat functionality', 'llm'),
('llm.completion', 'LLM Completion', 'Use LLM code completion', 'llm'),
('llm.analysis', 'LLM Analysis', 'Use LLM for data analysis', 'llm'),
('llm.admin', 'LLM Admin', 'Administer LLM settings', 'llm'),

-- Admin permissions
('admin.users', 'User Management', 'Manage users and accounts', 'admin'),
('admin.roles', 'Role Management', 'Manage roles and permissions', 'admin'),
('admin.system', 'System Admin', 'Full system administration', 'admin'),
('admin.logs', 'View Logs', 'View system logs', 'admin');

-- Insert default features
INSERT INTO features (name, display_name, description, category, icon, url_path, auto_grant, requires_approval) VALUES 
-- Core features
('dashboard', 'Dashboard', 'Main dashboard with system overview', 'core', 'dashboard', '/dashboard', TRUE, FALSE),
('profile', 'User Profile', 'Manage user profile and settings', 'core', 'user', '/profile', TRUE, FALSE),

-- Analysis features
('jupyter', 'Jupyter Notebooks', 'Access to Jupyter notebook environment', 'analysis', 'code', '/jupyter', FALSE, TRUE),
('data_upload', 'Data Upload', 'Upload and manage data files', 'analysis', 'upload', '/files', FALSE, TRUE),
('data_visualization', 'Data Visualization', 'Create charts and visualizations', 'analysis', 'chart-bar', '/visualization', FALSE, TRUE),

-- AI features
('llm_chat', 'AI Chat Assistant', 'Chat with AI assistant', 'ai', 'comments', '/llm/chat', FALSE, TRUE),
('code_completion', 'AI Code Completion', 'AI-powered code completion', 'ai', 'code', '/llm/completion', FALSE, TRUE),
('data_analysis_ai', 'AI Data Analysis', 'AI-powered data analysis', 'ai', 'brain', '/llm/analysis', FALSE, TRUE),

-- Utility features
('file_manager', 'File Manager', 'Manage files and folders', 'utility', 'folder', '/files', FALSE, TRUE),
('workspace_manager', 'Workspace Manager', 'Manage workspaces', 'utility', 'layers', '/workspaces', FALSE, TRUE),

-- Admin features
('user_management', 'User Management', 'Manage system users', 'admin', 'users', '/admin/users', FALSE, TRUE),
('system_settings', 'System Settings', 'Configure system settings', 'admin', 'cog', '/admin/settings', FALSE, TRUE),
('system_logs', 'System Logs', 'View system logs and monitoring', 'admin', 'list', '/admin/logs', FALSE, TRUE);

-- Insert default service categories
INSERT INTO service_categories (name, display_name, description, icon, color, sort_order) VALUES 
('development', 'Development Tools', 'Development and coding tools', 'code', '#3B82F6', 1),
('analysis', 'Data Analysis', 'Data analysis and visualization tools', 'chart-bar', '#10B981', 2),
('ai', 'AI & Machine Learning', 'AI and machine learning platforms', 'brain', '#8B5CF6', 3),
('collaboration', 'Collaboration', 'Team collaboration tools', 'users', '#F59E0B', 4),
('utilities', 'Utilities', 'System utilities and tools', 'wrench', '#6B7280', 5);

-- Insert default services
INSERT INTO services (name, display_name, description, category_id, icon, url, port, is_external, requires_approval) VALUES 
('jupyter', 'Jupyter Lab', 'Interactive notebook environment', 1, 'code', 'http://localhost:8888', 8888, FALSE, TRUE),
('vscode', 'VS Code Server', 'Web-based VS Code editor', 1, 'code', 'http://localhost:8080', 8080, FALSE, TRUE),
('rstudio', 'RStudio Server', 'R development environment', 2, 'chart-line', 'http://localhost:8787', 8787, FALSE, TRUE),
('ollama', 'Ollama', 'Local LLM inference server', 3, 'brain', 'http://localhost:11434', 11434, FALSE, TRUE),
('langflow', 'LangFlow', 'Visual LLM workflow builder', 3, 'share', 'http://localhost:7860', 7860, FALSE, TRUE);

-- Create default admin user (password: admin123!)
INSERT INTO users (id, real_name, display_name, email, hashed_password, is_active, is_admin, is_verified, approval_status, role_id, group_id, department, position, login_count) 
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'System Administrator', 
    'Admin', 
    'admin@example.com', 
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/37JmwC8cS', -- admin123!
    TRUE, 
    TRUE, 
    TRUE, 
    'approved',
    1, -- admin role
    2, -- administrators group
    'IT',
    'System Administrator',
    0
);

-- Create test users
INSERT INTO users (id, real_name, display_name, email, hashed_password, is_active, is_admin, is_verified, approval_status, role_id, group_id, department, position, login_count) 
VALUES 
(
    '00000000-0000-0000-0000-000000000002',
    'Test User 1', 
    'User1', 
    'user1@example.com', 
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/37JmwC8cS', -- password
    TRUE, 
    FALSE, 
    TRUE, 
    'approved',
    2, -- user role
    3, -- IT department
    'IT',
    'Developer',
    0
),
(
    '00000000-0000-0000-0000-000000000003',
    'Test User 2', 
    'User2', 
    'user2@example.com', 
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/37JmwC8cS', -- password
    TRUE, 
    FALSE, 
    TRUE, 
    'approved',
    4, -- analyst role
    6, -- data analysts group
    'Analytics',
    'Data Analyst',
    0
);

-- Grant permissions to roles
INSERT INTO role_permissions (role_id, permission_id) VALUES 
-- Admin role gets all permissions
(1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (1, 8), (1, 9), (1, 10), (1, 11), (1, 12), (1, 13), (1, 14), (1, 15), (1, 16), (1, 17), (1, 18), (1, 19), (1, 20), (1, 21), (1, 22), (1, 23),
-- User role gets basic permissions
(2, 1), (2, 2), (2, 3), (2, 4), (2, 5), (2, 6), (2, 7), (2, 8), (2, 9), (2, 10), (2, 11), (2, 12), (2, 13), (2, 14), (2, 15),
-- Analyst role gets analysis permissions
(4, 1), (4, 2), (4, 3), (4, 4), (4, 5), (4, 6), (4, 7), (4, 8), (4, 9), (4, 10), (4, 11), (4, 12), (4, 13), (4, 14), (4, 15), (4, 16), (4, 17);

-- Grant features to roles
INSERT INTO role_features (role_id, feature_id) VALUES 
-- Admin role gets all features
(1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (1, 8), (1, 9), (1, 10), (1, 11), (1, 12), (1, 13), (1, 14),
-- User role gets basic features
(2, 1), (2, 2), (2, 3), (2, 4), (2, 5), (2, 9), (2, 10), (2, 11),
-- Analyst role gets analysis features
(4, 1), (2, 2), (4, 3), (4, 4), (4, 5), (4, 6), (4, 7), (4, 8), (4, 9), (4, 10), (4, 11);

COMMIT; 