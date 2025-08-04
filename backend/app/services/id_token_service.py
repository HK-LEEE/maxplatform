"""
OIDC ID Token Service
Handles creation and validation of OpenID Connect ID tokens
"""
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from ..config import settings
from ..models import User
from .jwks_service import jwks_service

logger = logging.getLogger(__name__)

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
        from .claims_service import claims_service
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
    
    def refresh_id_token(
        self,
        user: User,
        client_id: str,
        scopes: List[str],
        db: Session,
        original_auth_time: Optional[datetime] = None
    ) -> str:
        """
        Create a new ID token during token refresh
        
        Preserves original auth_time but updates issue time
        """
        # Use original auth_time if available, otherwise current time
        auth_time = original_auth_time or datetime.utcnow()
        
        # Create new ID token without nonce (not required for refresh)
        return self.create_id_token(
            user=user,
            client_id=client_id,
            nonce=None,  # No nonce for refresh
            auth_time=auth_time,
            scopes=scopes,
            access_token=None,  # No at_hash for refresh response
            authorization_code=None,
            db=db
        )

# Singleton instance
id_token_service = IDTokenService()