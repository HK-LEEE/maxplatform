# OIDC Migration Strategy for MAX Platform

## Executive Summary

This document outlines the migration strategy for transitioning existing OAuth 2.0 clients to OpenID Connect (OIDC) while maintaining backward compatibility and zero downtime.

## Current State Analysis

### Existing OAuth 2.0 Clients
```
1. maxflowstudio - Visual workflow design platform
2. maxteamsync - Team collaboration platform  
3. maxlab - R&D experimentation platform
4. maxworkspace - Integrated workspace platform
5. maxapa - API management platform
6. maxmlops - ML operations platform
```

### Current Implementation
- Pure OAuth 2.0 with custom user info endpoint
- Access tokens in JWT format (HS256)
- No ID tokens
- No discovery mechanism
- Custom scopes without OIDC standard scopes

## Migration Principles

1. **Zero Breaking Changes**: Existing OAuth 2.0 flows must continue to work
2. **Gradual Adoption**: Clients can migrate to OIDC at their own pace
3. **Backward Compatibility**: Old tokens remain valid until expiration
4. **Feature Detection**: Clients can detect OIDC support via discovery
5. **Dual Mode Operation**: Support both OAuth 2.0 and OIDC simultaneously

## Migration Phases

### Phase 1: Infrastructure Preparation (Week 1)

#### 1.1 Database Schema Updates
```sql
-- Add OIDC support flags to clients
ALTER TABLE oauth_clients 
ADD COLUMN oidc_enabled BOOLEAN DEFAULT false,
ADD COLUMN id_token_signed_response_alg VARCHAR(10) DEFAULT 'RS256',
ADD COLUMN userinfo_signed_response_alg VARCHAR(10),
ADD COLUMN default_max_age INTEGER,
ADD COLUMN require_auth_time BOOLEAN DEFAULT false,
ADD COLUMN oidc_migration_date TIMESTAMP;

-- Add OIDC scopes to existing clients
UPDATE oauth_clients 
SET allowed_scopes = array_cat(
    allowed_scopes, 
    ARRAY['openid', 'profile', 'email', 'offline_access']
)
WHERE client_id IN ('maxflowstudio', 'maxteamsync', 'maxlab', 'maxworkspace', 'maxapa', 'maxmlops');

-- Create migration tracking table
CREATE TABLE oidc_migration_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id VARCHAR(50) NOT NULL REFERENCES oauth_clients(client_id),
    migration_phase VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL, -- planning, in_progress, completed, rolled_back
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### 1.2 Configuration Updates
```python
# backend/app/config.py additions
class Settings(BaseSettings):
    # ... existing settings ...
    
    # OIDC Migration Settings
    oidc_migration_enabled: bool = os.getenv("OIDC_MIGRATION_ENABLED", "true")
    oidc_dual_mode: bool = os.getenv("OIDC_DUAL_MODE", "true")  # Support both OAuth and OIDC
    oidc_legacy_hs256_support: bool = os.getenv("OIDC_LEGACY_HS256", "true")  # For transition
    oidc_migration_grace_period_days: int = int(os.getenv("OIDC_GRACE_PERIOD_DAYS", "90"))
```

### Phase 2: Dual-Mode Implementation (Week 2)

#### 2.1 Token Service Modifications
```python
# backend/app/api/oauth_simple.py modifications

def handle_authorization_code_grant(...):
    # ... existing code ...
    
    # Check if client has OIDC enabled
    client_oidc_enabled = check_client_oidc_status(client_id, db)
    
    # Parse scopes
    scopes = auth_code_dict['scope'].split() if auth_code_dict['scope'] else []
    
    # Determine token response based on client configuration and scopes
    if "openid" in scopes and (client_oidc_enabled or settings.oidc_dual_mode):
        # OIDC flow - return ID token
        response = create_oidc_token_response(...)
    else:
        # Legacy OAuth 2.0 flow
        response = create_oauth_token_response(...)
    
    return response

def check_client_oidc_status(client_id: str, db: Session) -> bool:
    """Check if client has OIDC enabled"""
    result = db.execute(
        text("SELECT oidc_enabled FROM oauth_clients WHERE client_id = :client_id"),
        {"client_id": client_id}
    )
    row = result.first()
    return row[0] if row else False
```

#### 2.2 Backward Compatibility Layer
```python
# backend/app/services/compatibility_service.py

