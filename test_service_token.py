#!/usr/bin/env python3
"""
Client Credentials Grant 및 서비스 토큰 테스트 스크립트
MAX Platform의 SERVICE_TOKEN 기능을 테스트합니다.
"""

import requests
import json
import time
from datetime import datetime


class ServiceTokenTester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.service_token = None
        
        # 테스트용 서비스 클라이언트 정보
        self.service_client_id = "maxplatform-service"
        self.service_client_secret = "service_maxplatform_2025_dev_secret"
    
    def print_header(self, title):
        """테스트 섹션 헤더 출력"""
        print(f"\n{'='*60}")
        print(f"🔧 {title}")
        print(f"{'='*60}")
    
    def print_step(self, step, description):
        """테스트 단계 출력"""
        print(f"\n📋 Step {step}: {description}")
        print("-" * 50)
    
    def print_result(self, success, message):
        """테스트 결과 출력"""
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{status}: {message}")
    
    def test_oauth_metadata(self):
        """OAuth metadata에서 client_credentials 지원 확인"""
        self.print_step(1, "OAuth Metadata에서 Client Credentials Grant 지원 확인")
        
        try:
            response = requests.get(f"{self.base_url}/api/oauth/.well-known/oauth-authorization-server")
            
            if response.status_code == 200:
                metadata = response.json()
                supported_grants = metadata.get("grant_types_supported", [])
                
                if "client_credentials" in supported_grants:
                    self.print_result(True, "Client Credentials Grant가 지원됩니다")
                    print(f"📝 지원되는 Grant Types: {supported_grants}")
                    
                    supported_scopes = metadata.get("scopes_supported", [])
                    service_scopes = [s for s in supported_scopes if s.startswith("admin:")]
                    print(f"📝 서비스 스코프: {service_scopes}")
                    return True
                else:
                    self.print_result(False, "Client Credentials Grant가 지원되지 않습니다")
                    return False
            else:
                self.print_result(False, f"OAuth metadata 조회 실패: {response.status_code}")
                return False
                
        except Exception as e:
            self.print_result(False, f"OAuth metadata 테스트 오류: {str(e)}")
            return False
    
    def test_client_credentials_grant(self):
        """Client Credentials Grant로 서비스 토큰 발급 테스트"""
        self.print_step(2, "Client Credentials Grant로 서비스 토큰 발급")
        
        try:
            token_url = f"{self.base_url}/api/oauth/token"
            
            data = {
                "grant_type": "client_credentials",
                "client_id": self.service_client_id,
                "client_secret": self.service_client_secret,
                "scope": "admin:oauth admin:users admin:system"
            }
            
            print(f"📤 요청 URL: {token_url}")
            print(f"📤 요청 데이터: {json.dumps({k: v if k != 'client_secret' else '***' for k, v in data.items()}, indent=2)}")
            
            response = requests.post(token_url, data=data)
            
            print(f"📥 응답 상태: {response.status_code}")
            
            if response.status_code == 200:
                token_data = response.json()
                self.service_token = token_data["access_token"]
                
                self.print_result(True, "서비스 토큰 발급 성공")
                print(f"📝 토큰 타입: {token_data['token_type']}")
                print(f"📝 만료 시간: {token_data['expires_in']}초 ({token_data['expires_in']/3600:.1f}시간)")
                print(f"📝 스코프: {token_data['scope']}")
                print(f"📝 토큰 (처음 20자): {self.service_token[:20]}...")
                
                # 리프레시 토큰이 없는지 확인 (Client Credentials Grant 특징)
                if token_data.get("refresh_token") is None:
                    print("✅ 리프레시 토큰 없음 (Client Credentials Grant 정상 동작)")
                else:
                    print("⚠️ 리프레시 토큰이 반환됨 (예상되지 않음)")
                
                return True
            else:
                error_details = response.text
                self.print_result(False, f"토큰 발급 실패: {response.status_code}")
                print(f"📝 오류 세부사항: {error_details}")
                return False
                
        except Exception as e:
            self.print_result(False, f"토큰 발급 테스트 오류: {str(e)}")
            return False
    
    def test_service_api_access(self):
        """서비스 토큰으로 관리자 API 접근 테스트"""
        self.print_step(3, "서비스 토큰으로 관리자 API 접근")
        
        if not self.service_token:
            self.print_result(False, "서비스 토큰이 없습니다")
            return False
        
        try:
            # 서비스 전용 OAuth 통계 API 테스트
            stats_url = f"{self.base_url}/api/admin/oauth/service/statistics"
            
            headers = {
                "Authorization": f"Bearer {self.service_token}",
                "Content-Type": "application/json"
            }
            
            print(f"📤 요청 URL: {stats_url}")
            print(f"📤 Authorization 헤더: Bearer {self.service_token[:20]}...")
            
            response = requests.get(stats_url, headers=headers)
            
            print(f"📥 응답 상태: {response.status_code}")
            
            if response.status_code == 200:
                stats = response.json()
                self.print_result(True, "서비스 API 접근 성공")
                print(f"📝 전체 클라이언트: {stats['total_clients']}")
                print(f"📝 활성 클라이언트: {stats['active_clients']}")
                print(f"📝 서비스 클라이언트: {stats['service_clients']}")
                print(f"📝 활성 서비스 토큰: {stats['active_service_tokens']}")
                print(f"📝 접근한 서비스: {stats['accessed_by_service']}")
                print(f"📝 서비스 스코프: {stats['service_scopes']}")
                return True
            else:
                error_details = response.text
                self.print_result(False, f"서비스 API 접근 실패: {response.status_code}")
                print(f"📝 오류 세부사항: {error_details}")
                return False
                
        except Exception as e:
            self.print_result(False, f"서비스 API 접근 테스트 오류: {str(e)}")
            return False
    
    def test_oauth_clients_service_api(self):
        """서비스 토큰으로 OAuth 클라이언트 목록 조회 테스트"""
        self.print_step(4, "서비스 토큰으로 OAuth 클라이언트 목록 조회")
        
        if not self.service_token:
            self.print_result(False, "서비스 토큰이 없습니다")
            return False
        
        try:
            clients_url = f"{self.base_url}/api/admin/oauth/service/clients"
            
            headers = {
                "Authorization": f"Bearer {self.service_token}",
                "Content-Type": "application/json"
            }
            
            # 서비스 클라이언트만 필터링해서 조회
            params = {"limit": 10}
            
            print(f"📤 요청 URL: {clients_url}")
            
            response = requests.get(clients_url, headers=headers, params=params)
            
            print(f"📥 응답 상태: {response.status_code}")
            
            if response.status_code == 200:
                clients = response.json()
                self.print_result(True, f"OAuth 클라이언트 목록 조회 성공 ({len(clients)}개)")
                
                for client in clients[:3]:  # 처음 3개만 출력
                    client_type = "서비스" if not client['redirect_uris'] else "웹"
                    print(f"📝 {client['client_id']} ({client_type}) - {client['client_name']}")
                
                return True
            else:
                error_details = response.text
                self.print_result(False, f"클라이언트 목록 조회 실패: {response.status_code}")
                print(f"📝 오류 세부사항: {error_details}")
                return False
                
        except Exception as e:
            self.print_result(False, f"클라이언트 목록 조회 테스트 오류: {str(e)}")
            return False
    
    def test_invalid_service_token(self):
        """잘못된 서비스 토큰으로 접근 테스트"""
        self.print_step(5, "잘못된 서비스 토큰으로 접근 (보안 테스트)")
        
        try:
            stats_url = f"{self.base_url}/api/admin/oauth/service/statistics"
            
            # 잘못된 토큰으로 테스트
            invalid_token = "invalid.token.here"
            headers = {
                "Authorization": f"Bearer {invalid_token}",
                "Content-Type": "application/json"
            }
            
            print(f"📤 요청 URL: {stats_url}")
            print(f"📤 잘못된 토큰: {invalid_token}")
            
            response = requests.get(stats_url, headers=headers)
            
            print(f"📥 응답 상태: {response.status_code}")
            
            if response.status_code == 401:
                self.print_result(True, "잘못된 토큰 접근이 올바르게 차단됨")
                return True
            else:
                self.print_result(False, f"잘못된 토큰 접근이 차단되지 않음: {response.status_code}")
                return False
                
        except Exception as e:
            self.print_result(False, f"보안 테스트 오류: {str(e)}")
            return False
    
    def test_scope_validation(self):
        """스코프 검증 테스트"""
        self.print_step(6, "제한된 스코프로 토큰 발급 및 접근 제한 테스트")
        
        try:
            # 제한된 스코프로 토큰 발급
            token_url = f"{self.base_url}/api/oauth/token"
            
            data = {
                "grant_type": "client_credentials",
                "client_id": self.service_client_id,
                "client_secret": self.service_client_secret,
                "scope": "admin:system"  # admin:oauth 스코프 제외
            }
            
            response = requests.post(token_url, data=data)
            
            if response.status_code == 200:
                limited_token_data = response.json()
                limited_token = limited_token_data["access_token"]
                
                print(f"📝 제한된 스코프 토큰 발급 성공: {limited_token_data['scope']}")
                
                # 이 토큰으로 admin:oauth가 필요한 API 접근 시도
                stats_url = f"{self.base_url}/api/admin/oauth/service/statistics"
                headers = {
                    "Authorization": f"Bearer {limited_token}",
                    "Content-Type": "application/json"
                }
                
                response = requests.get(stats_url, headers=headers)
                
                if response.status_code == 403:
                    self.print_result(True, "스코프 부족으로 접근이 올바르게 차단됨")
                    return True
                else:
                    self.print_result(False, f"스코프 검증이 작동하지 않음: {response.status_code}")
                    return False
            else:
                self.print_result(False, f"제한된 스코프 토큰 발급 실패: {response.status_code}")
                return False
                
        except Exception as e:
            self.print_result(False, f"스코프 검증 테스트 오류: {str(e)}")
            return False
    
    def run_all_tests(self):
        """모든 테스트 실행"""
        self.print_header("MAX Platform SERVICE_TOKEN 테스트")
        print(f"🎯 테스트 대상: {self.base_url}")
        print(f"🔑 서비스 클라이언트: {self.service_client_id}")
        print(f"⏰ 테스트 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        test_results = []
        
        # 각 테스트 실행
        test_results.append(("OAuth Metadata 확인", self.test_oauth_metadata()))
        test_results.append(("서비스 토큰 발급", self.test_client_credentials_grant()))
        test_results.append(("서비스 API 접근", self.test_service_api_access()))
        test_results.append(("OAuth 클라이언트 조회", self.test_oauth_clients_service_api()))
        test_results.append(("보안 테스트", self.test_invalid_service_token()))
        test_results.append(("스코프 검증", self.test_scope_validation()))
        
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
            print("\n🎉 모든 테스트가 성공했습니다! SERVICE_TOKEN 기능이 정상적으로 작동합니다.")
        else:
            print(f"\n⚠️ {total - passed}개의 테스트가 실패했습니다. 설정을 확인해주세요.")
        
        print(f"⏰ 테스트 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return passed == total


if __name__ == "__main__":
    import sys
    
    # 서버 URL 인자 처리
    base_url = "http://localhost:8000"
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    print("🚀 MAX Platform SERVICE_TOKEN 테스트 시작")
    print(f"💡 사용법: python {sys.argv[0]} [서버URL]")
    print(f"💡 예시: python {sys.argv[0]} http://localhost:8000")
    
    tester = ServiceTokenTester(base_url)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)