#!/usr/bin/env python3
"""
PostgreSQL 데이터베이스 테이블 재생성 스크립트
UUID 타입 호환성 문제 해결을 위한 완전 초기화
"""

import psycopg2
from psycopg2 import sql
import logging
from app.database import engine, Base
from app.models import user, refresh_token, workspace, service, tables  # 모든 모델 임포트

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def drop_all_tables():
    """모든 테이블 삭제"""
    try:
        # PostgreSQL 연결
        conn = psycopg2.connect(
            host='localhost',
            database='platform_integration',
            user='postgres',
            password='2300'
        )
        cur = conn.cursor()
        
        logger.info("🗑️ 기존 테이블 삭제 시작...")
        
        # 모든 테이블 삭제 (외래 키 제약 조건 때문에 CASCADE 사용)
        tables_to_drop = [
            'refresh_tokens',
            'user_services',
            'role_services', 
            'user_permissions',
            'user_features',
            'role_permissions',
            'role_features',
            'group_permissions',
            'group_features',
            'user_service_permissions',
            'service_requests',
            'services',
            'service_categories',
            'workspaces',
            'users',
            'roles',
            'groups',
            'permissions',
            'features'
        ]
        
        for table in tables_to_drop:
            try:
                cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                logger.info(f"✅ {table} 테이블 삭제 완료")
            except Exception as e:
                logger.warning(f"⚠️ {table} 테이블 삭제 중 오류 (무시): {e}")
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info("✅ 모든 테이블 삭제 완료!")
        return True
        
    except Exception as e:
        logger.error(f"❌ 테이블 삭제 실패: {e}")
        return False

def create_all_tables():
    """모든 테이블 생성"""
    try:
        logger.info("🔨 새 테이블 생성 시작...")
        
        # SQLAlchemy를 사용해 모든 테이블 생성
        Base.metadata.create_all(bind=engine)
        
        logger.info("✅ 모든 테이블 생성 완료!")
        return True
        
    except Exception as e:
        logger.error(f"❌ 테이블 생성 실패: {e}")
        return False

def create_initial_data():
    """기본 데이터 생성"""
    try:
        from sqlalchemy.orm import sessionmaker
        from app.models.user import User, Role, Group
        from passlib.context import CryptContext
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        logger.info("👤 기본 데이터 생성 시작...")
        
        # 비밀번호 해싱
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # 기본 역할 생성
        admin_role = Role(
            name="admin",
            description="시스템 관리자"
        )
        user_role = Role(
            name="user", 
            description="일반 사용자"
        )
        session.add(admin_role)
        session.add(user_role)
        session.commit()
        
        # 기본 그룹 생성 (created_by는 나중에 설정)
        default_group = Group(
            name="default",
            description="기본 사용자 그룹"
        )
        session.add(default_group)
        session.commit()
        
        # 관리자 계정 생성
        admin_user = User(
            real_name="시스템 관리자",
            display_name="Admin",
            email="admin@test.com",
            hashed_password=pwd_context.hash("admin123"),
            is_active=True,
            is_admin=True,
            is_verified=True,
            approval_status="approved",
            role_id=admin_role.id,
            group_id=default_group.id
        )
        session.add(admin_user)
        session.commit()
        
        # 그룹 생성자 업데이트
        default_group.created_by = admin_user.id
        session.commit()
        
        logger.info("✅ 기본 데이터 생성 완료!")
        logger.info("🔑 관리자 계정: admin@test.com / admin123")
        
        session.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ 기본 데이터 생성 실패: {e}")
        return False

def main():
    """메인 실행 함수"""
    logger.info("🚀 PostgreSQL 데이터베이스 재생성 시작")
    
    # 1. 모든 테이블 삭제
    if not drop_all_tables():
        return False
    
    # 2. 새 테이블 생성
    if not create_all_tables():
        return False
    
    # 3. 기본 데이터 생성
    if not create_initial_data():
        return False
    
    logger.info("🎉 데이터베이스 재생성 완료!")
    return True

if __name__ == "__main__":
    main() 