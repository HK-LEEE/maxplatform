"""
LLM API 라우터 - Jupyter 노트북 분석 및 수정 지원
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import os
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.llm_service import llm_service
from ..services.workspace_service import WorkspaceService
from .auth import get_current_user

router = APIRouter(prefix="/llm", tags=["LLM"])

# Pydantic 모델들
class ChatRequest(BaseModel):
    message: str
    workspace_id: int
    notebook_path: Optional[str] = None
    provider: Optional[str] = None

class CellAnalysisRequest(BaseModel):
    message: str
    workspace_id: int
    notebook_path: str
    cell_indices: List[int]
    provider: Optional[str] = None

class NotebookStructureRequest(BaseModel):
    workspace_id: int
    notebook_path: str

class ConnectionCheckRequest(BaseModel):
    provider: Optional[str] = None



@router.get("/status")
async def get_llm_status():
    """LLM 서비스 상태 확인"""
    try:
        connection_status = await llm_service.check_connection()
        available_models = await llm_service.get_available_models()
        
        return {
            "status": "ok",
            "connections": connection_status,
            "available_models": available_models,
            "azure_available": llm_service.azure_available,
            "ollama_available": llm_service.ollama_available
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "connections": {"azure": False, "ollama": False},
            "available_models": {"azure": [], "ollama": []}
        }

@router.post("/check-connection")
async def check_connection(request: ConnectionCheckRequest):
    """특정 LLM 제공자 연결 상태 확인"""
    try:
        connection_status = await llm_service.check_connection(request.provider)
        return {
            "status": "ok",
            "connections": connection_status
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "connections": {"azure": False, "ollama": False}
        }

@router.post("/chat")
async def chat_with_notebook(
    request: ChatRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """노트북 내용과 함께 LLM에 질문"""
    try:
        workspace_service = WorkspaceService(db)
        workspace = workspace_service.get_workspace_by_id(request.workspace_id, current_user.id)
        
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        # 노트북 파일 읽기
        notebook_content = ""
        if request.notebook_path:
            notebook_full_path = os.path.join(workspace.path, request.notebook_path)
            if os.path.exists(notebook_full_path) and notebook_full_path.endswith('.ipynb'):
                try:
                    with open(notebook_full_path, 'r', encoding='utf-8') as f:
                        notebook_content = f.read()
                except Exception as e:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"노트북 파일을 읽을 수 없습니다: {str(e)}"
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="노트북 파일을 찾을 수 없습니다"
                )
        else:
            # 노트북 파일이 지정되지 않은 경우 워크스페이스의 모든 노트북 파일 목록
            notebooks_dir = os.path.join(workspace.path, "notebooks")
            if os.path.exists(notebooks_dir):
                notebook_files = [f for f in os.listdir(notebooks_dir) if f.endswith('.ipynb')]
                if notebook_files:
                    # 첫 번째 노트북 파일 사용
                    first_notebook = os.path.join(notebooks_dir, notebook_files[0])
                    try:
                        with open(first_notebook, 'r', encoding='utf-8') as f:
                            notebook_content = f.read()
                    except Exception as e:
                        notebook_content = "{}"  # 빈 노트북
                else:
                    notebook_content = "{}"  # 빈 노트북
            else:
                notebook_content = "{}"  # 빈 노트북
        
        # LLM에게 질문
        result = await llm_service.analyze_notebook(
            notebook_content=notebook_content,
            user_message=request.message,
            provider=request.provider
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=result["error"]
            )
        
        return {
            "status": "success",
            "response": result["response"],
            "provider": result["provider"],
            "model": result["model"],
            "notebook_analyzed": bool(notebook_content and notebook_content != "{}")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM 요청 처리 실패: {str(e)}"
        )

@router.get("/models")
async def get_available_models():
    """사용 가능한 모델 목록 조회"""
    try:
        models = await llm_service.get_available_models()
        return {
            "status": "success",
            "models": models
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "models": {"azure": [], "ollama": []}
        }

@router.get("/workspace/{workspace_id}/notebooks")
async def get_workspace_notebooks(
    workspace_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """워크스페이스의 노트북 파일 목록 조회"""
    try:
        workspace_service = WorkspaceService(db)
        workspace = workspace_service.get_workspace_by_id(workspace_id, current_user.id)
        
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        notebooks = []
        
        # notebooks 폴더에서 .ipynb 파일 찾기
        notebooks_dir = os.path.join(workspace.path, "notebooks")
        if os.path.exists(notebooks_dir):
            for file in os.listdir(notebooks_dir):
                if file.endswith('.ipynb'):
                    file_path = os.path.join(notebooks_dir, file)
                    try:
                        stat = os.stat(file_path)
                        notebooks.append({
                            "name": file,
                            "path": f"notebooks/{file}",
                            "size": stat.st_size,
                            "modified": stat.st_mtime
                        })
                    except:
                        notebooks.append({
                            "name": file,
                            "path": f"notebooks/{file}",
                            "size": 0,
                            "modified": 0
                        })
        
        # 루트 디렉토리에서도 .ipynb 파일 찾기
        if os.path.exists(workspace.path):
            for file in os.listdir(workspace.path):
                if file.endswith('.ipynb'):
                    file_path = os.path.join(workspace.path, file)
                    try:
                        stat = os.stat(file_path)
                        notebooks.append({
                            "name": file,
                            "path": file,
                            "size": stat.st_size,
                            "modified": stat.st_mtime
                        })
                    except:
                        notebooks.append({
                            "name": file,
                            "path": file,
                            "size": 0,
                            "modified": 0
                        })
        
        return {
            "status": "success",
            "notebooks": notebooks
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"노트북 목록 조회 실패: {str(e)}"
        )

@router.post("/analyze-cells")
async def analyze_notebook_cells(
    request: CellAnalysisRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """선택된 노트북 셀들을 분석"""
    try:
        workspace_service = WorkspaceService(db)
        workspace = workspace_service.get_workspace_by_id(request.workspace_id, current_user.id)
        
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        # 노트북 파일 읽기
        notebook_full_path = os.path.join(workspace.path, request.notebook_path)
        if not os.path.exists(notebook_full_path) or not notebook_full_path.endswith('.ipynb'):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="노트북 파일을 찾을 수 없습니다"
            )
        
        try:
            with open(notebook_full_path, 'r', encoding='utf-8') as f:
                notebook_content = f.read()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"노트북 파일을 읽을 수 없습니다: {str(e)}"
            )
        
        # 셀 인덱스 유효성 검사
        if not request.cell_indices:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="분석할 셀을 선택해주세요"
            )
        
        # LLM에 특정 셀들 분석 요청
        result = await llm_service.analyze_notebook_cells(
            notebook_content=notebook_content,
            user_message=request.message,
            cell_indices=request.cell_indices,
            provider=request.provider
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=result["error"]
            )
        
        return {
            "status": "success",
            "response": result["response"],
            "provider": result["provider"],
            "model": result["model"],
            "analysis_info": result.get("analysis_info", {}),
            "cells_analyzed": len(request.cell_indices)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"셀 분석 요청 처리 실패: {str(e)}"
        )

@router.post("/notebook-structure")
async def get_notebook_structure(
    request: NotebookStructureRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """노트북의 구조 정보 조회 (셀 목록, 타입, 내용 미리보기)"""
    try:
        workspace_service = WorkspaceService(db)
        workspace = workspace_service.get_workspace_by_id(request.workspace_id, current_user.id)
        
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        # 노트북 파일 읽기
        notebook_full_path = os.path.join(workspace.path, request.notebook_path)
        if not os.path.exists(notebook_full_path) or not notebook_full_path.endswith('.ipynb'):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="노트북 파일을 찾을 수 없습니다"
            )
        
        try:
            with open(notebook_full_path, 'r', encoding='utf-8') as f:
                notebook_content = f.read()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"노트북 파일을 읽을 수 없습니다: {str(e)}"
            )
        
        # 노트북 구조 파싱
        parsed_notebook = llm_service.parse_notebook_content(notebook_content)
        
        if 'error' in parsed_notebook:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"노트북 파싱 실패: {parsed_notebook['error']}"
            )
        
        # 각 셀의 미리보기 정보 생성
        cells_preview = []
        for cell in parsed_notebook['cells']:
            preview = {
                'index': cell['index'],
                'cell_type': cell['cell_type'],
                'preview': cell['source'][:200] + '...' if len(cell['source']) > 200 else cell['source'],
                'line_count': len(cell['source'].split('\n')),
                'execution_count': cell.get('execution_count'),
                'has_output': len(cell.get('outputs', [])) > 0,
                'has_error': any(output.get('type') == 'error' for output in cell.get('outputs', []))
            }
            cells_preview.append(preview)
        
        return {
            "status": "success",
            "notebook_path": request.notebook_path,
            "summary": {
                "total_cells": parsed_notebook['total_cells'],
                "code_cells": parsed_notebook['code_cells_count'],
                "markdown_cells": parsed_notebook['markdown_cells_count']
            },
            "cells": cells_preview,
            "metadata": parsed_notebook['metadata']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"노트북 구조 분석 실패: {str(e)}"
        )

 