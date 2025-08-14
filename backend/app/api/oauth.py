"""
OAuth 2.0 API Router for MAX Platform
Implements Authorization Code Flow with PKCE support
"""

from datetime import datetime, timedelta, timezone
import secrets
import hashlib
import base64
import json
import time
from typing import Optional, List
from urllib.parse import urlparse, parse_qs

from fastapi import APIRouter, Depends, HTTPException, Request, Query, Form
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, delete, text
from pydantic import BaseModel, Field, HttpUrl
from jose import jwt, JWTError

from ..database import get_db
from ..models import User, Group
from ..config import settings
from ..utils.auth import get_current_user_optional, verify_password, create_access_token
from ..core.redis_session import get_session_store, create_user_session, get_user_session
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/oauth", tags=["OAuth 2.0"])


# Pydantic models
class AuthorizeRequest(BaseModel):
    response_type: str = Field(..., description="Must be 'code'")
    client_id: str
    redirect_uri: HttpUrl
    state: Optional[str] = None
    scope: Optional[str] = "read:profile"
    code_challenge: Optional[str] = None
    code_challenge_method: Optional[str] = None


class TokenRequest(BaseModel):
    grant_type: str = Field(..., description="Must be 'authorization_code'")
    code: str
    redirect_uri: HttpUrl
    client_id: str
    client_secret: Optional[str] = None
    code_verifier: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    scope: str
    refresh_token: Optional[str] = None


class IntrospectRequest(BaseModel):
    token: str
    token_type_hint: Optional[str] = "access_token"


class RevokeRequest(BaseModel):
    token: str
    token_type_hint: Optional[str] = "access_token"


class UserInfoResponse(BaseModel):
    sub: str  # User ID
    email: str
    name: str
    groups: List[str]
    permissions: List[str]


# Helper functions
def generate_authorization_code() -> str:
    """Generate a secure random authorization code"""
    return secrets.token_urlsafe(32)


def generate_token_hash(token: str) -> str:
    """Generate SHA256 hash of token for storage"""
    return hashlib.sha256(token.encode()).hexdigest()


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


async def verify_jwt_and_sync_redis(request: Request, db: Session) -> Optional[User]:
    """
    JWT 토큰 검증 및 Redis 세션 자동 복구
    OAuth 무한 루프 문제 해결을 위한 핵심 함수
    """
    try:
        # Extract JWT token from multiple sources
        token = None
        
        # 1. Check Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
        
        # 2. Check cookies
        if not token:
            token = request.cookies.get("access_token")
        
        # 3. Check query parameters (for OAuth flow)
        if not token:
            token = request.query_params.get("token")
        
        if not token:
            return None
        
        # Verify JWT token
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            user_id = payload.get("sub") or payload.get("user_id")
            
            if not user_id:
                logger.warning("JWT token missing user_id/sub field")
                return None
            
            # Get user from database
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                logger.warning(f"User {user_id} not found in database despite valid JWT")
                return None
            
            # Check Redis session
            try:
                session_store = get_session_store()
                
                # Try to get existing Redis session for this user
                user_sessions_key = f"maxplatform_session_user:{user_id}"
                existing_sessions = session_store.redis_client.smembers(user_sessions_key)
                
                redis_session_exists = False
                for session_id in existing_sessions:
                    session_data = session_store.get_session(session_id)
                    if session_data:
                        redis_session_exists = True
                        logger.info(f"✅ Found existing Redis session for user {user.email}")
                        break
                
                if not redis_session_exists:
                    # 🔥 핵심 수정: JWT는 유효하지만 Redis 세션이 없는 경우 자동 생성
                    logger.warning(f"JWT valid but no Redis session for user {user_id}, creating new session")
                    
                    session_data = {
                        "id": str(user.id),
                        "email": user.email,
                        "name": user.real_name or user.display_name or user.email,
                        "is_admin": user.is_admin,
                        "is_active": user.is_active,
                        "groups": [{"id": str(g.id), "name": g.name} for g in user.groups] if user.groups else [],
                        "roles": [{"id": str(r.id), "name": r.name} for r in user.roles] if user.roles else [],
                        "created_at": datetime.utcnow().isoformat(),
                        "source": "jwt_recovery",
                        "jwt_exp": payload.get("exp")
                    }
                    
                    # Calculate TTL from JWT expiration
                    ttl = payload.get("exp", 0) - int(time.time())
                    if ttl > 0:
                        # Override session timeout with JWT remaining time
                        session_store.session_timeout = ttl
                        
                    session_id = create_user_session(session_data)
                    logger.info(f"✅ Auto-recovered Redis session {session_id} for user {user.email}")
                    
                    # Store token in Redis session
                    session_store.store_oauth_tokens(session_id, {
                        "access_token": token,
                        "token_type": "Bearer",
                        "expires_at": payload.get("exp"),
                        "recovered": True
                    })
                
            except Exception as redis_error:
                # Redis 오류가 있어도 JWT가 유효하면 계속 진행
                logger.error(f"Redis session error (non-fatal): {redis_error}")
            
            return user
            
        except jwt.ExpiredSignatureError:
            logger.debug("JWT token expired")
            
            # JWT 만료 시 Redis 세션도 정리
            try:
                session_store = get_session_store()
                payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm], options={"verify_exp": False})
                user_id = payload.get("sub") or payload.get("user_id")
                if user_id:
                    deleted_count = session_store.delete_user_sessions(user_id)
                    if deleted_count > 0:
                        logger.info(f"Cleaned up {deleted_count} expired Redis sessions for user {user_id}")
            except:
                pass
                
            return None
            
        except JWTError as e:
            logger.debug(f"JWT validation error: {e}")
            return None
            
    except Exception as e:
        logger.error(f"Error in verify_jwt_and_sync_redis: {e}")
        return None


