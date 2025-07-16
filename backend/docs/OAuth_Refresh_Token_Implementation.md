# OAuth 2.0 Refresh Token Implementation Documentation

## Overview

This document provides comprehensive details about the RFC 6749 compliant refresh token implementation in the MAX Platform OAuth 2.0 system. The implementation adds full refresh token support to the existing authorization code flow, enabling long-lived authentication sessions without requiring users to re-authenticate.

## Key Features

- **RFC 6749 Compliant**: Full compliance with OAuth 2.0 specifications
- **Token Rotation**: Automatic refresh token rotation for enhanced security
- **Comprehensive Audit**: Full logging of all token operations
- **Security Hardened**: Cryptographically secure token generation and storage
- **Database Optimized**: Proper indexing and cleanup mechanisms

## Database Schema Changes

### New Table: `oauth_refresh_tokens`

```sql
CREATE TABLE oauth_refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_hash VARCHAR(255) NOT NULL UNIQUE,           -- SHA256 hash of refresh token
    client_id VARCHAR(50) NOT NULL REFERENCES oauth_clients(client_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    scope TEXT,                                         -- Granted OAuth scopes
    access_token_hash VARCHAR(255),                     -- Currently linked access token
    expires_at TIMESTAMP NOT NULL,                      -- Token expiration (30 days default)
    created_at TIMESTAMP DEFAULT NOW(),
    revoked_at TIMESTAMP,                              -- Token revocation timestamp
    last_used_at TIMESTAMP,                            -- Last token usage tracking
    client_ip INET,                                    -- Security: client IP tracking
    user_agent TEXT,                                   -- Security: user agent tracking
    rotation_count INTEGER DEFAULT 0                   -- Security: rotation counter
);
```

### Updated Table: `oauth_access_tokens`

Added column:
```sql
ALTER TABLE oauth_access_tokens ADD COLUMN refresh_token_hash VARCHAR(255);
```

### Database Indexes

```sql
CREATE INDEX idx_oauth_refresh_tokens_token_hash ON oauth_refresh_tokens(token_hash);
CREATE INDEX idx_oauth_refresh_tokens_expires_at ON oauth_refresh_tokens(expires_at);
CREATE INDEX idx_oauth_refresh_tokens_user_client ON oauth_refresh_tokens(user_id, client_id);
CREATE INDEX idx_oauth_refresh_tokens_access_token ON oauth_refresh_tokens(access_token_hash);
CREATE INDEX idx_oauth_access_tokens_refresh_token ON oauth_access_tokens(refresh_token_hash);
```

## API Changes

### Token Endpoint (`POST /api/oauth/token`)

The token endpoint now supports two grant types:

#### 1. Authorization Code Grant (`grant_type=authorization_code`)

**Request:**
```http
POST /api/oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&
code=<authorization_code>&
redirect_uri=<redirect_uri>&
client_id=<client_id>&
client_secret=<client_secret>&
code_verifier=<pkce_verifier>
```

**Response:**
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "scope": "read:profile read:groups",
    "refresh_token": "Rh8xS2kF9oP3mN7q...",
    "refresh_expires_in": 2592000
}
```

#### 2. Refresh Token Grant (`grant_type=refresh_token`)

**Request:**
```http
POST /api/oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token&
refresh_token=<refresh_token>&
client_id=<client_id>&
client_secret=<client_secret>
```

**Response:**
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "token_type": "Bearer", 
    "expires_in": 3600,
    "scope": "read:profile read:groups",
    "refresh_token": "Nz9dQ5vR8tY2wX6m...",
    "refresh_expires_in": 2592000
}
```

### OAuth Metadata Endpoint

The `/.well-known/oauth-authorization-server` endpoint now advertises refresh token support:

```json
{
    "grant_types_supported": ["authorization_code", "refresh_token"],
    ...
}
```

## Security Features

### 1. Token Rotation

**Implementation**: Every refresh token usage generates a new refresh token and invalidates the old one.

**Benefits**:
- Prevents replay attacks
- Limits token lifespan exposure
- Detects compromised tokens

**Process**:
1. Client presents refresh token
2. Server validates token
3. Server generates new access + refresh token pair
4. Server invalidates old refresh token
5. Server returns new tokens

