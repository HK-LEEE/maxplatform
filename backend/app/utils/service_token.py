"""
Service Token Management Utilities
서비스 토큰 자동 생성, 갱신, 관리 기능
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import threading
import time
import os

from ..config import settings
from .auth import verify_service_token

logger = logging.getLogger(__name__)


class ServiceTokenManager:
    """
    서비스 토큰 자동 관리 클래스
    - 토큰 자동 생성
    - 만료 전 자동 갱신
    - 환경변수 지원
    """
    
    def __init__(self):
        self.current_token = None
        self.token_expires_at = None
        self.auto_refresh_enabled = False
        self.refresh_thread = None
        self._lock = threading.Lock()
        
        # 초기 토큰 로드
        self._load_initial_token()
    
    def _load_initial_token(self):
        """환경변수나 새로 생성해서 초기 토큰 로드"""
        # 환경변수에서 SERVICE_TOKEN 확인
        if settings.service_token:
            logger.info("Loading service token from environment variable")
            token_info = verify_service_token(settings.service_token)
            if token_info:
                self.current_token = settings.service_token
                self.token_expires_at = datetime.fromtimestamp(token_info['exp'])
                logger.info(f"Service token loaded, expires at: {self.token_expires_at}")
                return
            else:
                logger.warning("Invalid service token in environment variable, will generate new one")
        
        # 환경변수에 토큰이 없거나 유효하지 않으면 새로 생성
        self._generate_new_token()
    
    def _generate_new_token(self) -> bool:
        """새로운 서비스 토큰 생성"""
        try:
            logger.info(f"Generating new service token for client: {settings.service_client_id}")
            
            # OAuth token endpoint 호출
            token_url = "http://localhost:8000/api/oauth/token"
            
            data = {
                "grant_type": "client_credentials",
                "client_id": settings.service_client_id,
                "client_secret": settings.service_client_secret,
                "scope": "admin:oauth admin:users admin:system"
            }
            
            response = requests.post(token_url, data=data, timeout=10)
            
            if response.status_code == 200:
                token_data = response.json()
                
                with self._lock:
                    self.current_token = token_data["access_token"]
                    expires_in = token_data.get("expires_in", 24 * 3600)  # Default 24 hours
                    self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                
                logger.info(f"Service token generated successfully, expires at: {self.token_expires_at}")
                return True
            else:
                logger.error(f"Failed to generate service token: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error generating service token: {str(e)}")
            return False
    
    def get_token(self) -> Optional[str]:
        """현재 유효한 서비스 토큰 반환"""
        with self._lock:
            if not self.current_token:
                logger.warning("No service token available")
                return None
            
            # 토큰 만료 확인 (5분 여유)
            if self.token_expires_at and datetime.utcnow() >= (self.token_expires_at - timedelta(minutes=5)):
                logger.info("Service token is about to expire, generating new one")
                if self._generate_new_token():
                    return self.current_token
                else:
                    logger.error("Failed to refresh expired service token")
                    return None
            
            return self.current_token
    
    def refresh_token(self) -> bool:
        """토큰 수동 갱신"""
        logger.info("Manually refreshing service token")
        return self._generate_new_token()
    
    def start_auto_refresh(self, check_interval_minutes: int = 30):
        """자동 토큰 갱신 시작"""
        if self.auto_refresh_enabled:
            logger.warning("Auto refresh is already enabled")
            return
        
        self.auto_refresh_enabled = True
        
        def refresh_worker():
            while self.auto_refresh_enabled:
                try:
                    # 토큰 만료 30분 전에 갱신
                    if (self.token_expires_at and 
                        datetime.utcnow() >= (self.token_expires_at - timedelta(minutes=30))):
                        
                        logger.info("Auto-refreshing service token (30 minutes before expiry)")
                        self._generate_new_token()
                    
                    # 지정된 간격으로 체크
                    time.sleep(check_interval_minutes * 60)
                    
                except Exception as e:
                    logger.error(f"Error in auto refresh worker: {str(e)}")
                    time.sleep(60)  # 에러 시 1분 후 재시도
        
        self.refresh_thread = threading.Thread(target=refresh_worker, daemon=True)
        self.refresh_thread.start()
        logger.info(f"Auto refresh started with {check_interval_minutes} minute intervals")
    
    def stop_auto_refresh(self):
        """자동 토큰 갱신 중지"""
        self.auto_refresh_enabled = False
        if self.refresh_thread:
            self.refresh_thread.join(timeout=5)
        logger.info("Auto refresh stopped")
    
    def get_token_info(self) -> Dict[str, Any]:
        """현재 토큰 정보 반환"""
        with self._lock:
            if not self.current_token:
                return {"status": "no_token"}
            
            token_info = verify_service_token(self.current_token)
            if not token_info:
                return {"status": "invalid_token"}
            
            return {
                "status": "valid",
                "client_id": token_info.get("client_id"),
                "scopes": token_info.get("scopes", []),
                "expires_at": self.token_expires_at.isoformat() if self.token_expires_at else None,
                "time_until_expiry": str(self.token_expires_at - datetime.utcnow()) if self.token_expires_at else None
            }


# 글로벌 서비스 토큰 매니저 인스턴스
service_token_manager = ServiceTokenManager()


def get_service_token() -> Optional[str]:
    """
    현재 유효한 서비스 토큰 반환
    환경변수 SERVICE_TOKEN이 설정되어 있으면 그것을 사용하고,
    없으면 자동으로 생성된 토큰을 사용
    """
    # 환경변수 우선 사용
    if settings.service_token:
        token_info = verify_service_token(settings.service_token)
        if token_info:
            return settings.service_token
        else:
            logger.warning("SERVICE_TOKEN environment variable contains invalid token")
    
    # 자동 생성된 토큰 사용
    return service_token_manager.get_token()


def refresh_service_token() -> bool:
    """서비스 토큰 수동 갱신"""
    return service_token_manager.refresh_token()


def start_service_token_auto_refresh():
    """서비스 토큰 자동 갱신 시작 (앱 시작 시 호출)"""
    service_token_manager.start_auto_refresh()


def get_service_token_info() -> Dict[str, Any]:
    """서비스 토큰 정보 조회"""
    return service_token_manager.get_token_info()


def create_service_request_headers() -> Dict[str, str]:
    """
    서비스 API 호출용 헤더 생성
    
    Returns:
        Authorization 헤더가 포함된 딕셔너리
    """
    token = get_service_token()
    if not token:
        raise RuntimeError("No valid service token available")
    
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "MAX-Platform-Service/1.0"
    }


def make_service_api_call(
    method: str,
    url: str,
    **kwargs
) -> requests.Response:
    """
    서비스 토큰을 사용한 API 호출
    
    Args:
        method: HTTP 메서드 (GET, POST, PUT, DELETE 등)
        url: 요청 URL
        **kwargs: requests 라이브러리의 추가 인자
    
    Returns:
        requests.Response 객체
    
    Raises:
        RuntimeError: 서비스 토큰이 없을 때
    """
    headers = create_service_request_headers()
    
    # 기존 헤더와 합치기
    if 'headers' in kwargs:
        headers.update(kwargs['headers'])
    kwargs['headers'] = headers
    
    return requests.request(method, url, **kwargs)