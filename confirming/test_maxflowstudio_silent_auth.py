#!/usr/bin/env python3
"""
maxflowstudio Silent Auth 연동 테스트
"""

import requests
import json
from urllib.parse import quote, unquote, parse_qs, urlparse
import time

def test_maxflowstudio_silent_auth():
    print("🚀 maxflowstudio Silent Auth 연동 테스트...")
    
    # 1. MAX Platform에 로그인 (SSO 상태 준비)
    print("\n1️⃣ MAX Platform 로그인 상태 준비...")
    session = requests.Session()
    
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
            print(f"❌ MAX Platform 로그인 실패: {login_response.text}")
            return
            
        print("✅ MAX Platform 로그인 성공")
        login_result = login_response.json()
        access_token = login_result.get('access_token')
        
        # 쿠키에도 토큰 설정 (브라우저 환경 시뮬레이션)
        session.cookies.set('access_token', access_token)
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 로그인 요청 실패: {e}")
        return
    
    # 2. maxflowstudio Silent Auth 시뮬레이션
    print("\n2️⃣ maxflowstudio Silent Auth 시뮬레이션...")
    
    # maxflowstudio가 보내는 것과 동일한 파라미터
    silent_auth_params = {
        "response_type": "code",
        "client_id": "maxflowstudio",
        "redirect_uri": "http://localhost:3005/oauth/callback", 
        "scope": "read:profile read:groups manage:workflows",
        "state": "silent_auth_test_" + str(int(time.time())),
        "code_challenge": "silent_test_challenge_" + str(int(time.time())),
        "code_challenge_method": "S256",
        "prompt": "none"  # Silent Auth의 핵심
    }
    
    try:
        start_time = time.time()
        
        response = session.get(
            "http://localhost:8000/api/oauth/authorize",
            params=silent_auth_params,
            allow_redirects=False,
            timeout=5  # maxflowstudio는 5초 타임아웃 사용
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        print(f"응답 시간: {response_time:.2f}초")
        print(f"응답 상태: {response.status_code}")
        
        if response.status_code in [302, 307]:
            location = response.headers.get('location', '')
            print(f"리다이렉트 URL: {location}")
            
            # URL 파싱
            parsed_url = urlparse(location)
            query_params = parse_qs(parsed_url.query)
            
            if 'code' in query_params:
                auth_code = query_params['code'][0]
                state = query_params.get('state', [''])[0]
                
                print(f"🎉 Silent Auth 성공!")
                print(f"  authorization_code: {auth_code[:20]}...")
                print(f"  state: {state}")
                print(f"  응답 속도: {response_time:.2f}초 (빠른 응답)")
                
                # 3. 토큰 교환 시뮬레이션
                print("\n3️⃣ Authorization Code → Access Token 교환 테스트...")
                
                token_data = {
                    "grant_type": "authorization_code",
                    "client_id": "maxflowstudio",
                    "code": auth_code,
                    "redirect_uri": "http://localhost:3005/oauth/callback",
                    "code_verifier": "silent_test_challenge_" + str(int(time.time()))
                }
                
                try:
                    token_response = session.post(
                        "http://localhost:8000/api/oauth/token",
                        data=token_data,
                        timeout=10
                    )
                    
                    print(f"토큰 교환 응답 상태: {token_response.status_code}")
                    
                    if token_response.status_code == 200:
                        token_result = token_response.json()
                        print("🎉 토큰 교환 성공!")
                        print(f"  access_token: {token_result.get('access_token', '')[:20]}...")
                        print(f"  token_type: {token_result.get('token_type', 'N/A')}")
                        print(f"  expires_in: {token_result.get('expires_in', 'N/A')}초")
                        print(f"  scope: {token_result.get('scope', 'N/A')}")
                        
                        print(f"\n✅ 완전한 Silent Auth 플로우 성공!")
                        print(f"   총 소요 시간: {response_time:.2f}초")
                        print(f"   사용자 상호작용: 없음")
                        
                    else:
                        print(f"❌ 토큰 교환 실패: {token_response.text}")
                        
                except requests.exceptions.RequestException as e:
                    print(f"❌ 토큰 교환 요청 실패: {e}")
                
            elif 'error' in query_params:
                error = query_params['error'][0]
                error_description = query_params.get('error_description', [''])[0]
                
                print(f"❌ Silent Auth 실패:")
                print(f"  error: {error}")
                print(f"  error_description: {error_description}")
                
                if error == "login_required":
                    print("ℹ️ 이는 MAX Platform에 로그인되지 않았을 때 정상적인 응답입니다")
                    
        else:
            print(f"❌ 예상치 못한 응답: {response.status_code}")
            print(f"응답 내용: {response.text[:200]}...")
            
    except requests.exceptions.Timeout:
        print("❌ Silent Auth 타임아웃 (5초)")
        print("ℹ️ maxflowstudio는 타임아웃 시 수동 로그인으로 fallback")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Silent Auth 요청 실패: {e}")
    
    # 4. 미인증 상태 테스트 (다른 세션)
    print("\n4️⃣ 미인증 상태에서 Silent Auth 테스트...")
    
    unauthenticated_session = requests.Session()
    
    try:
        response = unauthenticated_session.get(
            "http://localhost:8000/api/oauth/authorize",
            params=silent_auth_params,
            allow_redirects=False,
            timeout=5
        )
        
        print(f"미인증 응답 상태: {response.status_code}")
        
        if response.status_code in [302, 307]:
            location = response.headers.get('location', '')
            parsed_url = urlparse(location)
            query_params = parse_qs(parsed_url.query)
            
            if 'error' in query_params and query_params['error'][0] == 'login_required':
                print("✅ 미인증 상태에서 올바른 login_required 에러 반환")
            else:
                print(f"❌ 예상하지 못한 응답: {location}")
                
    except requests.exceptions.RequestException as e:
        print(f"❌ 미인증 테스트 실패: {e}")
    
    print("\n" + "="*60)
    print("📊 maxflowstudio Silent Auth 연동 테스트 완료")
    print("="*60)
    print("🎯 기대 결과:")
    print("  ✅ MAX Platform 로그인 상태: 자동 로그인 성공 (2-3초)")
    print("  ✅ MAX Platform 미로그인: login_required 에러 (즉시)")
    print("  ✅ 사용자 상호작용 없음")
    print("  ✅ maxflowstudio에서 빠른 fallback 가능")

if __name__ == "__main__":
    test_maxflowstudio_silent_auth()