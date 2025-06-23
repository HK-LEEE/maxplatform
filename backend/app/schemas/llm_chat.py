"""
LLM 채팅 서비스 Pydantic 스키마
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

# Enum 정의
class OwnerType(str, Enum):
    USER = "USER"  
    GROUP = "GROUP"

class SenderType(str, Enum):
    USER = "USER"
    AI = "AI"

class FeedbackRating(str, Enum):
    LIKE = "LIKE"
    DISLIKE = "DISLIKE"

class PublishScope(str, Enum):
    EVERYONE = "EVERYONE"
    GROUP = "GROUP" 
    USER = "USER"

class ModelType(str, Enum):
    AZURE_OPENAI = "AZURE_OPENAI"
    AZURE_CLAUDE = "AZURE_CLAUDE"
    AZURE_DEEPSEEK = "AZURE_DEEPSEEK"
    OLLAMA = "OLLAMA"
    FLOWSTUDIO = "FLOWSTUDIO"

# 페르소나 스키마
class PersonaBase(BaseModel):
    persona_name: str = Field(..., min_length=1, max_length=255)
    system_prompt: str = Field(..., min_length=1)

class PersonaCreate(PersonaBase):
    owner_type: OwnerType = OwnerType.USER
    owner_id: Optional[str] = None

class PersonaUpdate(BaseModel):
    persona_name: Optional[str] = Field(None, min_length=1, max_length=255)
    system_prompt: Optional[str] = Field(None, min_length=1)

class PersonaResponse(PersonaBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    owner_type: OwnerType
    owner_id: str
    created_at: datetime
    updated_at: datetime

# 프롬프트 템플릿 스키마
class PromptTemplateBase(BaseModel):
    template_title: str = Field(..., min_length=1, max_length=255)
    template_content: str = Field(..., min_length=1)

class PromptTemplateCreate(PromptTemplateBase):
    owner_type: OwnerType = OwnerType.USER
    owner_id: Optional[str] = None

class PromptTemplateUpdate(BaseModel):
    template_title: Optional[str] = Field(None, min_length=1, max_length=255)
    template_content: Optional[str] = Field(None, min_length=1)

class PromptTemplateResponse(PromptTemplateBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    owner_type: OwnerType
    owner_id: str
    created_at: datetime
    updated_at: datetime

# 채팅 스키마
class ChatCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    model_id: str = Field(..., min_length=1)
    persona_id: Optional[int] = None

class ChatUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    persona_id: Optional[int] = None

class ChatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    user_id: str
    model_id: str
    persona_id: Optional[int]
    title: str
    created_at: datetime
    updated_at: datetime
    persona: Optional[PersonaResponse] = None
    
    @classmethod
    def model_validate(cls, obj, **kwargs):
        # UUID 객체를 문자열로 변환
        if hasattr(obj, 'user_id') and isinstance(obj.user_id, uuid.UUID):
            obj.user_id = str(obj.user_id)
        return super().model_validate(obj, **kwargs)

# 메시지 스키마  
class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1)
    message_metadata: Optional[Dict[str, Any]] = None

class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    chat_id: str
    sender_type: SenderType
    content: str
    message_metadata: Optional[Dict[str, Any]]
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    total_cost: Optional[float]
    created_at: datetime

# 피드백 스키마
class MessageFeedbackCreate(BaseModel):
    rating: FeedbackRating
    comment: Optional[str] = None

class MessageFeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    message_id: str
    user_id: str
    rating: FeedbackRating
    comment: Optional[str]
    created_at: datetime
    
    @classmethod
    def model_validate(cls, obj, **kwargs):
        # UUID 객체를 문자열로 변환
        if hasattr(obj, 'user_id') and isinstance(obj.user_id, uuid.UUID):
            obj.user_id = str(obj.user_id)
        return super().model_validate(obj, **kwargs)

# 채팅 공유 스키마
class ChatShareCreate(BaseModel):
    expires_at: Optional[datetime] = None

class ChatShareResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    share_id: str
    chat_id: str
    created_by_user_id: str
    expires_at: Optional[datetime]
    created_at: datetime
    share_url: str
    
    @classmethod
    def model_validate(cls, obj, **kwargs):
        # UUID 객체를 문자열로 변환
        if hasattr(obj, 'created_by_user_id') and isinstance(obj.created_by_user_id, uuid.UUID):
            obj.created_by_user_id = str(obj.created_by_user_id)
        return super().model_validate(obj, **kwargs)

# 검색 스키마
class ChatSearchRequest(BaseModel):
    q: str = Field(..., min_length=1)

class ChatSearchResult(BaseModel):
    message_id: str
    chat_id: str
    chat_title: str
    content_snippet: str
    created_at: datetime

# FlowStudio 확장 스키마
class FlowPublishAccessCreate(BaseModel):
    flow_id: str
    publish_scope: PublishScope
    target_group_id: Optional[int] = None
    target_user_id: Optional[str] = None

class FlowPublishAccessResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    flow_id: str
    publish_scope: PublishScope
    target_group_id: Optional[int]
    target_user_id: Optional[str]
    created_at: datetime
    
    @classmethod
    def model_validate(cls, obj, **kwargs):
        # UUID 객체를 문자열로 변환
        if hasattr(obj, 'target_user_id') and isinstance(obj.target_user_id, uuid.UUID):
            obj.target_user_id = str(obj.target_user_id)
        return super().model_validate(obj, **kwargs)

# LLM 모델 정보
class LLMModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    description: Optional[str] = None
    is_available: bool = True

# RAG 데이터소스 정보
class RAGDataSourceInfo(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    document_count: int
    owner_type: OwnerType
    created_at: datetime

# 채팅 생성 요청 (모든 정보 포함)
class ChatCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    model_id: str = Field(..., min_length=1)
    persona_id: Optional[int] = None
    initial_message: Optional[str] = None

# 메시지 전송 요청
class MessageSendRequest(BaseModel):
    content: str = Field(..., min_length=1)
    rag_datasource_ids: Optional[List[int]] = None  # RAG 사용 시

# LLM 모델 관리 스키마
class LLMModelBase(BaseModel):
    model_name: str = Field(..., min_length=1, max_length=255)
    model_type: ModelType
    model_id: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    config: Dict[str, Any] = Field(..., description="모델 설정 정보 (JSON)")

class LLMModelCreate(LLMModelBase):
    owner_type: OwnerType = OwnerType.USER
    owner_id: Optional[str] = None

class LLMModelUpdate(BaseModel):
    model_name: Optional[str] = Field(None, min_length=1, max_length=255)
    model_type: Optional[ModelType] = None
    model_id: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class LLMModelResponse(LLMModelBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    owner_type: OwnerType
    owner_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime