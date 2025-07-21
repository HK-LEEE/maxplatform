#!/usr/bin/env python3
"""
OAuth 리다이렉트 무한루프 디버깅 스크립트
"""

import requests
import json
from urllib.parse import quote, unquote
import time

def debug_oauth_redirects():
    print("🔍 OAuth 리다이렉트 무한루프 디버깅...")
    
    # 세션 생성하여 쿠키 유지
    session = requests.Session()
    
    # 1. 먼저 로그인
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
    
    # 세션에 Authorization 헤더 추가
    session.headers.update({'Authorization': f'Bearer {access_token}'})
    
    # 2. 사용자 정보 확인
    print("\n2️⃣ 사용자 정보 확인...")
    me_response = session.get("http://localhost:8000/api/auth/me")
    if me_response.status_code == 200:
        user_info = me_response.json()
        print(f"✅ 인증된 사용자: {user_info.get('email')}")
    else:
        print(f"❌ 사용자 정보 조회 실패: {me_response.status_code}")
    
    # 3. OAuth authorize 요청 (여러 번 시도하여 루프 확인)
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
    
    print("\n3️⃣ OAuth authorize 요청 시리즈...")
    
    for i in range(3):
        print(f"\n--- 시도 {i+1} ---")
        
        try:
            oauth_response = session.get(
                "http://localhost:8000/api/oauth/authorize",
                params=oauth_params,
                allow_redirects=False,
                timeout=10
            )
            
            print(f"응답 상태: {oauth_response.status_code}")
            
            if oauth_response.status_code == 200:
                # 성공 응답 분석
                content_type = oauth_response.headers.get('content-type', '')
                content = oauth_response.text
                
                print(f"Content-Type: {content_type}")
                print(f"응답 길이: {len(content)}")
                
                if 'text/html' in content_type:
                    if 'OAUTH_SUCCESS' in content:
                        print("✅ OAUTH_SUCCESS PostMessage HTML 응답")
                        
                        # authorization code 추출
                        if "'code': '" in content:
                            start = content.find("'code': '") + 9
                            end = content.find("'", start)
                            auth_code = content[start:end]
                            print(f"🔑 Authorization Code: {auth_code}")
                        
                        break
                    else:
                        print("❌ 일반 HTML 응답 (PostMessage 없음)")
                elif 'application/json' in content_type:
                    data = oauth_response.json()
                    print(f"📄 JSON 응답: {data}")
                
            elif oauth_response.status_code in [302, 307]:
                # 리다이렉트 응답 분석
                location = oauth_response.headers.get('location', '')
                print(f"🔄 리다이렉트: {location}")
                
                if 'oauth_return' in location:
                    print("❌ 여전히 로그인 페이지로 리다이렉트됨 (무한루프 원인!)")
                    
                    # oauth_return 파라미터 분석
                    oauth_return_start = location.find('oauth_return=') + 13
                    oauth_return_end = location.find('&', oauth_return_start)
                    if oauth_return_end == -1:
                        oauth_return_end = len(location)
                    
                    oauth_return_encoded = location[oauth_return_start:oauth_return_end]
                    oauth_return_decoded = unquote(oauth_return_encoded)
                    
                    print(f"🔍 OAuth return 데이터: {oauth_return_decoded}")
                else:
                    print("🔄 다른 위치로 리다이렉트")
            
            else:
                print(f"❌ 예상치 못한 응답: {oauth_response.status_code}")
                print(f"응답 내용: {oauth_response.text[:200]}...")
        
        except requests.exceptions.RequestException as e:
            print(f"❌ 요청 실패: {e}")
        
        time.sleep(1)  # 1초 대기
    
    # 4. 쿠키 및 헤더 상태 확인
    print("\n4️⃣ 세션 상태 확인...")
    print(f"쿠키: {dict(session.cookies)}")
    print(f"헤더: {dict(session.headers)}")
    
    # 5. 수동으로 OAuth 클라이언트 검증
    print("\n5️⃣ OAuth 클라이언트 검증...")
    try:
        # 클라이언트 정보 조회 (만약 API가 있다면)
        client_response = session.get("http://localhost:8000/api/oauth/clients")
        if client_response.status_code == 200:
            clients = client_response.json()
            print(f"등록된 클라이언트: {len(clients)}")
            for client in clients:
                if client.get('client_id') == 'maxflowstudio':
                    print(f"✅ maxflowstudio 클라이언트 발견: {client}")
                    break
            else:
                print("❌ maxflowstudio 클라이언트 없음")
        else:
            print(f"클라이언트 조회 API 없음: {client_response.status_code}")
    except:
        print("클라이언트 조회 API 없음")
    
    print("\n" + "="*60)
    print("🔍 무한루프 원인 분석 결과")
    print("="*60)
    print("로그인된 상태에서도 OAuth authorize가 로그인 페이지로 리다이렉트됨")
    print("이는 다음 중 하나일 수 있음:")
    print("1. 백엔드에서 인증 상태를 올바르게 감지하지 못함")
    print("2. OAuth 클라이언트 검증 실패")  
    print("3. 권한 검증 로직 문제")
    print("4. 세션/토큰 처리 문제")

if __name__ == "__main__":
    debug_oauth_redirects()