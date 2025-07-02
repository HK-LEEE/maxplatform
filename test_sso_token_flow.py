#!/usr/bin/env python3
"""
대시보드 → maxflowstudio SSO 토큰 방식 테스트
"""

import requests
import json
from urllib.parse import quote, unquote, parse_qs, urlparse
import time

def test_sso_token_flow():
    print("🚀 대시보드 → maxflowstudio SSO 토큰 방식 테스트...")
    
    # 1. MAX Platform 로그인
    print("\n1️⃣ MAX Platform 로그인...")
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
            print(f"❌ 로그인 실패: {login_response.text}")
            return
            
        print("✅ MAX Platform 로그인 성공")
        login_result = login_response.json()
        access_token = login_result.get('access_token')
        print(f"액세스 토큰: {access_token[:30]}...")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 로그인 요청 실패: {e}")
        return
    
    # 2. 대시보드에서 maxflowstudio로 이동 시뮬레이션
    print("\n2️⃣ 대시보드 → maxflowstudio 이동 시뮬레이션...")
    
    # maxflowstudio URL (기능관리에서 설정된 것)
    target_url = "http://localhost:3005/"
    
    # SSO 토큰 방식으로 URL 생성 (대시보드 로직 시뮬레이션)
    sso_url = f"{target_url}?sso_token={quote(access_token)}"
    print(f"생성된 SSO URL: {sso_url[:80]}...")
    
    # 3. maxflowstudio 접속 시뮬레이션
    print("\n3️⃣ maxflowstudio SSO 토큰 처리 테스트...")
    
    try:
        # maxflowstudio에 SSO 토큰과 함께 접속
        response = requests.get(sso_url, timeout=10, allow_redirects=False)
        
        print(f"maxflowstudio 응답 상태: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ maxflowstudio 정상 응답")
            content_type = response.headers.get('content-type', '')
            print(f"Content-Type: {content_type}")
            
            # HTML 응답인 경우 페이지 로드 성공
            if 'text/html' in content_type:
                print("✅ maxflowstudio 페이지 로드 성공")
            else:
                print(f"ℹ️ 응답 타입: {content_type}")
                
        elif response.status_code in [302, 307]:
            # 리다이렉트가 발생한 경우
            location = response.headers.get('location', '')
            print(f"리다이렉트 URL: {location}")
            
            # OAuth 콜백으로 리다이렉트되는지 확인
            if 'oauth/callback' in location:
                print("❌ 여전히 OAuth 플로우로 리다이렉트됨")
                print("⚠️ 프론트엔드 캐시 또는 브라우저 새로고침 필요")
            else:
                print("ℹ️ 다른 페이지로 리다이렉트")
                
        else:
            print(f"❌ 예상치 못한 응답: {response.status_code}")
            print(f"응답 내용: {response.text[:200]}...")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ maxflowstudio 접속 실패: {e}")
    
    # 4. OAuth 플로우 비활성화 확인
    print("\n4️⃣ OAuth 플로우 비활성화 확인...")
    
    # MAX Platform에서 maxflowstudio가 OAuth 지원 플랫폼으로 인식되지 않는지 확인
    test_oauth_params = {
        "response_type": "code",
        "client_id": "maxflowstudio",
        "redirect_uri": "http://localhost:3005/oauth/callback",
        "scope": "read:profile",
        "state": "test_state",
        "code_challenge": "test_challenge",
        "code_challenge_method": "S256"
    }
    
    try:
        oauth_response = session.get(
            "http://localhost:8000/api/oauth/authorize",
            params=test_oauth_params,
            allow_redirects=False,
            timeout=10
        )
        
        print(f"OAuth 엔드포인트 응답 상태: {oauth_response.status_code}")
        
        if oauth_response.status_code == 400:
            print("✅ maxflowstudio OAuth 클라이언트 비활성화 확인")
            print("   (Invalid client_id 에러 예상됨)")
        else:
            print(f"⚠️ 예상치 못한 OAuth 응답: {oauth_response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ OAuth 테스트 실패: {e}")
    
    print("\n" + "="*60)
    print("📊 SSO 토큰 방식 테스트 완료")
    print("="*60)
    print("🎯 예상 결과:")
    print("  ✅ maxflowstudio OAuth 설정 제거됨")
    print("  ✅ 대시보드 → maxflowstudio SSO 토큰 방식 사용")
    print("  ✅ OAuth 콜백 URL로 리다이렉트되지 않음")
    print("  ✅ 직접 maxflowstudio 페이지 접속")
    print("\n💡 추가 확인 사항:")
    print("  - 브라우저 캐시 클리어 후 대시보드 테스트")
    print("  - maxflowstudio에서 SSO 토큰 자동 처리 확인")

if __name__ == "__main__":
    test_sso_token_flow()