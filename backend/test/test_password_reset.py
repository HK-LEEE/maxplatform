#!/usr/bin/env python3
"""
비밀번호 재설정 기능 테스트 스크립트
"""

import requests
import json

# 설정
BASE_URL = "http://localhost:8000"
ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "admin123"

def test_password_reset():
    """비밀번호 재설정 기능 테스트"""
    session = requests.Session()
    
    try:
        print("🧪 비밀번호 재설정 기능 테스트 시작")
        
        # 1. 관리자 로그인
        print("🔐 관리자 로그인 중...")
        login_data = {
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
        
        response = session.post(f"{BASE_URL}/api/auth/login", json=login_data)
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            session.headers.update({"Authorization": f"Bearer {token}"})
            print("  ✅ 로그인 성공")
        else:
            print(f"  ❌ 로그인 실패: {response.status_code}")
            print(f"     응답: {response.text}")
            return
        
        # 2. 사용자 목록 조회
        print("\n👥 사용자 목록 조회 중...")
        response = session.get(f"{BASE_URL}/admin/users")
        if response.status_code == 200:
            users = response.json()
            print(f"  ✅ {len(users)}명의 사용자 조회됨")
            
            # 첫 번째 사용자(관리자가 아닌) 선택
            target_user = None
            for user in users:
                if user['email'] != ADMIN_EMAIL:
                    target_user = user
                    break
            
            if not target_user and users:
                target_user = users[0]  # 다른 사용자가 없으면 관리자 자신 사용
                
            if target_user:
                print(f"  📋 테스트 대상 사용자: {target_user['real_name']} ({target_user['email']})")
                
                # 3. 비밀번호 재설정 테스트
                print("\n🔑 비밀번호 재설정 테스트...")
                reset_data = {
                    "user_id": target_user['id'],
                    "new_password": "newpassword123"
                }
                
                response = session.post(f"{BASE_URL}/admin/users/change-password", json=reset_data)
                if response.status_code == 200:
                    print("  ✅ 비밀번호 재설정 성공!")
                    print(f"     새 비밀번호: {reset_data['new_password']}")
                    
                    # 4. 새 비밀번호로 로그인 테스트
                    print("\n🔓 새 비밀번호로 로그인 테스트...")
                    test_session = requests.Session()
                    
                    login_test_data = {
                        "email": target_user['email'],
                        "password": reset_data['new_password']
                    }
                    
                    response = test_session.post(f"{BASE_URL}/api/auth/login", json=login_test_data)
                    if response.status_code == 200:
                        print("  ✅ 새 비밀번호로 로그인 성공!")
                        
                        # 5. 다시 원래 비밀번호로 복구 (관리자가 아닌 경우)
                        if target_user['email'] != ADMIN_EMAIL:
                            print("\n🔄 원래 비밀번호로 복구...")
                            restore_data = {
                                "user_id": target_user['id'],
                                "new_password": "user123"  # 기본 비밀번호
                            }
                            
                            response = session.post(f"{BASE_URL}/admin/users/change-password", json=restore_data)
                            if response.status_code == 200:
                                print("  ✅ 원래 비밀번호로 복구 완료")
                            else:
                                print(f"  ⚠️ 복구 실패: {response.status_code}")
                        
                    else:
                        print(f"  ❌ 새 비밀번호로 로그인 실패: {response.status_code}")
                        print(f"     응답: {response.text}")
                        
                else:
                    print(f"  ❌ 비밀번호 재설정 실패: {response.status_code}")
                    print(f"     응답: {response.text}")
            else:
                print("  ⚠️ 테스트할 사용자가 없습니다.")
        else:
            print(f"  ❌ 사용자 목록 조회 실패: {response.status_code}")
            print(f"     응답: {response.text}")
            
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
    
    print("\n🏁 비밀번호 재설정 테스트 완료")

if __name__ == "__main__":
    test_password_reset() 