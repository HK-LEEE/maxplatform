#!/usr/bin/env python3
"""
워크스페이스 API 테스트 스크립트
"""

import requests
import json

def test_workspace_api():
    """워크스페이스 API 테스트"""
    base_url = "http://localhost:8000"
    
    try:
        # 1. 로그인
        print("🔐 로그인 중...")
        login_data = {
            "email": "admin@jupyter-platform.com",
            "password": "admin123"
        }
        
        login_response = requests.post(
            f"{base_url}/api/auth/login",
            json=login_data
        )
        
        if login_response.status_code != 200:
            print(f"❌ 로그인 실패: {login_response.status_code}")
            print(f"Response: {login_response.text}")
            return
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ 로그인 성공!")
        
        # 2. 워크스페이스 목록 조회
        print("📁 워크스페이스 목록 조회 중...")
        workspace_response = requests.get(
            f"{base_url}/api/workspaces/",
            headers=headers
        )
        
        print(f"Status Code: {workspace_response.status_code}")
        print(f"Response: {workspace_response.text}")
        
        if workspace_response.status_code == 200:
            workspaces = workspace_response.json()
            print(f"✅ 워크스페이스 {len(workspaces)}개 조회 성공!")
            for ws in workspaces:
                print(f"  - {ws['name']}: {ws['description']}")
        else:
            print(f"❌ 워크스페이스 조회 실패: {workspace_response.status_code}")
        
    except Exception as e:
        print(f"💥 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_workspace_api() 