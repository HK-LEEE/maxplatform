# ID Token Service Design Document

## Overview

The ID Token Service is responsible for creating, signing, and validating OpenID Connect ID tokens. ID tokens are JWT tokens that contain claims about the authentication event and the authenticated user.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ID Token Service                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Claims     │  │    Token     │  │    Hash      │     │
│  │  Builder     │  │   Creator    │  │  Generator   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Token      │  │    Nonce     │  │   Token      │     │
│  │  Validator   │  │   Manager    │  │   Storage    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## Implementation

### 1. ID Token Service Core

```python
# backend/app/services/id_token_service.py
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..config import settings
from ..models import User
from .jwks_service import jwks_service
from .claims_service import claims_service
from ..utils.logging_config import get_oauth_logger

logger = get_oauth_logger()

class IDTokenService:
    """Service for creating and validating OIDC ID tokens"""
    
    def __init__(self):
        self.issuer = settings.oidc_issuer or settings.max_platform_api_url
        self.default_expiry_minutes = settings.oidc_id_token_expire_minutes
        
    def create_id_token(
        self,
        user: User,
        client_id: str,
        nonce: Optional[str],
        auth_time: datetime,
        scopes: List[str],
        access_token: Optional[str],
        authorization_code: Optional[str],
        db: Session,
        max_age: Optional[int] = None,
        acr_values: Optional[str] = None,
        additional_claims: Optional[Dict] = None
    ) -> str:
        """
        Create an ID token for the authenticated user
        
        Args:
            user: Authenticated user object
            client_id: OAuth client ID (audience)
            nonce: Nonce value from authorization request
            auth_time: Time when user authenticated
            scopes: List of granted scopes
            access_token: Access token (for at_hash)
            authorization_code: Auth code (for c_hash)
            db: Database session
            max_age: Maximum authentication age requested
            acr_values: Authentication context class reference
            additional_claims: Additional custom claims
            
        Returns:
            Signed JWT ID token
        """
        # Get active signing key
        signing_key = jwks_service.get_active_signing_key(db)
        if not signing_key:
            raise Exception("No active signing key available")
        
        # Build standard claims
        now = datetime.utcnow()
        exp = now + timedelta(minutes=self.default_expiry_minutes)
        
        # Base claims required by OIDC
        claims = {
            "iss": self.issuer,
            "sub": str(user.id),
            "aud": client_id,
            "exp": int(exp.timestamp()),
            "iat": int(now.timestamp()),
            "auth_time": int(auth_time.timestamp())
        }
        
        # Add nonce if provided (required for implicit flow)
        if nonce:
            claims["nonce"] = nonce
        
        # Add at_hash if access token provided (required for implicit/hybrid)
        if access_token:
            claims["at_hash"] = self._generate_hash(access_token, signing_key["algorithm"])
        
        # Add c_hash if authorization code provided (required for hybrid)
        if authorization_code:
            claims["c_hash"] = self._generate_hash(authorization_code, signing_key["algorithm"])
        
        # Add ACR (Authentication Context Reference) if provided
        if acr_values:
            claims["acr"] = acr_values
            claims["amr"] = ["pwd"]  # Authentication methods (password in this case)
        
        # Add user claims based on requested scopes
        user_claims = claims_service.get_user_claims(user, scopes, db)
        claims.update(user_claims)
        
        # Add any additional custom claims
        if additional_claims:
            claims.update(additional_claims)
        
        # Create JWT header with key ID
        headers = {
            "kid": signing_key["kid"],
            "alg": signing_key["algorithm"]
        }
        
        # Sign the token
        id_token = jwt.encode(
            claims,
            signing_key["private_key"],
            algorithm=signing_key["algorithm"],
            headers=headers
        )
        
        # Log token creation
        logger.info(f"ID token created for user {user.id} with client {client_id}")
        
        # Store token metadata for tracking (optional)
        self._store_token_metadata(db, user.id, client_id, claims["jti"] if "jti" in claims else None)
        
        return id_token
    
    def _generate_hash(self, value: str, algorithm: str = "RS256") -> str:
        """
        Generate hash for at_hash or c_hash claims
        
        OIDC spec: Use left-most half of hash, base64url encoded
        """
        # Determine hash algorithm based on signing algorithm
        if algorithm in ["RS256", "ES256", "PS256", "HS256"]:
            hash_alg = hashlib.sha256
        elif algorithm in ["RS384", "ES384", "PS384", "HS384"]:
            hash_alg = hashlib.sha384
        elif algorithm in ["RS512", "ES512", "PS512", "HS512"]:
            hash_alg = hashlib.sha512
        else:
            hash_alg = hashlib.sha256  # Default
        
        # Generate hash
        digest = hash_alg(value.encode('ascii')).digest()
        
        # Take left-most half
        half_len = len(digest) // 2
        half_digest = digest[:half_len]
        
        # Base64url encode without padding
        return base64.urlsafe_b64encode(half_digest).decode('ascii').rstrip('=')
    
    def validate_id_token(
        self,
        id_token: str,
        client_id: str,
        nonce: Optional[str],
        db: Session,
        access_token: Optional[str] = None,
        max_age: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Validate an ID token according to OIDC specifications
        
        Args:
            id_token: JWT ID token to validate
            client_id: Expected audience (client ID)
            nonce: Expected nonce value
            db: Database session
            access_token: Access token for at_hash validation
            max_age: Maximum age of authentication
            
        Returns:
            Validated token claims
            
        Raises:
            JWTError: If validation fails
        """
        try:
            # Decode header to get kid
            unverified_header = jwt.get_unverified_header(id_token)
            kid = unverified_header.get("kid")
            
            if not kid:
                raise JWTError("Missing kid in token header")
            
            # Get public key for verification
            jwks = jwks_service.get_public_keys_jwks(db)
            public_key = None
            
            for key in jwks["keys"]:
                if key["kid"] == kid:
                    # Convert JWK to PEM for jose library
                    public_key = self._jwk_to_pem(key)
                    break
            
            if not public_key:
                raise JWTError(f"Unknown kid: {kid}")
            
            # Decode and verify token
            claims = jwt.decode(
                id_token,
                public_key,
                algorithms=[unverified_header.get("alg", "RS256")],
                audience=client_id,
                issuer=self.issuer
            )
            
            # OIDC-specific validations
            
            # 1. Validate nonce if expected
            if nonce and claims.get("nonce") != nonce:
                raise JWTError("Invalid nonce")
            
            # 2. Validate at_hash if present
            if "at_hash" in claims and access_token:
                expected_at_hash = self._generate_hash(
                    access_token, 
                    unverified_header.get("alg", "RS256")
                )
                if claims["at_hash"] != expected_at_hash:
                    raise JWTError("Invalid at_hash")
            
            # 3. Validate auth_time and max_age
            if max_age is not None:
                auth_time = claims.get("auth_time")
                if not auth_time:
                    raise JWTError("Missing auth_time claim")
                
                current_time = datetime.utcnow().timestamp()
                if current_time - auth_time > max_age:
                    raise JWTError("Authentication too old")
            
            # 4. Additional security checks
            if "azp" in claims and claims["azp"] != client_id:
                raise JWTError("Invalid authorized party (azp)")
            
            logger.info(f"ID token validated successfully for subject {claims['sub']}")
            return claims
            
        except JWTError as e:
            logger.warning(f"ID token validation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during ID token validation: {str(e)}")
            raise JWTError(f"Token validation failed: {str(e)}")
    
    def _jwk_to_pem(self, jwk_dict: Dict) -> str:
        """Convert JWK to PEM format for token verification"""
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.backends import default_backend
        import base64
        
        # Decode base64url values
        def base64url_decode(value):
            # Add padding if needed
            padding = 4 - (len(value) % 4)
            if padding != 4:
                value += '=' * padding
            return base64.urlsafe_b64decode(value)
        
        # Extract RSA components
        n = int.from_bytes(base64url_decode(jwk_dict["n"]), byteorder='big')
        e = int.from_bytes(base64url_decode(jwk_dict["e"]), byteorder='big')
        
        # Create public key
        public_numbers = rsa.RSAPublicNumbers(e, n)
        public_key = public_numbers.public_key(default_backend())
        
        # Export as PEM
        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return pem.decode('utf-8')
    
    def _store_token_metadata(
        self, 
        db: Session, 
        user_id: str, 
        client_id: str,
        jti: Optional[str] = None
    ):
        """Store ID token metadata for tracking and revocation"""
        try:
            # This is optional - you may want to track ID tokens
            # for security auditing or revocation purposes
            pass
        except Exception as e:
            # Don't fail token creation if metadata storage fails
            logger.warning(f"Failed to store token metadata: {str(e)}")

# Singleton instance
id_token_service = IDTokenService()
```

