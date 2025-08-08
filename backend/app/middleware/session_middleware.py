"""
Session Middleware for JWT-Redis Session Synchronization
자동으로 JWT와 Redis 세션을 동기화하여 세션 일관성 보장
"""

import json
import time
import logging
from typing import Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import User
from ..core.redis_session import get_session_store, create_user_session, get_user_session

logger = logging.getLogger(__name__)


class SessionMiddleware(BaseHTTPMiddleware):
    """
    JWT와 Redis 세션 동기화 미들웨어
    모든 요청에서 JWT 토큰 확인 및 Redis 세션 자동 복구
    """
    
    def __init__(self, app, **kwargs):
        super().__init__(app)
        self.session_store = None
        self._init_session_store()
    
    def _init_session_store(self):
        """Initialize Redis session store"""
        try:
            self.session_store = get_session_store()
            logger.info("✅ SessionMiddleware initialized with Redis")
        except RuntimeError:
            logger.warning("⚠️ Redis not available - SessionMiddleware in JWT-only mode")
            self.session_store = None
    
    async def dispatch(self, request: Request, call_next):
        """
        Process each request to ensure JWT-Redis session consistency
        """
        # Skip middleware for health checks and static files
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Extract JWT token
        token = await self._extract_token(request)
        
        if token:
            # Process token and sync Redis session
            await self._process_token(request, token)
        
        # Process the request
        response = await call_next(request)
        
        return response
    
    async def _extract_token(self, request: Request) -> Optional[str]:
        """
        Extract JWT token from multiple sources
        
        Args:
            request: FastAPI Request object
            
        Returns:
            JWT token string or None
        """
        # 1. Check Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]
        
        # 2. Check cookies
        token = request.cookies.get("access_token")
        if token:
            return token
        
        # 3. Check query parameters (for OAuth flow)
        if "token" in request.query_params:
            return request.query_params["token"]
        
        return None
    
    async def _process_token(self, request: Request, token: str) -> None:
        """
        Process JWT token and ensure Redis session exists
        
        Args:
            request: FastAPI Request object
            token: JWT token string
        """
        try:
            # Verify JWT token
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            user_id = payload.get("sub") or payload.get("user_id")
            
            if not user_id:
                return
            
            # Store user info in request state
            request.state.user_id = user_id
            request.state.jwt_valid = True
            request.state.jwt_exp = payload.get("exp")
            
            # Check and sync Redis session
            if self.session_store:
                await self._sync_redis_session(user_id, payload, token)
                
        except jwt.ExpiredSignatureError:
            # JWT expired - clean up Redis session
            logger.debug(f"JWT token expired")
            request.state.jwt_valid = False
            
            if self.session_store and user_id:
                try:
                    # Parse expired token to get user_id
                    payload = jwt.decode(token, settings.secret_key, 
                                       algorithms=[settings.algorithm], 
                                       options={"verify_exp": False})
                    user_id = payload.get("sub") or payload.get("user_id")
                    
                    if user_id:
                        # Clean up expired Redis sessions
                        deleted = self.session_store.delete_user_sessions(user_id)
                        if deleted > 0:
                            logger.info(f"Cleaned up {deleted} expired Redis sessions for user {user_id}")
                except:
                    pass
                    
        except JWTError as e:
            logger.debug(f"JWT validation error: {e}")
            request.state.jwt_valid = False
        except Exception as e:
            logger.error(f"Error processing token: {e}")
            request.state.jwt_valid = False
    
    async def _sync_redis_session(self, user_id: str, jwt_payload: dict, token: str) -> None:
        """
        Ensure Redis session exists and is synchronized with JWT
        
        Args:
            user_id: User ID from JWT
            jwt_payload: Decoded JWT payload
            token: Original JWT token
        """
        try:
            # Check if Redis session exists
            user_sessions_key = f"maxplatform_session_user:{user_id}"
            existing_sessions = self.session_store.redis_client.smembers(user_sessions_key)
            
            redis_session_exists = False
            session_id = None
            
            for sid in existing_sessions:
                session_data = self.session_store.get_session(sid)
                if session_data:
                    redis_session_exists = True
                    session_id = sid
                    logger.debug(f"Found existing Redis session {sid} for user {user_id}")
                    break
            
            if not redis_session_exists:
                # 🔥 핵심: JWT는 유효하지만 Redis 세션이 없는 경우 자동 생성
                logger.warning(f"JWT valid but no Redis session for user {user_id}, creating new session")
                
                # Get user data from database
                user = await self._get_user_from_db(user_id)
                if not user:
                    logger.warning(f"User {user_id} not found in database")
                    return
                
                session_data = {
                    "id": str(user.id),
                    "email": user.email,
                    "name": user.real_name or user.display_name or user.email,
                    "is_admin": user.is_admin,
                    "is_active": user.is_active,
                    "groups": [{"id": str(g.id), "name": g.name} for g in user.groups] if user.groups else [],
                    "roles": [{"id": str(r.id), "name": r.name} for r in user.roles] if user.roles else [],
                    "created_at": time.time(),
                    "source": "middleware_recovery",
                    "jwt_exp": jwt_payload.get("exp")
                }
                
                # Calculate TTL from JWT expiration
                ttl = jwt_payload.get("exp", 0) - int(time.time())
                if ttl > 0:
                    # Override session timeout with JWT remaining time
                    original_timeout = self.session_store.session_timeout
                    self.session_store.session_timeout = ttl
                    
                    session_id = create_user_session(session_data)
                    
                    # Restore original timeout
                    self.session_store.session_timeout = original_timeout
                    
                    logger.info(f"✅ Auto-recovered Redis session {session_id} for user {user_id}")
                    
                    # Store token in Redis session
                    self.session_store.store_oauth_tokens(session_id, {
                        "access_token": token,
                        "token_type": "Bearer",
                        "expires_at": jwt_payload.get("exp"),
                        "recovered": True,
                        "recovered_by": "SessionMiddleware"
                    })
            else:
                # Update existing session's last accessed time
                logger.debug(f"Updating last accessed time for session {session_id}")
                
        except Exception as e:
            # Redis errors should not break the request
            logger.error(f"Redis session sync error (non-fatal): {e}")
    
    async def _get_user_from_db(self, user_id: str) -> Optional[User]:
        """
        Get user from database
        
        Args:
            user_id: User ID
            
        Returns:
            User object or None
        """
        try:
            # Create a new database session
            from ..database import SessionLocal
            db = SessionLocal()
            
            try:
                user = db.query(User).filter(User.id == user_id).first()
                return user
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Failed to get user from database: {e}")
            return None


def setup_session_middleware(app):
    """
    Setup session middleware for the FastAPI application
    
    Args:
        app: FastAPI application instance
    """
    app.add_middleware(SessionMiddleware)
    logger.info("✅ SessionMiddleware added to application")