### 2. Cryptographic Security

**Token Generation**:
- 48-byte (384-bit) cryptographically secure random tokens
- Base64 URL-safe encoding
- SHA256 hashing for database storage

**Code Example**:
```python
def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)  # 384 bits of entropy

def generate_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
```

### 3. Comprehensive Audit Logging

All refresh token operations are logged to `oauth_audit_logs`:

- Token creation
- Token usage/rotation
- Token revocation
- Failed validation attempts
- Security violations

### 4. Automatic Cleanup

The system automatically removes:
- Expired refresh tokens (> 30 days)
- Revoked refresh tokens
- Orphaned access tokens

## Integration Guide

### For Frontend Developers

#### 1. Authorization Code Flow with Refresh Token

```javascript
// Step 1: Exchange authorization code for tokens
const tokenResponse = await fetch('/api/oauth/token', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
        grant_type: 'authorization_code',
        code: authorizationCode,
        redirect_uri: redirectUri,
        client_id: clientId,
        client_secret: clientSecret,
        code_verifier: codeVerifier
    })
});

const tokens = await tokenResponse.json();
// Store tokens securely
localStorage.setItem('access_token', tokens.access_token);
localStorage.setItem('refresh_token', tokens.refresh_token);
```

#### 2. Automatic Token Refresh

```javascript
async function refreshAccessToken() {
    const refreshToken = localStorage.getItem('refresh_token');
    
    try {
        const response = await fetch('/api/oauth/token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                grant_type: 'refresh_token',
                refresh_token: refreshToken,
                client_id: clientId,
                client_secret: clientSecret
            })
        });
        
        if (response.ok) {
            const tokens = await response.json();
            // Update stored tokens
            localStorage.setItem('access_token', tokens.access_token);
            localStorage.setItem('refresh_token', tokens.refresh_token);
            return tokens.access_token;
        } else {
            // Refresh token expired or invalid - redirect to login
            redirectToLogin();
        }
    } catch (error) {
        console.error('Token refresh failed:', error);
        redirectToLogin();
    }
}
```

#### 3. API Request Interceptor

```javascript
// Axios interceptor example
axios.interceptors.response.use(
    (response) => response,
    async (error) => {
        if (error.response?.status === 401) {
            // Token expired, try to refresh
            const newToken = await refreshAccessToken();
            if (newToken) {
                // Retry original request with new token
                error.config.headers.Authorization = `Bearer ${newToken}`;
                return axios.request(error.config);
            }
        }
        return Promise.reject(error);
    }
);
```

### For Backend Developers

#### 1. Token Validation

```python
from app.api.oauth_simple import validate_refresh_token

def validate_user_refresh_token(refresh_token: str, client_id: str, db: Session) -> bool:
    token_info = validate_refresh_token(refresh_token, client_id, db)
    return token_info is not None
```

#### 2. Manual Token Revocation

```python
from app.api.oauth_simple import revoke_refresh_token, generate_token_hash

def revoke_user_refresh_token(refresh_token: str, db: Session) -> bool:
    token_hash = generate_token_hash(refresh_token)
    return revoke_refresh_token(token_hash, db)
```

#### 3. User Session Management

```python
# Get all active refresh tokens for a user
def get_user_active_sessions(user_id: str, db: Session) -> List[dict]:
    result = db.execute(
        text('''
            SELECT client_id, created_at, last_used_at, client_ip, user_agent
            FROM oauth_refresh_tokens 
            WHERE user_id = :user_id 
            AND revoked_at IS NULL 
            AND expires_at > NOW()
            ORDER BY last_used_at DESC
        '''),
        {"user_id": user_id}
    )
    return [dict(row) for row in result.fetchall()]

# Revoke all sessions for a user (logout everywhere)
def revoke_all_user_sessions(user_id: str, db: Session) -> int:
    result = db.execute(
        text('''
            UPDATE oauth_refresh_tokens 
            SET revoked_at = NOW() 
            WHERE user_id = :user_id 
            AND revoked_at IS NULL
        '''),
        {"user_id": user_id}
    )
    db.commit()
    return result.rowcount
```

## Configuration

### Environment Variables

