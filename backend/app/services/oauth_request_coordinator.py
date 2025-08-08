"""
Backend OAuth Request Coordinator
Coordinates OAuth sync requests with session invalidation to prevent race conditions
"""

import redis
import json
import time
import logging
import asyncio
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class BackendOAuthCoordinator:
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client
        if not self.redis:
            # Use default Redis connection
            from ..config import settings
            self.redis = redis.Redis(
                host=getattr(settings, 'REDIS_HOST', 'localhost'),
                port=getattr(settings, 'REDIS_PORT', 6379),
                db=getattr(settings, 'REDIS_DB', 0),
                decode_responses=True
            )
        
        self.request_ttl = 30  # 30 seconds TTL for OAuth sync tracking
        self.max_wait_time = 10  # Maximum wait time for sync requests
        
    def _get_sync_key(self, user_id: str) -> str:
        """Get Redis key for tracking OAuth sync requests for a user"""
        return f"oauth_sync:{user_id}"
    
    def _get_sync_request_key(self, user_id: str, request_id: str) -> str:
        """Get Redis key for a specific OAuth sync request"""
        return f"oauth_sync:{user_id}:{request_id}"
    
    def register_oauth_sync_request(self, user_id: str, request_id: str, request_type: str = "token_refresh") -> bool:
        """
        Register an ongoing OAuth sync request for coordination
        
        Args:
            user_id: User ID associated with the request
            request_id: Unique request identifier
            request_type: Type of OAuth request (token_refresh, sync, etc.)
            
        Returns:
            True if successfully registered
        """
        try:
            # Request details
            request_data = {
                "request_id": request_id,
                "type": request_type,
                "user_id": user_id,
                "timestamp": time.time(),
                "status": "in_progress"
            }
            
            # Store individual request
            request_key = self._get_sync_request_key(user_id, request_id)
            self.redis.setex(request_key, self.request_ttl, json.dumps(request_data))
            
            # Add to user's active requests set
            sync_key = self._get_sync_key(user_id)
            self.redis.sadd(sync_key, request_id)
            self.redis.expire(sync_key, self.request_ttl)
            
            logger.info(f"🔀 OAuth sync request registered: {request_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to register OAuth sync request: {e}")
            return False
    
    def complete_oauth_sync_request(self, user_id: str, request_id: str) -> bool:
        """
        Mark an OAuth sync request as completed
        
        Args:
            user_id: User ID associated with the request
            request_id: Request identifier to complete
            
        Returns:
            True if successfully marked as completed
        """
        try:
            # Update request status
            request_key = self._get_sync_request_key(user_id, request_id)
            request_data = self.redis.get(request_key)
            
            if request_data:
                data = json.loads(request_data)
                data["status"] = "completed"
                data["completed_at"] = time.time()
                self.redis.setex(request_key, 5, json.dumps(data))  # Keep for 5 seconds for cleanup
            
            # Remove from user's active requests
            sync_key = self._get_sync_key(user_id)
            self.redis.srem(sync_key, request_id)
            
            logger.info(f"✅ OAuth sync request completed: {request_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to complete OAuth sync request: {e}")
            return False
    
    def get_active_oauth_sync_requests(self, user_id: str) -> List[Dict]:
        """
        Get all active OAuth sync requests for a user
        
        Args:
            user_id: User ID to check
            
        Returns:
            List of active request data
        """
        try:
            sync_key = self._get_sync_key(user_id)
            request_ids = self.redis.smembers(sync_key)
            
            active_requests = []
            for request_id in request_ids:
                request_key = self._get_sync_request_key(user_id, request_id)
                request_data = self.redis.get(request_key)
                
                if request_data:
                    data = json.loads(request_data)
                    # Check if request is still fresh
                    if time.time() - data["timestamp"] < self.request_ttl:
                        active_requests.append(data)
                    else:
                        # Clean up expired request
                        self.redis.srem(sync_key, request_id)
                        self.redis.delete(request_key)
            
            return active_requests
            
        except Exception as e:
            logger.error(f"❌ Failed to get active OAuth sync requests: {e}")
            return []
    
    def has_active_oauth_sync_requests(self, user_id: str) -> bool:
        """
        Check if user has any active OAuth sync requests
        
        Args:
            user_id: User ID to check
            
        Returns:
            True if there are active sync requests
        """
        active_requests = self.get_active_oauth_sync_requests(user_id)
        return len(active_requests) > 0
    
    async def wait_for_oauth_sync_completion(self, user_id: str, max_wait_seconds: Optional[int] = None) -> Dict:
        """
        Wait for all OAuth sync requests for a user to complete
        
        Args:
            user_id: User ID to wait for
            max_wait_seconds: Maximum time to wait (defaults to self.max_wait_time)
            
        Returns:
            Dict with completion status and details
        """
        wait_time = max_wait_seconds or self.max_wait_time
        start_time = time.time()
        check_interval = 0.5  # Check every 500ms
        
        logger.info(f"⏳ Waiting for OAuth sync completion for user {user_id} (max {wait_time}s)")
        
        while time.time() - start_time < wait_time:
            active_requests = self.get_active_oauth_sync_requests(user_id)
            
            if not active_requests:
                elapsed = time.time() - start_time
                logger.info(f"✅ OAuth sync completed for user {user_id} in {elapsed:.2f}s")
                return {
                    "completed": True,
                    "elapsed_time": elapsed,
                    "remaining_requests": 0
                }
            
            # Log progress
            request_types = [req.get("type", "unknown") for req in active_requests]
            logger.debug(f"⏳ Still waiting for {len(active_requests)} OAuth sync requests: {request_types}")
            
            await asyncio.sleep(check_interval)
        
        # Timeout reached
        remaining_requests = self.get_active_oauth_sync_requests(user_id)
        elapsed = time.time() - start_time
        
        logger.warning(f"⚠️ OAuth sync wait timeout for user {user_id} after {elapsed:.2f}s, {len(remaining_requests)} requests still active")
        
        return {
            "completed": False,
            "elapsed_time": elapsed,
            "remaining_requests": len(remaining_requests),
            "timeout": True,
            "active_requests": remaining_requests
        }
    
    def cleanup_expired_requests(self, user_id: Optional[str] = None) -> int:
        """
        Clean up expired OAuth sync requests
        
        Args:
            user_id: Specific user to clean up (None for all users)
            
        Returns:
            Number of cleaned up requests
        """
        try:
            cleaned_count = 0
            
            if user_id:
                # Clean up specific user
                cleaned_count += self._cleanup_user_requests(user_id)
            else:
                # Find all oauth_sync keys and clean them up
                sync_keys = self.redis.keys("oauth_sync:*")
                for key in sync_keys:
                    if ":" in key and len(key.split(":")) == 2:  # oauth_sync:user_id format
                        user_id_from_key = key.split(":")[1]
                        cleaned_count += self._cleanup_user_requests(user_id_from_key)
            
            if cleaned_count > 0:
                logger.info(f"🧹 Cleaned up {cleaned_count} expired OAuth sync requests")
                
            return cleaned_count
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup expired OAuth sync requests: {e}")
            return 0
    
    def _cleanup_user_requests(self, user_id: str) -> int:
        """Clean up expired requests for a specific user"""
        try:
            sync_key = self._get_sync_key(user_id)
            request_ids = self.redis.smembers(sync_key)
            cleaned_count = 0
            
            for request_id in request_ids:
                request_key = self._get_sync_request_key(user_id, request_id)
                request_data = self.redis.get(request_key)
                
                if not request_data:
                    # Request data missing, remove from set
                    self.redis.srem(sync_key, request_id)
                    cleaned_count += 1
                    continue
                
                try:
                    data = json.loads(request_data)
                    if time.time() - data["timestamp"] > self.request_ttl:
                        # Request expired
                        self.redis.srem(sync_key, request_id)
                        self.redis.delete(request_key)
                        cleaned_count += 1
                except json.JSONDecodeError:
                    # Invalid data, clean up
                    self.redis.srem(sync_key, request_id)
                    self.redis.delete(request_key)
                    cleaned_count += 1
            
            # Clean up empty sync key
            if self.redis.scard(sync_key) == 0:
                self.redis.delete(sync_key)
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup requests for user {user_id}: {e}")
            return 0
    
    def get_coordination_stats(self) -> Dict:
        """
        Get statistics about OAuth coordination
        
        Returns:
            Dict with coordination statistics
        """
        try:
            stats = {
                "total_users_with_active_requests": 0,
                "total_active_requests": 0,
                "requests_by_type": {},
                "oldest_request_age": 0,
                "coordination_healthy": True
            }
            
            sync_keys = self.redis.keys("oauth_sync:*")
            user_keys = [key for key in sync_keys if len(key.split(":")) == 2]
            
            stats["total_users_with_active_requests"] = len(user_keys)
            
            current_time = time.time()
            oldest_timestamp = current_time
            
            for sync_key in user_keys:
                user_id = sync_key.split(":")[1]
                active_requests = self.get_active_oauth_sync_requests(user_id)
                
                stats["total_active_requests"] += len(active_requests)
                
                for req in active_requests:
                    req_type = req.get("type", "unknown")
                    stats["requests_by_type"][req_type] = stats["requests_by_type"].get(req_type, 0) + 1
                    
                    req_timestamp = req.get("timestamp", current_time)
                    if req_timestamp < oldest_timestamp:
                        oldest_timestamp = req_timestamp
            
            if oldest_timestamp < current_time:
                stats["oldest_request_age"] = current_time - oldest_timestamp
            
            # Health check: flag if there are very old requests
            stats["coordination_healthy"] = stats["oldest_request_age"] < (self.request_ttl * 2)
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get coordination stats: {e}")
            return {"error": str(e), "coordination_healthy": False}

# Singleton instance
_coordinator_instance = None

def get_oauth_coordinator() -> BackendOAuthCoordinator:
    """Get singleton OAuth coordinator instance"""
    global _coordinator_instance
    if _coordinator_instance is None:
        _coordinator_instance = BackendOAuthCoordinator()
    return _coordinator_instance

# Context manager for OAuth sync request tracking
@asynccontextmanager
async def track_oauth_sync_request(user_id: str, request_id: str, request_type: str = "token_refresh"):
    """
    Context manager to automatically track OAuth sync requests
    
    Usage:
        async with track_oauth_sync_request("user123", "req456", "token_refresh"):
            # Perform OAuth sync operation
            result = await some_oauth_operation()
            return result
    """
    coordinator = get_oauth_coordinator()
    
    # Register request
    coordinator.register_oauth_sync_request(user_id, request_id, request_type)
    
    try:
        yield coordinator
    finally:
        # Always complete the request, even if there was an exception
        coordinator.complete_oauth_sync_request(user_id, request_id)