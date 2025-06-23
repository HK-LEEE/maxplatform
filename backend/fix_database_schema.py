#!/usr/bin/env python3
"""
데이터베이스 스키마 수정 스크립트
- features 테이블에 누락된 컬럼들 추가
- permissions 테이블 구조 확인 및 수정
"""

import sys
import os
import pymysql
from datetime import datetime
from dotenv import load_dotenv
from urllib.parse import urlparse

# 환경 변수 로드
load_dotenv()

def parse_database_url():
    """DATABASE_URL 파싱"""
    database_url = os.getenv('DATABASE_URL', 'mysql+pymysql://test:test@localhost/jupyter_platform')
    parsed = urlparse(database_url)
    
    return {
        'host': parsed.hostname or 'localhost',
        'port': parsed.port or 3306,
        'user': parsed.username or 'root',
        'password': parsed.password or '',
        'database': parsed.path.lstrip('/') if parsed.path else 'jupyter_platform',
        'charset': 'utf8mb4'
    }

# 데이터베이스 연결 설정
DB_CONFIG = parse_database_url()

def get_connection():
    """데이터베이스 연결"""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        print(f"✅ MySQL 데이터베이스 연결 성공: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
        return conn
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")
        print(f"연결 정보: {DB_CONFIG}")
        return None

def check_table_exists(cursor, table_name):
    """테이블 존재 확인"""
    cursor.execute("SHOW TABLES LIKE %s", (table_name,))
    return cursor.fetchone() is not None

def check_column_exists(cursor, table_name, column_name):
    """컬럼 존재 확인"""
    cursor.execute(f"SHOW COLUMNS FROM {table_name} LIKE %s", (column_name,))
    return cursor.fetchone() is not None

def create_permissions_table(cursor):
    """permissions 테이블 생성"""
    create_sql = """
    CREATE TABLE IF NOT EXISTS permissions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) UNIQUE NOT NULL,
        display_name VARCHAR(200) NOT NULL,
        description TEXT,
        category VARCHAR(50) NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    cursor.execute(create_sql)
    print("✅ permissions 테이블 생성/확인 완료")

def create_features_table(cursor):
    """features 테이블 생성"""
    create_sql = """
    CREATE TABLE IF NOT EXISTS features (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) UNIQUE NOT NULL,
        display_name VARCHAR(200) NOT NULL,
        description TEXT,
        category VARCHAR(50) NOT NULL,
        icon VARCHAR(50),
        url_path VARCHAR(200),
        auto_grant BOOLEAN DEFAULT FALSE,
        requires_approval BOOLEAN DEFAULT TRUE,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    cursor.execute(create_sql)
    print("✅ features 테이블 생성/확인 완료")

def add_missing_columns(cursor):
    """누락된 컬럼들 추가"""
    
    # features 테이블에 컬럼 추가
    features_columns = [
        ("icon", "ALTER TABLE features ADD COLUMN icon VARCHAR(50) AFTER category"),
        ("url_path", "ALTER TABLE features ADD COLUMN url_path VARCHAR(200) AFTER icon"),
        ("auto_grant", "ALTER TABLE features ADD COLUMN auto_grant BOOLEAN DEFAULT FALSE AFTER url_path"),
        ("requires_approval", "ALTER TABLE features ADD COLUMN requires_approval BOOLEAN DEFAULT TRUE AFTER auto_grant"),
        ("created_at", "ALTER TABLE features ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ]
    
    for column_name, alter_sql in features_columns:
        if not check_column_exists(cursor, 'features', column_name):
            try:
                cursor.execute(alter_sql)
                print(f"✅ features 테이블에 {column_name} 컬럼 추가")
            except Exception as e:
                print(f"⚠️ features.{column_name} 컬럼 추가 실패: {e}")
    
    # permissions 테이블에 컬럼 추가
    permissions_columns = [
        ("created_at", "ALTER TABLE permissions ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ]
    
    for column_name, alter_sql in permissions_columns:
        if not check_column_exists(cursor, 'permissions', column_name):
            try:
                cursor.execute(alter_sql)
                print(f"✅ permissions 테이블에 {column_name} 컬럼 추가")
            except Exception as e:
                print(f"⚠️ permissions.{column_name} 컬럼 추가 실패: {e}")

def create_association_tables(cursor):
    """연관 테이블들 생성"""
    
    # user_permissions 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_permissions (
            user_id CHAR(36) NOT NULL,
            permission_id INT NOT NULL,
            PRIMARY KEY (user_id, permission_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)
    print("✅ user_permissions 테이블 생성/확인 완료")
    
    # user_features 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_features (
            user_id CHAR(36) NOT NULL,
            feature_id INT NOT NULL,
            PRIMARY KEY (user_id, feature_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (feature_id) REFERENCES features(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)
    print("✅ user_features 테이블 생성/확인 완료")
    
    # role_permissions 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS role_permissions (
            role_id INT NOT NULL,
            permission_id INT NOT NULL,
            PRIMARY KEY (role_id, permission_id),
            FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
            FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)
    print("✅ role_permissions 테이블 생성/확인 완료")
    
    # role_features 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS role_features (
            role_id INT NOT NULL,
            feature_id INT NOT NULL,
            PRIMARY KEY (role_id, feature_id),
            FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
            FOREIGN KEY (feature_id) REFERENCES features(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)
    print("✅ role_features 테이블 생성/확인 완료")

def main():
    """메인 함수"""
    print("🔧 데이터베이스 스키마 수정 시작...")
    
    conn = get_connection()
    if not conn:
        sys.exit(1)
    
    try:
        with conn.cursor() as cursor:
            # 기본 테이블들 생성/확인
            create_permissions_table(cursor)
            create_features_table(cursor)
            
            # 누락된 컬럼들 추가
            add_missing_columns(cursor)
            
            # 연관 테이블들 생성
            create_association_tables(cursor)
            
            # 변경사항 커밋
            conn.commit()
            print("✅ 모든 데이터베이스 스키마 수정 완료!")
            
    except Exception as e:
        print(f"❌ 스키마 수정 중 오류 발생: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main() 