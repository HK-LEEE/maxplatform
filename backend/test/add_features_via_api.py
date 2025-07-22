#!/usr/bin/env python3
"""
API를 통한 기본 기능 데이터 추가 스크립트

사용법:
python add_features_via_api.py

주의: 백엔드 서버가 실행 중이어야 합니다.
"""

import requests
import json

# 설정
BASE_URL = "http://localhost:8000"
ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "admin123"

class FeatureRestorer:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.token = None
    
    def login(self):
        """관리자 로그인"""
        print("🔐 관리자 로그인 중...")
        
        login_data = {
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
        
        response = self.session.post(
            f"{self.base_url}/api/auth/login",
            json=login_data
        )
        
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            print("  ✅ 로그인 성공")
            return True
        else:
            print(f"  ❌ 로그인 실패: {response.status_code}")
            print(f"     응답: {response.text}")
            return False
    
    def init_basic_data(self):
        """관리자 API를 통한 기본 데이터 초기화"""
        print("📦 기본 데이터 초기화 API 호출 중...")
        
        response = self.session.post(f"{self.base_url}/admin/init-data")
        
        if response.status_code == 200:
            print("  ✅ 기본 데이터 초기화 성공")
            return True
        else:
            print(f"  ❌ 기본 데이터 초기화 실패: {response.status_code}")
            print(f"     응답: {response.text}")
            return False
    
    def get_features(self):
        """현재 기능 목록 조회"""
        print("📋 현재 기능 목록 조회 중...")
        
        response = self.session.get(f"{self.base_url}/admin/features")
        
        if response.status_code == 200:
            features = response.json()
            print(f"  ✅ {len(features)}개 기능 조회됨")
            
            if features:
                print("\n📂 현재 기능 목록:")
                for feature in features:
                    approval_text = " (승인 필요)" if feature.get("requires_approval") else ""
                    category_name = feature.get("category_name", "미분류")
                    print(f"  • [{category_name}] {feature['display_name']}{approval_text}")
            else:
                print("  ⚠️ 기능이 없습니다.")
            
            return features
        else:
            print(f"  ❌ 기능 목록 조회 실패: {response.status_code}")
            print(f"     응답: {response.text}")
            return None
    
    def get_feature_categories(self):
        """기능 카테고리 목록 조회"""
        print("📂 기능 카테고리 조회 중...")
        
        response = self.session.get(f"{self.base_url}/admin/feature-categories")
        
        if response.status_code == 200:
            categories = response.json()
            print(f"  ✅ {len(categories)}개 카테고리 조회됨")
            
            if categories:
                print("\n📁 카테고리 목록:")
                for category in categories:
                    print(f"  • {category['icon']} {category['display_name']}")
            
            return categories
        else:
            print(f"  ❌ 카테고리 조회 실패: {response.status_code}")
            return None

def main():
    """메인 실행 함수"""
    print("🚀 API를 통한 기능 데이터 복구 시작\n")
    
    restorer = FeatureRestorer()
    
    try:
        # 1. 관리자 로그인
        if not restorer.login():
            print("❌ 로그인에 실패했습니다. 관리자 계정을 확인해주세요.")
            return
        print()
        
        # 2. 기본 데이터 초기화
        if restorer.init_basic_data():
            print()
            
            # 3. 결과 확인 - 카테고리
            restorer.get_feature_categories()
            print()
            
            # 4. 결과 확인 - 기능
            restorer.get_features()
            print()
            
            print("✅ 기능 데이터 복구 완료!")
            print(f"\n🔧 관리자 페이지 접근:")
            print(f"  • URL: {BASE_URL}/admin")
            print(f"  • 기능 관리: {BASE_URL}/admin/features")
        else:
            print("❌ 기본 데이터 초기화에 실패했습니다.")
    
    except requests.exceptions.ConnectionError:
        print("❌ 백엔드 서버에 연결할 수 없습니다.")
        print("   다음을 확인해주세요:")
        print(f"   • 백엔드 서버가 {BASE_URL}에서 실행 중인지 확인")
        print("   • 네트워크 연결 상태 확인")
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 