from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging

from ..database import get_db
from ..models.user import User
from ..models.workspace import Workspace
from ..schemas.chroma import ChromaCollectionCreate, ChromaCollectionResponse, ChromaDocumentAdd, ChromaQueryRequest
from ..services.chroma_service import ChromaService
from ..utils.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chroma", tags=["chroma"])

@router.get("/collections", response_model=List[ChromaCollectionResponse])
async def get_collections(
    request: Request,
    owner_type: str = Query(..., description="Owner type: 'user' or 'group'"),
    owner_id: str = Query(..., description="Owner ID (user_id or group_id)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    사용자/그룹 권한에 따른 ChromaDB Collection 목록 조회
    """
    try:
        chroma_service = ChromaService()
        
        # 권한 검증
        if owner_type == "user":
            if owner_id != str(current_user.id):
                raise HTTPException(status_code=403, detail="Access denied to user collections")
        elif owner_type == "group":
            # 그룹 권한 검증 로직 (실제 구현 필요)
            workspace = db.query(Workspace).filter(
                Workspace.id == owner_id,
                Workspace.created_by == current_user.id
            ).first()
            if not workspace:
                raise HTTPException(status_code=403, detail="Access denied to group collections")
        else:
            raise HTTPException(status_code=400, detail="Invalid owner_type")
        
        collections = await chroma_service.get_collections_by_owner(owner_type, owner_id)
        return collections
        
    except Exception as e:
        logger.error(f"Failed to get collections: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get collections: {str(e)}")

@router.get("/collections/{collection_id}", response_model=ChromaCollectionResponse)
async def get_collection(
    request: Request,
    collection_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Collection 상세 정보 조회
    """
    try:
        chroma_service = ChromaService()
        collection = await chroma_service.get_collection(collection_id)
        
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")
        
        # 권한 검증
        if collection.owner_type == "user" and collection.owner_id != str(current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")
        elif collection.owner_type == "group":
            # 그룹 권한 검증 로직
            workspace = db.query(Workspace).filter(
                Workspace.id == collection.owner_id,
                Workspace.created_by == current_user.id
            ).first()
            if not workspace:
                raise HTTPException(status_code=403, detail="Access denied")
        
        return collection
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get collection: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get collection: {str(e)}")

@router.post("/collections", response_model=ChromaCollectionResponse)
async def create_collection(
    request: Request,
    collection_data: ChromaCollectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    새 Collection 생성
    """
    try:
        # 권한 검증
        if collection_data.owner_type == "user":
            if collection_data.owner_id != str(current_user.id):
                raise HTTPException(status_code=403, detail="Cannot create collection for other users")
        elif collection_data.owner_type == "group":
            # 그룹 권한 검증
            workspace = db.query(Workspace).filter(
                Workspace.id == collection_data.owner_id,
                Workspace.created_by == current_user.id
            ).first()
            if not workspace:
                raise HTTPException(status_code=403, detail="Access denied to group")
        
        chroma_service = ChromaService()
        collection = await chroma_service.create_collection(collection_data)
        return collection
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create collection: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create collection: {str(e)}")

@router.delete("/collections/{collection_id}")
async def delete_collection(
    request: Request,
    collection_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Collection 삭제
    """
    try:
        chroma_service = ChromaService()
        collection = await chroma_service.get_collection(collection_id)
        
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")
        
        # 권한 검증
        if collection.owner_type == "user" and collection.owner_id != str(current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")
        elif collection.owner_type == "group":
            workspace = db.query(Workspace).filter(
                Workspace.id == collection.owner_id,
                Workspace.created_by == current_user.id
            ).first()
            if not workspace:
                raise HTTPException(status_code=403, detail="Access denied")
        
        await chroma_service.delete_collection(collection_id)
        return {"message": "Collection deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete collection: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete collection: {str(e)}")

@router.post("/collections/{collection_id}/documents")
async def add_documents(
    request: Request,
    collection_id: str,
    documents: ChromaDocumentAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Collection에 문서 추가
    """
    try:
        chroma_service = ChromaService()
        collection = await chroma_service.get_collection(collection_id)
        
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")
        
        # 권한 검증
        if collection.owner_type == "user" and collection.owner_id != str(current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")
        elif collection.owner_type == "group":
            workspace = db.query(Workspace).filter(
                Workspace.id == collection.owner_id,
                Workspace.created_by == current_user.id
            ).first()
            if not workspace:
                raise HTTPException(status_code=403, detail="Access denied")
        
        await chroma_service.add_documents(collection_id, documents)
        return {"message": "Documents added successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add documents: {str(e)}")

@router.post("/collections/{collection_id}/query")
async def query_documents(
    request: Request,
    collection_id: str,
    query: ChromaQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Collection에서 문서 검색
    """
    try:
        chroma_service = ChromaService()
        collection = await chroma_service.get_collection(collection_id)
        
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")
        
        # 권한 검증
        if collection.owner_type == "user" and collection.owner_id != str(current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")
        elif collection.owner_type == "group":
            workspace = db.query(Workspace).filter(
                Workspace.id == collection.owner_id,
                Workspace.created_by == current_user.id
            ).first()
            if not workspace:
                raise HTTPException(status_code=403, detail="Access denied")
        
        results = await chroma_service.query_documents(collection_id, query)
        return {"success": True, "data": results}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to query documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to query documents: {str(e)}")

@router.get("/debug/all-collections")
async def debug_all_collections(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    디버깅용: ChromaDB의 모든 컬렉션과 메타데이터 조회
    """
    try:
        chroma_service = ChromaService()
        
        # 모든 컬렉션 조회
        all_collections = chroma_service.client.list_collections()
        
        debug_info = {
            "total_collections": len(all_collections),
            "current_user": {
                "id": str(current_user.id),
                "email": current_user.email
            },
            "collections": []
        }
        
        for collection in all_collections:
            # 각 컬렉션의 메타데이터 조회
            collection_metadata = chroma_service._get_collection_metadata(collection.name)
            
            debug_info["collections"].append({
                "name": collection.name,
                "chroma_metadata": collection.metadata,
                "stored_metadata": collection_metadata,
                "document_count": collection.count() if hasattr(collection, 'count') else 0
            })
        
        return debug_info
        
    except Exception as e:
        logger.error(f"Failed to get debug info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get debug info: {str(e)}")

@router.post("/migrate-collections")
async def migrate_collections(
    request: Request,
    owner_type: str = Query("user", description="Owner type: 'user' or 'group'"),
    owner_id: str = Query(None, description="Owner ID (if not provided, uses current user)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    기존 컬렉션들을 현재 사용자 소유로 마이그레이션
    """
    try:
        chroma_service = ChromaService()
        
        # owner_id가 제공되지 않으면 현재 사용자 ID 사용
        if not owner_id:
            owner_id = str(current_user.id)
        
        # 권한 검증
        if owner_type == "user" and owner_id != str(current_user.id):
            raise HTTPException(status_code=403, detail="Cannot migrate collections for other users")
        
        # 마이그레이션 실행
        migrated_collections = await chroma_service.migrate_existing_collections(owner_type, owner_id)
        
        return {
            "message": f"Successfully migrated {len(migrated_collections)} collections",
            "migrated_collections": migrated_collections,
            "owner_type": owner_type,
            "owner_id": owner_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to migrate collections: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to migrate collections: {str(e)}") 