#!/usr/bin/env python3
"""
올바른 collation으로 서비스 테이블 생성
"""

import os
import sys
from sqlalchemy import create_engine, text
from app.database import get_database_url

def create_service_tables_fixed():
    """users 테이블과 동일한 collation으로 서비스 테이블 생성"""
    print("🚀 서비스 시스템 테이블 생성 시작 (collation 수정)...")
    
    # 데이터베이스 연결
    database_url = get_database_url()
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as connection:
            
            # 1. 서비스 카테고리 테이블
            print("📊 서비스 카테고리 테이블 생성...")
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS service_categories (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(50) NOT NULL UNIQUE,
                    display_name VARCHAR(100) NOT NULL,
                    description TEXT,
                    sort_order INT DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_category_name (name),
                    INDEX idx_category_active (is_active),
                    INDEX idx_category_sort (sort_order)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
            """))
            
            # 2. 서비스 테이블
            print("🔧 서비스 테이블 생성...")
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS services (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    display_name VARCHAR(100) NOT NULL,
                    description TEXT,
                    url VARCHAR(500) NOT NULL,
                    icon_url VARCHAR(500),
                    thumbnail_url VARCHAR(500),
                    is_active BOOLEAN DEFAULT TRUE,
                    is_external BOOLEAN DEFAULT FALSE,
                    requires_auth BOOLEAN DEFAULT TRUE,
                    open_in_new_tab BOOLEAN DEFAULT FALSE,
                    sort_order INT DEFAULT 0,
                    category VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    created_by CHAR(36) COLLATE utf8mb4_0900_ai_ci NOT NULL,
                    INDEX idx_service_name (name),
                    INDEX idx_service_active (is_active),
                    INDEX idx_service_category (category),
                    INDEX idx_service_sort (sort_order),
                    INDEX idx_service_creator (created_by)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
            """))
            
            # 3. 사용자-서비스 권한 테이블
            print("👥 사용자-서비스 권한 테이블 생성...")
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS user_services (
                    user_id CHAR(36) COLLATE utf8mb4_0900_ai_ci NOT NULL,
                    service_id INT NOT NULL,
                    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    granted_by CHAR(36) COLLATE utf8mb4_0900_ai_ci,
                    PRIMARY KEY (user_id, service_id),
                    INDEX idx_user_services_user (user_id),
                    INDEX idx_user_services_service (service_id),
                    INDEX idx_user_services_granted_by (granted_by)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
            """))
            
            # 4. 역할-서비스 권한 테이블
            print("🎭 역할-서비스 권한 테이블 생성...")
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS role_services (
                    role_id INT NOT NULL,
                    service_id INT NOT NULL,
                    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    granted_by CHAR(36) COLLATE utf8mb4_0900_ai_ci,
                    PRIMARY KEY (role_id, service_id),
                    INDEX idx_role_services_role (role_id),
                    INDEX idx_role_services_service (service_id),
                    INDEX idx_role_services_granted_by (granted_by)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
            """))
            
            # 5. 사용자 서비스 권한 상세 테이블
            print("🔐 사용자 서비스 권한 상세 테이블 생성...")
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS user_service_permissions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id CHAR(36) COLLATE utf8mb4_0900_ai_ci NOT NULL,
                    service_id INT NOT NULL,
                    permission_level VARCHAR(20) DEFAULT 'read',
                    custom_permissions TEXT,
                    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    granted_by CHAR(36) COLLATE utf8mb4_0900_ai_ci NOT NULL,
                    expires_at TIMESTAMP NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    INDEX idx_user_permissions_user (user_id),
                    INDEX idx_user_permissions_service (service_id),
                    INDEX idx_user_permissions_level (permission_level),
                    INDEX idx_user_permissions_active (is_active),
                    INDEX idx_user_permissions_expires (expires_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
            """))
            
            # 6. 기본 카테고리 데이터 삽입
            print("📁 기본 카테고리 데이터 삽입...")
            connection.execute(text("""
                INSERT IGNORE INTO service_categories (name, display_name, description, sort_order) VALUES
                ('analytics', '데이터 분석', '데이터 분석 관련 서비스', 1),
                ('development', '개발 도구', '개발 관련 도구 및 서비스', 2),
                ('management', '관리 도구', '시스템 관리 및 운영 도구', 3),
                ('collaboration', '협업 도구', '팀 협업 및 커뮤니케이션 도구', 4)
            """))
            
            connection.commit()
            
        print("✅ 테이블 생성 완료 (올바른 collation)!")
        return True
        
    except Exception as e:
        print(f"❌ 테이블 생성 실패: {e}")
        return False

if __name__ == "__main__":
    success = create_service_tables_fixed()
    if not success:
        sys.exit(1) 