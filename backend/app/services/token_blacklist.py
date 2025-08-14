"""
JWT Token Blacklist Service for MaxPlatform OAuth Server
Redis-based token blacklisting to prevent reuse of invalidated tokens
"""

import json
import time
import hashlib
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
import redis
from jose import jwt

logger = logging.getLogger(__name__)

@dataclass
class BlacklistEntry:
    """Blacklisted token information"""
    token_hash: str
    user_id: str
    reason: str
    blacklisted_at: int
    expires_at: Optional[int] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class TokenBlacklistService:
    """
    Redis-based token blacklist service for MaxPlatform OAuth server
    Prevents reuse of tokens after session invalidation (e.g., prompt=login)
    """
    
    def __init__(
        self,
        redis_client: redis.Redis,
        key_prefix: str = "max_token_blacklist:",
        default_expiry: int = 86400 * 7  # 7 days
    ):
        self.redis = redis_client
        self.key_prefix = key_prefix
        self.default_expiry = default_expiry
        
        # Keys for different blacklist categories
        self.blacklist_key = f"{key_prefix}tokens"
        self.user_tokens_key = f"{key_prefix}user_tokens"
        self.prompt_login_key = f"{key_prefix}prompt_login"
    
    def _hash_token(self, token: str) -> str:
        """Create secure hash of token for storage"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    def _extract_user_id_from_token(self, token: str) -> Optional[str]:
        """Extract user ID from JWT token without signature verification"""
        try:
            decoded = jwt.decode(token, options={"verify_signature": False})
            return decoded.get("sub") or decoded.get("user_id") or str(decoded.get("id", ""))
        except Exception:
            return None
    
    def _extract_token_expiry(self, token: str) -> Optional[int]:
        """Extract expiry time from JWT token"""
        try:
            decoded = jwt.decode(token, options={"verify_signature": False})
            return decoded.get("exp")
        except Exception:
            return None
    
    def blacklist_token(
        self,
        token: str,
        user_id: Optional[str] = None,
        reason: str = "revoked",
        expires_at: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Add token to blacklist
        
        Args:
            token: JWT token to blacklist
            user_id: User ID associated with token (auto-extracted if None)
            reason: Reason for blacklisting
            expires_at: When the token naturally expires (auto-extracted if None)
            ip_address: IP address of the request
            user_agent: User agent of the request
            
        Returns:
            bool: True if successfully blacklisted
        """
        try:
            token_hash = self._hash_token(token)
            current_time = int(time.time())
            
            # Auto-extract user ID if not provided
            if not user_id:
                user_id = self._extract_user_id_from_token(token) or "unknown"
            
            # Auto-extract expiry if not provided
            if not expires_at:
                expires_at = self._extract_token_expiry(token)
            
            # Calculate TTL - use token expiry or default
            if expires_at:
                ttl = max(expires_at - current_time, 3600)  # At least 1 hour
            else:
                ttl = self.default_expiry
            
            # Create blacklist entry
            entry = BlacklistEntry(
                token_hash=token_hash,
                user_id=user_id,
                reason=reason,
                blacklisted_at=current_time,
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Store in Redis with pipeline for atomicity
            with self.redis.pipeline() as pipe:
                # Main blacklist entry
                pipe.setex(
                    f"{self.blacklist_key}:{token_hash}",
                    ttl,
                    json.dumps(asdict(entry))
                )
                
                # User token tracking
                pipe.sadd(f"{self.user_tokens_key}:{user_id}", token_hash)
                pipe.expire(f"{self.user_tokens_key}:{user_id}", ttl)
                
                # Execute all operations
                pipe.execute()
            
            logger.info(f"Token blacklisted: user={user_id}, reason={reason}, ttl={ttl}")
            return True
            
        except redis.RedisError as e:
            logger.error(f"Failed to blacklist token: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error blacklisting token: {e}")
            return False
    
    def is_token_blacklisted(self, token: str) -> bool:
        """
        Check if token is blacklisted
        
        Args:
            token: JWT token to check
            
        Returns:
            bool: True if token is blacklisted
        """
        try:
            token_hash = self._hash_token(token)
            exists = self.redis.exists(f"{self.blacklist_key}:{token_hash}")
            
            if exists:
                logger.debug(f"Token found in blacklist: {token_hash[:8]}...")
                return True
            return False
            
        except redis.RedisError as e:
            logger.error(f"Failed to check token blacklist: {e}")
            # Fail open - don't block valid tokens due to Redis issues
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking blacklist: {e}")
            return False
    
    def blacklist_user_tokens_by_bearer_token(
        self,
        current_bearer_token: Optional[str],
        user_id: str,
        reason: str = "prompt_login_invalidation",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> int:
        """
        Blacklist current user's bearer token when prompt=login is used
        
        Args:
            current_bearer_token: Bearer token from Authorization header
            user_id: User ID whose session is being invalidated
            reason: Reason for blacklisting
            ip_address: IP address of the request
            user_agent: User agent of the request
            
        Returns:
            int: Number of tokens blacklisted
        """
        blacklisted_count = 0
        
        if current_bearer_token:
            try:
                # Remove 'Bearer ' prefix if present
                if current_bearer_token.startswith("Bearer "):
                    current_bearer_token = current_bearer_token[7:]
                
                success = self.blacklist_token(
                    token=current_bearer_token,
                    user_id=user_id,
                    reason=reason,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                if success:
                    blacklisted_count = 1
                    logger.info(f"Bearer token blacklisted for user {user_id} due to {reason}")
                else:
                    logger.error(f"Failed to blacklist bearer token for user {user_id}")
                    
            except Exception as e:
                logger.error(f"Error blacklisting bearer token for user {user_id}: {e}")
        
        return blacklisted_count
    
    def blacklist_user_all_tokens(
        self,
        user_id: str,
        reason: str = "user_logout_all"
    ) -> int:
        """
        Blacklist all known tokens for a specific user
        
        Args:
            user_id: User ID whose tokens to blacklist
            reason: Reason for blacklisting
            
        Returns:
            int: Number of tokens blacklisted
        """
        try:
            user_tokens_key = f"{self.user_tokens_key}:{user_id}"
            token_hashes = self.redis.smembers(user_tokens_key)
            
            if not token_hashes:
                logger.info(f"No stored tokens found for user {user_id}")
                return 0
            
            current_time = int(time.time())
            blacklisted_count = 0
            
            # Create blacklist entries for all user tokens
            with self.redis.pipeline() as pipe:
                for token_hash in token_hashes:
                    if isinstance(token_hash, bytes):
                        token_hash = token_hash.decode()
                    
                    # Create blacklist entry
                    entry = BlacklistEntry(
                        token_hash=token_hash,
                        user_id=user_id,
                        reason=reason,
                        blacklisted_at=current_time
                    )
                    
                    pipe.setex(
                        f"{self.blacklist_key}:{token_hash}",
                        self.default_expiry,
                        json.dumps(asdict(entry))
                    )
                    blacklisted_count += 1
                
                # Clear user token set
                pipe.delete(user_tokens_key)
                pipe.execute()
            
            logger.info(f"Blacklisted {blacklisted_count} tokens for user {user_id}")
            return blacklisted_count
            
        except redis.RedisError as e:
            logger.error(f"Failed to blacklist user tokens: {e}")
            return 0
    
    def get_blacklist_entry(self, token: str) -> Optional[BlacklistEntry]:
        """
        Get blacklist entry details for a token
        
        Args:
            token: JWT token to lookup
            
        Returns:
            BlacklistEntry or None if not found
        """
        try:
            token_hash = self._hash_token(token)
            entry_data = self.redis.get(f"{self.blacklist_key}:{token_hash}")
            
            if entry_data:
                entry_dict = json.loads(entry_data)
                return BlacklistEntry(**entry_dict)
            return None
            
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.error(f"Failed to get blacklist entry: {e}")
            return None
    
    def cleanup_expired_entries(self) -> int:
        """
        Clean up expired blacklist entries
        
        Returns:
            int: Number of entries cleaned up
        """
        try:
            pattern = f"{self.blacklist_key}:*"
            keys = self.redis.keys(pattern)
            
            cleaned_count = 0
            current_time = int(time.time())
            
            for key in keys:
                try:
                    entry_data = self.redis.get(key)
                    if entry_data:
                        entry_dict = json.loads(entry_data)
                        expires_at = entry_dict.get('expires_at')
                        
                        # Remove if token has naturally expired
                        if expires_at and current_time > expires_at:
                            self.redis.delete(key)
                            cleaned_count += 1
                except (json.JSONDecodeError, KeyError):
                    # Remove malformed entries
                    self.redis.delete(key)
                    cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired blacklist entries")
            return cleaned_count
            
        except redis.RedisError as e:
            logger.error(f"Failed to cleanup expired entries: {e}")
            return 0


# Global instance (will be initialized with Redis connection)
token_blacklist: Optional[TokenBlacklistService] = None

def initialize_token_blacklist(redis_client: redis.Redis) -> TokenBlacklistService:
    """Initialize global token blacklist instance"""
    global token_blacklist
    token_blacklist = TokenBlacklistService(redis_client)
    logger.info("MaxPlatform token blacklist service initialized with Redis backend")
    return token_blacklist

def get_token_blacklist() -> Optional[TokenBlacklistService]:
    """Get global token blacklist instance"""
    return token_blacklist