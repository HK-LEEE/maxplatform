#!/usr/bin/env python3
"""
간단한 워크스페이스 API 테스트
"""

import requests

def test_simple():
    """간단한 테스트"""
    base_url = "http://localhost:8000"
    
    # 1. Health check
    print("🏥 Health check...")
    health_response = requests.get(f"{base_url}/api/workspaces/health")
    print(f"Health Status: {health_response.status_code}")
    print(f"Health Response: {health_response.text}")
    
    # 2. 다양한 계정으로 로그인 시도
    accounts = [
        {"email": "admin@jupyter-platform.com", "password": "admin123"},
        {"email": "admin@example.com", "password": "admin123"},
        {"email": "test@example.com", "password": "test123"}
    ]
    
    for account in accounts:
        print(f"\n🔐 로그인 시도: {account['email']}")
        try:
            login_response = requests.post(
                f"{base_url}/api/auth/login",
                json=account
            )
            
            if login_response.status_code == 200:
                token = login_response.json()["access_token"]
                headers = {"Authorization": f"Bearer {token}"}
                print(f"✅ 로그인 성공! Token: {token[:20]}...")
                
                # 워크스페이스 목록 조회
                print("📁 워크스페이스 목록 조회...")
                workspace_response = requests.get(
                    f"{base_url}/api/workspaces/",
                    headers=headers
                )
                
                print(f"Workspace API Status: {workspace_response.status_code}")
                print(f"Workspace Response: {workspace_response.text}")
                
                break  # 성공하면 루프 종료
            else:
                print(f"❌ 로그인 실패: {login_response.status_code}")
                print(f"Response: {login_response.text}")
                
        except Exception as e:
            print(f"💥 오류: {e}")

if __name__ == "__main__":
    test_simple() 