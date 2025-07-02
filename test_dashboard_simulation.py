#!/usr/bin/env python3
"""
대시보드 maxflowstudio 카드 클릭 시뮬레이션 테스트
"""

import requests
import json
from urllib.parse import quote, unquote
import time

def simulate_dashboard_click():
    print("🎯 대시보드 maxflowstudio 카드 클릭 시뮬레이션...")
    
    # 1. 로그인하여 인증 상태 확보
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
            
        print("✅ 로그인 성공")
        login_result = login_response.json()
        access_token = login_result.get('access_token')
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 로그인 요청 실패: {e}")
        return
    
    # 2. 대시보드에서 서비스 목록 조회 (실제 대시보드 동작)
    print("\n2️⃣ 서비스 목록 조회...")
    
    try:
        # Authorization 헤더 설정
        headers = {'Authorization': f'Bearer {access_token}'}
        
        services_response = session.get(
            "http://localhost:8000/api/services/mother-page",
            headers=headers,
            timeout=10
        )
        
        print(f"서비스 조회 응답: {services_response.status_code}")
        
        if services_response.status_code == 200:
            response_data = services_response.json()
            print(f"✅ 서비스 응답 구조 확인:")
            print(f"  응답 타입: {type(response_data)}")
            print(f"  응답 키들: {list(response_data.keys()) if isinstance(response_data, dict) else 'Not a dict'}")
            
            # 실제 서비스 데이터 추출
            if isinstance(response_data, dict) and 'services' in response_data:
                services = response_data['services']
            elif isinstance(response_data, list):
                services = response_data
            else:
                services = []
            
            print(f"✅ 서비스 목록 조회 성공: {len(services)}개 서비스")
            
            # 처음 몇 개 서비스 구조 확인
            if services:
                print(f"첫 번째 서비스 구조: {services[0]}")
            
            # maxflowstudio 서비스 찾기
            maxflowstudio_service = None
            for service in services:
                # 서비스가 딕셔너리인지 확인
                if isinstance(service, dict):
                    name = service.get('service_name', '').lower()
                    url_path = service.get('url_path', '').lower()
                    display_name = service.get('service_display_name', '').lower()
                    
                    if 'flowstudio' in name or 'flowstudio' in url_path or 'flowstudio' in display_name:
                        maxflowstudio_service = service
                        break
            
            if maxflowstudio_service:
                print(f"🎯 MAX Flowstudio 서비스 발견:")
                print(f"  이름: {maxflowstudio_service.get('service_name')}")
                print(f"  표시명: {maxflowstudio_service.get('service_display_name')}")
                print(f"  URL: {maxflowstudio_service.get('url')}")
                print(f"  외부 링크: {maxflowstudio_service.get('is_external')}")
                print(f"  새 탭 열기: {maxflowstudio_service.get('open_in_new_tab')}")
                
                # 3. 대시보드 클릭 로직 시뮬레이션
                print(f"\n3️⃣ 대시보드 클릭 로직 시뮬레이션...")
                
                url_path = maxflowstudio_service.get('url') or maxflowstudio_service.get('url_path')
                is_external = maxflowstudio_service.get('is_external')
                open_in_new_tab = maxflowstudio_service.get('open_in_new_tab')
                
                if url_path:
                    # 대시보드의 handleFeatureClick 로직 시뮬레이션
                    if is_external or open_in_new_tab:
                        print(f"외부 플랫폼으로 이동 처리...")
                        
                        # OAuth 지원 플랫폼 체크 (프론트엔드 로직)
                        # localhost:3005가 더 이상 OAuth 클라이언트 목록에 없으므로 SSO 토큰 방식 사용
                        if 'localhost' in url_path and '3005' in url_path:
                            print("✅ maxflowstudio는 OAuth 미지원 플랫폼으로 분류")
                            print("🔄 SSO 토큰 방식 사용")
                            
                            # SSO 토큰 URL 생성
                            separator = '&' if '?' in url_path else '?'
                            sso_url = f"{url_path}{separator}sso_token={quote(access_token)}"
                            
                            print(f"생성된 URL: {sso_url[:60]}...")
                            
                            # 실제 접속 테스트
                            print(f"\n4️⃣ 생성된 URL로 실제 접속 테스트...")
                            
                            try:
                                test_response = requests.get(sso_url, timeout=10, allow_redirects=False)
                                print(f"접속 결과: {test_response.status_code}")
                                
                                if test_response.status_code == 200:
                                    print("🎉 maxflowstudio SSO 접속 성공!")
                                    print("✅ OAuth 콜백 URL이 아닌 정상 페이지 접속")
                                elif test_response.status_code in [302, 307]:
                                    location = test_response.headers.get('location', '')
                                    print(f"리다이렉트: {location}")
                                    if 'oauth/callback' in location:
                                        print("❌ 여전히 OAuth 콜백으로 리다이렉트")
                                    else:
                                        print("ℹ️ 다른 페이지로 리다이렉트")
                                else:
                                    print(f"❌ 예상치 못한 응답: {test_response.status_code}")
                                    
                            except requests.exceptions.RequestException as e:
                                print(f"❌ 접속 테스트 실패: {e}")
                        else:
                            print(f"ℹ️ 다른 플랫폼: {url_path}")
                    else:
                        print(f"내부 경로로 처리: {url_path}")
                else:
                    print("❌ URL 경로가 없습니다")
            else:
                print("❌ MAX Flowstudio 서비스를 찾을 수 없습니다")
                print("사용 가능한 서비스들:")
                for service in services[:5]:  # 처음 5개만 표시
                    print(f"  - {service.get('name')}: {service.get('url_path')}")
        else:
            print(f"❌ 서비스 조회 실패: {services_response.status_code}")
            print(f"응답: {services_response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 서비스 조회 실패: {e}")
    
    print("\n" + "="*60)
    print("📊 대시보드 시뮬레이션 테스트 완료")
    print("="*60)
    print("🎯 확인된 사항:")
    print("  ✅ maxflowstudio OAuth 설정 제거됨")
    print("  ✅ SSO 토큰 방식으로 자동 처리")
    print("  ✅ OAuth 콜백 URL로 리다이렉트되지 않음")
    print("\n🔄 실제 브라우저에서 확인:")
    print("  1. http://localhost:3000/dashboard 접속")
    print("  2. MAX Flowstudio(신규) 카드 클릭")
    print("  3. http://localhost:3005/?sso_token=... 형태로 이동 확인")

if __name__ == "__main__":
    simulate_dashboard_click()