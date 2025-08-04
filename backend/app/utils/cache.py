"""
Redis Caching Strategy - Wave 3 Implementation
Provides intelligent caching for LLM model and permission queries
"""

import json
import logging
import hashlib
from typing import Any, Optional, Dict, List, Callable, Union
from datetime import datetime, timedelta
from functools import wraps
import asyncio

import redis.asyncio as redis
from redis.exceptions import RedisError

from ..config import settings

logger = logging.getLogger(__name__)

class CacheConfig:
    """Cache configuration constants"""
    
    # Cache TTL (Time To Live) in seconds
    SHORT_TTL = 5 * 60      # 5 minutes
    MEDIUM_TTL = 30 * 60    # 30 minutes  
    LONG_TTL = 2 * 60 * 60  # 2 hours
    VERY_LONG_TTL = 24 * 60 * 60  # 24 hours
    
    # Cache key prefixes
    PREFIX_MODEL = "llm:model"
    PREFIX_MODELS_LIST = "llm:models_list"
    PREFIX_PERMISSIONS = "llm:permissions"
    PREFIX_USER_ACCESS = "llm:user_access"
    PREFIX_MODEL_COUNT = "llm:model_count"
    
    # Cache tags for invalidation
    TAG_MODEL = "model"
    TAG_PERMISSIONS = "permissions"
    TAG_USER = "user"

class CacheManager:
    """Redis cache manager with intelligent caching strategies"""
    
    def __init__(self):
        self.redis_client = None
        self._connected = False
    
    async def connect(self):
        """Initialize Redis connection"""
        try:
            redis_url = getattr(settings, 'redis_url', 'redis://localhost:6379/0')
            self.redis_client = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            
            # Test connection
            await self.redis_client.ping()
            self._connected = True
            logger.info("Redis cache connected successfully")
            
        except Exception as e:
            self._connected = False
            logger.warning(f"Redis connection failed: {e}. Caching disabled.")
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            self._connected = False
    
    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate consistent cache key"""
        # Create a deterministic key from arguments
        key_parts = [prefix]
        
        # Add positional arguments
        for arg in args:
            if isinstance(arg, (dict, list)):
                key_parts.append(hashlib.md5(json.dumps(arg, sort_keys=True).encode()).hexdigest())
            else:
                key_parts.append(str(arg))
        
        # Add keyword arguments
        for key, value in sorted(kwargs.items()):
            if isinstance(value, (dict, list)):
                key_parts.append(f"{key}:{hashlib.md5(json.dumps(value, sort_keys=True).encode()).hexdigest()}")
            else:
                key_parts.append(f"{key}:{value}")
        
        return ":".join(key_parts)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self._connected:
            return None
        
        try:
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except (RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = CacheConfig.MEDIUM_TTL) -> bool:
        """Set value in cache with TTL"""
        if not self._connected:
            return False
        
        try:
            serialized_value = json.dumps(value, default=str)
            await self.redis_client.setex(key, ttl, serialized_value)
            return True
        except (RedisError, json.JSONEncodeError) as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self._connected:
            return False
        
        try:
            await self.redis_client.delete(key)
            return True
        except RedisError as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        if not self._connected:
            return 0
        
        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                return await self.redis_client.delete(*keys)
            return 0
        except RedisError as e:
            logger.warning(f"Cache delete pattern error for {pattern}: {e}")
            return 0
    
    async def invalidate_model_cache(self, model_id: Optional[str] = None):
        """Invalidate model-related cache entries"""
        patterns = [
            f"{CacheConfig.PREFIX_MODELS_LIST}:*",
            f"{CacheConfig.PREFIX_MODEL_COUNT}:*"
        ]
        
        if model_id:
            patterns.extend([
                f"{CacheConfig.PREFIX_MODEL}:{model_id}:*",
                f"{CacheConfig.PREFIX_PERMISSIONS}:{model_id}:*",
                f"{CacheConfig.PREFIX_USER_ACCESS}:*:{model_id}:*"
            ])
        else:
            patterns.extend([
                f"{CacheConfig.PREFIX_MODEL}:*",
                f"{CacheConfig.PREFIX_PERMISSIONS}:*",
                f"{CacheConfig.PREFIX_USER_ACCESS}:*"
            ])
        
        total_deleted = 0
        for pattern in patterns:
            deleted = await self.delete_pattern(pattern)
            total_deleted += deleted
        
        logger.info(f"Invalidated {total_deleted} cache entries for model cache")
        return total_deleted
    
    async def invalidate_user_cache(self, user_id: str):
        """Invalidate user-specific cache entries"""
        patterns = [
            f"{CacheConfig.PREFIX_USER_ACCESS}:{user_id}:*",
            f"{CacheConfig.PREFIX_MODELS_LIST}:{user_id}:*"
        ]
        
        total_deleted = 0
        for pattern in patterns:
            deleted = await self.delete_pattern(pattern)
            total_deleted += deleted
        
        logger.info(f"Invalidated {total_deleted} cache entries for user {user_id}")
        return total_deleted

# Global cache manager instance
cache_manager = CacheManager()

# Caching decorators
def cache_result(
    prefix: str,
    ttl: int = CacheConfig.MEDIUM_TTL,
    key_args: Optional[List[str]] = None,
    invalidate_on: Optional[List[str]] = None
):
    """
    Decorator to cache function results
    
    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds
        key_args: Specific arguments to include in cache key
        invalidate_on: Events that should invalidate this cache
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_args:
                # Use only specified arguments for key generation
                cache_key_args = []
                cache_key_kwargs = {}
                
                for i, arg_name in enumerate(key_args):
                    if i < len(args):
                        cache_key_args.append(args[i])
                    elif arg_name in kwargs:
                        cache_key_kwargs[arg_name] = kwargs[arg_name]
                
                cache_key = cache_manager._generate_cache_key(prefix, *cache_key_args, **cache_key_kwargs)
            else:
                cache_key = cache_manager._generate_cache_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_result = await cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for key: {cache_key}")
                return cached_result
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache the result
            if result is not None:
                await cache_manager.set(cache_key, result, ttl)
                logger.debug(f"Cached result for key: {cache_key}")
            
            return result
        
        return wrapper
    return decorator

