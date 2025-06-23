from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from sqlalchemy.sql import text

from ..database import get_db
from ..services.flow_studio_service import FlowStudioService
from ..schemas.flow_studio import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    FlowCreate, FlowUpdate, FlowResponse, FlowSaveRequest,
    ComponentTemplateCreate, ComponentTemplateResponse,
    FlowStudioStats, FlowPublishRequest, FlowPublishResponse
)
from ..utils.auth import get_current_user, get_current_user_with_groups
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/flow-studio", tags=["Flow Studio"])

def get_flow_studio_service(db: Session = Depends(get_db)) -> FlowStudioService:
    """Flow Studio 서비스 의존성 주입"""
    return FlowStudioService(db)

# ==================== Project 관련 엔드포인트 ====================

@router.get("/projects", response_model=List[ProjectResponse])
async def get_projects(
    request: Request,
    skip: int = Query(0, ge=0, description="건너뛸 항목 수"),
    limit: int = Query(100, ge=1, le=1000, description="가져올 항목 수"),
    service: FlowStudioService = Depends(get_flow_studio_service),
    user_info = Depends(get_current_user_with_groups)
):
    """사용자의 프로젝트 목록 조회 (권한 기반)"""
    try:
        projects = await service.get_projects(
            user_info=user_info,
            skip=skip,
            limit=limit
        )
        return projects
    except Exception as e:
        logger.error(f"프로젝트 목록 조회 API 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="프로젝트 목록을 가져오는 중 오류가 발생했습니다."
        )

@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    request: Request,
    service: FlowStudioService = Depends(get_flow_studio_service),
    user_info = Depends(get_current_user_with_groups)
):
    """특정 프로젝트 조회 (권한 확인)"""
    try:
        project = await service.get_project_by_id(project_id, user_info)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="프로젝트를 찾을 수 없거나 접근 권한이 없습니다."
            )
        return project
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"프로젝트 조회 API 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="프로젝트 조회 중 오류가 발생했습니다."
        )

@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    request: Request,
    service: FlowStudioService = Depends(get_flow_studio_service),
    user_info = Depends(get_current_user_with_groups)
):
    """새 프로젝트 생성 (개인/그룹 권한 지원)"""
    try:
        project = await service.create_project(user_info, project_data)
        return project
    except ValueError as e:
        logger.warning(f"프로젝트 생성 권한 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"프로젝트 생성 API 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="프로젝트 생성 중 오류가 발생했습니다."
        )

@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    request: Request,
    service: FlowStudioService = Depends(get_flow_studio_service),
    user_info = Depends(get_current_user_with_groups)
):
    """프로젝트 수정 (권한 확인)"""
    try:
        project = await service.update_project(project_id, user_info, project_data)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="프로젝트를 찾을 수 없거나 수정 권한이 없습니다."
            )
        return project
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"프로젝트 수정 API 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="프로젝트 수정 중 오류가 발생했습니다."
        )

@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    request: Request,
    service: FlowStudioService = Depends(get_flow_studio_service),
    user_info = Depends(get_current_user_with_groups)
):
    """프로젝트 삭제 (권한 확인)"""
    try:
        success = await service.delete_project(project_id, user_info)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="프로젝트를 찾을 수 없거나 삭제 권한이 없습니다."
            )
        return
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"프로젝트 삭제 API 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="프로젝트 삭제 중 오류가 발생했습니다."
        )

# ==================== Flow 관련 엔드포인트 ====================

@router.get("/projects/{project_id}/flows", response_model=List[FlowResponse])
async def get_flows(
    project_id: str,
    request: Request,
    skip: int = Query(0, ge=0, description="건너뛸 항목 수"),
    limit: int = Query(100, ge=1, le=1000, description="가져올 항목 수"),
    service: FlowStudioService = Depends(get_flow_studio_service),
    user_info = Depends(get_current_user_with_groups)
):
    """프로젝트의 플로우 목록 조회 (권한 확인)"""
    try:
        flows = await service.get_flows(
            project_id=project_id,
            user_info=user_info,
            skip=skip,
            limit=limit
        )
        return flows
    except Exception as e:
        logger.error(f"플로우 목록 조회 API 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="플로우 목록을 가져오는 중 오류가 발생했습니다."
        )

