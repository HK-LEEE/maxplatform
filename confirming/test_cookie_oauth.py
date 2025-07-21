#!/usr/bin/env python3
"""
쿠키 기반 OAuth 테스트 스크립트
"""

import requests
import json
from urllib.parse import quote, unquote
import time

def test_cookie_oauth_flow():
    print("🚀 쿠키 기반 OAuth 플로우 테스트 시작...")
    
    # 세션 생성하여 쿠키 유지
    session = requests.Session()
    
    # 1. 로그인
    print("1️⃣ 로그인 시도...")
    login_data = {
        "email": "admin@test.com",
        "password": "admin123"
    }
    
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
    print(f"액세스 토큰: {access_token[:50]}...")
    
    # 2. 수동으로 쿠키 설정 (프론트엔드에서 설정한 것처럼)
    session.cookies.set('access_token', access_token)
    print("🍪 쿠키에 access_token 설정 완료")
    
    # 3. 쿠키 기반으로 OAuth authorize 요청
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
    
    print("🔍 쿠키 기반 OAuth authorize 요청...")
    
    oauth_response = session.get(
        "http://localhost:8000/api/oauth/authorize",
        params=oauth_params,
        allow_redirects=False,
        timeout=10
    )
    
    print(f"OAuth 응답 상태: {oauth_response.status_code}")
    
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
                    
                    # authorization code 추출
                    if "'code': '" in html_content:
                        start = html_content.find("'code': '") + 9
                        end = html_content.find("'", start)
                        auth_code = html_content[start:end]
                        print(f"🔑 Authorization Code: {auth_code}")
                        print("🎉 쿠키 기반 OAuth 성공!")
                    else:
                        print("❌ Authorization code 없음")
                else:
                    print("❌ OAUTH_SUCCESS 메시지 없음")
            else:
                print("❌ PostMessage 스크립트 없음")
                print(f"HTML 내용 (처음 500자): {html_content[:500]}")
    
    elif oauth_response.status_code in [302, 307]:
        # 여전히 리다이렉트되는 경우
        location = oauth_response.headers.get('location', '')
        print(f"❌ 여전히 리다이렉트됨: {location}")
        
        if 'oauth_return' in location:
            print("❌ 여전히 로그인 페이지로 리다이렉트 (쿠키 인증 실패)")
        else:
            print("🔄 다른 위치로 리다이렉트")
    
    else:
        print(f"❌ 예상치 못한 응답: {oauth_response.status_code}")
        print(f"응답 내용: {oauth_response.text[:200]}...")
    
    # 4. 쿠키 상태 확인
    print("\n4️⃣ 쿠키 상태 확인...")
    print(f"세션 쿠키: {dict(session.cookies)}")
    
    print("\n" + "="*50)
    print("📊 쿠키 기반 OAuth 테스트 완료")
    print("="*50)

if __name__ == "__main__":
    test_cookie_oauth_flow()