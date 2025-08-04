# OIDC Testing and Validation Plan

## Overview

This document outlines the comprehensive testing strategy for validating the OpenID Connect implementation in MAX Platform. The testing approach covers unit tests, integration tests, compliance testing, security validation, and performance benchmarks.

## Testing Framework

### Test Environment Setup
```yaml
# docker-compose.test.yml
version: '3.8'

services:
  postgres-test:
    image: postgres:15
    environment:
      POSTGRES_DB: maxplatform_test
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
    ports:
      - "5433:5432"
  
  redis-test:
    image: redis:7-alpine
    ports:
      - "6380:6379"
  
  oidc-test-server:
    image: maxplatform-api:test
    environment:
      DATABASE_URL: postgresql://test:test@postgres-test:5432/maxplatform_test
      REDIS_URL: redis://redis-test:6379
      OIDC_TESTING_MODE: "true"
    depends_on:
      - postgres-test
      - redis-test
    ports:
      - "8001:8000"
```

## 1. Unit Tests

### 1.1 JWKS Service Tests
```python
# tests/unit/test_jwks_service.py
import pytest
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from backend.app.services.jwks_service import JWKSService

class TestJWKSService:
    
    @pytest.fixture
    def jwks_service(self):
        return JWKSService()
    
    def test_generate_key_pair(self, jwks_service):
        """Test RSA key pair generation"""
        kid, private_key, public_key = jwks_service.generate_key_pair()
        
        # Validate key ID format
        assert kid is not None
        assert len(kid) > 10
        assert "-" in kid
        
        # Validate PEM format
        assert private_key.startswith("-----BEGIN PRIVATE KEY-----")
        assert private_key.endswith("-----END PRIVATE KEY-----\n")
        assert public_key.startswith("-----BEGIN PUBLIC KEY-----")
        assert public_key.endswith("-----END PUBLIC KEY-----\n")
        
        # Validate keys can be loaded
        priv = serialization.load_pem_private_key(
            private_key.encode(),
            password=None,
            backend=default_backend()
        )
        pub = serialization.load_pem_public_key(
            public_key.encode(),
            backend=default_backend()
        )
        
        # Validate key size
        assert priv.key_size == 2048
        assert pub.key_size == 2048
    
    def test_pem_to_jwk_conversion(self, jwks_service):
        """Test conversion from PEM to JWK format"""
        kid, _, public_key = jwks_service.generate_key_pair()
        
        jwk = jwks_service._pem_to_jwk(public_key, kid, "RS256")
        
        # Validate JWK structure
        assert jwk["kty"] == "RSA"
        assert jwk["use"] == "sig"
        assert jwk["kid"] == kid
        assert jwk["alg"] == "RS256"
        assert "n" in jwk  # modulus
        assert "e" in jwk  # exponent
        
        # Validate base64url encoding (no padding)
        assert "=" not in jwk["n"]
        assert "=" not in jwk["e"]
    
    def test_key_rotation(self, jwks_service, db_session):
        """Test key rotation logic"""
        # Generate initial key
        kid1, private1, public1 = jwks_service.generate_key_pair()
        jwks_service.store_key_pair(db_session, kid1, private1, public1)
        
        # Simulate time passing
        # (In real test, mock datetime.utcnow)
        
        # Perform rotation
        success = jwks_service.rotate_keys(db_session)
        assert success is True
        
        # Verify new key exists
        active_key = jwks_service.get_active_signing_key(db_session)
        assert active_key is not None
        assert active_key["kid"] != kid1
        
        # Verify old key is marked for expiration
        jwks = jwks_service.get_public_keys_jwks(db_session)
        assert len(jwks["keys"]) >= 2  # Both keys available during grace period
    
    def test_jwks_endpoint_format(self, jwks_service, db_session):
        """Test JWKS endpoint returns correct format"""
        # Store multiple keys
        for i in range(3):
            kid, private_key, public_key = jwks_service.generate_key_pair()
            jwks_service.store_key_pair(db_session, kid, private_key, public_key)
        
        jwks = jwks_service.get_public_keys_jwks(db_session)
        
        # Validate JWKS structure
        assert "keys" in jwks
        assert isinstance(jwks["keys"], list)
        assert len(jwks["keys"]) >= 3
        
        # Validate each key
        for key in jwks["keys"]:
            assert key["kty"] == "RSA"
            assert key["use"] == "sig"
            assert "kid" in key
            assert "alg" in key
            assert "n" in key
            assert "e" in key
```

