"""
그룹 및 사용자 트리 구조 API
그룹 계층구조와 그룹 내 사용자 정보를 트리 형태로 제공
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID

from ..database import get_db
from ..models.user import User, Group
from ..routers.auth import get_current_user

router = APIRouter(prefix="/api/admin/tree", tags=["Group Tree"])

# Pydantic 모델들
class UserTreeNode(BaseModel):
    id: str
    type: str = "user"
    name: str
    display_name: Optional[str] = None
    email: str
    is_active: bool
    is_admin: bool
    department: Optional[str] = None
    position: Optional[str] = None
    last_login_at: Optional[str] = None

class GroupTreeNode(BaseModel):
    id: str
    type: str = "group"
    name: str
    description: Optional[str] = None
    users_count: int
    created_at: str
    users: List[UserTreeNode] = []

class TreeResponse(BaseModel):
    groups: List[GroupTreeNode]
    total_groups: int
    total_users: int

@router.get("/groups", response_model=TreeResponse)
async def get_group_tree(
    include_users: bool = True,
    group_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    그룹 트리 구조 조회
    
    Args:
        include_users: 그룹 내 사용자 정보 포함 여부
        group_id: 특정 그룹만 조회할 경우 그룹 ID
    """
    try:
        # 관리자 권한 확인
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="관리자 권한이 필요합니다"
            )
        
        # 그룹 쿼리 구성
        groups_query = db.query(Group)
        
        if group_id:
            # 특정 그룹만 조회
            groups_query = groups_query.filter(Group.id == group_id)
        
        # 그룹 목록 조회 (사용자 수와 함께)
        groups = groups_query.all()
        
        group_tree_nodes = []
        total_users = 0
        
        for group in groups:
            # 그룹별 사용자 수 조회
            users_count = db.query(func.count(User.id)).filter(User.group_id == group.id).scalar()
            total_users += users_count
            
            # 그룹 노드 생성
            group_node = GroupTreeNode(
                id=str(group.id),
                name=group.name,
                description=group.description,
                users_count=users_count,
                created_at=group.created_at.isoformat() if group.created_at else "",
                users=[]
            )
            
            # 사용자 정보 포함 요청 시
            if include_users:
                users = db.query(User).filter(User.group_id == group.id).all()
                
                for user in users:
                    user_node = UserTreeNode(
                        id=str(user.id),
                        name=user.real_name,
                        display_name=user.display_name,
                        email=user.email,
                        is_active=user.is_active,
                        is_admin=user.is_admin,
                        department=user.department,
                        position=user.position,
                        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None
                    )
                    group_node.users.append(user_node)
            
            group_tree_nodes.append(group_node)
        
        return TreeResponse(
            groups=group_tree_nodes,
            total_groups=len(group_tree_nodes),
            total_users=total_users
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"트리 데이터 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/groups/{group_id}/users", response_model=List[UserTreeNode])
async def get_group_users(
    group_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    특정 그룹의 사용자 목록 조회
    """
    try:
        # 관리자 권한 확인
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="관리자 권한이 필요합니다"
            )
        
        # 그룹 존재 확인
        group = db.query(Group).filter(Group.id == group_id).first()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="그룹을 찾을 수 없습니다"
            )
        
        # 그룹 내 사용자 조회
        users = db.query(User).filter(User.group_id == group_id).all()
        
        user_nodes = []
        for user in users:
            user_node = UserTreeNode(
                id=str(user.id),
                name=user.real_name,
                display_name=user.display_name,
                email=user.email,
                is_active=user.is_active,
                is_admin=user.is_admin,
                department=user.department,
                position=user.position,
                last_login_at=user.last_login_at.isoformat() if user.last_login_at else None
            )
            user_nodes.append(user_node)
        
        return user_nodes
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"그룹 사용자 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/users/{user_id}/permissions")
async def get_user_permissions_summary(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    특정 사용자의 권한 요약 정보 조회
    """
    try:
        # 관리자 권한 확인
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="관리자 권한이 필요합니다"
            )
        
        # 사용자 존재 확인
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다"
            )
        
        # 사용자 권한 정보 구성
        permissions_summary = {
            "user_id": str(user.id),
            "user_name": user.real_name,
            "email": user.email,
            "group_id": str(user.group_id) if user.group_id else None,
            "group_name": user.group.name if user.group else None,
            "is_admin": user.is_admin,
            "is_active": user.is_active,
            "features": [],
            "llm_models": []
        }
        
        # 그룹 기능 권한 조회
        if user.group:
            # 그룹에 할당된 기능들
            group_features = []
            for feature in user.group.features:
                group_features.append({
                    "id": feature.id,
                    "name": feature.name,
                    "display_name": feature.display_name,
                    "category": feature.category,
                    "source": "group"
                })
            permissions_summary["features"] = group_features
        
        # LLM 모델 권한 조회 (향후 구현)
        # TODO: MAXLLM_Model_Permission을 통한 모델 권한 조회
        
        return permissions_summary
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"사용자 권한 조회 중 오류가 발생했습니다: {str(e)}"
        )