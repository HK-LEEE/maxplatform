from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Union
from passlib.context import CryptContext
from passlib.hash import bcrypt
from jose import JWTError, jwt
from datetime import datetime, timedelta
import json
import re
import os
import logging
from dotenv import load_dotenv
from sqlalchemy.sql import func
import uuid as uuid_module
from sqlalchemy.dialects.postgresql import UUID

from ..database import get_db
from ..models import User, Role, Group, Permission, Feature, RefreshToken
from ..config import settings
from ..utils.auth import get_current_user, verify_password, get_password_hash, create_access_token, create_refresh_token
# Import Redis session management for OAuth SSO consistency
from ..core.oauth_redis_integration import get_oauth_redis_manager, set_oauth_session_cookies
from ..core.redis_session import create_user_session

# 환경변수 로드
load_dotenv()

# 로거 설정
logger = logging.getLogger(__name__)

router = APIRouter()

# 비밀번호 해싱 - bcrypt 호환성 개선
try:
    # bcrypt 버전 호환성을 위한 설정
    pwd_context = CryptContext(
        schemes=["bcrypt"], 
        deprecated="auto",
        bcrypt__rounds=12,
        bcrypt__ident="2b"  # bcrypt 식별자 명시
    )
    
    # 테스트 해싱으로 bcrypt 작동 확인
    test_hash = pwd_context.hash("test")
    pwd_context.verify("test", test_hash)
    logger.info("bcrypt 해싱 시스템 정상 작동 확인")
    
except Exception as e:
    logger.warning(f"bcrypt 설정 실패, 대체 방법 사용: {e}")
    # 대체 방법: 직접 bcrypt 사용
    class PasswordContext:
        @staticmethod
        def verify(plain_password: str, hashed_password: str) -> bool:
            try:
                return bcrypt.verify(plain_password, hashed_password)
            except Exception as e:
                logger.error(f"비밀번호 검증 실패: {e}")
                return False
        
        @staticmethod
        def hash(password: str) -> str:
            try:
                return bcrypt.hash(password, rounds=12)
            except Exception as e:
                logger.error(f"비밀번호 해싱 실패: {e}")
                # 최후의 수단: 간단한 해싱 (개발용)
                import hashlib
                return hashlib.sha256(password.encode()).hexdigest()
    
    pwd_context = PasswordContext()

# OAuth2 스키마
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

# Pydantic 모델들
class UserCreate(BaseModel):
    real_name: str  # 실제 이름
    display_name: str = None  # 표시명 (선택사항)
    email: EmailStr
    phone_number: str
    password: str
    department: str = None  # 부서 (선택사항)
    position: str = None  # 직책 (선택사항)
    group_id: str = None  # 그룹 ID (선택사항)
    requested_permissions: List[int] = []  # 요청하는 권한 ID 목록
    requested_features: List[int] = []  # 요청하는 기능 ID 목록

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class PasswordReset(BaseModel):
    email: EmailStr
    phone_last_digits: str

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class AvailableGroup(BaseModel):
    id: str
    name: str
    description: str = None

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: dict

class TokenRefresh(BaseModel):
    refresh_token: str

class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class UserResponse(BaseModel):
    id: str  # UUID
    real_name: str
    display_name: str = None
    email: str
    phone_number: str = None
    department: str = None
    position: str = None
    is_active: bool
    is_admin: bool
    is_verified: bool
    created_at: datetime
    last_login_at: datetime = None
    login_count: int
    roles: list = []
    groups: list = []

    class Config:
        from_attributes = True

# 유틸리티 함수들 - utils.auth에서 가져온 함수들 사용
def validate_phone_number(phone: str) -> bool:
    """휴대폰 번호 유효성 검사"""
    pattern = r'^01[016789]-?\d{3,4}-?\d{4}$'
    return bool(re.match(pattern, phone.replace('-', '').replace(' ', '')))

def generate_default_password(phone_last_digits: str) -> str:
    """휴대폰 뒷자리로 기본 패스워드 생성"""
    return f"temp{phone_last_digits}!"

