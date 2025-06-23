"""
RAG Chroma Component for FlowRunner Pro

Chroma 벡터 데이터베이스를 사용한 RAG(Retrieval-Augmented Generation) 컴포넌트
문서 검색 및 컨텍스트 증강 생성을 지원
"""

import logging
from typing import Dict, Any, List, Optional
import asyncio
from fastapi import Depends

# 내부 서비스 import
from app.services.chroma_service import get_chroma_service

try:
    from langchain_community.vectorstores import Chroma
    from langchain_community.embeddings import OpenAIEmbeddings
    from langchain_core.runnables import RunnableLambda
    from langchain_core.runnables.base import Runnable
    from langchain_core.documents import Document
    
    # ChromaService를 우선으로 사용할 것이므로 이 부분은 fallback용
    LANGCHAIN_AVAILABLE = True
except ImportError:
    # langchain 라이브러리가 없는 경우 대체 구현
    logging.warning("langchain_community를 가져올 수 없습니다. 내부 ChromaService를 사용합니다.")
    LANGCHAIN_AVAILABLE = False
    
    class Document:
        """Document 대체 구현"""
        def __init__(self, page_content: str, metadata: Dict[str, Any] = None):
            self.page_content = page_content
            self.metadata = metadata or {}
    
    class Runnable:
        """Runnable 기본 클래스 대체 구현"""
        def invoke(self, input_data: Any) -> Any:
            return input_data
        
        def __or__(self, other):
            """파이프 연산자 지원"""
            return ChainedRunnable(self, other)
    
    class RunnableLambda(Runnable):
        """RunnableLambda 대체 구현"""
        def __init__(self, func):
            self.func = func
        
        def invoke(self, input_data: Any) -> Any:
            return self.func(input_data)
    
    class ChainedRunnable(Runnable):
        """체인된 Runnable 대체 구현"""
        def __init__(self, first, second):
            self.first = first
            self.second = second
        
        def invoke(self, input_data: Any) -> Any:
            intermediate = self.first.invoke(input_data)
            return self.second.invoke(intermediate)

logger = logging.getLogger(__name__)


