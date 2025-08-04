"""
Background task for automatic key rotation
Ensures signing keys are rotated periodically for security
"""
import asyncio
from datetime import datetime
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..services.jwks_service import jwks_service
import logging

logger = logging.getLogger(__name__)

async def rotate_signing_keys():
    """
    Background task to rotate signing keys periodically
    Runs daily to check if key rotation is needed
    """
    while True:
        try:
            db: Session = SessionLocal()
            try:
                # Check if rotation is needed
                current_key = jwks_service.get_active_signing_key(db)
                
                if not current_key:
                    # No active key, generate one
                    logger.info("No active signing key found, generating new key pair")
                    kid, private_key, public_key = jwks_service.generate_key_pair()
                    jwks_service.store_key_pair(db, kid, private_key, public_key)
                else:
                    # Check if current key needs rotation
                    from sqlalchemy import text
                    result = db.execute(
                        text("""
                            SELECT created_at 
                            FROM oauth_signing_keys 
                            WHERE kid = :kid
                        """),
                        {"kid": current_key["kid"]}
                    )
                    created_at = result.scalar()
                    
                    if created_at:
                        age_days = (datetime.utcnow() - created_at).days
                        if age_days >= jwks_service.rotation_days:
                            logger.info(f"Rotating signing keys, current key age: {age_days} days")
                            jwks_service.rotate_keys(db)
                
                # Cleanup expired keys
                deleted = jwks_service.cleanup_expired_keys(db)
                if deleted > 0:
                    logger.info(f"Cleaned up {deleted} expired keys")
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Key rotation task error: {str(e)}")
        
        # Wait for next check (daily)
        await asyncio.sleep(86400)  # 24 hours

def init_key_rotation_task():
    """
    Initialize key rotation task
    Called during application startup
    """
    # Ensure at least one active key exists
    db = SessionLocal()
    try:
        jwks_service.ensure_active_key_exists(db)
    finally:
        db.close()
    
    # Create background task
    asyncio.create_task(rotate_signing_keys())
    logger.info("Key rotation background task started")