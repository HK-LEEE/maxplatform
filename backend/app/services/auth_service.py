"""
Auth Service with Redis Session Synchronization
JWT 토큰 발급/갱신 시 Redis 세션도 함께 생성/갱신하여 세션 일관성 보장
"""

import json
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from ..models import User, RefreshToken
from ..config import settings
from ..utils.auth import create_access_token, create_refresh_token, get_password_hash, verify_password
from ..core.redis_session import get_session_store, create_user_session, get_user_session

logger = logging.getLogger(__name__)


class AuthService:
    """
    인증 서비스 - JWT와 Redis 세션 동기화 관리
    """
    
    def __init__(self):
        """Initialize auth service with Redis session store"""
        try:
            self.session_store = get_session_store()
            logger.info("✅ AuthService initialized with Redis session store")
        except RuntimeError:
            logger.warning("⚠️ Redis session store not available - JWT only mode")
            self.session_store = None
    
    async def create_tokens_with_redis_sync(self, user: User, db: Session) -> Dict[str, Any]:
        """
        JWT 토큰 생성과 동시에 Redis 세션 생성/갱신
        
        Args:
            user: User object
            db: Database session
            
        Returns:
            Dict containing tokens and session info
        """
        try:
            # 1. JWT 토큰 생성
            access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
            access_token = create_access_token(
                data={"sub": str(user.id), "email": user.email},
                expires_delta=access_token_expires
            )
            
            refresh_token = create_refresh_token(
                data={"sub": str(user.id), "email": user.email}
            )
            
            # 2. Redis 세션 동시 생성
            session_id = None
            if self.session_store:
                session_id = await self.create_redis_session(user, access_token)
                logger.info(f"✅ Created Redis session {session_id} for user {user.email}")
            
            # 3. Refresh token을 DB에 저장
            await self.save_refresh_token(user.id, refresh_token, db)
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "Bearer",
                "expires_in": settings.access_token_expire_minutes * 60,
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"Failed to create tokens with Redis sync: {e}")
            raise
    
    async def create_redis_session(self, user: User, token: str) -> Optional[str]:
        """
        JWT 발급과 동시에 Redis 세션 생성
        
        Args:
            user: User object
            token: JWT access token
            
        Returns:
            Session ID if successful
        """
        if not self.session_store:
            return None
        
        try:
            # Decode token to get expiration
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            exp_timestamp = payload.get("exp", 0)
            
            session_data = {
                "id": str(user.id),
                "email": user.email,
                "name": user.real_name or user.display_name or user.email,
                "is_admin": user.is_admin,
                "is_active": user.is_active,
                "groups": [{"id": str(user.group.id), "name": user.group.name}] if user.group else [],
                "roles": [{"id": str(user.role.id), "name": user.role.name}] if user.role else [],
                "permissions": self._extract_user_permissions(user),
                "created_at": datetime.utcnow().isoformat(),
                "token": token,
                "token_exp": exp_timestamp,
                "source": "jwt_sync"
            }
            
            # JWT 만료 시간과 동일하게 Redis TTL 설정
            ttl = exp_timestamp - int(time.time()) if exp_timestamp > 0 else 3600
            
            # 기존 세션이 있다면 먼저 삭제
            await self.cleanup_user_sessions(user.id)
            
            # 새 세션 생성
            original_timeout = self.session_store.session_timeout
            self.session_store.session_timeout = ttl
            session_id = create_user_session(session_data)
            self.session_store.session_timeout = original_timeout  # Restore original timeout
            
            # OAuth tokens 저장
            self.session_store.store_oauth_tokens(session_id, {
                "access_token": token,
                "token_type": "Bearer",
                "expires_at": exp_timestamp
            })
            
            # PM2 워커 간 동기화를 위한 pub/sub
            try:
                self.session_store.redis_client.publish(
                    "session_created",
                    json.dumps({"user_id": str(user.id), "session_id": session_id})
                )
            except:
                pass  # Pub/sub failure is non-critical
            
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create Redis session: {e}")
            return None
    
    async def refresh_tokens_with_redis_sync(self, refresh_token: str, db: Session) -> Optional[Dict[str, Any]]:
        """
        리프레시 토큰으로 새 액세스 토큰 발급 및 Redis 세션 갱신
        
        Args:
            refresh_token: Refresh token string
            db: Database session
            
        Returns:
            New tokens and session info
        """
        try:
            # 1. Refresh token 검증
            payload = jwt.decode(refresh_token, settings.secret_key, algorithms=[settings.algorithm])
            user_id = payload.get("sub")
            
            if not user_id:
                logger.warning("Invalid refresh token - missing user_id")
                return None
            
            # 2. DB에서 refresh token 확인
            stored_token = db.query(RefreshToken).filter(
                RefreshToken.user_id == user_id,
                RefreshToken.token == refresh_token,
                RefreshToken.is_active == True
            ).first()
            
            if not stored_token:
                logger.warning(f"Refresh token not found in DB for user {user_id}")
                return None
            
            # 3. 사용자 정보 조회
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User {user_id} not found")
                return None
            
            # 4. 새로운 토큰 발급 및 Redis 세션 갱신
            return await self.create_tokens_with_redis_sync(user, db)
            
        except jwt.ExpiredSignatureError:
            logger.info("Refresh token expired")
            return None
        except JWTError as e:
            logger.warning(f"Invalid refresh token: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to refresh tokens: {e}")
            return None
    
    async def save_refresh_token(self, user_id: str, token: str, db: Session) -> None:
        """
        Save refresh token to database
        
        Args:
            user_id: User ID
            token: Refresh token
            db: Database session
        """
        try:
            # 기존 활성 토큰 비활성화
            db.query(RefreshToken).filter(
                RefreshToken.user_id == user_id,
                RefreshToken.is_active == True
            ).update({"is_active": False})
            
            # 새 refresh token 저장
            refresh_token = RefreshToken(
                user_id=user_id,
                token=token,
                is_active=True,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
            )
            db.add(refresh_token)
            db.commit()
            
        except Exception as e:
            logger.error(f"Failed to save refresh token: {e}")
            db.rollback()
            raise
    
    async def cleanup_user_sessions(self, user_id: str) -> int:
        """
        사용자의 기존 Redis 세션 정리
        
        Args:
            user_id: User ID
            
        Returns:
            Number of sessions cleaned up
        """
        if not self.session_store:
            return 0
        
        try:
            deleted_count = self.session_store.delete_user_sessions(user_id)
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} existing Redis sessions for user {user_id}")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup user sessions: {e}")
            return 0
    
    def _extract_user_permissions(self, user) -> list:
        """
        사용자의 권한 목록 추출
        
        Args:
            user: User object
            
        Returns:
            List of permission names
        """
        permissions = []
        
        # User-level permissions
        if hasattr(user, 'permissions'):
            permissions.extend([p.name for p in user.permissions])
        
        # Group permissions  
        if hasattr(user, 'group') and user.group:
            if hasattr(user.group, 'permissions'):
                permissions.extend([p.name for p in user.group.permissions])
        
        # Role permissions
        if hasattr(user, 'role') and user.role:
            if hasattr(user.role, 'permissions'):
                permissions.extend([p.name for p in user.role.permissions])
        
        # Remove duplicates
        return list(set(permissions))
    
    async def logout_with_redis_cleanup(self, user_id: str, token: str, db: Session) -> bool:
        """
        로그아웃 시 JWT 무효화 및 Redis 세션 정리
        
        Args:
            user_id: User ID
            token: Current access token
            db: Database session
            
        Returns:
            Success status
        """
        try:
            # 1. Refresh tokens 비활성화
            db.query(RefreshToken).filter(
                RefreshToken.user_id == user_id,
                RefreshToken.is_active == True
            ).update({"is_active": False})
            db.commit()
            
            # 2. Redis 세션 삭제
            if self.session_store:
                deleted_count = await self.cleanup_user_sessions(user_id)
                logger.info(f"Logout: Deleted {deleted_count} Redis sessions for user {user_id}")
            
            # 3. PM2 워커 간 로그아웃 알림
            if self.session_store:
                try:
                    self.session_store.redis_client.publish(
                        "session_destroyed",
                        json.dumps({"user_id": str(user_id)})
                    )
                except:
                    pass  # Pub/sub failure is non-critical
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to logout with Redis cleanup: {e}")
            return False
    
    def _extract_user_permissions(self, user: User) -> list:
        """
        Extract user permissions from roles and groups
        
        Args:
            user: User object
            
        Returns:
            List of permissions
        """
        permissions = []
        
        # Extract from roles
        if user.roles:
            for role in user.roles:
                if hasattr(role, 'permissions'):
                    permissions.extend(role.permissions)
        
        # Extract from groups
        if user.groups:
            for group in user.groups:
                if hasattr(group, 'permissions'):
                    permissions.extend(group.permissions)
        
        # Remove duplicates
        return list(set(permissions))


# Global auth service instance
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """
    Get global auth service instance
    
    Returns:
        AuthService instance
    """
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service