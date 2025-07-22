import requests
import json

# 기본 URL
BASE_URL = "http://localhost:8000"

def test_login():
    """로그인 테스트"""
    url = f"{BASE_URL}/api/auth/login"
    data = {
        "email": "admin@jupyter-platform.com",
        "password": "admin123!"
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"Login Status Code: {response.status_code}")
        print(f"Login Response: {response.text}")
        
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            return None
    except Exception as e:
        print(f"Login Error: {e}")
        return None

def test_workspaces(token):
    """워크스페이스 목록 조회 테스트"""
    url = f"{BASE_URL}/api/workspaces/"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Workspaces Status Code: {response.status_code}")
        print(f"Workspaces Response: {response.text}")
    except Exception as e:
        print(f"Workspaces Error: {e}")

def test_health():
    """헬스 체크 테스트"""
    url = f"{BASE_URL}/health"
    
    try:
        response = requests.get(url)
        print(f"Health Status Code: {response.status_code}")
        print(f"Health Response: {response.text}")
    except Exception as e:
        print(f"Health Error: {e}")

if __name__ == "__main__":
    print("=== API 테스트 시작 ===")
    
    # 헬스 체크
    print("\n1. 헬스 체크:")
    test_health()
    
    # 로그인 테스트
    print("\n2. 로그인 테스트:")
    token = test_login()
    
    # 워크스페이스 테스트
    if token:
        print("\n3. 워크스페이스 테스트:")
        test_workspaces(token)
    else:
        print("\n3. 워크스페이스 테스트: 토큰이 없어서 건너뜀")
    
    print("\n=== API 테스트 완료 ===") 