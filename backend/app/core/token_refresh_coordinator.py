"""
Token Refresh Coordinator with Redis-based Distributed Locking
Prevents race conditions during token refresh operations
"""

import logging
import time
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
import redis
from redis.exceptions import RedisError
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class TokenRefreshCoordinator:
    """
    Coordinates token refresh operations using Redis distributed locks
    to prevent race conditions and duplicate refresh attempts
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.lock_ttl = 5  # seconds
        self.lock_retry_delay = 0.1  # seconds
        self.max_lock_wait = 2  # seconds
        self.refresh_cache_ttl = 10  # seconds for caching successful refreshes
    
    @contextmanager
    def acquire_refresh_lock(self, user_id: str, client_id: str, session_id: str = None):
        """
        Acquire a distributed lock for token refresh operation with session isolation
        
        Args:
            user_id: User identifier
            client_id: OAuth client identifier
            session_id: Optional session identifier for session-scoped locking
            
        Yields:
            Lock key if acquired, raises exception if timeout
        """
        # Use session-scoped locking if session_id provided, otherwise fall back to user+client
        if session_id:
            lock_key = f"token_refresh_lock:{user_id}:{client_id}:{session_id}"
        else:
            lock_key = f"token_refresh_lock:{user_id}:{client_id}"
        lock_value = f"{time.time()}_{id(self)}"  # Unique lock identifier
        start_time = time.time()
        
        try:
            # Try to acquire lock with retry logic
            while (time.time() - start_time) < self.max_lock_wait:
                # Set lock with NX (only if not exists) and EX (expiry)
                acquired = self.redis.set(
                    lock_key, 
                    lock_value, 
                    nx=True, 
                    ex=self.lock_ttl
                )
                
                if acquired:
                    logger.info(f"✅ Acquired refresh lock for user={user_id}, client={client_id}")
                    try:
                        yield lock_key
                    finally:
                        # Release lock only if we still own it
                        self._release_lock(lock_key, lock_value)
                    return
                
                # Check if there's a recent successful refresh we can use
                # Use session-scoped cache if session_id provided
                cached_result = self._get_cached_refresh(user_id, client_id, session_id)
                if cached_result:
                    if session_id:
                        logger.info(f"📦 Using cached refresh result for user={user_id}, client={client_id}, session={session_id}")
                    else:
                        logger.info(f"📦 Using cached refresh result for user={user_id}, client={client_id}")
                    yield None  # Signal to use cached result
                    return
                
                # Wait before retry
                time.sleep(self.lock_retry_delay)
            
            # Timeout reached
            logger.warning(f"⏱️ Lock acquisition timeout for user={user_id}, client={client_id}")
            raise TimeoutError(f"Could not acquire refresh lock within {self.max_lock_wait}s")
            
        except RedisError as e:
            logger.error(f"❌ Redis error during lock acquisition: {e}")
            raise
    
    def _release_lock(self, lock_key: str, lock_value: str):
        """
        Safely release a lock only if we still own it
        
        Args:
            lock_key: Redis key for the lock
            lock_value: Our unique lock value
        """
        try:
            # Use Lua script for atomic check-and-delete
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            
            result = self.redis.eval(lua_script, 1, lock_key, lock_value)
            
            if result:
                logger.debug(f"🔓 Released refresh lock: {lock_key}")
            else:
                logger.debug(f"🔒 Lock already released or expired: {lock_key}")
                
        except RedisError as e:
            logger.error(f"❌ Error releasing lock {lock_key}: {e}")
    
    def cache_refresh_result(
        self, 
        user_id: str, 
        client_id: str, 
        access_token: str,
        refresh_token: str,
        expires_in: int,
        session_id: str = None
    ):
        """
        Cache successful refresh result for fast retrieval with session isolation
        
        Args:
            user_id: User identifier
            client_id: OAuth client identifier
            access_token: New access token
            refresh_token: New refresh token
            expires_in: Token expiry in seconds
            session_id: Optional session identifier for session-scoped caching
        """
        # Use session-scoped cache if session_id provided
        if session_id:
            cache_key = f"token_refresh_cache:{user_id}:{client_id}:{session_id}"
        else:
            cache_key = f"token_refresh_cache:{user_id}:{client_id}"
        cache_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": expires_in,
            "cached_at": time.time()
        }
        
        try:
            # Store with short TTL to handle concurrent requests
            self.redis.setex(
                cache_key,
                self.refresh_cache_ttl,
                str(cache_data)
            )
            if session_id:
                logger.debug(f"💾 Cached refresh result for user={user_id}, client={client_id}, session={session_id}")
            else:
                logger.debug(f"💾 Cached refresh result for user={user_id}, client={client_id}")
            
        except RedisError as e:
            logger.error(f"❌ Error caching refresh result: {e}")
    
    def _get_cached_refresh(
        self, 
        user_id: str, 
        client_id: str,
        session_id: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached refresh result if available and valid with session isolation
        
        Args:
            user_id: User identifier
            client_id: OAuth client identifier
            session_id: Optional session identifier for session-scoped caching
            
        Returns:
            Cached token data if available and fresh, None otherwise
        """
        # Use session-scoped cache if session_id provided
        if session_id:
            cache_key = f"token_refresh_cache:{user_id}:{client_id}:{session_id}"
        else:
            cache_key = f"token_refresh_cache:{user_id}:{client_id}"
        
        try:
            cached = self.redis.get(cache_key)
            
            if cached:
                import ast
                cache_data = ast.literal_eval(cached)
                
                # Check if cache is still fresh (within TTL window)
                cache_age = time.time() - cache_data.get("cached_at", 0)
                if cache_age < self.refresh_cache_ttl:
                    logger.debug(f"✅ Found fresh cached refresh (age={cache_age:.1f}s)")
                    return cache_data
                    
        except (RedisError, ValueError, SyntaxError) as e:
            logger.debug(f"Cache retrieval failed: {e}")
        
        return None
    
    def is_refresh_in_progress(self, user_id: str, client_id: str) -> bool:
        """
        Check if a refresh operation is currently in progress
        
        Args:
            user_id: User identifier
            client_id: OAuth client identifier
            
        Returns:
            True if refresh is in progress, False otherwise
        """
        lock_key = f"token_refresh_lock:{user_id}:{client_id}"
        
        try:
            return self.redis.exists(lock_key) > 0
        except RedisError as e:
            logger.error(f"❌ Error checking refresh status: {e}")
            return False
    
    def clear_refresh_cache(self, user_id: str, client_id: str):
        """
        Clear cached refresh result (useful after logout or revocation)
        
        Args:
            user_id: User identifier
            client_id: OAuth client identifier
        """
        cache_key = f"token_refresh_cache:{user_id}:{client_id}"
        
        try:
            self.redis.delete(cache_key)
            logger.debug(f"🧹 Cleared refresh cache for user={user_id}, client={client_id}")
        except RedisError as e:
            logger.error(f"❌ Error clearing refresh cache: {e}")
    
    def get_refresh_metrics(self) -> Dict[str, int]:
        """
        Get metrics about ongoing refresh operations
        
        Returns:
            Dictionary with refresh operation metrics
        """
        try:
            # Count active locks
            lock_pattern = "token_refresh_lock:*"
            active_locks = len(self.redis.keys(lock_pattern))
            
            # Count cached results
            cache_pattern = "token_refresh_cache:*"
            cached_results = len(self.redis.keys(cache_pattern))
            
            return {
                "active_refresh_locks": active_locks,
                "cached_refresh_results": cached_results
            }
            
        except RedisError as e:
            logger.error(f"❌ Error getting refresh metrics: {e}")
            return {
                "active_refresh_locks": 0,
                "cached_refresh_results": 0
            }


# Singleton instance management
_coordinator_instance: Optional[TokenRefreshCoordinator] = None

def get_token_refresh_coordinator(redis_client: redis.Redis) -> TokenRefreshCoordinator:
    """
    Get or create the singleton TokenRefreshCoordinator instance
    
    Args:
        redis_client: Redis client instance
        
    Returns:
        TokenRefreshCoordinator instance
    """
    global _coordinator_instance
    
    if _coordinator_instance is None:
        _coordinator_instance = TokenRefreshCoordinator(redis_client)
        logger.info("✅ Token Refresh Coordinator initialized")
    
    return _coordinator_instance