### 1.2 ID Token Service Tests
```python
# tests/unit/test_id_token_service.py
import pytest
from datetime import datetime, timedelta
from jose import jwt, JWTError
from backend.app.services.id_token_service import IDTokenService
from backend.app.models import User

class TestIDTokenService:
    
    @pytest.fixture
    def id_token_service(self):
        return IDTokenService()
    
    @pytest.fixture
    def mock_user(self):
        return User(
            id="123e4567-e89b-12d3-a456-426614174000",
            email="test@example.com",
            display_name="Test User",
            is_admin=False,
            group_id="987e4567-e89b-12d3-a456-426614174000"
        )
    
    def test_create_id_token_basic(self, id_token_service, mock_user, db_session):
        """Test basic ID token creation"""
        # Setup signing key
        setup_test_signing_key(db_session)
        
        id_token = id_token_service.create_id_token(
            user=mock_user,
            client_id="test-client",
            nonce="test-nonce-123",
            auth_time=datetime.utcnow(),
            scopes=["openid", "profile", "email"],
            access_token=None,
            authorization_code=None,
            db=db_session
        )
        
        # Decode without verification for testing
        claims = jwt.get_unverified_claims(id_token)
        
        # Validate required claims
        assert claims["iss"] == id_token_service.issuer
        assert claims["sub"] == str(mock_user.id)
        assert claims["aud"] == "test-client"
        assert "exp" in claims
        assert "iat" in claims
        assert claims["nonce"] == "test-nonce-123"
        
        # Validate profile claims
        assert claims["email"] == "test@example.com"
        assert claims["name"] == "Test User"
    
    def test_at_hash_generation(self, id_token_service):
        """Test at_hash claim generation"""
        access_token = "test.access.token"
        
        # Test with RS256
        at_hash_rs256 = id_token_service._generate_hash(access_token, "RS256")
        assert len(at_hash_rs256) > 20  # Base64url encoded
        assert "=" not in at_hash_rs256  # No padding
        
        # Test with RS512
        at_hash_rs512 = id_token_service._generate_hash(access_token, "RS512")
        assert at_hash_rs512 != at_hash_rs256  # Different algorithms produce different hashes
    
    def test_id_token_with_access_token_hash(self, id_token_service, mock_user, db_session):
        """Test ID token with at_hash for implicit flow"""
        setup_test_signing_key(db_session)
        access_token = "sample.access.token"
        
        id_token = id_token_service.create_id_token(
            user=mock_user,
            client_id="test-client",
            nonce="nonce-456",
            auth_time=datetime.utcnow(),
            scopes=["openid"],
            access_token=access_token,
            authorization_code=None,
            db=db_session
        )
        
        claims = jwt.get_unverified_claims(id_token)
        
        # Verify at_hash is present and correct
        assert "at_hash" in claims
        expected_hash = id_token_service._generate_hash(access_token, "RS256")
        assert claims["at_hash"] == expected_hash
    
    def test_id_token_validation_success(self, id_token_service, mock_user, db_session):
        """Test successful ID token validation"""
        setup_test_signing_key(db_session)
        
        # Create token
        id_token = id_token_service.create_id_token(
            user=mock_user,
            client_id="test-client",
            nonce="nonce-789",
            auth_time=datetime.utcnow(),
            scopes=["openid"],
            access_token=None,
            authorization_code=None,
            db=db_session
        )
        
        # Validate token
        claims = id_token_service.validate_id_token(
            id_token=id_token,
            client_id="test-client",
            nonce="nonce-789",
            db=db_session
        )
        
        assert claims["sub"] == str(mock_user.id)
        assert claims["aud"] == "test-client"
        assert claims["nonce"] == "nonce-789"
    
    def test_id_token_validation_failures(self, id_token_service, db_session):
        """Test various ID token validation failures"""
        setup_test_signing_key(db_session)
        
        # Test with invalid signature
        invalid_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature"
        with pytest.raises(JWTError):
            id_token_service.validate_id_token(
                id_token=invalid_token,
                client_id="test-client",
                nonce=None,
                db=db_session
            )
        
        # Test with wrong audience
        # (Create valid token but validate with wrong client_id)
        
        # Test with expired token
        # (Create token with past expiration)
        
        # Test with wrong nonce
        # (Create token with one nonce, validate with another)
```

