#!/usr/bin/env python3
"""
로그인 테스트 및 디버그 스크립트
admin@test.com 계정으로 다양한 비밀번호를 시도해봅니다.
"""

import asyncio
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.database import get_db
from app.models.user import User
from app.utils.auth import verify_password
from sqlalchemy.orm import Session

async def test_login_credentials():
    """admin@test.com 계정의 로그인 테스트"""
    
    # 데이터베이스 연결
    db_gen = get_db()
    db: Session = next(db_gen)
    
    try:
        # admin@test.com 사용자 조회
        admin_user = db.query(User).filter(User.email == "admin@test.com").first()
        
        if not admin_user:
            print("❌ admin@test.com 사용자를 찾을 수 없습니다!")
            return
        
        print(f"✅ 사용자 발견:")
        print(f"   - 이메일: {admin_user.email}")
        print(f"   - 이름: {admin_user.real_name}")
        print(f"   - 활성화: {admin_user.is_active}")
        print(f"   - 관리자: {admin_user.is_admin}")
        print(f"   - 비밀번호 해시: {admin_user.hashed_password[:50]}...")
        print()
        
        # 다양한 비밀번호 시도
        passwords_to_try = [
            "admin123",      # LoginPage에서 시도하는 비밀번호
            "admin123!",     # create_admin_user.py에서 설정하는 비밀번호
            "admin",         # 간단한 비밀번호
            "password",      # 기본 비밀번호
            "123456"         # 일반적인 비밀번호
        ]
        
        print("🔐 비밀번호 테스트:")
        for password in passwords_to_try:
            is_valid = verify_password(password, admin_user.hashed_password)
            status = "✅ 성공" if is_valid else "❌ 실패"
            print(f"   {password:<12} -> {status}")
            
            if is_valid:
                print(f"\n🎉 올바른 비밀번호를 찾았습니다: '{password}'")
                break
        else:
            print("\n⚠️ 시도한 모든 비밀번호가 실패했습니다!")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("=== MAX Platform 로그인 테스트 ===")
    print()
    asyncio.run(test_login_credentials())