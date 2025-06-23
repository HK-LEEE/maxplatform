from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from ..database import Base

class Workspace(Base):
    __tablename__ = "workspaces"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="워크스페이스명")
    description = Column(Text, nullable=True, comment="워크스페이스 설명")
    
    # 소유자 정보 - PostgreSQL UUID 타입 사용
    owner_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    # 상태 정보
    is_active = Column(Boolean, default=True, comment="활성화 상태")
    is_private = Column(Boolean, default=False, comment="비공개 워크스페이스 여부")
    
    # Jupyter 설정
    jupyter_port = Column(Integer, nullable=True)
    jupyter_token = Column(String(255), nullable=True)
    jupyter_status = Column(String(20), default="stopped")  # stopped, starting, running, error
    
    # 파일 시스템 정보
    path = Column(String(500), nullable=True)  # workspace_path에서 path로 변경
    max_storage_mb = Column(Integer, default=1000)
    
    # 시스템 정보
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_accessed = Column(DateTime, nullable=True)
    
    # 관계 정의
    owner = relationship("User", back_populates="workspaces") 