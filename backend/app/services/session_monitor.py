"""
Session Monitor Service for JWT-Redis Session Consistency
주기적으로 JWT-Redis 세션 일관성을 확인하고 자동 복구
"""

import asyncio
import json
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from ..config import settings
from ..database import SessionLocal
from ..models import User
from ..core.redis_session import get_session_store, create_user_session

logger = logging.getLogger(__name__)


class SessionMonitor:
    """
    세션 불일치 감지 및 자동 복구 서비스
    JWT와 Redis 세션 간의 일관성을 보장
    """
    
    def __init__(self):
        """Initialize session monitor"""
        self.inconsistency_counter = 0
        self.recovery_threshold = 10  # 10회 이상 불일치 시 알림
        self.check_interval = 60  # 1분마다 확인
        self.active_tokens = {}  # 활성 JWT 토큰 추적
        self.session_store = None
        self.monitoring_task = None
        self.is_running = False
        self.stats = {
            "total_checks": 0,
            "inconsistencies_found": 0,
            "sessions_recovered": 0,
            "errors": 0,
            "last_check": None
        }
        
        self._init_session_store()
    
    def _init_session_store(self):
        """Initialize Redis session store"""
        try:
            self.session_store = get_session_store()
            logger.info("✅ SessionMonitor initialized with Redis")
        except RuntimeError:
            logger.warning("⚠️ Redis not available - SessionMonitor disabled")
            self.session_store = None
    
    async def start_monitoring(self):
        """
        Start the session monitoring task
        """
        if not self.session_store:
            logger.warning("SessionMonitor cannot start without Redis")
            return
        
        if self.is_running:
            logger.warning("SessionMonitor is already running")
            return
        
        self.is_running = True
        self.monitoring_task = asyncio.create_task(self.check_session_consistency())
        logger.info("✅ SessionMonitor started")
    
    async def stop_monitoring(self):
        """
        Stop the session monitoring task
        """
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("SessionMonitor stopped")
    
    async def check_session_consistency(self):
        """
        주기적으로 JWT-Redis 세션 일관성 확인
        """
        while self.is_running:
            try:
                await self._perform_consistency_check()
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Session monitor error: {e}")
                self.stats["errors"] += 1
                await asyncio.sleep(self.check_interval)
    
    async def _perform_consistency_check(self):
        """
        Perform a single consistency check cycle
        """
        start_time = time.time()
        self.stats["total_checks"] += 1
        self.stats["last_check"] = datetime.utcnow().isoformat()
        
        logger.debug("Starting session consistency check")
        
        # Get all active Redis sessions
        pattern = f"{self.session_store.key_prefix}:*"
        session_keys = self.session_store.redis_client.keys(pattern)
        
        sessions_checked = 0
        inconsistencies = 0
        recoveries = 0
        
        for session_key in session_keys:
            if not self.is_running:
                break
            
            try:
                # Get session data
                session_data = self.session_store.redis_client.get(session_key)
                if not session_data:
                    continue
                
                session = json.loads(session_data)
                user_id = session.get("user_id")
                jwt_exp = session.get("jwt_exp")
                
                if not user_id:
                    continue
                
                sessions_checked += 1
                
                # Check if JWT has expired
                if jwt_exp and jwt_exp < time.time():
                    # JWT expired - delete Redis session
                    session_id = session_key.split(":")[-1]
                    self.session_store.delete_session(session_id)
                    logger.info(f"Deleted expired Redis session {session_id} for user {user_id}")
                    continue
                
                # Check if session is orphaned (no JWT but Redis exists)
                if session.get("source") == "jwt_recovery":
                    # This session was auto-recovered, check if it's still valid
                    created_at = session.get("created_at")
                    if created_at:
                        # If session is older than 1 hour and marked as recovered, verify it
                        session_age = time.time() - (created_at if isinstance(created_at, (int, float)) else 0)
                        if session_age > 3600:  # 1 hour
                            await self._verify_recovered_session(session_key, session)
                
            except Exception as e:
                logger.error(f"Error checking session {session_key}: {e}")
                self.stats["errors"] += 1
        
        # Check for users with JWT but no Redis session (from recent requests)
        await self._check_active_tokens()
        
        elapsed = time.time() - start_time
        
        if inconsistencies > 0:
            logger.info(f"Session check completed: {sessions_checked} sessions, "
                       f"{inconsistencies} inconsistencies, {recoveries} recovered "
                       f"(took {elapsed:.2f}s)")
        else:
            logger.debug(f"Session check completed: {sessions_checked} sessions checked "
                        f"(took {elapsed:.2f}s)")
    
    async def _verify_recovered_session(self, session_key: str, session: dict):
        """
        Verify that a recovered session is still valid
        
        Args:
            session_key: Redis key for the session
            session: Session data
        """
        user_id = session.get("user_id")
        
        try:
            # Check if user still exists and is active
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == user_id).first()
                
                if not user or not user.is_active:
                    # User doesn't exist or is inactive - delete session
                    session_id = session_key.split(":")[-1]
                    self.session_store.delete_session(session_id)
                    logger.info(f"Deleted orphaned session {session_id} for inactive user {user_id}")
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error verifying recovered session: {e}")
    
    async def _check_active_tokens(self):
        """
        Check recently seen JWT tokens for Redis session consistency
        """
        # This would integrate with request tracking to monitor active JWTs
        # For now, we'll rely on the middleware to handle this
        pass
    
    async def recover_session(self, user_id: str, jwt_payload: dict) -> bool:
        """
        Redis 세션 자동 복구
        
        Args:
            user_id: User ID
            jwt_payload: Decoded JWT payload
            
        Returns:
            Success status
        """
        if not self.session_store:
            return False
        
        try:
            ttl = jwt_payload.get("exp", 0) - int(time.time())
            
            if ttl <= 0:
                logger.debug(f"JWT already expired for user {user_id}, skipping recovery")
                return False
            
            # Get user from database
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == user_id).first()
                
                if not user:
                    logger.warning(f"User {user_id} not found for session recovery")
                    return False
                
                session_data = {
                    "id": str(user.id),
                    "user_id": str(user.id),
                    "email": user.email,
                    "name": user.real_name or user.display_name or user.email,
                    "is_admin": user.is_admin,
                    "is_active": user.is_active,
                    "groups": [{"id": str(g.id), "name": g.name} for g in user.groups] if user.groups else [],
                    "roles": [{"id": str(r.id), "name": r.name} for r in user.roles] if user.roles else [],
                    "auto_recovered": True,
                    "recovered_at": datetime.utcnow().isoformat(),
                    "recovered_by": "SessionMonitor",
                    "jwt_exp": jwt_payload.get("exp"),
                    "source": "monitor_recovery"
                }
                
                # Override session timeout with JWT remaining time
                original_timeout = self.session_store.session_timeout
                self.session_store.session_timeout = ttl
                
                session_id = create_user_session(session_data)
                
                # Restore original timeout
                self.session_store.session_timeout = original_timeout
                
                logger.info(f"✅ Auto-recovered Redis session {session_id} for user {user_id}")
                
                self.stats["sessions_recovered"] += 1
                self.inconsistency_counter += 1
                
                # Check if we need to send an alert
                if self.inconsistency_counter >= self.recovery_threshold:
                    await self._send_admin_alert(
                        "High session inconsistency rate detected",
                        f"Recovered {self.inconsistency_counter} sessions in recent checks"
                    )
                    self.inconsistency_counter = 0
                
                return True
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Failed to recover session for user {user_id}: {e}")
            self.stats["errors"] += 1
            return False
    
    async def _send_admin_alert(self, subject: str, message: str):
        """
        Send alert to administrators
        
        Args:
            subject: Alert subject
            message: Alert message
        """
        # In production, this would send an email or notification
        logger.warning(f"ADMIN ALERT - {subject}: {message}")
        
        # Log to a dedicated alert file or monitoring system
        alert_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "subject": subject,
            "message": message,
            "stats": self.stats
        }
        
        logger.critical(f"SESSION_MONITOR_ALERT: {json.dumps(alert_data)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get monitoring statistics
        
        Returns:
            Dictionary with monitoring stats
        """
        return {
            **self.stats,
            "is_running": self.is_running,
            "inconsistency_counter": self.inconsistency_counter,
            "check_interval": self.check_interval
        }
    
    async def force_check(self) -> Dict[str, Any]:
        """
        Force an immediate consistency check
        
        Returns:
            Check results
        """
        if not self.session_store:
            return {"error": "Redis not available"}
        
        logger.info("Forcing session consistency check")
        
        start_time = time.time()
        await self._perform_consistency_check()
        elapsed = time.time() - start_time
        
        return {
            "elapsed_time": elapsed,
            "stats": self.get_stats()
        }


# Global session monitor instance
_session_monitor: Optional[SessionMonitor] = None


def get_session_monitor() -> SessionMonitor:
    """
    Get global session monitor instance
    
    Returns:
        SessionMonitor instance
    """
    global _session_monitor
    if _session_monitor is None:
        _session_monitor = SessionMonitor()
    return _session_monitor


async def start_session_monitoring():
    """
    Start the global session monitoring service
    """
    monitor = get_session_monitor()
    await monitor.start_monitoring()


async def stop_session_monitoring():
    """
    Stop the global session monitoring service
    """
    monitor = get_session_monitor()
    await monitor.stop_monitoring()