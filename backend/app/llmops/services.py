"""
LLM Operations 서비스

LLM 추론, RAG, 워크플로우 관련 서비스들을 제공합니다.
"""

import os
import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from ..services.chroma_service import ChromaService
from .models import RAGDataSource, Flow, FlowExecutionLog, Secret

import logging

logger = logging.getLogger(__name__)

# ChromaDB 서비스를 재정의하여 legacy 코드와의 호환성 유지
class ChromaDBService(ChromaService):
    """ChromaService를 상속받아 legacy 인터페이스 유지"""
    pass

class LLMInferenceService:
    """LLM 추론 서비스"""
    
    def __init__(self):
        pass
    
    async def generate_text(self, prompt: str, model_config: Dict[str, Any] = None) -> str:
        """텍스트 생성"""
        try:
            # Mock 구현 - 실제로는 LLM API 호출
            await asyncio.sleep(0.1)  # 시뮬레이션
            return f"Generated response for: {prompt[:50]}..."
        except Exception as e:
            logger.error(f"Text generation failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="텍스트 생성에 실패했습니다."
            )
    
    async def chat_completion(self, messages: List[Dict[str, str]], model_config: Dict[str, Any] = None) -> str:
        """채팅 완성"""
        try:
            # Mock 구현
            last_message = messages[-1]['content'] if messages else "안녕하세요"
            await asyncio.sleep(0.1)
            return f"AI: {last_message}에 대한 답변입니다."
        except Exception as e:
            logger.error(f"Chat completion failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="채팅 완성에 실패했습니다."
            )

class RAGService:
    """RAG (Retrieval-Augmented Generation) 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.chroma_service = ChromaService()
        self.llm_service = LLMInferenceService()
    
    async def query_rag(self, 
                       datasource_id: int, 
                       query: str, 
                       top_k: int = 5,
                       model_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """RAG 쿼리 실행"""
        try:
            # 데이터소스 조회
            datasource = self.db.query(RAGDataSource).filter(
                RAGDataSource.id == datasource_id
            ).first()
            
            if not datasource:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="데이터소스를 찾을 수 없습니다."
                )
            
            # 벡터 검색
            search_results = self.chroma_service.query_documents(
                collection_name=datasource.chroma_collection_name,
                query=query,
                n_results=top_k
            )
            
            # 컨텍스트 구성
            context = "\n\n".join([doc["content"] for doc in search_results])
            
            # LLM 프롬프트 구성
            prompt = f"""다음 컨텍스트를 참고하여 질문에 답하세요:

컨텍스트:
{context}

질문: {query}

답변:"""

            # LLM 답변 생성
            answer = await self.llm_service.generate_text(prompt, model_config)
            
            return {
                "answer": answer,
                "context_documents": search_results,
                "query": query,
                "datasource_id": datasource_id
            }
            
        except Exception as e:
            logger.error(f"RAG query failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="RAG 쿼리에 실패했습니다."
            )

class WorkflowService:
    """워크플로우 실행 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.chroma_service = ChromaService()
        self.llm_service = LLMInferenceService()
        self.rag_service = RAGService(db)
    
    async def execute_flow(self, flow_id: int, input_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """플로우 실행"""
        try:
            # 플로우 조회
            flow = self.db.query(Flow).filter(Flow.id == flow_id).first()
            if not flow:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="플로우를 찾을 수 없습니다."
                )
            
            # 실행 로그 생성
            execution_log = FlowExecutionLog(
                flow_id=flow_id,
                input_data=input_data or {},
                status="running",
                started_at=datetime.now()
            )
            self.db.add(execution_log)
            self.db.commit()
            
            try:
                # 플로우 실행 (Mock 구현)
                result = await self._execute_flow_nodes(flow.flow_data, input_data or {})
                
                # 성공 상태 업데이트
                execution_log.status = "completed"
                execution_log.output_data = result
                execution_log.completed_at = datetime.now()
                self.db.commit()
                
                return {
                    "execution_id": execution_log.id,
                    "status": "completed",
                    "result": result
                }
                
            except Exception as e:
                # 실패 상태 업데이트
                execution_log.status = "failed"
                execution_log.error_message = str(e)
                execution_log.completed_at = datetime.now()
                self.db.commit()
                raise
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Flow execution failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="플로우 실행에 실패했습니다."
            )
    
    async def _execute_flow_nodes(self, flow_data: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """플로우 노드 실행 (Mock 구현)"""
        # 간단한 Mock 실행
        await asyncio.sleep(1)  # 시뮬레이션
        
        return {
            "message": "플로우가 성공적으로 실행되었습니다.",
            "processed_nodes": len(flow_data.get("nodes", [])),
            "input_data": input_data,
            "timestamp": datetime.now().isoformat()
        }

class SecretService:
    """시크릿 관리 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_secret(self, name: str, value: str, description: str = None, user_id: str = None) -> Secret:
        """시크릿 생성"""
        try:
            # 중복 확인
            existing = self.db.query(Secret).filter(
                Secret.name == name,
                Secret.user_id == user_id
            ).first()
            
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="동일한 이름의 시크릿이 이미 존재합니다."
                )
            
            # 값 암호화 (실제로는 적절한 암호화 적용)
            encrypted_value = self._encrypt_value(value)
            
            secret = Secret(
                name=name,
                encrypted_value=encrypted_value,
                description=description,
                user_id=user_id,
                created_at=datetime.now()
            )
            
            self.db.add(secret)
            self.db.commit()
            self.db.refresh(secret)
            
            return secret
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Secret creation failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="시크릿 생성에 실패했습니다."
            )
    
    def get_secret_value(self, secret_id: int, user_id: str = None) -> str:
        """시크릿 값 조회 (복호화)"""
        try:
            secret = self.db.query(Secret).filter(
                Secret.id == secret_id,
                Secret.user_id == user_id
            ).first()
            
            if not secret:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="시크릿을 찾을 수 없습니다."
                )
            
            # 값 복호화
            decrypted_value = self._decrypt_value(secret.encrypted_value)
            return decrypted_value
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Secret retrieval failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="시크릿 조회에 실패했습니다."
            )
    
    def _encrypt_value(self, value: str) -> str:
        """값 암호화 (Mock 구현)"""
        # 실제로는 적절한 암호화 라이브러리 사용
        import base64
        return base64.b64encode(value.encode()).decode()
    
    def _decrypt_value(self, encrypted_value: str) -> str:
        """값 복호화 (Mock 구현)"""
        # 실제로는 적절한 복호화 구현
        import base64
        return base64.b64decode(encrypted_value.encode()).decode() 