#!/usr/bin/env python3
"""
간단한 마이그레이션 실행 스크립트
외래키 제약조건을 임시로 비활성화하고 실행
"""

import os
import sys
from sqlalchemy import create_engine, text
from app.database import get_database_url

def run_simple_migration():
    """외래키 제약조건을 비활성화하고 마이그레이션 실행"""
    print("🚀 데이터베이스 마이그레이션을 시작합니다...")
    
    # 데이터베이스 연결
    database_url = get_database_url()
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as connection:
            # 1. 외래키 체크 비활성화
            print("🔓 외래키 체크 비활성화...")
            connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            
            # 2. 테이블 생성
            print("📊 서비스 카테고리 테이블 생성...")
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS service_categories (
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
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='서비스 카테고리 관리'
            """))
            
            print("🔧 서비스 테이블 생성...")
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS services (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL UNIQUE COMMENT '서비스명',
                    display_name VARCHAR(100) NOT NULL COMMENT '화면에 표시되는 서비스명',
                    description TEXT COMMENT '서비스 설명',
                    url VARCHAR(500) NOT NULL COMMENT '서비스 URL 또는 라우트',
                    icon_url VARCHAR(500) COMMENT '서비스 아이콘 URL',
                    thumbnail_url VARCHAR(500) COMMENT '서비스 썸네일 이미지 URL',
                    is_active BOOLEAN DEFAULT TRUE COMMENT '서비스 활성화 여부',
                    is_external BOOLEAN DEFAULT FALSE COMMENT '외부 서비스 여부',
                    requires_auth BOOLEAN DEFAULT TRUE COMMENT '인증 필요 여부',
                    open_in_new_tab BOOLEAN DEFAULT FALSE COMMENT '새 탭에서 열기 여부',
                    sort_order INT DEFAULT 0 COMMENT '정렬 순서',
                    category VARCHAR(50) COMMENT '서비스 카테고리',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    created_by CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '생성자 UUID',
                    INDEX idx_service_name (name),
                    INDEX idx_service_active (is_active),
                    INDEX idx_service_category (category),
                    INDEX idx_service_sort (sort_order),
                    INDEX idx_service_creator (created_by)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='서비스 정보 관리'
            """))
            
            print("👥 사용자-서비스 권한 테이블 생성...")
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS user_services (
                    user_id CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '사용자 UUID',
                    service_id INT NOT NULL COMMENT '서비스 ID',
                    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '권한 부여 시간',
                    granted_by CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '권한 부여자 UUID',
                    PRIMARY KEY (user_id, service_id),
                    INDEX idx_user_services_user (user_id),
                    INDEX idx_user_services_service (service_id),
                    INDEX idx_user_services_granted_by (granted_by)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='사용자별 서비스 접근 권한'
            """))
            
            print("🎭 역할-서비스 권한 테이블 생성...")
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS role_services (
                    role_id INT NOT NULL COMMENT '역할 ID',
                    service_id INT NOT NULL COMMENT '서비스 ID',
                    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '권한 부여 시간',
                    granted_by CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '권한 부여자 UUID',
                    PRIMARY KEY (role_id, service_id),
                    INDEX idx_role_services_role (role_id),
                    INDEX idx_role_services_service (service_id),
                    INDEX idx_role_services_granted_by (granted_by)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='역할별 서비스 접근 권한'
            """))
            
            print("🔐 사용자 서비스 권한 상세 테이블 생성...")
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS user_service_permissions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '사용자 UUID',
                    service_id INT NOT NULL COMMENT '서비스 ID',
                    permission_level VARCHAR(20) DEFAULT 'read' COMMENT '권한 레벨: read, write, admin',
                    custom_permissions TEXT COMMENT 'JSON 형태의 커스텀 권한',
                    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '권한 부여 시간',
                    granted_by CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '권한 부여자 UUID',
                    expires_at TIMESTAMP NULL COMMENT '권한 만료일',
                    is_active BOOLEAN DEFAULT TRUE,
                    INDEX idx_user_permissions_user (user_id),
                    INDEX idx_user_permissions_service (service_id),
                    INDEX idx_user_permissions_level (permission_level),
                    INDEX idx_user_permissions_active (is_active),
                    INDEX idx_user_permissions_expires (expires_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='사용자별 서비스 권한 상세 관리'
            """))
            
            # 3. 외래키 제약조건 추가
            print("🔗 외래키 제약조건 추가...")
            try:
                connection.execute(text("ALTER TABLE services ADD CONSTRAINT fk_services_created_by FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT"))
            except Exception as e:
                if "duplicate" not in str(e).lower():
                    print(f"  ⚠️ services 외래키 추가 실패: {e}")
            
            try:
                connection.execute(text("ALTER TABLE user_services ADD CONSTRAINT fk_user_services_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"))
            except Exception as e:
                if "duplicate" not in str(e).lower():
                    print(f"  ⚠️ user_services 사용자 외래키 추가 실패: {e}")
            
            try:
                connection.execute(text("ALTER TABLE user_services ADD CONSTRAINT fk_user_services_service FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE"))
            except Exception as e:
                if "duplicate" not in str(e).lower():
                    print(f"  ⚠️ user_services 서비스 외래키 추가 실패: {e}")
            
            try:
                connection.execute(text("ALTER TABLE user_services ADD CONSTRAINT fk_user_services_granted_by FOREIGN KEY (granted_by) REFERENCES users(id) ON DELETE SET NULL"))
            except Exception as e:
                if "duplicate" not in str(e).lower():
                    print(f"  ⚠️ user_services 부여자 외래키 추가 실패: {e}")
            
            try:
                connection.execute(text("ALTER TABLE role_services ADD CONSTRAINT fk_role_services_role FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE"))
            except Exception as e:
                if "duplicate" not in str(e).lower():
                    print(f"  ⚠️ role_services 역할 외래키 추가 실패: {e}")
            
            try:
                connection.execute(text("ALTER TABLE role_services ADD CONSTRAINT fk_role_services_service FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE"))
            except Exception as e:
                if "duplicate" not in str(e).lower():
                    print(f"  ⚠️ role_services 서비스 외래키 추가 실패: {e}")
            
            try:
                connection.execute(text("ALTER TABLE role_services ADD CONSTRAINT fk_role_services_granted_by FOREIGN KEY (granted_by) REFERENCES users(id) ON DELETE SET NULL"))
            except Exception as e:
                if "duplicate" not in str(e).lower():
                    print(f"  ⚠️ role_services 부여자 외래키 추가 실패: {e}")
            
            try:
                connection.execute(text("ALTER TABLE user_service_permissions ADD CONSTRAINT fk_user_service_permissions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"))
            except Exception as e:
                if "duplicate" not in str(e).lower():
                    print(f"  ⚠️ user_service_permissions 사용자 외래키 추가 실패: {e}")
            
            try:
                connection.execute(text("ALTER TABLE user_service_permissions ADD CONSTRAINT fk_user_service_permissions_service FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE"))
            except Exception as e:
                if "duplicate" not in str(e).lower():
                    print(f"  ⚠️ user_service_permissions 서비스 외래키 추가 실패: {e}")
            
            try:
                connection.execute(text("ALTER TABLE user_service_permissions ADD CONSTRAINT fk_user_service_permissions_granted_by FOREIGN KEY (granted_by) REFERENCES users(id) ON DELETE RESTRICT"))
            except Exception as e:
                if "duplicate" not in str(e).lower():
                    print(f"  ⚠️ user_service_permissions 부여자 외래키 추가 실패: {e}")
            
            # 4. 외래키 체크 다시 활성화
            print("🔒 외래키 체크 재활성화...")
            connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            
            # 5. 기본 데이터 삽입
            print("📁 기본 카테고리 데이터 삽입...")
            connection.execute(text("""
                INSERT IGNORE INTO service_categories (name, display_name, description, sort_order) VALUES
                ('analytics', '데이터 분석', '데이터 분석 관련 서비스', 1),
                ('development', '개발 도구', '개발 관련 도구 및 서비스', 2),
                ('management', '관리 도구', '시스템 관리 및 운영 도구', 3),
                ('collaboration', '협업 도구', '팀 협업 및 커뮤니케이션 도구', 4)
            """))
            
            # 관리자 계정 확인
            admin_result = connection.execute(text("SELECT id FROM users WHERE is_admin = TRUE LIMIT 1")).fetchone()
            if admin_result:
                admin_user_id = admin_result[0]
                print(f"👤 관리자 계정 발견: {admin_user_id}")
                
                print("🔧 기본 서비스 생성...")
                connection.execute(text("""
                    INSERT IGNORE INTO services (name, display_name, description, url, category, sort_order, created_by) VALUES
                    ('jupyter_workspace', '쥬피터 워크스페이스', '데이터 분석을 위한 쥬피터 노트북 환경', '/dashboard', 'analytics', 1, :admin_id),
                    ('file_manager', '파일 관리자', '워크스페이스 파일 관리 도구', '/files', 'development', 2, :admin_id)
                """), {"admin_id": admin_user_id})
                
                print("🔐 기본 권한 설정...")
                # 일반 사용자에게 쥬피터 워크스페이스 권한 부여
                connection.execute(text("""
                    INSERT IGNORE INTO role_services (role_id, service_id, granted_by)
                    SELECT r.id, s.id, :admin_id
                    FROM roles r, services s 
                    WHERE r.name = 'user' AND s.name = 'jupyter_workspace'
                """), {"admin_id": admin_user_id})
                
                # 관리자에게 모든 서비스 권한 부여
                connection.execute(text("""
                    INSERT IGNORE INTO role_services (role_id, service_id, granted_by)
                    SELECT r.id, s.id, :admin_id
                    FROM roles r, services s 
                    WHERE r.name = 'admin'
                """), {"admin_id": admin_user_id})
                
            else:
                print("⚠️ 관리자 계정이 없어 기본 서비스를 생성하지 않습니다.")
            
            # 6. 뷰 생성
            print("👁️ 사용자 접근 가능 서비스 뷰 생성...")
            try:
                connection.execute(text("DROP VIEW IF EXISTS user_accessible_services"))
                connection.execute(text("""
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
                      AND s.is_active = TRUE
                """))
            except Exception as e:
                print(f"  ⚠️ 뷰 생성 실패 (무시): {e}")
            
            connection.commit()
            
        print("✅ 마이그레이션 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        return False

if __name__ == "__main__":
    success = run_simple_migration()
    if not success:
        sys.exit(1) 