class CompatibilityService:
    """Service to ensure backward compatibility during OIDC migration"""
    
    def create_hybrid_token_response(
        self,
        user: User,
        client_id: str,
        scopes: List[str],
        auth_code_dict: Dict,
        db: Session
    ) -> Dict:
        """Create token response that works for both OAuth 2.0 and OIDC clients"""
        
        # Always create access token (works for both)
        access_token = create_access_token(...)
        
        response = {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
            "scope": " ".join(scopes)
        }
        
        # Add refresh token if requested
        if "offline_access" in scopes or need_refresh_token(scopes):
            response["refresh_token"] = create_refresh_token(...)
        
        # Add ID token only if openid scope present
        if "openid" in scopes:
            # Check client preference for signing algorithm
            signing_alg = get_client_signing_algorithm(client_id, db)
            
            if signing_alg == "HS256" and settings.oidc_legacy_hs256_support:
                # Use symmetric key for legacy support
                id_token = create_hs256_id_token(...)
            else:
                # Use asymmetric key (recommended)
                id_token = id_token_service.create_id_token(...)
            
            response["id_token"] = id_token
        
        return response
    
    def validate_hybrid_token(
        self,
        token: str,
        client_id: str,
        db: Session
    ) -> Dict:
        """Validate tokens from both OAuth 2.0 and OIDC clients"""
        
        # Try to decode header
        try:
            header = jwt.get_unverified_header(token)
            alg = header.get("alg", "HS256")
            
            if alg == "HS256":
                # Legacy symmetric validation
                return validate_hs256_token(token, client_id)
            else:
                # Modern asymmetric validation
                return id_token_service.validate_id_token(token, client_id, None, db)
                
        except Exception as e:
            # Fallback to access token validation
            return validate_access_token(token)
```

### Phase 3: Client Migration (Week 3-4)

#### 3.1 Migration Guide for Each Client

##### MAX FlowStudio Migration
```javascript
// Before (OAuth 2.0)
const authUrl = `${AUTH_SERVER}/oauth/authorize?` +
    `response_type=code&` +
    `client_id=maxflowstudio&` +
    `redirect_uri=${REDIRECT_URI}&` +
    `scope=read:profile manage:workflows`;

// After (OIDC)
const authUrl = `${AUTH_SERVER}/oauth/authorize?` +
    `response_type=code&` +
    `client_id=maxflowstudio&` +
    `redirect_uri=${REDIRECT_URI}&` +
    `scope=openid profile email read:features manage:workflows&` +
    `nonce=${generateNonce()}`;

// Token handling
const tokenResponse = await exchangeCodeForToken(code);
if (tokenResponse.id_token) {
    // New OIDC flow
    const idTokenClaims = parseIdToken(tokenResponse.id_token);
    saveUserInfo(idTokenClaims);
} else {
    // Fallback to userinfo endpoint
    const userInfo = await fetchUserInfo(tokenResponse.access_token);
    saveUserInfo(userInfo);
}
```

#### 3.2 Client Migration Checklist
```markdown
## OIDC Migration Checklist

### Pre-Migration
- [ ] Review current OAuth implementation
- [ ] Update client libraries to support OIDC
- [ ] Implement nonce generation and validation
- [ ] Add ID token parsing capability
- [ ] Update token storage to handle ID tokens

### Migration Steps
- [ ] Add openid scope to authorization requests
- [ ] Implement ID token validation
- [ ] Update user info retrieval to use ID token claims
- [ ] Add discovery endpoint integration
- [ ] Implement JWKS key fetching and caching

### Post-Migration Testing
- [ ] Test backward compatibility with old tokens
- [ ] Verify ID token claims are correct
- [ ] Test token refresh flow
- [ ] Validate nonce handling
- [ ] Performance testing

### Rollback Plan
- [ ] Remove openid scope to revert to OAuth 2.0
- [ ] Keep userinfo endpoint as fallback
- [ ] Monitor for any authentication failures
```

### Phase 4: Progressive Enhancement (Week 5)

#### 4.1 Feature Flags for Gradual Rollout
```python
# backend/app/services/feature_flags.py

class OIDCFeatureFlags:
    """Feature flags for OIDC migration"""
    
    def __init__(self, db: Session):
        self.db = db
        self.cache = {}
    
    def is_oidc_enabled_for_client(self, client_id: str) -> bool:
        """Check if OIDC is enabled for specific client"""
        if client_id in self.cache:
            return self.cache[client_id]
        
        # Check database flag
        result = self.db.execute(
            text("""
                SELECT oidc_enabled 
                FROM oauth_clients 
                WHERE client_id = :client_id
            """),
            {"client_id": client_id}
        )
        
        enabled = result.scalar() or False
        self.cache[client_id] = enabled
        return enabled
    
    def get_migration_percentage(self) -> float:
        """Get percentage of clients migrated to OIDC"""
        result = self.db.execute(
            text("""
                SELECT 
                    COUNT(CASE WHEN oidc_enabled THEN 1 END)::float / 
                    COUNT(*)::float * 100 as percentage
                FROM oauth_clients
                WHERE is_active = true
            """)
        )
        
        return result.scalar() or 0.0