### 1.3 Claims Service Tests
```python
# tests/unit/test_claims_service.py
import pytest
from backend.app.services.claims_service import ClaimsService
from backend.app.models import User, Group, Role

class TestClaimsService:
    
    @pytest.fixture
    def claims_service(self):
        return ClaimsService()
    
    @pytest.fixture
    def user_with_group_and_role(self):
        group = Group(id="group-123", name="Developers")
        role = Role(id="role-456", name="Senior Developer")
        
        return User(
            id="user-789",
            email="dev@example.com",
            display_name="Developer User",
            real_name="John Doe",
            group=group,
            group_id=group.id,
            role=role,
            role_id=role.id,
            is_admin=False
        )
    
    def test_profile_scope_claims(self, claims_service, user_with_group_and_role, db_session):
        """Test claims returned for profile scope"""
        claims = claims_service.get_user_claims(
            user=user_with_group_and_role,
            scopes=["profile"],
            db=db_session
        )
        
        assert claims["name"] == "Developer User"
        assert claims["preferred_username"] == "dev"
        assert "given_name" in claims
        assert "family_name" in claims
    
    def test_email_scope_claims(self, claims_service, user_with_group_and_role, db_session):
        """Test claims returned for email scope"""
        claims = claims_service.get_user_claims(
            user=user_with_group_and_role,
            scopes=["email"],
            db=db_session
        )
        
        assert claims["email"] == "dev@example.com"
        assert claims["email_verified"] is True
    
    def test_custom_groups_scope(self, claims_service, user_with_group_and_role, db_session):
        """Test custom groups scope claims"""
        claims = claims_service.get_user_claims(
            user=user_with_group_and_role,
            scopes=["groups"],
            db=db_session
        )
        
        assert claims["groups"] == ["Developers"]
        assert claims["group_id"] == "group-123"
        assert claims["group_name"] == "Developers"
    
    def test_multiple_scopes(self, claims_service, user_with_group_and_role, db_session):
        """Test claims with multiple scopes"""
        claims = claims_service.get_user_claims(
            user=user_with_group_and_role,
            scopes=["profile", "email", "groups", "roles"],
            db=db_session
        )
        
        # Should have claims from all scopes
        assert "name" in claims  # profile
        assert "email" in claims  # email
        assert "groups" in claims  # groups
        assert "role" in claims  # roles
```

## 2. Integration Tests

### 2.1 Full OIDC Flow Tests
```python
# tests/integration/test_oidc_flows.py
import pytest
from fastapi.testclient import TestClient
from urllib.parse import urlparse, parse_qs
import secrets
import hashlib
import base64

class TestOIDCFlows:
    
    @pytest.fixture
    def client(self, app):
        return TestClient(app)
    
    @pytest.fixture
    def test_user_credentials(self):
        return {
            "email": "test@example.com",
            "password": "testpass123"
        }
    
    def test_authorization_code_flow_with_oidc(self, client, test_user_credentials):
        """Test complete authorization code flow with OIDC"""
        
        # Step 1: Create test user and login
        create_test_user(test_user_credentials)
        login_response = client.post("/api/auth/login", json=test_user_credentials)
        access_token = login_response.json()["access_token"]
        
        # Step 2: Authorization request with openid scope
        nonce = secrets.token_urlsafe(16)
        state = secrets.token_urlsafe(16)
        
        auth_params = {
            "response_type": "code",
            "client_id": "test-client",
            "redirect_uri": "http://localhost:3000/callback",
            "scope": "openid profile email",
            "state": state,
            "nonce": nonce
        }
        
        auth_response = client.get(
            "/api/oauth/authorize",
            params=auth_params,
            headers={"Authorization": f"Bearer {access_token}"},
            follow_redirects=False
        )
        
        assert auth_response.status_code == 302
        location = auth_response.headers["location"]
        parsed = urlparse(location)
        query = parse_qs(parsed.query)
        
        assert "code" in query
        assert query["state"][0] == state
        
        # Step 3: Token exchange
        code = query["code"][0]
        
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "http://localhost:3000/callback",
            "client_id": "test-client",
            "client_secret": "test-secret"
        }
        
        token_response = client.post(
            "/api/oauth/token",
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert token_response.status_code == 200
        token_json = token_response.json()
        
        # Verify response contains ID token
        assert "access_token" in token_json
        assert "id_token" in token_json
        assert "token_type" in token_json
        assert token_json["token_type"] == "Bearer"
        
        # Step 4: Validate ID token
        id_token = token_json["id_token"]
        
        # Decode and verify claims
        from jose import jwt
        unverified_claims = jwt.get_unverified_claims(id_token)
        
        assert unverified_claims["nonce"] == nonce
        assert unverified_claims["email"] == "test@example.com"
        assert "sub" in unverified_claims
        assert "aud" in unverified_claims
        assert "exp" in unverified_claims
        assert "iat" in unverified_claims
    
    def test_implicit_flow_with_id_token(self, client, test_user_credentials):
        """Test implicit flow requesting ID token"""
        
        # Login first
        create_test_user(test_user_credentials)
        login_response = client.post("/api/auth/login", json=test_user_credentials)
        access_token = login_response.json()["access_token"]
        
        # Authorization request for implicit flow
        nonce = secrets.token_urlsafe(16)
        state = secrets.token_urlsafe(16)
        
        auth_params = {
            "response_type": "id_token token",
            "client_id": "test-client",
            "redirect_uri": "http://localhost:3000/callback",
            "scope": "openid profile",
            "state": state,
            "nonce": nonce,
            "response_mode": "fragment"
        }
        
        auth_response = client.get(
            "/api/oauth/authorize",
            params=auth_params,
            headers={"Authorization": f"Bearer {access_token}"},
            follow_redirects=False
        )
        
        assert auth_response.status_code == 302
        location = auth_response.headers["location"]
        
        # Parse fragment (after #)
        parsed = urlparse(location)
        fragment_params = parse_qs(parsed.fragment)
        
        assert "id_token" in fragment_params
        assert "access_token" in fragment_params
        assert fragment_params["state"][0] == state
        
        # Verify at_hash in ID token
        id_token = fragment_params["id_token"][0]
        access_token = fragment_params["access_token"][0]
        
        claims = jwt.get_unverified_claims(id_token)
        assert "at_hash" in claims
        
        # Verify at_hash is correct
        hash_input = access_token.encode('ascii')
        hash_digest = hashlib.sha256(hash_input).digest()
        at_hash = base64.urlsafe_b64encode(hash_digest[:16]).decode().rstrip('=')
        assert claims["at_hash"] == at_hash
    
    def test_hybrid_flow(self, client, test_user_credentials):
        """Test hybrid flow with code and ID token"""
        
        # Test response_type = "code id_token"
        # Should return both authorization code and ID token
        # ID token should include c_hash claim
        pass
```

