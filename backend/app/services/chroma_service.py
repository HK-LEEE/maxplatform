"""
권한 기반 ChromaDB Collection 관리 서비스
ChromaDB와의 모든 상호작용을 관리합니다.
"""

import os
import uuid
import re
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

import chromadb
from sentence_transformers import SentenceTransformer
from fastapi import HTTPException

from ..schemas.chroma import ChromaCollectionCreate, ChromaCollectionResponse, ChromaDocumentAdd, ChromaQueryRequest

logger = logging.getLogger(__name__)

class ChromaService:
    """권한 기반 ChromaDB Collection 관리 서비스"""
    
    def __init__(self):
        self.client = None
        self.embedding_model = None
        self._initialize_client()
        self._initialize_embedding_model()
        # 메타데이터 저장을 위한 컬렉션 (권한 정보 저장)
        self.metadata_collection_name = "chroma-collections-metadata"
        self._ensure_metadata_collection()
    
    def _initialize_client(self):
        """ChromaDB 클라이언트 초기화"""
        try:
            chroma_host = os.getenv("CHROMA_HOST", "localhost")
            chroma_port = int(os.getenv("CHROMA_PORT", "8003"))
            chroma_path = os.getenv("CHROMA_PERSIST_PATH", "./chroma_data")
            
            logger.info(f"Initializing ChromaDB client with host={chroma_host}, port={chroma_port}, path={chroma_path}")
            
            if chroma_host == "localhost":
                os.makedirs(chroma_path, exist_ok=True)
                logger.info(f"Creating PersistentClient with path: {chroma_path}")
                self.client = chromadb.PersistentClient(path=chroma_path)
                logger.info(f"ChromaDB PersistentClient initialized with path: {chroma_path}")
            else:
                logger.info(f"Creating HttpClient with {chroma_host}:{chroma_port}")
                self.client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
                logger.info(f"ChromaDB HttpClient initialized with {chroma_host}:{chroma_port}")
            
            # 연결 테스트
            heartbeat = self.client.heartbeat()
            logger.info(f"ChromaDB connection successful: {heartbeat}")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail="ChromaDB 연결에 실패했습니다.")
    
    def _initialize_embedding_model(self):
        """임베딩 모델 초기화"""
        try:
            model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
            logger.info(f"Loading embedding model: {model_name}")
            self.embedding_model = SentenceTransformer(model_name)
            logger.info(f"Embedding model loaded successfully: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            # 임베딩 모델 로딩 실패 시 None으로 설정 (기본 임베딩 사용)
            self.embedding_model = None
            logger.warning("Embedding model not loaded, will use default ChromaDB embeddings")
    
    def _ensure_metadata_collection(self):
        """메타데이터 컬렉션 생성 (없는 경우)"""
        try:
            self.client.get_collection(name=self.metadata_collection_name)
        except:
            # 메타데이터 컬렉션이 없으면 생성 (기본 설정으로)
            self.client.create_collection(name=self.metadata_collection_name)
    
    def _get_collection_metadata(self, collection_name: str) -> Dict[str, Any]:
        """컬렉션 메타데이터 조회"""
        try:
            metadata_collection = self.client.get_collection(name=self.metadata_collection_name)
            
            # 컬렉션 이름으로 메타데이터 조회
            results = metadata_collection.get(
                ids=[collection_name],
                include=['metadatas']
            )
            
            if results['ids'] and len(results['ids']) > 0:
                # 메타데이터가 있으면 반환
                return results['metadatas'][0] if results['metadatas'] else {}
            else:
                # 메타데이터가 없으면 기본값 생성 및 저장
                default_metadata = {
                    "id": collection_name,
                    "owner_type": "user",
                    "owner_id": "unknown",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "is_active": True
                }
                
                # 기본 메타데이터 저장
                self._save_collection_metadata(collection_name, default_metadata)
                return default_metadata
                
        except Exception as e:
            logger.error(f"Failed to get collection metadata for {collection_name}: {str(e)}")
            # 오류 시 기본 메타데이터 반환
            return {
                "id": collection_name,
                "owner_type": "user",
                "owner_id": "unknown",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "is_active": True
            }
    
    def _save_collection_metadata(self, collection_name: str, metadata: Dict[str, Any]):
        """컬렉션 메타데이터 저장"""
        try:
            metadata_collection = self.client.get_collection(name=self.metadata_collection_name)
            
            # 메타데이터를 문서로 저장
            metadata_collection.upsert(
                ids=[collection_name],
                metadatas=[metadata],
                documents=[f"Metadata for collection: {collection_name}"]
            )
            
            logger.info(f"Saved metadata for collection: {collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to save collection metadata for {collection_name}: {str(e)}")
    
    def _check_collection_access(self, collection_info: Dict[str, Any], owner_type: str, owner_id: str) -> bool:
        """컬렉션 접근 권한 확인 (완화된 버전)"""
        try:
            collection_owner_type = collection_info.get("owner_type", "user")
            collection_owner_id = collection_info.get("owner_id", "")
            
            # 1. 소유자 타입과 ID가 일치하는지 확인
            if collection_owner_type == owner_type and collection_owner_id == owner_id:
                return True
            
            # 2. 메타데이터가 없거나 "unknown"인 경우 현재 사용자가 접근 가능하도록 처리
            if collection_owner_id in ["unknown", "", None]:
                logger.info(f"Collection has no owner metadata, allowing access and updating ownership")
                # 현재 사용자를 소유자로 설정
                self._update_collection_ownership(collection_info.get("id", ""), owner_type, owner_id)
                return True
            
            # 3. 개발 환경에서는 모든 컬렉션에 접근 가능 (임시)
            if os.getenv("ENVIRONMENT", "development") == "development":
                logger.info(f"Development mode: allowing access to all collections")
                return True
            
            # 4. 추가 권한 로직 (예: 그룹 멤버십, 공유 권한 등)
            # 현재는 기본적인 소유자 확인만 구현
            
            logger.info(f"Access denied for collection. Owner: {collection_owner_type}:{collection_owner_id}, Requester: {owner_type}:{owner_id}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to check collection access: {str(e)}")
            # 오류 발생 시 접근 허용 (안전한 기본값)
            return True
    
    def _update_collection_ownership(self, collection_name: str, owner_type: str, owner_id: str):
        """컬렉션 소유권 업데이트"""
        try:
            now = datetime.now()
            updated_metadata = {
                "id": collection_name,
                "owner_type": owner_type,
                "owner_id": owner_id,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "is_active": True,
                "migrated": True  # 마이그레이션된 컬렉션임을 표시
            }
            
            self._save_collection_metadata(collection_name, updated_metadata)
            logger.info(f"Updated ownership for collection {collection_name} to {owner_type}:{owner_id}")
            
        except Exception as e:
            logger.error(f"Failed to update collection ownership: {str(e)}")
    
    async def migrate_existing_collections(self, owner_type: str, owner_id: str) -> List[str]:
        """기존 컬렉션들을 현재 사용자 소유로 마이그레이션"""
        try:
            migrated_collections = []
            all_collections = self.client.list_collections()
            
            for collection in all_collections:
                if collection.name == self.metadata_collection_name:
                    continue
                
                # 현재 메타데이터 확인
                collection_info = self._get_collection_metadata(collection.name)
                current_owner_id = collection_info.get("owner_id", "")
                
                # 소유자가 없거나 "unknown"인 경우 마이그레이션
                if current_owner_id in ["unknown", "", None]:
                    self._update_collection_ownership(collection.name, owner_type, owner_id)
                    migrated_collections.append(collection.name)
                    logger.info(f"Migrated collection: {collection.name}")
            
            return migrated_collections
            
        except Exception as e:
            logger.error(f"Failed to migrate existing collections: {str(e)}")
            return []
    
    async def get_collections_by_owner(self, owner_type: str, owner_id: str) -> List[ChromaCollectionResponse]:
        """소유자별 Collection 목록 조회 (RAG 데이터소스 정보와 매핑)"""
        try:
            logger.info(f"Getting collections for owner_type={owner_type}, owner_id={owner_id}")
            
            # 기존 컬렉션들을 현재 사용자 소유로 마이그레이션
            migrated = await self.migrate_existing_collections(owner_type, owner_id)
            if migrated:
                logger.info(f"Migrated {len(migrated)} existing collections: {migrated}")
            
            # ChromaDB에서 모든 컬렉션 조회
            all_collections = self.client.list_collections()
            logger.info(f"Found {len(all_collections)} total collections in ChromaDB")
            
            # RAG 데이터소스와 매핑하기 위해 DB 세션 가져오기
            from sqlalchemy.orm import sessionmaker
            from ..database import engine
            from ..llmops.models import RAGDataSource
            
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            db = SessionLocal()
            
            try:
                # 모든 RAG 데이터소스 조회 (활성화된 것만)
                rag_datasources = db.query(RAGDataSource).filter(
                    RAGDataSource.is_active == True
                ).all()
                
                # chroma_collection_name을 키로 하는 매핑 딕셔너리 생성
                rag_mapping = {
                    ds.chroma_collection_name: {
                        'name': ds.name,
                        'description': ds.description or '',
                        'id': ds.id,
                        'owner_id': ds.owner_id,
                        'owner_type': ds.owner_type
                    }
                    for ds in rag_datasources
                }
                
                logger.info(f"[DEBUG] RAG datasource mapping: {list(rag_mapping.keys())}")
                
                result_collections = []
                
                # 메타데이터 컬렉션 제외하고 처리
                for collection in all_collections:
                    logger.info(f"Processing collection: {collection.name}")
                    if collection.name == self.metadata_collection_name:
                        logger.info(f"Skipping metadata collection: {collection.name}")
                        continue
                    
                    # 컬렉션 권한 정보 조회
                    collection_info = self._get_collection_metadata(collection.name)
                    logger.info(f"Collection {collection.name} metadata: {collection_info}")
                    
                    # 권한 확인
                    if self._check_collection_access(collection_info, owner_type, owner_id):
                        logger.info(f"User has access to collection: {collection.name}")
                        
                        # RAG 데이터소스 정보와 매핑
                        rag_info = rag_mapping.get(collection.name, {})
                        
                        if rag_info:
                            # RAG 데이터소스가 있는 경우 - 사용자 친화적인 이름 사용
                            display_name = f"{rag_info['name']} - {rag_info['description']}" if rag_info['description'] else rag_info['name']
                            description = rag_info['description']
                            logger.info(f"[DEBUG] Using RAG datasource info for {collection.name}: {display_name}")
                        else:
                            # RAG 데이터소스가 없는 경우 - 기본 컬렉션 이름 사용
                            display_name = collection.name
                            description = ""
                            logger.info(f"[DEBUG] Using collection name for {collection.name}: {display_name}")
                        
                        # ChromaCollectionResponse 객체 생성
                        chroma_collection = ChromaCollectionResponse(
                            id=collection_info.get("id", collection.name),
                            name=collection.name,  # 실제 ChromaDB 컬렉션 이름 (백엔드에서 사용)
                            display_name=display_name,  # 사용자에게 표시될 이름
                            description=description,  # 설명
                            metadata=collection.metadata or {},
                            owner_type=collection_info.get("owner_type", "user"),
                            owner_id=collection_info.get("owner_id", owner_id),
                            created_at=datetime.fromisoformat(collection_info.get("created_at", datetime.now().isoformat())),
                            updated_at=datetime.fromisoformat(collection_info.get("updated_at", datetime.now().isoformat())),
                            is_active=collection_info.get("is_active", True)
                        )
                        result_collections.append(chroma_collection)
                        logger.info(f"[DEBUG] Added collection {collection.name} with display_name: {display_name}")
                    else:
                        logger.info(f"User does not have access to collection: {collection.name}")
                
            finally:
                db.close()
            
            # 접근 가능한 컬렉션이 없고 마이그레이션된 것도 없다면 샘플 컬렉션 생성
            if len(result_collections) == 0 and len(migrated) == 0:
                logger.info("No accessible collections found and no migrations. Creating sample collections...")
                await self._create_sample_collections(owner_type, owner_id)
                
                # 다시 조회
                all_collections = self.client.list_collections()
                for collection in all_collections:
                    if collection.name == self.metadata_collection_name:
                        continue
                    
                    collection_info = self._get_collection_metadata(collection.name)
                    if self._check_collection_access(collection_info, owner_type, owner_id):
                        chroma_collection = ChromaCollectionResponse(
                            id=collection_info.get("id", collection.name),
                            name=collection.name,
                            display_name=collection.name,  # 샘플 컬렉션은 기본 이름 사용
                            description="",
                            metadata=collection.metadata or {},
                            owner_type=collection_info.get("owner_type", "user"),
                            owner_id=collection_info.get("owner_id", owner_id),
                            created_at=datetime.fromisoformat(collection_info.get("created_at", datetime.now().isoformat())),
                            updated_at=datetime.fromisoformat(collection_info.get("updated_at", datetime.now().isoformat())),
                            is_active=collection_info.get("is_active", True)
                        )
                        result_collections.append(chroma_collection)
            
            logger.info(f"Returning {len(result_collections)} collections for {owner_type}:{owner_id}")
            return result_collections
            
        except Exception as e:
            logger.error(f"Failed to get collections by owner: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            # 오류 발생 시 빈 목록 반환
            return []
    
    async def _create_sample_collections(self, owner_type: str, owner_id: str):
        """샘플 컬렉션 생성"""
        try:
            sample_collections = [
                {
                    "name": "user-documents",
                    "metadata": {"description": "사용자 문서 컬렉션"}
                },
                {
                    "name": "project-knowledge", 
                    "metadata": {"description": "프로젝트 지식베이스"}
                },
                {
                    "name": "research-papers",
                    "metadata": {"description": "연구 논문 컬렉션"}
                }
            ]
            
            for sample in sample_collections:
                collection_data = ChromaCollectionCreate(
                    name=sample["name"],
                    metadata=sample["metadata"],
                    owner_type=owner_type,
                    owner_id=owner_id
                )
                await self.create_collection(collection_data)
                
        except Exception as e:
            logger.error(f"Failed to create sample collections: {str(e)}")
    
    async def get_collection(self, collection_id: str) -> Optional[ChromaCollectionResponse]:
        """Collection 상세 정보 조회"""
        try:
            # 모든 컬렉션에서 ID로 검색
            all_collections = self.client.list_collections()
            
            for collection in all_collections:
                if collection.name == self.metadata_collection_name:
                    continue
                
                # 컬렉션 메타데이터 조회
                collection_info = self._get_collection_metadata(collection.name)
                
                # ID가 일치하는지 확인 (collection_id는 실제로는 name일 수도 있음)
                if collection_info.get("id") == collection_id or collection.name == collection_id:
                    return ChromaCollectionResponse(
                        id=collection_info.get("id", collection.name),
                        name=collection.name,
                        metadata=collection.metadata or {},
                        owner_type=collection_info.get("owner_type", "user"),
                        owner_id=collection_info.get("owner_id", "unknown"),
                        created_at=datetime.fromisoformat(collection_info.get("created_at", datetime.now().isoformat())),
                        updated_at=datetime.fromisoformat(collection_info.get("updated_at", datetime.now().isoformat())),
                        is_active=collection_info.get("is_active", True)
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get collection: {str(e)}")
            return None
    
    async def create_collection(self, collection_data: ChromaCollectionCreate) -> ChromaCollectionResponse:
        """새 Collection 생성"""
        try:
            logger.info(f"Creating collection: {collection_data.name}")
            logger.info(f"Collection metadata: {collection_data.metadata}")
            logger.info(f"Owner: {collection_data.owner_type}:{collection_data.owner_id}")
            
            # 컬렉션 이름 중복 확인
            try:
                existing_collection = self.client.get_collection(name=collection_data.name)
                if existing_collection:
                    raise HTTPException(status_code=400, detail="이미 존재하는 컬렉션 이름입니다.")
            except Exception as e:
                # 컬렉션이 존재하지 않으면 정상 (예외 무시)
                logger.info(f"Collection {collection_data.name} does not exist, proceeding with creation")
            
            # ChromaDB에 실제 컬렉션 생성
            logger.info(f"Creating ChromaDB collection with metadata: {collection_data.metadata}")
            chroma_collection = self.client.create_collection(
                name=collection_data.name,
                metadata=collection_data.metadata or {"hnsw:space": "cosine"}
            )
            logger.info(f"ChromaDB collection created successfully: {collection_data.name}")
            
            collection_id = str(uuid.uuid4())
            now = datetime.now()
            
            # 메타데이터 저장
            collection_metadata = {
                "id": collection_id,
                "owner_type": collection_data.owner_type,
                "owner_id": collection_data.owner_id,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "is_active": True
            }
            
            self._save_collection_metadata(collection_data.name, collection_metadata)
            
            logger.info(f"Created ChromaDB collection: {collection_data.name}")
            
            return ChromaCollectionResponse(
                id=collection_id,
                name=collection_data.name,
                metadata=collection_data.metadata or {},
                owner_type=collection_data.owner_type,
                owner_id=collection_data.owner_id,
                created_at=now,
                updated_at=now,
                is_active=True
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create collection: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail="Collection 생성에 실패했습니다.")
    
    async def delete_collection(self, collection_id: str):
        """Collection 삭제"""
        try:
            # 컬렉션 정보 조회
            collection_info = await self.get_collection(collection_id)
            if not collection_info:
                raise HTTPException(status_code=404, detail="Collection을 찾을 수 없습니다.")
            
            collection_name = collection_info.name
            
            # ChromaDB에서 실제 컬렉션 삭제
            self.client.delete_collection(name=collection_name)
            
            # 메타데이터에서도 삭제
            try:
                metadata_collection = self.client.get_collection(name=self.metadata_collection_name)
                metadata_collection.delete(ids=[collection_name])
            except Exception as e:
                logger.warning(f"Failed to delete metadata for collection {collection_name}: {str(e)}")
            
            logger.info(f"Deleted ChromaDB collection: {collection_name}")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete collection: {str(e)}")
            raise HTTPException(status_code=500, detail="Collection 삭제에 실패했습니다.")
    
    async def add_documents(self, collection_id: str, documents: ChromaDocumentAdd):
        """Collection에 문서 추가"""
        try:
            # 컬렉션 정보 조회
            collection_info = await self.get_collection(collection_id)
            if not collection_info:
                raise HTTPException(status_code=404, detail="Collection을 찾을 수 없습니다.")
            
            # ChromaDB 컬렉션 가져오기
            chroma_collection = self.client.get_collection(name=collection_info.name)
            
            # 문서 ID 생성 (제공되지 않은 경우)
            document_ids = documents.ids
            if not document_ids:
                document_ids = [str(uuid.uuid4()) for _ in documents.documents]
            elif len(document_ids) != len(documents.documents):
                raise HTTPException(status_code=400, detail="문서 수와 ID 수가 일치하지 않습니다.")
            
            # 임베딩 생성 (사용자 정의 임베딩 모델이 있는 경우)
            if self.embedding_model:
                embeddings = self.embedding_model.encode(documents.documents).tolist()
                # 문서 추가 (임베딩 포함)
                chroma_collection.add(
                    documents=documents.documents,
                    metadatas=documents.metadatas or [{}] * len(documents.documents),
                    ids=document_ids,
                    embeddings=embeddings
                )
            else:
                # 문서 추가 (ChromaDB 기본 임베딩 사용)
                chroma_collection.add(
                    documents=documents.documents,
                    metadatas=documents.metadatas or [{}] * len(documents.documents),
                    ids=document_ids
                )
            
            logger.info(f"Added {len(documents.documents)} documents to collection: {collection_info.name}")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to add documents: {str(e)}")
            raise HTTPException(status_code=500, detail="문서 추가에 실패했습니다.")

    async def query_documents(self, collection_id: str, query: ChromaQueryRequest):
        """Collection에서 문서 검색"""
        try:
            # 컬렉션 정보 조회
            collection_info = await self.get_collection(collection_id)
            if not collection_info:
                raise HTTPException(status_code=404, detail="Collection을 찾을 수 없습니다.")
            
            # ChromaDB 컬렉션 가져오기
            chroma_collection = self.client.get_collection(name=collection_info.name)
            
            # 문서 검색
            results = chroma_collection.query(
                query_texts=query.query_texts,
                n_results=query.n_results or 10,
                where=query.where,
                include=query.include or ["documents", "metadatas", "distances"]
            )
            
            logger.info(f"Queried collection: {collection_info.name} with {len(query.query_texts)} queries")
            return results
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to query documents: {str(e)}")
            raise HTTPException(status_code=500, detail="문서 검색에 실패했습니다.")
    
    # 추가 유틸리티 메서드들
    def list_collections(self) -> List[str]:
        """모든 컬렉션 목록 조회"""
        try:
            collections = self.client.list_collections()
            collection_names = [col.name for col in collections]
            logger.info(f"Retrieved {len(collection_names)} collections")
            return collection_names
        except Exception as e:
            logger.error(f"Failed to list ChromaDB collections: {str(e)}")
            return []
    
    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """컬렉션 통계 정보 조회"""
        try:
            collection = self.client.get_collection(name=collection_name)
            count = collection.count()
            
            return {
                "name": collection_name,
                "document_count": count,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats for collection {collection_name}: {str(e)}")
            return {"name": collection_name, "document_count": 0, "last_updated": None}
    
    def clear_collection(self, collection_name: str) -> bool:
        """컬렉션의 모든 문서 삭제"""
        try:
            collection = self.client.get_collection(name=collection_name)
            
            # 컬렉션의 모든 문서 ID 조회
            result = collection.get()
            if result['ids']:
                # 모든 문서 삭제
                collection.delete(ids=result['ids'])
                logger.info(f"Cleared {len(result['ids'])} documents from collection {collection_name}")
            else:
                logger.info(f"Collection {collection_name} is already empty")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear collection {collection_name}: {str(e)}")
            return False
    
    def _preprocess_query(self, query: str) -> str:
        """쿼리 전처리 - 한국어 검색 개선"""
        # 특수문자 제거 및 공백 정리
        query = re.sub(r'[^\w\s가-힣]', ' ', query)
        query = ' '.join(query.split())
        return query.strip()
    
    def _calculate_keyword_similarity(self, query: str, content: str) -> float:
        """키워드 기반 유사도 계산"""
        try:
            query_words = set(self._preprocess_query(query).split())
            content_words = set(self._preprocess_query(content).split())
            
            if not query_words:
                return 0.0
            
            # 교집합 비율
            intersection = len(query_words.intersection(content_words))
            return intersection / len(query_words)
            
        except Exception:
            return 0.0

    # RAG 서비스 호환성을 위한 추가 메서드들
    def hybrid_search(self, collection_name: str, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """하이브리드 검색 (벡터 + 키워드 기반)"""
        try:
            collection = self.client.get_collection(name=collection_name)
            
            # 벡터 검색
            vector_results = collection.query(
                query_texts=[query],
                n_results=n_results * 2,  # 더 많은 결과를 가져와서 하이브리드 점수로 재정렬
                include=["documents", "metadatas", "distances"]
            )
            
            # 결과 포맷팅 및 하이브리드 점수 계산
            hybrid_results = []
            if vector_results and 'documents' in vector_results and vector_results['documents']:
                documents = vector_results['documents'][0]
                metadatas = vector_results.get('metadatas', [[]])[0]
                distances = vector_results.get('distances', [[]])[0]
                ids = vector_results.get('ids', [[]])[0]
                
                for i, doc in enumerate(documents):
                    metadata = metadatas[i] if i < len(metadatas) else {}
                    distance = distances[i] if i < len(distances) else 1.0
                    doc_id = ids[i] if i < len(ids) else f"doc_{i}"
                    
                    # 벡터 유사도 (거리를 유사도로 변환)
                    vector_similarity = max(0, 1 - distance)
                    
                    # 키워드 유사도
                    keyword_similarity = self._calculate_keyword_similarity(query, doc)
                    
                    # 하이브리드 점수 (가중 평균)
                    hybrid_score = (vector_similarity * 0.7) + (keyword_similarity * 0.3)
                    
                    hybrid_results.append({
                        "id": doc_id,
                        "content": doc,
                        "similarity": hybrid_score,
                        "distance": distance,
                        "vector_score": vector_similarity,
                        "keyword_score": keyword_similarity,
                        "metadata": metadata
                    })
                
                # 하이브리드 점수로 정렬하고 상위 n_results개만 반환
                hybrid_results.sort(key=lambda x: x["similarity"], reverse=True)
                hybrid_results = hybrid_results[:n_results]
            
            logger.info(f"Hybrid search completed for collection {collection_name}: {len(hybrid_results)} results")
            return hybrid_results
            
        except Exception as e:
            logger.error(f"Failed to perform hybrid search on collection {collection_name}: {str(e)}")
            raise
    
    def query_documents_simple(self, collection_name: str, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """간단한 문서 검색 (RAG 서비스 호환성을 위한 메서드)"""
        try:
            collection = self.client.get_collection(name=collection_name)
            
            # 문서 검색
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            # 결과 포맷팅
            formatted_results = []
            if results and 'documents' in results and results['documents']:
                documents = results['documents'][0]
                metadatas = results.get('metadatas', [[]])[0]
                distances = results.get('distances', [[]])[0]
                ids = results.get('ids', [[]])[0]
                
                for i, doc in enumerate(documents):
                    metadata = metadatas[i] if i < len(metadatas) else {}
                    distance = distances[i] if i < len(distances) else 1.0
                    doc_id = ids[i] if i < len(ids) else f"doc_{i}"
                    
                    # 거리를 유사도로 변환
                    similarity = max(0, 1 - distance)
                    
                    formatted_results.append({
                        "id": doc_id,
                        "content": doc,
                        "similarity": similarity,
                        "distance": distance,
                        "metadata": metadata
                    })
            
            logger.info(f"Simple query completed for collection {collection_name}: {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to query documents from collection {collection_name}: {str(e)}")
            raise
    
    def get_documents(self, collection_name: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """컬렉션의 문서 목록 조회 (페이지네이션 지원)"""
        try:
            collection = self.client.get_collection(name=collection_name)
            
            # 전체 문서 수 조회
            total_count = collection.count()
            
            # 페이지네이션 계산
            offset = (page - 1) * page_size
            limit = page_size
            
            # 문서 조회
            results = collection.get(
                limit=limit,
                offset=offset,
                include=["documents", "metadatas"]
            )
            
            # 결과 포맷팅
            documents = []
            if results and 'documents' in results:
                for i, doc in enumerate(results['documents']):
                    metadata = results.get('metadatas', [])[i] if i < len(results.get('metadatas', [])) else {}
                    doc_id = results.get('ids', [])[i] if i < len(results.get('ids', [])) else f"doc_{i}"
                    
                    documents.append({
                        "id": doc_id,
                        "content": doc[:200] + "..." if len(doc) > 200 else doc,  # 미리보기용으로 제한
                        "full_content": doc,
                        "metadata": metadata
                    })
            
            return {
                "documents": documents,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": (total_count + page_size - 1) // page_size,
                    "has_next": page * page_size < total_count,
                    "has_prev": page > 1
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get documents from collection {collection_name}: {str(e)}")
            raise
    
    def delete_document(self, collection_name: str, document_id: str) -> bool:
        """컬렉션에서 특정 문서 삭제"""
        try:
            collection = self.client.get_collection(name=collection_name)
            
            # 문서 삭제
            collection.delete(ids=[document_id])
            
            logger.info(f"Document {document_id} deleted from collection {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document {document_id} from collection {collection_name}: {str(e)}")
            return False


# 전역 ChromaService 인스턴스
_chroma_service_instance = None

def get_chroma_service() -> ChromaService:
    """ChromaService 싱글톤 인스턴스 반환"""
    global _chroma_service_instance
    if _chroma_service_instance is None:
        _chroma_service_instance = ChromaService()
    return _chroma_service_instance
