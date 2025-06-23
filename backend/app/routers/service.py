from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models.user import User
from ..schemas.service import (
    ServiceCreate, ServiceUpdate, ServiceResponse,
    MotherPageResponse, ServicePermissionCreate,
    UserAccessibleService, ServiceCategoryResponse
)
from ..services.service_service import ServiceService
from .auth import get_current_user, get_current_admin_user

router = APIRouter(prefix="/api/services", tags=["services"])

@router.get("/mother-page", response_model=MotherPageResponse)
async def get_mother_page_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mother 페이지 데이터 조회"""
    try:
        return ServiceService.get_mother_page_data(db, current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 오류가 발생했습니다."
        )

@router.get("/accessible", response_model=List[UserAccessibleService])
async def get_user_accessible_services(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """현재 사용자가 접근 가능한 서비스 목록 조회"""
    return ServiceService.get_user_accessible_services(db, current_user.id)

@router.get("/categories", response_model=List[ServiceCategoryResponse])
async def get_service_categories(db: Session = Depends(get_db)):
    """서비스 카테고리 목록 조회"""
    return ServiceService.get_service_categories(db)

@router.get("/", response_model=List[ServiceResponse])
async def get_all_services(
    include_inactive: bool = False,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """모든 서비스 목록 조회 (관리자 전용)"""
    return ServiceService.get_all_services(db, include_inactive)

@router.get("/{service_id}", response_model=ServiceResponse)
async def get_service(
    service_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """서비스 상세 조회 (관리자 전용)"""
    service = ServiceService.get_service_by_id(db, service_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="서비스를 찾을 수 없습니다."
        )
    return service

@router.post("/", response_model=ServiceResponse)
async def create_service(
    service_data: ServiceCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """새 서비스 생성 (관리자 전용)"""
    # 중복 서비스명 확인
    existing_service = ServiceService.get_service_by_name(db, service_data.name)
    if existing_service:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 존재하는 서비스명입니다."
        )
    
    return ServiceService.create_service(db, service_data, current_user.id)

@router.put("/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: int,
    service_data: ServiceUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """서비스 정보 업데이트 (관리자 전용)"""
    updated_service = ServiceService.update_service(db, service_id, service_data)
    if not updated_service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="서비스를 찾을 수 없습니다."
        )
    return updated_service

@router.delete("/{service_id}")
async def delete_service(
    service_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """서비스 삭제 (관리자 전용)"""
    success = ServiceService.delete_service(db, service_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="서비스를 찾을 수 없습니다."
        )
    return {"message": "서비스가 성공적으로 삭제되었습니다."}

@router.post("/permissions/grant")
async def grant_service_permission(
    user_id: str,
    service_id: int,
    permission_level: str = "read",
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """사용자에게 서비스 권한 부여 (관리자 전용)"""
    success = ServiceService.grant_service_permission(
        db, user_id, service_id, current_user.id, permission_level
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="권한 부여에 실패했습니다."
        )
    return {"message": "권한이 성공적으로 부여되었습니다."}

@router.delete("/permissions/revoke")
async def revoke_service_permission(
    user_id: str,
    service_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """사용자의 서비스 권한 회수 (관리자 전용)"""
    success = ServiceService.revoke_service_permission(db, user_id, service_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="권한 회수에 실패했습니다."
        )
    return {"message": "권한이 성공적으로 회수되었습니다."}

@router.get("/check-access/{service_name}")
async def check_service_access(
    service_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자의 특정 서비스 접근 권한 확인"""
    has_access = ServiceService.check_user_service_access(
        db, current_user.id, service_name
    )
    return {
        "service_name": service_name,
        "has_access": has_access,
        "user_id": current_user.id
    } 