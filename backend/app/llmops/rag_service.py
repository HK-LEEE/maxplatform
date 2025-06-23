"""
RAG 데이터소스 관리 서비스

RAG 데이터소스의 생성, 관리, 문서 업로드, 검색 등을 담당합니다.
"""

import uuid
import re
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session
from fastapi import HTTPException, status, UploadFile
from langchain.text_splitter import RecursiveCharacterTextSplitter

from ..models.user import User
from .models import RAGDataSource, OwnerType
from .auth import LLMOpsAuthService
from ..services.chroma_service import ChromaService
from ..schemas.chroma import ChromaCollectionCreate, ChromaDocumentAdd, ChromaQueryRequest
from .file_storage_service import FileStorageService

import logging
import time

logger = logging.getLogger(__name__)

class RAGDataSourceService:
    """RAG 데이터소스 관리 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.chroma_service = ChromaService()
        self.auth_service = LLMOpsAuthService(db)
        self.file_storage_service = FileStorageService()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
    
    def _validate_datasource_name(self, name: str) -> None:
        """데이터소스 이름 검증"""
        if not name or not name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="데이터소스 이름은 필수입니다."
            )
        
        # 길이 검증
        if len(name.strip()) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="데이터소스 이름은 최소 2자 이상이어야 합니다."
            )
        
        if len(name.strip()) > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="데이터소스 이름은 최대 50자까지 입력할 수 있습니다."
            )
        
        # 영어, 숫자, 공백, 하이픈, 밑줄만 허용
        english_pattern = re.compile(r'^[a-zA-Z0-9\s\-_]+$')
        if not english_pattern.match(name.strip()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="데이터소스 이름은 영어, 숫자, 공백, 하이픈(-), 밑줄(_)만 사용할 수 있습니다."
            )
    
    async def create_datasource(
        self, 
        name: str, 
        description: Optional[str],
        owner_type: OwnerType,
        owner_id: str,
        current_user: User,
        embedding_config: Optional[Dict] = None
    ) -> RAGDataSource:
        """새 RAG 데이터소스 생성"""
        try:
            # 이름 검증
            self._validate_datasource_name(name)
            
            # 권한 확인
            if not self.auth_service.can_create_rag_datasource(current_user, owner_type, owner_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="데이터소스 생성 권한이 없습니다."
                )
            
            # ChromaDB 컬렉션 이름 생성 (영숫자와 밑줄만 사용)
            # 형식: {owner_type}_{clean_owner_id}_{unique_id}_{safe_name}
            unique_id = uuid.uuid4().hex[:8]
            
            # owner_id에서 하이픈 제거 (UUID의 경우)
            clean_owner_id = owner_id.replace("-", "")
            
            # 이름에서 영숫자만 추출 (공백, 하이픈을 밑줄로 변환)
            safe_name = re.sub(r'[^a-zA-Z0-9]', '_', name.strip())[:20]
            safe_name = re.sub(r'_+', '_', safe_name)  # 연속된 밑줄 제거
            safe_name = safe_name.strip('_')  # 앞뒤 밑줄 제거
            
            if not safe_name:  # 영숫자가 없는 경우 기본값 사용
                safe_name = "datasource"
            
            if owner_type == OwnerType.GROUP:
                collection_name = f"group_{clean_owner_id}_{unique_id}_{safe_name}"
            else:  # USER
                collection_name = f"user_{clean_owner_id}_{unique_id}_{safe_name}"
            
            # 컬렉션 이름이 ChromaDB 규칙에 맞는지 확인
            if len(collection_name) < 3 or len(collection_name) > 63:
                # 길이가 맞지 않으면 단순화
                collection_name = f"user_{clean_owner_id[:8]}_{unique_id}"
            
            logger.info(f"Creating RAG datasource with collection: {collection_name}")
            logger.info(f"Collection name length: {len(collection_name)}")
            logger.info(f"Owner type: {owner_type.value}, Owner ID: {owner_id}")
            logger.info(f"Created by user: {current_user.id}")
            
            # 데이터소스 생성
            datasource = RAGDataSource(
                name=name,
                description=description,
                owner_type=owner_type,
                owner_id=owner_id,
                created_by=current_user.id,
                chroma_collection_name=collection_name,  # 미리 설정
                embedding_config=embedding_config or {
                    "model": "all-MiniLM-L6-v2",
                    "chunk_size": 1000,
                    "chunk_overlap": 200
                }
            )
            
            # DB에 추가하고 ID 생성
            self.db.add(datasource)
            self.db.flush()  # ID 생성을 위해 flush
            
            # ChromaDB 컬렉션 생성 (확장된 메타데이터 포함)
            collection_metadata = {
                "datasource_id": datasource.id,
                "owner_type": owner_type.value,
                "owner_id": owner_id,
                "created_by": str(current_user.id),
                "created_at": datetime.now().isoformat(),
                "datasource_name": name,
                "access_level": "group" if owner_type == OwnerType.GROUP else "private"
            }
            
            # ChromaCollectionCreate 객체 생성
            collection_create = ChromaCollectionCreate(
                name=collection_name,
                metadata=collection_metadata,
                owner_type=owner_type.value,
                owner_id=owner_id
            )
            
            # ChromaDB 컬렉션 생성
            await self.chroma_service.create_collection(collection_create)
            
            self.db.commit()
            logger.info(f"RAG datasource created successfully: {datasource.id} (collection: {collection_name})")
            
            return datasource
            
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create RAG datasource: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="데이터소스 생성에 실패했습니다."
            )
    
    def get_datasource_list(self, current_user: User) -> List[Dict[str, Any]]:
        """현재 사용자가 접근 가능한 RAG 데이터소스 목록 조회"""
        try:
            from .auth import LLMOpsAuthService
            auth_service = LLMOpsAuthService(self.db)
            
            # 접근 가능한 데이터소스 조회
            accessible_datasources = auth_service.get_accessible_rag_datasources(current_user)
            
            result = []
            for datasource in accessible_datasources:
                try:
                    # ChromaDB에서 실시간 문서 수 조회
                    stats = self.chroma_service.get_collection_stats(datasource.chroma_collection_name)
                    actual_document_count = stats.get("document_count", 0)
                    
                    # 데이터베이스의 문서 수와 실제 ChromaDB 문서 수가 다르면 업데이트
                    if datasource.document_count != actual_document_count:
                        datasource.document_count = actual_document_count
                        self.db.commit()
                        logger.info(f"Updated document count for datasource {datasource.id}: {actual_document_count}")
                    
                    # 소유자 정보 구성
                    if datasource.owner_type == OwnerType.USER:
                        # 사용자 정보 조회
                        from ..models.user import User
                        owner_user = self.db.query(User).filter(User.id == datasource.owner_id).first()
                        owner_info = {
                            "type": "USER",
                            "name": f"{owner_user.display_name or owner_user.real_name}" if owner_user else f"사용자 {datasource.owner_id}"
                        }
                    else:  # GROUP
                        # 그룹 정보 조회
                        from ..models.user import Group
                        group = self.db.query(Group).filter(Group.id == int(datasource.owner_id)).first()
                        owner_info = {
                            "type": "GROUP", 
                            "name": group.name if group else f"그룹 {datasource.owner_id}"
                        }
                    
                    result.append({
                        "id": datasource.id,
                        "name": datasource.name,
                        "description": datasource.description,
                        "owner": owner_info,
                        "document_count": actual_document_count,  # 실시간 문서 수 사용
                        "is_active": datasource.is_active,
                        "created_at": datasource.created_at.isoformat(),
                        "last_updated": datasource.last_updated.isoformat(),
                        "tags": datasource.tags or []
                    })
                    
                except Exception as e:
                    logger.error(f"Error getting stats for datasource {datasource.id}: {str(e)}")
                    # ChromaDB 오류 시 데이터베이스 값 사용
                    if datasource.owner_type == OwnerType.USER:
                        from ..models.user import User
                        owner_user = self.db.query(User).filter(User.id == datasource.owner_id).first()
                        owner_info = {
                            "type": "USER",
                            "name": f"{owner_user.display_name or owner_user.real_name}" if owner_user else f"사용자 {datasource.owner_id}"
                        }
                    else:
                        from ..models.user import Group
                        group = self.db.query(Group).filter(Group.id == int(datasource.owner_id)).first()
                        owner_info = {
                            "type": "GROUP", 
                            "name": group.name if group else f"그룹 {datasource.owner_id}"
                        }
                    
                    result.append({
                        "id": datasource.id,
                        "name": datasource.name,
                        "description": datasource.description,
                        "owner": owner_info,
                        "document_count": datasource.document_count,  # 데이터베이스 값 사용
                        "is_active": datasource.is_active,
                        "created_at": datasource.created_at.isoformat(),
                        "last_updated": datasource.last_updated.isoformat(),
                        "tags": datasource.tags or []
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get datasource list: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="데이터소스 목록 조회에 실패했습니다."
            )
    
    async def upload_documents(
        self, 
        datasource: RAGDataSource, 
        files: List[UploadFile],
        current_user: User
    ) -> Dict[str, Any]:
        """데이터소스에 문서 업로드 (파일 저장 관리 포함)"""
        try:
            uploaded_docs = []
            failed_files = []
            stored_files = []
            
            for file in files:
                try:
                    # 파일을 저장소에 저장
                    file_info = await self.file_storage_service.save_uploaded_file(
                        file, datasource, current_user
                    )
                    stored_files.append(file_info)
                    
                    # 파일 내용 읽기 (저장된 파일에서)
                    with open(file_info["file_path"], "rb") as f:
                        content = f.read()
                    
                    # 파일 타입에 따른 텍스트 추출
                    text_content = self._extract_text_from_file(content, file.filename)
                    
                    if not text_content.strip():
                        failed_files.append({
                            "filename": file.filename, 
                            "error": "파일에서 텍스트를 추출할 수 없습니다.",
                            "stored_file": file_info["stored_filename"]
                        })
                        continue
                    
                    # 텍스트 청킹
                    chunks = self.text_splitter.split_text(text_content)
                    
                    # 각 청크를 문서로 변환
                    for i, chunk in enumerate(chunks):
                        doc_id = f"{file.filename}_{i}_{uuid.uuid4().hex[:8]}"
                        uploaded_docs.append({
                            "id": doc_id,
                            "content": chunk,
                            "metadata": {
                                "filename": file.filename,
                                "stored_filename": file_info["stored_filename"],
                                "chunk_index": i,
                                "total_chunks": len(chunks),
                                "uploaded_by": str(current_user.id),
                                "upload_time": datetime.now().isoformat(),
                                "file_size": len(content),
                                "file_type": self._get_file_type(file.filename),
                                "storage_path": file_info["relative_path"],
                                "original_file_path": file_info["file_path"]
                            }
                        })
                    
                    logger.info(f"Processed file {file.filename}: {len(chunks)} chunks, stored as {file_info['stored_filename']}")
                    
                except Exception as e:
                    logger.error(f"Failed to process file {file.filename}: {str(e)}")
                    failed_files.append({
                        "filename": file.filename, 
                        "error": str(e),
                        "stored_file": None
                    })
            
            # ChromaDB에 문서 추가
            if uploaded_docs:
                # ChromaDocumentAdd 객체 생성
                documents_to_add = ChromaDocumentAdd(
                    documents=[doc["content"] for doc in uploaded_docs],
                    metadatas=[doc["metadata"] for doc in uploaded_docs],
                    ids=[doc["id"] for doc in uploaded_docs]
                )
                
                # collection_name을 collection_id로 사용 (ChromaService에서 name으로도 검색 가능)
                await self.chroma_service.add_documents(
                    datasource.chroma_collection_name,
                    documents_to_add
                )
                
                # 데이터소스 문서 수 업데이트
                datasource.document_count += len(uploaded_docs)
                datasource.last_updated = datetime.now()
                self.db.commit()
            
            return {
                "success": True,
                "uploaded_documents": len(uploaded_docs),
                "failed_files": failed_files,
                "total_files_processed": len(files),
                "stored_files": stored_files,
                "storage_stats": self.file_storage_service.get_storage_stats(
                    datasource.owner_type, 
                    datasource.owner_id
                )
            }
            
        except Exception as e:
            logger.error(f"Failed to upload documents to datasource {datasource.id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="문서 업로드에 실패했습니다."
            )
    
    def _extract_text_from_file(self, content: bytes, filename: str) -> str:
        """파일 타입에 따라 텍스트 추출"""
        try:
            file_extension = filename.lower().split('.')[-1] if '.' in filename else ''
            
            if file_extension == 'pdf':
                return self._extract_text_from_pdf(content)
            elif file_extension in ['txt', 'md', 'py', 'js', 'html', 'css', 'json', 'xml']:
                # 텍스트 파일들은 여러 인코딩으로 시도
                for encoding in ['utf-8', 'cp949', 'euc-kr', 'latin-1']:
                    try:
                        return content.decode(encoding)
                    except UnicodeDecodeError:
                        continue
                # 모든 인코딩 실패 시 에러 처리
                return content.decode('utf-8', errors='ignore')
            else:
                # 기본적으로 UTF-8로 시도, 실패하면 무시하고 디코딩
                try:
                    return content.decode('utf-8')
                except UnicodeDecodeError:
                    return content.decode('utf-8', errors='ignore')
                    
        except Exception as e:
            logger.error(f"Failed to extract text from {filename}: {str(e)}")
            raise Exception(f"텍스트 추출 실패: {str(e)}")
    
    def _extract_text_from_pdf(self, content: bytes) -> str:
        """PDF 파일에서 텍스트 추출 (OCR 지원 포함)"""
        try:
            import io
            import pdfplumber
            from PyPDF2 import PdfReader
            
            # pdfplumber를 먼저 시도 (한글 지원이 더 좋음)
            try:
                with pdfplumber.open(io.BytesIO(content)) as pdf:
                    text_parts = []
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                    
                    extracted_text = '\n'.join(text_parts)
                    
                    if len(extracted_text.strip()) > 50:
                        logger.info(f"Successfully extracted {len(extracted_text)} characters using pdfplumber")
                        return extracted_text
                        
            except Exception as e:
                logger.warning(f"pdfplumber failed: {str(e)}, trying PyPDF2")
            
            # pdfplumber 실패 시 PyPDF2 시도
            try:
                pdf_reader = PdfReader(io.BytesIO(content))
                text_parts = []
                
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                
                extracted_text = '\n'.join(text_parts)
                
                if len(extracted_text.strip()) > 50:
                    logger.info(f"Successfully extracted {len(extracted_text)} characters using PyPDF2")
                    return extracted_text
                    
            except Exception as e:
                logger.warning(f"PyPDF2 failed: {str(e)}")
            
            # 텍스트 추출 실패 시 OCR 시도
            logger.info("Attempting OCR extraction for scanned PDF")
            return self._extract_text_with_ocr(content)
            
        except Exception as e:
            logger.error(f"PDF text extraction failed: {str(e)}")
            raise Exception(f"PDF 파일 처리 실패: {str(e)}")
    
    def _extract_text_with_ocr(self, content: bytes) -> str:
        """OCR을 사용하여 스캔된 PDF에서 텍스트 추출"""
        try:
            import io
            from PIL import Image, ImageEnhance
            import pytesseract
            from pdf2image import convert_from_bytes
            
            logger.info("Starting OCR extraction from PDF")
            
            # PDF를 이미지로 변환
            try:
                images = convert_from_bytes(content, dpi=300)
                logger.info(f"Converted PDF to {len(images)} images")
            except Exception as e:
                logger.error(f"Failed to convert PDF to images: {str(e)}")
                # poppler가 설치되지 않은 경우 사용자에게 안내
                if "poppler" in str(e).lower() or "pdftoppm" in str(e).lower():
                    raise Exception("PDF를 이미지로 변환할 수 없습니다. OCR 기능을 사용하려면 poppler-utils를 설치해주세요. 설치 가이드: backend/OCR_SETUP.md 참조")
                else:
                    raise Exception(f"PDF를 이미지로 변환할 수 없습니다: {str(e)}")
            
            # 각 페이지에서 텍스트 추출
            extracted_texts = []
            
            for i, image in enumerate(images):
                try:
                    # 이미지 전처리
                    processed_image = self._preprocess_image_for_ocr(image)
                    
                    # OCR 수행
                    page_text = pytesseract.image_to_string(
                        processed_image, 
                        lang='kor+eng',  # 한국어 + 영어
                        config='--psm 3 --oem 3'  # 페이지 분할 모드와 OCR 엔진 모드
                    )
                    
                    if page_text.strip():
                        extracted_texts.append(page_text.strip())
                        logger.info(f"OCR extracted {len(page_text)} characters from page {i+1}")
                    
                except Exception as e:
                    logger.warning(f"OCR failed for page {i+1}: {str(e)}")
                    continue
            
            if not extracted_texts:
                raise Exception("OCR로 텍스트를 추출할 수 없습니다.")
            
            final_text = '\n\n'.join(extracted_texts)
            logger.info(f"OCR extraction completed: {len(final_text)} total characters")
            return final_text
            
        except ImportError as e:
            logger.error(f"OCR dependencies not installed: {str(e)}")
            raise Exception("OCR 기능을 사용하려면 pytesseract, Pillow, pdf2image 라이브러리가 필요합니다. 설치 가이드: backend/OCR_SETUP.md 참조")
        except Exception as e:
            logger.error(f"OCR extraction failed: {str(e)}")
            raise Exception(f"OCR 처리 실패: {str(e)}")
    
    def _preprocess_image_for_ocr(self, image):
        """OCR을 위한 이미지 전처리"""
        try:
            from PIL import ImageEnhance
            
            # 그레이스케일 변환
            if image.mode != 'L':
                image = image.convert('L')
            
            # 대비 조정
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)
            
            # 선명도 조정
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.2)
            
            return image
            
        except Exception as e:
            logger.warning(f"Image preprocessing failed: {str(e)}")
            return image  # 전처리 실패 시 원본 이미지 반환
    
    def _get_file_type(self, filename: str) -> str:
        """파일 확장자로 파일 타입 결정"""
        if '.' not in filename:
            return 'unknown'
        
        extension = filename.lower().split('.')[-1]
        
        type_mapping = {
            'pdf': 'pdf',
            'txt': 'text',
            'md': 'markdown',
            'py': 'python',
            'js': 'javascript',
            'html': 'html',
            'css': 'css',
            'json': 'json',
            'xml': 'xml',
            'csv': 'csv'
        }
        
        return type_mapping.get(extension, 'text')
    
    async def delete_datasource(self, datasource: RAGDataSource, current_user: User) -> bool:
        """RAG 데이터소스 삭제 (파일 저장소 정리 포함)"""
        try:
            # ChromaDB 컬렉션 삭제
            await self.chroma_service.delete_collection(datasource.chroma_collection_name)
            
            # 파일 저장소 정리
            self.file_storage_service.cleanup_datasource_files(datasource)
            
            # 데이터베이스에서 삭제
            self.db.delete(datasource)
            self.db.commit()
            
            logger.info(f"RAG datasource deleted: {datasource.id} (including stored files)")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete RAG datasource {datasource.id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="데이터소스 삭제에 실패했습니다."
            )
    
    async def query_documents(self, datasource: RAGDataSource, query: str, top_k: int = 5) -> Dict[str, Any]:
        """RAG 데이터소스에서 문서 검색 (기본 버전)"""
        try:
            # ChromaQueryRequest 객체 생성
            query_request = ChromaQueryRequest(
                query_texts=[query],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            
            # ChromaDB에서 검색 수행 (collection_name을 collection_id로 사용)
            search_results = await self.chroma_service.query_documents(
                datasource.chroma_collection_name,
                query_request
            )
            
            # ChromaDB 결과를 RAG 서비스 형식으로 변환
            formatted_results = []
            if search_results and 'documents' in search_results and search_results['documents']:
                documents = search_results['documents'][0]  # 첫 번째 쿼리의 결과
                metadatas = search_results.get('metadatas', [[]])[0]
                distances = search_results.get('distances', [[]])[0]
                ids = search_results.get('ids', [[]])[0]
                
                for i, doc in enumerate(documents):
                    metadata = metadatas[i] if i < len(metadatas) else {}
                    distance = distances[i] if i < len(distances) else 1.0
                    doc_id = ids[i] if i < len(ids) else f"doc_{i}"
                    
                    # 거리를 유사도로 변환 (거리가 작을수록 유사도가 높음)
                    similarity = max(0, 1 - distance)
                    
                    formatted_results.append({
                        "id": doc_id,
                        "content": doc,
                        "similarity": similarity,
                        "distance": distance,
                        "confidence": self._calculate_confidence(similarity),
                        "metadata": {
                            "filename": metadata.get("filename", "알 수 없음"),
                            "chunk_index": metadata.get("chunk_index", 0),
                            "upload_time": metadata.get("upload_time", ""),
                            "file_size": metadata.get("file_size", 0)
                        }
                    })
            
            return {
                "query": query,
                "results": formatted_results,
                "total_results": len(formatted_results),
                "datasource_id": datasource.id,
                "datasource_name": datasource.name,
                "search_stats": {
                    "avg_similarity": round(sum(r["similarity"] for r in formatted_results) / len(formatted_results), 3) if formatted_results else 0,
                    "max_similarity": round(max(r["similarity"] for r in formatted_results), 3) if formatted_results else 0,
                    "min_similarity": round(min(r["similarity"] for r in formatted_results), 3) if formatted_results else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to query documents from datasource {datasource.id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="문서 검색에 실패했습니다."
            )
    
    def _calculate_confidence(self, similarity: float) -> str:
        """유사도를 기반으로 신뢰도 레벨 계산"""
        if similarity >= 0.8:
            return "매우 높음"
        elif similarity >= 0.6:
            return "높음"
        elif similarity >= 0.4:
            return "보통"
        elif similarity >= 0.2:
            return "낮음"
        else:
            return "매우 낮음"
    
    def clear_datasource_documents(self, datasource: RAGDataSource, current_user: User) -> bool:
        """데이터소스의 모든 문서 삭제"""
        try:
            # ChromaDB 컬렉션의 모든 문서 삭제
            success = self.chroma_service.clear_collection(datasource.chroma_collection_name)
            
            if success:
                # 데이터소스 문서 수 초기화
                datasource.document_count = 0
                datasource.last_updated = datetime.now()
                self.db.commit()
                
                logger.info(f"Cleared all documents from datasource {datasource.id}")
                return True
            else:
                return False
                
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to clear documents from datasource {datasource.id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="문서 삭제에 실패했습니다."
            )
    
    def get_documents(self, datasource: RAGDataSource, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """데이터소스의 문서 목록 조회 (페이지네이션 지원)"""
        try:
            # ChromaDB에서 문서 목록 조회
            documents = self.chroma_service.get_documents(
                datasource.chroma_collection_name,
                page=page,
                page_size=page_size
            )
            
            return documents
            
        except Exception as e:
            logger.error(f"Failed to get documents from datasource {datasource.id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="문서 목록 조회에 실패했습니다."
            )
    
    def delete_document(self, datasource: RAGDataSource, document_id: str, current_user: User) -> bool:
        """데이터소스에서 특정 문서 삭제"""
        try:
            # ChromaDB에서 문서 삭제
            success = self.chroma_service.delete_document(
                datasource.chroma_collection_name,
                document_id
            )
            
            if success:
                # 데이터소스 문서 수 업데이트
                stats = self.chroma_service.get_collection_stats(datasource.chroma_collection_name)
                datasource.document_count = stats.get("document_count", 0)
                datasource.last_updated = datetime.now()
                self.db.commit()
                
                logger.info(f"Document {document_id} deleted from datasource {datasource.id} by user {current_user.id}")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete document {document_id} from datasource {datasource.id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="문서 삭제에 실패했습니다."
            )
    
    def query_documents_with_analytics(self, datasource: RAGDataSource, query: str, top_k: int = 5, use_hybrid: bool = True) -> Dict[str, Any]:
        """RAG 데이터소스에서 문서 검색 (분석 기능 포함)"""
        start_time = time.time()
        
        try:
            # 하이브리드 검색 또는 일반 벡터 검색 선택
            if use_hybrid:
                search_results = self.chroma_service.hybrid_search(
                    datasource.chroma_collection_name,
                    query,
                    n_results=top_k
                )
                search_type = "hybrid"
            else:
                search_results = self.chroma_service.query_documents_simple(
                    datasource.chroma_collection_name,
                    query,
                    n_results=top_k
                )
                search_type = "vector"
            
            search_time = time.time() - start_time
            
            # 검색 결과 포맷팅
            formatted_results = []
            for result in search_results:
                metadata = result.get("metadata", {})
                
                formatted_result = {
                    "id": result["id"],
                    "content": result["content"],
                    "similarity": result["similarity"],
                    "distance": result["distance"],
                    "confidence": self._calculate_confidence(result["similarity"]),
                    "metadata": {
                        "filename": metadata.get("filename", "알 수 없음"),
                        "chunk_index": metadata.get("chunk_index", 0),
                        "upload_time": metadata.get("upload_time", ""),
                        "file_size": metadata.get("file_size", 0)
                    }
                }
                
                # 하이브리드 검색인 경우 추가 점수 정보 포함
                if use_hybrid and 'vector_score' in result:
                    formatted_result["vector_score"] = result["vector_score"]
                    formatted_result["keyword_score"] = result["keyword_score"]
                
                formatted_results.append(formatted_result)
            
            # 검색 품질 분석
            quality_metrics = self._analyze_search_quality(formatted_results, query)
            
            return {
                "query": query,
                "results": formatted_results,
                "total_results": len(formatted_results),
                "datasource_id": datasource.id,
                "datasource_name": datasource.name,
                "search_type": search_type,
                "performance_metrics": {
                    "search_time_ms": round(search_time * 1000, 2),
                    "avg_similarity": round(sum(r["similarity"] for r in formatted_results) / len(formatted_results), 3) if formatted_results else 0,
                    "max_similarity": round(max(r["similarity"] for r in formatted_results), 3) if formatted_results else 0,
                    "min_similarity": round(min(r["similarity"] for r in formatted_results), 3) if formatted_results else 0
                },
                "quality_metrics": quality_metrics
            }
            
        except Exception as e:
            logger.error(f"Failed to query documents from datasource {datasource.id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="문서 검색에 실패했습니다."
            )
    
    def _analyze_search_quality(self, results: List[Dict], query: str) -> Dict[str, Any]:
        """검색 품질 분석"""
        if not results:
            return {
                "quality_score": 0,
                "diversity_score": 0,
                "relevance_distribution": [],
                "recommendations": ["검색 결과가 없습니다. 다른 키워드를 시도해보세요."]
            }
        
        # 1. 전체 품질 점수 (평균 유사도 기반)
        avg_similarity = sum(r["similarity"] for r in results) / len(results)
        quality_score = min(avg_similarity * 100, 100)
        
        # 2. 다양성 점수 (결과 간 유사도 차이)
        similarities = [r["similarity"] for r in results]
        diversity_score = (max(similarities) - min(similarities)) * 100 if len(similarities) > 1 else 0
        
        # 3. 관련성 분포
        relevance_distribution = []
        for threshold in [0.8, 0.6, 0.4, 0.2]:
            count = sum(1 for r in results if r["similarity"] >= threshold)
            relevance_distribution.append({
                "threshold": threshold,
                "count": count,
                "percentage": round(count / len(results) * 100, 1)
            })
        
        # 4. 개선 권장사항
        recommendations = []
        if avg_similarity < 0.3:
            recommendations.append("검색 결과의 관련성이 낮습니다. 더 구체적인 키워드를 사용해보세요.")
        if diversity_score < 0.1:
            recommendations.append("검색 결과가 너무 유사합니다. 더 다양한 관점의 문서가 필요할 수 있습니다.")
        if len(results) < 3:
            recommendations.append("검색 결과가 적습니다. 더 많은 문서를 업로드하거나 검색 범위를 넓혀보세요.")
        
        if not recommendations:
            recommendations.append("검색 품질이 양호합니다.")
        
        return {
            "quality_score": round(quality_score, 1),
            "diversity_score": round(diversity_score, 1),
            "relevance_distribution": relevance_distribution,
            "recommendations": recommendations
        }
    
    def get_stored_files(self, datasource: RAGDataSource, current_user: User) -> Dict[str, Any]:
        """데이터소스에 저장된 파일 목록 조회"""
        try:
            # 권한 확인
            if not self.auth_service.can_access_rag_datasource(current_user, datasource):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="데이터소스 접근 권한이 없습니다."
                )
            
            stored_files = self.file_storage_service.get_stored_files(datasource)
            storage_stats = self.file_storage_service.get_storage_stats(
                datasource.owner_type, 
                datasource.owner_id
            )
            
            return {
                "datasource_id": datasource.id,
                "datasource_name": datasource.name,
                "stored_files": stored_files,
                "storage_stats": storage_stats,
                "total_stored_files": len(stored_files)
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get stored files for datasource {datasource.id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="저장된 파일 목록 조회에 실패했습니다."
            )
    
    def delete_stored_file(self, datasource: RAGDataSource, file_path: str, current_user: User) -> bool:
        """저장된 파일 삭제"""
        try:
            # 권한 확인
            if not self.auth_service.can_modify_rag_datasource(current_user, datasource):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="데이터소스 수정 권한이 없습니다."
                )
            
            # 파일 삭제
            success = self.file_storage_service.delete_stored_file(file_path)
            
            if success:
                logger.info(f"Stored file deleted: {file_path} by user {current_user.id}")
            
            return success
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete stored file {file_path}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="저장된 파일 삭제에 실패했습니다."
            )
    
    def get_user_storage_overview(self, current_user: User) -> Dict[str, Any]:
        """사용자의 전체 저장소 사용량 개요"""
        try:
            accessible_datasources = self.auth_service.get_accessible_rag_datasources(current_user)
            
            total_files = 0
            total_size = 0
            datasource_stats = []
            
            for datasource in accessible_datasources:
                try:
                    storage_info = self.get_stored_files(datasource, current_user)
                    
                    ds_file_count = len(storage_info.get("files", []))
                    ds_total_size = sum(file.get("size", 0) for file in storage_info.get("files", []))
                    
                    total_files += ds_file_count
                    total_size += ds_total_size
                    
                    datasource_stats.append({
                        "id": datasource.id,
                        "name": datasource.name,
                        "file_count": ds_file_count,
                        "total_size": ds_total_size,
                        "document_count": datasource.document_count
                    })
                    
                except Exception as e:
                    logger.warning(f"Failed to get storage info for datasource {datasource.id}: {e}")
                    continue
            
            return {
                "total_files": total_files,
                "total_size": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "datasource_count": len(accessible_datasources),
                "datasource_stats": datasource_stats
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage overview: {str(e)}")
            return {
                "total_files": 0,
                "total_size": 0,
                "total_size_mb": 0,
                "datasource_count": 0,
                "datasource_stats": []
            }

    async def search_similar_documents(self, datasource_id: int, query: str, top_k: int = 5, 
                                     similarity_threshold: float = 0.3) -> List[Dict[str, Any]]:
        """유사 문서 검색 (LLM 채팅 서비스용)"""
        try:
            # 데이터소스 조회
            datasource = self.db.query(RAGDataSource).filter(RAGDataSource.id == datasource_id).first()
            if not datasource:
                logger.warning(f"Datasource {datasource_id} not found")
                return []
            
            # ChromaDB에서 검색
            search_results = await self.query_documents(datasource, query, top_k)
            
            if not search_results.get("results"):
                return []
            
            # 결과 포맷팅
            formatted_results = []
            for result in search_results["results"]:
                # 유사도 점수 확인 (임계값 적용)
                similarity = result.get("similarity", 0.0)
                if similarity < similarity_threshold:
                    continue
                
                formatted_results.append({
                    "content": result.get("content", ""),
                    "similarity": similarity,
                    "metadata": result.get("metadata", {}),
                    "document_id": result.get("id", ""),
                    "source": result.get("metadata", {}).get("source", "unknown")
                })
            
            logger.info(f"Found {len(formatted_results)} similar documents for datasource {datasource_id}")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching similar documents for datasource {datasource_id}: {e}")
            return []

    async def search_multiple_datasources(self, datasource_ids: List[int], query: str, 
                                        top_k: int = 3, similarity_threshold: float = 0.3) -> List[Dict[str, Any]]:
        """여러 데이터소스에서 동시 검색"""
        try:
            all_results = []
            
            for datasource_id in datasource_ids:
                try:
                    results = await self.search_similar_documents(
                        datasource_id, query, top_k, similarity_threshold
                    )
                    
                    # 데이터소스 정보 추가
                    for result in results:
                        result["datasource_id"] = datasource_id
                        all_results.append(result)
                        
                except Exception as e:
                    logger.warning(f"Search failed for datasource {datasource_id}: {e}")
                    continue
            
            # 유사도 점수로 정렬
            all_results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
            
            # 최대 결과 수 제한
            max_total_results = top_k * len(datasource_ids)
            return all_results[:max_total_results]
            
        except Exception as e:
            logger.error(f"Error in multi-datasource search: {e}")
            return []

    async def hybrid_search(self, datasource_id: int, query: str, top_k: int = 5,
                          use_semantic: bool = True, use_keyword: bool = True,
                          semantic_weight: float = 0.7) -> List[Dict[str, Any]]:
        """하이브리드 검색 (의미론적 + 키워드 검색)"""
        try:
            if not use_semantic and not use_keyword:
                return []
            
            datasource = self.db.query(RAGDataSource).filter(RAGDataSource.id == datasource_id).first()
            if not datasource:
                return []
            
            semantic_results = []
            keyword_results = []
            
            # 의미론적 검색
            if use_semantic:
                semantic_results = await self.search_similar_documents(
                    datasource_id, query, top_k * 2
                )
            
            # 키워드 검색 (간단한 텍스트 매칭)
            if use_keyword:
                keyword_results = await self._keyword_search(datasource, query, top_k * 2)
            
            # 결과 병합 및 점수 조정
            combined_results = self._merge_search_results(
                semantic_results, keyword_results, semantic_weight, top_k
            )
            
            return combined_results
            
        except Exception as e:
            logger.error(f"Error in hybrid search: {e}")
            return []

    async def _keyword_search(self, datasource: RAGDataSource, query: str, top_k: int) -> List[Dict[str, Any]]:
        """키워드 기반 검색"""
        try:
            # ChromaDB에서 메타데이터 기반 검색
            # 실제 구현에서는 더 정교한 키워드 매칭 로직 필요
            query_terms = query.lower().split()
            
            # 간단한 키워드 매칭을 위한 where 조건 구성
            where_conditions = []
            for term in query_terms[:3]:  # 최대 3개 키워드만 사용
                if len(term) > 2:  # 2글자 이상만
                    where_conditions.append({"$contains": term})
            
            if not where_conditions:
                return []
            
            # ChromaDB 쿼리 실행
            collection = await self.chroma_service.get_collection(datasource.chroma_collection_name)
            if not collection:
                return []
            
            # 키워드 검색 결과
            results = []
            # 실제 키워드 검색 로직은 ChromaDB의 기능에 따라 구현
            # 여기서는 기본 검색 결과를 반환
            
            return results
            
        except Exception as e:
            logger.error(f"Keyword search error: {e}")
            return []

    def _merge_search_results(self, semantic_results: List[Dict], keyword_results: List[Dict],
                            semantic_weight: float, top_k: int) -> List[Dict[str, Any]]:
        """검색 결과 병합"""
        try:
            # 문서 ID 기반으로 결과 병합
            merged_docs = {}
            
            # 의미론적 검색 결과 처리
            for result in semantic_results:
                doc_id = result.get("document_id", "")
                if doc_id:
                    merged_docs[doc_id] = result.copy()
                    merged_docs[doc_id]["semantic_score"] = result.get("similarity", 0)
                    merged_docs[doc_id]["keyword_score"] = 0
            
            # 키워드 검색 결과 처리
            for result in keyword_results:
                doc_id = result.get("document_id", "")
                if doc_id:
                    if doc_id in merged_docs:
                        merged_docs[doc_id]["keyword_score"] = result.get("similarity", 0)
                    else:
                        merged_docs[doc_id] = result.copy()
                        merged_docs[doc_id]["semantic_score"] = 0
                        merged_docs[doc_id]["keyword_score"] = result.get("similarity", 0)
            
            # 최종 점수 계산
            for doc_id, doc in merged_docs.items():
                semantic_score = doc.get("semantic_score", 0)
                keyword_score = doc.get("keyword_score", 0)
                
                # 가중 평균 계산
                final_score = (semantic_score * semantic_weight + 
                             keyword_score * (1 - semantic_weight))
                
                doc["final_similarity"] = final_score
                doc["similarity"] = final_score  # 호환성을 위해
            
            # 최종 점수로 정렬
            sorted_results = sorted(merged_docs.values(), 
                                  key=lambda x: x.get("final_similarity", 0), 
                                  reverse=True)
            
            return sorted_results[:top_k]
            
        except Exception as e:
            logger.error(f"Error merging search results: {e}")
            return [] 