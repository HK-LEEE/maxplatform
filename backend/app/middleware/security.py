#%%
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import json
import logging
import redis
from functools import wraps

from ..database import get_db
from ..models import User
from ..config import settings
from ..utils.auth import get_current_user

logger = logging.getLogger(__name__)

# Redis client for rate limiting (실제 환경에서는 Redis 설정 필요)
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
except:
    redis_client = None
    logger.warning("Redis not available - rate limiting will use in-memory storage")

class BatchLogoutPermission(Enum):
    """일괄 로그아웃 권한 정의"""
    VIEW_BATCH_LOGOUT_JOBS = "batch_logout:view"
    EXECUTE_GROUP_LOGOUT = "batch_logout:execute:group"  
    EXECUTE_CLIENT_LOGOUT = "batch_logout:execute:client"
    EXECUTE_TIME_LOGOUT = "batch_logout:execute:time"
    EXECUTE_CONDITIONAL_LOGOUT = "batch_logout:execute:conditional"
    EXECUTE_EMERGENCY_LOGOUT = "batch_logout:execute:emergency"
    CANCEL_BATCH_LOGOUT = "batch_logout:cancel"
    BATCH_LOGOUT_ADMIN = "batch_logout:admin"

class RateLimitType(Enum):
    """Rate limit 타입"""
    GROUP_LOGOUT = "group_logout"
    CLIENT_LOGOUT = "client_logout"
    TIME_LOGOUT = "time_logout"
    CONDITIONAL_LOGOUT = "conditional_logout"
    EMERGENCY_LOGOUT = "emergency_logout"
    USER_SESSION_LOGOUT = "user_session_logout"