```

#### 4.2 A/B Testing Framework
```python
# Enable OIDC for specific percentage of requests
def should_use_oidc(client_id: str, user_id: str) -> bool:
    """Determine if request should use OIDC based on A/B testing"""
    
    # Always use OIDC if client explicitly requests it
    if "openid" in requested_scopes:
        return True
    
    # Check if client is in migration pilot
    if client_id in PILOT_CLIENTS:
        return True
    
    # Gradual rollout based on user ID hash
    if settings.oidc_migration_enabled:
        user_hash = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
        threshold = settings.oidc_rollout_percentage
        return (user_hash % 100) < threshold
    
    return False
```

### Phase 5: Monitoring and Validation (Week 6)

#### 5.1 Migration Metrics
```python
# backend/app/services/migration_metrics.py

class MigrationMetrics:
    """Track OIDC migration progress and health"""
    
    def track_token_issuance(
        self,
        client_id: str,
        token_type: str,  # 'oauth2' or 'oidc'
        success: bool,
        error: Optional[str] = None
    ):
        """Track token issuance metrics"""
        # Log to metrics system
        metrics.increment(
            'oauth.token.issued',
            tags={
                'client_id': client_id,
                'token_type': token_type,
                'success': success
            }
        )
    
    def get_migration_dashboard_data(self, db: Session) -> Dict:
        """Get migration statistics for monitoring dashboard"""
        return {
            "total_clients": self._get_total_clients(db),
            "migrated_clients": self._get_migrated_clients(db),
            "migration_percentage": self._get_migration_percentage(db),
            "token_stats": {
                "oauth2_tokens_24h": self._get_token_count(db, 'oauth2', 24),
                "oidc_tokens_24h": self._get_token_count(db, 'oidc', 24),
                "id_tokens_issued": self._get_id_token_count(db)
            },
            "error_rates": {
                "oauth2_errors": self._get_error_rate(db, 'oauth2'),
                "oidc_errors": self._get_error_rate(db, 'oidc')
            },
            "performance": {
                "avg_oauth2_response_time": self._get_avg_response_time(db, 'oauth2'),
                "avg_oidc_response_time": self._get_avg_response_time(db, 'oidc')
            }
        }
```

#### 5.2 Health Checks
```python
# backend/app/api/health.py

@router.get("/health/oidc")
def oidc_health_check(db: Session = Depends(get_db)):
    """OIDC system health check"""
    
    checks = {
        "jwks_available": False,
        "signing_key_active": False,
        "discovery_endpoint": False,
        "id_token_issuance": False,
        "backward_compatibility": False
    }
    
    try:
        # Check JWKS availability
        jwks = jwks_service.get_public_keys_jwks(db)
        checks["jwks_available"] = len(jwks.get("keys", [])) > 0
        
        # Check active signing key
        signing_key = jwks_service.get_active_signing_key(db)
        checks["signing_key_active"] = signing_key is not None
        
        # Check discovery endpoint
        response = requests.get(f"{settings.max_platform_api_url}/.well-known/openid-configuration")
        checks["discovery_endpoint"] = response.status_code == 200
        
        # Test ID token creation (dry run)
        if checks["signing_key_active"]:
            test_token = id_token_service.create_id_token(
                user=test_user,
                client_id="health-check",
                nonce=None,
                auth_time=datetime.utcnow(),
                scopes=["openid"],
                access_token=None,
                authorization_code=None,
                db=db
            )
            checks["id_token_issuance"] = test_token is not None
        
        # Check backward compatibility
        checks["backward_compatibility"] = settings.oidc_dual_mode
        
        # Overall health
        all_healthy = all(checks.values())
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "checks": checks,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
```

### Phase 6: Completion and Cleanup (Week 7-8)

#### 6.1 Migration Completion Criteria
```python
def check_migration_complete(db: Session) -> Dict[str, Any]:
    """Check if migration can be considered complete"""
    
    criteria = {
        "all_clients_capable": False,  # All clients can handle OIDC
        "adoption_threshold": False,   # >95% requests use OIDC
        "error_rate_acceptable": False, # <0.1% error rate
        "performance_maintained": False, # No performance degradation
        "grace_period_expired": False   # Grace period has passed
    }
    
    # Check all active clients have OIDC capability
    result = db.execute(
        text("""
            SELECT COUNT(*) as total,
                   COUNT(CASE WHEN oidc_enabled THEN 1 END) as oidc_enabled
            FROM oauth_clients
            WHERE is_active = true
        """)
    )
    counts = result.first()
    criteria["all_clients_capable"] = counts.total == counts.oidc_enabled
    
    # Check adoption rate
    oidc_percentage = get_oidc_request_percentage(db, days=7)
    criteria["adoption_threshold"] = oidc_percentage > 95.0
    
    # Check error rates
    error_rate = get_oidc_error_rate(db, days=7)
    criteria["error_rate_acceptable"] = error_rate < 0.1
    
    # Check performance
    perf_comparison = compare_oauth_oidc_performance(db, days=7)
    criteria["performance_maintained"] = perf_comparison["oidc_avg"] <= perf_comparison["oauth_avg"] * 1.1
    
    # Check grace period
    migration_start = get_migration_start_date(db)
    if migration_start:
        days_elapsed = (datetime.utcnow() - migration_start).days
        criteria["grace_period_expired"] = days_elapsed > settings.oidc_migration_grace_period_days
    
    return {
        "ready_for_completion": all(criteria.values()),
        "criteria": criteria,
        "recommendations": generate_completion_recommendations(criteria)
    }
