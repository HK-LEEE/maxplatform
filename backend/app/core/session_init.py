"""
Session Management Initialization
Sets up Redis session centralization on application startup
"""

import logging
import os
from typing import Optional
from .redis_session import init_session_store
from .oauth_redis_integration import init_oauth_redis_manager
from ..services.token_blacklist import initialize_token_blacklist

logger = logging.getLogger(__name__)

def init_session_management() -> bool:
    """
    Initialize session management system
    
    Returns:
        bool: True if Redis is available, False if using database-only sessions
    """
    try:
        # Get Redis configuration from environment
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        session_timeout = int(os.getenv('SESSION_TIMEOUT', '3600'))  # 1 hour default
        
        logger.info(f"🔧 Initializing session management with Redis: {redis_url}")
        
        # Initialize Redis session store
        session_store = init_session_store(redis_url, session_timeout)
        
        # Initialize OAuth Redis manager
        oauth_manager = init_oauth_redis_manager()
        
        # Initialize token blacklist service
        blacklist_service = initialize_token_blacklist(session_store.redis_client)
        
        logger.info("✅ Session management initialized with Redis backing")
        logger.info("✅ Token blacklist service initialized for OAuth token invalidation")
        logger.info(f"📊 Session configuration: timeout={session_timeout}s, redis={redis_url}")
        
        return True
        
    except Exception as e:
        logger.warning(f"⚠️ Redis session initialization failed: {e}")
        logger.info("📝 Application will use database-only sessions (not recommended for production)")
        
        # Initialize OAuth manager anyway (it will handle Redis unavailability gracefully)
        try:
            init_oauth_redis_manager()
            logger.info("✅ OAuth manager initialized in database-only mode")
        except Exception as manager_error:
            logger.error(f"❌ OAuth manager initialization failed: {manager_error}")
        
        return False

async def startup_session_management():
    """
    Async startup function for session management
    Can be used with FastAPI app.add_event_handler("startup", startup_session_management)
    """
    redis_available = init_session_management()
    
    if redis_available:
        logger.info("🚀 Session management startup completed with Redis")
    else:
        logger.warning("🚀 Session management startup completed without Redis (database-only)")

def get_session_management_status() -> dict:
    """
    Get current session management status
    
    Returns:
        dict: Status information
    """
    from .oauth_redis_integration import get_oauth_redis_manager
    
    manager = get_oauth_redis_manager()
    
    if manager and manager.is_redis_available():
        stats = manager.get_session_stats()
        return {
            'redis_available': True,
            'session_mode': 'redis_backed',
            'stats': stats
        }
    else:
        return {
            'redis_available': False,
            'session_mode': 'database_only',
            'warning': 'Redis session store not available - using database sessions only'
        }