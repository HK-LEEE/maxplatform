"""
LLMOps API 라우터

RAG 데이터소스 관리, Flow Studio 관련 API 엔드포인트를 정의합니다.
고도화된 기능: 버전 관리, 실행 기록, 시크릿 관리
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Header
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from pydantic import BaseModel
import uuid
from datetime import datetime

from ..database import get_db
from ..models.user import User
from ..routers.auth import get_current_user
from .models import RAGDataSource, OwnerType, Flow, FlowExecutionLog, Secret, ExecutionStatus
from ..services.chroma_service import ChromaService
from .rag_service import RAGDataSourceService
from .worker_manager import worker_manager

import logging
import os

logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(
    prefix="/api/llmops",
    tags=["LLMOps"]
)

# Pydantic 모델들
class CreateDataSourceRequest(BaseModel):
    name: str
    description: Optional[str] = None
    owner_type: OwnerType
    group_id: Optional[int] = None  # GROUP 타입일 때 필요
    embedding_config: Optional[Dict[str, Any]] = None

class QueryRequest(BaseModel):
    query: str
    n_results: Optional[int] = 5

# Flow 관련 Pydantic 모델들 (신규 추가)
class CreateFlowRequest(BaseModel):
    name: str
    description: Optional[str] = None
    flow_data: Dict[str, Any]
    owner_type: OwnerType
    owner_id: int
    workspace_id: Optional[int] = None
    parent_flow_id: Optional[int] = None  # 버전 관리용
    rag_datasource_id: Optional[int] = None
    tags: Optional[List[str]] = None

class UpdateFlowRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    flow_data: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None

class ExecuteFlowRequest(BaseModel):
    inputs: Dict[str, Any]
    version: Optional[int] = None  # 특정 버전 실행

class CreateSecretRequest(BaseModel):
    name: str
    value: str
    description: Optional[str] = None
    owner_type: OwnerType
    owner_id: int
    category: Optional[str] = None
    tags: Optional[List[str]] = None

class UpdateSecretRequest(BaseModel):
    value: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None

# RAG 데이터소스 관련 API
@router.post("/rag-datasources")
async def create_rag_datasource(
    request: CreateDataSourceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """새 RAG 데이터소스 생성"""
    try:
        service = RAGDataSourceService(db)
        
        # owner_id 결정
        if request.owner_type == OwnerType.GROUP:
            if not request.group_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="그룹 타입의 데이터소스는 group_id가 필요합니다."
                )
            owner_id = str(request.group_id)
        else:
            owner_id = str(current_user.id)
        
        datasource = await service.create_datasource(
            name=request.name,
            description=request.description,
            owner_type=request.owner_type,
            owner_id=owner_id,
            current_user=current_user,
            embedding_config=request.embedding_config
        )
        
        return {
            "success": True,
            "message": "데이터소스가 성공적으로 생성되었습니다.",
            "datasource": {
                "id": datasource.id,
                "name": datasource.name,
                "chroma_collection_name": datasource.chroma_collection_name
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating datasource: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="데이터소스 생성 중 오류가 발생했습니다."
        )

@router.get("/rag-datasources")
async def get_rag_datasources(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """현재 사용자가 접근 가능한 RAG 데이터소스 목록 조회"""
    try:
        service = RAGDataSourceService(db)
        datasources = service.get_datasource_list(current_user)
        
        return datasources
        
    except Exception as e:
        logger.error(f"Error getting datasources: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="데이터소스 목록 조회 중 오류가 발생했습니다."
        )

@router.get("/rag-collections")
async def get_rag_collections_for_flowstudio(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """FlowStudio RAG 컴포넌트용 Collection 목록 조회 (Select 옵션 형태)"""
    try:
        service = RAGDataSourceService(db)
        datasources = service.get_datasource_list(current_user)
        
        # Collection 옵션 형태로 변환
        collections = []
        for datasource in datasources:
            # datasource는 get_datasource_list에서 반환된 dict 형태
            # 실제 RAGDataSource 객체를 가져와서 chroma_collection_name을 얻어야 함
            from .auth import LLMOpsAuthService
            auth_service = LLMOpsAuthService(db)
            datasource_obj = auth_service.get_rag_datasource_with_permission(datasource["id"], current_user)
            
            collections.append({
                "value": datasource_obj.chroma_collection_name,  # 실제 Chroma collection name
                "label": f"{datasource['name']} ({datasource['document_count']}개 문서)",
                "description": datasource.get('description', ''),
                "owner_type": datasource["owner"]["type"],  # owner는 dict 형태
                "owner_id": datasource_obj.owner_id,
                "document_count": datasource["document_count"],
                "is_active": datasource["is_active"]
            })
        
        return {
            "collections": collections,
            "total_count": len(collections)
        }
        
    except Exception as e:
        logger.error(f"Error getting RAG collections for FlowStudio: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RAG Collection 목록 조회 중 오류가 발생했습니다."
        )

@router.get("/rag-datasources/{source_id}")
async def get_rag_datasource(
    source_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """특정 RAG 데이터소스 상세 정보 조회"""
    try:
        from .auth import LLMOpsAuthService
        auth_service = LLMOpsAuthService(db)
        datasource = auth_service.get_rag_datasource_with_permission(source_id, current_user)
        
        chroma_service = ChromaService()
        stats = chroma_service.get_collection_stats(datasource.chroma_collection_name)
        
        return {
            "id": datasource.id,
            "name": datasource.name,
            "description": datasource.description,
            "owner_type": datasource.owner_type.value,
            "owner_id": datasource.owner_id,
            "document_count": stats["document_count"],
            "is_active": datasource.is_active,
            "created_at": datasource.created_at.isoformat(),
            "last_updated": datasource.last_updated.isoformat(),
            "embedding_config": datasource.embedding_config,
            "tags": datasource.tags or []
        }
        
    except Exception as e:
        logger.error(f"Error getting datasource details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="데이터소스 상세 정보 조회 중 오류가 발생했습니다."
        )

@router.post("/rag-datasources/{source_id}/documents")
async def upload_documents(
    source_id: int,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """RAG 데이터소스에 문서 업로드"""
    try:
        from .auth import LLMOpsAuthService
        auth_service = LLMOpsAuthService(db)
        datasource = auth_service.get_rag_datasource_with_permission(source_id, current_user)
        
        service = RAGDataSourceService(db)
        result = await service.upload_documents(datasource, files, current_user)
        
        # 프론트엔드가 기대하는 형식으로 응답 변환
        return {
            "uploaded_files": result["total_files_processed"],
            "processed_chunks": result["uploaded_documents"],
            "failed_files": [f["filename"] for f in result["failed_files"]] if result["failed_files"] else [],
            "success": result["success"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="문서 업로드 중 오류가 발생했습니다."
        )

@router.post("/rag-datasources/{source_id}/query")
async def query_datasource(
    source_id: int,
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """RAG 데이터소스에서 문서 검색"""
    try:
        from .auth import LLMOpsAuthService
        auth_service = LLMOpsAuthService(db)
        datasource = auth_service.get_rag_datasource_with_permission(source_id, current_user)
        
        service = RAGDataSourceService(db)
        results = await service.query_documents(
            datasource, 
            request.query, 
            request.n_results
        )
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying datasource: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="문서 검색 중 오류가 발생했습니다."
        )

@router.post("/rag-datasources/{source_id}/query-advanced")
async def query_datasource_advanced(
    source_id: int,
    request: QueryRequest,
    use_hybrid: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """RAG 데이터소스에서 고급 문서 검색 (하이브리드 검색 + 분석)"""
    try:
        from .auth import LLMOpsAuthService
        auth_service = LLMOpsAuthService(db)
        datasource = auth_service.get_rag_datasource_with_permission(source_id, current_user)
        
        service = RAGDataSourceService(db)
        results = service.query_documents_with_analytics(
            datasource, 
            request.query, 
            request.n_results,
            use_hybrid=use_hybrid
        )
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in advanced query: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="고급 검색 중 오류가 발생했습니다."
        )

@router.delete("/rag-datasources/{source_id}")
async def delete_rag_datasource(
    source_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """RAG 데이터소스 삭제"""
    try:
        from .auth import LLMOpsAuthService
        auth_service = LLMOpsAuthService(db)
        datasource = auth_service.get_rag_datasource_with_permission(source_id, current_user)
        
        service = RAGDataSourceService(db)
        success = await service.delete_datasource(datasource, current_user)
        
        if success:
            return {
                "success": True,
                "message": "데이터소스가 성공적으로 삭제되었습니다."
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="데이터소스 삭제에 실패했습니다."
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting datasource: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="데이터소스 삭제 중 오류가 발생했습니다."
        )

@router.delete("/rag-datasources/{source_id}/documents")
async def clear_datasource_documents(
    source_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """RAG 데이터소스의 모든 문서 삭제"""
    try:
        from .auth import LLMOpsAuthService
        auth_service = LLMOpsAuthService(db)
        datasource = auth_service.get_rag_datasource_with_permission(source_id, current_user)
        
        service = RAGDataSourceService(db)
        success = service.clear_datasource_documents(datasource, current_user)
        
        if success:
            return {
                "success": True,
                "message": "모든 문서가 성공적으로 삭제되었습니다."
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="문서 삭제에 실패했습니다."
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="문서 삭제 중 오류가 발생했습니다."
        )

@router.get("/rag-datasources/{source_id}/documents")
async def get_documents(
    source_id: int,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """RAG 데이터소스의 문서 목록 조회"""
    try:
        from .auth import LLMOpsAuthService
        auth_service = LLMOpsAuthService(db)
        datasource = auth_service.get_rag_datasource_with_permission(source_id, current_user)
        
        service = RAGDataSourceService(db)
        documents = service.get_documents(datasource, page, page_size)
        
        return documents
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="문서 목록 조회 중 오류가 발생했습니다."
        )

@router.delete("/rag-datasources/{source_id}/documents/{document_id}")
async def delete_document(
    source_id: int,
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """RAG 데이터소스에서 특정 문서 삭제"""
    try:
        from .auth import LLMOpsAuthService
        auth_service = LLMOpsAuthService(db)
        datasource = auth_service.get_rag_datasource_with_permission(source_id, current_user)
        
        service = RAGDataSourceService(db)
        success = service.delete_document(datasource, document_id, current_user)
        
        if success:
            return {
                "success": True,
                "message": "문서가 성공적으로 삭제되었습니다."
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="문서를 찾을 수 없습니다."
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="문서 삭제 중 오류가 발생했습니다."
        )

@router.get("/rag-datasources/{source_id}/stored-files")
async def get_stored_files(
    source_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """데이터소스에 저장된 파일 목록 조회"""
    try:
        from .auth import LLMOpsAuthService
        auth_service = LLMOpsAuthService(db)
        datasource = auth_service.get_rag_datasource_with_permission(source_id, current_user)
        
        service = RAGDataSourceService(db)
        result = service.get_stored_files(datasource, current_user)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stored files: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="저장된 파일 목록 조회 중 오류가 발생했습니다."
        )

@router.delete("/rag-datasources/{source_id}/stored-files")
async def delete_stored_file(
    source_id: int,
    file_path: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """저장된 파일 삭제"""
    try:
        from .auth import LLMOpsAuthService
        auth_service = LLMOpsAuthService(db)
        datasource = auth_service.get_rag_datasource_with_permission(source_id, current_user)
        
        service = RAGDataSourceService(db)
        success = service.delete_stored_file(datasource, file_path, current_user)
        
        return {
            "success": success,
            "message": "파일이 성공적으로 삭제되었습니다." if success else "파일 삭제에 실패했습니다."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting stored file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="저장된 파일 삭제 중 오류가 발생했습니다."
        )

@router.get("/storage/overview")
async def get_storage_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자의 전체 저장소 사용량 개요"""
    try:
        service = RAGDataSourceService(db)
        overview = service.get_user_storage_overview(current_user)
        
        return overview
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting storage overview: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="저장소 개요 조회 중 오류가 발생했습니다."
        )

