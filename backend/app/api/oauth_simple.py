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
from ..utils.auth import get_current_user_optional, verify_password, create_access_token
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/oauth", tags=["OAuth 2.0"])


# Pydantic models
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    scope: str


class UserInfoResponse(BaseModel):
    sub: str  # User ID
    email: str
    name: str
    groups: List[str]


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
    """Log OAuth actions for audit trail"""
    if not db:
        return
    
    try:
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
        
    except Exception as e:
        logger.error(f"Audit log error: {str(e)}")
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
    current_user: Optional[User] = Depends(get_current_user_optional),
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
        
        # Get user
        user = db.query(User).filter(User.id == auth_code_dict['user_id']).first()
        if not user:
            raise HTTPException(status_code=400, detail="User not found")
        
        # Create access token (reuse existing JWT token creation)
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        
        # Store token hash for revocation
        token_hash = generate_token_hash(access_token)
        expires_at = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
        
        db.execute(
            text("""
                INSERT INTO oauth_access_tokens 
                (token_hash, client_id, user_id, scope, expires_at)
                VALUES (:token_hash, :client_id, :user_id, :scope, :expires_at)
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
        
        log_oauth_action(
            "token", client_id, auth_code_dict['user_id'], True,
            None, None, request, db
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="Bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            scope=auth_code_dict['scope'] or "read:profile"
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
    
    # Get user's groups
    groups = []
    
    if current_user.group_id:
        group = db.query(Group).filter(Group.id == current_user.group_id).first()
        if group:
            groups.append(group.name)
    
    return UserInfoResponse(
        sub=str(current_user.id),
        email=current_user.email,
        name=current_user.display_name or current_user.real_name or current_user.email,
        groups=groups
    )


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
        "grant_types_supported": ["authorization_code"],
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
            "manage:models"
        ]
    }