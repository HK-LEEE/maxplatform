from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.workspace import WorkspaceCreate, WorkspaceResponse
from ..services.workspace_service import WorkspaceService
from ..services.jupyter_service import jupyter_service
from .auth import get_current_user

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])

@router.get("/health")
async def workspace_health():
    """워크스페이스 라우터 상태 확인"""
    return {"status": "ok", "message": "Workspace router is working"}

@router.post("/", response_model=WorkspaceResponse)
async def create_workspace(
    workspace_data: WorkspaceCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """새 워크스페이스 생성"""
    workspace_service = WorkspaceService(db)
    workspace = workspace_service.create_workspace(workspace_data, current_user)
    return workspace

@router.get("/", response_model=List[WorkspaceResponse])
async def list_workspaces(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자의 워크스페이스 목록 조회"""
    workspace_service = WorkspaceService(db)
    workspaces = workspace_service.get_user_workspaces(current_user.id)
    return workspaces

@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """특정 워크스페이스 정보 조회"""
    workspace_service = WorkspaceService(db)
    workspace = workspace_service.get_workspace_by_id(workspace_id, current_user.id)
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    return workspace

@router.delete("/{workspace_id}")
async def delete_workspace(
    workspace_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """워크스페이스 삭제"""
    workspace_service = WorkspaceService(db)
    success = workspace_service.delete_workspace(workspace_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    return {"message": "Workspace deleted successfully"}

@router.post("/{workspace_id}/start")
async def start_jupyter_lab(
    workspace_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Jupyter Lab 시작"""
    workspace_service = WorkspaceService(db)
    workspace = workspace_service.get_workspace_by_id(workspace_id, current_user.id)
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    try:
        port, token = jupyter_service.start_jupyter_lab(workspace)
        
        # 워크스페이스 정보 업데이트
        workspace_service.update_jupyter_info(workspace_id, port, token)
        
        # Jupyter URL 생성
        jupyter_url = jupyter_service.get_jupyter_url(workspace)
        
        return {
            "message": "Jupyter Lab started successfully",
            "port": port,
            "token": token,
            "url": jupyter_url
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Jupyter Lab 시작 실패: {str(e)}"
        )

@router.post("/{workspace_id}/stop")
async def stop_jupyter_lab(
    workspace_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Jupyter Lab 중지"""
    workspace_service = WorkspaceService(db)
    workspace = workspace_service.get_workspace_by_id(workspace_id, current_user.id)
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    try:
        success = jupyter_service.stop_jupyter_lab(workspace_id)
        
        if success:
            # 워크스페이스 정보 업데이트 (포트와 토큰 제거)
            workspace_service.update_jupyter_info(workspace_id, None, None)
            return {"message": "Jupyter Lab stopped successfully"}
        else:
            return {"message": "Jupyter Lab was not running or could not be stopped"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Jupyter Lab 중지 실패: {str(e)}"
        )

@router.get("/{workspace_id}/status")
async def get_jupyter_status(
    workspace_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Jupyter Lab 실행 상태 확인"""
    workspace_service = WorkspaceService(db)
    workspace = workspace_service.get_workspace_by_id(workspace_id, current_user.id)
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    is_running = jupyter_service.is_process_running(workspace_id)
    jupyter_url = jupyter_service.get_jupyter_url(workspace) if is_running else None
    
    return {
        "workspace_id": workspace_id,
        "is_running": is_running,
        "port": workspace.jupyter_port if is_running else None,
        "url": jupyter_url
    } 