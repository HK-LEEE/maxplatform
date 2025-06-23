#!/usr/bin/env python3
"""
기능 API 테스트 스크립트
"""

import requests
import json

# 설정
BASE_URL = "http://localhost:8000"
ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "admin123"

def test_features_api():
    """기능 API 테스트"""
    session = requests.Session()
    
    try:
        # 1. 로그인
        print("🔐 관리자 로그인 중...")
        login_data = {
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
        
        response = session.post(f"{BASE_URL}/api/auth/login", json=login_data)
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            session.headers.update({"Authorization": f"Bearer {token}"})
            print("  ✅ 로그인 성공")
        else:
            print(f"  ❌ 로그인 실패: {response.status_code}")
            return
        
        # 2. 기능 목록 조회
        print("\n📋 기능 목록 조회 중...")
        response = session.get(f"{BASE_URL}/admin/features")
        
        if response.status_code == 200:
            features = response.json()
            print(f"  ✅ {len(features)}개 기능 조회됨")
            
            if features:
                print("\n📂 현재 기능 목록:")
                # 카테고리별로 그룹화
                categories = {}
                for feature in features:
                    category_name = feature.get("category_name", "미분류")
                    if category_name not in categories:
                        categories[category_name] = []
                    categories[category_name].append(feature)
                
                for category_name, category_features in categories.items():
                    print(f"\n📁 {category_name}")
                    for feature in category_features:
                        approval_text = " (승인 필요)" if feature.get("requires_approval") else ""
                        print(f"  • {feature['display_name']}{approval_text}")
                        if feature.get("url_path"):
                            print(f"    URL: {feature['url_path']}")
            else:
                print("  ⚠️ 기능이 없습니다.")
            
            return True
        else:
            print(f"  ❌ 기능 목록 조회 실패: {response.status_code}")
            print(f"     응답: {response.text}")
            return False
            
        # 3. 카테고리 목록 조회
        print("\n📂 카테고리 목록 조회 중...")
        response = session.get(f"{BASE_URL}/admin/feature-categories")
        
        if response.status_code == 200:
            categories = response.json()
            print(f"  ✅ {len(categories)}개 카테고리 조회됨")
            
            if categories:
                print("\n📁 카테고리 목록:")
                for category in sorted(categories, key=lambda x: x.get('sort_order', 0)):
                    print(f"  • {category.get('icon', '📁')} {category['display_name']}")
        else:
            print(f"  ❌ 카테고리 조회 실패: {response.status_code}")
    
    except requests.exceptions.ConnectionError:
        print("❌ 백엔드 서버에 연결할 수 없습니다.")
        print(f"   서버가 {BASE_URL}에서 실행 중인지 확인해주세요.")
        return False
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {str(e)}")
        return False

if __name__ == "__main__":
    print("🧪 기능 API 테스트 시작\n")
    if test_features_api():
        print(f"\n✅ 테스트 완료!")
        print(f"\n🔧 관리자 페이지 접근:")
        print(f"  • URL: {BASE_URL}/admin")
        print(f"  • 기능 관리: {BASE_URL}/admin/features")
    else:
        print(f"\n❌ 테스트 실패") 