def store_refresh_token(
    db: Session, 
    user_id, 
    refresh_token: str, 
    expires_at: datetime, 
    request: Request = None
):
    """Refresh Token을 데이터베이스에 저장"""
    # user_id가 UUID 객체인 경우 그대로 사용, 문자열인 경우 변환
    if isinstance(user_id, str):
        try:
            user_uuid = uuid_module.UUID(user_id)
        except ValueError:
            raise ValueError(f"Invalid UUID format: {user_id}")
    else:
        user_uuid = user_id
    
    # 기존 활성 토큰 무효화 (선택적)
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_uuid,
        RefreshToken.is_active == True
    ).update({"is_active": False})
    
    # 새 토큰 저장
    token_record = RefreshToken(
        token=refresh_token,
        user_id=user_uuid,
        expires_at=expires_at,
        device_info=request.headers.get("user-agent", "") if request else "",
        ip_address=request.client.host if request else "",
        user_agent=request.headers.get("user-agent", "") if request else ""
    )
    
    db.add(token_record)
    db.commit()
    return token_record

def verify_refresh_token(db: Session, refresh_token: str) -> Optional[RefreshToken]:
    """Refresh Token 검증"""
    try:
        # JWT 디코딩
        payload = jwt.decode(refresh_token, settings.secret_key, algorithms=[settings.algorithm])
        
        # 토큰 타입 확인
        if payload.get("type") != "refresh":
            return None
            
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        # 문자열을 UUID 객체로 변환
        try:
            user_uuid = uuid_module.UUID(user_id)
        except ValueError:
            return None
        
        # 데이터베이스에서 토큰 조회
        token_record = db.query(RefreshToken).filter(
            RefreshToken.token == refresh_token,
            RefreshToken.user_id == user_uuid
        ).first()
        
        if not token_record or not token_record.is_valid():
            return None
            
        return token_record
        
    except JWTError:
        return None

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id):
    try:
        # UUID 객체인지 확인하고 적절히 처리
        if isinstance(user_id, uuid_module.UUID):
            uuid_obj = user_id
        else:
            # 문자열을 UUID 객체로 변환
            uuid_obj = uuid_module.UUID(user_id)
        return db.query(User).filter(User.id == uuid_obj).first()
    except (ValueError, TypeError):
        # 유효하지 않은 UUID 형식
        return None

def get_user_by_phone(db: Session, phone: str):
    return db.query(User).filter(User.phone_number == phone).first()

