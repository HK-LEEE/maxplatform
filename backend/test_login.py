#!/usr/bin/env python3
"""
로그인 테스트 스크립트
"""

import requests
import json

def test_login():
    """관리자 계정 로그인 테스트"""
    
    # 로그인 데이터
    login_data = {
        "email": "admin@test.com",
        "password": "admin123"
    }
    
    try:
        # 로그인 요청
        print("🔐 로그인 테스트 시작...")
        response = requests.post(
            "http://localhost:8000/api/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"📊 응답 상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ 로그인 성공!")
            
            # 응답 데이터 출력
            response_data = response.json()
            print(f"🔑 Access Token: {response_data.get('access_token', 'N/A')[:50]}...")
            print(f"🔄 Refresh Token: {response_data.get('refresh_token', 'N/A')[:50]}...")
            print(f"👤 사용자 정보: {response_data.get('user', {})}")
            
            return True
            
        else:
            print("❌ 로그인 실패!")
            try:
                error_data = response.json()
                print(f"🔍 에러 내용: {error_data}")
            except:
                print(f"🔍 응답 텍스트: {response.text}")
                
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.")
        return False
        
    except Exception as e:
        print(f"❌ 예상치 못한 오류 발생: {e}")
        return False

if __name__ == "__main__":
    test_login() 