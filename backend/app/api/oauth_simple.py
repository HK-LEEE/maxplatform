"""
OAuth 2.0 API Router for MAX Platform (Simplified)
Implements Authorization Code Flow with basic functionality
"""

from datetime import datetime, timedelta
import secrets
import hashlib
import base64
from typing import Optional, List
from urllib.parse import urlparse, parse_qs

from fastapi import APIRouter, Depends, HTTPException, Request, Query, Form
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, Field, HttpUrl

from ..database import get_db
from ..models import User, Group
from ..config import settings
from ..utils.auth import get_current_user_optional, get_current_user_silent, verify_password, create_access_token
from ..utils.logging_config import get_oauth_logger, log_oauth_event, SecurityDataFilter

logger = get_oauth_logger()

router = APIRouter(prefix="/api/oauth", tags=["OAuth 2.0"])


# Pydantic models
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    scope: str
    refresh_token: Optional[str] = None
    refresh_expires_in: Optional[int] = None


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
    db: Session
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
                 expires_at, client_ip, user_agent, rotation_count)
                VALUES (:token_hash, :client_id, :user_id, :scope, :access_token_hash,
                        :expires_at, :client_ip, :user_agent, 0)
            """),
            {
                "token_hash": refresh_token_hash,
                "client_id": client_id,
                "user_id": user_id,
                "scope": scope,
                "access_token_hash": access_token_hash,
                "expires_at": expires_at,
                "client_ip": client_ip,
                "user_agent": user_agent
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
    db: Session
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
                 client_ip, user_agent, rotation_count, parent_token_hash, token_status)
                SELECT :new_token_hash, client_id, user_id, scope, :new_access_token_hash, :expires_at,
                       :client_ip, :user_agent, rotation_count + 1, :old_token_hash, 'active'
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
                (token_hash, client_id, user_id, scope, expires_at, refresh_token_hash)
                VALUES (:token_hash, :client_id, :user_id, :scope, :expires_at, :refresh_token_hash)
            """),
            {
                "token_hash": new_access_token_hash,
                "client_id": client_id,
                "user_id": user_id,
                "scope": scope,
                "expires_at": access_token_expires,
                "refresh_token_hash": new_refresh_token_hash
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
        
        # Check redirect URI
        if redirect_uri not in client_dict['redirect_uris']:
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
    db: Session
) -> str:
    """Create authorization code record in database"""
    try:
        code = generate_authorization_code()
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        
        db.execute(
            text("""
                INSERT INTO authorization_codes 
                (code, client_id, user_id, redirect_uri, scope, code_challenge, 
                 code_challenge_method, expires_at)
                VALUES (:code, :client_id, :user_id, :redirect_uri, :scope, 
                        :code_challenge, :code_challenge_method, :expires_at)
            """),
            {
                "code": code,
                "client_id": client_id,
                "user_id": user_id,
                "redirect_uri": redirect_uri,
                "scope": scope,
                "code_challenge": code_challenge,
                "code_challenge_method": code_challenge_method,
                "expires_at": expires_at
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


# OAuth endpoints
@router.get("/authorize")
def authorize(
    response_type: str = Query(...),
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    state: Optional[str] = Query(None),
    scope: Optional[str] = Query("read:profile"),
    code_challenge: Optional[str] = Query(None),
    code_challenge_method: Optional[str] = Query(None),
    display: Optional[str] = Query(None),  # popup 모드 감지용
    prompt: Optional[str] = Query(None),   # OpenID Connect prompt 파라미터
    request: Request = None,
    current_user: Optional[User] = Depends(get_current_user_silent),
    db: Session = Depends(get_db)
):
    """
    OAuth 2.0 Authorization Endpoint
    Initiates the authorization code flow
    """
    try:
        # 무한루프 감지를 위한 로깅
        logger.info(f"OAuth authorize request: client_id={client_id}, display={display}, prompt={prompt}, redirect_uri={redirect_uri}")
        
        # Validate request
        if response_type != "code":
            raise HTTPException(status_code=400, detail="Unsupported response_type")
        
        # Validate client and redirect URI
        client = validate_client(client_id, None, redirect_uri, db)
        
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
                    "prompt": prompt
                }
                
                # Remove None values
                oauth_params = {k: v for k, v in oauth_params.items() if v is not None}
                oauth_params_encoded = quote(json.dumps(oauth_params))
                
                # 팝업 모드에서도 로그인 페이지로 리다이렉트
                login_url = f"http://localhost:3000/login?oauth_return={oauth_params_encoded}"
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
                "prompt": prompt
            }
            
            # Remove None values
            oauth_params = {k: v for k, v in oauth_params.items() if v is not None}
            oauth_params_encoded = quote(json.dumps(oauth_params))
            
            # Redirect to login page with return URL
            login_url = f"http://localhost:3000/login?oauth_return={oauth_params_encoded}"
            
            log_oauth_action(
                "authorize", client_id, None, False, 
                "login_required", "User not authenticated - redirecting to login",
                request, db
            )
            
            return RedirectResponse(url=login_url)
        
        # prompt=none 처리: 사용자 상호작용 없이 즉시 authorization code 발급
        if prompt == "none":
            logger.info(f"prompt=none with authenticated user: immediately generating code for {current_user.email}")
            
            # Parse requested scopes
            requested_scopes = scope.split() if scope else ["read:profile"]
            
            # Create authorization code immediately without consent checks
            code = create_authorization_code_record(
                client_id, str(current_user.id), redirect_uri, scope,
                code_challenge, code_challenge_method, db
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
                    # Create new session
                    db.execute(
                        text("""
                            INSERT INTO oauth_sessions (user_id, client_id, granted_scopes, created_at, updated_at)
                            VALUES (:user_id, :client_id, :scopes, :now, :now)
                        """),
                        {
                            "user_id": str(current_user.id),
                            "client_id": client_id,
                            "scopes": requested_scopes,
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
            
            # Immediately redirect with authorization code (no user interaction)
            final_url = f"{redirect_uri}?code={code}"
            if state:
                final_url += f"&state={state}"
            
            logger.info(f"prompt=none success: redirecting to {final_url}")
            return RedirectResponse(url=final_url)
        
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
        
        # Create authorization code
        code = create_authorization_code_record(
            client_id, str(current_user.id), redirect_uri, scope,
            code_challenge, code_challenge_method, db
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
                # Create new session
                db.execute(
                    text("""
                        INSERT INTO oauth_sessions 
                        (user_id, client_id, granted_scopes)
                        VALUES (:user_id, :client_id, :granted_scopes)
                    """),
                    {
                        "user_id": str(current_user.id),
                        "client_id": client_id,
                        "granted_scopes": requested_scopes
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
            return HTMLResponse(content=html_content)
        
        # 일반 모드: 기존 리다이렉트 로직
        success_uri = f"{redirect_uri}?code={code}"
        if state:
            success_uri += f"&state={state}"
        
        log_oauth_action(
            "authorize", client_id, str(current_user.id), True,
            None, None, request, db
        )
        
        return RedirectResponse(url=success_uri)
        
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
    refresh_token = create_refresh_token_record(
        auth_code_dict['user_id'],
        client_id,
        auth_code_dict['scope'] or "read:profile",
        token_hash,
        request,
        db
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="Bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        scope=auth_code_dict['scope'] or "read:profile",
        refresh_token=refresh_token,
        refresh_expires_in=30 * 24 * 60 * 60  # 30 days in seconds
    )


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
    
    # Rotate refresh token (RFC 6749 security best practice)
    try:
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
        
        return TokenResponse(
            access_token=new_access_token,
            token_type="Bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            scope=token_info['scope'],
            refresh_token=new_refresh_token,
            refresh_expires_in=30 * 24 * 60 * 60  # 30 days in seconds
        )
        
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


@router.get("/userinfo", response_model=UserInfoResponse)
def userinfo(
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    OAuth 2.0 UserInfo Endpoint
    Returns information about the authenticated user
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