@router.get("/status")
async def get_llmops_status(
    db: Session = Depends(get_db)
):
    """LLMOps 시스템 상태 조회 (인증 불필요)"""
    try:
        # ChromaDB 연결 상태 확인
        chroma_service = ChromaService()
        chroma_status = "running"
        try:
            chroma_service.client.heartbeat()
        except:
            chroma_status = "stopped"
        
        # 데이터베이스 연결 상태 확인
        db_status = "running"
        try:
            db.execute("SELECT 1")
        except:
            db_status = "stopped"
        
        # 시스템 전체 통계 (인증 없이 일반적인 정보만)
        total_flows = db.query(Flow).count()
        total_datasources = db.query(RAGDataSource).count()
        
        return {
            "status": "running" if chroma_status == "running" and db_status == "running" else "degraded",
            "port": 8000,  # FastAPI 포트
            "message": "LLMOps 서비스가 정상 작동 중입니다.",
            "components": {
                "chroma_db": chroma_status,
                "database": db_status,
                "flow_runner": "running"
            },
            "statistics": {
                "total_flows": total_flows,
                "total_datasources": total_datasources,
                "total_secrets": 0  # 보안상 개별 사용자 정보는 제외
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting LLMOps status: {str(e)}")
        return {
            "status": "error",
            "port": 8000,
            "message": f"상태 조회 중 오류가 발생했습니다: {str(e)}",
            "components": {
                "chroma_db": "unknown",
                "database": "unknown", 
                "flow_runner": "unknown"
            },
            "timestamp": datetime.utcnow().isoformat()
        }

@router.post("/start")
async def start_llmops_service():
    """LLMOps 서비스 시작 (개발 모드 - 인증 불필요)"""
    try:
        logger.info("LLMOps 서비스 시작 요청")
        # 실제로는 서비스 시작 로직이 있을 것
        # 현재는 상태 정보만 반환
        return {
            "status": "running",
            "port": 8000,
            "message": "LLMOps 서비스가 시작되었습니다.",
            "pid": None,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error starting LLMOps service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서비스 시작에 실패했습니다."
        )

@router.post("/stop")
async def stop_llmops_service():
    """LLMOps 서비스 중지 (개발 모드 - 인증 불필요)"""
    try:
        logger.info("LLMOps 서비스 중지 요청")
        # 실제로는 서비스 중지 로직이 있을 것
        # 현재는 상태 정보만 반환
        return {
            "status": "stopped",
            "port": None,
            "message": "LLMOps 서비스가 중지되었습니다.",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error stopping LLMOps service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서비스 중지에 실패했습니다."
        )

@router.get("/health")
async def health_check():
    """시스템 헬스 체크 (인증 불필요)"""
    return {
        "status": "healthy",
        "service": "LLMOps Platform", 
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

# Flow 관리 API (신규 추가)
@router.post("/flows")
async def create_flow(
    request: CreateFlowRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """새 Flow 생성 또는 새 버전 생성"""
    try:
        # 새 버전 생성인지 확인
        if request.parent_flow_id:
            # 부모 Flow 존재 확인
            parent_flow = db.query(Flow).filter(Flow.id == request.parent_flow_id).first()
            if not parent_flow:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="부모 플로우를 찾을 수 없습니다."
                )
            
            # 기존 최신 버전의 is_latest를 False로 변경
            db.query(Flow).filter(
                and_(
                    or_(Flow.id == request.parent_flow_id, Flow.parent_flow_id == request.parent_flow_id),
                    Flow.is_latest == True
                )
            ).update({"is_latest": False})
            
            # 새 버전 번호 계산
            max_version = db.query(Flow).filter(
                or_(Flow.id == request.parent_flow_id, Flow.parent_flow_id == request.parent_flow_id)
            ).order_by(desc(Flow.version)).first()
            next_version = (max_version.version if max_version else 0) + 1
        else:
            next_version = 1
        
        # 새 Flow 생성
        new_flow = Flow(
            name=request.name,
            description=request.description,
            flow_data=request.flow_data,
            owner_type=request.owner_type,
            owner_id=request.owner_id,
            version=next_version,
            parent_flow_id=request.parent_flow_id,
            is_latest=True,
            workspace_id=request.workspace_id,
            rag_datasource_id=request.rag_datasource_id,
            tags=request.tags,
            created_by=current_user.id
        )
        
        db.add(new_flow)
        db.commit()
        db.refresh(new_flow)
        
        return {
            "success": True,
            "message": f"플로우 버전 {next_version}이 성공적으로 생성되었습니다.",
            "flow": {
                "id": new_flow.id,
                "name": new_flow.name,
                "version": new_flow.version,
                "is_latest": new_flow.is_latest,
                "created_at": new_flow.created_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating flow: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="플로우 생성 중 오류가 발생했습니다."
        )

@router.get("/flows")
async def get_flows(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    owner_type: Optional[OwnerType] = None,
    owner_id: Optional[int] = None,
    latest_only: bool = True
):
    """Flow 목록 조회"""
    try:
        query = db.query(Flow)
        
        # 소유권 필터링 - 현재 사용자가 접근 가능한 Flow만
        user_flows = query.filter(
            and_(Flow.owner_type == OwnerType.USER, Flow.owner_id == current_user.id)
        )
        
        # TODO: 그룹 권한 체크 로직 추가
        # group_flows = query.filter(...)
        
        if latest_only:
            user_flows = user_flows.filter(Flow.is_latest == True)
        
        flows = user_flows.order_by(desc(Flow.updated_at)).all()
        
        return [
            {
                "id": flow.id,
                "name": flow.name,
                "description": flow.description,
                "version": flow.version,
                "is_latest": flow.is_latest,
                "parent_flow_id": flow.parent_flow_id,
                "owner_type": flow.owner_type.value,
                "owner_id": flow.owner_id,
                "execution_count": flow.execution_count,
                "last_executed": flow.last_executed.isoformat() if flow.last_executed else None,
                "created_at": flow.created_at.isoformat(),
                "updated_at": flow.updated_at.isoformat(),
                "tags": flow.tags or []
            }
            for flow in flows
        ]
        
    except Exception as e:
        logger.error(f"Error getting flows: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="플로우 목록 조회 중 오류가 발생했습니다."
        )

@router.get("/flows/{flow_id}")
async def get_flow(
    flow_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """특정 Flow 상세 정보 조회"""
    try:
        flow = db.query(Flow).filter(Flow.id == flow_id).first()
        if not flow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="플로우를 찾을 수 없습니다."
            )
        
        # 권한 확인 (간단한 버전 - 실제로는 더 복잡한 권한 로직 필요)
        if flow.owner_type == OwnerType.USER and flow.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 플로우에 접근할 권한이 없습니다."
            )
        
        return {
            "id": flow.id,
            "name": flow.name,
            "description": flow.description,
            "flow_data": flow.flow_data,
            "version": flow.version,
            "is_latest": flow.is_latest,
            "parent_flow_id": flow.parent_flow_id,
            "owner_type": flow.owner_type.value,
            "owner_id": flow.owner_id,
            "workspace_id": flow.workspace_id,
            "rag_datasource_id": flow.rag_datasource_id,
            "execution_count": flow.execution_count,
            "last_executed": flow.last_executed.isoformat() if flow.last_executed else None,
            "created_at": flow.created_at.isoformat(),
            "updated_at": flow.updated_at.isoformat(),
            "tags": flow.tags or []
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting flow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="플로우 조회 중 오류가 발생했습니다."
        )

@router.get("/flows/{flow_id}/versions")
async def get_flow_versions(
    flow_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """특정 Flow의 모든 버전 목록 조회"""
    try:
        # 먼저 기준 Flow 조회
        base_flow = db.query(Flow).filter(Flow.id == flow_id).first()
        if not base_flow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="플로우를 찾을 수 없습니다."
            )
        
        # 권한 확인
        if base_flow.owner_type == OwnerType.USER and base_flow.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 플로우에 접근할 권한이 없습니다."
            )
        
        # 동일한 플로우 그룹의 모든 버전 조회
        if base_flow.parent_flow_id:
            # 자식 버전인 경우, 부모 ID를 기준으로 조회
            parent_id = base_flow.parent_flow_id
        else:
            # 부모 버전인 경우, 자신의 ID를 기준으로 조회
            parent_id = base_flow.id
        
        versions = db.query(Flow).filter(
            or_(Flow.id == parent_id, Flow.parent_flow_id == parent_id)
        ).order_by(desc(Flow.version)).all()
        
        return [
            {
                "id": version.id,
                "version": version.version,
                "name": version.name,
                "is_latest": version.is_latest,
                "created_at": version.created_at.isoformat(),
                "updated_at": version.updated_at.isoformat(),
                "description": version.description
            }
            for version in versions
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting flow versions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="플로우 버전 목록 조회 중 오류가 발생했습니다."
        )

@router.post("/flows/{flow_id}/execute")
async def execute_flow(
    flow_id: int,
    request: ExecuteFlowRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Flow 실행"""
    try:
        # Flow 조회
        flow = db.query(Flow).filter(Flow.id == flow_id).first()
        if not flow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="플로우를 찾을 수 없습니다."
            )
        
        # 권한 확인
        if flow.owner_type == OwnerType.USER and flow.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 플로우를 실행할 권한이 없습니다."
            )
        
        # 실행 로그 생성
        execution_log = FlowExecutionLog(
            flow_id=flow.id,
            version=flow.version,
            user_id=current_user.id,
            inputs=request.inputs,
            status=ExecutionStatus.PENDING,
            created_at=datetime.utcnow()
        )
        
        db.add(execution_log)
        db.commit()
        db.refresh(execution_log)
        
        # 비동기 실행 시작 (실제 구현에서는 Celery 등 사용)
        try:
            # 실행 상태 업데이트
            execution_log.status = ExecutionStatus.RUNNING
            db.commit()
            
            # Flow 실행 엔진 호출
            from .services import FlowRunnerService
            runner = FlowRunnerService(db)
            
            start_time = datetime.utcnow()
            result = await runner.execute_flow(flow, request.inputs, current_user)
            end_time = datetime.utcnow()
            
            # 실행 완료 처리
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
            execution_log.status = ExecutionStatus.SUCCESS
            execution_log.outputs = result
            execution_log.execution_time_ms = execution_time_ms
            execution_log.completed_at = end_time
            
            # Flow 실행 통계 업데이트
            flow.execution_count += 1
            flow.last_executed = end_time
            
            db.commit()
            
            return {
                "success": True,
                "execution_id": str(execution_log.id),
                "status": "SUCCESS",
                "outputs": result,
                "execution_time_ms": execution_time_ms
            }
            
        except Exception as e:
            # 실행 실패 처리
            execution_log.status = ExecutionStatus.FAILURE
            execution_log.error_message = str(e)
            execution_log.completed_at = datetime.utcnow()
            db.commit()
            
            return {
                "success": False,
                "execution_id": str(execution_log.id),
                "status": "FAILURE",
                "error_message": str(e)
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing flow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="플로우 실행 중 오류가 발생했습니다."
        )

@router.get("/flows/{flow_id}/logs")
async def get_flow_execution_logs(
    flow_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 20,
    offset: int = 0
):
    """특정 Flow의 실행 기록 조회"""
    try:
        # Flow 권한 확인
        flow = db.query(Flow).filter(Flow.id == flow_id).first()
        if not flow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="플로우를 찾을 수 없습니다."
            )
        
        if flow.owner_type == OwnerType.USER and flow.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 플로우에 접근할 권한이 없습니다."
            )
        
        # 실행 로그 조회
        logs = db.query(FlowExecutionLog).filter(
            FlowExecutionLog.flow_id == flow_id
        ).order_by(desc(FlowExecutionLog.created_at)).offset(offset).limit(limit).all()
        
        return [
            {
                "id": str(log.id),
                "flow_id": log.flow_id,
                "version": log.version,
                "status": log.status.value,
                "inputs": log.inputs,
                "outputs": log.outputs,
                "error_message": log.error_message,
                "execution_time_ms": log.execution_time_ms,
                "tokens_used": log.tokens_used,
                "created_at": log.created_at.isoformat(),
                "completed_at": log.completed_at.isoformat() if log.completed_at else None,
                "executor": {
                    "id": str(log.executor.id),
                    "username": log.executor.username
                }
            }
            for log in logs
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution logs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="실행 기록 조회 중 오류가 발생했습니다."
        )

# Secret 관리 API (신규 추가)
@router.post("/secrets")
async def create_secret(
    request: CreateSecretRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """새 Secret 생성"""
    try:
        # 중복 이름 확인
        existing = db.query(Secret).filter(
            and_(
                Secret.name == request.name,
                Secret.owner_type == request.owner_type,
                Secret.owner_id == request.owner_id
            )
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="동일한 이름의 시크릿이 이미 존재합니다."
            )
        
        # 새 Secret 생성
        secret = Secret(
            name=request.name,
            description=request.description,
            owner_type=request.owner_type,
            owner_id=request.owner_id,
            category=request.category,
            tags=request.tags,
            created_by=current_user.id
        )
        
        # 값 암호화하여 설정
        secret.value = request.value
        
        db.add(secret)
        db.commit()
        db.refresh(secret)
        
        return {
            "success": True,
            "message": "시크릿이 성공적으로 생성되었습니다.",
            "secret": {
                "id": secret.id,
                "name": secret.name,
                "description": secret.description,
                "category": secret.category,
                "created_at": secret.created_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating secret: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="시크릿 생성 중 오류가 발생했습니다."
        )

@router.get("/secrets")
async def get_secrets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    owner_type: Optional[OwnerType] = None,
    owner_id: Optional[int] = None
):
    """Secret 목록 조회 (값은 제외)"""
    try:
        query = db.query(Secret)
        
        # 현재 사용자가 접근 가능한 Secret만 조회
        user_secrets = query.filter(
            and_(Secret.owner_type == OwnerType.USER, Secret.owner_id == current_user.id)
        )
        
        # TODO: 그룹 권한 체크 로직 추가
        
        secrets = user_secrets.order_by(desc(Secret.created_at)).all()
        
        return [
            {
                "id": secret.id,
                "name": secret.name,
                "description": secret.description,
                "category": secret.category,
                "owner_type": secret.owner_type.value,
                "owner_id": secret.owner_id,
                "tags": secret.tags or [],
                "last_used": secret.last_used.isoformat() if secret.last_used else None,
                "usage_count": secret.usage_count,
                "created_at": secret.created_at.isoformat(),
                "expires_at": secret.expires_at.isoformat() if secret.expires_at else None
            }
            for secret in secrets
        ]
        
    except Exception as e:
        logger.error(f"Error getting secrets: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="시크릿 목록 조회 중 오류가 발생했습니다."
        )

@router.get("/secrets/{secret_id}")
async def get_secret_value(
    secret_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Secret 값 조회 (복호화)"""
    try:
        secret = db.query(Secret).filter(Secret.id == secret_id).first()
        if not secret:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="시크릿을 찾을 수 없습니다."
            )
        
        # 권한 확인
        if secret.owner_type == OwnerType.USER and secret.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 시크릿에 접근할 권한이 없습니다."
            )
        
        # 사용 통계 업데이트
        secret.last_used = datetime.utcnow()
        secret.usage_count += 1
        db.commit()
        
        return {
            "id": secret.id,
            "name": secret.name,
            "value": secret.value,  # 복호화된 값 반환
            "description": secret.description,
            "category": secret.category
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting secret value: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="시크릿 값 조회 중 오류가 발생했습니다."
        )

# ==================== 워커 관리 및 웹훅 API (Phase 4) ====================

class FlowReloadRequest(BaseModel):
    """플로우 리로드 요청 모델"""
    reason: Optional[str] = None
    force: bool = False

def verify_admin_api_key(x_admin_api_key: str = Header(None, alias="X-Admin-API-Key")) -> bool:
    """
    관리자용 API 키 검증
    
    Args:
        x_admin_api_key: X-Admin-API-Key 헤더
        
    Returns:
        검증 성공 여부
        
    Raises:
        HTTPException: 인증 실패 시
    """
    expected_key = os.getenv('LLMOPS_ADMIN_API_KEY', 'default-admin-key-change-me')
    
    if not x_admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="관리자 API 키가 필요합니다.",
            headers={"X-Required-Header": "X-Admin-API-Key"}
        )
    
    if x_admin_api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="유효하지 않은 관리자 API 키입니다."
        )
    
    return True