### 2.2 Discovery and JWKS Tests
```python
# tests/integration/test_discovery.py
import pytest
import requests
from jose import jwk

class TestDiscoveryAndJWKS:
    
    def test_openid_configuration(self, live_server):
        """Test OpenID Configuration discovery endpoint"""
        
        response = requests.get(f"{live_server.url}/.well-known/openid-configuration")
        
        assert response.status_code == 200
        config = response.json()
        
        # Validate required fields
        assert config["issuer"] == live_server.url
        assert config["authorization_endpoint"] == f"{live_server.url}/api/oauth/authorize"
        assert config["token_endpoint"] == f"{live_server.url}/api/oauth/token"
        assert config["userinfo_endpoint"] == f"{live_server.url}/api/oauth/userinfo"
        assert config["jwks_uri"] == f"{live_server.url}/api/oauth/jwks"
        
        # Validate supported values
        assert "code" in config["response_types_supported"]
        assert "openid" in config["scopes_supported"]
        assert "RS256" in config["id_token_signing_alg_values_supported"]
        
        # Validate all endpoints are reachable
        for endpoint_key in ["authorization_endpoint", "token_endpoint", "userinfo_endpoint", "jwks_uri"]:
            endpoint_url = config[endpoint_key]
            # Skip actual authorization endpoint (requires auth)
            if "authorize" not in endpoint_url:
                resp = requests.get(endpoint_url)
                assert resp.status_code in [200, 401, 405]  # Endpoint exists
    
    def test_jwks_endpoint(self, live_server):
        """Test JWKS endpoint returns valid keys"""
        
        response = requests.get(f"{live_server.url}/api/oauth/jwks")
        
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json"
        
        jwks_data = response.json()
        assert "keys" in jwks_data
        assert isinstance(jwks_data["keys"], list)
        assert len(jwks_data["keys"]) > 0
        
        # Validate each key
        for key_data in jwks_data["keys"]:
            assert key_data["kty"] == "RSA"
            assert key_data["use"] == "sig"
            assert "kid" in key_data
            assert "n" in key_data
            assert "e" in key_data
            assert key_data["alg"] in ["RS256", "RS384", "RS512"]
            
            # Verify key can be loaded
            try:
                jwk_key = jwk.construct(key_data)
                assert jwk_key is not None
            except Exception as e:
                pytest.fail(f"Failed to construct JWK: {e}")
    
    def test_jwks_key_rotation(self, live_server, admin_client):
        """Test JWKS endpoint handles key rotation properly"""
        
        # Get initial keys
        response1 = requests.get(f"{live_server.url}/api/oauth/jwks")
        keys1 = response1.json()["keys"]
        kids1 = {key["kid"] for key in keys1}
        
        # Trigger key rotation (admin endpoint)
        admin_client.post("/api/admin/rotate-keys")
        
        # Get keys after rotation
        response2 = requests.get(f"{live_server.url}/api/oauth/jwks")
        keys2 = response2.json()["keys"]
        kids2 = {key["kid"] for key in keys2}
        
        # Should have both old and new keys during grace period
        assert len(keys2) > len(keys1)
        assert kids1.issubset(kids2)  # Old keys still present
        assert kids2 - kids1  # New keys added
```

## 3. Security Tests

### 3.1 Token Security Tests
```python
# tests/security/test_token_security.py
import pytest
import time
from jose import jwt, JWTError

class TestTokenSecurity:
    
    def test_nonce_replay_attack_prevention(self, client):
        """Test that nonce cannot be reused"""
        
        # Use same nonce twice
        nonce = "duplicate-nonce-123"
        
        # First request should succeed
        first_response = make_oidc_request(client, nonce=nonce)
        assert first_response.status_code == 200
        
        # Second request with same nonce should fail
        second_response = make_oidc_request(client, nonce=nonce)
        assert second_response.status_code == 400
        assert "nonce" in second_response.json()["error_description"].lower()
    
    def test_token_expiration_validation(self, client):
        """Test that expired tokens are rejected"""
        
        # Create token with very short expiration
        expired_token = create_test_id_token(expires_in=-60)  # Expired 60 seconds ago
        
        # Try to use expired token
        response = client.get(
            "/api/protected",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()
    
    def test_audience_validation(self, client):
        """Test that tokens with wrong audience are rejected"""
        
        # Create token for different client
        wrong_aud_token = create_test_id_token(aud="different-client")
        
        # Try to validate for our client
        with pytest.raises(JWTError) as exc_info:
            validate_id_token(wrong_aud_token, expected_aud="test-client")
        
        assert "audience" in str(exc_info.value).lower()
    
    def test_signature_tampering_detection(self, client):
        """Test that tampered signatures are detected"""
        
        # Create valid token
        valid_token = create_test_id_token()
        
        # Tamper with signature
        parts = valid_token.split('.')
        tampered_signature = parts[2][:-4] + "XXXX"  # Change last 4 chars
        tampered_token = f"{parts[0]}.{parts[1]}.{tampered_signature}"
        
        # Try to validate tampered token
        with pytest.raises(JWTError) as exc_info:
            validate_id_token(tampered_token)
        
        assert "signature" in str(exc_info.value).lower()
    
    def test_at_hash_validation(self, client):
        """Test at_hash validation for implicit flow security"""
        
        access_token = "test.access.token"
        
        # Create ID token with correct at_hash
        correct_token = create_test_id_token(
            access_token=access_token,
            include_at_hash=True
        )
        
        # Validation should succeed
        claims = validate_id_token(correct_token, access_token=access_token)
        assert claims is not None
        
        # Create ID token with wrong at_hash
        wrong_token = create_test_id_token(
            access_token="different.token",
            include_at_hash=True
        )
        
        # Validation should fail
        with pytest.raises(JWTError) as exc_info:
            validate_id_token(wrong_token, access_token=access_token)
        
        assert "at_hash" in str(exc_info.value).lower()
```

