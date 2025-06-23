"""
LLM 채팅 서비스
"""
import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text
from fastapi import HTTPException, status

from ..models.llm_chat import (
    MAXLLM_Persona, MAXLLM_Prompt_Template, MAXLLM_Chat, 
    MAXLLM_Message, MAXLLM_Message_Feedback, MAXLLM_Shared_Chat,
    MAXLLM_Flow_Publish_Access, MAXLLM_Model, MAXLLM_Chat_Backup, MAXLLM_Message_Backup,
    OwnerType, SenderType, PublishScope, ModelType
)
from ..schemas.llm_chat import (
    PersonaCreate, PersonaUpdate, PersonaResponse,
    PromptTemplateCreate, PromptTemplateUpdate, PromptTemplateResponse,
    ChatCreateRequest, ChatUpdate, ChatResponse,
    MessageSendRequest, MessageResponse, MessageFeedbackCreate,
    ChatShareCreate, ChatShareResponse, ChatSearchRequest, ChatSearchResult,
    LLMModelCreate, LLMModelUpdate, LLMModelResponse
)
from ..llmops.auth import LLMOpsAuthService
from ..services.llm_service import llm_service

logger = logging.getLogger(__name__)

class LLMChatService:
    """LLM 채팅 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.llmops_auth = LLMOpsAuthService(db)
    
    def _get_user_groups(self, user_info: Dict[str, Any]) -> List[str]:
        """사용자가 속한 그룹 ID 목록 반환"""
        groups = user_info.get("groups", [])
        return [str(group.get("id", group)) for group in groups] if isinstance(groups, list) else []
    
    def _check_owner_permission(self, user_info: Dict[str, Any], owner_type: OwnerType, owner_id: str) -> bool:
        """소유권 확인"""
        user_id = str(user_info["user_id"])
        
        if owner_type == OwnerType.USER:
            return owner_id == user_id
        elif owner_type == OwnerType.GROUP:
            user_groups = self._get_user_groups(user_info)
            return owner_id in user_groups
        
        return False
    
    # ==================== 페르소나 관리 ====================
    
    async def create_persona(self, user_info: Dict[str, Any], persona_data: PersonaCreate) -> PersonaResponse:
        """페르소나 생성"""
        try:
            # owner_id 설정
            if persona_data.owner_type == OwnerType.USER:
                owner_id = str(user_info["user_id"])
            else:  # GROUP
                if not persona_data.owner_id:
                    raise HTTPException(status_code=400, detail="그룹 타입 페르소나는 owner_id가 필요합니다.")
                owner_id = persona_data.owner_id
                # 그룹 권한 확인
                user_groups = self._get_user_groups(user_info)
                if owner_id not in user_groups:
                    raise HTTPException(status_code=403, detail="해당 그룹에 대한 권한이 없습니다.")
            
            persona = MAXLLM_Persona(
                persona_name=persona_data.persona_name,
                system_prompt=persona_data.system_prompt,
                owner_type=persona_data.owner_type,
                owner_id=owner_id
            )
            
            self.db.add(persona)
            self.db.commit()
            self.db.refresh(persona)
            
            logger.info(f"페르소나 생성 완료: {persona.id} by user {user_info['user_id']}")
            return PersonaResponse.model_validate(persona)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"페르소나 생성 실패: {e}")
            raise
    
    async def get_personas(self, user_info: Dict[str, Any]) -> List[PersonaResponse]:
        """사용자가 접근 가능한 페르소나 목록 조회"""
        try:
            user_id = str(user_info["user_id"])
            user_groups = self._get_user_groups(user_info)
            
            # 개인 소유 페르소나
            conditions = [
                and_(
                    MAXLLM_Persona.owner_type == OwnerType.USER,
                    MAXLLM_Persona.owner_id == user_id
                )
            ]
            
            # 그룹 소유 페르소나
            if user_groups:
                conditions.append(
                    and_(
                        MAXLLM_Persona.owner_type == OwnerType.GROUP,
                        MAXLLM_Persona.owner_id.in_(user_groups)
                    )
                )
            
            personas = self.db.query(MAXLLM_Persona)\
                .filter(or_(*conditions))\
                .order_by(MAXLLM_Persona.created_at.desc())\
                .all()
            
            return [PersonaResponse.model_validate(persona) for persona in personas]
            
        except Exception as e:
            logger.error(f"페르소나 목록 조회 실패: {e}")
            raise
    
    async def update_persona(self, user_info: Dict[str, Any], persona_id: int, persona_data: PersonaUpdate) -> PersonaResponse:
        """페르소나 수정"""
        try:
            persona = self.db.query(MAXLLM_Persona).filter(MAXLLM_Persona.id == persona_id).first()
            if not persona:
                raise HTTPException(status_code=404, detail="페르소나를 찾을 수 없습니다.")
            
            # 권한 확인
            if not self._check_owner_permission(user_info, persona.owner_type, persona.owner_id):
                raise HTTPException(status_code=403, detail="페르소나 수정 권한이 없습니다.")
            
            # 업데이트
            if persona_data.persona_name is not None:
                persona.persona_name = persona_data.persona_name
            if persona_data.system_prompt is not None:
                persona.system_prompt = persona_data.system_prompt
            
            self.db.commit()
            self.db.refresh(persona)
            
            return PersonaResponse.model_validate(persona)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"페르소나 수정 실패: {e}")
            raise
    
    async def delete_persona(self, user_info: Dict[str, Any], persona_id: int) -> bool:
        """페르소나 삭제"""
        try:
            persona = self.db.query(MAXLLM_Persona).filter(MAXLLM_Persona.id == persona_id).first()
            if not persona:
                raise HTTPException(status_code=404, detail="페르소나를 찾을 수 없습니다.")
            
            # 권한 확인
            if not self._check_owner_permission(user_info, persona.owner_type, persona.owner_id):
                raise HTTPException(status_code=403, detail="페르소나 삭제 권한이 없습니다.")
            
            self.db.delete(persona)
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"페르소나 삭제 실패: {e}")
            raise
    
    # ==================== 프롬프트 템플릿 관리 ====================
    
    async def create_prompt_template(self, user_info: Dict[str, Any], template_data: PromptTemplateCreate) -> PromptTemplateResponse:
        """프롬프트 템플릿 생성"""
        try:
            # owner_id 설정
            if template_data.owner_type == OwnerType.USER:
                owner_id = str(user_info["user_id"])
            else:  # GROUP
                if not template_data.owner_id:
                    raise HTTPException(status_code=400, detail="그룹 타입 템플릿은 owner_id가 필요합니다.")
                owner_id = template_data.owner_id
                # 그룹 권한 확인
                user_groups = self._get_user_groups(user_info)
                if owner_id not in user_groups:
                    raise HTTPException(status_code=403, detail="해당 그룹에 대한 권한이 없습니다.")
            
            template = MAXLLM_Prompt_Template(
                template_title=template_data.template_title,
                template_content=template_data.template_content,
                owner_type=template_data.owner_type,
                owner_id=owner_id
            )
            
            self.db.add(template)
            self.db.commit()
            self.db.refresh(template)
            
            logger.info(f"프롬프트 템플릿 생성 완료: {template.id} by user {user_info['user_id']}")
            return PromptTemplateResponse.model_validate(template)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"프롬프트 템플릿 생성 실패: {e}")
            raise
    
    async def get_prompt_templates(self, user_info: Dict[str, Any]) -> List[PromptTemplateResponse]:
        """사용자가 접근 가능한 프롬프트 템플릿 목록 조회"""
        try:
            user_id = str(user_info["user_id"])
            user_groups = self._get_user_groups(user_info)
            
            # 개인 소유 템플릿
            conditions = [
                and_(
                    MAXLLM_Prompt_Template.owner_type == OwnerType.USER,
                    MAXLLM_Prompt_Template.owner_id == user_id
                )
            ]
            
            # 그룹 소유 템플릿
            if user_groups:
                conditions.append(
                    and_(
                        MAXLLM_Prompt_Template.owner_type == OwnerType.GROUP,
                        MAXLLM_Prompt_Template.owner_id.in_(user_groups)
                    )
                )
            
            templates = self.db.query(MAXLLM_Prompt_Template)\
                .filter(or_(*conditions))\
                .order_by(MAXLLM_Prompt_Template.created_at.desc())\
                .all()
            
            return [PromptTemplateResponse.model_validate(template) for template in templates]
            
        except Exception as e:
            logger.error(f"프롬프트 템플릿 목록 조회 실패: {e}")
            raise
    
    # ==================== 채팅 관리 ====================
    
    async def create_chat(self, user_info: Dict[str, Any], chat_data: ChatCreateRequest) -> ChatResponse:
        """채팅 세션 생성"""
        try:
            # 페르소나 존재 및 권한 확인
            if chat_data.persona_id:
                persona = self.db.query(MAXLLM_Persona).filter(MAXLLM_Persona.id == chat_data.persona_id).first()
                if not persona:
                    raise HTTPException(status_code=404, detail="페르소나를 찾을 수 없습니다.")
                if not self._check_owner_permission(user_info, persona.owner_type, persona.owner_id):
                    raise HTTPException(status_code=403, detail="페르소나 사용 권한이 없습니다.")
            
            chat = MAXLLM_Chat(
                user_id=user_info["user_id"],
                model_id=chat_data.model_id,
                persona_id=chat_data.persona_id,
                title=chat_data.title
            )
            
            self.db.add(chat)
            self.db.commit()
            self.db.refresh(chat)
            
            # 초기 메시지 생성
            if chat_data.initial_message:
                await self._add_user_message(chat.id, chat_data.initial_message)
                # AI 응답 생성 (백그라운드에서 처리할 수도 있음)
                ai_response = await self._generate_ai_response(chat, chat_data.initial_message)
                await self._add_ai_message(chat.id, ai_response["content"], ai_response.get("message_metadata"))
            
            logger.info(f"채팅 생성 완료: {chat.id} by user {user_info['user_id']}")
            return ChatResponse.model_validate(chat)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"채팅 생성 실패: {e}")
            raise
    
    async def get_user_chats(self, user_info: Dict[str, Any], skip: int = 0, limit: int = 20) -> List[ChatResponse]:
        """사용자 채팅 목록 조회"""
        try:
            chats = self.db.query(MAXLLM_Chat)\
                .filter(MAXLLM_Chat.user_id == user_info["user_id"])\
                .order_by(MAXLLM_Chat.updated_at.desc())\
                .offset(skip).limit(limit)\
                .all()
            
            return [ChatResponse.model_validate(chat) for chat in chats]
            
        except Exception as e:
            logger.error(f"채팅 목록 조회 실패: {e}")
            raise
    
    async def get_chat_messages(self, user_info: Dict[str, Any], chat_id: str) -> List[MessageResponse]:
        """채팅 메시지 목록 조회"""
        try:
            # 채팅 권한 확인
            chat = self.db.query(MAXLLM_Chat).filter(
                MAXLLM_Chat.id == chat_id,
                MAXLLM_Chat.user_id == user_info["user_id"]
            ).first()
            
            if not chat:
                raise HTTPException(status_code=404, detail="채팅을 찾을 수 없습니다.")
            
            messages = self.db.query(MAXLLM_Message)\
                .filter(MAXLLM_Message.chat_id == chat_id)\
                .order_by(MAXLLM_Message.created_at.asc())\
                .all()
            
            return [MessageResponse.model_validate(message) for message in messages]
            
        except Exception as e:
            logger.error(f"채팅 메시지 조회 실패: {e}")
            raise

    async def delete_chat(self, user_info: Dict[str, Any], chat_id: str) -> bool:
        """채팅 삭제 (백업 후 삭제)"""
        try:
            # 채팅 소유권 확인
            chat = self.db.query(MAXLLM_Chat).filter(
                MAXLLM_Chat.id == chat_id,
                MAXLLM_Chat.user_id == user_info["user_id"]
            ).first()
            
            if not chat:
                raise HTTPException(status_code=404, detail="채팅을 찾을 수 없습니다.")
            
            # 채팅의 모든 메시지 조회
            messages = self.db.query(MAXLLM_Message)\
                .filter(MAXLLM_Message.chat_id == chat_id)\
                .all()
            
            # 1. 메시지들을 백업 테이블로 이관
            for message in messages:
                message_backup = MAXLLM_Message_Backup(
                    id=message.id,
                    chat_id=message.chat_id,
                    sender_type=message.sender_type,
                    content=message.content,
                    message_metadata=message.message_metadata,
                    prompt_tokens=message.prompt_tokens,
                    completion_tokens=message.completion_tokens,
                    total_cost=message.total_cost,
                    created_at=message.created_at,
                    deleted_by=user_info["user_id"]
                )
                self.db.add(message_backup)
            
            # 2. 채팅을 백업 테이블로 이관
            chat_backup = MAXLLM_Chat_Backup(
                id=chat.id,
                user_id=chat.user_id,
                model_id=chat.model_id,
                persona_id=chat.persona_id,
                title=chat.title,
                created_at=chat.created_at,
                updated_at=chat.updated_at,
                deleted_by=user_info["user_id"]
            )
            self.db.add(chat_backup)
            
            # 3. 원본 메시지들 삭제
            for message in messages:
                self.db.delete(message)
            
            # 4. 원본 채팅 삭제
            self.db.delete(chat)
            
            self.db.commit()
            
            logger.info(f"채팅 삭제 완료: {chat_id} by user {user_info['user_id']}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"채팅 삭제 실패: {e}")
            raise
    
    async def send_message(self, user_info: Dict[str, Any], chat_id: str, message_data: MessageSendRequest) -> MessageResponse:
        """메시지 전송 및 AI 응답 생성"""
        try:
            # 채팅 권한 확인
            chat = self.db.query(MAXLLM_Chat).filter(
                MAXLLM_Chat.id == chat_id,
                MAXLLM_Chat.user_id == user_info["user_id"]
            ).first()
            
            if not chat:
                raise HTTPException(status_code=404, detail="채팅을 찾을 수 없습니다.")
            
            # 사용자 메시지 저장
            user_message = await self._add_user_message(chat_id, message_data.content)
            
            # AI 응답 생성
            ai_response = await self._generate_ai_response(chat, message_data.content, message_data.rag_datasource_ids)
            ai_message = await self._add_ai_message(
                chat_id, 
                ai_response["content"], 
                ai_response.get("message_metadata"),
                ai_response.get("prompt_tokens"),
                ai_response.get("completion_tokens"),
                ai_response.get("total_cost")
            )
            
            # 첫 번째 메시지인 경우 채팅 제목 자동 생성
            message_count = self.db.query(MAXLLM_Message).filter(MAXLLM_Message.chat_id == chat_id).count()
            if message_count <= 2:  # 사용자 메시지 + AI 응답 = 2개
                await self._update_chat_title(chat, message_data.content)
            
            # 채팅 업데이트 시간 갱신
            chat.updated_at = datetime.utcnow()
            self.db.commit()
            
            return MessageResponse.model_validate(ai_message)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"메시지 전송 실패: {e}")
            raise
    
    async def _add_user_message(self, chat_id: str, content: str) -> MAXLLM_Message:
        """사용자 메시지 추가"""
        message = MAXLLM_Message(
            chat_id=chat_id,
            sender_type=SenderType.USER,
            content=content
        )
        self.db.add(message)
        self.db.flush()
        return message
    
    async def _add_ai_message(self, chat_id: str, content: str, message_metadata: Optional[Dict] = None,
                             prompt_tokens: Optional[int] = None, completion_tokens: Optional[int] = None,
                             total_cost: Optional[float] = None) -> MAXLLM_Message:
        """AI 메시지 추가"""
        message = MAXLLM_Message(
            chat_id=chat_id,
            sender_type=SenderType.AI,
            content=content,
            message_metadata=message_metadata,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_cost=total_cost
        )
        self.db.add(message)
        self.db.flush()
        return message
    
    async def _generate_ai_response(self, chat: MAXLLM_Chat, user_message: str, 
                                   rag_datasource_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """AI 응답 생성"""
        try:
            # 채팅 히스토리 가져오기
            messages = self.db.query(MAXLLM_Message)\
                .filter(MAXLLM_Message.chat_id == chat.id)\
                .order_by(MAXLLM_Message.created_at.asc())\
                .all()
            
            # 메시지 포맷 변환
            chat_messages = []
            
            # 페르소나 시스템 프롬프트 추가
            if chat.persona:
                chat_messages.append({
                    "role": "system",
                    "content": chat.persona.system_prompt
                })
            
            # 기존 메시지 추가
            for msg in messages:
                role = "user" if msg.sender_type == SenderType.USER else "assistant"
                chat_messages.append({
                    "role": role,
                    "content": msg.content
                })
            
            # 현재 사용자 메시지 추가
            chat_messages.append({
                "role": "user", 
                "content": user_message
            })
            
            # RAG 컨텍스트 추가
            rag_context = ""
            if rag_datasource_ids:
                rag_context = await self._get_rag_context(rag_datasource_ids, user_message)
                if rag_context:
                    # RAG 컨텍스트를 시스템 메시지로 추가
                    chat_messages.insert(-1, {
                        "role": "system",
                        "content": f"다음 정보를 참고하여 답변해주세요:\n\n{rag_context}"
                    })
            
            # LLM 서비스 호출
            response = await llm_service.generate_response(
                messages=chat_messages,
                model=chat.model_id,
                stream=False
            )
            
            return {
                "content": response.get("content", ""),
                "message_metadata": {
                    "model": chat.model_id,
                    "rag_used": bool(rag_context),
                    "rag_datasource_ids": rag_datasource_ids or []
                },
                "prompt_tokens": response.get("usage", {}).get("prompt_tokens"),
                "completion_tokens": response.get("usage", {}).get("completion_tokens"),
                "total_cost": self._calculate_cost(response.get("usage", {}), chat.model_id)
            }
            
        except Exception as e:
            logger.error(f"AI 응답 생성 실패: {e}")
            return {
                "content": "죄송합니다. 응답 생성 중 오류가 발생했습니다.",
                "message_metadata": {"error": str(e)}
            }
    
    async def _get_rag_context(self, datasource_ids: List[int], query: str) -> str:
        """RAG 데이터소스에서 관련 컨텍스트 검색 및 정제"""
        try:
            if not datasource_ids:
                return ""
            
            # RAG 서비스 호출 (기존 구현 활용)
            from ..llmops.rag_service import RAGDataSourceService
            from ..llmops.models import RAGDataSource
            
            rag_service = RAGDataSourceService(self.db)
            
            context_parts = []
            datasource_names = []
            
            for ds_id in datasource_ids:
                try:
                    results = await rag_service.search_similar_documents(ds_id, query, top_k=3)
                    if results:
                        context_parts.extend([doc["content"] for doc in results])
                        
                        # 데이터소스 이름도 가져오기
                        datasource = self.db.query(RAGDataSource).filter(RAGDataSource.id == ds_id).first()
                        if datasource:
                            datasource_names.append(datasource.name)
                            
                except Exception as e:
                    logger.warning(f"RAG 검색 실패 (datasource {ds_id}): {e}")
            
            # 컨텍스트가 있으면 정제된 형태로 반환
            if context_parts:
                return await self._refine_rag_context(context_parts, query, datasource_names)
            else:
                return ""
            
        except Exception as e:
            logger.error(f"RAG 컨텍스트 조회 실패: {e}")
            return ""

    async def _refine_rag_context(self, contexts: List[str], query: str, datasource_names: List[str]) -> str:
        """RAG 검색 결과를 정제하여 더 나은 컨텍스트 생성"""
        try:
            # 컨텍스트가 너무 길면 요약
            combined_context = "\n\n".join([f"[문서 {i+1}] {ctx}" for i, ctx in enumerate(contexts)])
            
            # 문서 소스 정보 추가
            source_info = f"📚 검색된 데이터소스: {', '.join(set(datasource_names))}"
            
            # 컨텍스트 길이 제한 (토큰 절약)
            max_context_length = 3000
            if len(combined_context) > max_context_length:
                # 관련성 높은 부분만 선택
                truncated_context = combined_context[:max_context_length] + "..."
                refined_context = f"""
{source_info}

