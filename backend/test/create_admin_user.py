#!/usr/bin/env python3
"""
관리자 계정 생성 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import get_db
from app.models.user import User, Role
from app.routers.auth import hash_password
from sqlalchemy.orm import Session
import uuid

def create_admin_user():
    """관리자 계정 생성"""
    
    # 데이터베이스 세션 얻기
    db = next(get_db())
    
    try:
        # 기존 관리자 계정 확인
        existing_admin = db.query(User).filter(User.email == "admin@test.com").first()
        if existing_admin:
            print("✅ 기존 관리자 계정이 있습니다:")
            print(f"   이메일: {existing_admin.email}")
            print(f"   이름: {existing_admin.real_name}")
            print(f"   관리자 권한: {existing_admin.is_admin}")
            print(f"   활성화 상태: {existing_admin.is_active}")
            
            # 관리자 권한이 없으면 부여
            if not existing_admin.is_admin:
                existing_admin.is_admin = True
                existing_admin.is_active = True
                existing_admin.approval_status = 'approved'
                db.commit()
                print("✅ 기존 계정에 관리자 권한을 부여했습니다.")
            
            return existing_admin
        
        # admin 역할 찾기 또는 생성
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            admin_role = Role(
                name="admin",
                description="시스템 관리자",
                is_active=True
            )
            db.add(admin_role)
            db.commit()
            db.refresh(admin_role)
            print("✅ admin 역할 생성완료")
        
        # 관리자 계정 생성
        admin_user = User(
            id=str(uuid.uuid4()),
            real_name="시스템 관리자",
            display_name="Admin",
            email="admin@test.com",
            phone_number="010-0000-0000",
            department="IT",
            position="시스템 관리자",
            hashed_password=hash_password("admin123!"),
            is_active=True,
            is_admin=True,
            is_verified=True,
            approval_status='approved',
            role_id=admin_role.id,
            login_count=0
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print("🎉 관리자 계정이 생성되었습니다!")
        print(f"   이메일: {admin_user.email}")
        print(f"   비밀번호: admin123!")
        print(f"   이름: {admin_user.real_name}")
        print("   📝 보안을 위해 로그인 후 비밀번호를 변경하세요.")
        
        return admin_user
        
    except Exception as e:
        print(f"❌ 관리자 계정 생성 실패: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_user() 