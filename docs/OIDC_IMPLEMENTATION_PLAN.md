# MAX Platform OIDC Implementation Plan

## Executive Summary

This document outlines a comprehensive plan to implement OpenID Connect (OIDC) 1.0 Core specification on top of the existing OAuth 2.0 implementation in MAX Platform. The implementation will maintain backward compatibility while adding identity layer capabilities.

## 1. Architecture Overview

### Current State (OAuth 2.0)
- ✅ Authorization Code Flow with PKCE
- ✅ Refresh Token Flow
- ✅ Client Credentials Flow
- ✅ Token Revocation
- ✅ UserInfo Endpoint
- ❌ ID Tokens
- ❌ JWKS Endpoint
- ❌ OpenID Configuration Discovery
- ❌ OIDC Scopes and Claims

### Target State (OAuth 2.0 + OIDC)
All current OAuth 2.0 features plus:
- ✅ ID Token issuance and validation
- ✅ JWKS endpoint for public key distribution
- ✅ OpenID Configuration discovery
- ✅ Standard OIDC scopes and claims
- ✅ Nonce validation for security
- ✅ Hybrid and Implicit flows support
- ✅ Asymmetric key signatures (RS256)

## 2. Implementation Phases

### Phase 1: Core Infrastructure (Week 1-2)

#### 1.1 Key Management System
```python
# New file: backend/app/services/jwks_service.py
class JWKSService:
    - Generate RSA key pairs
    - Rotate keys periodically
    - Serve public keys via JWKS endpoint
    - Store keys securely in database
```

**Database Schema Changes:**
```sql
-- New table for key management
CREATE TABLE oauth_signing_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kid VARCHAR(255) UNIQUE NOT NULL,
    private_key TEXT NOT NULL, -- Encrypted
    public_key TEXT NOT NULL,
    algorithm VARCHAR(10) DEFAULT 'RS256',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    rotated_at TIMESTAMP
);
```

#### 1.2 ID Token Service
```python
# New file: backend/app/services/id_token_service.py
class IDTokenService:
    - Create ID tokens with standard claims
    - Sign tokens with private key
    - Include at_hash and c_hash when required
    - Handle nonce values
```

### Phase 2: OIDC Endpoints (Week 2-3)

#### 2.1 OpenID Configuration Discovery
```python
# Add to backend/app/api/oauth_simple.py
@router.get("/.well-known/openid-configuration")
def openid_configuration():
    return {
        "issuer": settings.max_platform_api_url,
        "authorization_endpoint": f"{settings.max_platform_api_url}/api/oauth/authorize",
        "token_endpoint": f"{settings.max_platform_api_url}/api/oauth/token",
        "userinfo_endpoint": f"{settings.max_platform_api_url}/api/oauth/userinfo",
        "jwks_uri": f"{settings.max_platform_api_url}/api/oauth/jwks",
        "registration_endpoint": f"{settings.max_platform_api_url}/api/oauth/register",
        "scopes_supported": [
            "openid", "profile", "email", "address", "phone", "offline_access",
            "read:profile", "read:features", "read:groups", # Existing scopes
        ],
        "response_types_supported": [
            "code", "id_token", "token id_token", "code id_token", "code token", "code token id_token"
        ],
        "response_modes_supported": ["query", "fragment", "form_post"],
        "grant_types_supported": [
            "authorization_code", "implicit", "refresh_token", "client_credentials"
        ],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["RS256", "HS256"],
        "token_endpoint_auth_methods_supported": [
            "client_secret_post", "client_secret_basic", "client_secret_jwt", "private_key_jwt"
        ],
        "claims_supported": [
            "sub", "iss", "aud", "exp", "iat", "auth_time", "nonce",
            "name", "given_name", "family_name", "middle_name", "nickname",
            "preferred_username", "profile", "picture", "website", "gender",
            "birthdate", "zoneinfo", "locale", "updated_at",
            "email", "email_verified", "phone_number", "phone_number_verified",
            "address", "groups", "roles"
        ],
        "code_challenge_methods_supported": ["plain", "S256"],
        "introspection_endpoint": f"{settings.max_platform_api_url}/api/oauth/introspect",
        "revocation_endpoint": f"{settings.max_platform_api_url}/api/oauth/revoke",
        "claim_types_supported": ["normal"],
        "claims_parameter_supported": false,
        "request_parameter_supported": false,
        "request_uri_parameter_supported": false
    }
```

