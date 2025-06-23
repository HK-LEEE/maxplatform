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

logger = logging.getLogger(__name__)

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

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """JWT 액세스 토큰 생성"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire, "type": "access", "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
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
            return None
        return username
    except JWTError as e:
        logger.warning(f"Token verification failed: {e}")
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
        
        # 토큰 만료 확인
        exp = payload.get("exp")
        if exp and datetime.utcnow().timestamp() > exp:
            logger.warning("Token has expired")
            raise credentials_exception
            
        user_id: str = payload.get("sub")
        if user_id is None:
            logger.warning("No user ID in token payload")
            raise credentials_exception
            
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Unexpected error in token validation: {e}")
        raise credentials_exception
    
    # 사용자 조회
    user = get_user_by_id(db, user_id)
    if user is None:
        logger.warning(f"User not found for ID: {user_id}")
        raise credentials_exception
        
    logger.info(f"Successfully authenticated user: {user.id}")
    return user

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

def get_current_user_optional(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """선택적 사용자 인증 (토큰이 없어도 에러를 발생시키지 않음)"""
    try:
        return get_current_user(request, token, db)
    except HTTPException:
        return None 