```

#### 6.2 Final Migration Steps
```sql
-- Mark migration as complete
UPDATE oidc_migration_status
SET status = 'completed',
    completed_at = NOW()
WHERE client_id IN (
    SELECT client_id 
    FROM oauth_clients 
    WHERE oidc_enabled = true
);

-- Disable legacy HS256 support (optional)
UPDATE oauth_clients
SET id_token_signed_response_alg = 'RS256'
WHERE id_token_signed_response_alg = 'HS256';

-- Clean up migration flags
ALTER TABLE oauth_clients 
DROP COLUMN IF EXISTS oidc_migration_date;
```

## Rollback Strategy

### Immediate Rollback (Emergency)
```python
def emergency_rollback():
    """Immediately disable OIDC and revert to OAuth 2.0 only"""
    
    # Disable OIDC in configuration
    settings.oidc_migration_enabled = False
    settings.oidc_dual_mode = False
    
    # Update all clients to disable OIDC
    db.execute(
        text("UPDATE oauth_clients SET oidc_enabled = false")
    )
    
    # Log rollback event
    logger.critical("OIDC migration rolled back - emergency procedure executed")
    
    # Notify monitoring
    send_alert("OIDC Migration Rollback Executed", priority="high")
```

### Gradual Rollback
```python
def gradual_rollback(client_id: Optional[str] = None):
    """Gradually rollback OIDC for specific client or all clients"""
    
    if client_id:
        # Rollback specific client
        db.execute(
            text("""
                UPDATE oauth_clients 
                SET oidc_enabled = false,
                    oidc_migration_date = NULL
                WHERE client_id = :client_id
            """),
            {"client_id": client_id}
        )
        
        # Update migration status
        db.execute(
            text("""
                UPDATE oidc_migration_status
                SET status = 'rolled_back',
                    completed_at = NOW(),
                    notes = 'Client requested rollback'
                WHERE client_id = :client_id
            """),
            {"client_id": client_id}
        )
    else:
        # Gradual rollback for all clients
        # Reduce rollout percentage gradually
        current_percentage = settings.oidc_rollout_percentage
        new_percentage = max(0, current_percentage - 10)
        settings.oidc_rollout_percentage = new_percentage
        
        logger.info(f"OIDC rollout percentage reduced from {current_percentage}% to {new_percentage}%")
```

## Success Metrics

### Technical Metrics
- **Token Issuance Success Rate**: >99.9%
- **Average Response Time**: <100ms for ID token generation
- **JWKS Endpoint Availability**: >99.99%
- **Discovery Endpoint Availability**: >99.99%
- **Backward Compatibility**: 100% of OAuth 2.0 requests continue to work

### Business Metrics
- **Client Adoption Rate**: 100% of active clients migrated
- **User Impact**: Zero authentication failures due to migration
- **Support Tickets**: <5 migration-related issues per week
- **Performance**: No degradation in authentication speed

### Security Metrics
- **Nonce Validation Rate**: 100% for implicit/hybrid flows
- **Token Signature Verification**: 100% successful
- **Key Rotation Success**: 100% without service interruption
- **Security Scan Results**: Pass with no critical issues

## Timeline Summary

- **Week 1**: Infrastructure preparation
- **Week 2**: Dual-mode implementation
- **Week 3-4**: Client migration support
- **Week 5**: Progressive enhancement
- **Week 6**: Monitoring and validation
- **Week 7-8**: Completion and cleanup

Total migration time: 8 weeks with careful monitoring and rollback capabilities at each phase.