📋 관련 문서 내용 (요약):
{truncated_context}

💡 위 문서들을 참고하여 질문에 답변해주세요. 문서에 없는 내용은 추측하지 말고, 문서 기반으로만 답변해주세요. 답변 시 어떤 문서에서 가져온 정보인지 명시해주세요.
"""
            else:
                refined_context = f"""
{source_info}

📋 관련 문서 내용:
{combined_context}

💡 위 문서들을 참고하여 질문에 답변해주세요. 문서에 없는 내용은 추측하지 말고, 문서 기반으로만 답변해주세요. 답변 시 어떤 문서에서 가져온 정보인지 명시해주세요.
"""
            
            return refined_context
            
        except Exception as e:
            logger.error(f"RAG 컨텍스트 정제 실패: {e}")
            # 실패 시 기본 형태로 반환
            return "\n\n---\n\n".join(contexts)
    
    def _calculate_cost(self, usage: Dict[str, Any], model_id: str) -> Optional[float]:
        """토큰 사용량 기반 비용 계산"""
        try:
            # 모델별 토큰 단가 (예시)
            token_prices = {
                "gpt-4": {"prompt": 0.00003, "completion": 0.00006},
                "gpt-3.5-turbo": {"prompt": 0.0000015, "completion": 0.000002},
                # 추가 모델들...
            }
            
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            
            if model_id in token_prices:
                prices = token_prices[model_id]
                total_cost = (prompt_tokens * prices["prompt"]) + (completion_tokens * prices["completion"])
                return round(total_cost, 8)
            
            return None
            
        except Exception as e:
            logger.error(f"비용 계산 실패: {e}")
            return None
    
    # ==================== 피드백 관리 ====================
    
    async def add_message_feedback(self, user_info: Dict[str, Any], message_id: str, 
                                  feedback_data: MessageFeedbackCreate) -> bool:
        """메시지 피드백 추가/업데이트"""
        try:
            # 기존 피드백 확인
            existing_feedback = self.db.query(MAXLLM_Message_Feedback).filter(
                MAXLLM_Message_Feedback.message_id == message_id,
                MAXLLM_Message_Feedback.user_id == user_info["user_id"]
            ).first()
            
            if existing_feedback:
                # 기존 피드백 업데이트
                existing_feedback.rating = feedback_data.rating
                existing_feedback.comment = feedback_data.comment
            else:
                # 새 피드백 생성
                feedback = MAXLLM_Message_Feedback(
                    message_id=message_id,
                    user_id=user_info["user_id"],
                    rating=feedback_data.rating,
                    comment=feedback_data.comment
                )
                self.db.add(feedback)
            
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"피드백 추가 실패: {e}")
            raise
    
    # ==================== 2단계: 검색 및 공유 기능 ====================
    
    async def search_messages(self, user_info: Dict[str, Any], search_request: ChatSearchRequest) -> List[ChatSearchResult]:
        """채팅 메시지 전체 검색 (PostgreSQL Full-Text Search 사용)"""
        try:
            # 사용자의 채팅 ID 목록 조회
            user_chat_ids = self.db.query(MAXLLM_Chat.id)\
                .filter(MAXLLM_Chat.user_id == user_info["user_id"])\
                .subquery()
            
            # PostgreSQL Full-Text Search 쿼리
            search_query = text("""
                SELECT 
                    m.id as message_id,
                    m.chat_id,
                    c.title as chat_title,
                    LEFT(m.content, 200) as content_snippet,
                    m.created_at,
                    ts_rank(to_tsvector('korean', m.content), plainto_tsquery('korean', :query)) as rank
                FROM maxllm_messages m
                JOIN maxllm_chats c ON m.chat_id = c.id
                WHERE 
                    m.chat_id IN (SELECT id FROM :user_chats)
                    AND to_tsvector('korean', m.content) @@ plainto_tsquery('korean', :query)
                ORDER BY rank DESC, m.created_at DESC
                LIMIT 20
            """)
            
            result = self.db.execute(search_query, {
                "query": search_request.q,
                "user_chats": user_chat_ids
            })
            
            search_results = []
            for row in result:
                search_results.append(ChatSearchResult(
                    message_id=str(row.message_id),
                    chat_id=str(row.chat_id),
                    chat_title=row.chat_title,
                    content_snippet=row.content_snippet,
                    created_at=row.created_at
                ))
            
            logger.info(f"메시지 검색 완료: {len(search_results)}개 결과")
            return search_results
            
        except Exception as e:
            logger.error(f"메시지 검색 실패: {e}")
            # PostgreSQL이 아닌 경우 LIKE 검색으로 fallback
            return await self._search_messages_fallback(user_info, search_request)
    
    async def _search_messages_fallback(self, user_info: Dict[str, Any], search_request: ChatSearchRequest) -> List[ChatSearchResult]:
        """검색 fallback (LIKE 사용)"""
        try:
            messages = self.db.query(MAXLLM_Message, MAXLLM_Chat.title)\
                .join(MAXLLM_Chat)\
                .filter(
                    MAXLLM_Chat.user_id == user_info["user_id"],
                    MAXLLM_Message.content.ilike(f"%{search_request.q}%")
                )\
                .order_by(MAXLLM_Message.created_at.desc())\
                .limit(20)\
                .all()
            
            search_results = []
            for message, chat_title in messages:
                content_snippet = message.content[:200] + "..." if len(message.content) > 200 else message.content
                search_results.append(ChatSearchResult(
                    message_id=message.id,
                    chat_id=message.chat_id,
                    chat_title=chat_title,
                    content_snippet=content_snippet,
                    created_at=message.created_at
                ))
            
            return search_results
            
        except Exception as e:
            logger.error(f"Fallback 검색 실패: {e}")
            return []
    
    async def create_chat_share(self, user_info: Dict[str, Any], chat_id: str, 
                               share_data: ChatShareCreate) -> ChatShareResponse:
        """채팅 공유 링크 생성"""
        try:
            # 채팅 권한 확인
            chat = self.db.query(MAXLLM_Chat).filter(
                MAXLLM_Chat.id == chat_id,
                MAXLLM_Chat.user_id == user_info["user_id"]
            ).first()
            
            if not chat:
                raise HTTPException(status_code=404, detail="채팅을 찾을 수 없습니다.")
            
            # 기존 공유 링크 확인
            existing_share = self.db.query(MAXLLM_Shared_Chat).filter(
                MAXLLM_Shared_Chat.chat_id == chat_id
            ).first()
            
            if existing_share:
                # 기존 공유 링크 업데이트
                existing_share.expires_at = share_data.expires_at
                shared_chat = existing_share
            else:
                # 새 공유 링크 생성
                shared_chat = MAXLLM_Shared_Chat(
                    chat_id=chat_id,
                    created_by_user_id=user_info["user_id"],
                    expires_at=share_data.expires_at
                )
                self.db.add(shared_chat)
            
            self.db.commit()
            self.db.refresh(shared_chat)
            
            # 공유 URL 생성
            share_url = f"/chat/share/{shared_chat.share_id}"
            
            response = ChatShareResponse.model_validate(shared_chat)
            response.share_url = share_url
            
            logger.info(f"채팅 공유 링크 생성: {shared_chat.share_id}")
            return response
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"채팅 공유 링크 생성 실패: {e}")
            raise
    
    async def get_shared_chat(self, share_id: str) -> Dict[str, Any]:
        """공유된 채팅 조회 (인증 불필요)"""
        try:
            shared_chat = self.db.query(MAXLLM_Shared_Chat).filter(
                MAXLLM_Shared_Chat.share_id == share_id
            ).first()
            
            if not shared_chat:
                raise HTTPException(status_code=404, detail="공유 링크를 찾을 수 없습니다.")
            
            # 만료 확인
            if shared_chat.expires_at and shared_chat.expires_at < datetime.utcnow():
                raise HTTPException(status_code=404, detail="공유 링크가 만료되었습니다.")
            
            # 채팅 및 메시지 조회
            chat = self.db.query(MAXLLM_Chat).filter(MAXLLM_Chat.id == shared_chat.chat_id).first()
            if not chat:
                raise HTTPException(status_code=404, detail="채팅을 찾을 수 없습니다.")
            
            messages = self.db.query(MAXLLM_Message)\
                .filter(MAXLLM_Message.chat_id == shared_chat.chat_id)\
                .order_by(MAXLLM_Message.created_at.asc())\
                .all()
            
            return {
                "chat": ChatResponse.model_validate(chat),
                "messages": [MessageResponse.model_validate(msg) for msg in messages],
                "is_shared": True,
                "share_info": {
                    "created_at": shared_chat.created_at,
                    "expires_at": shared_chat.expires_at
                }
            }
            
        except Exception as e:
            logger.error(f"공유 채팅 조회 실패: {e}")
            raise
    
    # ==================== FlowStudio 확장 기능 ====================
    
    async def get_published_flows(self, user_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """사용자가 접근 가능한 Published FlowStudio 플로우 목록"""
        try:
            from ..models.flow_studio import FlowStudioFlow, PublishStatus
            
            user_id = str(user_info["user_id"])
            user_groups = self._get_user_groups(user_info)
            
            # 기본 쿼리: PUBLISHED 상태인 플로우들
            base_query = self.db.query(FlowStudioFlow).filter(
                FlowStudioFlow.publish_status == PublishStatus.PUBLISHED,
                FlowStudioFlow.is_latest_published == True
            )
            
            # 접근 권한 확인
            access_conditions = []
            
            # 1. EVERYONE 범위 플로우
            everyone_flows = self.db.query(MAXLLM_Flow_Publish_Access.flow_id).filter(
                MAXLLM_Flow_Publish_Access.publish_scope == PublishScope.EVERYONE
            ).subquery()
            
            access_conditions.append(FlowStudioFlow.id.in_(
                self.db.query(MAXLLM_Flow_Publish_Access.flow_id).filter(
                    MAXLLM_Flow_Publish_Access.publish_scope == PublishScope.EVERYONE
                ).scalar_subquery()
            ))
            
            # 2. GROUP 범위 플로우 (사용자가 속한 그룹)
            if user_groups:
                group_flows = self.db.query(MAXLLM_Flow_Publish_Access.flow_id).filter(
                    MAXLLM_Flow_Publish_Access.publish_scope == PublishScope.GROUP,
                    MAXLLM_Flow_Publish_Access.target_group_id.in_([int(g) for g in user_groups])
                ).subquery()
                
                access_conditions.append(FlowStudioFlow.id.in_(
                    self.db.query(MAXLLM_Flow_Publish_Access.flow_id).filter(
                        MAXLLM_Flow_Publish_Access.publish_scope == PublishScope.GROUP,
                        MAXLLM_Flow_Publish_Access.target_group_id.in_([int(g) for g in user_groups])
                    ).scalar_subquery()
                ))
            
            # 3. USER 범위 플로우 (특정 사용자 대상)
            user_flows = self.db.query(MAXLLM_Flow_Publish_Access.flow_id).filter(
                MAXLLM_Flow_Publish_Access.publish_scope == PublishScope.USER,
                MAXLLM_Flow_Publish_Access.target_user_id == user_id
            ).subquery()
            
            access_conditions.append(FlowStudioFlow.id.in_(
                self.db.query(MAXLLM_Flow_Publish_Access.flow_id).filter(
                    MAXLLM_Flow_Publish_Access.publish_scope == PublishScope.USER,
                    MAXLLM_Flow_Publish_Access.target_user_id == user_id
                ).scalar_subquery()
            ))
            
            # 4. 사용자 본인이 소유한 플로우
            access_conditions.append(FlowStudioFlow.user_id == user_id)
            
            # 최종 쿼리 실행
            flows = base_query.filter(or_(*access_conditions)).all()
            
            result = []
            for flow in flows:
                result.append({
                    "id": flow.id,
                    "name": flow.name,
                    "description": flow.description,
                    "version": flow.version,
                    "created_at": flow.created_at,
                    "updated_at": flow.updated_at
                })
            
            logger.info(f"Published 플로우 {len(result)}개 조회 완료")
            return result
            
        except Exception as e:
            logger.error(f"Published 플로우 조회 실패: {e}")
            return []
    
    async def get_accessible_rag_datasources(self, user_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """사용자가 접근 가능한 RAG 데이터소스 목록"""
        try:
            # 기존 LLMOps Auth 서비스 활용
            from ..models.user import User
            current_user = self.db.query(User).filter(User.id == user_info["user_id"]).first()
            if not current_user:
                return []
            
            accessible_datasources = self.llmops_auth.get_accessible_rag_datasources(current_user)
            
            result = []
            for ds in accessible_datasources:
                result.append({
                    "id": ds.id,
                    "name": ds.name,
                    "description": ds.description,
                    "document_count": ds.document_count,
                    "owner_type": ds.owner_type.value,
                    "created_at": ds.created_at
                })
            
            return result
            
        except Exception as e:
            logger.error(f"RAG 데이터소스 조회 실패: {e}")
            return []
    
    # ==================== LLM 모델 관리 ====================
    
    async def create_llm_model(self, user_info: Dict[str, Any], model_data: LLMModelCreate) -> LLMModelResponse:
        """LLM 모델 생성"""
        try:
            # owner_id 설정
            if model_data.owner_type == OwnerType.USER:
                owner_id = str(user_info["user_id"])
            else:  # GROUP
                if not model_data.owner_id:
                    raise HTTPException(status_code=400, detail="그룹 타입 모델은 owner_id가 필요합니다.")
                owner_id = model_data.owner_id
                # 그룹 권한 확인
                user_groups = self._get_user_groups(user_info)
                if owner_id not in user_groups:
                    raise HTTPException(status_code=403, detail="해당 그룹에 대한 권한이 없습니다.")
            
            model = MAXLLM_Model(
                model_name=model_data.model_name,
                model_type=model_data.model_type,
                model_id=model_data.model_id,
                description=model_data.description,
                config=model_data.config,
                owner_type=model_data.owner_type,
                owner_id=owner_id
            )
            
            self.db.add(model)
            self.db.commit()
            self.db.refresh(model)
            
            logger.info(f"LLM 모델 생성 완료: {model.id} by user {user_info['user_id']}")
            return LLMModelResponse.model_validate(model)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"LLM 모델 생성 실패: {e}")
            raise
    
    async def get_accessible_llm_models(self, user_info: Dict[str, Any]) -> List[LLMModelResponse]:
        """사용자가 접근 가능한 LLM 모델 목록 조회"""
        try:
            user_id = str(user_info["user_id"])
            user_groups = self._get_user_groups(user_info)
            
            # 개인 소유 모델
            conditions = [
                and_(
                    MAXLLM_Model.owner_type == OwnerType.USER,
                    MAXLLM_Model.owner_id == user_id,
                    MAXLLM_Model.is_active == True
                )
            ]
            
            # 그룹 소유 모델
            if user_groups:
                conditions.append(
                    and_(
                        MAXLLM_Model.owner_type == OwnerType.GROUP,
                        MAXLLM_Model.owner_id.in_(user_groups),
                        MAXLLM_Model.is_active == True
                    )
                )
            
            models = self.db.query(MAXLLM_Model)\
                .filter(or_(*conditions))\
                .order_by(MAXLLM_Model.created_at.desc())\
                .all()
            
            return [LLMModelResponse.model_validate(model) for model in models]
            
        except Exception as e:
            logger.error(f"LLM 모델 목록 조회 실패: {e}")
            raise
    
    async def update_llm_model(self, user_info: Dict[str, Any], model_id: int, model_data: LLMModelUpdate) -> LLMModelResponse:
        """LLM 모델 수정"""
        try:
            model = self.db.query(MAXLLM_Model).filter(MAXLLM_Model.id == model_id).first()
            if not model:
                raise HTTPException(status_code=404, detail="모델을 찾을 수 없습니다.")
            
            # 권한 확인
            if not self._check_owner_permission(user_info, model.owner_type, model.owner_id):
                raise HTTPException(status_code=403, detail="모델 수정 권한이 없습니다.")
            
            # 업데이트
            if model_data.model_name is not None:
                model.model_name = model_data.model_name
            if model_data.model_type is not None:
                model.model_type = model_data.model_type
            if model_data.model_id is not None:
                model.model_id = model_data.model_id
            if model_data.description is not None:
                model.description = model_data.description
            if model_data.config is not None:
                model.config = model_data.config
            if model_data.is_active is not None:
                model.is_active = model_data.is_active
            
            self.db.commit()
            self.db.refresh(model)
            
            return LLMModelResponse.model_validate(model)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"LLM 모델 수정 실패: {e}")
            raise
    
    async def delete_llm_model(self, user_info: Dict[str, Any], model_id: int) -> bool:
        """LLM 모델 삭제"""
        try:
            model = self.db.query(MAXLLM_Model).filter(MAXLLM_Model.id == model_id).first()
            if not model:
                raise HTTPException(status_code=404, detail="모델을 찾을 수 없습니다.")
            
            # 권한 확인
            if not self._check_owner_permission(user_info, model.owner_type, model.owner_id):
                raise HTTPException(status_code=403, detail="모델 삭제 권한이 없습니다.")
            
            self.db.delete(model)
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"LLM 모델 삭제 실패: {e}")
            raise
    
    async def get_combined_available_models(self, user_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """사용자가 사용 가능한 모든 모델 목록 (MAXLLM_Model + FlowStudio Published)"""
        try:
            result = []
            
            # 1. MAXLLM_Model 테이블에서 가져오기
            llm_models = await self.get_accessible_llm_models(user_info)
            for model in llm_models:
                result.append({
                    "id": f"model_{model.id}",
                    "name": model.model_name,
                    "type": model.model_type.value,
                    "provider": self._get_provider_name(model.model_type),
                    "description": model.description,
                    "source": "maxllm_model",
                    "config": model.config
                })
            
            # 2. FlowStudio Published API에서 가져오기
            published_flows = await self.get_published_flows(user_info)
            for flow in published_flows:
                result.append({
                    "id": f"flow_{flow['id']}",
                    "name": flow["name"],
                    "type": "FLOWSTUDIO",
                    "provider": "FlowStudio",
                    "description": flow.get("description", ""),
                    "source": "flowstudio",
                    "config": {"flow_id": flow["id"]}
                })
            
            return result
            
        except Exception as e:
            logger.error(f"통합 모델 목록 조회 실패: {e}")
            raise
    
    def _get_provider_name(self, model_type: ModelType) -> str:
        """모델 타입에 따른 제공자 이름 반환"""
        provider_map = {
            ModelType.AZURE_OPENAI: "Azure OpenAI",
            ModelType.AZURE_CLAUDE: "Azure Claude",
            ModelType.AZURE_DEEPSEEK: "Azure DeepSeek",
            ModelType.OLLAMA: "Ollama",
            ModelType.FLOWSTUDIO: "FlowStudio"
        }
        return provider_map.get(model_type, "Unknown")

    async def _update_chat_title(self, chat: MAXLLM_Chat, first_message: str) -> None:
        """첫 번째 메시지를 기반으로 채팅 제목 자동 생성"""
        try:
            # 첫 번째 메시지가 너무 짧으면 그대로 사용
            if len(first_message.strip()) <= 30:
                new_title = first_message.strip()
            else:
                # 긴 메시지의 경우 요약 생성
                new_title = await self._generate_chat_title(first_message)
            
            # 제목 길이 제한
            if len(new_title) > 50:
                new_title = new_title[:47] + "..."
            
            chat.title = new_title
            logger.info(f"채팅 제목 자동 생성: {chat.id} -> {new_title}")
            
        except Exception as e:
            logger.error(f"채팅 제목 생성 실패: {e}")
            # 실패 시 기본 제목 유지

    async def _generate_chat_title(self, message: str) -> str:
        """메시지 내용을 기반으로 채팅 제목 생성"""
        try:
            # 간단한 키워드 추출 방식
            words = message.strip().split()
            
            # 불용어 제거 (한국어 기준)
            stop_words = {
                '안녕하세요', '안녕', '안녕하십니까', '반갑습니다', '저는', '제가', '그런데', '그리고', 
                '그래서', '하지만', '그러나', '그럼', '그러면', '이것', '그것', '저것', '이거', '그거', 
                '저거', '여기', '거기', '저기', '어디', '언제', '어떻게', '왜', '무엇', '누구', '어느',
                '입니다', '습니다', '이에요', '예요', '이야', '야', '이다', '다', '요', '죠', '네', '예',
                '아니오', '아니', '맞아요', '맞습니다', '틀려요', '틀렸습니다', '알겠습니다', '알겠어요',
                '좋아요', '좋습니다', '나쁘네요', '나쁩니다', '대해', '관해', '에서', '에게', '에서는', 
                '에게는', '으로', '로', '을', '를', '이', '가', '은', '는', '의', '도', '만', '부터', '까지',
                '와', '과', '하고', '랑', '이랑', '더불어', '함께', '같이', '처럼', '마냥', '보다', '만큼',
                '뿐', '조차', '마저', '라도', '나마', '치고', '커녕', '고사하고'
            }
            
            # 의미있는 단어들만 추출
            meaningful_words = []
            for word in words[:10]:  # 처음 10개 단어만 분석
                cleaned_word = ''.join(c for c in word if c.isalnum() or c in '가-힣')
                if len(cleaned_word) >= 2 and cleaned_word not in stop_words:
                    meaningful_words.append(cleaned_word)
                    if len(meaningful_words) >= 4:  # 최대 4개 단어
                        break
            
            if meaningful_words:
                title = ' '.join(meaningful_words)
                return title if len(title) <= 30 else title[:27] + "..."
            else:
                # 키워드 추출 실패 시 첫 30자 사용
                return message[:30] + ("..." if len(message) > 30 else "")
                
        except Exception as e:
            logger.error(f"제목 생성 중 오류: {e}")
            return message[:30] + ("..." if len(message) > 30 else "") 