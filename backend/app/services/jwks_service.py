"""
JWKS (JSON Web Key Set) Service for OIDC
Manages RSA key pairs for signing and verifying ID tokens
"""
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from jose import jwk
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from ..config import settings
from ..utils.encryption import encrypt_data, decrypt_data

logger = logging.getLogger(__name__)

class JWKSService:
    """Service for managing JSON Web Keys"""
    
    def __init__(self):
        self.key_size = 2048
        self.algorithm = "RS256"
        self.rotation_days = getattr(settings, 'oidc_key_rotation_days', 90)
        
    def generate_key_pair(self) -> Tuple[str, str, str]:
        """
        Generate a new RSA key pair for token signing
        
        Returns:
            Tuple of (kid, private_key_pem, public_key_pem)
        """
        # Generate unique key ID
        kid = f"{datetime.utcnow().strftime('%Y%m')}-{uuid.uuid4().hex[:8]}"
        
        # Generate RSA key pair
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=self.key_size,
            backend=default_backend()
        )
        
        # Export private key as PEM (no encryption here, we'll encrypt before storage)
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
        
        # Export public key as PEM
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
        logger.info(f"Generated new RSA key pair with kid: {kid}")
        return kid, private_pem, public_pem
    
    def store_key_pair(
        self, 
        db: Session, 
        kid: str, 
        private_key: str, 
        public_key: str,
        expires_at: Optional[datetime] = None
    ) -> bool:
        """
        Store key pair in database with encryption
        
        Args:
            db: Database session
            kid: Key ID
            private_key: Private key in PEM format
            public_key: Public key in PEM format
            expires_at: Key expiration time
            
        Returns:
            True if successful
        """
        try:
            # Encrypt private key before storage
            encrypted_private_key = encrypt_data(private_key)
            
            if not expires_at:
                expires_at = datetime.utcnow() + timedelta(days=self.rotation_days * 2)
            
            db.execute(
                text("""
                    INSERT INTO oauth_signing_keys 
                    (kid, private_key, public_key, algorithm, is_active, expires_at)
                    VALUES (:kid, :private_key, :public_key, :algorithm, true, :expires_at)
                """),
                {
                    "kid": kid,
                    "private_key": encrypted_private_key,
                    "public_key": public_key,
                    "algorithm": self.algorithm,
                    "expires_at": expires_at
                }
            )
            db.commit()
            logger.info(f"Stored new key pair with kid: {kid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store key pair: {str(e)}")
            db.rollback()
            raise Exception(f"Failed to store key pair: {str(e)}")
    
    def get_active_signing_key(self, db: Session) -> Optional[Dict]:
        """
        Get the current active signing key
        
        Args:
            db: Database session
            
        Returns:
            Dictionary with key information or None
        """
        result = db.execute(
            text("""
                SELECT kid, private_key, public_key, algorithm 
                FROM oauth_signing_keys 
                WHERE is_active = true 
                AND expires_at > NOW()
                ORDER BY created_at DESC 
                LIMIT 1
            """)
        )
        
        key_data = result.first()
        if key_data:
            return {
                "kid": key_data[0],
                "private_key": decrypt_data(key_data[1]),
                "public_key": key_data[2],
                "algorithm": key_data[3]
            }
        return None
    
    def get_public_keys_jwks(self, db: Session) -> Dict:
        """
        Get all active public keys in JWKS format
        
        Args:
            db: Database session
            
        Returns:
            JWKS formatted dictionary
        """
        # Get all active public keys
        result = db.execute(
            text("""
                SELECT kid, public_key, algorithm 
                FROM oauth_signing_keys 
                WHERE is_active = true 
                AND expires_at > NOW()
                ORDER BY created_at DESC
            """)
        )
        
        keys = []
        for row in result:
            kid, public_key_pem, algorithm = row
            
            # Convert PEM to JWK format
            jwk_key = self._pem_to_jwk(public_key_pem, kid, algorithm)
            keys.append(jwk_key)
        
        return {"keys": keys}
    
    def _pem_to_jwk(self, pem_key: str, kid: str, algorithm: str = "RS256") -> Dict:
        """
        Convert PEM formatted key to JWK format
        
        Args:
            pem_key: Public key in PEM format
            kid: Key ID
            algorithm: Signing algorithm
            
        Returns:
            JWK dictionary
        """
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend
        import base64
        
        # Load the public key
        public_key = serialization.load_pem_public_key(
            pem_key.encode(),
            backend=default_backend()
        )
        
        # Extract RSA key parameters
        numbers = public_key.public_numbers()
        
        # Convert to base64url encoding (no padding)
        def int_to_base64url(n):
            byte_length = (n.bit_length() + 7) // 8
            return base64.urlsafe_b64encode(
                n.to_bytes(byte_length, byteorder='big')
            ).decode().rstrip('=')
        
        return {
            "kty": "RSA",
            "use": "sig",
            "kid": kid,
            "alg": algorithm,
            "n": int_to_base64url(numbers.n),  # modulus
            "e": int_to_base64url(numbers.e)   # exponent
        }
    
    def rotate_keys(self, db: Session) -> bool:
        """
        Rotate signing keys
        
        1. Generate new key pair
        2. Mark old keys for expiration
        3. Keep old keys active for grace period
        
        Args:
            db: Database session
            
        Returns:
            True if successful
        """
        try:
            # Generate new key pair
            kid, private_key, public_key = self.generate_key_pair()
            
            # Store new key pair
            self.store_key_pair(db, kid, private_key, public_key)
            
            # Mark keys older than rotation period for expiration
            expiration_date = datetime.utcnow() + timedelta(days=7)  # 7 day grace period
            
            db.execute(
                text("""
                    UPDATE oauth_signing_keys 
                    SET is_active = false,
                        rotated_at = NOW(),
                        expires_at = :expires_at
                    WHERE created_at < NOW() - INTERVAL ':rotation_days days'
                    AND is_active = true
                """),
                {
                    "expires_at": expiration_date,
                    "rotation_days": self.rotation_days
                }
            )
            
            db.commit()
            logger.info("Successfully rotated signing keys")
            return True
            
        except Exception as e:
            logger.error(f"Key rotation failed: {str(e)}")
            db.rollback()
            raise Exception(f"Key rotation failed: {str(e)}")
    
    def validate_key_usage(self, db: Session, kid: str) -> bool:
        """
        Validate if a key ID is valid for use
        
        Args:
            db: Database session
            kid: Key ID to validate
            
        Returns:
            True if key is valid
        """
        result = db.execute(
            text("""
                SELECT COUNT(*) 
                FROM oauth_signing_keys 
                WHERE kid = :kid 
                AND is_active = true 
                AND expires_at > NOW()
            """),
            {"kid": kid}
        )
        
        count = result.scalar()
        return count > 0
    
    def cleanup_expired_keys(self, db: Session) -> int:
        """
        Remove expired keys from database
        
        Args:
            db: Database session
            
        Returns:
            Number of keys deleted
        """
        try:
            result = db.execute(
                text("""
                    DELETE FROM oauth_signing_keys 
                    WHERE expires_at < NOW() - INTERVAL '30 days'
                    OR (is_active = false AND rotated_at < NOW() - INTERVAL '30 days')
                """)
            )
            
            deleted_count = result.rowcount
            db.commit()
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired keys")
                
            return deleted_count
            
        except Exception as e:
            logger.error(f"Key cleanup failed: {str(e)}")
            db.rollback()
            raise Exception(f"Key cleanup failed: {str(e)}")
    
    def ensure_active_key_exists(self, db: Session) -> None:
        """
        Ensure at least one active signing key exists
        Called during application startup
        
        Args:
            db: Database session
        """
        active_key = self.get_active_signing_key(db)
        if not active_key:
            logger.info("No active signing key found, generating new key pair")
            kid, private_key, public_key = self.generate_key_pair()
            self.store_key_pair(db, kid, private_key, public_key)


# Singleton instance
jwks_service = JWKSService()