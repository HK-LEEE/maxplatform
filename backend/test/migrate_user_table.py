#!/usr/bin/env python3
"""
사용자 테이블 마이그레이션 스크립트
기존 users 테이블에 새로운 권한 관리 컬럼들을 추가
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import get_database_url

def migrate_users_table():
    """users 테이블에 새로운 컬럼들을 추가합니다."""
    print("사용자 테이블 마이그레이션 시작...")
    
    engine = create_engine(get_database_url())
    
    # 추가할 컬럼들
    new_columns = [
        "ADD COLUMN approval_status VARCHAR(20) DEFAULT 'pending' COMMENT '승인 상태: pending, approved, rejected'",
        "ADD COLUMN approval_note TEXT NULL COMMENT '승인/거부 사유'",
        "ADD COLUMN approved_by CHAR(36) NULL COMMENT '승인한 관리자'",
        "ADD COLUMN approved_at DATETIME NULL COMMENT '승인 일시'"
    ]
    
    try:
        with engine.connect() as connection:
            # 트랜잭션 시작
            trans = connection.begin()
            
            try:
                for column_def in new_columns:
                    sql = f"ALTER TABLE users {column_def}"
                    print(f"실행 중: {sql}")
                    connection.execute(text(sql))
                
                # 기존 사용자들을 승인된 상태로 업데이트
                update_sql = "UPDATE users SET approval_status = 'approved' WHERE approval_status IS NULL OR approval_status = 'pending'"
                print(f"실행 중: {update_sql}")
                connection.execute(text(update_sql))
                
                # 외래키 제약조건 추가
                fk_sql = "ALTER TABLE users ADD CONSTRAINT fk_users_approved_by FOREIGN KEY (approved_by) REFERENCES users(id)"
                print(f"실행 중: {fk_sql}")
                try:
                    connection.execute(text(fk_sql))
                except Exception as e:
                    print(f"외래키 제약조건 추가 실패 (이미 존재할 수 있음): {e}")
                
                trans.commit()
                print("✅ 사용자 테이블 마이그레이션 완료")
                
            except Exception as e:
                trans.rollback()
                print(f"❌ 마이그레이션 실패: {e}")
                raise
                
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")
        raise

def create_new_tables():
    """새로운 테이블들을 생성합니다."""
    print("새로운 테이블 생성 중...")
    
    engine = create_engine(get_database_url())
    
    # 새로운 테이블 생성 SQL
    tables_sql = [
        """
        CREATE TABLE IF NOT EXISTS permissions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL COMMENT '권한 이름',
            display_name VARCHAR(100) NOT NULL COMMENT '표시될 권한 이름',
            description TEXT NULL COMMENT '권한 설명',
            category VARCHAR(50) NOT NULL COMMENT '권한 카테고리',
            is_active BOOLEAN DEFAULT TRUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        """
        CREATE TABLE IF NOT EXISTS features (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL COMMENT '기능 이름',
            display_name VARCHAR(100) NOT NULL COMMENT '표시될 기능 이름',
            description TEXT NULL COMMENT '기능 설명',
            category VARCHAR(50) NOT NULL COMMENT '기능 카테고리',
            icon VARCHAR(50) NULL COMMENT '아이콘 이름',
            url_path VARCHAR(200) NULL COMMENT '기능 URL 경로',
            is_active BOOLEAN DEFAULT TRUE,
            requires_approval BOOLEAN DEFAULT FALSE COMMENT '승인이 필요한 기능인지',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        """
        CREATE TABLE IF NOT EXISTS user_permissions (
            user_id CHAR(36) NOT NULL,
            permission_id INT NOT NULL,
            PRIMARY KEY (user_id, permission_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        """
        CREATE TABLE IF NOT EXISTS user_features (
            user_id CHAR(36) NOT NULL,
            feature_id INT NOT NULL,
            PRIMARY KEY (user_id, feature_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (feature_id) REFERENCES features(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        """
        CREATE TABLE IF NOT EXISTS role_permissions (
            role_id INT NOT NULL,
            permission_id INT NOT NULL,
            PRIMARY KEY (role_id, permission_id),
            FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
            FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        """
        CREATE TABLE IF NOT EXISTS role_features (
            role_id INT NOT NULL,
            feature_id INT NOT NULL,
            PRIMARY KEY (role_id, feature_id),
            FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
            FOREIGN KEY (feature_id) REFERENCES features(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    ]
    
    try:
        with engine.connect() as connection:
            trans = connection.begin()
            
            try:
                for sql in tables_sql:
                    print(f"테이블 생성 중...")
                    connection.execute(text(sql))
                
                trans.commit()
                print("✅ 새로운 테이블 생성 완료")
                
            except Exception as e:
                trans.rollback()
                print(f"❌ 테이블 생성 실패: {e}")
                raise
                
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")
        raise

def main():
    """메인 실행 함수"""
    print("🚀 데이터베이스 마이그레이션 시작")
    print("=" * 50)
    
    try:
        # 1. 사용자 테이블 마이그레이션
        migrate_users_table()
        
        # 2. 새로운 테이블 생성
        create_new_tables()
        
        print("=" * 50)
        print("🎉 데이터베이스 마이그레이션 완료!")
        print("\n다음 단계:")
        print("1. python init_permission_system.py 실행")
        print("2. 백엔드 서버 재시작")
        
    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 