#### 2.2 JWKS Endpoint
```python
# Add to backend/app/api/oauth_simple.py
@router.get("/jwks")
def jwks():
    """JSON Web Key Set endpoint for public key distribution"""
    return jwks_service.get_public_keys()
```

### Phase 3: Token Enhancement (Week 3-4)

#### 3.1 Authorization Endpoint Updates
- Add `openid` scope validation
- Handle `nonce` parameter
- Support `prompt` parameter (none, login, consent, select_account)
- Add `max_age` parameter support
- Implement `id_token_hint` validation

#### 3.2 Token Endpoint Updates
```python
# Modify handle_authorization_code_grant()
def handle_authorization_code_grant(...):
    # ... existing code ...
    
    # Check if openid scope is requested
    if "openid" in scopes:
        # Generate ID token
        id_token_claims = {
            "iss": settings.max_platform_api_url,
            "sub": str(user.id),
            "aud": client_id,
            "exp": expires_at,
            "iat": now,
            "auth_time": auth_time,
            "nonce": nonce if nonce else None,
            "at_hash": generate_at_hash(access_token) if implicit_or_hybrid else None,
            "email": user.email,
            "email_verified": user.email_verified,
            "name": user.display_name,
            # Add more claims based on requested scopes
        }
        
        id_token = id_token_service.create_id_token(
            claims=id_token_claims,
            kid=current_signing_key_id
        )
        
        response["id_token"] = id_token
```

### Phase 4: Security Enhancements (Week 4-5)

#### 4.1 Nonce Handling
```python
# Add nonce validation
class NonceService:
    - Store nonce with authorization code
    - Validate nonce in ID token
    - Prevent replay attacks
    - Clean up expired nonces
```

#### 4.2 Hash Validation
```python
# Add hash generation utilities
def generate_at_hash(access_token: str, algorithm: str = "RS256") -> str:
    """Generate at_hash claim for ID token"""
    hash_digest = hashlib.sha256(access_token.encode()).digest()
    return base64.urlsafe_b64encode(hash_digest[:16]).decode().rstrip("=")

def generate_c_hash(code: str, algorithm: str = "RS256") -> str:
    """Generate c_hash claim for ID token"""
    hash_digest = hashlib.sha256(code.encode()).digest()
    return base64.urlsafe_b64encode(hash_digest[:16]).decode().rstrip("=")
```

### Phase 5: Claims and Scopes (Week 5-6)

#### 5.1 Claims Mapping
```python
# New file: backend/app/services/claims_service.py
class ClaimsService:
    SCOPE_CLAIMS_MAP = {
        "profile": ["name", "family_name", "given_name", "middle_name", 
                   "nickname", "preferred_username", "profile", "picture", 
                   "website", "gender", "birthdate", "zoneinfo", "locale", 
                   "updated_at"],
        "email": ["email", "email_verified"],
        "address": ["address"],
        "phone": ["phone_number", "phone_number_verified"],
    }
    
    def get_claims_for_scopes(self, user, requested_scopes):
        """Return user claims based on requested scopes"""
```

#### 5.2 UserInfo Endpoint Enhancement
```python
# Update userinfo endpoint to support OIDC claims
@router.get("/userinfo")
def userinfo(
    current_user: User = Depends(get_current_user_optional),
    authorization: str = Header(None)
):
    # Validate access token has openid scope
    # Return claims based on token scopes
    # Support both JSON and JWT response formats
```

### Phase 6: Migration and Testing (Week 6-7)

#### 6.1 Database Migration
```sql
-- Add OIDC fields to existing tables
ALTER TABLE authorization_codes ADD COLUMN nonce VARCHAR(255);
ALTER TABLE authorization_codes ADD COLUMN auth_time TIMESTAMP;

ALTER TABLE oauth_clients ADD COLUMN id_token_signed_response_alg VARCHAR(10) DEFAULT 'RS256';
ALTER TABLE oauth_clients ADD COLUMN userinfo_signed_response_alg VARCHAR(10);
ALTER TABLE oauth_clients ADD COLUMN default_max_age INTEGER;
ALTER TABLE oauth_clients ADD COLUMN require_auth_time BOOLEAN DEFAULT false;

-- Update oauth_scopes table
INSERT INTO oauth_scopes (scope, description, category) VALUES
('openid', 'OpenID Connect authentication', 'oidc'),
('profile', 'Basic profile information', 'oidc'),
('email', 'Email address and verification status', 'oidc'),
('address', 'Physical address', 'oidc'),
('phone', 'Phone number and verification status', 'oidc'),
('offline_access', 'Maintain access while user is offline', 'oidc');
```

