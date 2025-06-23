from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from ..database import Base

def generate_token_id():
    """토큰 고유 ID 생성 (UUID 기반)"""
    return uuid.uuid4()

class RefreshToken(Base):
    """
    JWT Refresh Token 모델
    사용자의 Refresh Token을 안전하게 저장하고 관리
    """
    __tablename__ = "refresh_tokens"
    
    # 기본 정보 - PostgreSQL 네이티브 UUID 타입 사용
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_token_id, index=True)
    token = Column(Text, nullable=False, unique=True, comment="JWT Refresh Token")
    
    # 사용자 연결 - PostgreSQL 네이티브 UUID 타입 사용
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, comment="토큰 소유 사용자 ID")
    
    # 토큰 메타데이터
    device_info = Column(String(255), nullable=True, comment="기기 정보")
    ip_address = Column(String(45), nullable=True, comment="발급 시 IP 주소")
    user_agent = Column(Text, nullable=True, comment="사용자 에이전트")
    
    # 상태 관리
    is_active = Column(Boolean, default=True, comment="토큰 활성화 상태")
    is_revoked = Column(Boolean, default=False, comment="토큰 무효화 여부")
    
    # 시간 정보
    created_at = Column(DateTime, default=func.now(), comment="토큰 생성 시간")
    expires_at = Column(DateTime, nullable=False, comment="토큰 만료 시간")
    last_used_at = Column(DateTime, nullable=True, comment="마지막 사용 시간")
    revoked_at = Column(DateTime, nullable=True, comment="무효화 시간")
    
    # 관계 정의
    user = relationship("User", back_populates="refresh_tokens")
    
    def is_expired(self):
        """토큰이 만료되었는지 확인"""
        from datetime import datetime
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self):
        """토큰이 유효한지 확인"""
        return self.is_active and not self.is_revoked and not self.is_expired()
    
    def revoke(self):
        """토큰 무효화"""
        self.is_revoked = True
        self.revoked_at = func.now()
        self.is_active = False
    
    def use(self):
        """토큰 사용 기록"""
        self.last_used_at = func.now() 