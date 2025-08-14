"""
OAuth 2.0 API Router for MAX Platform (Simplified)
Implements Authorization Code Flow with basic functionality
"""

from datetime import datetime, timedelta
import secrets
import hashlib
import base64
import time
from typing import Optional, List
from urllib.parse import urlparse, parse_qs
from jose import jwt, JWTError

from fastapi import APIRouter, Depends, HTTPException, Request, Query, Form
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, Field, HttpUrl

from ..database import get_db
from ..models import User, Group
from ..config import settings
from ..utils.auth import get_current_user_optional, get_current_user_silent, get_current_user_with_redis_session, verify_password, create_access_token
from ..utils.logging_config import get_oauth_logger, log_oauth_event, SecurityDataFilter
from ..services.user_switch_security_service import user_switch_security_service
from ..core.oauth_redis_integration import (
    get_oauth_session_from_request,
    validate_oauth_redis_session,
    create_oauth_redis_session,
    cleanup_oauth_redis_sessions,
    set_oauth_session_cookies,
    clear_oauth_session_cookies
)
from ..core.token_refresh_coordinator import get_token_refresh_coordinator
from ..core.redis_session import get_session_store

logger = get_oauth_logger()

router = APIRouter()


# Pydantic models
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    scope: str
    refresh_token: Optional[str] = None
    refresh_expires_in: Optional[int] = None
    id_token: Optional[str] = None  # OIDC ID token


class UserInfoResponse(BaseModel):
    sub: str  # User ID
    email: str
    name: str
    groups: List[str]
    is_admin: bool = False
    group_id: Optional[str] = None
    group_name: Optional[str] = None
    role_id: Optional[str] = None
    role_name: Optional[str] = None


# Helper functions
def generate_authorization_code() -> str:
    """Generate a secure random authorization code"""
    return secrets.token_urlsafe(32)


def check_client_oidc_status(client_id: str, db: Session) -> bool:
    """Check if client has OIDC enabled"""
    try:
        result = db.execute(
            text("SELECT oidc_enabled FROM oauth_clients WHERE client_id = :client_id"),
            {"client_id": client_id}
        )
        row = result.first()
        if row and row[0] is not None:
            return row[0]
        # Default to dual mode if column doesn't exist or is null
        return settings.oidc_dual_mode if hasattr(settings, 'oidc_dual_mode') else True
    except Exception as e:
        logger.debug(f"Could not check OIDC status for client {client_id}: {e}")
        # Default to dual mode on error
        return settings.oidc_dual_mode if hasattr(settings, 'oidc_dual_mode') else True


def generate_token_hash(token: str) -> str:
    """Generate SHA256 hash of token for storage"""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_refresh_token() -> str:
    """Generate a secure random refresh token (RFC 6749 compliant)"""
    return secrets.token_urlsafe(48)  # 48 bytes = 384 bits for extra security


def calculate_refresh_token_expiry() -> datetime:
    """Calculate refresh token expiration time"""
    # Default to 30 days for refresh tokens
    return datetime.utcnow() + timedelta(days=30)


def cleanup_expired_tokens(db: Session) -> int:
    """Clean up expired and revoked tokens"""
    try:
        # Clean up access tokens
        access_result = db.execute(
            text("""
                DELETE FROM oauth_access_tokens 
                WHERE expires_at < NOW() OR revoked_at IS NOT NULL
            """)
        )
        
        # Clean up refresh tokens
        refresh_result = db.execute(
            text("""
                DELETE FROM oauth_refresh_tokens 
                WHERE expires_at < NOW() OR revoked_at IS NOT NULL
            """)
        )
        
        total_deleted = access_result.rowcount + refresh_result.rowcount
        db.commit()
        
        if total_deleted > 0:
            logger.info(f"Cleaned up {total_deleted} expired/revoked tokens")
        
        return total_deleted
        
    except Exception as e:
        logger.error(f"Token cleanup error: {str(e)}")
        db.rollback()
        return 0


def verify_code_challenge(code_verifier: str, code_challenge: str, method: str = "S256") -> bool:
    """Verify PKCE code challenge"""
    if method == "plain":
        return code_verifier == code_challenge
    elif method == "S256":
        verifier_bytes = code_verifier.encode('ascii')
        challenge_bytes = hashlib.sha256(verifier_bytes).digest()
        generated_challenge = base64.urlsafe_b64encode(challenge_bytes).decode('ascii').rstrip('=')
        return generated_challenge == code_challenge
    return False