# Specific caching functions for LLM models
class LLMModelCache:
    """Specialized caching for LLM model operations"""
    
    @staticmethod
    async def get_model(model_id: str) -> Optional[Dict[str, Any]]:
        """Get cached model data"""
        key = cache_manager._generate_cache_key(CacheConfig.PREFIX_MODEL, model_id)
        return await cache_manager.get(key)
    
    @staticmethod
    async def set_model(model_id: str, model_data: Dict[str, Any], ttl: int = CacheConfig.LONG_TTL):
        """Cache model data"""
        key = cache_manager._generate_cache_key(CacheConfig.PREFIX_MODEL, model_id)
        return await cache_manager.set(key, model_data, ttl)
    
    @staticmethod
    async def get_models_list(user_id: str, accessible_only: bool = True) -> Optional[List[Dict[str, Any]]]:
        """Get cached models list for user"""
        key = cache_manager._generate_cache_key(
            CacheConfig.PREFIX_MODELS_LIST, 
            user_id, 
            accessible_only=accessible_only
        )
        return await cache_manager.get(key)
    
    @staticmethod
    async def set_models_list(
        user_id: str, 
        models_data: List[Dict[str, Any]], 
        accessible_only: bool = True,
        ttl: int = CacheConfig.MEDIUM_TTL
    ):
        """Cache models list for user"""
        key = cache_manager._generate_cache_key(
            CacheConfig.PREFIX_MODELS_LIST, 
            user_id, 
            accessible_only=accessible_only
        )
        return await cache_manager.set(key, models_data, ttl)
    
    @staticmethod
    async def get_model_permissions(model_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached model permissions"""
        key = cache_manager._generate_cache_key(CacheConfig.PREFIX_PERMISSIONS, model_id)
        return await cache_manager.get(key)
    
    @staticmethod
    async def set_model_permissions(
        model_id: str, 
        permissions_data: List[Dict[str, Any]], 
        ttl: int = CacheConfig.SHORT_TTL
    ):
        """Cache model permissions (shorter TTL as permissions change frequently)"""
        key = cache_manager._generate_cache_key(CacheConfig.PREFIX_PERMISSIONS, model_id)
        return await cache_manager.set(key, permissions_data, ttl)
    
    @staticmethod
    async def get_user_model_access(user_id: str, model_id: str) -> Optional[bool]:
        """Get cached user access to specific model"""
        key = cache_manager._generate_cache_key(CacheConfig.PREFIX_USER_ACCESS, user_id, model_id)
        return await cache_manager.get(key)
    
    @staticmethod
    async def set_user_model_access(
        user_id: str, 
        model_id: str, 
        has_access: bool, 
        ttl: int = CacheConfig.SHORT_TTL
    ):
        """Cache user access to specific model"""
        key = cache_manager._generate_cache_key(CacheConfig.PREFIX_USER_ACCESS, user_id, model_id)
        return await cache_manager.set(key, has_access, ttl)

# Cache invalidation events
class CacheEvents:
    """Cache invalidation events"""
    
    @staticmethod
    async def on_model_created(model_id: str):
        """Handle model creation event"""
        await cache_manager.invalidate_model_cache()
    
    @staticmethod
    async def on_model_updated(model_id: str):
        """Handle model update event"""
        await cache_manager.invalidate_model_cache(model_id)
    
    @staticmethod
    async def on_model_deleted(model_id: str):
        """Handle model deletion event"""
        await cache_manager.invalidate_model_cache(model_id)
    
    @staticmethod
    async def on_permission_granted(model_id: str, user_id: Optional[str] = None):
        """Handle permission granted event"""
        await cache_manager.invalidate_model_cache(model_id)
        if user_id:
            await cache_manager.invalidate_user_cache(user_id)
    
    @staticmethod
    async def on_permission_revoked(model_id: str, user_id: Optional[str] = None):
        """Handle permission revoked event"""
        await cache_manager.invalidate_model_cache(model_id)
        if user_id:
            await cache_manager.invalidate_user_cache(user_id)

# Startup and shutdown hooks
async def initialize_cache():
    """Initialize cache on application startup"""
    await cache_manager.connect()

async def cleanup_cache():
    """Cleanup cache on application shutdown"""
    await cache_manager.disconnect()