"""
Background task for cleaning up expired nonces
Ensures nonce table doesn't grow indefinitely
"""
import asyncio
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..services.nonce_service import nonce_service
import logging

logger = logging.getLogger(__name__)

async def cleanup_expired_nonces():
    """
    Background task to cleanup expired nonces
    Runs every hour to remove old nonces
    """
    while True:
        try:
            db: Session = SessionLocal()
            try:
                # Cleanup expired nonces
                deleted = nonce_service.cleanup_expired_nonces(db)
                if deleted > 0:
                    logger.info(f"Cleaned up {deleted} expired nonces")
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Nonce cleanup task error: {str(e)}")
        
        # Wait for next check (hourly)
        await asyncio.sleep(3600)  # 1 hour

def init_nonce_cleanup_task():
    """
    Initialize nonce cleanup task
    Called during application startup
    """
    # Create background task
    asyncio.create_task(cleanup_expired_nonces())
    logger.info("Nonce cleanup background task started")