@router.get("/flows/{flow_id}", response_model=FlowResponse)
async def get_flow(
    flow_id: str,
    request: Request,
    service: FlowStudioService = Depends(get_flow_studio_service),
    user_info = Depends(get_current_user_with_groups)
):
    """특정 플로우 조회 (권한 확인)"""
    try:
        flow = await service.get_flow_by_id(flow_id, user_info)
        if not flow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="플로우를 찾을 수 없거나 접근 권한이 없습니다."
            )
        return flow
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"플로우 조회 API 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="플로우 조회 중 오류가 발생했습니다."
        )

@router.post("/flows", response_model=FlowResponse, status_code=status.HTTP_201_CREATED)
async def create_flow(
    flow_data: FlowCreate,
    request: Request,
    service: FlowStudioService = Depends(get_flow_studio_service),
    user_info = Depends(get_current_user_with_groups)
):
    """새 플로우 생성 (권한 확인)"""
    try:
        flow = await service.create_flow(user_info, flow_data)
        if not flow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="프로젝트를 찾을 수 없거나 플로우 생성 권한이 없습니다."
            )
        return flow
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"플로우 생성 API 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="플로우 생성 중 오류가 발생했습니다."
        )

@router.put("/flows/{flow_id}", response_model=FlowResponse)
async def update_flow(
    flow_id: str,
    flow_data: FlowUpdate,
    request: Request,
    service: FlowStudioService = Depends(get_flow_studio_service),
    user_info = Depends(get_current_user_with_groups)
):
    """플로우 수정 (권한 확인)"""
    try:
        flow = await service.update_flow(flow_id, user_info, flow_data)
        if not flow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="플로우를 찾을 수 없거나 수정 권한이 없습니다."
            )
        return flow
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"플로우 수정 API 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="플로우 수정 중 오류가 발생했습니다."
        )

@router.delete("/flows/{flow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flow(
    flow_id: str,
    request: Request,
    service: FlowStudioService = Depends(get_flow_studio_service),
    user_info = Depends(get_current_user_with_groups)
):
    """플로우 삭제 (권한 확인)"""
    try:
        success = await service.delete_flow(flow_id, user_info)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="플로우를 찾을 수 없거나 삭제 권한이 없습니다."
            )
        return
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"플로우 삭제 API 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="플로우 삭제 중 오류가 발생했습니다."
        )

@router.post("/flows/save", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def save_flow(
    save_request: FlowSaveRequest,
    request: Request,
    service: FlowStudioService = Depends(get_flow_studio_service),
    user_info = Depends(get_current_user_with_groups)
):
    """플로우 저장 (프로젝트 자동 생성 포함, 권한 기능 지원)"""
    try:
        result = await service.save_flow_with_project(user_info, save_request)
        return result
    except ValueError as e:
        logger.warning(f"플로우 저장 권한 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"플로우 저장 API 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="플로우 저장 중 오류가 발생했습니다."
        )

# ==================== Component Template 관련 엔드포인트 ====================

@router.get("/component-templates", response_model=List[ComponentTemplateResponse])
async def get_component_templates(
    request: Request,
    category: Optional[str] = Query(None, description="컴포넌트 카테고리 필터"),
    skip: int = Query(0, ge=0, description="건너뛸 항목 수"),
    limit: int = Query(100, ge=1, le=1000, description="가져올 항목 수"),
    service: FlowStudioService = Depends(get_flow_studio_service)
):
    """컴포넌트 템플릿 목록 조회 (공용 리소스)"""
    try:
        templates = await service.get_component_templates(
            category=category,
            skip=skip,
            limit=limit
        )
        return templates
    except Exception as e:
        logger.error(f"컴포넌트 템플릿 목록 조회 API 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="컴포넌트 템플릿 목록을 가져오는 중 오류가 발생했습니다."
        )

@router.post("/component-templates", response_model=ComponentTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_component_template(
    template_data: ComponentTemplateCreate,
    request: Request,
    service: FlowStudioService = Depends(get_flow_studio_service),
    current_user = Depends(get_current_user)
):
    """컴포넌트 템플릿 생성 (관리자 권한 필요)"""
    try:
        # 관리자 권한 확인
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="컴포넌트 템플릿 생성 권한이 없습니다."
            )
        
        template = await service.create_component_template(template_data)
        return template
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"컴포넌트 템플릿 생성 API 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="컴포넌트 템플릿 생성 중 오류가 발생했습니다."
        )