### 3.2 Authorization Security Tests
```python
# tests/security/test_authorization_security.py
import pytest

class TestAuthorizationSecurity:
    
    def test_pkce_required_for_public_clients(self, client):
        """Test that public clients must use PKCE"""
        
        # Try authorization without PKCE
        response = client.get("/api/oauth/authorize", params={
            "response_type": "code",
            "client_id": "public-client",
            "redirect_uri": "http://localhost:3000/callback",
            "scope": "openid"
        })
        
        assert response.status_code == 400
        assert "code_challenge" in response.json()["error_description"]
    
    def test_redirect_uri_validation(self, client):
        """Test that only registered redirect URIs are allowed"""
        
        # Try with unregistered redirect URI
        response = client.get("/api/oauth/authorize", params={
            "response_type": "code",
            "client_id": "test-client",
            "redirect_uri": "http://evil.com/steal-token",
            "scope": "openid"
        })
        
        assert response.status_code == 400
        assert "redirect_uri" in response.json()["error_description"]
    
    def test_state_parameter_preserved(self, client):
        """Test that state parameter is preserved to prevent CSRF"""
        
        state = "unique-state-12345"
        
        # Make authorization request
        response = make_authorization_request(client, state=state)
        
        # Check state is preserved in redirect
        location = response.headers["location"]
        assert f"state={state}" in location
    
    def test_response_type_validation(self, client):
        """Test that only supported response types are allowed"""
        
        # Try unsupported response type
        response = client.get("/api/oauth/authorize", params={
            "response_type": "invalid_type",
            "client_id": "test-client",
            "redirect_uri": "http://localhost:3000/callback",
            "scope": "openid"
        })
        
        assert response.status_code == 400
        assert "response_type" in response.json()["error_description"]
```

## 4. Compliance Tests

### 4.1 OIDC Conformance Tests
```python
# tests/compliance/test_oidc_conformance.py
"""
These tests validate compliance with OpenID Connect Core 1.0 specification
Reference: https://openid.net/specs/openid-connect-core-1_0.html
"""

class TestOIDCConformance:
    
    def test_required_endpoints_exist(self, client):
        """3.1.2.1 - Authorization endpoint requirements"""
        
        # Authorization endpoint must support GET and POST
        get_response = client.get("/api/oauth/authorize")
        post_response = client.post("/api/oauth/authorize")
        
        assert get_response.status_code in [302, 400]  # Redirect or error
        assert post_response.status_code in [302, 400]
    
    def test_id_token_required_claims(self, id_token):
        """2 - ID Token must contain required claims"""
        
        claims = jwt.get_unverified_claims(id_token)
        
        # Required claims per spec
        required = ["iss", "sub", "aud", "exp", "iat"]
        for claim in required:
            assert claim in claims, f"Missing required claim: {claim}"
        
        # Validate claim types
        assert isinstance(claims["iss"], str)
        assert isinstance(claims["sub"], str)
        assert isinstance(claims["aud"], (str, list))
        assert isinstance(claims["exp"], (int, float))
        assert isinstance(claims["iat"], (int, float))
    
    def test_auth_time_claim_when_max_age(self, client):
        """3.1.2.1 - auth_time required when max_age requested"""
        
        # Request with max_age
        response = make_authorization_request(client, max_age=300)
        id_token = extract_id_token(response)
        
        claims = jwt.get_unverified_claims(id_token)
        assert "auth_time" in claims
        assert isinstance(claims["auth_time"], (int, float))
    
    def test_nonce_claim_preserved(self, client):
        """3.1.2.1 - nonce must be preserved in ID token"""
        
        nonce = "test-nonce-456"
        response = make_authorization_request(client, nonce=nonce)
        id_token = extract_id_token(response)
        
        claims = jwt.get_unverified_claims(id_token)
        assert claims.get("nonce") == nonce
    
    def test_acr_claim_when_requested(self, client):
        """3.1.2.1 - acr claim when acr_values requested"""
        
        response = make_authorization_request(client, acr_values="1 2")
        id_token = extract_id_token(response)
        
        claims = jwt.get_unverified_claims(id_token)
        assert "acr" in claims
        assert claims["acr"] in ["1", "2"]
```

