"""
LLM 모델 관리 API
모델 권한 시스템을 포함한 LLM 모델 관리 기능
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID

from ..database import get_db
from ..models.llm_chat import MAXLLM_Model, MAXLLM_Model_Permission, ModelType, OwnerType
from ..models.user import User, Group
from ..routers.auth import get_current_user

router = APIRouter(prefix="/api/llm-models", tags=["LLM Models"])

# Pydantic 모델들
class ModelPermissionCreate(BaseModel):
    model_id: str
    grantee_type: OwnerType
    grantee_id: str

class ModelPermissionResponse(BaseModel):
    id: str
    model_id: str
    grantee_type: OwnerType
    grantee_id: str
    grantee_name: Optional[str] = None
    granted_by: str
    granted_by_name: Optional[str] = None
    created_at: str
    updated_at: str

class ModelResponse(BaseModel):
    id: str
    model_name: str
    model_type: ModelType
    model_id: str
    description: Optional[str] = None
    owner_type: OwnerType
    owner_id: str
    owner_name: Optional[str] = None
    is_active: bool
    created_at: str
    updated_at: str
    permissions_count: int = 0
    has_permission: bool = False

class ModelCreate(BaseModel):
    model_name: str
    model_type: ModelType
    model_id: str
    description: Optional[str] = None
    config: dict
    owner_type: OwnerType = OwnerType.USER
    owner_id: Optional[str] = None

class ModelUpdate(BaseModel):
    model_name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[dict] = None
    is_active: Optional[bool] = None

# 권한 확인 헬퍼 함수들
def _check_model_access(db: Session, model: MAXLLM_Model, user_id: str) -> bool:
    """사용자가 특정 모델에 접근 권한이 있는지 확인"""
    # 모델 소유자인 경우
    if model.owner_type == OwnerType.USER and model.owner_id == user_id:
        return True
    
    # 사용자 그룹 조회
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    
    # 그룹 소유 모델인 경우
    if model.owner_type == OwnerType.GROUP and user.group_id and str(user.group_id) == model.owner_id:
        return True
    
    # 직접 권한 부여된 경우
    user_permission = db.query(MAXLLM_Model_Permission).filter(
        and_(
            MAXLLM_Model_Permission.model_id == model.id,
            MAXLLM_Model_Permission.grantee_type == OwnerType.USER,
            MAXLLM_Model_Permission.grantee_id == user_id
        )
    ).first()
    
    if user_permission:
        return True
    
    # 그룹 권한이 있는 경우
    if user.group_id:
        group_permission = db.query(MAXLLM_Model_Permission).filter(
            and_(
                MAXLLM_Model_Permission.model_id == model.id,
                MAXLLM_Model_Permission.grantee_type == OwnerType.GROUP,
                MAXLLM_Model_Permission.grantee_id == str(user.group_id)
            )
        ).first()
        
        if group_permission:
            return True
    
    return False

def _check_model_manage_permission(db: Session, model: MAXLLM_Model, user_id: str) -> bool:
    """사용자가 특정 모델을 관리할 권한이 있는지 확인"""
    # 모델 소유자이거나 관리자인 경우
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    
    # 관리자는 모든 모델 관리 가능
    if user.is_superuser:
        return True
    
    # 모델 소유자인 경우
    if model.owner_type == OwnerType.USER and model.owner_id == user_id:
        return True
    
    # 그룹 소유 모델이고 해당 그룹의 구성원인 경우
    if model.owner_type == OwnerType.GROUP and user.group_id and str(user.group_id) == model.owner_id:
        return True
    
    return False

def _get_user_accessible_models(db: Session, user_id: str):
    """사용자가 접근 가능한 모델 목록 조회"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return []
    
    # 기본 쿼리: 활성화된 모델들
    base_query = db.query(MAXLLM_Model).filter(MAXLLM_Model.is_active == True)
    
    # 접근 가능한 모델 조건들
    access_conditions = []
    
    # 1. 사용자 소유 모델
    access_conditions.append(
        and_(
            MAXLLM_Model.owner_type == OwnerType.USER,
            MAXLLM_Model.owner_id == user_id
        )
    )
    
    # 2. 사용자 그룹 소유 모델
    if user.group_id:
        access_conditions.append(
            and_(
                MAXLLM_Model.owner_type == OwnerType.GROUP,
                MAXLLM_Model.owner_id == str(user.group_id)
            )
        )
    
    # 3. 직접 권한이 부여된 모델
    user_permission_subquery = db.query(MAXLLM_Model_Permission.model_id).filter(
        and_(
            MAXLLM_Model_Permission.grantee_type == OwnerType.USER,
            MAXLLM_Model_Permission.grantee_id == user_id
        )
    ).subquery()
    
    access_conditions.append(MAXLLM_Model.id.in_(user_permission_subquery))
    
    # 4. 그룹 권한이 부여된 모델
    if user.group_id:
        group_permission_subquery = db.query(MAXLLM_Model_Permission.model_id).filter(
            and_(
                MAXLLM_Model_Permission.grantee_type == OwnerType.GROUP,
                MAXLLM_Model_Permission.grantee_id == str(user.group_id)
            )
        ).subquery()
        
        access_conditions.append(MAXLLM_Model.id.in_(group_permission_subquery))
    
    # 조건들을 OR로 결합
    return base_query.filter(or_(*access_conditions))

