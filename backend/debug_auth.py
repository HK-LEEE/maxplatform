#!/usr/bin/env python3
"""
Auth 시스템 디버깅 스크립트
"""

from app.database import get_db, SessionLocal
from app.models.user import User
from app.routers.auth import get_user_by_email, authenticate_user
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_database_operations():
    """데이터베이스 기본 작업 테스트"""
    
    print("=== 데이터베이스 작업 테스트 ===")
    
    try:
        # 세션 직접 생성
        db = SessionLocal()
        print("✅ 세션 생성 성공")
        
        # 사용자 수 조회
        user_count = db.query(User).count()
        print(f"📊 총 사용자 수: {user_count}")
        
        # 모든 사용자 조회
        users = db.query(User).all()
        print(f"👥 사용자 목록:")
        for user in users:
            print(f"  - {user.email} ({user.real_name}) - Admin: {user.is_admin}")
        
        # 특정 사용자 조회
        admin_user = db.query(User).filter(User.email == "admin@test.com").first()
        if admin_user:
            print(f"✅ 관리자 사용자 발견: {admin_user.real_name}")
            print(f"   ID: {admin_user.id}")
            print(f"   Email: {admin_user.email}")
            print(f"   Active: {admin_user.is_active}")
            print(f"   Admin: {admin_user.is_admin}")
        else:
            print("❌ 관리자 사용자를 찾을 수 없음")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ 데이터베이스 작업 실패: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def test_auth_functions():
    """Auth 함수들 테스트"""
    
    print("\n=== Auth 함수 테스트 ===")
    
    try:
        db = SessionLocal()
        
        # get_user_by_email 테스트
        print("1. get_user_by_email 테스트...")
        user = get_user_by_email(db, "admin@test.com")
        if user:
            print(f"✅ 사용자 발견: {user.email}")
        else:
            print("❌ 사용자를 찾을 수 없음")
        
        # authenticate_user 테스트
        print("2. authenticate_user 테스트...")
        auth_result = authenticate_user(db, "admin@test.com", "admin123")
        if auth_result:
            print(f"✅ 인증 성공: {auth_result.email}")
        else:
            print("❌ 인증 실패")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Auth 함수 테스트 실패: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def test_dependency_injection():
    """FastAPI 의존성 주입 테스트"""
    
    print("\n=== 의존성 주입 테스트 ===")
    
    try:
        # get_db 제너레이터 테스트
        db_gen = get_db()
        db = next(db_gen)
        
        print("✅ get_db() 제너레이터 성공")
        
        # 간단한 쿼리 실행
        user_count = db.query(User).count()
        print(f"📊 사용자 수: {user_count}")
        
        # 제너레이터 종료
        try:
            next(db_gen)
        except StopIteration:
            print("✅ 제너레이터 정상 종료")
        
        return True
        
    except Exception as e:
        print(f"❌ 의존성 주입 테스트 실패: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def main():
    """메인 테스트 실행"""
    print("🔍 Auth 시스템 디버깅 시작\n")
    
    results = []
    
    # 1. 데이터베이스 기본 작업 테스트
    results.append(test_database_operations())
    
    # 2. Auth 함수 테스트
    results.append(test_auth_functions())
    
    # 3. 의존성 주입 테스트
    results.append(test_dependency_injection())
    
    print("\n=== 테스트 결과 요약 ===")
    if all(results):
        print("✅ 모든 테스트 성공!")
    else:
        print("❌ 일부 테스트 실패!")
        for i, result in enumerate(results, 1):
            status = "✅" if result else "❌"
            print(f"  테스트 {i}: {status}")

if __name__ == "__main__":
    main() 