### 4.2 Standards Compliance Tests
```python
# tests/compliance/test_standards.py

class TestStandardsCompliance:
    
    def test_jwt_header_compliance(self, id_token):
        """RFC 7519 - JWT header requirements"""
        
        header = jwt.get_unverified_header(id_token)
        
        assert header["typ"] in ["JWT", None]  # Optional but if present must be JWT
        assert header["alg"] in ["RS256", "RS384", "RS512", "HS256"]
        assert "kid" in header  # Key ID for key selection
    
    def test_jose_compliance(self, id_token):
        """RFC 7515 - JWS compliance"""
        
        # Token must be valid JWS format
        parts = id_token.split('.')
        assert len(parts) == 3  # Header.Payload.Signature
        
        # Each part must be base64url encoded
        for part in parts:
            assert all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_' for c in part)
    
    def test_oauth2_compatibility(self, client):
        """RFC 6749 - OAuth 2.0 compatibility"""
        
        # OIDC requests without openid scope should work as pure OAuth 2.0
        response = client.post("/api/oauth/token", data={
            "grant_type": "authorization_code",
            "code": get_test_auth_code(),
            "client_id": "test-client",
            "client_secret": "secret",
            "redirect_uri": "http://localhost:3000/callback"
        })
        
        assert response.status_code == 200
        token_data = response.json()
        
        # Should not include ID token without openid scope
        assert "access_token" in token_data
        assert "id_token" not in token_data
```

## 5. Performance Tests

### 5.1 Load Testing
```python
# tests/performance/test_load.py
import pytest
import asyncio
import aiohttp
import time
from statistics import mean, stdev

class TestPerformance:
    
    @pytest.mark.asyncio
    async def test_token_generation_performance(self):
        """Test ID token generation under load"""
        
        async def generate_token():
            start = time.time()
            async with aiohttp.ClientSession() as session:
                # Make token request
                async with session.post(
                    "http://localhost:8000/api/oauth/token",
                    data={
                        "grant_type": "authorization_code",
                        "code": await get_auth_code(),
                        "client_id": "test-client",
                        "client_secret": "secret"
                    }
                ) as response:
                    await response.json()
            return time.time() - start
        
        # Run 100 concurrent requests
        tasks = [generate_token() for _ in range(100)]
        response_times = await asyncio.gather(*tasks)
        
        # Analyze results
        avg_time = mean(response_times)
        std_dev = stdev(response_times)
        max_time = max(response_times)
        
        # Performance requirements
        assert avg_time < 0.1  # Average under 100ms
        assert max_time < 0.5  # Max under 500ms
        assert std_dev < 0.05  # Consistent performance
    
    @pytest.mark.asyncio
    async def test_jwks_endpoint_performance(self):
        """Test JWKS endpoint can handle high load"""
        
        async def fetch_jwks():
            async with aiohttp.ClientSession() as session:
                start = time.time()
                async with session.get("http://localhost:8000/api/oauth/jwks") as response:
                    await response.json()
                return time.time() - start
        
        # Run 1000 concurrent requests (JWKS should be cached)
        tasks = [fetch_jwks() for _ in range(1000)]
        response_times = await asyncio.gather(*tasks)
        
        # Should be very fast due to caching
        avg_time = mean(response_times)
        assert avg_time < 0.01  # Average under 10ms
    
    def test_token_validation_performance(self):
        """Test token validation performance"""
        
        # Create test tokens
        tokens = [create_test_id_token() for _ in range(100)]
        
        # Measure validation time
        start = time.time()
        for token in tokens:
            validate_id_token(token)
        total_time = time.time() - start
        
        # Should validate 100 tokens in under 1 second
        assert total_time < 1.0
        assert (total_time / 100) < 0.01  # Under 10ms per token
```

