"""
Redis Session Store for OAuth SSO Session Centralization
Solves multi-worker session inconsistency issues by centralizing session storage
"""

import json
import uuid
from typing import Any, Dict, Optional, Union
from datetime import datetime, timedelta
import redis
import logging
from functools import wraps

logger = logging.getLogger(__name__)

class RedisSessionStore:
    """
    Centralized session storage using Redis
    Replaces in-memory sessions that cause worker isolation issues
    """
    
    def __init__(self, 
                 redis_url: str = "redis://localhost:6379/0",
                 session_timeout: int = 3600,  # 1 hour
                 key_prefix: str = "maxplatform_session"):
        """
        Initialize Redis session store
        
        Args:
            redis_url: Redis connection URL
            session_timeout: Session TTL in seconds
            key_prefix: Redis key prefix for sessions
        """
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()  # Test connection
            logger.info(f"✅ Redis connection established: {redis_url}")
        except redis.ConnectionError as e:
            logger.error(f"❌ Redis connection failed: {e}")
            raise ConnectionError(f"Failed to connect to Redis: {e}")
        
        self.session_timeout = session_timeout
        self.key_prefix = key_prefix
        
    def _get_session_key(self, session_id: str) -> str:
        """Generate Redis key for session"""
        return f"{self.key_prefix}:{session_id}"
    
    def _get_user_sessions_key(self, user_id: str) -> str:
        """Generate Redis key for user's session list"""
        return f"{self.key_prefix}_user:{user_id}"
    
    def create_session(self, user_data: Dict[str, Any]) -> str:
        """
        Create new session in Redis
        
        Args:
            user_data: User information to store in session
            
        Returns:
            str: Generated session ID
        """
        session_id = str(uuid.uuid4())
        session_key = self._get_session_key(session_id)
        
        session_data = {
            'session_id': session_id,
            'user_id': str(user_data.get('id', '')),
            'user_email': user_data.get('email', ''),
            'user_name': user_data.get('name', ''),
            'created_at': datetime.utcnow().isoformat(),
            'last_accessed': datetime.utcnow().isoformat(),
            'user_data': user_data,
            'oauth_tokens': {},
            'is_active': True
        }
        
        try:
            # Store session with TTL
            self.redis_client.setex(
                session_key, 
                self.session_timeout, 
                json.dumps(session_data, default=str)
            )
            
            # Track user's sessions
            if session_data['user_id']:
                user_sessions_key = self._get_user_sessions_key(session_data['user_id'])
                self.redis_client.sadd(user_sessions_key, session_id)
                self.redis_client.expire(user_sessions_key, self.session_timeout)
            
            logger.info(f"✅ Session created: {session_id} for user {session_data['user_email']}")
            return session_id
            
        except redis.RedisError as e:
            logger.error(f"❌ Failed to create session: {e}")
            raise RuntimeError(f"Session creation failed: {e}")
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session data from Redis
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dict containing session data or None if not found
        """
        if not session_id:
            return None
            
        session_key = self._get_session_key(session_id)
        
        try:
            session_data = self.redis_client.get(session_key)
            if session_data:
                data = json.loads(session_data)
                
                # Update last accessed time
                data['last_accessed'] = datetime.utcnow().isoformat()
                self.redis_client.setex(
                    session_key, 
                    self.session_timeout, 
                    json.dumps(data, default=str)
                )
                
                logger.debug(f"🔍 Session retrieved: {session_id}")
                return data
            
            logger.debug(f"🔍 Session not found: {session_id}")
            return None
            
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.error(f"❌ Failed to get session {session_id}: {e}")
            return None
    
    def update_session(self, session_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update session data in Redis
        
        Args:
            session_id: Session identifier
            update_data: Data to update
            
        Returns:
            bool: Success status
        """
        session_data = self.get_session(session_id)
        if not session_data:
            logger.warning(f"⚠️ Cannot update non-existent session: {session_id}")
            return False
        
        # Merge update data
        session_data.update(update_data)
        session_data['last_accessed'] = datetime.utcnow().isoformat()
        
        session_key = self._get_session_key(session_id)
        
        try:
            self.redis_client.setex(
                session_key, 
                self.session_timeout, 
                json.dumps(session_data, default=str)
            )
            
            logger.debug(f"✅ Session updated: {session_id}")
            return True
            
        except redis.RedisError as e:
            logger.error(f"❌ Failed to update session {session_id}: {e}")
            return False
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete session from Redis
        
        Args:
            session_id: Session identifier
            
        Returns:
            bool: Success status
        """
        if not session_id:
            return False
            
        session_data = self.get_session(session_id)
        session_key = self._get_session_key(session_id)
        
        try:
            # Remove from Redis
            deleted = self.redis_client.delete(session_key)
            
            # Remove from user's session list
            if session_data and session_data.get('user_id'):
                user_sessions_key = self._get_user_sessions_key(session_data['user_id'])
                self.redis_client.srem(user_sessions_key, session_id)
            
            if deleted:
                logger.info(f"✅ Session deleted: {session_id}")
                return True
            else:
                logger.warning(f"⚠️ Session not found for deletion: {session_id}")
                return False
                
        except redis.RedisError as e:
            logger.error(f"❌ Failed to delete session {session_id}: {e}")
            return False
    
    def delete_user_sessions(self, user_id: str) -> int:
        """
        Delete all sessions for a specific user
        
        Args:
            user_id: User identifier
            
        Returns:
            int: Number of sessions deleted
        """
        user_sessions_key = self._get_user_sessions_key(user_id)
        
        try:
            # Get all session IDs for this user
            session_ids = self.redis_client.smembers(user_sessions_key)
            
            deleted_count = 0
            for session_id in session_ids:
                if self.delete_session(session_id):
                    deleted_count += 1
            
            # Clean up user sessions set
            self.redis_client.delete(user_sessions_key)
            
            logger.info(f"✅ Deleted {deleted_count} sessions for user {user_id}")
            return deleted_count
            
        except redis.RedisError as e:
            logger.error(f"❌ Failed to delete user sessions for {user_id}: {e}")
            return 0
    
    def store_oauth_tokens(self, session_id: str, tokens: Dict[str, Any]) -> bool:
        """
        Store OAuth tokens in session
        
        Args:
            session_id: Session identifier
            tokens: OAuth token data
            
        Returns:
            bool: Success status
        """
        session_data = self.get_session(session_id)
        if not session_data:
            logger.warning(f"⚠️ Cannot store tokens for non-existent session: {session_id}")
            return False
        
        # Update OAuth tokens
        session_data['oauth_tokens'] = tokens
        session_data['token_updated_at'] = datetime.utcnow().isoformat()
        
        return self.update_session(session_id, session_data)
    
    def get_oauth_tokens(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve OAuth tokens from session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dict containing OAuth tokens or None
        """
        session_data = self.get_session(session_id)
        if session_data:
            return session_data.get('oauth_tokens', {})
        return None
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions (Redis TTL handles this automatically)
        This method is for manual cleanup if needed
        
        Returns:
            int: Number of sessions cleaned up
        """
        try:
            # Get all session keys
            pattern = f"{self.key_prefix}:*"
            session_keys = self.redis_client.keys(pattern)
            
            cleaned_count = 0
            for key in session_keys:
                ttl = self.redis_client.ttl(key)
                if ttl == -2:  # Key doesn't exist
                    cleaned_count += 1
                elif ttl == -1:  # Key exists but has no TTL (shouldn't happen)
                    session_id = key.split(':')[-1]
                    self.redis_client.expire(key, self.session_timeout)
                    logger.warning(f"⚠️ Set TTL for session without expiry: {session_id}")
            
            if cleaned_count > 0:
                logger.info(f"🧹 Cleaned up {cleaned_count} expired sessions")
            
            return cleaned_count
            
        except redis.RedisError as e:
            logger.error(f"❌ Failed to cleanup expired sessions: {e}")
            return 0
    
    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get session statistics
        
        Returns:
            Dict with session statistics
        """
        try:
            # Count active sessions
            pattern = f"{self.key_prefix}:*"
            session_keys = self.redis_client.keys(pattern)
            active_sessions = len(session_keys)
            
            # Count user session sets
            user_pattern = f"{self.key_prefix}_user:*"
            user_keys = self.redis_client.keys(user_pattern)
            active_users = len(user_keys)
            
            # Redis info
            redis_info = self.redis_client.info()
            
            return {
                'active_sessions': active_sessions,
                'active_users': active_users,
                'redis_memory_used': redis_info.get('used_memory_human', 'Unknown'),
                'redis_connected_clients': redis_info.get('connected_clients', 0),
                'session_timeout': self.session_timeout,
                'key_prefix': self.key_prefix
            }
            
        except redis.RedisError as e:
            logger.error(f"❌ Failed to get session stats: {e}")
            return {'error': str(e)}

