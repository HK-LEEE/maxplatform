"""
Groups API Router
사용자 토큰으로 접근 가능한 그룹 관련 API
OAuth 표준을 준수하여 사용자가 자신의 토큰으로 그룹 정보 조회 가능
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text, and_, or_
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from ..database import get_db
from ..models import User, Group
from ..utils.auth import get_current_user, get_current_user_with_groups
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/groups", tags=["Groups API"])


# Pydantic models
class GroupSearchResponse(BaseModel):
    id: str
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    member_count: int = 0
    
    class Config:
        from_attributes = True


class GroupDetailResponse(BaseModel):
    id: str
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    member_count: int = 0
    members: Optional[List[dict]] = None  # 멤버 정보 (권한에 따라)
    
    class Config:
        from_attributes = True


class MyGroupResponse(BaseModel):
    id: str
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    member_count: int = 0
    my_role: Optional[str] = None
    joined_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


def check_group_access_permission(user: User, group_id: str) -> bool:
    """
    그룹 정보 접근 권한 확인
    - 관리자는 모든 그룹 접근 가능
    - 그룹 멤버는 자신이 속한 그룹 접근 가능
    - 활성화된 그룹만 일반 검색 가능
    """
    # 관리자 권한
    if user.is_admin:
        return True
    
    # 자신이 속한 그룹
    if user.group_id and str(user.group_id) == group_id:
        return True
    
    return False


@router.get("/search")
def search_groups(
    name: Optional[str] = Query(None, description="그룹명으로 검색"),
    display_name: Optional[str] = Query(None, description="표시명으로 검색"),
    limit: int = Query(10, ge=1, le=50, description="결과 제한"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[GroupSearchResponse]:
    """
    그룹 검색 API (사용자 토큰으로 접근)
    
    - 관리자는 모든 그룹 검색 가능
    - 일반 사용자는 활성화된 그룹만 검색 가능
    """
    try:
        if not name and not display_name:
            raise HTTPException(status_code=400, detail="name 또는 display_name 파라미터가 필요합니다")
        
        # 기본 쿼리
        query = db.query(Group)
        
        # 관리자가 아니면 활성화된 그룹만
        if not current_user.is_admin:
            query = query.filter(Group.is_active == True)
        
        # 검색 조건 추가
        if name:
            query = query.filter(Group.name.ilike(f"%{name}%"))
        
        if display_name:
            query = query.filter(Group.display_name.ilike(f"%{display_name}%"))
        
        groups = query.limit(limit).all()
        
        results = []
        for group in groups:
            # 멤버 수 조회
            member_count = db.query(User).filter(
                User.group_id == group.id,
                User.is_active == True,
                User.approval_status == 'approved'
            ).count()
            
            results.append(GroupSearchResponse(
                id=str(group.id),
                name=group.name,
                display_name=group.display_name,
                description=group.description,
                is_active=group.is_active,
                member_count=member_count
            ))
        
        logger.info(f"User {current_user.email} searched groups with name='{name}', display_name='{display_name}', found {len(results)} results")
        
        return results
        
    except Exception as e:
        logger.error(f"Error searching groups: {str(e)}")
        raise HTTPException(status_code=500, detail="그룹 검색 중 오류가 발생했습니다")


@router.get("/my")
def get_my_group(
    current_user_info: dict = Depends(get_current_user_with_groups),
    db: Session = Depends(get_db)
) -> Optional[MyGroupResponse]:
    """
    현재 사용자가 속한 그룹 정보 조회
    """
    try:
        user = current_user_info["user"]
        
        if not user.group_id:
            return None
        
        group = db.query(Group).filter(Group.id == user.group_id).first()
        
        if not group:
            return None
        
        # 멤버 수 조회
        member_count = db.query(User).filter(
            User.group_id == group.id,
            User.is_active == True,
            User.approval_status == 'approved'
        ).count()
        
        response = MyGroupResponse(
            id=str(group.id),
            name=group.name,
            display_name=group.display_name,
            description=group.description,
            is_active=group.is_active,
            member_count=member_count,
            my_role=current_user_info.get("role_name"),
            joined_at=user.created_at  # 그룹 가입일은 사용자 생성일로 대체
        )
        
        logger.info(f"User {user.email} accessed their group info: {group.name}")
        return response
        
    except Exception as e:
        logger.error(f"Error getting user's group: {str(e)}")
        raise HTTPException(status_code=500, detail="내 그룹 정보 조회 중 오류가 발생했습니다")


@router.get("/{group_id}")
def get_group_detail(
    group_id: str,
    include_members: bool = Query(False, description="멤버 목록 포함 여부"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> GroupDetailResponse:
    """
    특정 그룹 상세 정보 조회
    - 관리자는 모든 그룹 정보 접근 가능
    - 그룹 멤버는 자신이 속한 그룹의 상세 정보 접근 가능
    - 일반 사용자는 활성화된 그룹의 기본 정보만 접근 가능
    """
    try:
        # 그룹 조회
        group = db.query(Group).filter(Group.id == group_id).first()
        
        if not group:
            raise HTTPException(status_code=404, detail="그룹을 찾을 수 없습니다")
        
        # 접근 권한 확인
        has_full_access = check_group_access_permission(current_user, group_id)
        
        # 일반 사용자는 활성화된 그룹만 접근 가능
        if not has_full_access and not group.is_active:
            raise HTTPException(status_code=403, detail="해당 그룹 정보에 접근할 권한이 없습니다")
        
        # 멤버 수 조회
        member_count = db.query(User).filter(
            User.group_id == group.id,
            User.is_active == True,
            User.approval_status == 'approved'
        ).count()
        
        # 멤버 목록 조회 (권한이 있고 요청한 경우만)
        members = None
        if include_members and has_full_access:
            member_query = db.query(User).options(joinedload(User.role)).filter(
                User.group_id == group.id,
                User.is_active == True,
                User.approval_status == 'approved'
            ).all()
            
            members = []
            for member in member_query:
                members.append({
                    "id": str(member.id),
                    "email": member.email,
                    "real_name": member.real_name,
                    "display_name": member.display_name,
                    "department": member.department,
                    "position": member.position,
                    "role_name": member.role.name if member.role else None,
                    "is_admin": member.is_admin,
                    "created_at": member.created_at.isoformat() if member.created_at else None
                })
        
        response = GroupDetailResponse(
            id=str(group.id),
            name=group.name,
            display_name=group.display_name,
            description=group.description,
            is_active=group.is_active,
            created_at=group.created_at,
            updated_at=group.updated_at,
            member_count=member_count,
            members=members
        )
        
        logger.info(f"User {current_user.email} accessed group detail: {group.name} (include_members={include_members})")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting group detail: {str(e)}")
        raise HTTPException(status_code=500, detail="그룹 상세 정보 조회 중 오류가 발생했습니다")


@router.get("/name/{group_name}")
def get_group_by_name(
    group_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> GroupSearchResponse:
    """
    그룹명으로 그룹 정보 조회 (정확히 일치)
    MAX Lab에서 그룹명 → 그룹 정보 변환 시 사용
    """
    try:
        # 그룹명으로 검색 (정확히 일치)
        group = db.query(Group).filter(Group.name == group_name).first()
        
        if not group:
            raise HTTPException(status_code=404, detail="해당 이름의 그룹을 찾을 수 없습니다")
        
        # 일반 사용자는 활성화된 그룹만 접근 가능
        if not current_user.is_admin and not group.is_active:
            raise HTTPException(status_code=403, detail="해당 그룹 정보에 접근할 권한이 없습니다")
        
        # 멤버 수 조회
        member_count = db.query(User).filter(
            User.group_id == group.id,
            User.is_active == True,
            User.approval_status == 'approved'
        ).count()
        
        response = GroupSearchResponse(
            id=str(group.id),
            name=group.name,
            display_name=group.display_name,
            description=group.description,
            is_active=group.is_active,
            member_count=member_count
        )
        
        logger.info(f"User {current_user.email} looked up group by name: {group_name}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting group by name: {str(e)}")
        raise HTTPException(status_code=500, detail="그룹명으로 그룹 조회 중 오류가 발생했습니다")


@router.get("/{group_id}/members")
def get_group_members(
    group_id: str,
    limit: int = Query(50, ge=1, le=100, description="결과 제한"),
    skip: int = Query(0, ge=0, description="건너뛸 개수"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[dict]:
    """
    그룹 멤버 목록 조회
    - 관리자는 모든 그룹의 멤버 조회 가능
    - 그룹 멤버는 자신이 속한 그룹의 멤버 조회 가능
    """
    try:
        # 그룹 존재 확인
        group = db.query(Group).filter(Group.id == group_id).first()
        
        if not group:
            raise HTTPException(status_code=404, detail="그룹을 찾을 수 없습니다")
        
        # 접근 권한 확인
        if not check_group_access_permission(current_user, group_id):
            raise HTTPException(status_code=403, detail="해당 그룹의 멤버 목록에 접근할 권한이 없습니다")
        
        # 멤버 목록 조회
        members = db.query(User).options(joinedload(User.role)).filter(
            User.group_id == group.id,
            User.is_active == True,
            User.approval_status == 'approved'
        ).offset(skip).limit(limit).all()
        
        results = []
        for member in members:
            results.append({
                "id": str(member.id),
                "email": member.email,
                "real_name": member.real_name,
                "display_name": member.display_name,
                "department": member.department,
                "position": member.position,
                "role_id": str(member.role.id) if member.role else None,
                "role_name": member.role.name if member.role else None,
                "is_admin": member.is_admin,
                "created_at": member.created_at.isoformat() if member.created_at else None,
                "last_login_at": member.last_login_at.isoformat() if member.last_login_at else None
            })
        
        logger.info(f"User {current_user.email} accessed members of group {group.name} (skip={skip}, limit={limit})")
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting group members: {str(e)}")
        raise HTTPException(status_code=500, detail="그룹 멤버 목록 조회 중 오류가 발생했습니다")