class SecurityMiddleware:
    """일괄 로그아웃 보안 미들웨어"""
    
    def __init__(self):
        self.rate_limits = {
            RateLimitType.GROUP_LOGOUT: {"count": 10, "window": 3600},      # 10회/시간
            RateLimitType.CLIENT_LOGOUT: {"count": 5, "window": 3600},      # 5회/시간
            RateLimitType.TIME_LOGOUT: {"count": 3, "window": 86400},       # 3회/일
            RateLimitType.CONDITIONAL_LOGOUT: {"count": 5, "window": 21600}, # 5회/6시간
            RateLimitType.EMERGENCY_LOGOUT: {"count": 1, "window": 86400},  # 1회/일
            RateLimitType.USER_SESSION_LOGOUT: {"count": 50, "window": 3600} # 50회/시간
        }
        self.permission_hierarchy = {
            BatchLogoutPermission.BATCH_LOGOUT_ADMIN: [
                BatchLogoutPermission.VIEW_BATCH_LOGOUT_JOBS,
                BatchLogoutPermission.EXECUTE_GROUP_LOGOUT,
                BatchLogoutPermission.EXECUTE_CLIENT_LOGOUT,
                BatchLogoutPermission.EXECUTE_TIME_LOGOUT,
                BatchLogoutPermission.EXECUTE_CONDITIONAL_LOGOUT,
                BatchLogoutPermission.EXECUTE_EMERGENCY_LOGOUT,
                BatchLogoutPermission.CANCEL_BATCH_LOGOUT
            ]
        }
        # In-memory storage fallback
        self._memory_store: Dict[str, List[float]] = {}

    def require_permission(self, permission: BatchLogoutPermission):
        """권한 검증 데코레이터"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 현재 사용자 추출
                current_user = None
                for key, value in kwargs.items():
                    if isinstance(value, User):
                        current_user = value
                        break
                
                if not current_user:
                    raise HTTPException(
                        status_code=401, 
                        detail="Authentication required"
                    )
                
                if not self.has_permission(current_user, permission):
                    logger.warning(f"Permission denied for user {current_user.email}: {permission.value}")
                    raise HTTPException(
                        status_code=403,
                        detail=f"Permission denied: {permission.value} required"
                    )
                
                # 감사 로그
                self._log_permission_check(current_user, permission, True)
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator

    def rate_limit(self, limit_type: RateLimitType, user_key_extractor: Callable = None):
        """Rate limiting 데코레이터"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 사용자 키 추출
                if user_key_extractor:
                    user_key = user_key_extractor(*args, **kwargs)
                else:
                    # 기본적으로 current_user에서 추출
                    current_user = None
                    for key, value in kwargs.items():
                        if isinstance(value, User):
                            current_user = value
                            break
                    
                    if not current_user:
                        raise HTTPException(status_code=401, detail="Authentication required")
                    
                    user_key = str(current_user.id)
                
                # Rate limit 확인
                if not self._check_rate_limit(user_key, limit_type):
                    limit_config = self.rate_limits[limit_type]
                    remaining_time = self._get_remaining_time(user_key, limit_type)
                    
                    logger.warning(f"Rate limit exceeded for user {user_key}: {limit_type.value}")
                    
                    raise HTTPException(
                        status_code=429,
                        detail=f"Rate limit exceeded for {limit_type.value}. "
                               f"Try again in {remaining_time} seconds."
                    )
                
                # Rate limit 기록
                self._record_rate_limit(user_key, limit_type)
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator

    def audit_log(self, action_type: str, sensitive: bool = False):
        """감사 로그 데코레이터"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = datetime.utcnow()
                success = False
                error_message = None
                
                # 사용자 정보 추출
                current_user = None
                request_data = {}
                
                for key, value in kwargs.items():
                    if isinstance(value, User):
                        current_user = value
                    elif hasattr(value, 'dict'):  # Pydantic 모델
                        request_data[key] = value.dict()
                
                try:
                    result = await func(*args, **kwargs)
                    success = True
                    return result
                except Exception as e:
                    error_message = str(e)
                    raise
                finally:
                    # 감사 로그 기록
                    self._write_audit_log(
                        action_type=action_type,
                        user_id=str(current_user.id) if current_user else None,
                        user_email=current_user.email if current_user else None,
                        success=success,
                        error_message=error_message,
                        request_data=request_data if not sensitive else {"sensitive": "data_redacted"},
                        execution_time=(datetime.utcnow() - start_time).total_seconds()
                    )
            
            return wrapper
        return decorator

    def emergency_auth_required(self, confirmation_code: str = "LOGOUT_ALL_USERS"):
        """긴급 인증 요구 데코레이터"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Request 객체에서 emergency key 확인
                request = kwargs.get('request')
                if not request:
                    for arg in args:
                        if hasattr(arg, 'headers'):
                            request = arg
                            break
                
                emergency_key = None
                if request and hasattr(request, 'headers'):
                    emergency_key = request.headers.get('X-Emergency-Key')
                
                # 요청 본문에서 확인 코드 확인
                confirm_value = None
                for key, value in kwargs.items():
                    if hasattr(value, 'confirm'):
                        confirm_value = value.confirm
                        break
                
                if confirm_value != confirmation_code:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Emergency confirmation required: {confirmation_code}"
                    )
                
                # Emergency key 검증 (실제 구현에서는 Redis 등에서 확인)
                current_user = None
                for key, value in kwargs.items():
                    if isinstance(value, User):
                        current_user = value
                        break
                
                if current_user and not self._verify_emergency_key(str(current_user.id), emergency_key):
                    logger.critical(f"Invalid emergency key for user {current_user.email}")
                    raise HTTPException(
                        status_code=403,
                        detail="Invalid emergency key"
                    )
                
                logger.critical(f"Emergency operation authorized for user {current_user.email if current_user else 'Unknown'}")
                return await func(*args, **kwargs)
            
            return wrapper
        return decorator

    def has_permission(self, user: User, permission: BatchLogoutPermission) -> bool:
        """사용자 권한 확인"""
        # 최고 관리자는 모든 권한
        if user.is_admin and hasattr(user, 'is_super_admin') and user.is_super_admin:
            return True
        
        # 관리자는 일반 배치 로그아웃 권한 (긴급 제외)
        if user.is_admin and permission != BatchLogoutPermission.EXECUTE_EMERGENCY_LOGOUT:
            return True
        
        # 실제 구현에서는 사용자의 permissions 필드 확인
        # 현재는 간단한 구현
        user_permissions = getattr(user, 'permissions', [])
        
        # 직접 권한 확인
        if permission.value in user_permissions:
            return True
        
        # 상위 권한 확인
        for parent_perm, child_perms in self.permission_hierarchy.items():
            if parent_perm.value in user_permissions and permission in child_perms:
                return True
        
        return False

    def _check_rate_limit(self, user_key: str, limit_type: RateLimitType) -> bool:
        """Rate limit 확인"""
        limit_config = self.rate_limits[limit_type]
        redis_key = f"rate_limit:{limit_type.value}:{user_key}"
        
        current_time = datetime.utcnow().timestamp()
        window_start = current_time - limit_config["window"]
        
        if redis_client:
            try:
                # Redis를 사용한 sliding window
                pipe = redis_client.pipeline()
                pipe.zremrangebyscore(redis_key, 0, window_start)
                pipe.zcard(redis_key)
                pipe.expire(redis_key, limit_config["window"])
                results = pipe.execute()
                
                current_count = results[1]
                return current_count < limit_config["count"]
                
            except Exception as e:
                logger.error(f"Redis error in rate limiting: {e}")
                # Redis 실패 시 메모리 저장소 사용
                
        # 메모리 저장소 fallback
        if user_key not in self._memory_store:
            self._memory_store[user_key] = []
        
        # 오래된 기록 제거
        self._memory_store[user_key] = [
            timestamp for timestamp in self._memory_store[user_key]
            if timestamp > window_start
        ]
        
        return len(self._memory_store[user_key]) < limit_config["count"]

    def _record_rate_limit(self, user_key: str, limit_type: RateLimitType):
        """Rate limit 기록"""
        redis_key = f"rate_limit:{limit_type.value}:{user_key}"
        current_time = datetime.utcnow().timestamp()
        
        if redis_client:
            try:
                redis_client.zadd(redis_key, {str(current_time): current_time})
                return
            except Exception as e:
                logger.error(f"Redis error recording rate limit: {e}")
        
        # 메모리 저장소 fallback
        if user_key not in self._memory_store:
            self._memory_store[user_key] = []
        
        self._memory_store[user_key].append(current_time)

    def _get_remaining_time(self, user_key: str, limit_type: RateLimitType) -> int:
        """남은 시간 계산 (초)"""
        limit_config = self.rate_limits[limit_type]
        redis_key = f"rate_limit:{limit_type.value}:{user_key}"
        
        if redis_client:
            try:
                oldest_request = redis_client.zrange(redis_key, 0, 0, withscores=True)
                if oldest_request:
                    oldest_time = oldest_request[0][1]
                    return max(0, int(oldest_time + limit_config["window"] - datetime.utcnow().timestamp()))
            except Exception as e:
                logger.error(f"Redis error getting remaining time: {e}")
        
        # 메모리 저장소 fallback
        if user_key in self._memory_store and self._memory_store[user_key]:
            oldest_time = min(self._memory_store[user_key])
            return max(0, int(oldest_time + limit_config["window"] - datetime.utcnow().timestamp()))
        
        return 0

    def _verify_emergency_key(self, user_id: str, emergency_key: str) -> bool:
        """긴급 키 검증"""
        if not emergency_key:
            return False
        
        redis_key = f"emergency_key:{user_id}"
        
        if redis_client:
            try:
                stored_key = redis_client.get(redis_key)
                if stored_key and stored_key == emergency_key:
                    # 사용된 키 삭제
                    redis_client.delete(redis_key)
                    return True
            except Exception as e:
                logger.error(f"Redis error verifying emergency key: {e}")
        
        # 실제 구현에서는 데이터베이스나 다른 저장소 사용
        # 현재는 개발용으로 간단한 검증 (실제 운영에서는 제거)
        return emergency_key == "DEV_EMERGENCY_KEY_2025"

    def _log_permission_check(self, user: User, permission: BatchLogoutPermission, success: bool):
        """권한 검증 로그"""
        logger.info(f"Permission check: user={user.email}, permission={permission.value}, success={success}")

    def _write_audit_log(self, **kwargs):
        """감사 로그 작성"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action_type": kwargs.get("action_type"),
            "user_id": kwargs.get("user_id"),
            "user_email": kwargs.get("user_email"),
            "success": kwargs.get("success"),
            "error_message": kwargs.get("error_message"),
            "execution_time": kwargs.get("execution_time"),
            "request_data": kwargs.get("request_data", {})
        }
        
        # 실제 구현에서는 데이터베이스나 로그 시스템에 저장
        logger.info(f"AUDIT_LOG: {json.dumps(log_entry, default=str)}")

# 전역 보안 미들웨어 인스턴스
security_middleware = SecurityMiddleware()

# 편의 함수들
def require_batch_logout_permission(permission: BatchLogoutPermission):
    """일괄 로그아웃 권한 확인 데코레이터"""
    return security_middleware.require_permission(permission)

def batch_logout_rate_limit(limit_type: RateLimitType):
    """일괄 로그아웃 Rate limit 데코레이터"""
    return security_middleware.rate_limit(limit_type)

def audit_batch_logout_action(action_type: str, sensitive: bool = False):
    """일괄 로그아웃 감사 로그 데코레이터"""
    return security_middleware.audit_log(action_type, sensitive)

def require_emergency_auth(confirmation_code: str = "LOGOUT_ALL_USERS"):
    """긴급 인증 요구 데코레이터"""
    return security_middleware.emergency_auth_required(confirmation_code)