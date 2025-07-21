"""
User API Router
사용자 토큰으로 접근 가능한 사용자 관련 API
OAuth 표준을 준수하여 사용자가 자신의 토큰으로 정보 조회 가능
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text, and_, or_
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

from ..database import get_db
from ..models import User, Group
from ..utils.auth import get_current_user, get_current_user_with_groups
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["Users API"])


# Pydantic models
class UserSearchResponse(BaseModel):
    id: str
    email: str
    real_name: str
    display_name: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    is_active: bool
    group_id: Optional[str] = None
    group_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class UserProfileResponse(BaseModel):
    id: str
    email: str
    real_name: str
    display_name: Optional[str] = None
    phone_number: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    bio: Optional[str] = None
    is_active: bool
    is_admin: bool
    approval_status: str
    created_at: datetime
    last_login_at: Optional[datetime] = None
    login_count: int = 0
    group_id: Optional[str] = None
    group_name: Optional[str] = None
    role_id: Optional[str] = None
    role_name: Optional[str] = None
    
    class Config:
        from_attributes = True


def check_user_access_permission(requesting_user: User, target_user_id: str) -> bool:
    """
    사용자 정보 접근 권한 확인
    - 본인 정보는 항상 접근 가능
    - 관리자는 모든 사용자 정보 접근 가능
    - 같은 그룹 멤버는 제한적 정보 접근 가능
    """
    # 본인 정보 접근
    if str(requesting_user.id) == target_user_id:
        return True
    
    # 관리자 권한
    if requesting_user.is_admin:
        return True
    
    # 같은 그룹 멤버 (선택적 구현)
    # if requesting_user.group_id and target_user.group_id == requesting_user.group_id:
    #     return True
    
    return False


@router.get("/search")
def search_users(
    email: Optional[str] = Query(None, description="이메일로 사용자 검색"),
    name: Optional[str] = Query(None, description="이름으로 사용자 검색"),
    limit: int = Query(10, ge=1, le=50, description="결과 제한"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[UserSearchResponse]:
    """
    사용자 검색 API (사용자 토큰으로 접근)
    
    - 본인 정보는 항상 검색 가능
    - 관리자는 모든 사용자 검색 가능
    - 일반 사용자는 활성화된 사용자만 검색 가능 (제한된 정보)
    """
    try:
        if not email and not name:
            raise HTTPException(status_code=400, detail="email 또는 name 파라미터가 필요합니다")
        
        # 기본 쿼리 (활성 사용자만)
        query = db.query(User).options(joinedload(User.group))
        
        # 관리자가 아니면 승인되고 활성화된 사용자만
        if not current_user.is_admin:
            query = query.filter(
                User.is_active == True,
                User.approval_status == 'approved'
            )
        
        # 검색 조건 추가
        if email:
            query = query.filter(User.email.ilike(f"%{email}%"))
        
        if name:
            query = query.filter(
                or_(
                    User.real_name.ilike(f"%{name}%"),
                    User.display_name.ilike(f"%{name}%")
                )
            )
        
        users = query.limit(limit).all()
        
        results = []
        for user in users:
            # 접근 권한 확인 (관리자이거나 본인이거나 같은 그룹)
            if (current_user.is_admin or 
                str(user.id) == str(current_user.id) or
                (current_user.group_id and user.group_id == current_user.group_id)):
                
                results.append(UserSearchResponse(
                    id=str(user.id),
                    email=user.email,
                    real_name=user.real_name,
                    display_name=user.display_name,
                    department=user.department,
                    position=user.position,
                    is_active=user.is_active,
                    group_id=str(user.group.id) if user.group else None,
                    group_name=user.group.name if user.group else None
                ))
            else:
                # 제한된 정보만 제공
                results.append(UserSearchResponse(
                    id=str(user.id),
                    email=user.email,
                    real_name=user.real_name,
                    display_name=user.display_name,
                    department=None,  # 민감 정보 제외
                    position=None,    # 민감 정보 제외
                    is_active=user.is_active,
                    group_id=None,    # 민감 정보 제외
                    group_name=None   # 민감 정보 제외
                ))
        
        logger.info(f"User {current_user.email} searched users with email='{email}', name='{name}', found {len(results)} results")
        
        return results
        
    except Exception as e:
        logger.error(f"Error searching users: {str(e)}")
        raise HTTPException(status_code=500, detail="사용자 검색 중 오류가 발생했습니다")


@router.get("/me")
def get_my_profile(
    current_user_info: dict = Depends(get_current_user_with_groups),
    db: Session = Depends(get_db)
) -> UserProfileResponse:
    """
    현재 사용자 프로필 조회 (상세 정보)
    /api/auth/me와 유사하지만 더 상세한 정보 제공
    """
    try:
        user = current_user_info["user"]
        
        response = UserProfileResponse(
            id=str(user.id),
            email=user.email,
            real_name=user.real_name,
            display_name=user.display_name,
            phone_number=user.phone_number,
            department=user.department,
            position=user.position,
            bio=user.bio,
            is_active=user.is_active,
            is_admin=user.is_admin,
            approval_status=user.approval_status,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
            login_count=user.login_count or 0,
            group_id=current_user_info.get("group_id"),
            group_name=current_user_info.get("group_name"),
            role_id=current_user_info.get("role_id"),
            role_name=current_user_info.get("role_name")
        )
        
        logger.info(f"User {user.email} accessed their profile")
        return response
        
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        raise HTTPException(status_code=500, detail="프로필 조회 중 오류가 발생했습니다")


@router.get("/{user_id}")
def get_user_profile(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserProfileResponse:
    """
    특정 사용자 프로필 조회
    - 본인 정보는 항상 접근 가능
    - 관리자는 모든 사용자 정보 접근 가능
    - 일반 사용자는 같은 그룹 멤버의 제한된 정보만 접근 가능
    """
    try:
        # 대상 사용자 조회
        target_user = db.query(User).options(
            joinedload(User.group),
            joinedload(User.role)
        ).filter(User.id == user_id).first()
        
        if not target_user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
        
        # 접근 권한 확인
        if not check_user_access_permission(current_user, user_id):
            # 같은 그룹이면 제한된 정보 제공
            if (current_user.group_id and 
                target_user.group_id == current_user.group_id and
                target_user.is_active and 
                target_user.approval_status == 'approved'):
                
                # 제한된 정보만 반환
                return UserProfileResponse(
                    id=str(target_user.id),
                    email=target_user.email,
                    real_name=target_user.real_name,
                    display_name=target_user.display_name,
                    phone_number=None,  # 민감 정보 제외
                    department=target_user.department,
                    position=target_user.position,
                    bio=None,  # 민감 정보 제외
                    is_active=target_user.is_active,
                    is_admin=False,  # 민감 정보 제외
                    approval_status=target_user.approval_status,
                    created_at=target_user.created_at,
                    last_login_at=None,  # 민감 정보 제외
                    login_count=0,  # 민감 정보 제외
                    group_id=str(target_user.group.id) if target_user.group else None,
                    group_name=target_user.group.name if target_user.group else None,
                    role_id=None,  # 민감 정보 제외
                    role_name=None   # 민감 정보 제외
                )
            else:
                raise HTTPException(status_code=403, detail="해당 사용자 정보에 접근할 권한이 없습니다")
        
        # 전체 정보 반환 (본인이거나 관리자)
        response = UserProfileResponse(
            id=str(target_user.id),
            email=target_user.email,
            real_name=target_user.real_name,
            display_name=target_user.display_name,
            phone_number=target_user.phone_number,
            department=target_user.department,
            position=target_user.position,
            bio=target_user.bio,
            is_active=target_user.is_active,
            is_admin=target_user.is_admin,
            approval_status=target_user.approval_status,
            created_at=target_user.created_at,
            last_login_at=target_user.last_login_at,
            login_count=target_user.login_count or 0,
            group_id=str(target_user.group.id) if target_user.group else None,
            group_name=target_user.group.name if target_user.group else None,
            role_id=str(target_user.role.id) if target_user.role else None,
            role_name=target_user.role.name if target_user.role else None
        )
        
        logger.info(f"User {current_user.email} accessed profile of user {target_user.email}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        raise HTTPException(status_code=500, detail="사용자 프로필 조회 중 오류가 발생했습니다")


@router.get("/email/{email}")
def get_user_by_email(
    email: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserSearchResponse:
    """
    이메일로 사용자 정보 조회 (UUID 매핑용)
    MAX Lab에서 이메일 → UUID 변환 시 사용
    """
    try:
        # 이메일로 사용자 검색
        target_user = db.query(User).options(joinedload(User.group)).filter(
            User.email == email,
            User.is_active == True,
            User.approval_status == 'approved'
        ).first()
        
        if not target_user:
            raise HTTPException(status_code=404, detail="해당 이메일의 사용자를 찾을 수 없습니다")
        
        # 접근 권한 확인
        can_access_full_info = (
            current_user.is_admin or 
            str(target_user.id) == str(current_user.id) or
            (current_user.group_id and target_user.group_id == current_user.group_id)
        )
        
        if can_access_full_info:
            response = UserSearchResponse(
                id=str(target_user.id),
                email=target_user.email,
                real_name=target_user.real_name,
                display_name=target_user.display_name,
                department=target_user.department,
                position=target_user.position,
                is_active=target_user.is_active,
                group_id=str(target_user.group.id) if target_user.group else None,
                group_name=target_user.group.name if target_user.group else None
            )
        else:
            # 제한된 정보만 제공
            response = UserSearchResponse(
                id=str(target_user.id),
                email=target_user.email,
                real_name=target_user.real_name,
                display_name=target_user.display_name,
                department=None,
                position=None,
                is_active=target_user.is_active,
                group_id=None,
                group_name=None
            )
        
        logger.info(f"User {current_user.email} looked up user by email: {email}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user by email: {str(e)}")
        raise HTTPException(status_code=500, detail="이메일로 사용자 조회 중 오류가 발생했습니다")