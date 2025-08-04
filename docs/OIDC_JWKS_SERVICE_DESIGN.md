# JWKS Service Design Document

## Overview

The JWKS (JSON Web Key Set) Service manages cryptographic keys for signing and verifying OIDC tokens. This service implements key generation, rotation, storage, and distribution following JWT and JWK standards.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    JWKS Service                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │    Key      │  │    Key      │  │   JWKS      │    │
│  │ Generation  │  │  Storage    │  │  Endpoint   │    │
│  └─────────────┘  └─────────────┘  └─────────────┘    │
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │    Key      │  │    Key      │  │   Key       │    │
│  │  Rotation   │  │ Encryption  │  │ Validation  │    │
│  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────┘
```

## Implementation

### 1. Key Generation Service

```python
# backend/app/services/jwks_service.py
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

from ..config import settings
from ..utils.encryption import encrypt_data, decrypt_data

class JWKSService:
    """Service for managing JSON Web Keys"""
    
    def __init__(self):
        self.key_size = 2048
        self.algorithm = "RS256"
        self.rotation_days = settings.oidc_key_rotation_days
        
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
        
        # Export private key as PEM
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
        
        return kid, private_pem, public_pem
    
    def store_key_pair(
        self, 
        db: Session, 
        kid: str, 
        private_key: str, 
        public_key: str,
        expires_at: Optional[datetime] = None
    ) -> bool:
        """Store key pair in database with encryption"""
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
            return True
            
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to store key pair: {str(e)}")
    
    def get_active_signing_key(self, db: Session) -> Optional[Dict]:
        """Get the current active signing key"""
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
        """Convert PEM formatted key to JWK format"""
        # Load the public key
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend
        import base64
        
        public_key = serialization.load_pem_public_key(
            pem_key.encode(),
            backend=default_backend()
        )
        
        # Extract key parameters
        numbers = public_key.public_numbers()
        
        # Convert to base64url encoding
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
            "n": int_to_base64url(numbers.n),
            "e": int_to_base64url(numbers.e)
        }
    
    def rotate_keys(self, db: Session) -> bool:
        """
        Rotate signing keys
        
        1. Generate new key pair
        2. Mark old keys for expiration
        3. Keep old keys active for grace period
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
            return True
            
        except Exception as e:
            db.rollback()
            raise Exception(f"Key rotation failed: {str(e)}")
    
    def validate_key_usage(self, db: Session, kid: str) -> bool:
        """Validate if a key ID is valid for use"""
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
        """Remove expired keys from database"""
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
            return deleted_count
            
        except Exception as e:
            db.rollback()
            raise Exception(f"Key cleanup failed: {str(e)}")


# Singleton instance
jwks_service = JWKSService()
```

### 2. Encryption Utility for Private Keys

```python
# backend/app/utils/encryption.py
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from ..config import settings

class KeyEncryption:
    """Utility for encrypting/decrypting sensitive keys"""
    
    def __init__(self):
        # Derive encryption key from secret
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'stable_salt_for_key_encryption',  # In production, use proper salt management
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(
            kdf.derive(settings.secret_key.encode())
        )
        self.cipher = Fernet(key)
    
    def encrypt(self, data: str) -> str:
        """Encrypt string data"""
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string data"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()

# Global instance
key_encryption = KeyEncryption()

def encrypt_data(data: str) -> str:
    """Encrypt sensitive data"""
    return key_encryption.encrypt(data)

def decrypt_data(encrypted_data: str) -> str:
    """Decrypt sensitive data"""
    return key_encryption.decrypt(encrypted_data)
```

### 3. JWKS Endpoint Implementation

```python
# Add to backend/app/api/oauth_simple.py

from ..services.jwks_service import jwks_service

@router.get("/jwks", response_model=Dict)
def get_jwks(db: Session = Depends(get_db)):
    """
    JSON Web Key Set endpoint
    
    Returns public keys for token verification in JWKS format
    Implements: https://tools.ietf.org/html/rfc7517
    """
    try:
        jwks = jwks_service.get_public_keys_jwks(db)
        
        # Add cache headers for performance
        headers = {
            "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
            "Content-Type": "application/json"
        }
        
        return JSONResponse(content=jwks, headers=headers)
        
    except Exception as e:
        logger.error(f"JWKS endpoint error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve JWKS"
        )
```

### 4. Key Rotation Task

```python
# backend/app/tasks/key_rotation.py
import asyncio
from datetime import datetime
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..services.jwks_service import jwks_service
import logging

logger = logging.getLogger(__name__)

async def rotate_signing_keys():
    """Background task to rotate signing keys periodically"""
    while True:
        try:
            db = SessionLocal()
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

# Add to main.py startup
@app.on_event("startup")
async def startup_event():
    # ... existing code ...
    asyncio.create_task(rotate_signing_keys())
```

### 5. Database Migration

```sql
-- backend/migrations/add_oauth_signing_keys.sql
CREATE TABLE IF NOT EXISTS oauth_signing_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kid VARCHAR(255) UNIQUE NOT NULL,
    private_key TEXT NOT NULL, -- Encrypted
    public_key TEXT NOT NULL,
    algorithm VARCHAR(10) DEFAULT 'RS256',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    rotated_at TIMESTAMP,
    
    -- Indexes
    INDEX idx_kid (kid),
    INDEX idx_active_keys (is_active, expires_at),
    INDEX idx_created_at (created_at)
);

-- Add comments
COMMENT ON TABLE oauth_signing_keys IS 'Cryptographic keys for OIDC token signing';
COMMENT ON COLUMN oauth_signing_keys.kid IS 'Key ID for JWT header';
COMMENT ON COLUMN oauth_signing_keys.private_key IS 'Encrypted private key in PEM format';
COMMENT ON COLUMN oauth_signing_keys.public_key IS 'Public key in PEM format';
```

## Testing Strategy

### Unit Tests

```python
# tests/test_jwks_service.py
import pytest
from datetime import datetime, timedelta
from backend.app.services.jwks_service import JWKSService

class TestJWKSService:
    def test_generate_key_pair(self):
        service = JWKSService()
        kid, private_key, public_key = service.generate_key_pair()
        
        assert kid is not None
        assert private_key.startswith("-----BEGIN PRIVATE KEY-----")
        assert public_key.startswith("-----BEGIN PUBLIC KEY-----")
    
    def test_pem_to_jwk_conversion(self):
        service = JWKSService()
        kid, _, public_key = service.generate_key_pair()
        
        jwk = service._pem_to_jwk(public_key, kid)
        
        assert jwk["kty"] == "RSA"
        assert jwk["use"] == "sig"
        assert jwk["kid"] == kid
        assert jwk["alg"] == "RS256"
        assert "n" in jwk
        assert "e" in jwk
    
    def test_jwks_format(self, db_session):
        service = JWKSService()
        
        # Generate and store test keys
        for i in range(3):
            kid, private_key, public_key = service.generate_key_pair()
            service.store_key_pair(db_session, kid, private_key, public_key)
        
        # Get JWKS
        jwks = service.get_public_keys_jwks(db_session)
        
        assert "keys" in jwks
        assert len(jwks["keys"]) == 3
        assert all(key["kty"] == "RSA" for key in jwks["keys"])
```

## Security Considerations

1. **Private Key Protection**
   - Encrypt private keys at rest using AES-256
   - Use hardware security modules (HSM) in production
   - Implement key escrow for disaster recovery

2. **Key Rotation**
   - Automatic rotation every 90 days
   - Grace period for old keys (7 days)
   - Audit trail for all key operations

3. **Access Control**
   - JWKS endpoint is public (read-only)
   - Key management requires admin privileges
   - Rate limiting on JWKS endpoint

4. **Monitoring**
   - Alert on key rotation failures
   - Monitor key usage patterns
   - Track token validation errors

## Performance Optimization

1. **Caching**
   - Cache JWKS response for 1 hour
   - In-memory cache for active signing key
   - ETags for conditional requests

2. **Database Queries**
   - Indexed lookups by kid
   - Efficient active key queries
   - Batch operations for cleanup

3. **Key Size**
   - 2048-bit RSA keys (balance security/performance)
   - Consider ECDSA for better performance
   - Pre-generate keys during low load

## Integration Points

1. **ID Token Service**
   - Uses active signing key
   - Includes kid in JWT header
   - Handles key rotation gracefully

2. **Token Validation**
   - Fetches public keys from JWKS
   - Validates kid matches
   - Caches keys locally

3. **Discovery Endpoint**
   - References JWKS URI
   - Lists supported algorithms
   - Indicates key rotation policy