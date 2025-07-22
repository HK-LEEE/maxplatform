#!/usr/bin/env python3
"""
사용자 프로필 API 테스트 스크립트
"""

import requests
import json

# 설정
BASE_URL = "http://localhost:8000"
ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "admin123"

def test_profile_api():
    """사용자 프로필 API 테스트"""
    try:
        print("🧪 사용자 프로필 API 테스트 시작")
        
        # 1. 로그인
        print("🔐 로그인 중...")
        login_data = {
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            print("  ✅ 로그인 성공")
        else:
            print(f"  ❌ 로그인 실패: {response.status_code}")
            print(f"     응답: {response.text}")
            return
        
        # 2. 현재 사용자 정보 조회 (/api/auth/me)
        print("\n👤 현재 사용자 정보 조회 중...")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        if response.status_code == 200:
            user_info = response.json()
            print("  ✅ 사용자 정보 조회 성공!")
            print(f"     ID: {user_info.get('id')}")
            print(f"     이름: {user_info.get('real_name')}")
            print(f"     이메일: {user_info.get('email')}")
            print(f"     관리자: {user_info.get('is_admin')}")
            
            # 3. 비밀번호 변경 테스트 (/api/auth/change-password)
            print("\n🔑 비밀번호 변경 테스트...")
            password_data = {
                "current_password": ADMIN_PASSWORD,
                "new_password": "newadminpass123"
            }
            
            response = requests.post(f"{BASE_URL}/api/auth/change-password", headers=headers, json=password_data)
            if response.status_code == 200:
                print("  ✅ 비밀번호 변경 성공!")
                
                # 4. 새 비밀번호로 로그인 테스트
                print("\n🔓 새 비밀번호로 로그인 테스트...")
                new_login_data = {
                    "email": ADMIN_EMAIL,
                    "password": "newadminpass123"
                }
                
                response = requests.post(f"{BASE_URL}/api/auth/login", json=new_login_data)
                if response.status_code == 200:
                    print("  ✅ 새 비밀번호로 로그인 성공!")
                    
                    # 5. 원래 비밀번호로 복구
                    print("\n🔄 원래 비밀번호로 복구...")
                    new_token = response.json().get("access_token")
                    new_headers = {"Authorization": f"Bearer {new_token}"}
                    
                    restore_data = {
                        "current_password": "newadminpass123",
                        "new_password": ADMIN_PASSWORD
                    }
                    
                    response = requests.post(f"{BASE_URL}/api/auth/change-password", headers=new_headers, json=restore_data)
                    if response.status_code == 200:
                        print("  ✅ 원래 비밀번호로 복구 완료")
                    else:
                        print(f"  ⚠️ 복구 실패: {response.status_code}")
                        print(f"     응답: {response.text}")
                        
                else:
                    print(f"  ❌ 새 비밀번호로 로그인 실패: {response.status_code}")
                    print(f"     응답: {response.text}")
                    
            else:
                print(f"  ❌ 비밀번호 변경 실패: {response.status_code}")
                print(f"     응답: {response.text}")
            
        else:
            print(f"  ❌ 사용자 정보 조회 실패: {response.status_code}")
            print(f"     응답: {response.text}")
            
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
    
    print("\n🏁 사용자 프로필 API 테스트 완료")

if __name__ == "__main__":
    test_profile_api() 