def create_refresh_token_record(
    user_id: str,
    client_id: str,
    scope: str,
    access_token_hash: str,
    request: Request,
    db: Session,
    session_id: str = None
) -> str:
    """Create and store a new refresh token"""
    refresh_token = generate_refresh_token()
    refresh_token_hash = generate_token_hash(refresh_token)
    expires_at = calculate_refresh_token_expiry()
    
    # Get client IP and user agent for security tracking
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")
    
    try:
        db.execute(
            text("""
                INSERT INTO oauth_refresh_tokens 
                (token_hash, client_id, user_id, scope, access_token_hash, 
                 expires_at, client_ip, user_agent, rotation_count, session_id)
                VALUES (:token_hash, :client_id, :user_id, :scope, :access_token_hash,
                        :expires_at, :client_ip, :user_agent, 0, :session_id)
            """),
            {
                "token_hash": refresh_token_hash,
                "client_id": client_id,
                "user_id": user_id,
                "scope": scope,
                "access_token_hash": access_token_hash,
                "expires_at": expires_at,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "session_id": session_id
            }
        )
        db.commit()
        
        # Log OAuth event with security filtering
        log_oauth_event(
            event_type="refresh_token_created",
            client_id=client_id,
            user_id=user_id,
            scope=scope,
            success=True,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        return refresh_token
        
    except Exception as e:
        error_msg = f"Failed to create refresh token: {str(e)}"
        
        # Log OAuth event failure
        log_oauth_event(
            event_type="refresh_token_created",
            client_id=client_id,
            user_id=user_id,
            scope=scope,
            success=False,
            error=error_msg,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create refresh token")


def validate_refresh_token(
    refresh_token: str,
    client_id: str,
    db: Session
) -> dict:
    """Validate refresh token and return token info (supports graceful rotation)"""
    refresh_token_hash = generate_token_hash(refresh_token)
    
    # Log validation attempt with security filtering
    log_oauth_event(
        event_type="refresh_token_validation",
        client_id=client_id,
        success=True  # Will be updated based on result
    )
    
    try:
        # First, clean up expired grace period tokens
        cleanup_count = db.execute(
            text("""
                UPDATE oauth_refresh_tokens 
                SET token_status = 'revoked', revoked_at = NOW()
                WHERE token_status = 'rotating' 
                AND rotation_grace_expires_at < NOW()
            """)
        ).rowcount
        
        if cleanup_count > 0:
            logger.info(f"Cleaned up {cleanup_count} expired grace period tokens")
        
        # Validate token (including 'rotating' tokens within grace period)
        result = db.execute(
            text("""
                SELECT * FROM oauth_refresh_tokens 
                WHERE token_hash = :token_hash 
                AND client_id = :client_id 
                AND revoked_at IS NULL 
                AND expires_at > NOW()
                AND (
                    token_status = 'active' 
                    OR (token_status = 'rotating' AND rotation_grace_expires_at > NOW())
                )
            """),
            {
                "token_hash": refresh_token_hash,
                "client_id": client_id
            }
        )
        token_record = result.first()
        
        if not token_record:
            error_msg = f"Refresh token not found or invalid for client_id: {client_id}"
            
            # Enhanced debugging for graceful rotation
            check_result = db.execute(
                text("""
                    SELECT token_status, revoked_at, expires_at, rotation_grace_expires_at, client_id 
                    FROM oauth_refresh_tokens 
                    WHERE token_hash = :token_hash
                """),
                {"token_hash": refresh_token_hash}
            )
            check_record = check_result.first()
            
            debug_info = {}
            if check_record:
                status, revoked_at, expires_at, grace_expires_at, found_client_id = check_record
                debug_info = {
                    "found_status": status,
                    "revoked_at": str(revoked_at) if revoked_at else None,
                    "expires_at": str(expires_at) if expires_at else None,
                    "grace_expires_at": str(grace_expires_at) if grace_expires_at else None,
                    "found_client_id": found_client_id,
                    "expected_client_id": client_id
                }
                
                if status == 'rotating' and grace_expires_at and grace_expires_at < datetime.utcnow():
                    error_msg += " - Token was in rotating status but grace period expired"
                elif status == 'revoked':
                    error_msg += " - Token has been revoked"
                elif found_client_id != client_id:
                    error_msg += f" - Client ID mismatch"
            else:
                error_msg += " - Token hash not found in database"
            
            # Log validation failure
            log_oauth_event(
                event_type="refresh_token_validation",
                client_id=client_id,
                success=False,
                error=error_msg
            )
            
            return None
            
        # Get the current column count to handle the new fields
        status = token_record[13] if len(token_record) > 13 else 'active'  # token_status
        parent_hash = token_record[14] if len(token_record) > 14 else None  # parent_token_hash
        grace_expires = token_record[15] if len(token_record) > 15 else None  # rotation_grace_expires_at
        
        # Log successful validation
        log_oauth_event(
            event_type="refresh_token_validation",
            client_id=client_id,
            user_id=str(token_record[3]),
            success=True
        )
        
        return {
            'id': token_record[0],
            'token_hash': token_record[1],
            'client_id': token_record[2],
            'user_id': token_record[3],
            'scope': token_record[4],
            'access_token_hash': token_record[5],
            'expires_at': token_record[6],
            'created_at': token_record[7],
            'revoked_at': token_record[8],
            'last_used_at': token_record[9],
            'client_ip': token_record[10],
            'user_agent': token_record[11],
            'rotation_count': token_record[12],
            'token_status': status,
            'parent_token_hash': parent_hash,
            'rotation_grace_expires_at': grace_expires
        }
        
    except Exception as e:
        logger.error(f"Refresh token validation error: {str(e)}")
        return None


def revoke_refresh_token(refresh_token_hash: str, db: Session) -> bool:
    """Revoke a refresh token"""
    try:
        result = db.execute(
            text("""
                UPDATE oauth_refresh_tokens 
                SET revoked_at = NOW() 
                WHERE token_hash = :token_hash
            """),
            {"token_hash": refresh_token_hash}
        )
        db.commit()
        return result.rowcount > 0
        
    except Exception as e:
        logger.error(f"Failed to revoke refresh token: {str(e)}")
        db.rollback()
        return False


def rotate_refresh_token(
    old_refresh_token_hash: str,
    user_id: str,
    client_id: str, 
    scope: str,
    request: Request,
    db: Session,
    session_id: str = None
) -> tuple[str, str]:
    """Rotate refresh token with graceful rotation (security best practice + reliability)"""
    try:
        logger.info(f"Starting graceful token rotation - old_hash: {old_refresh_token_hash[:10]}..., user_id: {user_id}, client_id: {client_id}")
        
        # Create new tokens
        new_refresh_token = generate_refresh_token()
        new_refresh_token_hash = generate_token_hash(new_refresh_token)
        
        logger.info(f"Generated new refresh token - new_hash: {new_refresh_token_hash[:10]}...")
        
        # Create new access token
        token_data = {"sub": str(user_id), "client_id": client_id, "scope": scope}
        new_access_token = create_access_token(data=token_data)
        new_access_token_hash = generate_token_hash(new_access_token)
        
        logger.info(f"Generated new access token for user_id: {user_id}")
        
        # Calculate expiry times
        expires_at = calculate_refresh_token_expiry()
        grace_expires_at = datetime.utcnow() + timedelta(seconds=10)  # 10-second grace period
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")
        
        # Step 1: Mark old token as 'rotating' with grace period (not immediately revoked)
        logger.info(f"Setting old token to 'rotating' status with grace period until {grace_expires_at}")
        db.execute(
            text("""
                UPDATE oauth_refresh_tokens 
                SET token_status = 'rotating',
                    rotation_grace_expires_at = :grace_expires_at,
                    last_used_at = NOW()
                WHERE token_hash = :old_token_hash
            """),
            {
                "grace_expires_at": grace_expires_at,
                "old_token_hash": old_refresh_token_hash
            }
        )
        
        # Step 2: Create new refresh token record (token family)
        logger.info(f"Creating new refresh token with parent relationship")
        db.execute(
            text("""
                INSERT INTO oauth_refresh_tokens 
                (token_hash, client_id, user_id, scope, access_token_hash, expires_at, 
                 client_ip, user_agent, rotation_count, parent_token_hash, token_status, session_id)
                SELECT :new_token_hash, client_id, user_id, scope, :new_access_token_hash, :expires_at,
                       :client_ip, :user_agent, rotation_count + 1, :old_token_hash, 'active', session_id
                FROM oauth_refresh_tokens 
                WHERE token_hash = :old_token_hash
            """),
            {
                "new_token_hash": new_refresh_token_hash,
                "new_access_token_hash": new_access_token_hash,
                "expires_at": expires_at,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "old_token_hash": old_refresh_token_hash
            }
        )
        
        # Step 3: Store new access token
        access_token_expires = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
        db.execute(
            text("""
                INSERT INTO oauth_access_tokens 
                (token_hash, client_id, user_id, scope, expires_at, refresh_token_hash, session_id)
                VALUES (:token_hash, :client_id, :user_id, :scope, :expires_at, :refresh_token_hash, :session_id)
            """),
            {
                "token_hash": new_access_token_hash,
                "client_id": client_id,
                "user_id": user_id,
                "scope": scope,
                "expires_at": access_token_expires,
                "refresh_token_hash": new_refresh_token_hash,
                "session_id": session_id
            }
        )
        
        # Step 4: Revoke old access token if exists
        db.execute(
            text("""
                UPDATE oauth_access_tokens 
                SET revoked_at = NOW() 
                WHERE refresh_token_hash = :old_token_hash
            """),
            {"old_token_hash": old_refresh_token_hash}
        )
        
        db.commit()
        logger.info(f"Graceful rotation completed - old token has {grace_expires_at} grace period")
        logger.info(f"Token family: {old_refresh_token_hash[:10]}... → {new_refresh_token_hash[:10]}...")
        
        return new_access_token, new_refresh_token
        
    except Exception as e:
        logger.error(f"Failed to rotate refresh token: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to rotate tokens")


def validate_client_for_refresh_token(
    client_id: str,
    client_secret: Optional[str],
    db: Session
) -> dict:
    """Validate OAuth client for refresh token grant (no redirect_uri needed)"""
    try:
        logger.info(f"Looking up client in database: {client_id}")
        # Get client from database
        result = db.execute(
            text("SELECT * FROM oauth_clients WHERE client_id = :client_id AND is_active = true"),
            {"client_id": client_id}
        )
        client = result.first()
        
        if not client:
            logger.error(f"Client not found in database: {client_id}")
            raise HTTPException(status_code=401, detail="Invalid client_id")
        
        logger.info(f"Client found in database: {client_id}")
        
        # Convert to dict for easier access
        client_dict = {
            'id': client[0],
            'client_id': client[1], 
            'client_secret': client[2],
            'client_name': client[3],
            'description': client[4],
            'redirect_uris': client[5],
            'allowed_scopes': client[6],
            'is_confidential': client[7],
            'is_active': client[8],
            'logo_url': client[9],
            'homepage_url': client[10],
            'created_at': client[11],
            'updated_at': client[12]
        }
        
        logger.info(f"Client is_confidential: {client_dict['is_confidential']}, has_client_secret: {client_secret is not None}")
        
        # For confidential clients, validate client secret
        if client_dict['is_confidential'] and client_secret != client_dict['client_secret']:
            logger.error(f"Client secret mismatch for confidential client: {client_id}")
            raise HTTPException(status_code=401, detail="Invalid client_secret")
        
        logger.info(f"Client validation completed successfully: {client_id}")
        return client_dict
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Client validation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Client validation failed")


def validate_client(
    client_id: str,
    client_secret: Optional[str],
    redirect_uri: str,
    db: Session
) -> dict:
    """Validate OAuth client credentials and redirect URI"""
    try:
        # Get client from database
        result = db.execute(
            text("SELECT * FROM oauth_clients WHERE client_id = :client_id AND is_active = true"),
            {"client_id": client_id}
        )
        client = result.first()
        
        if not client:
            raise HTTPException(status_code=400, detail="Invalid client_id")
        
        # Convert to dict for easier access
        client_dict = {
            'id': client[0],
            'client_id': client[1], 
            'client_secret': client[2],
            'client_name': client[3],
            'description': client[4],
            'redirect_uris': client[5],
            'allowed_scopes': client[6],
            'is_confidential': client[7],
            'is_active': client[8],
            'logo_url': client[9],
            'homepage_url': client[10],
            'created_at': client[11],
            'updated_at': client[12]
        }
        
        # Check redirect URI (OAuth 표준에 따라 쿼리 파라미터가 포함된 URI도 허용)
        from urllib.parse import urlparse
        
        redirect_base_uri = urlparse(redirect_uri)._replace(query='', fragment='').geturl()
        registered_uris = [urlparse(uri)._replace(query='', fragment='').geturl() for uri in client_dict['redirect_uris']]
        
        if redirect_base_uri not in registered_uris:
            logger.warning(f"Redirect URI validation failed - Requested: {redirect_uri}, Registered: {client_dict['redirect_uris']}")
            raise HTTPException(status_code=400, detail="Invalid redirect_uri")
        
        # For confidential clients, verify secret (only if secret is provided)
        if client_dict['is_confidential'] and client_secret is not None and client_secret != client_dict['client_secret']:
            raise HTTPException(status_code=401, detail="Invalid client_secret")
        
        return client_dict
        
    except Exception as e:
        logger.error(f"Client validation error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Client validation failed: {str(e)}")


def create_authorization_code_record(
    client_id: str,
    user_id: str,
    redirect_uri: str,
    scope: str,
    code_challenge: Optional[str],
    code_challenge_method: Optional[str],
    db: Session,
    nonce: Optional[str] = None,
    auth_time: Optional[datetime] = None
) -> str:
    """Create authorization code record in database"""
    try:
        code = generate_authorization_code()
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        
        db.execute(
            text("""
                INSERT INTO authorization_codes 
                (code, client_id, user_id, redirect_uri, scope, code_challenge, 
                 code_challenge_method, expires_at, nonce, auth_time)
                VALUES (:code, :client_id, :user_id, :redirect_uri, :scope, 
                        :code_challenge, :code_challenge_method, :expires_at, :nonce, :auth_time)
            """),
            {
                "code": code,
                "client_id": client_id,
                "user_id": user_id,
                "redirect_uri": redirect_uri,
                "scope": scope,
                "code_challenge": code_challenge,
                "code_challenge_method": code_challenge_method,
                "expires_at": expires_at,
                "nonce": nonce,
                "auth_time": auth_time or datetime.utcnow()
            }
        )
        db.commit()
        
        return code
        
    except Exception as e:
        logger.error(f"Authorization code creation error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create authorization code")


def log_oauth_action(
    action: str,
    client_id: Optional[str],
    user_id: Optional[str],
    success: bool,
    error_code: Optional[str] = None,
    error_description: Optional[str] = None,
    request: Optional[Request] = None,
    db: Session = None
):
    """Log OAuth actions for audit trail with separate transaction"""
    if not db:
        return
    
    try:
        ip_address = None
        user_agent = None
        
        if request:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("User-Agent")
        
        # Use a separate transaction for audit logging
        db.execute(text("BEGIN"))
        
        db.execute(
            text("""
                INSERT INTO oauth_audit_logs 
                (action, client_id, user_id, ip_address, user_agent, success, 
                 error_code, error_description)
                VALUES (:action, :client_id, :user_id, :ip_address, :user_agent, 
                        :success, :error_code, :error_description)
            """),
            {
                "action": action,
                "client_id": client_id,
                "user_id": user_id,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "success": success,
                "error_code": error_code,
                "error_description": error_description
            }
        )
        
        db.execute(text("COMMIT"))
        
    except Exception as e:
        logger.error(f"Audit log error: {str(e)}")
        try:
            db.execute(text("ROLLBACK"))
        except:
            pass
        # Don't fail the main operation due to logging issues




# OIDC Discovery Document
@router.get("/.well-known/openid-configuration")
def get_openid_configuration(request: Request):
    """
    OpenID Connect Discovery Document
    Returns metadata about the OpenID Provider's configuration
    """
    base_url = str(request.base_url).rstrip('/')
    
    return {
        "issuer": settings.oidc_issuer,
        "authorization_endpoint": f"{base_url}/api/oauth/authorize",
        "token_endpoint": f"{base_url}/api/oauth/token",
        "userinfo_endpoint": f"{base_url}/api/oauth/userinfo",
        "jwks_uri": f"{base_url}/api/oauth/.well-known/jwks.json",
        "end_session_endpoint": f"{base_url}/api/oauth/logout",  # RP-Initiated Logout
        "revocation_endpoint": f"{base_url}/api/oauth/revoke",
        "introspection_endpoint": f"{base_url}/api/oauth/introspect",
        
        # Supported features
        "response_types_supported": ["code", "code id_token"],
        "response_modes_supported": ["query", "fragment"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["RS256", "HS256"],
        "scopes_supported": [
            "openid", "profile", "email", "phone", "address", "offline_access",
            "read:profile", "read:groups", "manage:workflows"
        ],
        "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"],
        "claims_supported": settings.oidc_supported_claims,
        "code_challenge_methods_supported": ["S256", "plain"],
        
        # Additional OIDC features
        "request_parameter_supported": False,
        "request_uri_parameter_supported": False,
        "require_request_uri_registration": False,
        "claims_parameter_supported": False,
        
        # Service documentation
        "service_documentation": f"{base_url}/docs",
        "ui_locales_supported": ["ko-KR", "en-US"],
        
        # Token configuration
        "access_token_expires_in": settings.access_token_expire_minutes * 60,
        "refresh_token_expires_in": settings.refresh_token_expire_days * 86400,
        "id_token_expires_in": settings.oidc_id_token_expire_minutes * 60,
    }


# OAuth endpoints
@router.get("/authorize")
async def authorize(
    response_type: str = Query(...),
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    state: Optional[str] = Query(None),
    scope: Optional[str] = Query("read:profile"),
    code_challenge: Optional[str] = Query(None),
    code_challenge_method: Optional[str] = Query(None),
    display: Optional[str] = Query(None),  # popup 모드 감지용
    prompt: Optional[str] = Query(None),   # OpenID Connect prompt 파라미터
    # OIDC-specific parameters
    nonce: Optional[str] = Query(None),    # OIDC nonce for replay attack prevention
    max_age: Optional[int] = Query(None),  # Maximum authentication age
    id_token_hint: Optional[str] = Query(None),  # Previously issued ID token
    login_hint: Optional[str] = Query(None),     # Hint about user's login identifier
    acr_values: Optional[str] = Query(None),     # Authentication context class reference
    request: Request = None,
    current_user: Optional[User] = Depends(get_current_user_with_redis_session),
    db: Session = Depends(get_db)
):
    """
    OAuth 2.0 Authorization Endpoint
    Initiates the authorization code flow
    """
    try:
        # 무한루프 감지를 위한 로깅
        logger.info(f"OAuth authorize request: client_id={client_id}, display={display}, prompt={prompt}, redirect_uri={redirect_uri}")
        
        # 🔍 DEBUG: Check authentication status with worker info
        import os
        worker_id = os.getpid()
        logger.info(f"🔍 Worker {worker_id}: Current user authentication status: {current_user is not None}")
        if current_user:
            logger.info(f"🔍 Worker {worker_id}: Authenticated user: {current_user.email}")
        
        # 🔒 TOKEN BLACKLIST VALIDATION: Check if current Bearer token is blacklisted
        if current_user:
            try:
                from ..services.token_blacklist import get_token_blacklist
                
                authorization_header = request.headers.get("Authorization")
                blacklist_service = get_token_blacklist()
                
                if blacklist_service and authorization_header:
                    # Extract token from Bearer header
                    token = authorization_header
                    if token.startswith("Bearer "):
                        token = token[7:]
                    
                    if blacklist_service.is_token_blacklisted(token):
                        logger.warning(f"🚫 Worker {worker_id}: Blacklisted token detected for user {current_user.email}")
                        logger.warning(f"🚫 Worker {worker_id}: Token invalidated due to previous prompt=login")
                        
                        # Force re-authentication by clearing current user
                        current_user = None
                        prompt = "login"  # Force fresh login
                        
                        logger.warning(f"🚫 Worker {worker_id}: Forced re-authentication due to blacklisted token")
                
            except Exception as e:
                logger.error(f"❌ Worker {worker_id}: Error checking token blacklist: {e}")
                # Continue with normal flow - don't block due to blacklist check errors
        
        # 🔍 DEBUG: Check cookies
        cookies = request.cookies
        logger.info(f"🔍 Worker {worker_id}: Request cookies: {list(cookies.keys())}")
        if 'access_token' in cookies:
            logger.info(f"🔍 Worker {worker_id}: Access token cookie found: {cookies['access_token'][:20]}...")
        else:
            logger.info(f"🔍 Worker {worker_id}: No access_token cookie found")
        
        # 🔍 DEBUG: Check all cookie details
        for cookie_name, cookie_value in cookies.items():
            logger.info(f"🔍 Worker {worker_id}: Cookie '{cookie_name}': {cookie_value[:50]}...")
        
        # 🔍 DEBUG: Check headers
        auth_header = request.headers.get('Authorization')
        logger.info(f"🔍 Worker {worker_id}: Authorization header: {auth_header[:30] if auth_header else 'None'}")
        
        # 🔍 DEBUG: Check frontend URL setting
        logger.info(f"🔍 Worker {worker_id}: MAX_PLATFORM_FRONTEND_URL: {settings.max_platform_frontend_url}")
        
        # 🔥 PERFECT SOLUTION: MaxLab popup에서 강제 로그인 요구
        # "다른 사용자로 로그인" 버튼 클릭 시 무조건 로그인 창 표시
        if display == "popup" and current_user and client_id == "maxlab":
            logger.warning(f"🔥 Worker {worker_id}: MaxLab popup OAuth request - FORCING FRESH LOGIN (no auto-auth)")
            prompt = "login"  # select_account가 아닌 login으로 강제 로그인
            
        # 🔍 추가 보안: 다른 클라이언트에서 인증된 사용자가 또 다른 클라이언트로 요청
        try:
            from ..core.redis_session import get_session_store
            session_store = get_session_store()
            if session_store and current_user:
                # 현재 사용자의 모든 활성 세션에서 클라이언트 확인
                user_sessions_key = f"maxplatform_session_user:{current_user.id}"
                existing_sessions = session_store.redis_client.smembers(user_sessions_key)
                
                different_client_found = False
                for session_id in existing_sessions:
                    session_data = session_store.get_session(session_id)
                    if session_data and session_data.get('oauth_client_id'):
                        existing_client = session_data.get('oauth_client_id')
                        if existing_client != client_id:
                            different_client_found = True
                            logger.warning(f"🔄 Worker {worker_id}: User has active session with different client ({existing_client}) - forcing select_account")
                            break
                
                if different_client_found:
                    prompt = "select_account"
        except Exception as e:
            logger.debug(f"Client switching detection failed: {e}")
            
        # 🔍 Referrer 기반 감지
        referrer = request.headers.get("referer", "")
        if current_user and "maxlab.dwchem.co.kr" in referrer and "/login" in referrer:
            logger.warning(f"🔥 Worker {worker_id}: Request from maxlab login page - FORCING FRESH LOGIN")
            prompt = "login"  # 무조건 로그인 창 표시
        
        # Validate request
        if response_type != "code":
            raise HTTPException(status_code=400, detail="Unsupported response_type")
        
        # Validate client and redirect URI
        client = validate_client(client_id, None, redirect_uri, db)
        
        # 🔴 CRITICAL SECURITY: 최종 prompt 강제 검증
        final_prompt_decision = prompt
        if current_user:
            # 모든 인증된 요청에 대해 보안 정책 적용
            security_reasons = []
            
            # 이유 1: MaxLab 클라이언트의 popup 요청
            if client_id == "maxlab" and display == "popup":
                security_reasons.append("maxlab_popup_request")
            
            # 이유 2: 인증된 사용자에게 prompt 파라미터 없음
            if not prompt:
                security_reasons.append("no_prompt_with_authenticated_user")
            
            # 이유 3: 다른 도메인에서 온 popup 요청
            if display == "popup" and referrer and "maxlab.dwchem.co.kr" in referrer:
                security_reasons.append("cross_domain_popup_request")
            
            # 🔥 PERFECT SOLUTION: popup 요청에 강제 로그인 적용 (자동인증 완전 차단)
            if security_reasons:
                final_prompt_decision = "login"  # select_account가 아닌 login으로 변경
                logger.critical(f"🔥 Worker {worker_id}: PERFECT SECURITY POLICY APPLIED")
                logger.critical(f"🔥 Worker {worker_id}: User: {current_user.email}, Client: {client_id}")
                logger.critical(f"🔥 Worker {worker_id}: Reasons: {', '.join(security_reasons)}")
                logger.critical(f"🔥 Worker {worker_id}: Forcing prompt=login (FRESH LOGIN REQUIRED)")
        
        # 최종 prompt 적용
        prompt = final_prompt_decision
        logger.info(f"🔄 Worker {worker_id}: Final prompt decision: {prompt}")
        
        # 🔄 Redis Session Validation: Check if current authentication is backed by valid Redis session
        if current_user:
            try:
                redis_session = get_oauth_session_from_request(request)
                
                if redis_session:
                    # Validate that Redis session matches current user
                    session_client_id = redis_session.get('oauth_client_id')
                    session_user_id = redis_session.get('user_id')
                    
                    # Check user_id match first (critical security check)
                    if str(session_user_id) != str(current_user.id):
                        logger.warning(f"🚨 Worker {worker_id}: Redis session user mismatch - session: {session_user_id} vs current: {current_user.id}")
                        current_user = None  # Force re-authentication for security
                    # Handle client_id validation with support for standard login sessions
                    elif session_client_id is not None and session_client_id != client_id:
                        logger.warning(f"🚨 Worker {worker_id}: Redis session client mismatch - session: {session_client_id} vs current: {client_id}")
                        current_user = None  # Force re-authentication
                    else:
                        # Session is valid - handle standard login sessions (client_id = None)
                        if session_client_id is None:
                            logger.info(f"🔄 Worker {worker_id}: Upgrading standard login session to OAuth session for client {client_id}")
                            # Update Redis session with OAuth client context
                            try:
                                from ..core.redis_session import update_user_session
                                update_user_session(redis_session.get('session_id'), {
                                    'oauth_client_id': client_id,
                                    'oauth_upgrade_time': datetime.utcnow().isoformat()
                                })
                                logger.info(f"✅ Worker {worker_id}: Standard login session upgraded for OAuth client {client_id}")
                            except Exception as upgrade_error:
                                logger.warning(f"⚠️ Worker {worker_id}: Failed to upgrade session: {upgrade_error} - proceeding anyway")
                        else:
                            logger.info(f"✅ Worker {worker_id}: Redis session validated for user {current_user.email} and client {client_id}")
                else:
                    # Redis 세션이 없어도 JWT가 유효하면 진행하되, Redis 세션 생성 시도
                    logger.warning(f"⚠️ Worker {worker_id}: User authenticated but no Redis session found - attempting to create one")
                    try:
                        from ..core.redis_session import create_user_session
                        
                        # 현재 토큰으로 Redis 세션 생성 시도
                        access_token = request.cookies.get('access_token')
                        if access_token:
                            # JWT 토큰에서 만료 시간 추출
                            payload = jwt.decode(access_token, settings.secret_key, algorithms=[settings.algorithm], options={"verify_exp": False})
                            exp_timestamp = payload.get("exp", 0)
                            
                            session_data = {
                                "id": str(current_user.id),
                                "email": current_user.email,
                                "name": current_user.real_name or current_user.display_name or current_user.email,
                                "is_admin": current_user.is_admin,
                                "is_active": current_user.is_active,
                                "groups": [{"id": str(current_user.group.id), "name": current_user.group.name}] if current_user.group else [],
                                "roles": [{"id": str(current_user.role.id), "name": current_user.role.name}] if current_user.role else [],
                                "created_at": datetime.utcnow().isoformat(),
                                "token": access_token,
                                "token_exp": exp_timestamp,
                                "source": "oauth_recovery"
                            }
                            
                            # TTL 계산
                            ttl = exp_timestamp - int(time.time()) if exp_timestamp > 0 else 1800
                            
                            if ttl > 0:
                                session_id = create_user_session(session_data)
                                if session_id:
                                    logger.info(f"✅ Worker {worker_id}: Created Redis session {session_id} for user {current_user.email}")
                                else:
                                    logger.warning(f"⚠️ Worker {worker_id}: Failed to create Redis session, continuing with JWT only")
                            else:
                                logger.warning(f"⚠️ Worker {worker_id}: Token expired, cannot create Redis session")
                    except Exception as e:
                        logger.error(f"❌ Worker {worker_id}: Error creating Redis session: {e}")
                        # Continue with JWT authentication even if Redis session creation fails
                    
            except Exception as e:
                logger.error(f"❌ Worker {worker_id}: Redis session validation failed: {e}")
                # Don't force re-auth on Redis errors - gracefully degrade
                logger.info(f"🔄 Worker {worker_id}: Continuing without Redis session validation due to error")
        
        # 🎯 OVERRIDE CLIENT PROMPT: 통합 SSO에서는 클라이언트가 보낸 prompt를 오버라이드
        # 클라이언트가 prompt=login을 보내도 통합 SSO 상황에서는 무시
        
        # 특별한 파라미터로 다른 사용자로 로그인 의도 감지
        force_account_selection = request.query_params.get("force_account_selection") == "true"
        switch_user_intent = request.query_params.get("switch_user") == "true"
        
        # 🔥 사용자 전환 감지: login_hint가 현재 사용자와 다른 경우 강제 로그인
        different_user_requested = False
        if current_user and login_hint:
            # login_hint가 이메일 형식인지 확인
            if "@" in login_hint and login_hint != current_user.email:
                logger.warning(f"🔥 Worker {worker_id}: Different user login attempt detected - current: {current_user.email}, requested: {login_hint}")
                different_user_requested = True
        
        # 🔥 **NEW**: 백업 감지 메커니즘 - 프론트엔드 파라미터 없이도 "다른 사용자로 로그인" 감지
        popup_user_switch_detected = False
        if (current_user and 
            display == "popup" and 
            not prompt and  # 프론트엔드가 prompt 파라미터를 보내지 않음
            not force_account_selection and 
            not switch_user_intent and
            not different_user_requested):
            # 팝업 + 인증된 사용자 + prompt 없음 = "다른 사용자로 로그인" 시나리오 가능성
            logger.warning(f"🔥 Worker {worker_id}: POPUP USER SWITCH DETECTED - authenticated user in popup without prompt parameter")
            logger.warning(f"🔥 Worker {worker_id}: This likely indicates '다른 사용자로 로그인' button click without frontend parameters")
            popup_user_switch_detected = True
        
        # 🔥 사용자 전환 의도가 명확한 경우만 강제 로그인
        user_switch_intent = force_account_selection or switch_user_intent or different_user_requested or popup_user_switch_detected
        
        if current_user and user_switch_intent:
            # 명확한 사용자 전환 의도가 있는 경우만 강제 로그인
            logger.warning(f"🔥 Worker {worker_id}: User switch intent detected - FORCING FRESH LOGIN")
            logger.info(f"🔥 Worker {worker_id}: force_account_selection={force_account_selection}, switch_user={switch_user_intent}, different_user={different_user_requested}, popup_switch={popup_user_switch_detected}")
            prompt = "login"  # 무조건 로그인 창 표시
        
        # Check if user is authenticated
        if not current_user:
            # prompt=none 처리: OpenID Connect 표준에 따라 login_required 에러 반환
            if prompt == "none":
                log_oauth_action(
                    "authorize", client_id, None, False, 
                    "login_required", "prompt=none but user not authenticated",
                    request, db
                )
                
                # OpenID Connect 표준 에러 응답
                error_url = f"{redirect_uri}?error=login_required"
                if state:
                    error_url += f"&state={state}"
                error_url += "&error_description=User+not+logged+in"
                
                logger.info(f"prompt=none login_required: redirecting to {error_url}")
                return RedirectResponse(url=error_url)
            
            # 팝업 모드 처리: 로그인 페이지로 리다이렉트 (표준 OAuth 방식)
            if display == "popup":
                log_oauth_action(
                    "authorize", client_id, None, False, 
                    "login_required", "User not authenticated - redirecting to login",
                    request, db
                )
                
                # OAuth 파라미터를 보존하여 로그인 페이지로 리다이렉트
                from urllib.parse import quote
                import json
                
                oauth_params = {
                    "response_type": response_type,
                    "client_id": client_id,
                    "redirect_uri": redirect_uri,
                    "scope": scope,
                    "state": state,
                    "code_challenge": code_challenge,
                    "code_challenge_method": code_challenge_method,
                    "display": display,
                    "prompt": prompt,
                    "nonce": nonce,
                    "max_age": max_age,
                    "id_token_hint": id_token_hint,
                    "login_hint": login_hint,
                    "acr_values": acr_values
                }
                
                # Remove None values
                oauth_params = {k: v for k, v in oauth_params.items() if v is not None}
                oauth_params_encoded = quote(json.dumps(oauth_params))
                
                # 팝업 모드에서도 로그인 페이지로 리다이렉트
                login_url = f"{settings.max_platform_frontend_url}/login?oauth_return={oauth_params_encoded}"
                return RedirectResponse(url=login_url)
            
            # 일반 모드: 기존 로직 유지
            # Encode OAuth parameters for return after login
            from urllib.parse import quote
            import json
            
            oauth_params = {
                "response_type": response_type,
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scope": scope,
                "state": state,
                "code_challenge": code_challenge,
                "code_challenge_method": code_challenge_method,
                "display": display,
                "prompt": prompt,
                "nonce": nonce,
                "max_age": max_age,
                "id_token_hint": id_token_hint,
                "login_hint": login_hint,
                "acr_values": acr_values
            }
            
            # Remove None values
            oauth_params = {k: v for k, v in oauth_params.items() if v is not None}
            oauth_params_encoded = quote(json.dumps(oauth_params))
            
            # Redirect to login page with return URL
            login_url = f"{settings.max_platform_frontend_url}/login?oauth_return={oauth_params_encoded}"
            
            log_oauth_action(
                "authorize", client_id, None, False, 
                "login_required", "User not authenticated - redirecting to login",
                request, db
            )
            
            return RedirectResponse(url=login_url)
        
        # prompt=login 처리: 강제로 재인증 요구
        if prompt == "login":
            logger.info(f"prompt=login: forcing re-authentication for client {client_id}")
            
            # 🔥 CRITICAL FIX: 현재 사용자의 모든 세션을 완전히 무효화하여 무한 루프 방지
            if current_user:
                logger.warning(f"🔥 Worker {worker_id}: COMPLETE SESSION INVALIDATION for prompt=login - user: {current_user.email}")
                
                # 🔧 RACE CONDITION FIX: Wait for OAuth sync requests to complete before session invalidation
                try:
                    from ..services.oauth_request_coordinator import get_oauth_coordinator
                    
                    coordinator = get_oauth_coordinator()
                    user_id = str(current_user.id)
                    
                    # Check if there are active OAuth sync requests
                    active_requests = coordinator.get_active_oauth_sync_requests(user_id)
                    if active_requests:
                        logger.info(f"⏳ Worker {worker_id}: Waiting for {len(active_requests)} OAuth sync requests before session invalidation")
                        
                        # Wait for OAuth sync completion with 8 second timeout
                        wait_result = await coordinator.wait_for_oauth_sync_completion(user_id, max_wait_seconds=8)
                        
                        if wait_result["completed"]:
                            logger.info(f"✅ Worker {worker_id}: OAuth sync completed in {wait_result['elapsed_time']:.2f}s, proceeding with session invalidation")
                        else:
                            logger.warning(f"⚠️ Worker {worker_id}: OAuth sync timeout after {wait_result['elapsed_time']:.2f}s, {wait_result.get('remaining_requests', 0)} requests still active")
                            logger.warning(f"⚠️ Worker {worker_id}: Proceeding with session invalidation despite pending OAuth requests")
                    
                except Exception as e:
                    logger.error(f"❌ Worker {worker_id}: Failed to coordinate OAuth sync wait: {e}")
                    logger.info(f"🔥 Worker {worker_id}: Proceeding with session invalidation despite coordination error")
                
                # 1. 현재 access token을 블랙리스트에 추가 (무한 루프 방지)
                try:
                    from ..services.token_blacklist import get_token_blacklist
                    
                    # Extract and blacklist the current Bearer token
                    authorization_header = request.headers.get("Authorization")
                    blacklist_service = get_token_blacklist()
                    
                    if blacklist_service and authorization_header:
                        blacklisted_count = blacklist_service.blacklist_user_tokens_by_bearer_token(
                            current_bearer_token=authorization_header,
                            user_id=str(current_user.id),
                            reason="prompt_login_invalidation",
                            ip_address=request.client.host if request.client else None,
                            user_agent=request.headers.get("User-Agent")
                        )
                        logger.warning(f"🔒 Worker {worker_id}: Blacklisted {blacklisted_count} tokens for user {current_user.email} due to prompt=login")
                    else:
                        logger.warning(f"⚠️ Worker {worker_id}: Token blacklist service not available or no Authorization header")
                    
                    from ..core.redis_session import delete_all_user_sessions
                    
                    # 현재 사용자의 모든 Redis 세션 삭제
                    deleted_sessions = delete_all_user_sessions(str(current_user.id))
                    logger.warning(f"🔥 Worker {worker_id}: Deleted {deleted_sessions} Redis sessions for user {current_user.email}")
                    
                except Exception as e:
                    logger.error(f"❌ Worker {worker_id}: Failed to delete Redis sessions or blacklist tokens: {e}")
                
                # 2. 보안 정리 수행 (OAuth 토큰 정리)
                cleanup_result = user_switch_security_service.force_previous_user_cleanup(
                    client_id=client_id,
                    previous_user_id=str(current_user.id),
                    new_user_id=None,  # None instead of "pending" to avoid UUID type error
                    reason="prompt_login_complete_invalidation",
                    db=db
                )
                
                logger.info(f"🔒 Security cleanup for prompt=login: {cleanup_result}")
            
            # OAuth 파라미터 준비
            oauth_params = {
                "response_type": response_type,
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scope": scope,
                "state": state,
                "code_challenge": code_challenge,
                "code_challenge_method": code_challenge_method,
                "display": display,
                "prompt": prompt,
                "nonce": nonce,
                "max_age": max_age,
                "id_token_hint": id_token_hint,
                "login_hint": login_hint,
                "acr_values": acr_values
            }
            
            # None 값 제거
            oauth_params = {k: v for k, v in oauth_params.items() if v is not None}
            
            # OAuth 파라미터 인코딩
            from urllib.parse import quote
            import json
            oauth_params_encoded = quote(json.dumps(oauth_params))
            
            # 로그인 페이지로 리다이렉트 (force_login 파라미터 추가)
            login_url = f"{settings.max_platform_frontend_url}/login?oauth_return={oauth_params_encoded}&force_login=true"
            
            logger.info(f"Redirecting to login page with force_login=true: {login_url}")
            
            log_oauth_action(
                "authorize", client_id, str(current_user.id) if current_user else None, 
                False, "prompt_login", "Force re-authentication requested",
                request, db
            )
            
            # 🔥 CRITICAL: 모든 인증 관련 쿠키 완전 삭제 (무한 루프 방지)
            response = RedirectResponse(url=login_url)
            
            # 모든 인증 관련 쿠키 목록 (포괄적 삭제)
            auth_cookies = [
                "session_token", "session_id", "access_token", "refresh_token", 
                "user_id", "oauth_session", "auth_token", "_session", "jwt_token"
            ]
            
            logger.warning(f"🔥 Worker {worker_id}: Deleting ALL authentication cookies for complete invalidation")
            
            for cookie_name in auth_cookies:
                try:
                    # 1. 도메인 없이 삭제 (현재 도메인)
                    response.delete_cookie(cookie_name, path="/")
                    
                    # 2. .dwchem.co.kr 도메인으로 삭제 (크로스 도메인)
                    response.delete_cookie(cookie_name, domain=".dwchem.co.kr", path="/")
                    
                    # 3. max.dwchem.co.kr 도메인으로 삭제 (명시적)
                    response.delete_cookie(cookie_name, domain="max.dwchem.co.kr", path="/")
                    
                    # 4. localhost 도메인으로 삭제 (개발 환경)
                    response.delete_cookie(cookie_name, domain="localhost", path="/")
                    
                    # 5. Secure, SameSite 옵션으로도 삭제 시도
                    response.delete_cookie(cookie_name, domain=".dwchem.co.kr", path="/", 
                                         secure=not settings.debug, samesite="lax")
                                         
                except Exception as e:
                    logger.debug(f"Cookie deletion failed for {cookie_name}: {e}")
            
            logger.warning(f"🔥 Worker {worker_id}: Complete session invalidation completed - redirecting to fresh login")
            return response
        
        # prompt=select_account 처리: 계정 선택 화면 표시 (다른 사용자로 로그인)
        if prompt == "select_account" or max_age == 0:
            logger.info(f"prompt=select_account or max_age=0: forcing account selection for client {client_id}")
            
            # 현재 사용자의 세션을 무효화 (보안 정리) - 모든 플로우에서 실행
            if current_user:
                cleanup_result = user_switch_security_service.force_previous_user_cleanup(
                    client_id=client_id,
                    previous_user_id=str(current_user.id),
                    new_user_id=None,  # None instead of "pending" to avoid UUID type error
                    reason="select_account",
                    db=db
                )
                
                logger.info(f"🔒 Security cleanup for select_account: {cleanup_result}")
            
            # 모든 플로우에서 로그인 페이지로 리다이렉트 (force_login 파라미터 추가)
            oauth_params = {
                "response_type": response_type,
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scope": scope,
                "state": state,
                "code_challenge": code_challenge,
                "code_challenge_method": code_challenge_method,
                "display": display,
                "prompt": "select_account",
                "nonce": nonce,
                "max_age": max_age,
                "id_token_hint": id_token_hint,
                "login_hint": login_hint,
                "acr_values": acr_values
            }
            
            oauth_params = {k: v for k, v in oauth_params.items() if v is not None}
            from urllib.parse import quote
            import json
            oauth_params_encoded = quote(json.dumps(oauth_params))
            
            # force_login=true와 함께 로그인 페이지로 이동하여 현재 세션 무시하고 재로그인
            login_url = f"{settings.max_platform_frontend_url}/login?oauth_return={oauth_params_encoded}&force_login=true"
            logger.info(f"Redirecting to account selection with force_login: {login_url}")
            
            # 세션 쿠키 삭제 (계정 선택 강제, 크로스 도메인 완전 삭제)
            response = RedirectResponse(url=login_url)
            for cookie_name in ["session_token", "session_id", "access_token", "user_id", "oauth_session"]:
                # 도메인 없이 삭제
                response.delete_cookie(cookie_name)
                # .dwchem.co.kr 도메인으로 삭제 (크로스 도메인 쿠키)
                response.delete_cookie(cookie_name, domain=".dwchem.co.kr")
                # 현재 도메인으로도 삭제
                response.delete_cookie(cookie_name, path="/")
            
            return response
        
        # prompt=none 처리: 사용자 상호작용 없이 즉시 authorization code 발급
        if prompt == "none":
            logger.info(f"prompt=none with authenticated user: immediately generating code for {current_user.email}")
            
            # 🚀 PERFORMANCE: Parallel processing for prompt=none flow
            import asyncio
            from concurrent.futures import ThreadPoolExecutor
            
            client_ip = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent", "")
            requested_scopes = scope.split() if scope else ["read:profile"]
            
            # Create tasks for parallel execution
            async def run_security_check():
                """Run security check asynchronously"""
                try:
                    switch_detection = user_switch_security_service.detect_user_switch(
                        client_id=client_id,
                        new_user_id=str(current_user.id),
                        request_ip=client_ip,
                        db=db
                    )
                    
                    if switch_detection["is_user_switch"] and switch_detection["requires_cleanup"]:
                        logger.warning(f"🔒 prompt=none User switch detected: {switch_detection['switch_type']} "
                                     f"(risk: {switch_detection['risk_level']})")
                        
                        # Perform security cleanup
                        cleanup_result = user_switch_security_service.force_previous_user_cleanup(
                            client_id=client_id,
                            previous_user_id=switch_detection["previous_user_id"],
                            new_user_id=str(current_user.id),
                            reason="user_switch_prompt_none",
                            db=db
                        )
                        
                        # Create audit trail
                        user_switch_security_service.audit_user_switch(
                            client_id=client_id,
                            previous_user_id=switch_detection["previous_user_id"],
                            new_user_id=str(current_user.id),
                            switch_type=switch_detection["switch_type"],
                            risk_level=switch_detection["risk_level"],
                            risk_factors=switch_detection.get("risk_factors", []),
                            request_ip=client_ip,
                            user_agent=user_agent,
                            cleanup_stats=cleanup_result.get("stats"),
                            db=db
                        )
                except Exception as e:
                    logger.error(f"❌ prompt=none security check failed: {str(e)}")
            
            async def store_nonce_async():
                """Store nonce asynchronously if provided"""
                if nonce:
                    from ..services.nonce_service import nonce_service
                    nonce_service.store_nonce(
                        db=db,
                        nonce=nonce,
                        client_id=client_id,
                        user_id=str(current_user.id),
                        expires_in_minutes=10
                    )
            
            # Run security check and nonce storage in parallel
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Start both operations in parallel
                tasks = []
                tasks.append(loop.create_task(run_security_check()))
                if nonce:
                    tasks.append(loop.create_task(store_nonce_async()))
                
                # Create authorization code while other operations run
                code = create_authorization_code_record(
                    client_id, str(current_user.id), redirect_uri, scope,
                    code_challenge, code_challenge_method, db,
                    nonce=nonce,
                    auth_time=datetime.utcnow()
                )
                
                # Wait for parallel operations to complete
                if tasks:
                    loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
            finally:
                loop.close()
            
            # Create or update OAuth session
            try:
                # Update or create session with granted scopes
                session_result = db.execute(
                    text("SELECT id FROM oauth_sessions WHERE user_id = :user_id AND client_id = :client_id"),
                    {"user_id": str(current_user.id), "client_id": client_id}
                )
                existing_session = session_result.first()
                
                if existing_session:
                    # Update existing session
                    db.execute(
                        text("""
                            UPDATE oauth_sessions 
                            SET granted_scopes = :scopes, updated_at = :now
                            WHERE user_id = :user_id AND client_id = :client_id
                        """),
                        {
                            "scopes": requested_scopes,
                            "now": datetime.utcnow(),
                            "user_id": str(current_user.id),
                            "client_id": client_id
                        }
                    )
                else:
                    # Create new session with IP and User-Agent tracking
                    db.execute(
                        text("""
                            INSERT INTO oauth_sessions 
                            (user_id, client_id, granted_scopes, ip_address, user_agent, created_at, updated_at)
                            VALUES (:user_id, :client_id, :scopes, :ip_address, :user_agent, :now, :now)
                        """),
                        {
                            "user_id": str(current_user.id),
                            "client_id": client_id,
                            "scopes": requested_scopes,
                            "ip_address": client_ip,
                            "user_agent": request.headers.get("User-Agent", ""),
                            "now": datetime.utcnow()
                        }
                    )
                
                db.commit()
                
                log_oauth_action(
                    "authorize", client_id, str(current_user.id), True,
                    "prompt_none_success", f"Immediate authorization code generated for prompt=none",
                    request, db
                )
                
            except Exception as e:
                logger.warning(f"Session creation failed for prompt=none: {e}")
                db.rollback()
            
            # Immediately redirect with authorization code (no user interaction) with 쿠키 보존
            final_url = f"{redirect_uri}?code={code}"
            if state:
                final_url += f"&state={state}"
            
            logger.info(f"prompt=none success: redirecting to {final_url}")
            
            # 🔧 prompt=none 리다이렉트 시에도 쿠키 보존
            prompt_none_response = RedirectResponse(url=final_url)
            
            try:
                access_token_cookie = request.cookies.get('access_token')
                if access_token_cookie:
                    prompt_none_response.set_cookie(
                        'access_token', 
                        access_token_cookie, 
                        domain='.dwchem.co.kr',
                        httponly=True,
                        secure=not settings.debug,
                        samesite='lax',
                        max_age=3600
                    )
                
                # Redis 세션 쿠키도 보존
                session_id_cookie = request.cookies.get('session_id')
                session_token_cookie = request.cookies.get('session_token')
                user_id_cookie = request.cookies.get('user_id')
                
                if session_id_cookie:
                    prompt_none_response.set_cookie('session_id', session_id_cookie, domain='.dwchem.co.kr', httponly=True, secure=not settings.debug, samesite='lax', max_age=3600)
                if session_token_cookie:
                    prompt_none_response.set_cookie('session_token', session_token_cookie, domain='.dwchem.co.kr', httponly=True, secure=not settings.debug, samesite='lax', max_age=3600)
                if user_id_cookie:
                    prompt_none_response.set_cookie('user_id', user_id_cookie, domain='.dwchem.co.kr', httponly=True, secure=not settings.debug, samesite='lax', max_age=3600)
                    
                logger.info(f"✅ Worker {worker_id}: Preserved cookies in prompt=none redirect")
                
            except Exception as cookie_error:
                logger.warning(f"⚠️ Worker {worker_id}: Failed to preserve cookies in prompt=none redirect: {cookie_error}")
            
            return prompt_none_response
        
        # Check max_age requirement for OIDC
        if max_age is not None:
            # Check user's last authentication time
            # In a real implementation, you would track the actual auth time
            # For now, we'll require re-authentication if max_age is very small
            if max_age < 60:  # Less than 1 minute
                # Force re-authentication
                logger.info(f"max_age {max_age} requires re-authentication")
                if prompt != "none":
                    # Redirect to login with max_age requirement
                    oauth_params = {
                        "response_type": response_type,
                        "client_id": client_id,
                        "redirect_uri": redirect_uri,
                        "scope": scope,
                        "state": state,
                        "code_challenge": code_challenge,
                        "code_challenge_method": code_challenge_method,
                        "display": display,
                        "prompt": "login",  # Force login
                        "nonce": nonce,
                        "max_age": max_age,
                        "id_token_hint": id_token_hint,
                        "login_hint": login_hint,
                        "acr_values": acr_values
                    }
                    oauth_params = {k: v for k, v in oauth_params.items() if v is not None}
                    from urllib.parse import quote
                    import json
                    oauth_params_encoded = quote(json.dumps(oauth_params))
                    login_url = f"{settings.max_platform_frontend_url}/login?oauth_return={oauth_params_encoded}"
                    return RedirectResponse(url=login_url)
        
        # 🔒 SECURITY: Check for user switching and perform cleanup if needed
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")
        
        try:
            switch_detection = user_switch_security_service.detect_user_switch(
                client_id=client_id,
                new_user_id=str(current_user.id),
                request_ip=client_ip,
                db=db
            )
            
            if switch_detection["is_user_switch"] and switch_detection["requires_cleanup"]:
                logger.warning(f"🔒 User switch detected: {switch_detection['switch_type']} "
                             f"(risk: {switch_detection['risk_level']})")
                
                # Perform security cleanup
                cleanup_result = user_switch_security_service.force_previous_user_cleanup(
                    client_id=client_id,
                    previous_user_id=switch_detection["previous_user_id"],
                    new_user_id=str(current_user.id),
                    reason="user_switch_security",
                    db=db
                )
                
                # Create audit trail
                user_switch_security_service.audit_user_switch(
                    client_id=client_id,
                    previous_user_id=switch_detection["previous_user_id"],
                    new_user_id=str(current_user.id),
                    switch_type=switch_detection["switch_type"],
                    risk_level=switch_detection["risk_level"],
                    risk_factors=switch_detection.get("risk_factors", []),
                    request_ip=client_ip,
                    user_agent=user_agent,
                    cleanup_stats=cleanup_result.get("stats"),
                    db=db
                )
                
                # Log security event
                # extra_data 파라미터 제거하여 함수 시그니처 오류 방지
                log_oauth_event(
                    event_type="user_switch_security_cleanup",
                    client_id=client_id,
                    user_id=str(current_user.id),
                    success=cleanup_result["success"],
                    ip_address=client_ip,
                    user_agent=user_agent
                )
                
                if not cleanup_result["success"]:
                    logger.error(f"❌ Security cleanup failed for user switch: {cleanup_result.get('error')}")
                    # Continue with flow but log the security concern
                
        except Exception as e:
            logger.error(f"❌ User switch security check failed: {str(e)}")
            # Continue with flow but log the security concern
            log_oauth_event(
                event_type="user_switch_security_error",
                client_id=client_id,
                user_id=str(current_user.id),
                success=False,
                error=str(e),
                ip_address=client_ip,
                user_agent=user_agent
            )

        # Check existing OAuth session for auto-approval (normal flow)
        requested_scopes = scope.split() if scope else ["read:profile"]
        needs_consent = False
        
        try:
            # Check if user has already granted these scopes
            session_result = db.execute(
                text("""
                    SELECT granted_scopes FROM oauth_sessions 
                    WHERE user_id = :user_id AND client_id = :client_id
                """),
                {"user_id": str(current_user.id), "client_id": client_id}
            )
            existing_session = session_result.first()
            
            if existing_session:
                granted_scopes = existing_session[0] or []
                # Check if all requested scopes are already granted
                needs_consent = not all(scope in granted_scopes for scope in requested_scopes)
            else:
                needs_consent = True
            
            # For trusted MAX Platform clients, auto-approve
            # In production, you might want to show consent screen for new scopes
            if client_id in ['maxflowstudio', 'maxlab', 'maxteamsync', 'maxworkspace', 'maxapa', 'maxmlops']:
                needs_consent = False
                
        except Exception as e:
            logger.warning(f"Session check failed: {e}")
            needs_consent = False  # Default to auto-approve for simplicity
        
        # Store nonce if provided (for OIDC)
        if nonce:
            from ..services.nonce_service import nonce_service
            nonce_service.store_nonce(
                db=db,
                nonce=nonce,
                client_id=client_id,
                user_id=str(current_user.id),
                expires_in_minutes=10
            )
        
        # Create authorization code with OIDC parameters
        code = create_authorization_code_record(
            client_id, str(current_user.id), redirect_uri, scope,
            code_challenge, code_challenge_method, db,
            nonce=nonce,
            auth_time=datetime.utcnow()  # Record current authentication time
        )
        
        # Create or update OAuth session
        try:
            # Update or create session with granted scopes
            session_result = db.execute(
                text("SELECT id FROM oauth_sessions WHERE user_id = :user_id AND client_id = :client_id"),
                {"user_id": str(current_user.id), "client_id": client_id}
            )
            existing_session = session_result.first()
            
            if existing_session:
                # Update existing session
                db.execute(
                    text("""
                        UPDATE oauth_sessions 
                        SET granted_scopes = :granted_scopes, last_used_at = NOW()
                        WHERE user_id = :user_id AND client_id = :client_id
                    """),
                    {
                        "user_id": str(current_user.id),
                        "client_id": client_id,
                        "granted_scopes": requested_scopes
                    }
                )
            else:
                # Create new session with IP and User-Agent tracking
                db.execute(
                    text("""
                        INSERT INTO oauth_sessions 
                        (user_id, client_id, granted_scopes, ip_address, user_agent, created_at, updated_at)
                        VALUES (:user_id, :client_id, :granted_scopes, :ip_address, :user_agent, NOW(), NOW())
                    """),
                    {
                        "user_id": str(current_user.id),
                        "client_id": client_id,
                        "granted_scopes": requested_scopes,
                        "ip_address": client_ip,
                        "user_agent": request.headers.get("User-Agent", "")
                    }
                )
            
            db.commit()
            
        except Exception as e:
            logger.warning(f"Session management error: {str(e)}")
            # Continue anyway
        
        # 팝업 모드 처리: PostMessage용 HTML 페이지 반환
        if display == "popup":
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>OAuth Authorization</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: #f5f5f5;
        }}
        .container {{
            text-align: center;
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .spinner {{
            border: 4px solid #f3f3f3;
            border-top: 4px solid #3498db;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }}
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="spinner"></div>
        <h2>인증 완료</h2>
        <p>잠시만 기다려주세요...</p>
    </div>
    
    <script>
        // PostMessage로 부모 창에 성공 결과 전달
        try {{
            // 세션스토리지 정리 (무한루프 방지)
            sessionStorage.removeItem('oauth_processing');
            
            if (window.opener) {{
                // 동적 origin 감지 (요청한 클라이언트의 origin 사용)
                const clientOrigin = '{redirect_uri}'.split('/oauth/callback')[0];
                
                console.log('🎉 OAuth success - sending PostMessage to:', clientOrigin);
                
                window.opener.postMessage({{
                    type: 'OAUTH_SUCCESS',
                    code: '{code}',
                    state: '{state or ""}',
                    redirect_uri: '{redirect_uri}',
                    timestamp: Date.now()  // 중복 방지용 타임스탬프
                }}, clientOrigin);
                
                // 짧은 지연 후 창 닫기
                setTimeout(() => {{
                    console.log('🚪 Closing OAuth popup');
                    window.close();
                }}, 1000);
            }} else {{
                // opener가 없는 경우 일반 리다이렉트
                console.log('🔄 No opener found, redirecting to callback');
                window.location.href = '{redirect_uri}?code={code}' + ('{state}' ? '&state={state}' : '');
            }}
        }} catch (error) {{
            console.error('❌ PostMessage error:', error);
            // 세션스토리지 정리
            sessionStorage.removeItem('oauth_processing');
            // 에러 시 일반 리다이렉트
            window.location.href = '{redirect_uri}?code={code}' + ('{state}' ? '&state={state}' : '');
        }}
    </script>
</body>
</html>
            """
            
            log_oauth_action(
                "authorize", client_id, str(current_user.id), True,
                None, None, request, db
            )
            
            from fastapi.responses import HTMLResponse
            popup_response = HTMLResponse(content=html_content)
            
            # 🔧 팝업 모드에서도 쿠키 보존
            try:
                access_token_cookie = request.cookies.get('access_token')
                if access_token_cookie:
                    popup_response.set_cookie(
                        'access_token', 
                        access_token_cookie, 
                        domain='.dwchem.co.kr',
                        httponly=True,
                        secure=not settings.debug,
                        samesite='lax',
                        max_age=3600
                    )
                
                # Redis 세션 쿠키도 보존
                session_id_cookie = request.cookies.get('session_id')
                session_token_cookie = request.cookies.get('session_token')
                user_id_cookie = request.cookies.get('user_id')
                
                if session_id_cookie:
                    popup_response.set_cookie('session_id', session_id_cookie, domain='.dwchem.co.kr', httponly=True, secure=not settings.debug, samesite='lax', max_age=3600)
                if session_token_cookie:
                    popup_response.set_cookie('session_token', session_token_cookie, domain='.dwchem.co.kr', httponly=True, secure=not settings.debug, samesite='lax', max_age=3600)
                if user_id_cookie:
                    popup_response.set_cookie('user_id', user_id_cookie, domain='.dwchem.co.kr', httponly=True, secure=not settings.debug, samesite='lax', max_age=3600)
                    
                logger.info(f"✅ Worker {worker_id}: Preserved cookies in OAuth popup response")
                
            except Exception as cookie_error:
                logger.warning(f"⚠️ Worker {worker_id}: Failed to preserve cookies in popup response: {cookie_error}")
            
            return popup_response
        
        # 일반 모드: 기존 리다이렉트 로직 with 쿠키 보존
        success_uri = f"{redirect_uri}?code={code}"
        if state:
            success_uri += f"&state={state}"
        
        log_oauth_action(
            "authorize", client_id, str(current_user.id), True,
            None, None, request, db
        )
        
        # 🔧 OAuth 리다이렉트 시 세션 쿠키 보존
        response = RedirectResponse(url=success_uri)
        
        try:
            # 기존 access_token 쿠키 보존 (크로스 도메인 OAuth 지원)
            access_token_cookie = request.cookies.get('access_token')
            if access_token_cookie:
                response.set_cookie(
                    'access_token', 
                    access_token_cookie, 
                    domain='.dwchem.co.kr',
                    httponly=True,
                    secure=not settings.debug,
                    samesite='lax',
                    max_age=3600
                )
                logger.info(f"✅ Worker {worker_id}: Preserved access_token cookie in OAuth redirect")
            
            # Redis 세션 쿠키 보존
            session_id_cookie = request.cookies.get('session_id')
            session_token_cookie = request.cookies.get('session_token')
            user_id_cookie = request.cookies.get('user_id')
            
            if session_id_cookie:
                response.set_cookie('session_id', session_id_cookie, domain='.dwchem.co.kr', httponly=True, secure=not settings.debug, samesite='lax', max_age=3600)
            if session_token_cookie:
                response.set_cookie('session_token', session_token_cookie, domain='.dwchem.co.kr', httponly=True, secure=not settings.debug, samesite='lax', max_age=3600)
            if user_id_cookie:
                response.set_cookie('user_id', user_id_cookie, domain='.dwchem.co.kr', httponly=True, secure=not settings.debug, samesite='lax', max_age=3600)
                
            logger.info(f"✅ Worker {worker_id}: Preserved session cookies in OAuth redirect")
            
        except Exception as cookie_error:
            logger.warning(f"⚠️ Worker {worker_id}: Failed to preserve cookies in OAuth redirect: {cookie_error}")
            # Continue anyway - cookie preservation failure shouldn't break OAuth flow
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authorization error: {str(e)}")
        error_uri = f"{redirect_uri}?error=server_error"
        if state:
            error_uri += f"&state={state}"
        
        log_oauth_action(
            "authorize", client_id, None, False,
            "server_error", str(e), request, db
        )
        
        return RedirectResponse(url=error_uri)


@router.options("/token")
def token_options():
    """Handle CORS preflight requests for token endpoint"""
    return {}

@router.post("/preemptive-refresh", response_model=TokenResponse)
def preemptive_refresh(
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Preemptive token refresh endpoint
    Refreshes token if it expires in less than 5 minutes
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check token expiry from JWT
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = auth_header.split(" ")[1]
    
    try:
        # Decode token to check expiry
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
        exp = payload.get("exp")
        
        if not exp:
            raise HTTPException(status_code=400, detail="Token has no expiry")
        
        # Check if token expires in less than 5 minutes
        time_to_expiry = exp - time.time()
        
        if time_to_expiry > 300:  # More than 5 minutes
            logger.info(f"Token still valid for {time_to_expiry:.0f}s, no refresh needed")
            return TokenResponse(
                access_token=token,
                token_type="Bearer",
                expires_in=int(time_to_expiry),
                scope=payload.get("scope", ""),
                refresh_token=None  # Don't expose refresh token unnecessarily
            )
        
        # Token expires soon, generate new one
        logger.info(f"Preemptive refresh for user {current_user.id}, token expires in {time_to_expiry:.0f}s")
        
        # Generate new access token
        new_access_token = create_access_token(
            data={"sub": str(current_user.id)},
            expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
        )
        
        # Log the preemptive refresh
        log_oauth_action(
            "preemptive_refresh", "maxlab", current_user.id, True,
            None, None, request, db
        )
        
        return TokenResponse(
            access_token=new_access_token,
            token_type="Bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            scope=payload.get("scope", ""),
            refresh_token=None  # Don't rotate refresh token on preemptive refresh
        )
        
    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Preemptive refresh error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/token", response_model=TokenResponse)
def token(
    grant_type: str = Form(...),
    code: Optional[str] = Form(None),
    redirect_uri: Optional[str] = Form(None),
    client_id: str = Form(...),
    client_secret: Optional[str] = Form(None),
    code_verifier: Optional[str] = Form(None),
    refresh_token: Optional[str] = Form(None),
    scope: Optional[str] = Form(None),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    OAuth 2.0 Token Endpoint (RFC 6749 Compliant)
    Supports:
    - authorization_code grant type: Exchanges authorization code for access token
    - refresh_token grant type: Refreshes access token using refresh token
    - client_credentials grant type: Service-to-service authentication
    """
    try:
        # Clean up expired tokens periodically
        cleanup_expired_tokens(db)
        
        if grant_type == "authorization_code":
            return handle_authorization_code_grant(
                code, redirect_uri, client_id, client_secret, 
                code_verifier, request, db
            )
        elif grant_type == "refresh_token":
            return handle_refresh_token_grant(
                refresh_token, client_id, client_secret, request, db
            )
        elif grant_type == "client_credentials":
            return handle_client_credentials_grant(
                client_id, client_secret, scope, request, db
            )
        else:
            raise HTTPException(status_code=400, detail="Unsupported grant_type")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


def handle_authorization_code_grant(
    code: str,
    redirect_uri: str, 
    client_id: str,
    client_secret: Optional[str],
    code_verifier: Optional[str],
    request: Request,
    db: Session
) -> TokenResponse:
    """Handle authorization_code grant type"""
    if not code or not redirect_uri:
        raise HTTPException(status_code=400, detail="Missing required parameters")
    
    # Get authorization code record
    code_result = db.execute(
        text("SELECT * FROM authorization_codes WHERE code = :code AND used_at IS NULL"),
        {"code": code}
    )
    auth_code = code_result.first()
    
    if not auth_code:
        log_oauth_action(
            "token", client_id, None, False,
            "invalid_grant", "Invalid or expired authorization code",
            request, db
        )
        raise HTTPException(status_code=400, detail="Invalid authorization code")
    
    # Convert to dict for easier access 
    auth_code_dict = {
        'id': auth_code[0],
        'code': auth_code[1],
        'client_id': auth_code[2],
        'user_id': auth_code[3],
        'redirect_uri': auth_code[4],
        'scope': auth_code[5],
        'code_challenge': auth_code[6],
        'code_challenge_method': auth_code[7],
        'expires_at': auth_code[8],
        'used_at': auth_code[9],
        'created_at': auth_code[10]
    }
    
    # Check if code is expired
    if auth_code_dict['expires_at'] < datetime.utcnow():
        log_oauth_action(
            "token", client_id, auth_code_dict['user_id'], False,
            "invalid_grant", "Authorization code expired",
            request, db
        )
        raise HTTPException(status_code=400, detail="Authorization code expired")
    
    # Validate client
    client = validate_client(client_id, client_secret, redirect_uri, db)
    
    # Validate redirect URI matches
    if redirect_uri != auth_code_dict['redirect_uri']:
        log_oauth_action(
            "token", client_id, auth_code_dict['user_id'], False,
            "invalid_grant", "Redirect URI mismatch",
            request, db
        )
        raise HTTPException(status_code=400, detail="Redirect URI mismatch")
    
    # Validate PKCE if used
    if auth_code_dict['code_challenge']:
        if not code_verifier:
            log_oauth_action(
                "token", client_id, auth_code_dict['user_id'], False,
                "invalid_grant", "Missing code_verifier",
                request, db
            )
            raise HTTPException(status_code=400, detail="Missing code_verifier")
        
        if not verify_code_challenge(
            code_verifier, 
            auth_code_dict['code_challenge'], 
            auth_code_dict['code_challenge_method'] or "S256"
        ):
            log_oauth_action(
                "token", client_id, auth_code_dict['user_id'], False,
                "invalid_grant", "Invalid code_verifier",
                request, db
            )
            raise HTTPException(status_code=400, detail="Invalid code_verifier")
    
    # Mark code as used
    db.execute(
        text("UPDATE authorization_codes SET used_at = NOW() WHERE code = :code"),
        {"code": code}
    )
    
    # Get user with group and role information (eager loading)
    from sqlalchemy.orm import joinedload
    user = db.query(User).options(
        joinedload(User.group),
        joinedload(User.role)
    ).filter(User.id == auth_code_dict['user_id']).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    
    # Prepare complete user data for JWT token
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "is_admin": user.is_admin,
        "user_id": str(user.id)
    }
    
    # Add group information if available
    if user.group_id and user.group:
        token_data.update({
            "group_id": str(user.group_id),
            "group_name": user.group.name
        })
    
    # Add role information if available
    if user.role_id and user.role:
        token_data.update({
            "role_id": str(user.role_id),
            "role_name": user.role.name
        })
    
    # Create access token with complete user information
    access_token = create_access_token(data=token_data)
    
    # Store token hash for revocation with conflict handling
    token_hash = generate_token_hash(access_token)
    expires_at = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    try:
        # Clean up expired tokens for this user/client first
        db.execute(
            text("""
                DELETE FROM oauth_access_tokens 
                WHERE user_id = :user_id AND client_id = :client_id 
                AND (expires_at < NOW() OR revoked_at IS NOT NULL)
            """),
            {
                "user_id": auth_code_dict['user_id'],
                "client_id": client_id
            }
        )
        
        # Insert new token with conflict handling
        db.execute(
            text("""
                INSERT INTO oauth_access_tokens 
                (token_hash, client_id, user_id, scope, expires_at)
                VALUES (:token_hash, :client_id, :user_id, :scope, :expires_at)
                ON CONFLICT (token_hash) DO UPDATE SET
                    expires_at = EXCLUDED.expires_at,
                    revoked_at = NULL,
                    created_at = NOW()
            """),
            {
                "token_hash": token_hash,
                "client_id": client_id,
                "user_id": auth_code_dict['user_id'],
                "scope": auth_code_dict['scope'],
                "expires_at": expires_at
            }
        )
        
        db.commit()
        
    except Exception as token_error:
        logger.error(f"Token storage error: {str(token_error)}")
        db.rollback()
        
        # Log the error in a separate transaction
        log_oauth_action(
            "token", client_id, auth_code_dict['user_id'], False,
            "server_error", f"Token storage failed: {str(token_error)}",
            request, db
        )
        raise HTTPException(status_code=500, detail="Token creation failed")
    
    log_oauth_action(
        "token", client_id, auth_code_dict['user_id'], True,
        None, None, request, db
    )
    
    # Create refresh token
    # Extract session ID for session-scoped token management
    session_id = request.cookies.get('session_id') if request else None
    
    refresh_token = create_refresh_token_record(
        auth_code_dict['user_id'],
        client_id,
        auth_code_dict['scope'] or "read:profile",
        token_hash,
        request,
        db,
        session_id
    )
    
    # Check if openid scope is requested for ID token generation
    scopes = auth_code_dict['scope'].split() if auth_code_dict['scope'] else []
    response_data = {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
        "scope": auth_code_dict['scope'] or "read:profile",
        "refresh_token": refresh_token,
        "refresh_expires_in": 30 * 24 * 60 * 60  # 30 days in seconds
    }
    
    # Check if OIDC is enabled for this client
    client_oidc_enabled = check_client_oidc_status(client_id, db)
    
    if "openid" in scopes and client_oidc_enabled:
        # Import ID token service
        from ..services.id_token_service import id_token_service
        
        # Get nonce and auth_time from authorization code
        nonce = auth_code_dict.get('nonce')
        auth_time = auth_code_dict.get('auth_time') or auth_code_dict.get('created_at', datetime.utcnow())
        
        # Create ID token
        id_token = id_token_service.create_id_token(
            user=user,
            client_id=client_id,
            nonce=nonce,
            auth_time=auth_time,
            scopes=scopes,
            access_token=access_token,
            authorization_code=code,
            db=db
        )
        
        response_data["id_token"] = id_token
        logger.info(f"ID token generated for user {user.id} with client {client_id}")
    
    # 🔄 Create Redis Session: Establish centralized session for multi-worker consistency
    try:
        # Prepare user data for Redis session
        user_data_for_session = {
            'id': str(user.id),
            'user_id': str(user.id),  # Add user_id field for consistency
            'email': user.email,
            'name': user.display_name or user.real_name or user.email,  # Fix: Use display_name/real_name instead of name
            'real_name': user.real_name,
            'display_name': user.display_name,
            'is_admin': user.is_admin,
            'is_active': user.is_active
        }
        
        # Add group information if available
        if user.group_id and user.group:
            user_data_for_session.update({
                'group_id': str(user.group_id),
                'group_name': user.group.name
            })
        
        # Add role information if available  
        if user.role_id and user.role:
            user_data_for_session.update({
                'role_id': str(user.role_id),
                'role_name': user.role.name
            })
        
        # Create Redis session with OAuth context
        granted_scopes = auth_code_dict['scope'].split() if auth_code_dict['scope'] else ['read:profile']
        redis_session_id = create_oauth_redis_session(
            user_data=user_data_for_session,
            client_id=client_id,
            granted_scopes=granted_scopes,
            request=request
        )
        
        if redis_session_id:
            logger.info(f"✅ Redis session created for OAuth token: {redis_session_id} (user: {user.email}, client: {client_id})")
        else:
            logger.warning(f"⚠️ Redis session creation failed for user {user.email} and client {client_id} - continuing with database-only session")
            
    except Exception as redis_error:
        logger.error(f"❌ Redis session creation error: {redis_error}")
        # Don't fail the token creation if Redis fails - graceful degradation
        logger.info(f"🔄 Continuing with token creation despite Redis session failure")
    
    # Return extended response class that includes optional id_token
    return response_data


def handle_refresh_token_grant(
    refresh_token: str,
    client_id: str,
    client_secret: Optional[str],
    request: Request,
    db: Session
) -> TokenResponse:
    """Handle refresh_token grant type (RFC 6749 Section 6)"""
    logger.info(f"Processing refresh token grant for client_id: {client_id}")
    
    if not refresh_token:
        logger.error(f"Missing refresh_token parameter for client_id: {client_id}")
        log_oauth_action(
            "token", client_id, None, False,
            "invalid_request", "Missing refresh_token parameter",
            request, db
        )
        raise HTTPException(status_code=400, detail="Missing refresh_token parameter")
    
    # Validate client (refresh token requests require client authentication)
    try:
        logger.info(f"Validating client credentials for client_id: {client_id}")
        client = validate_client_for_refresh_token(client_id, client_secret, db)
        logger.info(f"Client validation successful for client_id: {client_id}")
    except HTTPException as e:
        # Re-raise with appropriate error for refresh token context
        logger.error(f"Client validation failed for client_id: {client_id}, error: {e.detail}")
        log_oauth_action(
            "token", client_id, None, False,
            "invalid_client", f"Client authentication failed: {e.detail}",
            request, db
        )
        raise HTTPException(status_code=401, detail="Invalid client credentials")
    
    # Validate refresh token
    logger.info(f"Validating refresh token for client_id: {client_id}")
    token_info = validate_refresh_token(refresh_token, client_id, db)
    if not token_info:
        logger.error(f"Refresh token validation failed for client_id: {client_id}")
        log_oauth_action(
            "token", client_id, None, False,
            "invalid_grant", "Invalid or expired refresh token",
            request, db
        )
        raise HTTPException(status_code=400, detail="Invalid or expired refresh token")
    
    logger.info(f"Refresh token validation successful for client_id: {client_id}, user_id: {token_info['user_id']}")
    
    # Get Redis coordinator for distributed locking with session isolation
    try:
        redis_store = get_session_store()
        if redis_store and redis_store.redis_client:
            coordinator = get_token_refresh_coordinator(redis_store.redis_client)
            
            # Extract session ID from request for session-scoped token management
            session_id = request.cookies.get('session_id') if request else None
            logger.info(f"🔐 Token refresh with session isolation - user={token_info['user_id']}, client={client_id}, session={session_id}")
            
            # Use distributed lock to prevent race conditions with session scope
            with coordinator.acquire_refresh_lock(token_info['user_id'], client_id, session_id) as lock_acquired:
                if lock_acquired is None:
                    # Using cached result from another concurrent refresh with session scope
                    cached = coordinator._get_cached_refresh(token_info['user_id'], client_id, session_id)
                    if cached:
                        if session_id:
                            logger.info(f"📦 Using cached refresh result for user={token_info['user_id']}, session={session_id}")
                        else:
                            logger.info(f"📦 Using cached refresh result for user={token_info['user_id']}")
                        return TokenResponse(
                            access_token=cached['access_token'],
                            token_type="Bearer",
                            expires_in=cached['expires_in'],
                            scope=token_info['scope'],
                            refresh_token=cached['refresh_token'],
                            refresh_expires_in=30 * 24 * 60 * 60
                        )
                
                # Proceed with token rotation under lock protection
                logger.info(f"🔒 Token rotation under distributed lock for client_id: {client_id}, user_id: {token_info['user_id']}")
                new_access_token, new_refresh_token = rotate_refresh_token(
                    token_info['token_hash'],
                    token_info['user_id'],
                    client_id,
                    token_info['scope'],
                    request,
                    db,
                    session_id
                )
                
                # Cache the result for other concurrent requests with session scope
                coordinator.cache_refresh_result(
                    token_info['user_id'],
                    client_id,
                    new_access_token,
                    new_refresh_token,
                    settings.access_token_expire_minutes * 60,
                    session_id
                )
                
                logger.info(f"Token rotation successful (with Redis) for client_id: {client_id}, user_id: {token_info['user_id']}")
                
                # Log successful token refresh
                log_oauth_action(
                    "token", client_id, token_info['user_id'], True,
                    None, None, request, db
                )
                
                # Check if openid scope is requested for ID token generation
                scopes = token_info['scope'].split() if token_info['scope'] else []
                response_data = {
                    "access_token": new_access_token,
                    "token_type": "Bearer",
                    "expires_in": settings.access_token_expire_minutes * 60,
                    "scope": token_info['scope'],
                    "refresh_token": new_refresh_token,
                    "refresh_expires_in": 30 * 24 * 60 * 60  # 30 days in seconds
                }
                
                # Check if OIDC is enabled for this client
                client_oidc_enabled = check_client_oidc_status(client_id, db)
                
                if "openid" in scopes and client_oidc_enabled:
                    # Import ID token service
                    from ..services.id_token_service import id_token_service
                    
                    # Get user for ID token
                    user = db.query(User).filter(User.id == token_info['user_id']).first()
                    if user:
                        # Create ID token for refresh (preserving original auth_time if available)
                        id_token = id_token_service.refresh_id_token(
                            user=user,
                            client_id=client_id,
                            scopes=scopes,
                            db=db,
                            original_auth_time=token_info.get('auth_time')
                        )
                        response_data["id_token"] = id_token
                        logger.info(f"ID token refreshed for user {user.id} with client {client_id}")
                
                return TokenResponse(**response_data)
        else:
            # Fallback to original behavior if Redis is not available
            session_id = request.cookies.get('session_id') if request else None
            logger.warning(f"⚠️ Redis not available, proceeding without distributed lock (session={session_id})")
            new_access_token, new_refresh_token = rotate_refresh_token(
                token_info['token_hash'],
                token_info['user_id'],
                client_id,
                token_info['scope'],
                request,
                db,
                session_id
            )
            
            logger.info(f"Token rotation successful (without Redis) for client_id: {client_id}, user_id: {token_info['user_id']}")
            
            # Log successful token refresh
            log_oauth_action(
                "token", client_id, token_info['user_id'], True,
                None, None, request, db
            )
            
            # Check if openid scope is requested for ID token generation
            scopes = token_info['scope'].split() if token_info['scope'] else []
            response_data = {
                "access_token": new_access_token,
                "token_type": "Bearer",
                "expires_in": settings.access_token_expire_minutes * 60,
                "scope": token_info['scope'],
                "refresh_token": new_refresh_token,
                "refresh_expires_in": 30 * 24 * 60 * 60  # 30 days in seconds
            }
            
            # Check if OIDC is enabled for this client
            client_oidc_enabled = check_client_oidc_status(client_id, db)
            
            if "openid" in scopes and client_oidc_enabled:
                # Import ID token service
                from ..services.id_token_service import id_token_service
                
                # Get user for ID token
                user = db.query(User).filter(User.id == token_info['user_id']).first()
                if user:
                    # Create ID token for refresh (preserving original auth_time if available)
                    id_token = id_token_service.refresh_id_token(
                        user=user,
                        client_id=client_id,
                        scopes=scopes,
                        db=db,
                        original_auth_time=token_info.get('auth_time')
                    )
                    response_data["id_token"] = id_token
                    logger.info(f"ID token refreshed for user {user.id} with client {client_id}")
            
            return TokenResponse(**response_data)
    except TimeoutError:
        logger.error(f"⏱️ Token refresh lock timeout for user={token_info['user_id']}, client={client_id}")
        raise HTTPException(status_code=503, detail="Service temporarily unavailable, please retry")
    except Exception as e:
        logger.error(f"❌ Unexpected error during token refresh: {e}")
        # Fallback to original behavior
        logger.info(f"Starting token rotation for client_id: {client_id}, user_id: {token_info['user_id']}")
        new_access_token, new_refresh_token = rotate_refresh_token(
            token_info['token_hash'],
            token_info['user_id'],
            client_id,
            token_info['scope'],
            request,
            db
        )
        
        logger.info(f"Token rotation successful for client_id: {client_id}, user_id: {token_info['user_id']}")
        
        # Log successful token refresh
        log_oauth_action(
            "token", client_id, token_info['user_id'], True,
            None, None, request, db
        )
        
        # Check if openid scope is requested for ID token generation
        scopes = token_info['scope'].split() if token_info['scope'] else []
        response_data = {
            "access_token": new_access_token,
            "token_type": "Bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
            "scope": token_info['scope'],
            "refresh_token": new_refresh_token,
            "refresh_expires_in": 30 * 24 * 60 * 60  # 30 days in seconds
        }
        
        # Check if OIDC is enabled for this client
        client_oidc_enabled = check_client_oidc_status(client_id, db)
        
        if "openid" in scopes and client_oidc_enabled:
            # Import ID token service
            from ..services.id_token_service import id_token_service
            
            # Get user for ID token
            user = db.query(User).filter(User.id == token_info['user_id']).first()
            if user:
                # Create ID token for refresh (preserving original auth_time if available)
                id_token = id_token_service.refresh_id_token(
                    user=user,
                    client_id=client_id,
                    scopes=scopes,
                    db=db,
                    original_auth_time=token_info.get('auth_time')
                )
                response_data["id_token"] = id_token
                logger.info(f"ID token refreshed for user {user.id} with client {client_id}")
        
        return TokenResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Refresh token rotation error: {str(e)}")
        log_oauth_action(
            "token", client_id, token_info['user_id'], False,
            "server_error", f"Token rotation failed: {str(e)}",
            request, db
        )
        raise HTTPException(status_code=500, detail="Token refresh failed")


def handle_client_credentials_grant(
    client_id: str,
    client_secret: Optional[str],
    scope: Optional[str],
    request: Request,
    db: Session
) -> TokenResponse:
    """Handle client_credentials grant type for service authentication"""
    logger.info(f"Processing client credentials grant for client_id: {client_id}")
    
    if not client_secret:
        logger.error(f"Missing client_secret for client_credentials grant: {client_id}")
        log_oauth_action(
            "token", client_id, None, False,
            "invalid_request", "Missing client_secret for confidential client",
            request, db
        )
        raise HTTPException(status_code=400, detail="client_secret required for client_credentials grant")
    
    # Validate client exists and is confidential
    try:
        result = db.execute(
            text("SELECT * FROM oauth_clients WHERE client_id = :client_id AND is_active = true"),
            {"client_id": client_id}
        )
        client = result.first()
        
        if not client:
            logger.error(f"Client not found: {client_id}")
            log_oauth_action(
                "token", client_id, None, False,
                "invalid_client", "Client not found",
                request, db
            )
            raise HTTPException(status_code=401, detail="Invalid client_id")
        
        # Convert to dict for easier access
        client_dict = {
            'id': client[0],
            'client_id': client[1],
            'client_secret': client[2],
            'client_name': client[3],
            'description': client[4],
            'redirect_uris': client[5],
            'allowed_scopes': client[6],
            'is_confidential': client[7],
            'is_active': client[8]
        }
        
        # Only confidential clients can use client_credentials grant
        if not client_dict['is_confidential']:
            logger.error(f"Public client attempted client_credentials grant: {client_id}")
            log_oauth_action(
                "token", client_id, None, False,
                "unauthorized_client", "Public clients cannot use client_credentials grant",
                request, db
            )
            raise HTTPException(status_code=401, detail="Only confidential clients can use client_credentials grant")
        
        # Verify client secret
        if client_secret != client_dict['client_secret']:
            logger.error(f"Invalid client_secret for client_id: {client_id}")
            log_oauth_action(
                "token", client_id, None, False,
                "invalid_client", "Invalid client_secret",
                request, db
            )
            raise HTTPException(status_code=401, detail="Invalid client_secret")
        
        # Check if client is intended for service use (no redirect_uris indicates service client)
        if client_dict['redirect_uris'] and len(client_dict['redirect_uris']) > 0:
            logger.warning(f"Web client attempting client_credentials grant: {client_id}")
        
        logger.info(f"Client validation successful for service client: {client_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Client validation error for client_credentials: {str(e)}")
        log_oauth_action(
            "token", client_id, None, False,
            "server_error", f"Client validation failed: {str(e)}",
            request, db
        )
        raise HTTPException(status_code=500, detail="Client validation failed")
    
    # Validate and process requested scopes
    try:
        if scope:
            requested_scopes = scope.split()
        else:
            # Default scopes for service clients (admin-level access)
            requested_scopes = ["admin:oauth", "admin:users", "admin:system"]
        
        # Ensure requested scopes are within allowed scopes for this client
        allowed_scopes = client_dict['allowed_scopes'] or []
        
        # Add default service scopes if not present in client config
        default_service_scopes = ["admin:oauth", "admin:users", "admin:system"]
        for default_scope in default_service_scopes:
            if default_scope not in allowed_scopes:
                allowed_scopes.append(default_scope)
        
        # Check if all requested scopes are allowed
        invalid_scopes = [s for s in requested_scopes if s not in allowed_scopes]
        if invalid_scopes:
            logger.error(f"Invalid scopes requested for client {client_id}: {invalid_scopes}")
            log_oauth_action(
                "token", client_id, None, False,
                "invalid_scope", f"Invalid scopes: {', '.join(invalid_scopes)}",
                request, db
            )
            raise HTTPException(status_code=400, detail=f"Invalid scope(s): {', '.join(invalid_scopes)}")
        
        granted_scope = " ".join(requested_scopes)
        logger.info(f"Granted scopes for service client {client_id}: {granted_scope}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scope validation error: {str(e)}")
        log_oauth_action(
            "token", client_id, None, False,
            "server_error", f"Scope validation failed: {str(e)}",
            request, db
        )
        raise HTTPException(status_code=500, detail="Scope validation failed")
    
    # Create service token (no user_id, longer expiration)
    try:
        # Service tokens have longer expiration (24 hours by default)
        service_token_expire_hours = 24
        
        token_data = {
            "sub": f"service:{client_id}",  # Service identifier
            "client_id": client_id,
            "scope": granted_scope,
            "token_type": "service",
            "iss": "maxplatform"
        }
        
        # Create service access token with extended expiration
        service_token_expires_delta = timedelta(hours=service_token_expire_hours)
        access_token = create_access_token(data=token_data, expires_delta=service_token_expires_delta)
        
        # Store service token (no user_id for service tokens)
        token_hash = generate_token_hash(access_token)
        expires_at = datetime.utcnow() + service_token_expires_delta
        
        # Clean up any existing service tokens for this client
        db.execute(
            text("""
                DELETE FROM oauth_access_tokens 
                WHERE client_id = :client_id AND user_id IS NULL
                AND (expires_at < NOW() OR revoked_at IS NOT NULL)
            """),
            {"client_id": client_id}
        )
        
        # Insert new service token
        db.execute(
            text("""
                INSERT INTO oauth_access_tokens 
                (token_hash, client_id, user_id, scope, expires_at)
                VALUES (:token_hash, :client_id, NULL, :scope, :expires_at)
                ON CONFLICT (token_hash) DO UPDATE SET
                    expires_at = EXCLUDED.expires_at,
                    revoked_at = NULL,
                    created_at = NOW()
            """),
            {
                "token_hash": token_hash,
                "client_id": client_id,
                "scope": granted_scope,
                "expires_at": expires_at
            }
        )
        
        db.commit()
        
        logger.info(f"Service token created successfully for client: {client_id}")
        
        # Log successful service token creation
        log_oauth_action(
            "token", client_id, None, True,
            None, f"Service token created with scopes: {granted_scope}",
            request, db
        )
        
        # Return token response (no refresh token for client_credentials)
        return TokenResponse(
            access_token=access_token,
            token_type="Bearer",
            expires_in=service_token_expire_hours * 3600,  # Convert to seconds
            scope=granted_scope,
            refresh_token=None,  # No refresh token for client_credentials grant
            refresh_expires_in=None
        )
        
    except Exception as e:
        logger.error(f"Service token creation failed for client {client_id}: {str(e)}")
        db.rollback()
        log_oauth_action(
            "token", client_id, None, False,
            "server_error", f"Service token creation failed: {str(e)}",
            request, db
        )
        raise HTTPException(status_code=500, detail="Service token creation failed")


@router.get("/userinfo")
def userinfo(
    request: Request,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    OAuth 2.0 / OIDC UserInfo Endpoint
    Returns information about the authenticated user based on granted scopes
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get user's groups with eager loading for better performance
    from sqlalchemy.orm import joinedload
    user_with_relations = db.query(User).options(
        joinedload(User.group),
        joinedload(User.role)
    ).filter(User.id == current_user.id).first()
    
    if not user_with_relations:
        user_with_relations = current_user
    
    # Try to get scopes from access token
    scopes = []
    try:
        # Get authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            # Decode token to get scopes (without verification since user is already authenticated)
            from jose import jwt
            payload = jwt.get_unverified_claims(token)
            token_scopes = payload.get("scope", "")
            scopes = token_scopes.split() if token_scopes else []
    except Exception as e:
        logger.debug(f"Could not extract scopes from token: {e}")
        # Default scopes if can't extract from token
        scopes = ["openid", "profile", "email"]
    
    # Check if OIDC scopes are requested
    if "openid" in scopes:
        # Use claims service for OIDC-compliant response
        from ..services.claims_service import claims_service
        
        # Get OIDC claims based on scopes
        claims = claims_service.get_userinfo_response(
            user=user_with_relations,
            scopes=scopes,
            db=db,
            as_jwt=False  # Return as JSON by default
        )
        
        # Return raw claims dictionary for OIDC compliance
        return claims
    else:
        # Legacy OAuth 2.0 response for backward compatibility
        # Prepare group information
        groups = []
        group_id = None
        group_name = None
        
        if user_with_relations.group:
            groups.append(user_with_relations.group.name)
            group_id = str(user_with_relations.group.id)
            group_name = user_with_relations.group.name
        
        # Prepare role information
        role_id = None
        role_name = None
        
        if user_with_relations.role:
            role_id = str(user_with_relations.role.id)
            role_name = user_with_relations.role.name
        
        return UserInfoResponse(
            sub=str(user_with_relations.id),
            email=user_with_relations.email,
            name=user_with_relations.display_name or user_with_relations.real_name or user_with_relations.email,
            groups=groups,
            is_admin=user_with_relations.is_admin,
            group_id=group_id,
            group_name=group_name,
            role_id=role_id,
            role_name=role_name
        )


@router.options("/revoke")
def revoke_options():
    """Handle CORS preflight requests for revoke endpoint"""
    return {}

@router.post("/revoke")
def revoke(
    token: str = Form(...),
    token_type_hint: Optional[str] = Form("access_token"),
    client_id: str = Form(...),
    client_secret: Optional[str] = Form(None),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    OAuth 2.0 Token Revocation Endpoint
    Revokes an access token
    """
    try:
        # Validate client (basic validation)
        client_result = db.execute(
            text("SELECT is_confidential FROM oauth_clients WHERE client_id = :client_id"),
            {"client_id": client_id}
        )
        client = client_result.first()
        
        if not client:
            raise HTTPException(status_code=401, detail="Invalid client")
        
        # Generate token hash
        token_hash = generate_token_hash(token)
        
        # Revoke token
        result = db.execute(
            text("""
                UPDATE oauth_access_tokens 
                SET revoked_at = NOW() 
                WHERE token_hash = :token_hash AND client_id = :client_id
                RETURNING user_id
            """),
            {"token_hash": token_hash, "client_id": client_id}
        )
        
        revoked = result.first()
        db.commit()
        
        log_oauth_action(
            "revoke", client_id, revoked.user_id if revoked else None, True,
            None, None, request, db
        )
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Revocation error: {str(e)}")
        log_oauth_action(
            "revoke", client_id, None, False,
            "server_error", str(e), request, db
        )
        # Per spec, always return 200 OK
        return {"status": "ok"}


@router.get("/.well-known/oauth-authorization-server")
def oauth_metadata():
    """
    OAuth 2.0 Authorization Server Metadata
    Returns server capabilities and endpoints
    """
    base_url = f"http://localhost:8000"
    
    return {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/api/oauth/authorize",
        "token_endpoint": f"{base_url}/api/oauth/token",
        "userinfo_endpoint": f"{base_url}/api/oauth/userinfo",
        "revocation_endpoint": f"{base_url}/api/oauth/revoke",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token", "client_credentials"],
        "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"],
        "revocation_endpoint_auth_methods_supported": ["client_secret_post"],
        "code_challenge_methods_supported": ["S256", "plain"],
        "scopes_supported": [
            "read:profile",
            "read:features", 
            "read:groups",
            "manage:workflows",
            "manage:teams",
            "manage:experiments",
            "manage:workspaces",
            "manage:apis",
            "manage:models",
            "admin:oauth",
            "admin:users",
            "admin:system"
        ]
    }


@router.get("/.well-known/openid-configuration")
def openid_configuration():
    """
    OpenID Connect Discovery Endpoint
    Returns OIDC provider configuration
    """
    base_url = settings.oidc_issuer or settings.max_platform_api_url
    
    return {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/api/oauth/authorize",
        "token_endpoint": f"{base_url}/api/oauth/token",
        "userinfo_endpoint": f"{base_url}/api/oauth/userinfo",
        "jwks_uri": f"{base_url}/api/oauth/jwks",
        "scopes_supported": [
            # OIDC standard scopes
            "openid", "profile", "email", "address", "phone", "offline_access",
            # MAX Platform custom scopes
            "read:profile", "read:features", "read:groups",
            "manage:workflows", "manage:teams", "manage:experiments",
            "manage:workspaces", "manage:apis", "manage:models",
            "groups", "roles",  # Custom OIDC scopes
            # Admin scopes
            "admin:oauth", "admin:users", "admin:system"
        ],
        "response_types_supported": [
            "code",
            "id_token",
            "token id_token",
            "code id_token",
            "code token",
            "code token id_token"
        ],
        "response_modes_supported": ["query", "fragment", "form_post"],
        "grant_types_supported": [
            "authorization_code",
            "implicit",
            "refresh_token",
            "client_credentials"
        ],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["RS256", "HS256"],
        "token_endpoint_auth_methods_supported": [
            "client_secret_post",
            "client_secret_basic",
            "client_secret_jwt",
            "private_key_jwt"
        ],
        "claims_supported": settings.oidc_supported_claims,
        "code_challenge_methods_supported": ["plain", "S256"],
        "introspection_endpoint": f"{base_url}/api/oauth/introspect",
        "revocation_endpoint": f"{base_url}/api/oauth/revoke",
        "claim_types_supported": ["normal"],
        "claims_parameter_supported": False,
        "request_parameter_supported": False,
        "request_uri_parameter_supported": False,
        "require_request_uri_registration": False,
        "check_session_iframe": f"{base_url}/api/oauth/check_session",
        "end_session_endpoint": f"{base_url}/api/oauth/logout",
        "acr_values_supported": ["0", "1"],
        "display_values_supported": ["page", "popup"],
        "prompt_values_supported": ["none", "login", "consent", "select_account"]
    }


@router.get("/jwks")
def jwks(db: Session = Depends(get_db)):
    """
    JSON Web Key Set (JWKS) Endpoint
    Returns public keys for ID token verification
    """
    from ..services.jwks_service import jwks_service
    
    try:
        jwks_data = jwks_service.get_public_keys_jwks(db)
        return jwks_data
    except Exception as e:
        logger.error(f"JWKS endpoint error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve JWKS"
        )


@router.get("/logout", response_class=RedirectResponse)
async def oauth_logout(
    request: Request,
    post_logout_redirect_uri: Optional[str] = None,
    client_id: Optional[str] = None,
    id_token_hint: Optional[str] = None,
    state: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    ENHANCED OIDC RP-Initiated Logout Endpoint
    
    Enhanced logout process with better session handling:
    1. Multiple user identification methods (token, cookie, client_id)
    2. Aggressive token cleanup across all possible storage locations  
    3. Cookie cleanup with proper domain/path settings
    4. Client-side coordination through response headers
    5. Comprehensive error handling and logging
    """
    from sqlalchemy import text
    from ..utils.auth import get_current_user_silent, get_current_user_from_token
    
    logout_stats = {
        "access_tokens_revoked": 0,
        "refresh_tokens_revoked": 0, 
        "sessions_terminated": 0,
        "id_tokens_invalidated": 0,
        "cookies_cleared": 0
    }
    
    # Enhanced user identification with multiple fallback methods
    current_user = None
    user_id_from_token = None
    access_token_value = None
    
    logger.info(f"🔐 Starting enhanced logout process - client_id: {client_id}")
    
    # Method 1: ID Token Hint (most reliable for logout)
    if id_token_hint:
        try:
            from jose import jwt
            unverified_claims = jwt.get_unverified_claims(id_token_hint)
            user_id_from_token = unverified_claims.get("sub")
            logger.info(f"🔐 User ID from token hint: {user_id_from_token}")
        except Exception as e:
            logger.warning(f"Failed to parse id_token_hint: {e}")
    
    # Method 2: Authorization Header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            access_token_value = auth_header.split(" ")[1]
            current_user = await get_current_user_silent(request=request, db=db)
            if current_user:
                logger.info(f"🔐 User from auth header: {current_user.email}")
        except Exception as e:
            logger.debug(f"No valid token in Authorization header: {e}")
    
    # Method 3: Cookie-based identification (CRITICAL for web apps)
    if not current_user and not access_token_value:
        cookie_names = ["access_token", "token", "auth_token", "jwt_token"]
        for cookie_name in cookie_names:
            try:
                cookie_value = request.cookies.get(cookie_name)
                if cookie_value:
                    logger.info(f"🔐 Found token in cookie: {cookie_name}")
                    current_user = get_current_user_from_token(cookie_value, db)
                    if current_user:
                        access_token_value = cookie_value
                        logger.info(f"🔐 User from cookie {cookie_name}: {current_user.email}")
                        break
                    else:
                        # Even if token is invalid, we should clear the cookie
                        logout_stats["cookies_cleared"] += 1
            except Exception as e:
                logger.debug(f"Cookie {cookie_name} validation failed: {e}")
                logout_stats["cookies_cleared"] += 1
    
    # Method 4: Database-based user lookup (fallback for lost sessions)
    target_user_id = None
    if current_user:
        target_user_id = str(current_user.id)
    elif user_id_from_token:
        target_user_id = user_id_from_token
    elif client_id:
        # Last resort: find the most recent active session for this client
        try:
            recent_session = db.execute(
                text("""
                    SELECT user_id FROM oauth_access_tokens 
                    WHERE client_id = :client_id 
                    AND revoked_at IS NULL 
                    ORDER BY created_at DESC 
                    LIMIT 1
                """),
                {"client_id": client_id}
            ).first()
            
            if recent_session:
                target_user_id = recent_session.user_id
                logger.info(f"🔐 Found user from recent session: {target_user_id}")
        except Exception as e:
            logger.error(f"Failed to find user from recent sessions: {e}")
    
    if not target_user_id:
        logger.warning(f"🔐 No user context found for logout - proceeding with cookie cleanup only")
    
    # Enhanced Token Revocation Process
    try:
        # 1. Revoke specific access token if we have it
        if access_token_value:
            try:
                from ..utils.auth import generate_token_hash
                token_hash = generate_token_hash(access_token_value)
                
                result = db.execute(
                    text("""
                        UPDATE oauth_access_tokens 
                        SET revoked_at = NOW(),
                            revocation_reason = 'oidc_logout_direct'
                        WHERE token_hash = :token_hash 
                        AND revoked_at IS NULL
                    """),
                    {"token_hash": token_hash}
                )
                logout_stats["access_tokens_revoked"] += result.rowcount
                logger.info(f"🔐 Revoked direct token: {result.rowcount} tokens")
            except Exception as e:
                logger.error(f"Failed to revoke direct access token: {e}")
        
        # 2. Revoke all user tokens if we have user context
        if target_user_id:
            # Access tokens
            if client_id:
                # Client-specific revocation
                result = db.execute(
                    text("""
                        UPDATE oauth_access_tokens 
                        SET revoked_at = NOW(),
                            revocation_reason = 'oidc_logout_client'
                        WHERE user_id = :user_id 
                        AND client_id = :client_id
                        AND revoked_at IS NULL
                    """),
                    {"user_id": target_user_id, "client_id": client_id}
                )
                logout_stats["access_tokens_revoked"] += result.rowcount
            else:
                # All clients
                result = db.execute(
                    text("""
                        UPDATE oauth_access_tokens 
                        SET revoked_at = NOW(),
                            revocation_reason = 'oidc_logout_all'
                        WHERE user_id = :user_id 
                        AND revoked_at IS NULL
                    """),
                    {"user_id": target_user_id}
                )
                logout_stats["access_tokens_revoked"] += result.rowcount
            
            # Refresh tokens  
            if client_id:
                result = db.execute(
                    text("""
                        UPDATE oauth_refresh_tokens 
                        SET revoked_at = NOW(),
                            token_status = 'revoked'
                        WHERE user_id = :user_id 
                        AND client_id = :client_id
                        AND revoked_at IS NULL
                    """),
                    {"user_id": target_user_id, "client_id": client_id}
                )
                logout_stats["refresh_tokens_revoked"] += result.rowcount
            else:
                result = db.execute(
                    text("""
                        UPDATE oauth_refresh_tokens 
                        SET revoked_at = NOW(),
                            token_status = 'revoked'
                        WHERE user_id = :user_id 
                        AND revoked_at IS NULL
                    """),
                    {"user_id": target_user_id}
                )
                logout_stats["refresh_tokens_revoked"] += result.rowcount
            
            # OAuth sessions
            if client_id:
                result = db.execute(
                    text("""
                        DELETE FROM oauth_sessions 
                        WHERE user_id = :user_id 
                        AND client_id = :client_id
                    """),
                    {"user_id": target_user_id, "client_id": client_id}
                )
                logout_stats["sessions_terminated"] += result.rowcount
            else:
                result = db.execute(
                    text("""
                        DELETE FROM oauth_sessions 
                        WHERE user_id = :user_id
                    """),
                    {"user_id": target_user_id}
                )
                logout_stats["sessions_terminated"] += result.rowcount
            
            # Legacy JWT refresh tokens
            try:
                from ..models.refresh_token import RefreshToken
                if current_user:
                    result = db.query(RefreshToken).filter(
                        RefreshToken.user_id == current_user.id,
                        RefreshToken.is_active == True
                    ).update({
                        "is_active": False,
                        "is_revoked": True
                    })
                    logout_stats["refresh_tokens_revoked"] += result
            except Exception as e:
                logger.error(f"Failed to revoke JWT refresh tokens: {e}")
            
            # 🔄 Redis Session Cleanup: Remove centralized sessions for multi-worker consistency
            try:
                redis_cleanup_count = cleanup_oauth_redis_sessions(
                    user_id=str(target_user_id),
                    client_id=client_id if client_id else None
                )
                
                if redis_cleanup_count > 0:
                    logger.info(f"✅ Cleaned up {redis_cleanup_count} Redis sessions for user {target_user_id}")
                    logout_stats["sessions_terminated"] += redis_cleanup_count
                else:
                    logger.debug(f"🔍 No Redis sessions found for user {target_user_id}")
                    
            except Exception as redis_cleanup_error:
                logger.error(f"❌ Redis session cleanup error for user {target_user_id}: {redis_cleanup_error}")
                # Don't fail the logout if Redis cleanup fails - graceful degradation
                logger.info(f"🔄 Continuing with logout despite Redis cleanup failure")
        
        # 3. Client-wide cleanup as final fallback
        elif client_id:
            logger.info(f"🔐 Performing client-wide cleanup for: {client_id}")
            
            result = db.execute(
                text("""
                    UPDATE oauth_access_tokens 
                    SET revoked_at = NOW(),
                        revocation_reason = 'client_logout_fallback'
                    WHERE client_id = :client_id 
                    AND revoked_at IS NULL
                """),
                {"client_id": client_id}
            )
            logout_stats["access_tokens_revoked"] += result.rowcount
            
            result = db.execute(
                text("""
                    UPDATE oauth_refresh_tokens 
                    SET revoked_at = NOW(),
                        token_status = 'revoked'
                    WHERE client_id = :client_id 
                    AND revoked_at IS NULL
                """),
                {"client_id": client_id}
            )
            logout_stats["refresh_tokens_revoked"] += result.rowcount
            
            result = db.execute(
                text("""
                    DELETE FROM oauth_sessions 
                    WHERE client_id = :client_id
                """),
                {"client_id": client_id}
            )
            logout_stats["sessions_terminated"] += result.rowcount
    
        # Commit all token changes
        db.commit()
        logger.info(f"🔐 Token revocation completed: {logout_stats}")
        
    except Exception as e:
        logger.error(f"Failed to revoke tokens: {e}")
        db.rollback()
        # Continue with cookie cleanup even if token revocation fails
    
    # Enhanced Logout Audit Log
    try:
        log_oauth_action(
            action="oidc_logout_enhanced",
            client_id=client_id,
            user_id=target_user_id,
            success=True,
            error_code=None,
            error_description=f"Enhanced OIDC logout: {logout_stats}",
            request=request,
            db=db
        )
    except Exception as e:
        logger.error(f"Failed to log logout action: {e}")
    
    # Prepare redirect URL
    if post_logout_redirect_uri:
        try:
            from urllib.parse import urlparse
            parsed_uri = urlparse(post_logout_redirect_uri)
            allowed_domains = [
                "maxlab.dwchem.co.kr",
                "devmaxlab.dwchem.co.kr", 
                "max.dwchem.co.kr",
                "devmax.dwchem.co.kr",
                urlparse(settings.max_platform_frontend_url).hostname
            ]
            
            if parsed_uri.hostname not in allowed_domains:
                logger.warning(f"🔒 Logout redirect to untrusted domain: {parsed_uri.hostname}")
                redirect_url = f"{settings.max_platform_frontend_url}/login?logout=success&error=untrusted_domain"
            else:
                redirect_url = post_logout_redirect_uri
                logger.info(f"🔐 Logout redirect to trusted domain: {parsed_uri.hostname}")
        except Exception as e:
            logger.error(f"Failed to parse logout redirect URI: {e}")
            redirect_url = f"{settings.max_platform_frontend_url}/login?logout=success&error=parse_error"
    else:
        redirect_url = f"{settings.max_platform_frontend_url}/login?logout=success"
    
    # Add state parameter if provided
    if state:
        separator = "&" if "?" in redirect_url else "?"
        redirect_url = f"{redirect_url}{separator}state={state}"
    
    logger.info(f"🔐 Enhanced OIDC Logout completed: {logout_stats}")
    logger.info(f"🔐 Redirecting to: {redirect_url}")
    
    # Enhanced Response with Comprehensive Cookie Cleanup
    response = RedirectResponse(url=redirect_url, status_code=302)
    
    # Clear all possible cookie variations (JWT, 세션, OAuth 관련 모든 쿠키)
    cookie_names = [
        "access_token", "token", "auth_token", "jwt_token", "refresh_token",
        "session_id", "session_token", "user_id", "oauth_session",
        "maxplatform_session", "maxlab_session"
    ]
    cookie_domains = [None, ".dwchem.co.kr", "max.dwchem.co.kr", "maxlab.dwchem.co.kr"]
    cookie_paths = ["/", "/api/", "/oauth/"]
    
    for cookie_name in cookie_names:
        # Clear for current domain/path
        response.delete_cookie(
            key=cookie_name,
            path="/",
            secure=True,
            httponly=True,
            samesite="lax"
        )
        
        # Clear for all possible domain/path combinations
        for domain in cookie_domains:
            for path in cookie_paths:
                try:
                    response.delete_cookie(
                        key=cookie_name,
                        domain=domain,
                        path=path,
                        secure=True,
                        httponly=True,
                        samesite="lax"
                    )
                    logout_stats["cookies_cleared"] += 1
                except Exception as e:
                    logger.debug(f"Could not clear cookie {cookie_name} for {domain}{path}: {e}")
    
    # Add headers to coordinate client-side cleanup
    response.headers["X-Logout-Status"] = "completed"
    response.headers["X-Logout-Stats"] = str(logout_stats)
    response.headers["X-Clear-Storage"] = "true"  # Signal frontend to clear localStorage/sessionStorage
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    return response


@router.get("/check_session")
async def check_session(
    request: Request,
    client_id: Optional[str] = Query(None),
    session_state: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    OIDC Session Management - Check Session Iframe Endpoint
    
    This endpoint is designed to be loaded in an iframe by client applications
    to check if the user's session is still active. It returns an HTML page
    that can communicate with the parent window via postMessage.
    
    Used for OIDC Session Management (OP iframe) as per:
    https://openid.net/specs/openid-connect-session-1_0.html#OPiframe
    """
    
    # Check if user has a valid session
    session_valid = False
    user_id = None
    
    try:
        # Try to get current user from various sources
        current_user = await get_current_user_optional(request, db)
        if current_user:
            session_valid = True
            user_id = str(current_user.id)
            logger.debug(f"Session check: User {current_user.email} has valid session")
        else:
            logger.debug("Session check: No valid user session found")
    except Exception as e:
        logger.debug(f"Session check error: {e}")
        session_valid = False
    
    # Generate session state if not provided (should match client's session state)
    if not session_state and session_valid and client_id:
        # Generate a simple session state based on user_id and client_id
        import hashlib
        session_state = hashlib.sha256(f"{user_id}:{client_id}:{int(time.time() // 300)}".encode()).hexdigest()[:16]
    
    # HTML content for the iframe
    # This implements the OIDC Session Management check_session_iframe
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>OIDC Session Check</title>
        <style>
            body {{ margin: 0; padding: 0; font-family: Arial, sans-serif; font-size: 12px; }}
            .status {{ padding: 5px; background: {'#e8f5e8' if session_valid else '#ffeaa7'}; }}
        </style>
    </head>
    <body>
        <div class="status">
            Session: {'Valid' if session_valid else 'Invalid'}
            {f' | Client: {client_id}' if client_id else ''}
            {f' | State: {session_state}' if session_state else ''}
        </div>
        
        <script>
            (function() {{
                var clientId = '{client_id or ''}';
                var sessionState = '{session_state or ''}';
                var sessionValid = {'true' if session_valid else 'false'};
                
                // Listen for session check requests from parent window
                window.addEventListener('message', function(e) {{
                    if (e.origin !== window.location.origin) {{
                        return; // Security: only respond to same-origin requests
                    }}
                    
                    try {{
                        var data = e.data;
                        if (typeof data === 'string') {{
                            var parts = data.split(' ');
                            if (parts.length >= 2) {{
                                var checkClientId = parts[0];
                                var checkSessionState = parts[1];
                                
                                var status = 'changed'; // Default to changed
                                
                                if (sessionValid && checkClientId === clientId) {{
                                    if (checkSessionState === sessionState) {{
                                        status = 'unchanged';
                                    }} else {{
                                        status = 'changed';
                                    }}
                                }} else {{
                                    status = 'error';
                                }}
                                
                                // Send response back to parent
                                e.source.postMessage(status, e.origin);
                            }}
                        }}
                    }} catch (err) {{
                        // Send error response
                        e.source.postMessage('error', e.origin);
                    }}
                }});
                
                // Periodically check session status
                setInterval(function() {{
                    try {{
                        // Send keepalive message to parent if session is valid
                        if (sessionValid && window.parent && window.parent !== window) {{
                            window.parent.postMessage({{
                                type: 'session_keepalive',
                                client_id: clientId,
                                session_state: sessionState,
                                timestamp: new Date().getTime()
                            }}, window.location.origin);
                        }}
                    }} catch (err) {{
                        // Ignore errors in keepalive
                    }}
                }}, 30000); // Every 30 seconds
                
                console.log('OIDC Check Session iframe loaded', {{
                    clientId: clientId,
                    sessionState: sessionState,
                    sessionValid: sessionValid
                }});
            }})();
        </script>
    </body>
    </html>
    """
    
    # Create response with proper headers for iframe usage
    from fastapi.responses import HTMLResponse
    response = HTMLResponse(content=html_content)
    
    # CRITICAL: Remove X-Frame-Options to allow framing
    # This endpoint MUST be frameable for OIDC session management
    if "X-Frame-Options" in response.headers:
        del response.headers["X-Frame-Options"]
    
    # Set Content-Security-Policy to allow framing from same origin
    response.headers["Content-Security-Policy"] = "frame-ancestors 'self' https://*.dwchem.co.kr"
    
    # Cache control for session checking
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    logger.info(f"Check session iframe served - Valid: {session_valid}, Client: {client_id}")
    
    return response