### 2. Claims Service

```python
# backend/app/services/claims_service.py
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from ..models import User

class ClaimsService:
    """Service for managing OIDC claims based on scopes"""
    
    # Standard OIDC scope to claims mapping
    SCOPE_CLAIMS_MAP = {
        "profile": [
            "name", "family_name", "given_name", "middle_name",
            "nickname", "preferred_username", "profile", "picture",
            "website", "gender", "birthdate", "zoneinfo", "locale",
            "updated_at"
        ],
        "email": ["email", "email_verified"],
        "address": ["address"],
        "phone": ["phone_number", "phone_number_verified"],
        # Custom scopes for MAX Platform
        "groups": ["groups", "group_id", "group_name"],
        "roles": ["role", "role_id", "role_name", "permissions"]
    }
    
    def get_user_claims(
        self, 
        user: User, 
        scopes: List[str],
        db: Session,
        include_custom: bool = True
    ) -> Dict[str, Any]:
        """
        Get user claims based on requested scopes
        
        Args:
            user: User object
            scopes: List of requested scopes
            db: Database session
            include_custom: Include custom MAX Platform claims
            
        Returns:
            Dictionary of claims
        """
        claims = {}
        
        # Always include sub (subject) - it's the user ID
        # Sub is included in base token, not here
        
        # Process standard OIDC scopes
        for scope in scopes:
            if scope in self.SCOPE_CLAIMS_MAP:
                scope_claims = self.SCOPE_CLAIMS_MAP[scope]
                for claim in scope_claims:
                    value = self._get_claim_value(user, claim, db)
                    if value is not None:
                        claims[claim] = value
        
        # Add custom claims if requested
        if include_custom and any(s.startswith("read:") or s.startswith("manage:") for s in scopes):
            custom_claims = self._get_custom_claims(user, scopes, db)
            claims.update(custom_claims)
        
        return claims
    
    def _get_claim_value(
        self, 
        user: User, 
        claim: str,
        db: Session
    ) -> Any:
        """Get individual claim value from user object"""
        
        # Standard profile claims
        if claim == "name":
            return user.display_name or user.real_name or user.email
        elif claim == "given_name":
            # Extract from real_name if available
            if user.real_name and " " in user.real_name:
                return user.real_name.split(" ")[0]
            return None
        elif claim == "family_name":
            # Extract from real_name if available
            if user.real_name and " " in user.real_name:
                parts = user.real_name.split(" ")
                return " ".join(parts[1:]) if len(parts) > 1 else None
            return None
        elif claim == "preferred_username":
            return user.username if hasattr(user, 'username') else user.email.split("@")[0]
        elif claim == "email":
            return user.email
        elif claim == "email_verified":
            return getattr(user, 'email_verified', True)  # Default to True if not tracked
        elif claim == "updated_at":
            if hasattr(user, 'updated_at') and user.updated_at:
                return int(user.updated_at.timestamp())
            return None
        elif claim == "locale":
            return getattr(user, 'locale', 'ko-KR')  # Default Korean locale
        elif claim == "zoneinfo":
            return getattr(user, 'timezone', 'Asia/Seoul')  # Default Seoul timezone
        
        # Group-related claims
        elif claim == "groups":
            if user.group:
                return [user.group.name]
            return []
        elif claim == "group_id":
            return str(user.group_id) if user.group_id else None
        elif claim == "group_name":
            return user.group.name if user.group else None
        
        # Role-related claims
        elif claim == "role":
            return user.role.name if user.role else None
        elif claim == "role_id":
            return str(user.role_id) if user.role_id else None
        elif claim == "role_name":
            return user.role.name if user.role else None
        
        # Address claim (structured)
        elif claim == "address":
            # Return formatted address if available
            if hasattr(user, 'address') and user.address:
                return {
                    "formatted": user.address,
                    "country": "KR"  # Default to Korea
                }
            return None
        
        # Phone claims
        elif claim == "phone_number":
            return getattr(user, 'phone_number', None)
        elif claim == "phone_number_verified":
            return getattr(user, 'phone_verified', False)
        
        # Profile picture
        elif claim == "picture":
            return getattr(user, 'avatar_url', None)
        
        # Gender
        elif claim == "gender":
            return getattr(user, 'gender', None)
        
        # Birthdate
        elif claim == "birthdate":
            if hasattr(user, 'birthdate') and user.birthdate:
                return user.birthdate.strftime("%Y-%m-%d")
            return None
        
        # Default: try to get attribute directly
        return getattr(user, claim, None)
    
    def _get_custom_claims(
        self,
        user: User,
        scopes: List[str],
        db: Session
    ) -> Dict[str, Any]:
        """Get custom MAX Platform claims"""
        custom_claims = {}
        
        # Admin status
        if user.is_admin:
            custom_claims["is_admin"] = True
        
        # Feature permissions based on scopes
        features = []
        if "read:features" in scopes:
            # Get user's available features
            if user.group:
                # You would fetch features from group permissions
                features = ["dashboard", "analytics", "reports"]
        
        if features:
            custom_claims["features"] = features
        
        # Workspace information
        if "manage:workspaces" in scopes:
            custom_claims["workspace_quota"] = getattr(user, 'workspace_quota', 5)
            custom_claims["active_workspaces"] = getattr(user, 'active_workspace_count', 0)
        
        # API quotas
        if "manage:apis" in scopes:
            custom_claims["api_quota"] = {
                "daily_limit": 10000,
                "rate_limit": "100/minute"
            }
        
        # ML model permissions
        if "manage:models" in scopes:
            custom_claims["ml_models_access"] = ["gpt-4", "llama-2", "stable-diffusion"]
        
        return custom_claims
    
    def get_userinfo_response(
        self,
        user: User,
        scopes: List[str],
        db: Session,
        as_jwt: bool = False,
        client_id: Optional[str] = None
    ) -> Any:
        """
        Get UserInfo endpoint response
        
        Can return either JSON or JWT format
        """
        # Get all claims for the scopes
        claims = self.get_user_claims(user, scopes, db)
        
        # Always include sub
        claims["sub"] = str(user.id)
        
        if as_jwt and client_id:
            # Return as signed JWT (optional per OIDC spec)
            from .id_token_service import id_token_service
            
            # Create a minimal ID token with just userinfo claims
            return id_token_service.create_id_token(
                user=user,
                client_id=client_id,
                nonce=None,  # No nonce for userinfo
                auth_time=datetime.utcnow(),  # Not relevant for userinfo
                scopes=scopes,
                access_token=None,
                authorization_code=None,
                db=db,
                additional_claims=claims
            )
        else:
            # Return as JSON (default)
            return claims

# Singleton instance
claims_service = ClaimsService()
```