def authenticate_user(db: Session, email: str, password: str):
    """사용자 인증"""
    user = get_user_by_email(db, email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def get_current_admin_user(current_user: User = Depends(get_current_user)):
    """관리자 권한 확인"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다."
        )
    return current_user

# 라우트들
@router.get("/available-groups", response_model=List[AvailableGroup])
async def get_available_groups(db: Session = Depends(get_db)):
    """회원가입 시 선택 가능한 그룹 목록 조회 (인증 불필요)"""
    # 활성화된 그룹만 조회
    groups = db.query(Group).filter(Group.is_active == True).all()
    
    return [
        AvailableGroup(
            id=str(group.id),
            name=group.name,
            description=group.description or ""
        )
        for group in groups
    ]

@router.post("/register", response_model=Token)
async def register(user_data: UserCreate, request: Request, db: Session = Depends(get_db)):
    # 이메일 중복 확인
    if get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 등록된 이메일입니다."
        )
    
    # 휴대폰 번호 유효성 검사
    if not validate_phone_number(user_data.phone_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="올바른 휴대폰 번호 형식이 아닙니다. (예: 010-1234-5678)"
        )
    
    # 휴대폰 번호 중복 확인
    if get_user_by_phone(db, user_data.phone_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 등록된 휴대폰 번호입니다."
        )
    
    # 그룹 유효성 검사 (그룹이 선택된 경우)
    group_uuid = None
    if user_data.group_id:
        # 임시 그룹인 경우 None으로 처리 (나중에 관리자가 배정)
        if user_data.group_id == "temp":
            group_uuid = None
        else:
            try:
                group_uuid = uuid_module.UUID(user_data.group_id)
                group = db.query(Group).filter(
                    Group.id == group_uuid,
                    Group.is_active == True
                ).first()
                if not group:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="유효하지 않은 그룹입니다."
                    )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="올바르지 않은 그룹 ID 형식입니다."
                )
    
    # 사용자 생성
    hashed_password = get_password_hash(user_data.password)
    
    db_user = User(
        real_name=user_data.real_name,
        display_name=user_data.display_name or user_data.real_name,
        email=user_data.email,
        phone_number=user_data.phone_number,
        hashed_password=hashed_password,
        department=user_data.department,
        position=user_data.position,
        group_id=group_uuid,  # 그룹 할당
        is_active=False,  # 비활성화 상태로 시작 (관리자 승인 필요)
        is_verified=False,  # 이메일 인증 필요
        approval_status="pending"  # 관리자 승인 필요
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # JWT 토큰 생성
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    refresh_token_expires = timedelta(days=settings.refresh_token_expire_days)
    
    access_token = create_access_token(
        data={"sub": str(db_user.id)}, 
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data={"sub": str(db_user.id)}
    )
    
    # Refresh Token 저장
    refresh_expires_at = datetime.utcnow() + refresh_token_expires
    store_refresh_token(db, db_user.id, refresh_token, refresh_expires_at, request)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
        "user": {
            "id": str(db_user.id),
            "real_name": db_user.real_name,
            "display_name": db_user.display_name,
            "email": db_user.email,
            "is_admin": db_user.is_admin,
            "is_verified": db_user.is_verified,
            "approval_status": db_user.approval_status
        }
    }

@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, request: Request, response: Response, db: Session = Depends(get_db)):
    """사용자 로그인"""
    try:
        logger.info(f"로그인 시도: {user_data.email}")
        
        # 사용자 인증
        user = authenticate_user(db, user_data.email, user_data.password)
        if not user:
            logger.warning(f"인증 실패: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="이메일 또는 비밀번호가 올바르지 않습니다.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            logger.warning(f"비활성 계정 로그인 시도: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="비활성화된 계정입니다."
            )
        
        logger.info(f"사용자 인증 성공: {user.email} (ID: {user.id})")
        
        # 로그인 기록 업데이트
        try:
            user.last_login_at = datetime.utcnow()
            user.login_count += 1
            db.commit()
            logger.info(f"로그인 기록 업데이트 완료: {user.email}")
        except Exception as e:
            logger.error(f"로그인 기록 업데이트 실패: {e}")
            db.rollback()
            # 계속 진행 (기록 업데이트 실패가 로그인을 막지 않음)
        
        # JWT 토큰 생성 (그룹 정보 포함)
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        refresh_token_expires = timedelta(days=settings.refresh_token_expire_days)
        
        # 토큰에 포함할 데이터 준비
        token_data = {
            "sub": str(user.id),
            "user_id": str(user.id),
            "email": user.email,
            "is_admin": user.is_admin
        }
        
        # 그룹 정보 추가
        if user.group:
            token_data["group_id"] = str(user.group.id)
            token_data["group_name"] = user.group.name
        
        # 역할 정보 추가
        if user.role:
            token_data["role_id"] = str(user.role.id)
            token_data["role_name"] = user.role.name
        
        access_token = create_access_token(
            data=token_data, 
            expires_delta=access_token_expires
        )
        
        refresh_token = create_refresh_token(
            data={"sub": str(user.id)}
        )
        
        logger.info(f"JWT 토큰 생성 완료: {user.email}")
        
        # Refresh Token 저장
        try:
            refresh_expires_at = datetime.utcnow() + refresh_token_expires
            store_refresh_token(db, user.id, refresh_token, refresh_expires_at, request)
            logger.info(f"Refresh Token 저장 완료: {user.email}")
        except Exception as e:
            logger.error(f"Refresh Token 저장 실패: {e}")
            # Refresh Token 저장 실패시에도 로그인 진행
        
        # 🔧 OAuth SSO 일관성을 위한 Redis 세션 생성
        redis_session_created = False
        redis_session_id = None
        try:
            oauth_manager = get_oauth_redis_manager()
            if oauth_manager and oauth_manager.is_redis_available():
                # Redis 세션 데이터 준비
                session_user_data = {
                    "id": str(user.id),
                    "user_id": str(user.id),
                    "email": user.email,
                    "name": user.display_name or user.real_name,
                    "real_name": user.real_name,
                    "display_name": user.display_name,
                    "is_admin": user.is_admin,
                    "login_method": "standard_login"  # OAuth와 구분
                }
                
                # 그룹 정보 추가 (있는 경우)
                if user.group:
                    session_user_data["group_id"] = str(user.group.id)
                    session_user_data["group_name"] = user.group.name
                
                # Redis 세션 생성
                redis_session_id = create_user_session(session_user_data)
                
                if redis_session_id:
                    # 세션 쿠키 설정 (크로스 도메인 OAuth 호환성을 위해)
                    set_oauth_session_cookies(response, redis_session_id, session_user_data)
                    redis_session_created = True
                    logger.info(f"🔒 Redis 세션 및 쿠키 설정 완료: {user.email} (세션 ID: {redis_session_id[:8]}...)")
                else:
                    logger.warning(f"⚠️ Redis 세션 생성 실패: {user.email}")
            else:
                logger.warning(f"⚠️ Redis 세션 매니저 사용 불가: {user.email}")
        except Exception as e:
            logger.error(f"❌ Redis 세션 생성 중 오류: {user.email} - {e}")
            import traceback
            logger.error(f"상세 오류: {traceback.format_exc()}")
            # Redis 세션 실패가 로그인을 방해하지 않도록 계속 진행
        
        logger.info(f"로그인 성공: {user.email} (Redis 세션: {'✅' if redis_session_created else '❌'})")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
            "user": {
                "id": str(user.id),
                "real_name": user.real_name,
                "display_name": user.display_name,
                "email": user.email,
                "is_admin": user.is_admin,
                "is_verified": user.is_verified,
                "approval_status": user.approval_status
            }
        }
        
    except HTTPException:
        # FastAPI HTTPException은 그대로 전달
        raise
    except Exception as e:
        logger.error(f"로그인 처리 중 예상치 못한 오류: {e}")
        import traceback
        logger.error(f"상세 오류: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 내부 오류가 발생했습니다."
        )

@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(token_data: TokenRefresh, db: Session = Depends(get_db)):
    """Refresh Token으로 새로운 Access Token 발급"""
    token_record = verify_refresh_token(db, token_data.refresh_token)
    
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 refresh token입니다."
        )
    
    # 사용자 정보 조회
    user = get_user_by_id(db, token_record.user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 사용자입니다."
        )
    
    # 새로운 Access Token 생성
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)}, 
        expires_delta=access_token_expires
    )
    
    # Refresh Token 사용 기록
    token_record.use()
    db.commit()
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60
    }

@router.post("/logout")
async def logout(
    request: Request,
    refresh_token: str = None, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    로그아웃 - Refresh Token 및 OAuth Access Token 무효화
    
    토큰 블랙리스트 처리:
    1. JWT Refresh Token 무효화
    2. OAuth Access Token 무효화
    3. 관련 세션 종료
    4. 로그아웃 이벤트 로깅
    """
    import hashlib
    from sqlalchemy import text
    
    logout_stats = {
        "refresh_tokens_revoked": 0,
        "oauth_tokens_revoked": 0,
        "sessions_terminated": 0
    }
    
    # 1. JWT Refresh Token 무효화
    if refresh_token:
        # 특정 Refresh Token 무효화
        token_record = db.query(RefreshToken).filter(
            RefreshToken.token == refresh_token,
            RefreshToken.user_id == current_user.id
        ).first()
        
        if token_record:
            token_record.revoke()
            logout_stats["refresh_tokens_revoked"] = 1
    else:
        # 모든 Refresh Token 무효화
        result = db.query(RefreshToken).filter(
            RefreshToken.user_id == current_user.id,
            RefreshToken.is_active == True
        ).update({"is_active": False, "is_revoked": True})
        logout_stats["refresh_tokens_revoked"] = result
    
    # 2. OAuth Access Token 블랙리스트 처리
    # 현재 요청의 access token을 블랙리스트에 추가
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        access_token = auth_header.split(" ")[1]
        token_hash = hashlib.sha256(access_token.encode()).hexdigest()
        
        # OAuth access token 무효화
        try:
            result = db.execute(
                text("""
                    UPDATE oauth_access_tokens 
                    SET revoked_at = NOW(),
                        revocation_reason = 'user_logout'
                    WHERE token_hash = :token_hash 
                    AND user_id = :user_id
                    AND revoked_at IS NULL
                """),
                {
                    "token_hash": token_hash,
                    "user_id": str(current_user.id)
                }
            )
            logout_stats["oauth_tokens_revoked"] += result.rowcount
        except Exception as e:
            logger.warning(f"Failed to revoke OAuth token: {str(e)}")
    
    # 3. 사용자의 모든 OAuth 토큰 무효화 (옵션)
    if not refresh_token:  # 모든 토큰 무효화 요청인 경우
        try:
            result = db.execute(
                text("""
                    UPDATE oauth_access_tokens 
                    SET revoked_at = NOW(),
                        revocation_reason = 'user_logout_all'
                    WHERE user_id = :user_id 
                    AND revoked_at IS NULL
                """),
                {"user_id": str(current_user.id)}
            )
            logout_stats["oauth_tokens_revoked"] += result.rowcount
        except Exception as e:
            logger.warning(f"Failed to revoke all OAuth tokens: {str(e)}")
    
    # 4. 로그아웃 이벤트 로깅
    try:
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent", "")
        
        db.execute(
            text("""
                INSERT INTO oauth_audit_logs 
                (event_type, client_id, user_id, success, ip_address, user_agent, details)
                VALUES ('logout', NULL, :user_id, true, :ip_address, :user_agent, :details)
            """),
            {
                "user_id": str(current_user.id),
                "ip_address": client_ip,
                "user_agent": user_agent,
                "details": f"Logout stats: {logout_stats}"
            }
        )
    except Exception as e:
        logger.warning(f"Failed to log logout event: {str(e)}")
    
    db.commit()
    
    return {
        "message": "성공적으로 로그아웃되었습니다.",
        "stats": logout_stats
    }

@router.post("/revoke-all-tokens")
async def revoke_all_tokens(
    request: Request,
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    모든 기기의 토큰 무효화
    JWT Refresh Token과 OAuth Access Token 모두 블랙리스트 처리
    """
    from sqlalchemy import text
    
    revoke_stats = {
        "refresh_tokens_revoked": 0,
        "oauth_tokens_revoked": 0
    }
    
    # 1. 모든 JWT Refresh Token 무효화
    result = db.query(RefreshToken).filter(
        RefreshToken.user_id == current_user.id
    ).update({
        "is_active": False, 
        "is_revoked": True,
        "revoked_at": func.now()
    })
    revoke_stats["refresh_tokens_revoked"] = result
    
    # 2. 모든 OAuth Access Token 무효화
    try:
        result = db.execute(
            text("""
                UPDATE oauth_access_tokens 
                SET revoked_at = NOW(),
                    revocation_reason = 'revoke_all_tokens'
                WHERE user_id = :user_id 
                AND revoked_at IS NULL
            """),
            {"user_id": str(current_user.id)}
        )
        revoke_stats["oauth_tokens_revoked"] = result.rowcount
    except Exception as e:
        logger.warning(f"Failed to revoke OAuth tokens: {str(e)}")
    
    # 3. 로그아웃 이벤트 로깅
    try:
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent", "")
        
        db.execute(
            text("""
                INSERT INTO oauth_audit_logs 
                (event_type, client_id, user_id, success, ip_address, user_agent, details)
                VALUES ('revoke_all_tokens', NULL, :user_id, true, :ip_address, :user_agent, :details)
            """),
            {
                "user_id": str(current_user.id),
                "ip_address": client_ip,
                "user_agent": user_agent,
                "details": f"Revoked all tokens: {revoke_stats}"
            }
        )
    except Exception as e:
        logger.warning(f"Failed to log revoke event: {str(e)}")
    
    db.commit()
    
    return {
        "message": "모든 기기의 토큰이 무효화되었습니다.",
        "stats": revoke_stats
    }

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    request: Request,
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    # 사용자 정보 반환
    return UserResponse(
        id=str(current_user.id),
        real_name=current_user.real_name,
        display_name=current_user.display_name,
        email=current_user.email,
        phone_number=current_user.phone_number,
        department=current_user.department,
        position=current_user.position,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        last_login_at=current_user.last_login_at,
        login_count=current_user.login_count,
        roles=[],  # TODO: 역할 정보 추가
        groups=[]  # TODO: 그룹 정보 추가
    )

@router.post("/reset-password")
async def reset_password(reset_data: PasswordReset, request: Request, db: Session = Depends(get_db)):
    user = get_user_by_email(db, reset_data.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 이메일의 사용자를 찾을 수 없습니다."
        )
    
    # 휴대폰 뒷자리 확인
    if not user.phone_number or not user.phone_number.endswith(reset_data.phone_last_digits):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="휴대폰 번호 뒷자리가 일치하지 않습니다."
        )
    
    # 임시 비밀번호 생성 및 설정
    temp_password = generate_default_password(reset_data.phone_last_digits)
    user.hashed_password = get_password_hash(temp_password)
    db.commit()
    
    return {
        "message": "임시 비밀번호가 설정되었습니다.",
        "temp_password": temp_password
    }

@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 현재 비밀번호 확인
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 비밀번호가 올바르지 않습니다."
        )
    
    # 새 비밀번호로 변경
    current_user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()
    
    return {"message": "비밀번호가 성공적으로 변경되었습니다."}

@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """현재 사용자 정보 조회"""
    return {
        "id": str(current_user.id),
        "real_name": current_user.real_name,
        "display_name": current_user.display_name,
        "email": current_user.email,
        "phone_number": current_user.phone_number,
        "department": current_user.department,
        "position": current_user.position,
        "bio": current_user.bio,
        "is_active": current_user.is_active,
        "is_admin": current_user.is_admin,
        "approval_status": current_user.approval_status,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "last_login_at": current_user.last_login_at.isoformat() if current_user.last_login_at else None,
        "login_count": current_user.login_count
    } 