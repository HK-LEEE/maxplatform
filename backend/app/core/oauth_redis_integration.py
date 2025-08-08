"""
OAuth Redis Session Integration
Integrates Redis centralized session management with existing OAuth endpoints
Solves multi-worker session inconsistency issues
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from fastapi import Request, Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from .redis_session import get_session_store, create_user_session, get_user_session, delete_user_session, delete_all_user_sessions, store_user_oauth_tokens
from ..config import settings

logger = logging.getLogger(__name__)

class OAuthRedisSessionManager:
    """
    OAuth Redis Session Management Integration
    Handles session creation, validation, and cleanup with Redis backing
    """
    
    def __init__(self):
        self.session_store = None
        self._init_session_store()
    
    def _init_session_store(self):
        """Initialize Redis session store"""
        try:
            self.session_store = get_session_store()
            logger.info("✅ OAuth Redis session manager initialized")
        except RuntimeError:
            logger.warning("⚠️ Redis session store not initialized - OAuth will use database only")
            self.session_store = None
    
    def is_redis_available(self) -> bool:
        """Check if Redis session store is available"""
        return self.session_store is not None
    
    def create_oauth_session(self, user_data: Dict[str, Any], client_id: str, 
                           granted_scopes: List[str], request: Request) -> Optional[str]:
        """
        Create OAuth session with Redis backing
        
        Args:
            user_data: User information
            client_id: OAuth client identifier
            granted_scopes: Granted OAuth scopes
            request: FastAPI Request object
            
        Returns:
            Session ID if successful, None otherwise
        """
        if not self.is_redis_available():
            logger.debug("Redis not available - using database-only sessions")
            return None
        
        try:
            # Prepare enhanced user data for Redis session
            enhanced_user_data = {
                **user_data,
                'oauth_client_id': client_id,
                'oauth_granted_scopes': granted_scopes,
                'login_ip': request.client.host if request.client else 'unknown',
                'user_agent': request.headers.get('User-Agent', 'unknown'),
                'login_method': 'oauth',
                'session_type': 'oauth_session'
            }
            
            # Create Redis session
            session_id = create_user_session(enhanced_user_data)
            
            logger.info(f"✅ OAuth Redis session created: {session_id} for user {user_data.get('email')} client {client_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"❌ Failed to create OAuth Redis session: {e}")
            return None
    
    def validate_oauth_session(self, session_id: str, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Validate OAuth session from Redis
        
        Args:
            session_id: Session identifier
            client_id: OAuth client identifier
            
        Returns:
            Session data if valid, None otherwise
        """
        if not self.is_redis_available() or not session_id:
            return None
        
        try:
            session_data = get_user_session(session_id)
            
            if not session_data:
                logger.debug(f"🔍 OAuth session not found in Redis: {session_id}")
                return None
            
            # Validate client_id matches
            session_client_id = session_data.get('oauth_client_id')
            if session_client_id != client_id:
                logger.warning(f"⚠️ OAuth session client mismatch: expected {client_id}, got {session_client_id}")
                return None
            
            # Check if session is active
            if not session_data.get('is_active', False):
                logger.debug(f"🔍 OAuth session inactive: {session_id}")
                return None
            
            logger.debug(f"✅ OAuth session validated: {session_id}")
            return session_data
            
        except Exception as e:
            logger.error(f"❌ Failed to validate OAuth Redis session {session_id}: {e}")
            return None
    
    def store_oauth_tokens_in_session(self, session_id: str, tokens: Dict[str, Any]) -> bool:
        """
        Store OAuth tokens in Redis session
        
        Args:
            session_id: Session identifier
            tokens: OAuth token data
            
        Returns:
            Success status
        """
        if not self.is_redis_available() or not session_id:
            return False
        
        try:
            success = store_user_oauth_tokens(session_id, tokens)
            
            if success:
                logger.info(f"✅ OAuth tokens stored in Redis session: {session_id}")
            else:
                logger.warning(f"⚠️ Failed to store OAuth tokens in Redis session: {session_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error storing OAuth tokens in Redis session {session_id}: {e}")
            return False
    
    def cleanup_user_oauth_sessions(self, user_id: str, client_id: Optional[str] = None) -> int:
        """
        Clean up OAuth sessions for a user
        
        Args:
            user_id: User identifier
            client_id: Optional client identifier filter
            
        Returns:
            Number of sessions cleaned up
        """
        if not self.is_redis_available():
            return 0
        
        try:
            # If Redis cleanup fails, continue with database cleanup
            deleted_count = delete_all_user_sessions(user_id)
            
            if deleted_count > 0:
                logger.info(f"✅ Cleaned up {deleted_count} OAuth Redis sessions for user {user_id}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up OAuth Redis sessions for user {user_id}: {e}")
            return 0
    
    def delete_oauth_session(self, session_id: str) -> bool:
        """
        Delete specific OAuth session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Success status
        """
        if not self.is_redis_available() or not session_id:
            return False
        
        try:
            success = delete_user_session(session_id)
            
            if success:
                logger.info(f"✅ OAuth Redis session deleted: {session_id}")
            else:
                logger.debug(f"🔍 OAuth Redis session not found for deletion: {session_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error deleting OAuth Redis session {session_id}: {e}")
            return False
    
    def get_session_from_request(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Extract and validate session from HTTP request
        
        Args:
            request: FastAPI Request object
            
        Returns:
            Session data if found and valid, None otherwise
        """
        if not self.is_redis_available():
            return None
        
        try:
            # Try to get session ID from cookies
            session_id = request.cookies.get('session_id') or request.cookies.get('session_token')
            
            if not session_id:
                logger.debug("🔍 No session ID found in request cookies")
                return None
            
            # Validate session
            session_data = get_user_session(session_id)
            
            if session_data:
                logger.debug(f"✅ Session found from request: {session_id}")
                return session_data
            else:
                logger.debug(f"🔍 Session not found or expired: {session_id}")
                return None
            
        except Exception as e:
            logger.error(f"❌ Error getting session from request: {e}")
            return None
    
    def set_session_cookies(self, response: Response, session_id: str, user_data: Dict[str, Any]) -> None:
        """
        Set session cookies on response
        
        Args:
            response: FastAPI Response object
            session_id: Session identifier
            user_data: User data for additional cookies
        """
        try:
            # Set session cookies with proper security settings
            cookie_settings = {
                'httponly': True,
                'secure': not settings.debug,  # Use secure cookies in production
                'samesite': 'lax',
                'max_age': 3600  # 1 hour
            }
            
            # Primary session identifier
            response.set_cookie('session_id', session_id, **cookie_settings)
            response.set_cookie('session_token', session_id, **cookie_settings)
            
            # User identifier for quick access
            if user_data.get('id'):
                response.set_cookie('user_id', str(user_data['id']), **cookie_settings)
            
            logger.debug(f"✅ Session cookies set for: {session_id}")
            
        except Exception as e:
            logger.error(f"❌ Error setting session cookies: {e}")
    
    def clear_session_cookies(self, response: Response) -> None:
        """
        Clear session cookies from response
        
        Args:
            response: FastAPI Response object
        """
        try:
            # List of cookies to clear
            cookies_to_clear = [
                'session_id', 'session_token', 'user_id', 
                'access_token', 'refresh_token', 'oauth_state'
            ]
            
            for cookie_name in cookies_to_clear:
                response.delete_cookie(cookie_name)
                # Also try with domain and path variations for thorough cleanup
                response.delete_cookie(cookie_name, domain=f".{settings.base_url}")
                response.delete_cookie(cookie_name, path="/")
            
            logger.debug("✅ Session cookies cleared")
            
        except Exception as e:
            logger.error(f"❌ Error clearing session cookies: {e}")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get OAuth session statistics
        
        Returns:
            Statistics dictionary
        """
        if not self.is_redis_available():
            return {'error': 'Redis not available'}
        
        try:
            return self.session_store.get_session_stats()
        except Exception as e:
            logger.error(f"❌ Error getting session stats: {e}")
            return {'error': str(e)}

# Global OAuth Redis session manager instance
oauth_redis_manager: Optional[OAuthRedisSessionManager] = None

def init_oauth_redis_manager() -> OAuthRedisSessionManager:
    """
    Initialize global OAuth Redis session manager
    
    Returns:
        OAuthRedisSessionManager instance
    """
    global oauth_redis_manager
    oauth_redis_manager = OAuthRedisSessionManager()
    return oauth_redis_manager

def get_oauth_redis_manager() -> Optional[OAuthRedisSessionManager]:
    """
    Get global OAuth Redis session manager
    
    Returns:
        OAuthRedisSessionManager instance or None if not initialized
    """
    global oauth_redis_manager
    return oauth_redis_manager

# Convenience functions for OAuth endpoints
def create_oauth_redis_session(user_data: Dict[str, Any], client_id: str, 
                             granted_scopes: List[str], request: Request) -> Optional[str]:
    """Create OAuth session with Redis backing"""
    manager = get_oauth_redis_manager()
    if manager:
        return manager.create_oauth_session(user_data, client_id, granted_scopes, request)
    return None

def validate_oauth_redis_session(session_id: str, client_id: str) -> Optional[Dict[str, Any]]:
    """Validate OAuth session from Redis"""
    manager = get_oauth_redis_manager()
    if manager:
        return manager.validate_oauth_session(session_id, client_id)
    return None

def cleanup_oauth_redis_sessions(user_id: str, client_id: Optional[str] = None) -> int:
    """Clean up OAuth sessions for a user"""
    manager = get_oauth_redis_manager()
    if manager:
        return manager.cleanup_user_oauth_sessions(user_id, client_id)
    return 0

def get_oauth_session_from_request(request: Request) -> Optional[Dict[str, Any]]:
    """Extract and validate session from HTTP request"""
    manager = get_oauth_redis_manager()
    if manager:
        return manager.get_session_from_request(request)
    return None

def set_oauth_session_cookies(response: Response, session_id: str, user_data: Dict[str, Any]) -> None:
    """Set session cookies on response"""
    manager = get_oauth_redis_manager()
    if manager:
        manager.set_session_cookies(response, session_id, user_data)

def clear_oauth_session_cookies(response: Response) -> None:
    """Clear session cookies from response"""
    manager = get_oauth_redis_manager()
    if manager:
        manager.clear_session_cookies(response)