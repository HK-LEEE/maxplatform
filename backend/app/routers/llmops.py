from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
import os
import json
import subprocess
import asyncio
import logging
from pathlib import Path
import tempfile
import uuid

from ..database import get_db
from ..models import User
from .auth import get_current_user
from ..services.chroma_service import get_chroma_service

router = APIRouter()
security = HTTPBearer()

# Langflow 프로세스 관리를 위한 전역 변수
langflow_processes: Dict[str, subprocess.Popen] = {}

@router.get("/llmops/health")
async def llmops_health():
    """LLMOps 서비스 상태 확인"""
    return {"status": "healthy", "service": "llmops"}

@router.get("/llmops/ui", response_class=HTMLResponse)
async def get_llmops_ui(
    current_user: User = Depends(get_current_user)
):
    """Langflow UI를 임베딩한 HTML 페이지 반환"""
    
    # 사용자별 고유 포트 할당 (베이스 포트 7860 + 사용자 ID 해시)
    user_port = 7860 + (hash(current_user.id) % 100)
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>LLMOps Platform - Langflow</title>
        <style>
            body {{
                margin: 0;
                padding: 0;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #f5f5f5;
            }}
            .header {{
                background: white;
                padding: 1rem;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .header h1 {{
                margin: 0;
                color: #333;
                font-size: 1.5rem;
            }}
            .user-info {{
                color: #666;
                font-size: 0.9rem;
            }}
            .langflow-container {{
                width: 100%;
                height: calc(100vh - 80px);
                border: none;
                background: white;
            }}
            .loading {{
                display: flex;
                justify-content: center;
                align-items: center;
                height: 50vh;
                flex-direction: column;
            }}
            .spinner {{
                border: 4px solid #f3f3f3;
                border-top: 4px solid #3498db;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 2s linear infinite;
                margin-bottom: 1rem;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>LLMOps Platform</h1>
            <div class="user-info">
                사용자: {current_user.display_name or current_user.real_name} | 
                포트: {user_port}
            </div>
        </div>
        
        <div id="loading" class="loading">
            <div class="spinner"></div>
            <p>Langflow 인스턴스를 시작하는 중...</p>
        </div>
        
        <iframe 
            id="langflow-frame"
            class="langflow-container"
            src="http://localhost:{user_port}"
            style="display: none;"
            onload="hideLoading()"
            onerror="showError()"
        ></iframe>
        
        <script>
            let retryCount = 0;
            const maxRetries = 30;
            
            function hideLoading() {{
                document.getElementById('loading').style.display = 'none';
                document.getElementById('langflow-frame').style.display = 'block';
            }}
            
            function showError() {{
                document.getElementById('loading').innerHTML = 
                    '<p>Langflow 서버 연결에 실패했습니다. 서버를 시작하는 중입니다...</p>';
                
                // 자동 재시도
                if (retryCount < maxRetries) {{
                    setTimeout(() => {{
                        retryCount++;
                        document.getElementById('langflow-frame').src = 
                            'http://localhost:{user_port}?' + new Date().getTime();
                    }}, 2000);
                }}
            }}
            
            // 페이지 로드 시 Langflow 서버 시작
            fetch('/api/llmops/start', {{
                method: 'POST',
                headers: {{
                    'Authorization': 'Bearer ' + localStorage.getItem('token'),
                    'Content-Type': 'application/json'
                }}
            }}).then(response => response.json())
              .then(data => console.log('Langflow 시작:', data))
              .catch(error => console.error('Error:', error));
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

@router.post("/llmops/start")
async def start_langflow_instance(
    current_user: User = Depends(get_current_user)
):
    """사용자별 Langflow 인스턴스 시작"""
    
    user_id = str(current_user.id)
    user_port = 7860 + (hash(current_user.id) % 100)
    
    # 이미 실행 중인 프로세스가 있는지 확인
    if user_id in langflow_processes:
        process = langflow_processes[user_id]
        if process.poll() is None:  # 프로세스가 살아있음
            return {
                "status": "already_running",
                "port": user_port,
                "message": "Langflow 인스턴스가 이미 실행 중입니다."
            }
        else:
            # 죽은 프로세스 제거
            del langflow_processes[user_id]
    
    try:
        # 사용자별 워크스페이스 디렉토리 생성
        workspace_dir = Path(f"data/langflow_workspaces/user_{current_user.id}")
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # Langflow 시작 명령
        cmd = [
            "python", "-m", "langflow", "run",
            "--host", "0.0.0.0",
            "--port", str(user_port),
            "--path", str(workspace_dir),
            "--log-level", "info"
        ]
        
        # 환경 변수 설정
        env = os.environ.copy()
        env.update({
            "LANGFLOW_DATABASE_URL": f"sqlite:///{workspace_dir}/langflow.db",
            "LANGFLOW_CONFIG_DIR": str(workspace_dir),
            "LANGFLOW_LOG_LEVEL": "INFO"
        })
        
        # 백그라운드에서 Langflow 프로세스 시작
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(workspace_dir)
        )
        
        langflow_processes[user_id] = process
        
        # 서버가 시작될 때까지 잠깐 대기
        await asyncio.sleep(3)
        
        return {
            "status": "started",
            "port": user_port,
            "pid": process.pid,
            "workspace": str(workspace_dir),
            "message": "Langflow 인스턴스가 성공적으로 시작되었습니다."
        }
        
    except Exception as e:
        logging.error(f"Langflow 시작 실패 (사용자 {current_user.id}): {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Langflow 인스턴스 시작에 실패했습니다: {str(e)}"
        )

@router.post("/llmops/stop")
async def stop_langflow_instance(
    current_user: User = Depends(get_current_user)
):
    """사용자의 Langflow 인스턴스 중지"""
    
    user_id = str(current_user.id)
    
    if user_id not in langflow_processes:
        return {
            "status": "not_running",
            "message": "실행 중인 Langflow 인스턴스가 없습니다."
        }
    
    try:
        process = langflow_processes[user_id]
        process.terminate()
        
        # 프로세스가 종료될 때까지 잠깐 대기
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()  # 강제 종료
        
        del langflow_processes[user_id]
        
        return {
            "status": "stopped",
            "message": "Langflow 인스턴스가 중지되었습니다."
        }
        
    except Exception as e:
        logging.error(f"Langflow 중지 실패 (사용자 {current_user.id}): {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Langflow 인스턴스 중지에 실패했습니다: {str(e)}"
        )

@router.get("/llmops/status")
async def get_langflow_status(
    current_user: User = Depends(get_current_user)
):
    """사용자의 Langflow 인스턴스 상태 확인"""
    
    user_id = str(current_user.id)
    user_port = 7860 + (hash(current_user.id) % 100)
    
    if user_id not in langflow_processes:
        return {
            "status": "not_running",
            "port": user_port,
            "message": "Langflow 인스턴스가 실행되지 않았습니다."
        }
    
    process = langflow_processes[user_id]
    
    if process.poll() is None:  # 프로세스가 살아있음
        return {
            "status": "running",
            "port": user_port,
            "pid": process.pid,
            "message": "Langflow 인스턴스가 실행 중입니다."
        }
    else:
        # 죽은 프로세스 제거
        del langflow_processes[user_id]
        return {
            "status": "stopped",
            "port": user_port,
            "message": "Langflow 인스턴스가 중지되었습니다."
        }

@router.get("/llmops/flows")
async def list_user_flows(
    current_user: User = Depends(get_current_user)
):
    """사용자의 Langflow 플로우 목록 조회"""
    
    workspace_dir = Path(f"data/langflow_workspaces/user_{current_user.id}")
    flows_dir = workspace_dir / "flows"
    
    if not flows_dir.exists():
        return {"flows": []}
    
    flows = []
    for flow_file in flows_dir.glob("*.json"):
        try:
            with open(flow_file, 'r', encoding='utf-8') as f:
                flow_data = json.load(f)
                flows.append({
                    "id": flow_file.stem,
                    "name": flow_data.get("name", flow_file.name),
                    "description": flow_data.get("description", ""),
                    "created_at": flow_file.stat().st_ctime,
                    "modified_at": flow_file.stat().st_mtime
                })
        except Exception as e:
            logging.warning(f"플로우 파일 읽기 실패 {flow_file}: {str(e)}")
    
    return {"flows": flows}

@router.post("/llmops/flows/export")
async def export_flow(
    flow_id: str,
    current_user: User = Depends(get_current_user)
):
    """플로우 내보내기"""
    
    workspace_dir = Path(f"data/langflow_workspaces/user_{current_user.id}")
    flow_file = workspace_dir / "flows" / f"{flow_id}.json"
    
    if not flow_file.exists():
        raise HTTPException(status_code=404, detail="플로우를 찾을 수 없습니다.")
    
    try:
        with open(flow_file, 'r', encoding='utf-8') as f:
            flow_data = json.load(f)
        
        return {
            "flow_id": flow_id,
            "data": flow_data,
            "exported_at": str(Path.now())
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"플로우 내보내기에 실패했습니다: {str(e)}"
        )

@router.delete("/llmops/cleanup")
async def cleanup_user_processes():
    """모든 사용자의 Langflow 프로세스 정리"""
    
    cleanup_count = 0
    for user_id, process in list(langflow_processes.items()):
        try:
            if process.poll() is not None:  # 프로세스가 죽었음
                del langflow_processes[user_id]
                cleanup_count += 1
        except Exception as e:
            logging.error(f"프로세스 정리 실패 (사용자 {user_id}): {str(e)}")
    
    return {
        "cleaned_up": cleanup_count,
        "active_processes": len(langflow_processes),
        "message": f"{cleanup_count}개의 죽은 프로세스를 정리했습니다."
    }

@router.get("/llmops/rag-collections")
async def get_rag_collections(
    current_user: User = Depends(get_current_user)
):
    """사용자가 접근 가능한 RAG Collection 목록 조회"""
    try:
        chroma_service = get_chroma_service()
        
        # 사용자 소유 컬렉션 조회
        user_collections = await chroma_service.get_collections_by_owner("user", str(current_user.id))
        
        # 응답 형식 변환
        collections = []
        for collection in user_collections:
            collections.append({
                "value": collection.id,
                "label": collection.name,
                "description": collection.description or f"사용자 {current_user.display_name or current_user.real_name}의 컬렉션",
                "owner_type": "user",
                "owner_id": str(current_user.id),
                "created_at": collection.created_at,
                "document_count": getattr(collection, 'document_count', 0)
            })
        
        # TODO: 그룹 권한 기반 컬렉션도 추가
        # group_collections = await chroma_service.get_collections_by_group(current_user.groups)
        
        return {
            "collections": collections,
            "total_count": len(collections)
        }
        
    except Exception as e:
        logging.error(f"RAG 컬렉션 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="RAG 컬렉션 목록을 가져올 수 없습니다.") 
