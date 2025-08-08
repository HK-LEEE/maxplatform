from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from ..config import settings
from ..database import get_db
from ..models.user import User
import logging
import secrets
import uuid
import hashlib
from .logging_config import get_auth_logger, log_auth_event, SecurityDataFilter

logger = get_auth_logger()

# OAuth2 스키마
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)

# 비밀번호 암호화 컨텍스트
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """비밀번호 해시 생성"""
    return pwd_context.hash(password)

def generate_token_hash(token: str) -> str:
    """Generate SHA256 hash of token for storage and revocation"""
    return hashlib.sha256(token.encode()).hexdigest()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """JWT 액세스 토큰 생성 (고유성 보장)"""
    to_encode = data.copy()
    now = datetime.utcnow()
    
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    
    # 고유성 보장을 위한 추가 필드
    to_encode.update({
        "exp": expire,
        "type": "access", 
        "iat": now,
        "jti": str(uuid.uuid4()),  # JWT ID for uniqueness
        "nbf": now,  # Not before
        "iss": "maxplatform",  # Issuer
        "nonce": secrets.token_hex(8)  # Additional randomness
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    
    # Log token creation
    log_auth_event(
        event_type="access_token_created",
        user_id=data.get("sub") or data.get("user_id"),
        success=True,
        additional_data={
            "token_type": "access",
            "expires_at": expire.isoformat(),
            "jti": to_encode["jti"]
        }
    )
    
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """JWT 리프레시 토큰 생성"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh", "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def verify_token(token: str) -> Optional[str]:
    """JWT 토큰 검증 및 사용자명 반환"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None:
            log_auth_event(
                event_type="token_verification",
                success=False,
                error="Missing subject in token payload"
            )
            return None
        
        # Log successful verification
        log_auth_event(
            event_type="token_verification",
            user_id=username,
            success=True,
            additional_data={
                "token_type": payload.get("type", "unknown"),
                "jti": payload.get("jti")
            }
        )
        
        return username
    except JWTError as e:
        log_auth_event(
            event_type="token_verification",
            success=False,
            error=f"JWT decode error: {str(e)}"
        )
        return None

def extract_user_info_from_token(token: str) -> Optional[Dict[str, Any]]:
    """JWT 토큰에서 사용자 정보 추출 (그룹 정보 포함)"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        
        # 토큰 타입 확인
        token_type = payload.get("type")
        if token_type != "access":
            return None
        
        # 토큰 만료 확인
        exp = payload.get("exp")
        if exp and datetime.utcnow().timestamp() > exp:
            return None
            
        user_info = {
            "user_id": payload.get("user_id") or payload.get("sub"),
            "email": payload.get("email"),
            "is_admin": payload.get("is_admin", False),
            "group_id": payload.get("group_id"),
            "group_name": payload.get("group_name"),
            "role_id": payload.get("role_id"),
            "role_name": payload.get("role_name")
        }
        
        return user_info
        
    except JWTError as e:
        logger.warning(f"Token info extraction failed: {e}")
        return None

def get_user_by_id(db: Session, user_id: str):
    """ID로 사용자 조회"""
    from ..models.user import User
    return db.query(User).filter(User.id == user_id).first()

def extract_token_from_request(request: Request) -> Optional[str]:
    """Request에서 토큰 추출 (Authorization 헤더 또는 쿠키에서)"""
    # Authorization 헤더에서 토큰 추출
    authorization = request.headers.get("Authorization")
    if authorization:
        if authorization.startswith("Bearer "):
            return authorization[7:]
        elif authorization.startswith("bearer "):
            return authorization[7:]
    
    # 쿠키에서 토큰 추출 (fallback)
    token = request.cookies.get("access_token")
    if token:
        return token
    
    return None

def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
):
    """Access Token으로부터 현재 사용자 정보 조회"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 토큰이 oauth2_scheme에서 오지 않았다면 request에서 직접 추출
        if not token:
            token = extract_token_from_request(request)
        
        if not token or token.strip() == "":
            logger.warning("No token provided in request")
            raise credentials_exception
            
        # Bearer 접두사 제거 (이미 제거되었을 수도 있음)
        if token.startswith("Bearer "):
            token = token[7:]
        elif token.startswith("bearer "):
            token = token[7:]
        
        # 토큰 세그먼트 확인 (JWT는 3개의 세그먼트로 구성)
        token_parts = token.split('.')
        if len(token_parts) != 3:
            logger.warning(f"Invalid token format: expected 3 segments, got {len(token_parts)}")
            raise credentials_exception
            
        # JWT 디코딩 및 검증
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        
        # 토큰 타입 확인
        token_type = payload.get("type")
        if token_type != "access":
            logger.warning(f"Invalid token type: {token_type}")
            raise credentials_exception
        
        # 토큰 만료 확인 (JWT 라이브러리에서 자동으로 체크하지만 명시적으로 확인)
        exp = payload.get("exp")
        if exp:
            current_timestamp = datetime.utcnow().timestamp()
            if current_timestamp > exp:
                logger.debug("Token has expired")
                raise credentials_exception
            
        user_id: str = payload.get("sub")
        if user_id is None:
            logger.warning("No user ID in token payload")
            raise credentials_exception
            
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise credentials_exception
    except HTTPException:
        # HTTPException은 다시 발생시키지 말고 credentials_exception으로 변환
        raise credentials_exception
    except Exception as e:
        # 로그 레벨을 debug로 낮춰서 스팸 방지
        logger.debug(f"Token validation failed: {e}")
        raise credentials_exception
    
    # OAuth 토큰 취소 상태 확인
    # OAuth 테이블에 토큰이 저장되어 있는 경우 취소 여부 확인
    from sqlalchemy import text
    token_hash = generate_token_hash(token)
    result = db.execute(
        text("""
            SELECT revoked_at FROM oauth_access_tokens 
            WHERE token_hash = :token_hash
            LIMIT 1
        """),
        {"token_hash": token_hash}
    )
    oauth_token = result.first()
    
    # OAuth 토큰이 존재하고 취소된 경우
    if oauth_token and oauth_token.revoked_at is not None:
        logger.warning(f"Token for user {user_id} has been revoked")
        raise credentials_exception
    
    # 사용자 조회
    user = get_user_by_id(db, user_id)
    if user is None:
        logger.warning(f"User not found for ID: {user_id}")
        raise credentials_exception
        
    logger.info(f"Successfully authenticated user: {user.id}")
    return user

def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Access Token으로부터 현재 사용자 정보 조회 (선택적)
    인증되지 않은 경우 None을 반환하고 예외를 발생시키지 않음
    OAuth 토큰 취소 상태도 확인함
    """
    try:
        # Request에서 토큰 추출
        token = extract_token_from_request(request)
        
        if not token or token.strip() == "":
            return None
            
        # Bearer 접두사 제거
        if token.startswith("Bearer "):
            token = token[7:]
        elif token.startswith("bearer "):
            token = token[7:]
        
        # 토큰 세그먼트 확인
        token_parts = token.split('.')
        if len(token_parts) != 3:
            return None
            
        # JWT 디코딩 및 검증
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        
        # 토큰 타입 확인
        if payload.get("type") != "access":
            return None
            
        # 사용자 ID 추출
        user_id = payload.get("user_id") or payload.get("sub")
        if not user_id:
            return None
            
        # OAuth 토큰 취소 상태 확인
        # OAuth 테이블에 토큰이 저장되어 있는 경우 취소 여부 확인
        from sqlalchemy import text
        token_hash = generate_token_hash(token)
        result = db.execute(
            text("""
                SELECT revoked_at FROM oauth_access_tokens 
                WHERE token_hash = :token_hash
                LIMIT 1
            """),
            {"token_hash": token_hash}
        )
        oauth_token = result.first()
        
        # OAuth 토큰이 존재하고 취소된 경우
        if oauth_token and oauth_token.revoked_at is not None:
            logger.info(f"Token for user {user_id} has been revoked")
            return None
            
        # 데이터베이스에서 사용자 조회
        user = get_user_by_id(db, user_id)
        if not user:
            return None
            
        # 사용자 활성 상태 확인
        if not user.is_active:
            return None
            
        return user
        
    except Exception as e:
        # 정상적인 시나리오이므로 로깅하지 않음 (토큰이 없거나 만료됨)
        return None

def get_current_user_with_groups(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Access Token으로부터 현재 사용자 정보와 그룹 정보를 함께 조회"""
    user = get_current_user(request, token, db)
    
    # 토큰에서 그룹 정보 추출
    if not token:
        token = extract_token_from_request(request)
    
    if token:
        if token.startswith("Bearer "):
            token = token[7:]
        elif token.startswith("bearer "):
            token = token[7:]
        
        user_info = extract_user_info_from_token(token)
        if user_info:
            return {
                "user": user,
                "user_id": user_info["user_id"],
                "group_id": user_info["group_id"],
                "group_name": user_info["group_name"],
                "role_id": user_info["role_id"],
                "role_name": user_info["role_name"],
                "is_admin": user_info["is_admin"]
            }
    
    # 토큰에서 정보를 가져올 수 없는 경우 DB에서 조회
    return {
        "user": user,
        "user_id": str(user.id),
        "group_id": str(user.group.id) if user.group else None,
        "group_name": user.group.name if user.group else None,
        "role_id": str(user.role.id) if user.role else None,
        "role_name": user.role.name if user.role else None,
        "is_admin": user.is_admin
    }

def get_current_user_optional_with_token(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """선택적 사용자 인증 (토큰이 없어도 에러를 발생시키지 않음) - OAuth 토큰 취소 상태 확인 포함"""
    try:
        return get_current_user(request, token, db)
    except HTTPException:
        return None

def get_current_user_silent(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Silent 사용자 인증 - OAuth authorization 엔드포인트용
    토큰이 없을 때 경고를 로그하지 않고 조용히 None을 반환
    실제 토큰 검증 오류(형식 오류, 만료 등)만 로그에 기록
    """
    try:
        # Request에서 토큰 추출
        token = extract_token_from_request(request)
        
        if not token or token.strip() == "":
            # 토큰이 없는 것은 OAuth authorization 엔드포인트에서 정상적임
            return None
            
        # Bearer 접두사 제거
        if token.startswith("Bearer "):
            token = token[7:]
        elif token.startswith("bearer "):
            token = token[7:]
        
        # 토큰 세그먼트 확인
        token_parts = token.split('.')
        if len(token_parts) != 3:
            logger.warning(f"Invalid token format: expected 3 segments, got {len(token_parts)}")
            return None
            
        # JWT 디코딩 및 검증
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        
        # 토큰 타입 확인
        if payload.get("type") != "access":
            logger.warning(f"Invalid token type: {payload.get('type')}")
            return None
            
        # 사용자 ID 추출
        user_id = payload.get("user_id") or payload.get("sub")
        if not user_id:
            logger.warning("No user ID in token payload")
            return None
            
        # 데이터베이스에서 사용자 조회
        user = get_user_by_id(db, user_id)
        if not user:
            logger.warning(f"User not found for ID: {user_id}")
            return None
            
        # 사용자 활성 상태 확인
        if not user.is_active:
            logger.warning(f"User {user_id} is not active")
            return None
            
        return user
        
    except JWTError as e:
        # JWT 관련 오류만 로그 (실제 토큰 검증 오류)
        logger.warning(f"JWT verification failed: {e}")
        return None
    except Exception as e:
        # 기타 예외는 디버그 레벨로 로그
        logger.debug(f"Silent token validation failed: {e}")
        return None


def get_current_user_with_redis_session(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    OAuth authorization 엔드포인트용 하이브리드 인증
    1단계: JWT 토큰 검증 (기존 방식)
    2단계: Redis 세션 검증 (새로운 방식)
    
    이 함수는 JWT 토큰과 Redis 세션을 모두 확인하여
    OAuth SSO 플로우에서 일관된 인증 상태를 보장합니다.
    """
    try:
        # 1단계: 기존 JWT 토큰 검증 시도
        jwt_user = get_current_user_silent(request, db)
        if jwt_user:
            logger.debug(f"✅ User authenticated via JWT token: {jwt_user.email}")
            return jwt_user
        
        # 2단계: Redis 세션 검증 시도 (로그인 후 access_token 쿠키가 없는 경우)
        try:
            from ..core.oauth_redis_integration import get_oauth_session_from_request
            
            # Redis 세션에서 사용자 정보 추출
            session_data = get_oauth_session_from_request(request)
            
            if session_data:
                # 세션에서 사용자 ID 추출
                user_id = session_data.get('user_id') or session_data.get('id')
                
                if user_id:
                    # 데이터베이스에서 사용자 조회
                    user = get_user_by_id(db, user_id)
                    
                    if user and user.is_active:
                        logger.info(f"✅ User authenticated via Redis session: {user.email} (session upgrade)")
                        return user
                    else:
                        logger.warning(f"⚠️ User not found or inactive from Redis session: {user_id}")
                else:
                    logger.debug("🔍 No user_id in Redis session data")
            else:
                logger.debug("🔍 No Redis session found")
        
        except Exception as e:
            logger.debug(f"🔍 Redis session validation failed (non-critical): {e}")
            # Redis 세션 검증 실패는 OAuth 플로우를 방해하지 않음
        
        # 3단계: 두 방법 모두 실패한 경우 None 반환 (정상적인 OAuth 시나리오)
        logger.debug("🔍 No authentication found (JWT or Redis) - proceeding with OAuth flow")
        return None
        
    except Exception as e:
        # 예외 발생 시에도 OAuth 플로우 계속 진행
        logger.debug(f"🔍 Hybrid authentication failed: {e}")
        return None


def get_current_user_from_token(token: str, db: Session) -> Optional[User]:
    """
    토큰 문자열로부터 직접 사용자 조회
    OAuth logout 엔드포인트에서 쿠키 토큰 검증용
    
    Args:
        token: JWT 토큰 문자열
        db: 데이터베이스 세션
    
    Returns:
        User 객체 또는 None
    """
    try:
        # Bearer 접두사 제거
        if token.startswith("Bearer "):
            token = token[7:]
        
        # 토큰 검증 및 사용자 ID 추출
        user_id = verify_token(token)
        
        if not user_id:
            return None
        
        # 데이터베이스에서 사용자 조회
        user = get_user_by_id(db, user_id)
        
        if user and user.is_active:
            logger.debug(f"✅ User validated from token: {user.email}")
            return user
        else:
            logger.debug(f"User not found or inactive: {user_id}")
            return None
            
    except Exception as e:
        logger.debug(f"Token validation failed: {e}")
        return None


def verify_service_token(token: str, required_scopes: Optional[list] = None) -> Dict[str, Any]:
    """
    서비스 토큰 검증 (Client Credentials Grant용)
    
    Args:
        token: JWT 서비스 토큰
        required_scopes: 필요한 스코프 목록
    
    Returns:
        토큰 정보 딕셔너리 또는 None
    """
    try:
        # JWT 디코딩 및 검증
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        
        # 서비스 토큰 확인
        token_type = payload.get("token_type")
        if token_type != "service":
            logger.warning(f"Invalid token type for service verification: {token_type}")
            return None
        
        # 토큰 만료 확인
        exp = payload.get("exp")
        if exp and datetime.utcnow().timestamp() > exp:
            logger.debug("Service token has expired")
            return None
        
        # 클라이언트 정보 추출
        client_id = payload.get("client_id")
        if not client_id:
            logger.warning("No client_id in service token")
            return None
        
        # 스코프 검증
        token_scopes = payload.get("scope", "").split()
        if required_scopes:
            missing_scopes = [scope for scope in required_scopes if scope not in token_scopes]
            if missing_scopes:
                logger.warning(f"Missing required scopes for service token: {missing_scopes}")
                return None
        
        service_info = {
            "client_id": client_id,
            "scopes": token_scopes,
            "token_type": "service",
            "sub": payload.get("sub"),
            "iss": payload.get("iss"),
            "exp": exp,
            "jti": payload.get("jti")
        }
        
        # 성공적인 서비스 토큰 검증 로그
        log_auth_event(
            event_type="service_token_verification",
            user_id=f"service:{client_id}",
            success=True,
            additional_data={
                "client_id": client_id,
                "scopes": token_scopes,
                "jti": payload.get("jti")
            }
        )
        
        return service_info
        
    except JWTError as e:
        logger.warning(f"Service token verification failed: {e}")
        log_auth_event(
            event_type="service_token_verification",
            success=False,
            error=f"JWT decode error: {str(e)}"
        )
        return None
    except Exception as e:
        logger.warning(f"Service token verification error: {e}")
        log_auth_event(
            event_type="service_token_verification",
            success=False,
            error=f"Verification error: {str(e)}"
        )
        return None


def get_current_service(
    request: Request,
    required_scopes: Optional[list] = None,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    현재 서비스 정보 조회 (서비스 토큰 기반)
    
    Args:
        request: FastAPI Request 객체
        required_scopes: 필요한 스코프 목록
        db: 데이터베이스 세션
    
    Returns:
        서비스 정보 딕셔너리
    
    Raises:
        HTTPException: 인증 실패 시
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate service credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 토큰 추출
        token = extract_token_from_request(request)
        
        if not token or token.strip() == "":
            logger.warning("No service token provided")
            raise credentials_exception
        
        # Bearer 접두사 제거
        if token.startswith("Bearer "):
            token = token[7:]
        elif token.startswith("bearer "):
            token = token[7:]
        
        # 서비스 토큰 검증
        service_info = verify_service_token(token, required_scopes)
        if not service_info:
            logger.warning("Service token verification failed")
            raise credentials_exception
        
        # 클라이언트가 데이터베이스에 존재하고 활성화되어 있는지 확인
        from sqlalchemy import text
        result = db.execute(
            text("SELECT is_active, is_confidential FROM oauth_clients WHERE client_id = :client_id"),
            {"client_id": service_info["client_id"]}
        )
        client = result.first()
        
        if not client or not client.is_active or not client.is_confidential:
            logger.warning(f"Invalid or inactive service client: {service_info['client_id']}")
            raise credentials_exception
        
        logger.info(f"Successfully authenticated service: {service_info['client_id']}")
        return service_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Service authentication failed: {e}")
        raise credentials_exception


def require_service_auth(required_scopes: Optional[list] = None):
    """
    서비스 인증 데코레이터
    
    Args:
        required_scopes: 필요한 스코프 목록
    
    Returns:
        서비스 정보를 반환하는 Depends 함수
    """
    def _get_service(
        request: Request,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        return get_current_service(request, required_scopes, db)
    
    return Depends(_get_service)