### 3. Nonce Management

```python
# backend/app/services/nonce_service.py
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

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
            return True
            
        except Exception as e:
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
            
            return True
            
        except Exception as e:
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
            return count
            
        except Exception as e:
            db.rollback()
            return 0

# Singleton instance
nonce_service = NonceService()
```

### 4. Database Schema for Nonces

```sql
-- Add nonce tracking table
CREATE TABLE IF NOT EXISTS oauth_nonces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nonce_hash VARCHAR(255) NOT NULL,
    client_id VARCHAR(50) NOT NULL,
    user_id UUID,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_nonce_lookup (nonce_hash, client_id, expires_at)
);

COMMENT ON TABLE oauth_nonces IS 'Nonce tracking for OIDC replay attack prevention';
```

## Integration with Token Endpoint

```python
# Modifications to backend/app/api/oauth_simple.py

def handle_authorization_code_grant(...):
    # ... existing code ...
    
    # Check if openid scope is requested
    scopes = auth_code_dict['scope'].split() if auth_code_dict['scope'] else []
    
    if "openid" in scopes:
        # Get nonce from authorization code if stored
        nonce = None
        nonce_result = db.execute(
            text("SELECT nonce FROM authorization_codes WHERE code = :code"),
            {"code": code}
        )
        nonce_record = nonce_result.first()
        if nonce_record:
            nonce = nonce_record[0]
        
        # Get auth_time from authorization code
        auth_time = auth_code_dict.get('created_at', datetime.utcnow())
        
        # Create ID token
        id_token = id_token_service.create_id_token(
            user=user,
            client_id=client_id,
            nonce=nonce,
            auth_time=auth_time,
            scopes=scopes,
            access_token=access_token,
            authorization_code=code if response_type_includes_code else None,
            db=db
        )
        
        # Add to response
        response_data = {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
            "scope": auth_code_dict['scope'] or "read:profile",
            "id_token": id_token  # Add ID token
        }
        
        # Add refresh token if offline_access scope
        if "offline_access" in scopes:
            refresh_token = create_refresh_token_record(...)
            response_data["refresh_token"] = refresh_token
```

