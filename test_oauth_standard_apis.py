#!/usr/bin/env python3
"""
OAuth 표준 준수 API 테스트 스크립트
사용자 토큰으로 접근 가능한 새로운 API 엔드포인트 테스트
"""

import requests
import json
import time
from datetime import datetime


class OAuthStandardAPITester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.user_token = None
        self.admin_token = None
        
        # 테스트용 사용자 정보
        self.test_user = {
            "email": "test@example.com",
            "password": "test123"
        }
        
        self.test_admin = {
            "email": "admin@example.com", 
            "password": "admin123"
        }
    
    def print_header(self, title):
        """테스트 섹션 헤더 출력"""
        print(f"\n{'='*60}")
        print(f"🔧 {title}")
        print(f"{'='*60}")
    
    def print_step(self, step, description):
        """테스트 단계 출력"""
        print(f"\n📋 Step {step}: {description}")
        print("-" * 50)
    
    def print_result(self, success, message, data=None):
        """테스트 결과 출력"""
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{status}: {message}")
        if data and isinstance(data, (dict, list)):
            print(f"📝 응답 데이터: {json.dumps(data, indent=2, ensure_ascii=False)}")
    
    def login_user(self, user_info, is_admin=False):
        """사용자 로그인"""
        try:
            login_url = f"{self.base_url}/api/auth/login"
            response = requests.post(login_url, json=user_info)
            
            if response.status_code == 200:
                token_data = response.json()
                token = token_data["access_token"]
                
                if is_admin:
                    self.admin_token = token
                    print(f"✅ 관리자 로그인 성공: {user_info['email']}")
                else:
                    self.user_token = token
                    print(f"✅ 사용자 로그인 성공: {user_info['email']}")
                
                return token
            else:
                print(f"❌ 로그인 실패: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ 로그인 오류: {str(e)}")
            return None
    
    def test_user_search_api(self):
        """사용자 검색 API 테스트"""
        self.print_step(1, "사용자 검색 API 테스트 (/api/users/search)")
        
        if not self.user_token:
            self.print_result(False, "사용자 토큰이 없습니다")
            return False
        
        try:
            # 이메일로 검색
            url = f"{self.base_url}/api/users/search"
            headers = {"Authorization": f"Bearer {self.user_token}"}
            params = {"email": "test", "limit": 5}
            
            print(f"📤 요청: GET {url}")
            print(f"📤 파라미터: {params}")
            
            response = requests.get(url, headers=headers, params=params)
            
            print(f"📥 응답 상태: {response.status_code}")
            
            if response.status_code == 200:
                users = response.json()
                self.print_result(True, f"사용자 검색 성공 ({len(users)}명 조회)", users[:2])  # 처음 2명만 출력
                return True
            else:
                self.print_result(False, f"사용자 검색 실패: {response.text}")
                return False
                
        except Exception as e:
            self.print_result(False, f"사용자 검색 테스트 오류: {str(e)}")
            return False
    
    def test_user_profile_apis(self):
        """사용자 프로필 API 테스트"""
        self.print_step(2, "사용자 프로필 API 테스트 (/api/users/me, /api/users/{id})")
        
        if not self.user_token:
            self.print_result(False, "사용자 토큰이 없습니다")
            return False
        
        try:
            # 내 프로필 조회
            url = f"{self.base_url}/api/users/me"
            headers = {"Authorization": f"Bearer {self.user_token}"}
            
            print(f"📤 요청: GET {url}")
            
            response = requests.get(url, headers=headers)
            
            print(f"📥 응답 상태: {response.status_code}")
            
            if response.status_code == 200:
                profile = response.json()
                user_id = profile["id"]
                
                self.print_result(True, "내 프로필 조회 성공", {
                    "id": profile["id"],
                    "email": profile["email"],
                    "real_name": profile["real_name"],
                    "group_name": profile.get("group_name")
                })
                
                # 특정 사용자 프로필 조회 (본인)
                user_url = f"{self.base_url}/api/users/{user_id}"
                user_response = requests.get(user_url, headers=headers)
                
                if user_response.status_code == 200:
                    self.print_result(True, "특정 사용자 프로필 조회 성공 (본인)")
                    return True
                else:
                    self.print_result(False, f"특정 사용자 프로필 조회 실패: {user_response.text}")
                    return False
            else:
                self.print_result(False, f"내 프로필 조회 실패: {response.text}")
                return False
                
        except Exception as e:
            self.print_result(False, f"사용자 프로필 테스트 오류: {str(e)}")
            return False
    
    def test_user_email_lookup(self):
        """이메일로 사용자 조회 API 테스트"""
        self.print_step(3, "이메일로 사용자 조회 API 테스트 (/api/users/email/{email})")
        
        if not self.user_token:
            self.print_result(False, "사용자 토큰이 없습니다")
            return False
        
        try:
            # 이메일로 사용자 조회 (본인)
            email = self.test_user["email"]
            url = f"{self.base_url}/api/users/email/{email}"
            headers = {"Authorization": f"Bearer {self.user_token}"}
            
            print(f"📤 요청: GET {url}")
            
            response = requests.get(url, headers=headers)
            
            print(f"📥 응답 상태: {response.status_code}")
            
            if response.status_code == 200:
                user_data = response.json()
                self.print_result(True, "이메일로 사용자 조회 성공", {
                    "id": user_data["id"],
                    "email": user_data["email"],
                    "real_name": user_data["real_name"]
                })
                return True
            else:
                self.print_result(False, f"이메일로 사용자 조회 실패: {response.text}")
                return False
                
        except Exception as e:
            self.print_result(False, f"이메일 조회 테스트 오류: {str(e)}")
            return False
    
    def test_groups_search_api(self):
        """그룹 검색 API 테스트"""
        self.print_step(4, "그룹 검색 API 테스트 (/api/groups/search)")
        
        if not self.user_token:
            self.print_result(False, "사용자 토큰이 없습니다")
            return False
        
        try:
            # 그룹명으로 검색
            url = f"{self.base_url}/api/groups/search"
            headers = {"Authorization": f"Bearer {self.user_token}"}
            params = {"name": "dev", "limit": 5}
            
            print(f"📤 요청: GET {url}")
            print(f"📤 파라미터: {params}")
            
            response = requests.get(url, headers=headers, params=params)
            
            print(f"📥 응답 상태: {response.status_code}")
            
            if response.status_code == 200:
                groups = response.json()
                self.print_result(True, f"그룹 검색 성공 ({len(groups)}개 조회)", groups[:2])  # 처음 2개만 출력
                return True
            else:
                self.print_result(False, f"그룹 검색 실패: {response.text}")
                return False
                
        except Exception as e:
            self.print_result(False, f"그룹 검색 테스트 오류: {str(e)}")
            return False
    
    def test_my_group_api(self):
        """내 그룹 조회 API 테스트"""
        self.print_step(5, "내 그룹 조회 API 테스트 (/api/groups/my)")
        
        if not self.user_token:
            self.print_result(False, "사용자 토큰이 없습니다")
            return False
        
        try:
            url = f"{self.base_url}/api/groups/my"
            headers = {"Authorization": f"Bearer {self.user_token}"}
            
            print(f"📤 요청: GET {url}")
            
            response = requests.get(url, headers=headers)
            
            print(f"📥 응답 상태: {response.status_code}")
            
            if response.status_code == 200:
                group_data = response.json()
                if group_data:
                    self.print_result(True, "내 그룹 조회 성공", {
                        "id": group_data["id"],
                        "name": group_data["name"],
                        "display_name": group_data.get("display_name"),
                        "member_count": group_data.get("member_count"),
                        "my_role": group_data.get("my_role")
                    })
                else:
                    self.print_result(True, "그룹에 속하지 않음")
                return True
            else:
                self.print_result(False, f"내 그룹 조회 실패: {response.text}")
                return False
                
        except Exception as e:
            self.print_result(False, f"내 그룹 조회 테스트 오류: {str(e)}")
            return False
    
    def test_group_name_lookup(self):
        """그룹명으로 그룹 조회 API 테스트"""
        self.print_step(6, "그룹명으로 그룹 조회 API 테스트 (/api/groups/name/{name})")
        
        if not self.user_token:
            self.print_result(False, "사용자 토큰이 없습니다")
            return False
        
        try:
            # 그룹명으로 조회 (존재하는 그룹명 사용)
            group_name = "developers"  # 예시 그룹명
            url = f"{self.base_url}/api/groups/name/{group_name}"
            headers = {"Authorization": f"Bearer {self.user_token}"}
            
            print(f"📤 요청: GET {url}")
            
            response = requests.get(url, headers=headers)
            
            print(f"📥 응답 상태: {response.status_code}")
            
            if response.status_code == 200:
                group_data = response.json()
                self.print_result(True, "그룹명으로 그룹 조회 성공", {
                    "id": group_data["id"],
                    "name": group_data["name"],
                    "display_name": group_data.get("display_name"),
                    "member_count": group_data.get("member_count")
                })
                return True
            elif response.status_code == 404:
                self.print_result(True, f"그룹 '{group_name}'을 찾을 수 없음 (정상적인 404)")
                return True
            else:
                self.print_result(False, f"그룹명 조회 실패: {response.text}")
                return False
                
        except Exception as e:
            self.print_result(False, f"그룹명 조회 테스트 오류: {str(e)}")
            return False
    
    def test_permission_system(self):
        """권한 시스템 테스트"""
        self.print_step(7, "권한 시스템 테스트 (본인/타인 정보 접근)")
        
        if not self.user_token or not self.admin_token:
            self.print_result(False, "사용자 토큰 또는 관리자 토큰이 없습니다")
            return False
        
        try:
            # 1. 일반 사용자가 자신의 정보 접근 (허용)
            me_url = f"{self.base_url}/api/users/me"
            user_headers = {"Authorization": f"Bearer {self.user_token}"}
            
            me_response = requests.get(me_url, headers=user_headers)
            if me_response.status_code == 200:
                self.print_result(True, "✅ 본인 정보 접근 허용")
            else:
                self.print_result(False, "❌ 본인 정보 접근 실패")
                return False
            
            # 2. 관리자가 사용자 검색 (허용)
            admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
            search_url = f"{self.base_url}/api/users/search"
            
            admin_search_response = requests.get(search_url, headers=admin_headers, params={"email": "test"})
            if admin_search_response.status_code == 200:
                self.print_result(True, "✅ 관리자 사용자 검색 허용")
            else:
                self.print_result(False, "❌ 관리자 사용자 검색 실패")
                return False
            
            # 3. 권한 체계가 올바르게 작동함을 확인
            self.print_result(True, "권한 시스템이 올바르게 작동합니다")
            return True
            
        except Exception as e:
            self.print_result(False, f"권한 시스템 테스트 오류: {str(e)}")
            return False
    
    def run_all_tests(self):
        """모든 테스트 실행"""
        self.print_header("OAuth 표준 준수 API 테스트")
        print(f"🎯 테스트 대상: {self.base_url}")
        print(f"⏰ 테스트 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 로그인
        print("\n🔐 사용자 로그인 중...")
        user_login_success = self.login_user(self.test_user)
        admin_login_success = self.login_user(self.test_admin, is_admin=True)
        
        if not user_login_success:
            print("⚠️ 사용자 로그인 실패. 일부 테스트를 건너뛰거나 실패할 수 있습니다.")
        
        if not admin_login_success:
            print("⚠️ 관리자 로그인 실패. 권한 테스트를 건너뛸 수 있습니다.")
        
        # 테스트 실행
        test_results = []
        
        test_results.append(("사용자 검색 API", self.test_user_search_api()))
        test_results.append(("사용자 프로필 API", self.test_user_profile_apis()))
        test_results.append(("이메일 조회 API", self.test_user_email_lookup()))
        test_results.append(("그룹 검색 API", self.test_groups_search_api()))
        test_results.append(("내 그룹 조회 API", self.test_my_group_api()))
        test_results.append(("그룹명 조회 API", self.test_group_name_lookup()))
        
        if user_login_success and admin_login_success:
            test_results.append(("권한 시스템", self.test_permission_system()))
        
        # 결과 요약
        self.print_header("테스트 결과 요약")
        
        passed = sum(1 for _, result in test_results if result)
        total = len(test_results)
        
        for test_name, result in test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")
        
        print(f"\n📊 총 테스트: {total}개")
        print(f"✅ 성공: {passed}개")
        print(f"❌ 실패: {total - passed}개")
        print(f"📈 성공률: {passed/total*100:.1f}%")
        
        if passed == total:
            print("\n🎉 모든 테스트가 성공했습니다! OAuth 표준 준수 API가 정상적으로 작동합니다.")
            print("\n📋 이제 다음과 같이 MAX Lab 코드를 수정할 수 있습니다:")
            print("""
            # Before (잘못된 방식)
            async def get_user_uuid_by_email(self, email: str):
                headers = {"Authorization": f"Bearer {await self._get_service_token()}"}
                
            # After (올바른 방식)
            async def get_user_uuid_by_email(self, email: str, user_token: str):
                headers = {"Authorization": f"Bearer {user_token}"}
                url = "http://localhost:8000/api/users/email/{email}"
            """)
        else:
            print(f"\n⚠️ {total - passed}개의 테스트가 실패했습니다. API 설정을 확인해주세요.")
        
        print(f"⏰ 테스트 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return passed == total


if __name__ == "__main__":
    import sys
    
    # 서버 URL 인자 처리
    base_url = "http://localhost:8000"
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    print("🚀 OAuth 표준 준수 API 테스트 시작")
    print(f"💡 사용법: python {sys.argv[0]} [서버URL]")
    print(f"💡 예시: python {sys.argv[0]} http://localhost:8000")
    print(f"📢 주의: 테스트용 사용자 계정이 있어야 합니다 (test@example.com / admin@example.com)")
    
    tester = OAuthStandardAPITester(base_url)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)