### 5.2 Stress Testing
```python
# tests/performance/test_stress.py
import pytest
from locust import HttpUser, task, between

class OIDCUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # Login and get access token
        response = self.client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "password"
        })
        self.access_token = response.json()["access_token"]
    
    @task(3)
    def authorize_request(self):
        """Simulate authorization requests"""
        self.client.get(
            "/api/oauth/authorize",
            params={
                "response_type": "code",
                "client_id": "test-client",
                "redirect_uri": "http://localhost:3000/callback",
                "scope": "openid profile",
                "state": "random-state",
                "nonce": "random-nonce"
            },
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
    
    @task(2)
    def token_exchange(self):
        """Simulate token exchange"""
        # Get auth code first
        auth_response = self.authorize_request()
        code = extract_code(auth_response)
        
        # Exchange for tokens
        self.client.post(
            "/api/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": "test-client",
                "client_secret": "secret"
            }
        )
    
    @task(1)
    def userinfo_request(self):
        """Simulate userinfo requests"""
        self.client.get(
            "/api/oauth/userinfo",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
    
    @task(5)
    def jwks_request(self):
        """Simulate JWKS requests (should be frequent)"""
        self.client.get("/api/oauth/jwks")

# Run with: locust -f test_stress.py --host=http://localhost:8000
```

## 6. Test Data and Fixtures

### 6.1 Test Fixtures
```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.database import Base
from backend.app.models import User, OAuthClient
from backend.app.services.jwks_service import jwks_service

@pytest.fixture(scope="session")
def test_db():
    """Create test database"""
    engine = create_engine("postgresql://test:test@localhost:5433/test_oidc")
    Base.metadata.create_all(bind=engine)
    
    SessionLocal = sessionmaker(bind=engine)
    
    yield SessionLocal
    
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session(test_db):
    """Create test database session"""
    session = test_db()
    
    yield session
    
    session.rollback()
    session.close()

@pytest.fixture
def test_client_app(db_session):
    """Create test OAuth client"""
    client = OAuthClient(
        client_id="test-client",
        client_secret="test-secret",
        client_name="Test Client",
        redirect_uris=["http://localhost:3000/callback"],
        allowed_scopes=["openid", "profile", "email"],
        is_confidential=True,
        oidc_enabled=True
    )
    db_session.add(client)
    db_session.commit()
    
    return client

@pytest.fixture
def test_signing_key(db_session):
    """Setup test signing key"""
    kid, private_key, public_key = jwks_service.generate_key_pair()
    jwks_service.store_key_pair(db_session, kid, private_key, public_key)
    return kid

@pytest.fixture
def test_user(db_session):
    """Create test user"""
    user = User(
        email="test@example.com",
        password_hash=hash_password("password"),
        display_name="Test User",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    
    return user
```

## 7. CI/CD Integration

### 7.1 GitHub Actions Workflow
```yaml
# .github/workflows/oidc-tests.yml
name: OIDC Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run unit tests
      run: |
        pytest tests/unit -v --cov=backend/app/services --cov-report=xml
    
    - name: Run integration tests
      run: |
        pytest tests/integration -v
    
    - name: Run security tests
      run: |
        pytest tests/security -v
    
    - name: Run compliance tests
      run: |
        pytest tests/compliance -v
    
    - name: Run performance tests
      run: |
        pytest tests/performance -v -m "not stress"
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

## 8. Test Execution Plan

### Phase 1: Unit Tests (Week 1)
- Run all unit tests for individual components
- Achieve >90% code coverage
- Fix any failing tests

### Phase 2: Integration Tests (Week 2)
- Test complete OIDC flows
- Verify all endpoints work correctly
- Test edge cases and error scenarios

### Phase 3: Security Tests (Week 3)
- Run security validation tests
- Perform penetration testing
- Validate all security measures

### Phase 4: Compliance Tests (Week 4)
- Run OIDC conformance suite
- Validate standards compliance
- Document any deviations

### Phase 5: Performance Tests (Week 5)
- Run load tests
- Measure response times
- Optimize bottlenecks

### Phase 6: User Acceptance Testing (Week 6)
- Test with real clients
- Gather feedback
- Make final adjustments

## 9. Success Criteria

- All unit tests pass with >90% coverage
- All integration tests pass
- All security tests pass
- OIDC conformance tests pass
- Performance meets requirements (<100ms average)
- No critical security vulnerabilities
- Backward compatibility maintained
- Zero authentication failures during migration