#### 6.2 Testing Strategy
1. **Unit Tests**
   - ID token generation and validation
   - JWKS key rotation
   - Claims mapping
   - Nonce validation

2. **Integration Tests**
   - Full OIDC flow testing
   - Discovery endpoint validation
   - Token introspection
   - Multi-client scenarios

3. **Compliance Tests**
   - OIDC Conformance Test Suite
   - Security vulnerability scanning
   - Performance testing

## 3. Implementation Details

### 3.1 ID Token Structure
```json
{
  "header": {
    "alg": "RS256",
    "typ": "JWT",
    "kid": "2025-01-key-001"
  },
  "payload": {
    "iss": "https://auth.maxplatform.com",
    "sub": "248289761001",
    "aud": "maxflowstudio",
    "exp": 1311281970,
    "iat": 1311280970,
    "auth_time": 1311280900,
    "nonce": "n-0S6_WzA2Mj",
    "at_hash": "MTIzNDU2Nzg5MDEyMzQ1Ng",
    "email": "user@example.com",
    "email_verified": true,
    "groups": ["developers", "admins"],
    "role": "senior_developer"
  }
}
```

### 3.2 Configuration Updates
```python
# Add to backend/app/config.py
class Settings(BaseSettings):
    # ... existing settings ...
    
    # OIDC Settings
    oidc_issuer: str = os.getenv("OIDC_ISSUER", max_platform_api_url)
    oidc_signing_algorithm: str = os.getenv("OIDC_SIGNING_ALG", "RS256")
    oidc_key_rotation_days: int = int(os.getenv("OIDC_KEY_ROTATION_DAYS", "90"))
    oidc_id_token_expire_minutes: int = int(os.getenv("OIDC_ID_TOKEN_EXPIRE_MINUTES", "60"))
    oidc_supported_claims: List[str] = [
        "sub", "name", "given_name", "family_name", "email", 
        "email_verified", "groups", "roles", "picture"
    ]
```

### 3.3 Backward Compatibility
- All existing OAuth 2.0 flows continue to work
- OIDC features only activate when `openid` scope is requested
- Existing access tokens remain valid
- No breaking changes to current API contracts

## 4. Security Considerations

### 4.1 Key Management
- Store private keys encrypted at rest
- Implement key rotation every 90 days
- Support multiple active keys during rotation
- Audit all key usage

### 4.2 Token Security
- Use RS256 for ID tokens (asymmetric)
- Maintain HS256 for backward compatibility
- Implement token binding where supported
- Add rate limiting for token endpoints

### 4.3 Privacy Protection
- Only include claims explicitly requested via scopes
- Support selective disclosure
- Implement consent management
- Audit claim access

## 5. Monitoring and Maintenance

### 5.1 Metrics to Track
- ID token issuance rate
- Key rotation success/failure
- Discovery endpoint availability
- Token validation errors
- Claim access patterns

### 5.2 Logging Requirements
- All authentication events
- Key rotation events
- Scope and claim usage
- Security violations
- Performance metrics

## 6. Rollout Plan

### Week 1-2: Infrastructure
- Implement key management
- Create ID token service
- Set up testing framework

### Week 3-4: Core OIDC
- Add discovery endpoint
- Implement JWKS endpoint
- Enhance token endpoints

### Week 5-6: Features
- Add claims mapping
- Implement nonce handling
- Enhance security features

### Week 7: Testing & Launch
- Run compliance tests
- Performance testing
- Documentation
- Gradual rollout

## 7. Success Criteria

- [ ] Pass OIDC Conformance Test Suite
- [ ] Zero breaking changes for existing OAuth clients
- [ ] < 100ms latency for ID token generation
- [ ] 99.9% availability for discovery and JWKS endpoints
- [ ] Support for all standard OIDC claims
- [ ] Comprehensive audit logging
- [ ] Security scan passes with no critical issues

## 8. References

- [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html)
- [OAuth 2.0 RFC 6749](https://tools.ietf.org/html/rfc6749)
- [JSON Web Token (JWT) RFC 7519](https://tools.ietf.org/html/rfc7519)
- [JSON Web Key (JWK) RFC 7517](https://tools.ietf.org/html/rfc7517)