# API 엔드포인트들
@router.get("/", response_model=List[ModelResponse])
async def get_models(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    accessible_only: bool = Query(False, description="사용자가 접근 가능한 모델만 조회")
):
    """LLM 모델 목록 조회"""
    try:
        if accessible_only:
            # 사용자가 접근 가능한 모델만 조회
            query = _get_user_accessible_models(db, str(current_user.id))
        else:
            # 관리자는 모든 모델, 일반 사용자는 접근 가능한 모델만
            if current_user.is_superuser:
                query = db.query(MAXLLM_Model)
            else:
                query = _get_user_accessible_models(db, str(current_user.id))
        
        models = query.all()
        
        result = []
        for model in models:
            # 권한 개수 계산
            permissions_count = db.query(MAXLLM_Model_Permission).filter(
                MAXLLM_Model_Permission.model_id == model.id
            ).count()
            
            # 사용자 접근 권한 확인
            has_permission = _check_model_access(db, model, str(current_user.id))
            
            # 소유자 이름 조회
            owner_name = None
            if model.owner_type == OwnerType.USER:
                owner = db.query(User).filter(User.id == model.owner_id).first()
                owner_name = owner.full_name if owner else model.owner_id
            elif model.owner_type == OwnerType.GROUP:
                owner = db.query(Group).filter(Group.id == model.owner_id).first()
                owner_name = owner.name if owner else model.owner_id
            
            result.append(ModelResponse(
                id=model.id,
                model_name=model.model_name,
                model_type=model.model_type,
                model_id=model.model_id,
                description=model.description,
                owner_type=model.owner_type,
                owner_id=model.owner_id,
                owner_name=owner_name,
                is_active=model.is_active,
                created_at=model.created_at.isoformat(),
                updated_at=model.updated_at.isoformat(),
                permissions_count=permissions_count,
                has_permission=has_permission
            ))
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"모델 목록 조회 실패: {str(e)}"
        )

