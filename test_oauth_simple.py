#!/usr/bin/env python3
"""
간단한 OAuth 테스트 스크립트
"""

import requests
import json
from urllib.parse import quote, unquote
import time

def test_oauth_flow():
    print("🚀 OAuth 플로우 테스트 시작...")
    
    # 1. MAX Platform 백엔드 상태 확인
    try:
        response = requests.get("http://localhost:8000/api/auth/me", timeout=5)
        print(f"✅ MAX Platform 백엔드 상태: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ MAX Platform 백엔드 연결 실패: {e}")
        return
    
    # 2. maxflowstudio 프론트엔드 상태 확인
    try:
        response = requests.get("http://localhost:3005", timeout=5)
        print(f"✅ maxflowstudio 프론트엔드 상태: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ maxflowstudio 프론트엔드 연결 실패: {e}")
        return
    
    # 3. OAuth authorize 엔드포인트 테스트 (미인증 상태)
    oauth_params = {
        "response_type": "code",
        "client_id": "maxflowstudio", 
        "redirect_uri": "http://localhost:3005/oauth/callback",
        "scope": "read:profile read:groups manage:workflows",
        "state": "test_state_123",
        "code_challenge": "test_challenge_123",
        "code_challenge_method": "S256",
        "display": "popup"
    }
    
    print("🔍 OAuth authorize 엔드포인트 테스트...")
    try:
        response = requests.get(
            "http://localhost:8000/api/oauth/authorize",
            params=oauth_params,
            allow_redirects=False,
            timeout=10
        )
        
        print(f"응답 상태: {response.status_code}")
        print(f"응답 헤더: {dict(response.headers)}")
        
        if response.status_code == 302:
            location = response.headers.get('location', '')
            print(f"리다이렉트 URL: {location}")
            
            if 'oauth_return' in location:
                # oauth_return 파라미터 파싱
                oauth_return_start = location.find('oauth_return=') + 13
                oauth_return_end = location.find('&', oauth_return_start)
                if oauth_return_end == -1:
                    oauth_return_end = len(location)
                
                oauth_return_encoded = location[oauth_return_start:oauth_return_end]
                oauth_return_decoded = unquote(oauth_return_encoded)
                
                print(f"🔍 OAuth return 파라미터:")
                print(f"  인코딩됨: {oauth_return_encoded[:100]}...")
                print(f"  디코딩됨: {oauth_return_decoded}")
                
                try:
                    oauth_data = json.loads(oauth_return_decoded)
                    print(f"  파싱된 데이터: {oauth_data}")
                except json.JSONDecodeError as e:
                    print(f"  JSON 파싱 오류: {e}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ OAuth 요청 실패: {e}")
    
    # 4. 로그인 페이지 테스트 (oauth_return 파라미터 포함)
    print("\n🔍 로그인 페이지 OAuth 처리 테스트...")
    
    # 세션 생성하여 로그인 유지
    session = requests.Session()
    
    # 로그인 시도
    login_data = {
        "email": "admin@test.com",
        "password": "admin123"
    }
    
    try:
        login_response = session.post(
            "http://localhost:8000/api/auth/login",
            json=login_data,
            timeout=10
        )
        
        print(f"로그인 응답: {login_response.status_code}")
        
        if login_response.status_code == 200:
            login_result = login_response.json()
            print(f"✅ 로그인 성공: {login_result.get('user', {}).get('email', 'Unknown')}")
            
            # 인증된 상태에서 OAuth 요청 재시도
            print("\n🔍 인증된 상태에서 OAuth 요청...")
            
            oauth_response = session.get(
                "http://localhost:8000/api/oauth/authorize",
                params=oauth_params,
                allow_redirects=False,
                timeout=10
            )
            
            print(f"인증된 OAuth 응답: {oauth_response.status_code}")
            
            if oauth_response.status_code == 200:
                content_type = oauth_response.headers.get('content-type', '')
                print(f"응답 타입: {content_type}")
                
                if 'text/html' in content_type:
                    html_content = oauth_response.text
                    print(f"HTML 응답 길이: {len(html_content)}")
                    
                    # PostMessage 스크립트 확인
                    if 'postMessage' in html_content:
                        print("✅ PostMessage 스크립트 발견")
                        
                        # authorization code 추출 시도
                        if 'OAUTH_SUCCESS' in html_content:
                            print("✅ OAUTH_SUCCESS 메시지 발견")
                        else:
                            print("❌ OAUTH_SUCCESS 메시지 없음")
                    else:
                        print("❌ PostMessage 스크립트 없음")
            
        else:
            print(f"❌ 로그인 실패: {login_response.text}")
    
    except requests.exceptions.RequestException as e:
        print(f"❌ 로그인 요청 실패: {e}")
    
    print("\n" + "="*50)
    print("📊 테스트 완료")
    print("="*50)

if __name__ == "__main__":
    test_oauth_flow()