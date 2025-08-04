"""
OIDC Nonce Service
Manages nonces for replay attack prevention
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

class NonceService:
    """Service for managing nonces for OIDC security"""
    
    def generate_nonce(self) -> str:
        """Generate a cryptographically secure nonce"""
        return secrets.token_urlsafe(32)
    
    def store_nonce(
        self,
        db: Session,
        nonce: str,
        client_id: str,
        user_id: Optional[str] = None,
        expires_in_minutes: int = 10
    ) -> bool:
        """Store nonce for later validation"""
        try:
            expires_at = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
            nonce_hash = hashlib.sha256(nonce.encode()).hexdigest()
            
            db.execute(
                text("""
                    INSERT INTO oauth_nonces 
                    (nonce_hash, client_id, user_id, expires_at)
                    VALUES (:nonce_hash, :client_id, :user_id, :expires_at)
                """),
                {
                    "nonce_hash": nonce_hash,
                    "client_id": client_id,
                    "user_id": user_id,
                    "expires_at": expires_at
                }
            )
            db.commit()
            logger.info(f"Stored nonce for client {client_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store nonce: {str(e)}")
            db.rollback()
            return False
    
    def validate_nonce(
        self,
        db: Session,
        nonce: str,
        client_id: str,
        consume: bool = True
    ) -> bool:
        """Validate and optionally consume a nonce"""
        try:
            nonce_hash = hashlib.sha256(nonce.encode()).hexdigest()
            
            # Check if nonce exists and is valid
            result = db.execute(
                text("""
                    SELECT id FROM oauth_nonces
                    WHERE nonce_hash = :nonce_hash
                    AND client_id = :client_id
                    AND expires_at > NOW()
                    AND used_at IS NULL
                """),
                {
                    "nonce_hash": nonce_hash,
                    "client_id": client_id
                }
            )
            
            nonce_record = result.first()
            if not nonce_record:
                logger.warning(f"Invalid or expired nonce for client {client_id}")
                return False
            
            if consume:
                # Mark as used
                db.execute(
                    text("""
                        UPDATE oauth_nonces
                        SET used_at = NOW()
                        WHERE id = :id
                    """),
                    {"id": nonce_record[0]}
                )
                db.commit()
                logger.info(f"Consumed nonce for client {client_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Nonce validation error: {str(e)}")
            db.rollback()
            return False
    
    def cleanup_expired_nonces(self, db: Session) -> int:
        """Remove expired nonces"""
        try:
            result = db.execute(
                text("""
                    DELETE FROM oauth_nonces
                    WHERE expires_at < NOW()
                    OR used_at < NOW() - INTERVAL '1 hour'
                """)
            )
            
            count = result.rowcount
            db.commit()
            
            if count > 0:
                logger.info(f"Cleaned up {count} expired nonces")
            
            return count
            
        except Exception as e:
            logger.error(f"Nonce cleanup error: {str(e)}")
            db.rollback()
            return 0
    
    def validate_nonce_for_code(
        self,
        db: Session,
        code: str,
        expected_nonce: Optional[str]
    ) -> bool:
        """
        Validate nonce associated with authorization code
        
        Args:
            db: Database session
            code: Authorization code
            expected_nonce: Expected nonce value
            
        Returns:
            True if valid or no nonce expected
        """
        if not expected_nonce:
            return True
        
        try:
            # Get nonce from authorization code
            result = db.execute(
                text("""
                    SELECT nonce 
                    FROM authorization_codes 
                    WHERE code = :code
                """),
                {"code": code}
            )
            
            row = result.first()
            if not row:
                logger.warning("Authorization code not found")
                return False
            
            stored_nonce = row[0]
            if stored_nonce != expected_nonce:
                logger.warning("Nonce mismatch")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating nonce for code: {str(e)}")
            return False

# Singleton instance
nonce_service = NonceService()