@router.post("/admin/reload-flow/{project_id}/{flow_id}")
async def reload_flow_webhook(
    project_id: str,
    flow_id: str,
    request: FlowReloadRequest = FlowReloadRequest(),
    _: bool = Depends(verify_admin_api_key)
):
    """
    Flow Studio에서 플로우가 Publish될 때 호출되는 웹훅 엔드포인트
    기존 워커를 종료하고 새로운 플로우 데이터로 업데이트
    
    Args:
        project_id: 프로젝트 ID  
        flow_id: 플로우 ID
        request: 리로드 요청 데이터
        x_admin_api_key: 관리자 API 키 (헤더)
        
    Returns:
        리로드 결과
    """
    try:
        logger.info(f"플로우 리로드 웹훅 호출: {project_id}/{flow_id} - 사유: {request.reason}")
        
        # WorkerPoolManager를 통해 핫 리로딩 수행
        success = await worker_manager.reload_worker(project_id, flow_id)
        
        if success:
            return {
                "success": True,
                "message": f"플로우 {project_id}/{flow_id} 리로드 완료",
                "project_id": project_id,
                "flow_id": flow_id,
                "reason": request.reason,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "success": False,
                "message": f"플로우 {project_id}/{flow_id} 리로드 실패",
                "project_id": project_id,
                "flow_id": flow_id,
                "reason": request.reason,
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"플로우 리로드 웹훅 처리 실패: {project_id}/{flow_id} - {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"플로우 리로드 처리 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/admin/workers/stats")
async def get_worker_stats(
    _: bool = Depends(verify_admin_api_key)
):
    """
    워커 풀 통계 정보 조회 (관리자용)
    
    Returns:
        워커 풀 통계 정보
    """
    try:
        stats = await worker_manager.get_worker_stats()
        return {
            "success": True,
            "data": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"워커 통계 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"워커 통계 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/admin/workers/cleanup")
async def cleanup_workers(
    force: bool = False,
    _: bool = Depends(verify_admin_api_key)
):
    """
    유휴 워커 정리 (관리자용)
    
    Args:
        force: 강제 정리 여부
        
    Returns:
        정리 결과
    """
    try:
        # 현재는 가장 오래된 워커만 정리하지만, 추후 확장 가능
        await worker_manager._cleanup_oldest_worker()
        
        return {
            "success": True,
            "message": "워커 정리 완료",
            "force": force,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"워커 정리 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"워커 정리 중 오류가 발생했습니다: {str(e)}"
        )

class FlowExecuteRequest(BaseModel):
    """플로우 실행 요청 모델"""
    input_data: Dict[str, Any]
    parameters: Optional[Dict[str, Any]] = None
    stream: bool = False

class FlowTestRequest(BaseModel):
    """플로우 테스트 실행 요청 모델"""
    flow_data: Dict[str, Any]  # 노드와 엣지 정보
    input_data: Dict[str, Any]
    parameters: Optional[Dict[str, Any]] = None
    stream: bool = False

@router.post("/run-flow/{flow_id}")
async def run_flow_published(
    flow_id: str,
    request: FlowExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    게시된 플로우 실행 엔드포인트 (권한 기반)
    Flow Studio에서 게시된 플로우를 권한 검사 후 실행
    
    Args:
        flow_id: 플로우 ID (Flow Studio)
        request: 플로우 실행 요청
        current_user: 현재 사용자
        db: 데이터베이스 세션
        
    Returns:
        플로우 실행 결과 또는 스트리밍 응답
    """
    try:
        logger.info(f"게시된 플로우 실행 요청: {flow_id} - 사용자: {current_user.email}")
        
        # 사용자 그룹 정보 조회
        user_groups = [group.name for group in current_user.groups] if current_user.groups else []
        
        # 워커 가져오기 또는 생성 (권한 검사 포함)
        worker_result = await worker_manager.get_or_create_worker(
            project_id="published",  # 게시된 플로우는 프로젝트 ID를 "published"로 설정
            flow_id=flow_id,
            user_id=str(current_user.id),
            user_groups=user_groups
        )
        
        if worker_result is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="해당 플로우에 대한 실행 권한이 없거나 플로우를 찾을 수 없습니다."
            )
        
        worker_url, worker_port = worker_result
        
        # 워커에 플로우 실행 요청
        import httpx
        
        execution_params = request.parameters or {}
        execution_params.update({
            "user_id": current_user.id,
            "user_email": current_user.email,
            "user_name": current_user.real_name or current_user.display_name or current_user.email,
            "stream": request.stream
        })
        
        if request.stream:
            # 스트리밍 응답
            from fastapi.responses import StreamingResponse
            
            async def stream_proxy():
                async with httpx.AsyncClient() as client:
                    async with client.stream(
                        "POST",
                        f"{worker_url}/execute",
                        json={
                            "input_data": request.input_data,
                            "parameters": execution_params
                        },
                        timeout=120.0
                    ) as response:
                        if response.status_code != 200:
                            yield f"data: {{'type': 'error', 'error': '워커 실행 실패: {response.status_code}'}}\n\n"
                            return
                        
                        async for chunk in response.aiter_text():
                            yield chunk
            
            return StreamingResponse(
                stream_proxy(),
                media_type="text/plain",
                headers={
                    "X-Flow-ID": flow_id,
                    "X-Worker-Port": str(worker_port),
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive"
                }
            )
        else:
            # 일반 응답
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{worker_url}/execute",
                    json={
                        "input_data": request.input_data,
                        "parameters": execution_params
                    },
                    timeout=120.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"플로우 실행 완료: {flow_id}")
                    
                    return {
                        "success": True,
                        "flow_id": flow_id,
                        "worker_port": worker_port,
                        "result": result,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    logger.error(f"워커 플로우 실행 실패: {response.status_code} - {response.text}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="플로우 실행 중 오류가 발생했습니다."
                    )
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"게시된 플로우 실행 실패: {flow_id} - {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"플로우 실행 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/test-flow")
async def test_flow_execution(
    request: FlowTestRequest,
    current_user: User = Depends(get_current_user)
):
    """
    플로우 테스트 실행 엔드포인트 (Flow Studio 내부 테스트용)
    저장되지 않은 플로우를 임시로 실행하여 테스트
    
    Args:
        request: 플로우 테스트 요청 (flow_data, input_data 포함)
        current_user: 현재 사용자
        
    Returns:
        플로우 실행 결과 또는 스트리밍 응답
    """
    try:
        logger.info(f"플로우 테스트 실행 요청 - 사용자: {current_user.email}")
        
        # 디버깅을 위한 플로우 데이터 구조 로깅
        import json
        logger.info(f"플로우 데이터 구조: {json.dumps(request.flow_data, indent=2, ensure_ascii=False)}")
        
        # GraphBuilder를 직접 사용하여 테스트 실행
        from .graph_builder import GraphBuilder
        
        # 플로우 데이터 검증
        if not request.flow_data or 'nodes' not in request.flow_data or 'edges' not in request.flow_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="유효하지 않은 플로우 데이터입니다. nodes와 edges가 필요합니다."
            )
        
        # GraphBuilder로 체인 생성
        builder = GraphBuilder(request.flow_data)
        chain = builder.build()
        
        if chain is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="플로우를 실행 가능한 체인으로 변환할 수 없습니다."
            )
        
        # 입력 데이터 준비
        chain_input = request.input_data or {}
        
        # 텍스트 입력이 있는 경우 처리
        if isinstance(request.input_data, dict) and 'text' in request.input_data:
            chain_input = {"input": request.input_data['text']}
        elif isinstance(request.input_data, str):
            chain_input = {"input": request.input_data}
        elif not chain_input:
            chain_input = {"input": ""}
        
        # 파라미터 병합
        if request.parameters:
            chain_input.update(request.parameters)
        
        # 사용자 정보 추가
        chain_input.update({
            "user_id": current_user.id,
            "user_email": current_user.email,
            "user_name": current_user.real_name or current_user.display_name or current_user.email
        })
        
        if request.stream:
            # 스트리밍 응답
            from fastapi.responses import StreamingResponse
            import json
            import asyncio
            
            async def stream_test_execution():
                try:
                    # 시작 메시지
                    yield f"data: {json.dumps({'type': 'start', 'message': '플로우 테스트 시작'})}\n\n"
                    
                    # 노드 정보를 기반으로 실행 단계 정보 생성
                    nodes = request.flow_data.get('nodes', [])
                    step_info = []
                    for i, node in enumerate(nodes):
                        node_data = node.get('data', {})
                        step_info.append({
                            'step_index': i,
                            'node_id': node.get('id'),
                            'node_name': node_data.get('title', node_data.get('name', f'Node {i+1}')),
                            'node_type': node_data.get('category', 'unknown'),
                            'component_type': node_data.get('type', 'unknown')
                        })
                    
                    # 실행 단계 정보 전송
                    yield f"data: {json.dumps({'type': 'steps', 'steps': step_info})}\n\n"
                    
                    # 각 단계별로 시작 알림
                    step_start_times = {}
                    for step in step_info:
                        step_start_time = datetime.utcnow()
                        step_start_times[step['node_id']] = step_start_time
                        step_data = {**step, 'start_time': step_start_time.isoformat()}
                        yield f"data: {json.dumps({'type': 'step_start', 'step': step_data})}\n\n"
                        await asyncio.sleep(0.1)  # 단계별 지연
                    
                    # 스트리밍 실행 시도
                    if hasattr(chain, 'astream'):
                        async for chunk in chain.astream(chain_input):
                            chunk_data = {
                                'type': 'chunk',
                                'data': chunk if isinstance(chunk, (str, dict)) else str(chunk)
                            }
                            yield f"data: {json.dumps(chunk_data)}\n\n"
                    elif hasattr(chain, 'stream'):
                        for chunk in chain.stream(chain_input):
                            chunk_data = {
                                'type': 'chunk',
                                'data': chunk if isinstance(chunk, (str, dict)) else str(chunk)
                            }
                            yield f"data: {json.dumps(chunk_data)}\n\n"
                            await asyncio.sleep(0)
                    else:
                        # 스트리밍을 지원하지 않는 경우 일반 실행
                        if hasattr(chain, 'ainvoke'):
                            result = await chain.ainvoke(chain_input)
                        else:
                            result = chain.invoke(chain_input)
                        
                        result_data = {
                            'type': 'result',
                            'data': result if isinstance(result, (str, dict)) else str(result)
                        }
                        yield f"data: {json.dumps(result_data)}\n\n"
                    
                    # 각 단계별로 완료 알림
                    for step in step_info:
                        step_end_time = datetime.utcnow()
                        start_time = step_start_times.get(step['node_id'])
                        duration_ms = 0
                        if start_time:
                            duration_ms = int((step_end_time - start_time).total_seconds() * 1000)
                        
                        step_data = {
                            **step, 
                            'end_time': step_end_time.isoformat(),
                            'duration_ms': duration_ms
                        }
                        yield f"data: {json.dumps({'type': 'step_complete', 'step': step_data})}\n\n"
                        await asyncio.sleep(0.1)  # 단계별 지연
                    
                    # 완료 메시지
                    yield f"data: {json.dumps({'type': 'complete', 'message': '플로우 테스트 완료'})}\n\n"
                    
                except Exception as e:
                    error_data = {
                        'type': 'error',
                        'error': str(e)
                    }
                    yield f"data: {json.dumps(error_data)}\n\n"
            
            return StreamingResponse(
                stream_test_execution(),
                media_type="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive"
                }
            )
        else:
            # 일반 응답
            try:
                # 체인 실행
                if hasattr(chain, 'ainvoke'):
                    result = await chain.ainvoke(chain_input)
                else:
                    result = chain.invoke(chain_input)
                
                # 결과 포맷팅
                formatted_result = {
                    "success": True,
                    "result": result if isinstance(result, (str, dict)) else str(result),
                    "input": chain_input,
                    "timestamp": datetime.utcnow().isoformat(),
                    "execution_type": "test"
                }
                
                logger.info(f"플로우 테스트 실행 완료 - 사용자: {current_user.email}")
                return formatted_result
                
            except Exception as execution_error:
                logger.error(f"플로우 테스트 실행 실패: {execution_error}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"플로우 실행 중 오류가 발생했습니다: {str(execution_error)}"
                )
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"플로우 테스트 요청 처리 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"플로우 테스트 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/run/{project_id}/{flow_id}")
async def run_flow_worker(
    project_id: str,
    flow_id: str,
    input_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """
    플로우 실행 엔드포인트 (워커 기반) - Legacy 지원
    WorkerPoolManager를 통해 워커를 가져오거나 생성하고 플로우를 실행
    
    Args:
        project_id: 프로젝트 ID
        flow_id: 플로우 ID  
        input_data: 플로우 입력 데이터
        current_user: 현재 사용자
        
    Returns:
        플로우 실행 결과
    """
    try:
        logger.info(f"레거시 플로우 실행 요청: {project_id}/{flow_id} - 사용자: {current_user.email}")
        
        # 사용자 그룹 정보 조회
        user_groups = [group.name for group in current_user.groups] if current_user.groups else []
        
        # 워커 가져오기 또는 생성 (업데이트된 시그니처 사용)
        worker_result = await worker_manager.get_or_create_worker(
            project_id=project_id,
            flow_id=flow_id,
            user_id=str(current_user.id),
            user_groups=user_groups
        )
        
        if worker_result is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="플로우 워커를 생성할 수 없습니다."
            )
        
        worker_url, worker_port = worker_result
        
        # 워커에 플로우 실행 요청
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{worker_url}/execute",
                json={
                    "input_data": input_data,
                    "parameters": {
                        "user_id": current_user.id,
                        "user_email": current_user.email,
                        "user_name": current_user.real_name or current_user.display_name or current_user.email
                    }
                },
                timeout=60.0
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"플로우 실행 완료: {project_id}/{flow_id}")
                
                return {
                    "success": True,
                    "project_id": project_id,
                    "flow_id": flow_id,
                    "worker_port": worker_port,
                    "result": result,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                logger.error(f"워커 플로우 실행 실패: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="플로우 실행 중 오류가 발생했습니다."
                )
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"플로우 실행 실패: {project_id}/{flow_id} - {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"플로우 실행 중 오류가 발생했습니다: {str(e)}"
        ) 