from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from ..database import get_db
from ..services.workspace_service import WorkspaceService
from ..services.jupyter_service import jupyter_service
from .auth import get_current_user

# 로깅 설정
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jupyter", tags=["Jupyter"])

@router.post("/start/{workspace_id}")
async def start_jupyter(
    workspace_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Jupyter Lab 인스턴스 시작"""
    try:
        logger.info(f"Jupyter Lab 시작 요청 - workspace_id: {workspace_id}, user_id: {current_user.id}")
        
        workspace_service = WorkspaceService(db)
        workspace = workspace_service.get_workspace_by_id(workspace_id, current_user.id)
        
        if not workspace:
            logger.error(f"워크스페이스를 찾을 수 없음 - workspace_id: {workspace_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        logger.info(f"워크스페이스 찾음 - name: {workspace.name}, path: {workspace.path}")
        
        # 워크스페이스 상태를 'starting'으로 변경
        workspace.jupyter_status = "starting"
        db.commit()
        
        try:
            # Jupyter Lab 시작 (데이터베이스 세션 전달)
            logger.info("Jupyter Lab 시작 중...")
            port, token = jupyter_service.start_jupyter_lab(workspace, db)
            logger.info(f"Jupyter Lab 시작 완료 - port: {port}, token: {token}")
            
            # 데이터베이스에 Jupyter 정보 업데이트
            logger.info("데이터베이스 업데이트 중...")
            workspace.jupyter_port = port
            workspace.jupyter_token = token
            workspace.jupyter_status = "running"
            db.commit()
            
            # Jupyter URL 생성
            jupyter_url = jupyter_service.get_jupyter_url(workspace)
            
            logger.info(f"Jupyter Lab 시작 성공 - workspace_id: {workspace_id}, port: {port}")
            
            return {
                "message": "Jupyter Lab started successfully",
                "workspace_id": workspace_id,
                "port": port,
                "token": token,
                "url": jupyter_url,
                "status": "running"
            }
            
        except Exception as e:
            # 시작 실패 시 상태를 'error'로 변경
            workspace.jupyter_status = "error"
            workspace.jupyter_port = None
            workspace.jupyter_token = None
            db.commit()
            logger.error(f"Jupyter Lab 시작 실패: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Jupyter Lab 시작 실패: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"예상치 못한 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"서버 오류: {str(e)}"
        )

@router.post("/stop/{workspace_id}")
async def stop_jupyter(
    workspace_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Jupyter Lab 인스턴스 중지"""
    try:
        logger.info(f"Jupyter Lab 중지 요청 - workspace_id: {workspace_id}, user_id: {current_user.id}")
        
        workspace_service = WorkspaceService(db)
        workspace = workspace_service.get_workspace_by_id(workspace_id, current_user.id)
        
        if not workspace:
            logger.error(f"워크스페이스를 찾을 수 없음 - workspace_id: {workspace_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        logger.info(f"워크스페이스 찾음 - name: {workspace.name}, 현재 상태: {workspace.jupyter_status}")
        
        # Jupyter Lab 중지 시도
        success = jupyter_service.stop_jupyter_lab(workspace_id)
        
        # 상태 업데이트 (성공 여부와 관계없이)
        workspace.jupyter_status = "stopped"
        workspace.jupyter_port = None
        workspace.jupyter_token = None
        db.commit()
        
        if success:
            logger.info(f"Jupyter Lab 중지 성공 - workspace_id: {workspace_id}")
            return {
                "message": "Jupyter Lab stopped successfully",
                "workspace_id": workspace_id,
                "status": "stopped"
            }
        else:
            logger.warning(f"Jupyter Lab 프로세스가 이미 중지되어 있음 - workspace_id: {workspace_id}")
            return {
                "message": "Jupyter Lab was not running or already stopped",
                "workspace_id": workspace_id,
                "status": "stopped"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Jupyter Lab 중지 중 오류: {str(e)}")
        # 오류가 발생해도 상태는 업데이트
        try:
            workspace_service = WorkspaceService(db)
            workspace = workspace_service.get_workspace_by_id(workspace_id, current_user.id)
            if workspace:
                workspace.jupyter_status = "stopped"
                workspace.jupyter_port = None
                workspace.jupyter_token = None
                db.commit()
        except:
            pass  # 상태 업데이트 실패는 무시
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Jupyter Lab 중지 실패: {str(e)}"
        )

@router.get("/status/{workspace_id}")
async def get_jupyter_status(
    workspace_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Jupyter Lab 상태 확인"""
    try:
        workspace_service = WorkspaceService(db)
        workspace = workspace_service.get_workspace_by_id(workspace_id, current_user.id)
        
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        # 프로세스 실제 상태 확인
        is_running = jupyter_service.is_process_running(workspace_id)
        
        # 데이터베이스 상태와 실제 프로세스 상태가 다른 경우 동기화
        if workspace.jupyter_status == "running" and not is_running:
            workspace.jupyter_status = "stopped"
            workspace.jupyter_port = None
            workspace.jupyter_token = None
            db.commit()
            logger.info(f"워크스페이스 {workspace_id} 상태 동기화: stopped")
        
        # Jupyter URL 생성 (실행 중인 경우)
        jupyter_url = None
        if is_running and workspace.jupyter_port:
            jupyter_url = jupyter_service.get_jupyter_url(workspace)
        
        return {
            "workspace_id": workspace_id,
            "status": workspace.jupyter_status or "stopped",
            "is_running": is_running,
            "port": workspace.jupyter_port,
            "url": jupyter_url,
            "last_updated": workspace.updated_at.isoformat() if workspace.updated_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Jupyter 상태 확인 중 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"상태 확인 실패: {str(e)}"
        ) 