# Global session store instance
session_store: Optional[RedisSessionStore] = None

def init_session_store(redis_url: str = "redis://localhost:6379/0",
                      session_timeout: int = 3600) -> RedisSessionStore:
    """
    Initialize global session store instance
    
    Args:
        redis_url: Redis connection URL
        session_timeout: Session TTL in seconds
        
    Returns:
        RedisSessionStore instance
    """
    global session_store
    session_store = RedisSessionStore(redis_url, session_timeout)
    return session_store

def get_session_store() -> RedisSessionStore:
    """
    Get global session store instance
    
    Returns:
        RedisSessionStore instance
        
    Raises:
        RuntimeError: If session store not initialized
    """
    global session_store
    if session_store is None:
        raise RuntimeError("Session store not initialized. Call init_session_store() first.")
    return session_store

def redis_session_required(f):
    """
    Decorator to ensure Redis session store is available
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            get_session_store()
            return f(*args, **kwargs)
        except RuntimeError as e:
            logger.error(f"❌ Redis session store not available: {e}")
            raise
    return decorated_function

# Session management utilities
def create_user_session(user_data: Dict[str, Any]) -> str:
    """Create user session and return session ID"""
    store = get_session_store()
    return store.create_session(user_data)

def get_user_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get user session data"""
    store = get_session_store()
    return store.get_session(session_id)

def update_user_session(session_id: str, data: Dict[str, Any]) -> bool:
    """Update user session data"""
    store = get_session_store()
    return store.update_session(session_id, data)

def delete_user_session(session_id: str) -> bool:
    """Delete user session"""
    store = get_session_store()
    return store.delete_session(session_id)

def delete_all_user_sessions(user_id: str) -> int:
    """Delete all sessions for a user"""
    store = get_session_store()
    return store.delete_user_sessions(user_id)

def store_user_oauth_tokens(session_id: str, tokens: Dict[str, Any]) -> bool:
    """Store OAuth tokens for session"""
    store = get_session_store()
    return store.store_oauth_tokens(session_id, tokens)

def get_user_oauth_tokens(session_id: str) -> Optional[Dict[str, Any]]:
    """Get OAuth tokens from session"""
    store = get_session_store()
    return store.get_oauth_tokens(session_id)