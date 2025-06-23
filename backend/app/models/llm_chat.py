"""
LLM 채팅 서비스 모델
"""
import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, 
    ForeignKey, Enum as SAEnum, JSON, Numeric, Boolean
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from ..database import Base

# Enum 정의
class OwnerType(str, enum.Enum):
    USER = "USER"
    GROUP = "GROUP"

class SenderType(str, enum.Enum):
    USER = "USER"
    AI = "AI"

class FeedbackRating(str, enum.Enum):
    LIKE = "LIKE"
    DISLIKE = "DISLIKE"

class PublishScope(str, enum.Enum):
    EVERYONE = "EVERYONE"
    GROUP = "GROUP"
    USER = "USER"

class ModelType(str, enum.Enum):
    AZURE_OPENAI = "AZURE_OPENAI"
    AZURE_CLAUDE = "AZURE_CLAUDE"
    AZURE_DEEPSEEK = "AZURE_DEEPSEEK"
    OLLAMA = "OLLAMA"
    FLOWSTUDIO = "FLOWSTUDIO"

class MAXLLM_Persona(Base):
    """페르소나 관리 모델"""
    __tablename__ = 'maxllm_personas'
    
    id = Column(Integer, primary_key=True, index=True)
    persona_name = Column(String(255), nullable=False, index=True)
    system_prompt = Column(Text, nullable=False)
    owner_type = Column(SAEnum(OwnerType), nullable=False)
    owner_id = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 관계
    chats = relationship("MAXLLM_Chat", back_populates="persona")

class MAXLLM_Prompt_Template(Base):
    """프롬프트 템플릿 관리 모델"""
    __tablename__ = 'maxllm_prompt_templates'
    
    id = Column(Integer, primary_key=True, index=True)
    template_title = Column(String(255), nullable=False, index=True)
    template_content = Column(Text, nullable=False)
    owner_type = Column(SAEnum(OwnerType), nullable=False)
    owner_id = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class MAXLLM_Chat(Base):
    """채팅 세션 모델"""
    __tablename__ = 'maxllm_chats'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    model_id = Column(String(255), nullable=False)  # LLM 모델 또는 FlowStudio ID
    persona_id = Column(Integer, ForeignKey('maxllm_personas.id'), nullable=True)
    title = Column(String(500), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 관계
    persona = relationship("MAXLLM_Persona", back_populates="chats")
    messages = relationship("MAXLLM_Message", back_populates="chat", cascade="all, delete-orphan")

class MAXLLM_Message(Base):
    """채팅 메시지 모델"""
    __tablename__ = 'maxllm_messages'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chat_id = Column(String(36), ForeignKey('maxllm_chats.id'), nullable=False, index=True)
    sender_type = Column(SAEnum(SenderType), nullable=False)
    content = Column(Text, nullable=False)
    message_metadata = Column(JSON, nullable=True)  # RAG 사용 정보, 모델 정보 등
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_cost = Column(Numeric(10, 8), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    
    # 관계
    chat = relationship("MAXLLM_Chat", back_populates="messages")
    feedbacks = relationship("MAXLLM_Message_Feedback", back_populates="message", cascade="all, delete-orphan")

class MAXLLM_Message_Feedback(Base):
    """메시지 피드백 모델"""
    __tablename__ = 'maxllm_message_feedbacks'
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String(36), ForeignKey('maxllm_messages.id'), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    rating = Column(SAEnum(FeedbackRating), nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    
    # 관계
    message = relationship("MAXLLM_Message", back_populates="feedbacks")

class MAXLLM_Shared_Chat(Base):
    """채팅 공유 링크 모델"""
    __tablename__ = 'maxllm_shared_chats'
    
    share_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4())[:8])
    chat_id = Column(String(36), ForeignKey('maxllm_chats.id'), nullable=False, index=True)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    
    # 관계
    chat = relationship("MAXLLM_Chat")

# FlowStudio Publish 확장
class MAXLLM_Flow_Publish_Access(Base):
    """FlowStudio 공개 범위 관리 모델"""
    __tablename__ = 'maxllm_flow_publish_access'
    
    id = Column(Integer, primary_key=True, index=True)
    flow_id = Column(String(36), nullable=False, index=True)  # FlowStudioFlow ID
    publish_scope = Column(SAEnum(PublishScope), nullable=False, index=True)
    target_group_id = Column(Integer, nullable=True)  # GROUP 범위인 경우
    target_user_id = Column(UUID(as_uuid=True), nullable=True)  # USER 범위인 경우
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class MAXLLM_Model(Base):
    """LLM 모델 관리 테이블"""
    __tablename__ = 'maxllm_models'
    
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(255), nullable=False, index=True)
    model_type = Column(SAEnum(ModelType), nullable=False, index=True)
    model_id = Column(String(255), nullable=False, index=True)  # 실제 모델 식별자
    description = Column(Text, nullable=True)
    config = Column(JSON, nullable=False)  # 모델 설정 정보 (JSON)
    owner_type = Column(SAEnum(OwnerType), nullable=False)
    owner_id = Column(String(255), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

# 백업 테이블들
class MAXLLM_Chat_Backup(Base):
    """채팅 백업 테이블"""
    __tablename__ = 'maxllm_chats_backup'
    
    id = Column(String(36), primary_key=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    model_id = Column(String(255), nullable=False)
    persona_id = Column(Integer, nullable=True)
    title = Column(String(500), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    deleted_at = Column(DateTime, server_default=func.now())  # 삭제 시점
    deleted_by = Column(UUID(as_uuid=True), nullable=False)  # 삭제한 사용자

class MAXLLM_Message_Backup(Base):
    """메시지 백업 테이블"""
    __tablename__ = 'maxllm_messages_backup'
    
    id = Column(String(36), primary_key=True)
    chat_id = Column(String(36), nullable=False, index=True)
    sender_type = Column(SAEnum(SenderType), nullable=False)
    content = Column(Text, nullable=False)
    message_metadata = Column(JSON, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_cost = Column(Numeric(10, 8), nullable=True)
    created_at = Column(DateTime, nullable=False)
    deleted_at = Column(DateTime, server_default=func.now())  # 삭제 시점
    deleted_by = Column(UUID(as_uuid=True), nullable=False)  # 삭제한 사용자