```bash
# Token expiration settings
ACCESS_TOKEN_EXPIRE_MINUTES=60          # Access token lifetime (1 hour)
REFRESH_TOKEN_EXPIRE_DAYS=30            # Refresh token lifetime (30 days)

# Security settings
OAUTH_TOKEN_ROTATION_ENABLED=true       # Enable token rotation
OAUTH_AUDIT_LOGGING_ENABLED=true        # Enable audit logging
```

### Database Configuration

```python
# settings.py
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 30
```

## Error Handling

### Common Error Responses

#### Invalid Refresh Token
```json
{
    "error": "invalid_grant",
    "error_description": "Invalid or expired refresh token"
}
```

#### Missing Parameters
```json
{
    "error": "invalid_request", 
    "error_description": "Missing refresh_token parameter"
}
```

#### Client Authentication Failed
```json
{
    "error": "invalid_client",
    "error_description": "Client authentication failed"
}
```

## Monitoring and Maintenance

### 1. Database Monitoring

Monitor these metrics:
- Refresh token usage patterns
- Token rotation frequency  
- Failed authentication attempts
- Token cleanup efficiency

### 2. Performance Considerations

- Index usage on token lookups
- Database connection pooling
- Token cleanup scheduling
- Audit log rotation

### 3. Security Monitoring

Watch for:
- Excessive token refresh requests
- Refresh token reuse attempts
- Unusual client authentication patterns
- Geographic anomalies in token usage

## Troubleshooting

### Common Issues

#### 1. "Invalid or expired refresh token"
**Cause**: Token expired, revoked, or client_id mismatch
**Solution**: Check token expiration, verify client_id matches

#### 2. "Client authentication failed"
**Cause**: Invalid client credentials
**Solution**: Verify client_id and client_secret

#### 3. "Token refresh failed"
**Cause**: Database error during token rotation
**Solution**: Check database connectivity and transaction logs

### Debug Queries

```sql
-- Check refresh token status
SELECT 
    token_hash, client_id, user_id, expires_at, revoked_at, rotation_count
FROM oauth_refresh_tokens 
WHERE token_hash = '<token_hash>';

-- Check recent audit logs
SELECT *
FROM oauth_audit_logs 
WHERE action = 'token' 
ORDER BY created_at DESC 
LIMIT 10;

-- Monitor token usage patterns
SELECT 
    client_id, 
    COUNT(*) as token_count,
    AVG(rotation_count) as avg_rotations
FROM oauth_refresh_tokens 
WHERE revoked_at IS NULL 
GROUP BY client_id;
```

## Migration Guide

### From No Refresh Tokens

1. **Deploy database schema changes**
2. **Update client applications** to handle refresh tokens
3. **Monitor token usage patterns**
4. **Gradually migrate users** to refresh token flow

### Rollback Plan

If issues arise:
1. Revert OAuth metadata to exclude refresh_token
2. Clients fall back to authorization_code only
3. Existing refresh tokens remain valid but unused
4. Database schema can remain (no data loss)

## Best Practices

### Client-Side

1. **Secure Storage**: Store refresh tokens in httpOnly cookies or secure storage
2. **Token Rotation**: Always use new refresh token from response
3. **Error Handling**: Implement proper fallback to re-authentication
4. **Background Refresh**: Refresh tokens before access token expiry

### Server-Side

1. **Token Rotation**: Always rotate refresh tokens on use
2. **Audit Logging**: Log all token operations for security monitoring
3. **Cleanup**: Regularly clean expired tokens
4. **Rate Limiting**: Implement rate limiting on token endpoint

## Support and Maintenance

### Monitoring Checklist

- [ ] Database performance (token table sizes)
- [ ] Token rotation success rates
- [ ] Authentication failure patterns
- [ ] Cleanup job execution
- [ ] Audit log growth

### Regular Maintenance

- Weekly: Review audit logs for anomalies
- Monthly: Analyze token usage patterns
- Quarterly: Review and update security policies
- Annually: Security audit of token implementation

## Conclusion

This refresh token implementation provides a secure, RFC 6749 compliant solution for long-lived authentication sessions in the MAX Platform. The implementation includes comprehensive security features, proper error handling, and extensive monitoring capabilities to ensure reliable operation in production environments.

For questions or issues, refer to the troubleshooting section or contact the development team.