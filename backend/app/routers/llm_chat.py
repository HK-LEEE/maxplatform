"""
LLM 채팅 서비스 API 라우터
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from ..database import get_db
from ..services.llm_chat_service import LLMChatService
from ..schemas.llm_chat import (
    PersonaCreate, PersonaUpdate, PersonaResponse,
    PromptTemplateCreate, PromptTemplateUpdate, PromptTemplateResponse,
    ChatCreateRequest, ChatUpdate, ChatResponse,
    MessageSendRequest, MessageResponse, MessageFeedbackCreate,
    ChatShareCreate, ChatShareResponse, ChatSearchRequest, ChatSearchResult,
    LLMModelInfo, RAGDataSourceInfo, LLMModelCreate, LLMModelUpdate, LLMModelResponse
)
from ..utils.auth import get_current_user_with_groups
import logging
import httpx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["LLM Chat"])

def get_llm_chat_service(db: Session = Depends(get_db)) -> LLMChatService:
    """LLM 채팅 서비스 의존성 주입"""
    return LLMChatService(db)

# ==================== 페르소나 관리 API ====================

@router.post("/personas", response_model=PersonaResponse)
async def create_persona(
    persona_data: PersonaCreate,
    service: LLMChatService = Depends(get_llm_chat_service),
    user_info = Depends(get_current_user_with_groups)
):
    """페르소나 생성"""
    try:
        return await service.create_persona(user_info, persona_data)
    except Exception as e:
        logger.error(f"페르소나 생성 API 오류: {e}")
        raise HTTPException(status_code=500, detail="페르소나 생성 중 오류가 발생했습니다.")

@router.get("/personas", response_model=List[PersonaResponse])
async def get_personas(
    service: LLMChatService = Depends(get_llm_chat_service),
    user_info = Depends(get_current_user_with_groups)
):
    """페르소나 목록 조회"""
    try:
        return await service.get_personas(user_info)
    except Exception as e:
        logger.error(f"페르소나 목록 조회 API 오류: {e}")
        raise HTTPException(status_code=500, detail="페르소나 목록 조회 중 오류가 발생했습니다.")

@router.put("/personas/{persona_id}", response_model=PersonaResponse)
async def update_persona(
    persona_id: int,
    persona_data: PersonaUpdate,
    service: LLMChatService = Depends(get_llm_chat_service),
    user_info = Depends(get_current_user_with_groups)
):
    """페르소나 수정"""
    try:
        return await service.update_persona(user_info, persona_id, persona_data)
    except Exception as e:
        logger.error(f"페르소나 수정 API 오류: {e}")
        raise HTTPException(status_code=500, detail="페르소나 수정 중 오류가 발생했습니다.")

@router.delete("/personas/{persona_id}")
async def delete_persona(
    persona_id: int,
    service: LLMChatService = Depends(get_llm_chat_service),
    user_info = Depends(get_current_user_with_groups)
):
    """페르소나 삭제"""
    try:
        success = await service.delete_persona(user_info, persona_id)
        return {"success": success, "message": "페르소나가 삭제되었습니다."}
    except Exception as e:
        logger.error(f"페르소나 삭제 API 오류: {e}")
        raise HTTPException(status_code=500, detail="페르소나 삭제 중 오류가 발생했습니다.")

# ==================== 프롬프트 템플릿 관리 API ====================

@router.post("/prompt-templates", response_model=PromptTemplateResponse)
async def create_prompt_template(
    template_data: PromptTemplateCreate,
    service: LLMChatService = Depends(get_llm_chat_service),
    user_info = Depends(get_current_user_with_groups)
):
    """프롬프트 템플릿 생성"""
    try:
        return await service.create_prompt_template(user_info, template_data)
    except Exception as e:
        logger.error(f"프롬프트 템플릿 생성 API 오류: {e}")
        raise HTTPException(status_code=500, detail="프롬프트 템플릿 생성 중 오류가 발생했습니다.")

@router.get("/prompt-templates", response_model=List[PromptTemplateResponse])
async def get_prompt_templates(
    service: LLMChatService = Depends(get_llm_chat_service),
    user_info = Depends(get_current_user_with_groups)
):
    """프롬프트 템플릿 목록 조회"""
    try:
        return await service.get_prompt_templates(user_info)
    except Exception as e:
        logger.error(f"프롬프트 템플릿 목록 조회 API 오류: {e}")
        raise HTTPException(status_code=500, detail="프롬프트 템플릿 목록 조회 중 오류가 발생했습니다.")

# ==================== 채팅 관리 API ====================

@router.post("/chats", response_model=ChatResponse)
async def create_chat(
    chat_data: ChatCreateRequest,
    service: LLMChatService = Depends(get_llm_chat_service),
    user_info = Depends(get_current_user_with_groups)
):
    """채팅 세션 생성"""
    try:
        return await service.create_chat(user_info, chat_data)
    except Exception as e:
        logger.error(f"채팅 생성 API 오류: {e}")
        raise HTTPException(status_code=500, detail="채팅 생성 중 오류가 발생했습니다.")

@router.get("/chats", response_model=List[ChatResponse])
async def get_user_chats(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    service: LLMChatService = Depends(get_llm_chat_service),
    user_info = Depends(get_current_user_with_groups)
):
    """사용자 채팅 목록 조회"""
    try:
        return await service.get_user_chats(user_info, skip, limit)
    except Exception as e:
        logger.error(f"채팅 목록 조회 API 오류: {e}")
        raise HTTPException(status_code=500, detail="채팅 목록 조회 중 오류가 발생했습니다.")

@router.get("/chats/{chat_id}/messages", response_model=List[MessageResponse])
async def get_chat_messages(
    chat_id: str,
    service: LLMChatService = Depends(get_llm_chat_service),
    user_info = Depends(get_current_user_with_groups)
):
    """채팅 메시지 목록 조회"""
    try:
        return await service.get_chat_messages(user_info, chat_id)
    except Exception as e:
        logger.error(f"채팅 메시지 조회 API 오류: {e}")
        raise HTTPException(status_code=500, detail="채팅 메시지 조회 중 오류가 발생했습니다.")

@router.delete("/chats/{chat_id}")
async def delete_chat(
    chat_id: str,
    service: LLMChatService = Depends(get_llm_chat_service),
    user_info = Depends(get_current_user_with_groups)
):
    """채팅 삭제 (백업 후 삭제)"""
    try:
        success = await service.delete_chat(user_info, chat_id)
        return {"success": success, "message": "채팅이 삭제되었습니다."}
    except Exception as e:
        logger.error(f"채팅 삭제 API 오류: {e}")
        raise HTTPException(status_code=500, detail="채팅 삭제 중 오류가 발생했습니다.")

@router.post("/chats/{chat_id}/messages", response_model=MessageResponse)
async def send_message(
    chat_id: str,
    message_data: MessageSendRequest,
    service: LLMChatService = Depends(get_llm_chat_service),
    user_info = Depends(get_current_user_with_groups)
):
    """메시지 전송"""
    try:
        return await service.send_message(user_info, chat_id, message_data)
    except Exception as e:
        logger.error(f"메시지 전송 API 오류: {e}")
        raise HTTPException(status_code=500, detail="메시지 전송 중 오류가 발생했습니다.")

# ==================== 피드백 관리 API ====================

@router.post("/messages/{message_id}/feedback")
async def add_message_feedback(
    message_id: str,
    feedback_data: MessageFeedbackCreate,
    service: LLMChatService = Depends(get_llm_chat_service),
    user_info = Depends(get_current_user_with_groups)
):
    """메시지 피드백 추가"""
    try:
        success = await service.add_message_feedback(user_info, message_id, feedback_data)
        return {"success": success, "message": "피드백이 저장되었습니다."}
    except Exception as e:
        logger.error(f"피드백 추가 API 오류: {e}")
        raise HTTPException(status_code=500, detail="피드백 저장 중 오류가 발생했습니다.")

# ==================== 검색 API ====================

@router.get("/search", response_model=List[ChatSearchResult])
async def search_messages(
    q: str = Query(..., min_length=1, description="검색어"),
    service: LLMChatService = Depends(get_llm_chat_service),
    user_info = Depends(get_current_user_with_groups)
):
    """채팅 메시지 검색"""
    try:
        search_request = ChatSearchRequest(q=q)
        return await service.search_messages(user_info, search_request)
    except Exception as e:
        logger.error(f"메시지 검색 API 오류: {e}")
        raise HTTPException(status_code=500, detail="메시지 검색 중 오류가 발생했습니다.")

# ==================== 공유 API ====================

@router.post("/chats/{chat_id}/share", response_model=ChatShareResponse)
async def create_chat_share(
    chat_id: str,
    share_data: ChatShareCreate,
    service: LLMChatService = Depends(get_llm_chat_service),
    user_info = Depends(get_current_user_with_groups)
):
    """채팅 공유 링크 생성"""
    try:
        return await service.create_chat_share(user_info, chat_id, share_data)
    except Exception as e:
        logger.error(f"채팅 공유 API 오류: {e}")
        raise HTTPException(status_code=500, detail="채팅 공유 링크 생성 중 오류가 발생했습니다.")

@router.get("/share/{share_id}")
async def get_shared_chat(
    share_id: str,
    service: LLMChatService = Depends(get_llm_chat_service)
):
    """공유된 채팅 조회 (인증 불필요)"""
    try:
        return await service.get_shared_chat(share_id)
    except Exception as e:
        logger.error(f"공유 채팅 조회 API 오류: {e}")
        raise HTTPException(status_code=500, detail="공유 채팅 조회 중 오류가 발생했습니다.")

# ==================== 리소스 조회 API ====================

@router.get("/models")
async def get_available_models(
    service: LLMChatService = Depends(get_llm_chat_service),
    user_info = Depends(get_current_user_with_groups)
):
    """사용 가능한 LLM 모델 목록 조회 (MAXLLM_Model + FlowStudio)"""
    try:
        return await service.get_combined_available_models(user_info)
    except Exception as e:
        logger.error(f"모델 목록 조회 API 오류: {e}")
        raise HTTPException(status_code=500, detail="모델 목록 조회 중 오류가 발생했습니다.")

# ==================== LLM 모델 관리 API ====================

@router.post("/admin/models", response_model=LLMModelResponse)
async def create_llm_model(
    model_data: LLMModelCreate,
    service: LLMChatService = Depends(get_llm_chat_service),
    user_info = Depends(get_current_user_with_groups)
):
    """LLM 모델 생성 (관리자용)"""
    try:
        return await service.create_llm_model(user_info, model_data)
    except Exception as e:
        logger.error(f"LLM 모델 생성 API 오류: {e}")
        raise HTTPException(status_code=500, detail="LLM 모델 생성 중 오류가 발생했습니다.")

@router.get("/admin/models", response_model=List[LLMModelResponse])
async def get_llm_models(
    service: LLMChatService = Depends(get_llm_chat_service),
    user_info = Depends(get_current_user_with_groups)
):
    """LLM 모델 목록 조회 (관리자용)"""
    try:
        return await service.get_accessible_llm_models(user_info)
    except Exception as e:
        logger.error(f"LLM 모델 목록 조회 API 오류: {e}")
        raise HTTPException(status_code=500, detail="LLM 모델 목록 조회 중 오류가 발생했습니다.")

@router.put("/admin/models/{model_id}", response_model=LLMModelResponse)
async def update_llm_model(
    model_id: int,
    model_data: LLMModelUpdate,
    service: LLMChatService = Depends(get_llm_chat_service),
    user_info = Depends(get_current_user_with_groups)
):
    """LLM 모델 수정 (관리자용)"""
    try:
        return await service.update_llm_model(user_info, model_id, model_data)
    except Exception as e:
        logger.error(f"LLM 모델 수정 API 오류: {e}")
        raise HTTPException(status_code=500, detail="LLM 모델 수정 중 오류가 발생했습니다.")

@router.delete("/admin/models/{model_id}")
async def delete_llm_model(
    model_id: int,
    service: LLMChatService = Depends(get_llm_chat_service),
    user_info = Depends(get_current_user_with_groups)
):
    """LLM 모델 삭제 (관리자용)"""
    try:
        success = await service.delete_llm_model(user_info, model_id)
        return {"success": success, "message": "LLM 모델이 삭제되었습니다."}
    except Exception as e:
        logger.error(f"LLM 모델 삭제 API 오류: {e}")
        raise HTTPException(status_code=500, detail="LLM 모델 삭제 중 오류가 발생했습니다.")

@router.get("/rag-datasources", response_model=List[RAGDataSourceInfo])
async def get_rag_datasources(
    service: LLMChatService = Depends(get_llm_chat_service),
    user_info = Depends(get_current_user_with_groups)
):
    """사용 가능한 RAG 데이터소스 목록 조회"""
    try:
        datasources_data = await service.get_accessible_rag_datasources(user_info)
        
        datasources = []
        for ds in datasources_data:
            datasources.append(RAGDataSourceInfo(
                id=ds["id"],
                name=ds["name"],
                description=ds.get("description"),
                document_count=ds["document_count"],
                owner_type=ds["owner_type"],
                created_at=ds["created_at"]
            ))
        
        return datasources
    except Exception as e:
        logger.error(f"RAG 데이터소스 목록 조회 API 오류: {e}")
        raise HTTPException(status_code=500, detail="RAG 데이터소스 목록 조회 중 오류가 발생했습니다.")

# ==================== Ollama 관련 API ====================

@router.get("/ollama/models")
async def get_ollama_models(
    host: str = Query("localhost", description="Ollama 서버 호스트"),
    port: int = Query(11434, description="Ollama 서버 포트")
):
    """Ollama 서버에서 사용 가능한 모델 목록 조회"""
    try:
        ollama_url = f"http://{host}:{port}/api/tags"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(ollama_url)
            
            if response.status_code == 200:
                data = response.json()
                models = []
                
                for model in data.get("models", []):
                    models.append({
                        "name": model.get("name", ""),
                        "size": model.get("size", 0),
                        "digest": model.get("digest", ""),
                        "modified_at": model.get("modified_at", ""),
                        "details": model.get("details", {})
                    })
                
                return {
                    "success": True,
                    "models": models,
                    "server": f"{host}:{port}"
                }
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Ollama 서버 응답 오류: {response.text}"
                )
                
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=408,
            detail=f"Ollama 서버 연결 시간 초과: {host}:{port}"
        )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama 서버에 연결할 수 없습니다: {host}:{port}"
        )
    except Exception as e:
        logger.error(f"Ollama 모델 목록 조회 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail="Ollama 모델 목록 조회 중 오류가 발생했습니다."
        )