class RAGChromaComponent:
    """
    RAG Chroma 컴포넌트
    
    Chroma 벡터 데이터베이스를 사용하여 문서 검색 및 컨텍스트 증강 생성을 수행
    """
    
    def get_runnable(self, node_data: Dict[str, Any]) -> Runnable:
        """
        노드 데이터로부터 RAG Chroma Runnable을 생성합니다.
        
        Args:
            node_data: Flow JSON에서 특정 노드에 해당하는 데이터 딕셔너리
                      예상 구조: {
                          "data": {
                              "fieldValues": {
                                  "collection_name": "user_xxx_collection",
                                  "n_results": 5,
                                  "similarity_threshold": 0.7,
                                  "include_metadata": true
                              }
                          }
                      }
        
        Returns:
            RunnableLambda 인스턴스
        """
        try:
            # 노드 데이터에서 RAG 설정 추출
            field_values = node_data.get("data", {}).get("fieldValues", {})
            
            # Chroma 설정
            collection_name = field_values.get("collection_name", "default")
            n_results = int(field_values.get("n_results", 5))
            similarity_threshold = float(field_values.get("similarity_threshold", 0.7))
            include_metadata = field_values.get("include_metadata", True)
            
            # ChromaService 인스턴스 가져오기
            try:
                chroma_service = get_chroma_service()
            except Exception as e:
                logger.error(f"ChromaService 인스턴스를 가져올 수 없습니다: {e}")
                chroma_service = None
            
            def rag_process(input_data: Dict[str, Any]) -> Dict[str, Any]:
                """
                RAG 처리를 수행하는 내부 함수
                
                Args:
                    input_data: 입력 데이터 딕셔너리
                    
                Returns:
                    검색된 문서와 컨텍스트가 포함된 데이터
                """
                try:
                    # 쿼리 추출
                    if isinstance(input_data, str):
                        query = input_data
                    elif isinstance(input_data, dict):
                        query = input_data.get("input", "") or input_data.get("query", "") or input_data.get("question", "") or input_data.get("text", "")
                    else:
                        query = str(input_data)
                    
                    if not query:
                        logger.warning("RAG 처리를 위한 쿼리가 비어있습니다")
                        return {
                            "query": "",
                            "context": "",
                            "documents": [],
                            "_component_type": "RAGChroma",
                            "_error": "쿼리가 비어있습니다"
                        }
                    
                    # ChromaService를 이용한 문서 검색
                    documents_data = []
                    context_parts = []
                    
                    if chroma_service:
                        try:
                            # hybrid_search 메서드를 사용하여 문서 검색
                            search_results = chroma_service.hybrid_search(
                                collection_name=collection_name,
                                query=query,
                                n_results=n_results
                            )
                            
                            # 검색 결과 처리
                            for i, result in enumerate(search_results):
                                # ChromaService의 hybrid_search 결과 구조에 맞춤
                                content = result.get('content', '') or result.get('document', '')
                                metadata = result.get('metadata', {})
                                similarity = result.get('similarity', 0.0)
                                
                                # 메타데이터에서 파일 정보 추출
                                filename = metadata.get('filename', '알 수 없는 파일')
                                chunk_index = metadata.get('chunk_index', 0)
                                total_chunks = metadata.get('total_chunks', 1)
                                uploaded_by = metadata.get('uploaded_by', '알 수 없음')
                                upload_time = metadata.get('upload_time', '알 수 없음')
                                
                                # 출처 정보 생성
                                source_info = f"📄 파일: {filename} | 📝 청크: {chunk_index + 1}/{total_chunks} | 👤 업로드: {uploaded_by} | 📅 시간: {upload_time}"
                                
                                # 컨텍스트에 출처 정보와 함께 추가
                                context_parts.append(f"[문서 {i+1}]\n{source_info}\n내용: {content}")
                                
                                # 문서 정보 구성 (더 자세한 정보 포함)
                                doc_info = {
                                    "content": content,
                                    "index": i + 1,
                                    "similarity": similarity,
                                    "source": {
                                        "filename": filename,
                                        "chunk_index": chunk_index,
                                        "total_chunks": total_chunks,
                                        "uploaded_by": uploaded_by,
                                        "upload_time": upload_time
                                    }
                                }
                                
                                if include_metadata:
                                    doc_info["metadata"] = metadata
                                
                                documents_data.append(doc_info)
                            
                            logger.info(f"ChromaService를 통한 RAG 처리 완료: {len(documents_data)}개 문서 검색됨")
                            
                        except Exception as e:
                            logger.error(f"ChromaService 문서 검색 실패: {e}")
                    else:
                        logger.warning("ChromaService를 사용할 수 없어 빈 응답을 반환합니다")
                    
                    # 최종 컨텍스트 생성
                    context = "\n\n".join(context_parts)
                    
                    # 결과 구성
                    result = {
                        "query": query,
                        "context": context,
                        "documents": documents_data,
                        "document_count": len(documents_data),
                        "_component_type": "RAGChroma",
                        "_collection_name": collection_name
                    }
                    
                    # 원본 입력 데이터도 포함
                    if isinstance(input_data, dict):
                        for key, value in input_data.items():
                            if key not in result:
                                result[key] = value
                    
                    logger.info(f"RAG 처리 완료: {len(documents_data)}개 문서 검색됨")
                    return result
                    
                except Exception as e:
                    logger.error(f"RAG 처리 실패: {e}")
                    return {
                        "query": query if 'query' in locals() else "",
                        "context": "",
                        "documents": [],
                        "_component_type": "RAGChroma",
                        "_error": str(e)
                    }
            
            # RunnableLambda로 RAG 처리 함수를 래핑
            runnable = RunnableLambda(rag_process)
            
            logger.info(f"RAG Chroma 컴포넌트 생성 완료: {collection_name} (n_results={n_results})")
            return runnable
            
        except Exception as e:
            logger.error(f"RAG Chroma 컴포넌트 생성 실패: {e}")
            # 기본 처리 함수를 반환
            return RunnableLambda(lambda x: {
                "query": str(x) if x else "",
                "context": "RAG 서비스를 사용할 수 없습니다.",
                "documents": [],
                "_error": str(e)
            })
    
    def validate_node_data(self, node_data: Dict[str, Any]) -> bool:
        """
        노드 데이터의 유효성을 검사합니다.
        
        Args:
            node_data: 검사할 노드 데이터
            
        Returns:
            유효하면 True, 아니면 False
        """
        try:
            field_values = node_data.get("data", {}).get("fieldValues", {})
            
            # collection_name 확인 (필수는 아니지만 권장)
            collection_name = field_values.get("collection_name", "")
            
            # 기본값으로도 작동 가능하므로 항상 유효
            return True
            
        except Exception:
            return False
    
    def get_collection_info(self, collection_name: str, persist_directory: str = "./chroma_data") -> Dict[str, Any]:
        """
        Chroma 컬렉션 정보를 반환합니다.
        
        Args:
            collection_name: 컬렉션 이름
            persist_directory: Chroma 데이터 디렉토리
            
        Returns:
            컬렉션 정보 딕셔너리
        """
        try:
            # 실제 구현에서는 Chroma 클라이언트를 사용하여 컬렉션 정보 조회
            info = {
                "name": collection_name,
                "persist_directory": persist_directory,
                "document_count": 0,
                "status": "unknown"
            }
            
            # 시뮬레이션된 정보
            if collection_name:
                info["status"] = "available"
                info["document_count"] = 100  # 예시값
            
            return info
            
        except Exception as e:
            logger.error(f"컬렉션 정보 조회 실패: {e}")
            return {
                "name": collection_name,
                "persist_directory": persist_directory,
                "status": "error",
                "error": str(e)
            } 