# ==================== RAG 데이터소스 관련 엔드포인트 ====================

@router.get("/rag-datasources", response_model=List[Dict[str, Any]])
async def get_accessible_rag_datasources(
    request: Request,
    service: FlowStudioService = Depends(get_flow_studio_service),
    user_info = Depends(get_current_user_with_groups)
):
    """사용자가 접근 가능한 RAG 데이터소스 목록 조회 (권한 기반)"""
    try:
        datasources = await service.get_accessible_rag_datasources(user_info)
        return datasources
    except Exception as e:
        logger.error(f"RAG 데이터소스 목록 조회 API 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RAG 데이터소스 목록을 가져오는 중 오류가 발생했습니다."
        )

# ==================== 통계 관련 엔드포인트 ====================

@router.get("/stats", response_model=FlowStudioStats)
async def get_flow_studio_stats(
    request: Request,
    service: FlowStudioService = Depends(get_flow_studio_service),
    user_info = Depends(get_current_user_with_groups)
):
    """Flow Studio 통계 조회 (권한 기반)"""
    try:
        stats = await service.get_flow_studio_stats(user_info)
        return stats
    except Exception as e:
        logger.error(f"Flow Studio 통계 조회 API 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="통계 정보를 가져오는 중 오류가 발생했습니다."
        )

# ==================== Publish 관련 엔드포인트 ====================

@router.post("/flows/{flow_id}/publish", response_model=FlowPublishResponse, status_code=status.HTTP_201_CREATED)
async def publish_flow(
    flow_id: str,
    publish_request: FlowPublishRequest,
    request: Request,
    service: FlowStudioService = Depends(get_flow_studio_service),
    user_info = Depends(get_current_user_with_groups)
):
    """플로우 배포 (LLMOps 시스템 연동)"""
    try:
        result = await service.publish_flow(flow_id, user_info, publish_request)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="플로우를 찾을 수 없거나 배포 권한이 없습니다."
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"플로우 배포 API 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="플로우 배포 중 오류가 발생했습니다."
        )

@router.post("/flows/{flow_id}/unpublish", status_code=status.HTTP_204_NO_CONTENT)
async def unpublish_flow(
    flow_id: str,
    request: Request,
    service: FlowStudioService = Depends(get_flow_studio_service),
    user_info = Depends(get_current_user_with_groups)
):
    """플로우 배포 해제 (DEPRECATED 상태로 변경)"""
    try:
        success = await service.unpublish_flow(flow_id, user_info)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="플로우를 찾을 수 없거나 배포 해제 권한이 없습니다."
            )
        return
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"플로우 배포 해제 API 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="플로우 배포 해제 중 오류가 발생했습니다."
        )

@router.get("/flows/{flow_id}/publish-history")
async def get_publish_history(
    flow_id: str,
    request: Request,
    skip: int = Query(0, ge=0, description="건너뛸 항목 수"),
    limit: int = Query(20, ge=1, le=100, description="가져올 항목 수"),
    service: FlowStudioService = Depends(get_flow_studio_service),
    user_info = Depends(get_current_user_with_groups)
):
    """플로우 배포 이력 조회"""
    try:
        history = await service.get_publish_history(
            flow_id=flow_id,
            user_info=user_info,
            skip=skip,
            limit=limit
        )
        
        # 응답 형식으로 변환
        result = []
        for record in history:
            result.append({
                "id": record.id,
                "version": record.version,
                "publish_status": record.publish_status.value,
                "published_by": record.published_by,
                "publish_message": record.publish_message,
                "target_environment": record.target_environment,
                "webhook_called": record.webhook_called,
                "webhook_response": record.webhook_response,
                "published_at": record.published_at,
                "deprecated_at": record.deprecated_at
            })
        
        return {
            "flow_id": flow_id,
            "total_count": len(result),
            "history": result
        }
    except Exception as e:
        logger.error(f"플로우 배포 이력 조회 API 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="플로우 배포 이력을 가져오는 중 오류가 발생했습니다."
        )

 