@router.get("/accessible", response_model=List[ModelResponse])
async def get_accessible_models(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자가 접근 가능한 모델 목록 조회 (채팅에서 사용)"""
    try:
        query = _get_user_accessible_models(db, str(current_user.id))
        models = query.all()
        
        result = []
        for model in models:
            result.append(ModelResponse(
                id=model.id,
                model_name=model.model_name,
                model_type=model.model_type,
                model_id=model.model_id,
                description=model.description,
                owner_type=model.owner_type,
                owner_id=model.owner_id,
                is_active=model.is_active,
                created_at=model.created_at.isoformat(),
                updated_at=model.updated_at.isoformat(),
                has_permission=True
            ))
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"접근 가능한 모델 조회 실패: {str(e)}"
        )

@router.get("/{model_id}/permissions", response_model=List[ModelPermissionResponse])
async def get_model_permissions(
    model_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """특정 모델의 권한 목록 조회"""
    try:
        # 모델 존재 확인
        model = db.query(MAXLLM_Model).filter(MAXLLM_Model.id == model_id).first()
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="모델을 찾을 수 없습니다"
            )
        
        # 관리 권한 확인
        if not _check_model_manage_permission(db, model, str(current_user.id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="모델 권한을 조회할 권한이 없습니다"
            )
        
        permissions = db.query(MAXLLM_Model_Permission).filter(
            MAXLLM_Model_Permission.model_id == model_id
        ).all()
        
        result = []
        for permission in permissions:
            # 권한 부여자 이름 조회
            granter = db.query(User).filter(User.id == permission.granted_by).first()
            granted_by_name = granter.full_name if granter else str(permission.granted_by)
            
            # 권한 대상자 이름 조회
            grantee_name = None
            if permission.grantee_type == OwnerType.USER:
                grantee = db.query(User).filter(User.id == permission.grantee_id).first()
                grantee_name = grantee.full_name if grantee else permission.grantee_id
            elif permission.grantee_type == OwnerType.GROUP:
                grantee = db.query(Group).filter(Group.id == permission.grantee_id).first()
                grantee_name = grantee.name if grantee else permission.grantee_id
            
            result.append(ModelPermissionResponse(
                id=permission.id,
                model_id=permission.model_id,
                grantee_type=permission.grantee_type,
                grantee_id=permission.grantee_id,
                grantee_name=grantee_name,
                granted_by=str(permission.granted_by),
                granted_by_name=granted_by_name,
                created_at=permission.created_at.isoformat(),
                updated_at=permission.updated_at.isoformat()
            ))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"권한 목록 조회 실패: {str(e)}"
        )

@router.post("/{model_id}/permissions", response_model=ModelPermissionResponse)
async def grant_model_permission(
    model_id: str,
    permission_data: ModelPermissionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """모델 사용 권한 부여"""
    try:
        # 모델 존재 확인
        model = db.query(MAXLLM_Model).filter(MAXLLM_Model.id == model_id).first()
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="모델을 찾을 수 없습니다"
            )
        
        # 관리 권한 확인
        if not _check_model_manage_permission(db, model, str(current_user.id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="모델 권한을 부여할 권한이 없습니다"
            )
        
        # 권한 대상자 존재 확인
        if permission_data.grantee_type == OwnerType.USER:
            grantee = db.query(User).filter(User.id == permission_data.grantee_id).first()
            if not grantee:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="사용자를 찾을 수 없습니다"
                )
        elif permission_data.grantee_type == OwnerType.GROUP:
            grantee = db.query(Group).filter(Group.id == permission_data.grantee_id).first()
            if not grantee:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="그룹을 찾을 수 없습니다"
                )
        
        # 중복 권한 확인
        existing_permission = db.query(MAXLLM_Model_Permission).filter(
            and_(
                MAXLLM_Model_Permission.model_id == model_id,
                MAXLLM_Model_Permission.grantee_type == permission_data.grantee_type,
                MAXLLM_Model_Permission.grantee_id == permission_data.grantee_id
            )
        ).first()
        
        if existing_permission:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 권한이 부여되어 있습니다"
            )
        
        # 권한 생성
        new_permission = MAXLLM_Model_Permission(
            model_id=model_id,
            grantee_type=permission_data.grantee_type,
            grantee_id=permission_data.grantee_id,
            granted_by=current_user.id
        )
        
        db.add(new_permission)
        db.commit()
        db.refresh(new_permission)
        
        # 응답 데이터 구성
        grantee_name = None
        if permission_data.grantee_type == OwnerType.USER:
            grantee_name = grantee.full_name
        elif permission_data.grantee_type == OwnerType.GROUP:
            grantee_name = grantee.name
        
        return ModelPermissionResponse(
            id=new_permission.id,
            model_id=new_permission.model_id,
            grantee_type=new_permission.grantee_type,
            grantee_id=new_permission.grantee_id,
            grantee_name=grantee_name,
            granted_by=str(new_permission.granted_by),
            granted_by_name=current_user.full_name,
            created_at=new_permission.created_at.isoformat(),
            updated_at=new_permission.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"권한 부여 실패: {str(e)}"
        )

@router.delete("/{model_id}/permissions/{permission_id}")
async def revoke_model_permission(
    model_id: str,
    permission_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """모델 사용 권한 취소"""
    try:
        # 모델 존재 확인
        model = db.query(MAXLLM_Model).filter(MAXLLM_Model.id == model_id).first()
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="모델을 찾을 수 없습니다"
            )
        
        # 관리 권한 확인
        if not _check_model_manage_permission(db, model, str(current_user.id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="모델 권한을 취소할 권한이 없습니다"
            )
        
        # 권한 존재 확인
        permission = db.query(MAXLLM_Model_Permission).filter(
            and_(
                MAXLLM_Model_Permission.id == permission_id,
                MAXLLM_Model_Permission.model_id == model_id
            )
        ).first()
        
        if not permission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="권한을 찾을 수 없습니다"
            )
        
        # 권한 삭제
        db.delete(permission)
        db.commit()
        
        return {"message": "권한이 성공적으로 취소되었습니다"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"권한 취소 실패: {str(e)}"
        )

@router.get("/admin/permissions/matrix")
async def get_permissions_matrix(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """권한 매트릭스를 위한 모든 권한 정보 조회"""
    try:
        # 관리자 권한 확인
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="관리자 권한이 필요합니다"
            )
        
        # 모든 권한 조회
        permissions = db.query(MAXLLM_Model_Permission).all()
        
        permission_data = []
        for permission in permissions:
            # 권한 대상자 이름 조회
            grantee_name = None
            if permission.grantee_type == OwnerType.USER:
                grantee = db.query(User).filter(User.id == permission.grantee_id).first()
                grantee_name = grantee.real_name if grantee else "Unknown User"
            elif permission.grantee_type == OwnerType.GROUP:
                grantee = db.query(Group).filter(Group.id == permission.grantee_id).first()
                grantee_name = grantee.name if grantee else "Unknown Group"
            
            permission_data.append({
                "id": permission.id,
                "model_id": permission.model_id,
                "grantee_type": permission.grantee_type.value,
                "grantee_id": permission.grantee_id,
                "grantee_name": grantee_name,
                "granted_by": permission.granted_by,
                "created_at": permission.created_at.isoformat() if permission.created_at else None
            })
        
        return permission_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"권한 매트릭스 조회 중 오류가 발생했습니다: {str(e)}"
        )