def validate_client(
    client_id: str,
    client_secret: Optional[str],
    redirect_uri: str,
    db: Session
) -> dict:
    """Validate OAuth client credentials and redirect URI"""
    # Get client from database
    result = db.execute(
        text("SELECT * FROM oauth_clients WHERE client_id = :client_id AND is_active = true"),
        {"client_id": client_id}
    )
    client = result.first()
    
    if not client:
        raise HTTPException(status_code=400, detail="Invalid client_id")
    
    # Check redirect URI
    if redirect_uri not in client.redirect_uris:
        raise HTTPException(status_code=400, detail="Invalid redirect_uri")
    
    # For confidential clients, verify secret
    if client.is_confidential and client_secret != client.client_secret:
        raise HTTPException(status_code=401, detail="Invalid client_secret")
    
    return dict(client)


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
    code = generate_authorization_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    
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
    """Log OAuth actions for audit trail"""
    if not db:
        return
    
    ip_address = None
    user_agent = None
    
    if request:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")
    
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
    db.commit()


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
    request: Request = None,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    OAuth 2.0 Authorization Endpoint with Redis Session Auto-Recovery
    Initiates the authorization code flow and manages JWT-Redis session sync
    """
    try:
        # Validate request
        if response_type != "code":
            raise HTTPException(status_code=400, detail="Unsupported response_type")
        
        # Validate client and redirect URI
        client = validate_client(client_id, None, redirect_uri, db)
        
        # JWT 토큰 검증 및 Redis 세션 동기화
        jwt_user = await verify_jwt_and_sync_redis(request, db)
        
        # Use JWT user if available, otherwise use current_user
        authenticated_user = jwt_user or current_user
        
        # Check if user is authenticated
        if not authenticated_user:
            # Store OAuth params in session and redirect to login
            error_uri = f"{redirect_uri}?error=login_required"
            if state:
                error_uri += f"&state={state}"
            
            log_oauth_action(
                "authorize", client_id, None, False, 
                "login_required", "User not authenticated",
                request, db
            )
            
            return RedirectResponse(url=error_uri)
        
        # Check if user has already authorized this client
        session_result = db.execute(
            text("SELECT granted_scopes FROM oauth_sessions WHERE user_id = :user_id AND client_id = :client_id"),
            {"user_id": str(authenticated_user.id), "client_id": client_id}
        )
        existing_session = session_result.first()
        
        requested_scopes = scope.split() if scope else ["read:profile"]
        
        # If user has existing session with all requested scopes, auto-approve
        if existing_session and all(s in existing_session.granted_scopes for s in requested_scopes):
            # Create authorization code
            code = create_authorization_code_record(
                client_id, str(authenticated_user.id), redirect_uri, scope,
                code_challenge, code_challenge_method, db
            )
            
            # Update last used timestamp
            db.execute(
                text("""
                    UPDATE oauth_sessions 
                    SET last_used_at = NOW() 
                    WHERE user_id = :user_id AND client_id = :client_id
                """),
                {"user_id": str(authenticated_user.id), "client_id": client_id}
            )
            db.commit()
            
            # Build redirect URI
            success_uri = f"{redirect_uri}?code={code}"
            if state:
                success_uri += f"&state={state}"
            
            log_oauth_action(
                "authorize", client_id, str(authenticated_user.id), True,
                None, None, request, db
            )
            
            return RedirectResponse(url=success_uri)
        
        # Otherwise, show consent screen
        # For API implementation, we'll auto-approve for now
        # In production, you'd redirect to a consent page
        
        # Create new session
        if not existing_session:
            db.execute(
                text("""
                    INSERT INTO oauth_sessions 
                    (user_id, client_id, granted_scopes)
                    VALUES (:user_id, :client_id, :granted_scopes)
                """),
                {
                    "user_id": str(authenticated_user.id),
                    "client_id": client_id,
                    "granted_scopes": requested_scopes
                }
            )
        else:
            # Update existing session with new scopes
            all_scopes = list(set(existing_session.granted_scopes + requested_scopes))
            db.execute(
                text("""
                    UPDATE oauth_sessions 
                    SET granted_scopes = :granted_scopes, last_used_at = NOW()
                    WHERE user_id = :user_id AND client_id = :client_id
                """),
                {
                    "user_id": str(authenticated_user.id),
                    "client_id": client_id,
                    "granted_scopes": all_scopes
                }
            )
        
        # Create authorization code
        code = create_authorization_code_record(
            client_id, str(authenticated_user.id), redirect_uri, scope,
            code_challenge, code_challenge_method, db
        )
        
        db.commit()
        
        # Build redirect URI
        success_uri = f"{redirect_uri}?code={code}"
        if state:
            success_uri += f"&state={state}"
        
        log_oauth_action(
            "authorize", client_id, str(authenticated_user.id), True,
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


@router.post("/token", response_model=TokenResponse)
def token(
    grant_type: str = Form(...),
    code: str = Form(...),
    redirect_uri: str = Form(...),
    client_id: str = Form(...),
    client_secret: Optional[str] = Form(None),
    code_verifier: Optional[str] = Form(None),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    OAuth 2.0 Token Endpoint
    Exchanges authorization code for access token
    """
    try:
        if grant_type != "authorization_code":
            raise HTTPException(status_code=400, detail="Unsupported grant_type")
        
        # Get authorization code record
        code_result = await db.execute(
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
        
        # Check if code is expired
        if auth_code.expires_at < datetime.now(timezone.utc):
            log_oauth_action(
                "token", client_id, auth_code.user_id, False,
                "invalid_grant", "Authorization code expired",
                request, db
            )
            raise HTTPException(status_code=400, detail="Authorization code expired")
        
        # Validate client
        client = await validate_client(client_id, client_secret, redirect_uri, db)
        
        # Validate redirect URI matches
        if redirect_uri != auth_code.redirect_uri:
            log_oauth_action(
                "token", client_id, auth_code.user_id, False,
                "invalid_grant", "Redirect URI mismatch",
                request, db
            )
            raise HTTPException(status_code=400, detail="Redirect URI mismatch")
        
        # Validate PKCE if used
        if auth_code.code_challenge:
            if not code_verifier:
                log_oauth_action(
                    "token", client_id, auth_code.user_id, False,
                    "invalid_grant", "Missing code_verifier",
                    request, db
                )
                raise HTTPException(status_code=400, detail="Missing code_verifier")
            
            if not verify_code_challenge(
                code_verifier, 
                auth_code.code_challenge, 
                auth_code.code_challenge_method or "S256"
            ):
                log_oauth_action(
                    "token", client_id, auth_code.user_id, False,
                    "invalid_grant", "Invalid code_verifier",
                    request, db
                )
                raise HTTPException(status_code=400, detail="Invalid code_verifier")
        
        # Mark code as used
        await db.execute(
            text("UPDATE authorization_codes SET used_at = NOW() WHERE code = :code"),
            {"code": code}
        )
        
        # Get user
        user_result = await db.execute(
            select(User).where(User.id == auth_code.user_id)
        )
        user = user_result.scalar_one()
        
        # Create access token (reuse existing JWT token creation)
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        
        # Store token hash for revocation
        token_hash = generate_token_hash(access_token)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        await db.execute(
            text("""
                INSERT INTO oauth_access_tokens 
                (token_hash, client_id, user_id, scope, expires_at)
                VALUES (:token_hash, :client_id, :user_id, :scope, :expires_at)
            """),
            {
                "token_hash": token_hash,
                "client_id": client_id,
                "user_id": auth_code.user_id,
                "scope": auth_code.scope,
                "expires_at": expires_at
            }
        )
        
        db.commit()
        
        log_oauth_action(
            "token", client_id, auth_code.user_id, True,
            None, None, request, db
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="Bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            scope=auth_code.scope or "read:profile"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token error: {str(e)}")
        log_oauth_action(
            "token", client_id, None, False,
            "server_error", str(e), request, db
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/userinfo", response_model=UserInfoResponse)
async def userinfo(
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth 2.0 UserInfo Endpoint
    Returns information about the authenticated user
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get user's groups
    groups = []
    permissions = []
    
    if current_user.group_id:
        group_result = await db.execute(
            select(Group).where(Group.id == current_user.group_id)
        )
        group = group_result.scalar_one_or_none()
        if group:
            groups.append(group.name)
            if group.permissions:
                permissions.extend(group.permissions.get("permissions", []))
    
    return UserInfoResponse(
        sub=str(current_user.id),
        email=current_user.email,
        name=current_user.display_name or current_user.real_name or current_user.email,
        groups=groups,
        permissions=permissions
    )


@router.post("/revoke")
def revoke(
    token: str = Form(...),
    token_type_hint: Optional[str] = Form("access_token"),
    client_id: str = Form(...),
    client_secret: Optional[str] = Form(None),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth 2.0 Token Revocation Endpoint
    Revokes an access token
    """
    try:
        # Validate client (basic validation)
        client_result = await db.execute(
            text("SELECT is_confidential FROM oauth_clients WHERE client_id = :client_id"),
            {"client_id": client_id}
        )
        client = client_result.first()
        
        if not client:
            raise HTTPException(status_code=401, detail="Invalid client")
        
        # Generate token hash
        token_hash = generate_token_hash(token)
        
        # Revoke token
        result = await db.execute(
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


@router.post("/introspect")
def introspect(
    token: str = Form(...),
    token_type_hint: Optional[str] = Form("access_token"),
    client_id: str = Form(...),
    client_secret: Optional[str] = Form(None),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth 2.0 Token Introspection Endpoint
    Checks if a token is active
    """
    try:
        # Generate token hash
        token_hash = generate_token_hash(token)
        
        # Check token
        result = await db.execute(
            text("""
                SELECT * FROM oauth_access_tokens WHERE
                token_hash = :token_hash AND 
                revoked_at IS NULL AND 
                expires_at > NOW()
            """),
            {"token_hash": token_hash}
        )
        
        token_record = result.first()
        
        if not token_record:
            return {"active": False}
        
        # Get user info
        user_result = await db.execute(
            select(User).where(User.id == token_record.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            return {"active": False}
        
        log_oauth_action(
            "introspect", client_id, str(user.id), True,
            None, None, request, db
        )
        
        return {
            "active": True,
            "scope": token_record.scope,
            "client_id": token_record.client_id,
            "username": user.email,
            "exp": int(token_record.expires_at.timestamp()),
            "sub": str(user.id)
        }
        
    except Exception as e:
        logger.error(f"Introspection error: {str(e)}")
        log_oauth_action(
            "introspect", client_id, None, False,
            "server_error", str(e), request, db
        )
        return {"active": False}


@router.get("/.well-known/oauth-authorization-server")
async def oauth_metadata():
    """
    OAuth 2.0 Authorization Server Metadata
    Returns server capabilities and endpoints
    """
    #base_url = f"http://localhost:8000"
    base_url = settings.MAX_PLATFORM_API_URL
    
    return {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/api/oauth/authorize",
        "token_endpoint": f"{base_url}/api/oauth/token",
        "userinfo_endpoint": f"{base_url}/api/oauth/userinfo",
        "revocation_endpoint": f"{base_url}/api/oauth/revoke",
        "introspection_endpoint": f"{base_url}/api/oauth/introspect",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"],
        "revocation_endpoint_auth_methods_supported": ["client_secret_post"],
        "introspection_endpoint_auth_methods_supported": ["client_secret_post"],
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
            "manage:models"
        ]
    }