## Testing

```python
# tests/test_id_token_service.py
import pytest
from datetime import datetime
from jose import jwt
from backend.app.services.id_token_service import IDTokenService
from backend.app.models import User

class TestIDTokenService:
    def test_create_id_token(self, db_session, test_user, test_client):
        service = IDTokenService()
        
        # Create ID token
        id_token = service.create_id_token(
            user=test_user,
            client_id=test_client.client_id,
            nonce="test-nonce-123",
            auth_time=datetime.utcnow(),
            scopes=["openid", "profile", "email"],
            access_token="test-access-token",
            authorization_code=None,
            db=db_session
        )
        
        # Decode without verification for testing
        claims = jwt.get_unverified_claims(id_token)
        
        assert claims["sub"] == str(test_user.id)
        assert claims["aud"] == test_client.client_id
        assert claims["nonce"] == "test-nonce-123"
        assert "at_hash" in claims
        assert "email" in claims
        assert "name" in claims
    
    def test_hash_generation(self):
        service = IDTokenService()
        
        # Test at_hash generation
        access_token = "test-access-token-12345"
        at_hash = service._generate_hash(access_token)
        
        # Verify format
        assert len(at_hash) > 20  # Base64url encoded
        assert "=" not in at_hash  # No padding
        
        # Same input should produce same hash
        at_hash2 = service._generate_hash(access_token)
        assert at_hash == at_hash2
    
    def test_token_validation(self, db_session, test_id_token):
        service = IDTokenService()
        
        # Validate token
        claims = service.validate_id_token(
            id_token=test_id_token,
            client_id="test-client",
            nonce="expected-nonce",
            db=db_session
        )
        
        assert claims["sub"] == "test-user-id"
        assert claims["aud"] == "test-client"
```

## Security Considerations

1. **Nonce Validation**
   - Always validate nonce for implicit/hybrid flows
   - One-time use only (consume on validation)
   - Sufficient entropy (32 bytes)

2. **Hash Validation**
   - Validate at_hash when access token present
   - Validate c_hash for hybrid flow
   - Use correct hash algorithm

3. **Audience Restriction**
   - Strictly validate audience claim
   - Support multiple audiences if needed
   - Reject tokens for wrong client

4. **Time-based Security**
   - Short expiration times (1 hour default)
   - Validate auth_time for max_age
   - Clock skew tolerance (5 minutes)

## Performance Optimization

1. **Caching**
   - Cache user claims per session
   - Cache signing keys in memory
   - Batch claim lookups

2. **Efficient Queries**
   - Preload user relationships
   - Index claim source tables
   - Minimize database round trips

3. **Token Size**
   - Include only requested claims
   - Use compact claim names
   - Consider claim references