#!/usr/bin/env python3
"""
prompt=none 파라미터 테스트 스크립트
"""

import requests
import json
from urllib.parse import quote, unquote, parse_qs, urlparse
import time

def test_prompt_none():
    print("🚀 prompt=none 파라미터 테스트 시작...")
    
    # 세션 생성하여 쿠키 유지
    session = requests.Session()
    
    # 테스트 1: 미인증 상태에서 prompt=none
    print("\n1️⃣ 미인증 상태에서 prompt=none 테스트...")
    oauth_params = {
        "response_type": "code",
        "client_id": "maxflowstudio",
        "redirect_uri": "http://localhost:3005/oauth/callback",
        "scope": "read:profile read:groups manage:workflows",
        "state": "test_state_prompt_none",
        "code_challenge": "test_challenge_123",
        "code_challenge_method": "S256",
        "prompt": "none"  # 핵심 파라미터
    }
    
    try:
        response = session.get(
            "http://localhost:8000/api/oauth/authorize",
            params=oauth_params,
            allow_redirects=False,
            timeout=10
        )
        
        print(f"응답 상태: {response.status_code}")
        
        if response.status_code in [302, 307]:
            location = response.headers.get('location', '')
            print(f"리다이렉트 URL: {location}")
            
            # URL 파싱하여 에러 확인
            parsed_url = urlparse(location)
            query_params = parse_qs(parsed_url.query)
            
            if 'error' in query_params:
                error = query_params['error'][0]
                error_description = query_params.get('error_description', [''])[0]
                state = query_params.get('state', [''])[0]
                
                print(f"✅ 예상된 에러 응답:")
                print(f"  error: {error}")
                print(f"  error_description: {error_description}")
                print(f"  state: {state}")
                
                if error == "login_required":
                    print("✅ prompt=none 미인증 처리 정상 작동")
                else:
                    print(f"❌ 예상하지 못한 에러: {error}")
            else:
                print("❌ 에러 파라미터가 없음")
        else:
            print(f"❌ 예상치 못한 응답 상태: {response.status_code}")
            print(f"응답 내용: {response.text[:200]}...")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 요청 실패: {e}")
    
    # 테스트 2: 인증된 상태에서 prompt=none
    print("\n2️⃣ 인증된 상태에서 prompt=none 테스트...")
    
    # 먼저 로그인
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
        
        if login_response.status_code != 200:
            print(f"❌ 로그인 실패: {login_response.text}")
            return
        
        print("✅ 로그인 성공")
        login_result = login_response.json()
        access_token = login_result.get('access_token')
        
        # 쿠키에도 토큰 설정
        session.cookies.set('access_token', access_token)
        
        # 인증된 상태에서 prompt=none 요청
        response = session.get(
            "http://localhost:8000/api/oauth/authorize",
            params=oauth_params,
            allow_redirects=False,
            timeout=10
        )
        
        print(f"인증된 상태 응답 상태: {response.status_code}")
        
        if response.status_code in [302, 307]:
            location = response.headers.get('location', '')
            print(f"리다이렉트 URL: {location}")
            
            # URL 파싱하여 authorization code 확인
            parsed_url = urlparse(location)
            query_params = parse_qs(parsed_url.query)
            
            if 'code' in query_params:
                auth_code = query_params['code'][0]
                state = query_params.get('state', [''])[0]
                
                print(f"✅ prompt=none 인증 성공:")
                print(f"  authorization_code: {auth_code}")
                print(f"  state: {state}")
                print("✅ prompt=none 인증된 사용자 처리 정상 작동")
                
            elif 'error' in query_params:
                error = query_params['error'][0]
                error_description = query_params.get('error_description', [''])[0]
                print(f"❌ 인증된 상태에서도 에러 발생:")
                print(f"  error: {error}")
                print(f"  error_description: {error_description}")
            else:
                print("❌ authorization code도 error도 없음")
                
        elif response.status_code == 200:
            print("❌ 리다이렉트 대신 200 응답 (예상하지 못함)")
            print(f"응답 내용: {response.text[:200]}...")
        else:
            print(f"❌ 예상치 못한 응답 상태: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 인증 테스트 실패: {e}")
    
    # 테스트 3: 일반 플로우와 비교 (prompt 없음)
    print("\n3️⃣ 일반 플로우 비교 테스트 (prompt 파라미터 없음)...")
    
    normal_params = oauth_params.copy()
    del normal_params['prompt']  # prompt 파라미터 제거
    
    try:
        response = session.get(
            "http://localhost:8000/api/oauth/authorize",
            params=normal_params,
            allow_redirects=False,
            timeout=10
        )
        
        print(f"일반 플로우 응답 상태: {response.status_code}")
        
        if response.status_code in [302, 307]:
            location = response.headers.get('location', '')
            print(f"리다이렉트 URL: {location}")
            
            if 'code=' in location:
                print("✅ 일반 플로우도 정상 작동 (authorization code 발급)")
            else:
                print("ℹ️ 일반 플로우는 다른 처리 (로그인 페이지 등)")
                
    except requests.exceptions.RequestException as e:
        print(f"❌ 일반 플로우 테스트 실패: {e}")
    
    print("\n" + "="*60)
    print("📊 prompt=none 테스트 완료")
    print("="*60)
    print("✅ 정상 작동 시:")
    print("  - 미인증: login_required 에러")
    print("  - 인증됨: 즉시 authorization code 발급")
    print("  - 사용자 상호작용 없음")

if __name__ == "__main__":
    test_prompt_none()