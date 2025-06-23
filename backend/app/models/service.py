from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Table
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.dialects.postgresql import UUID
from ..database import Base

# 다대다 관계를 위한 연결 테이블
user_service_association = Table(
    'user_services',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True),
    Column('service_id', Integer, ForeignKey('services.id'), primary_key=True),
    Column('granted_at', DateTime, default=func.now()),
    Column('granted_by', UUID(as_uuid=True), ForeignKey('users.id'))
)

role_service_association = Table(
    'role_services',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True),
    Column('service_id', Integer, ForeignKey('services.id'), primary_key=True),
    Column('granted_at', DateTime, default=func.now()),
    Column('granted_by', UUID(as_uuid=True), ForeignKey('users.id'))
)

class Service(Base):
    """서비스 정보를 관리하는 모델"""
    __tablename__ = "services"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, comment="서비스명")
    display_name = Column(String(100), nullable=False, comment="화면에 표시되는 서비스명")
    description = Column(Text, nullable=True, comment="서비스 설명")
    
    # 서비스 접근 정보
    url = Column(String(500), nullable=False, comment="서비스 URL 또는 라우트")
    icon_url = Column(String(500), nullable=True, comment="서비스 아이콘 URL")
    thumbnail_url = Column(String(500), nullable=True, comment="서비스 썸네일 이미지 URL")
    
    # 서비스 상태 및 설정
    is_active = Column(Boolean, default=True, comment="서비스 활성화 여부")
    is_external = Column(Boolean, default=False, comment="외부 서비스 여부")
    requires_auth = Column(Boolean, default=True, comment="인증 필요 여부")
    open_in_new_tab = Column(Boolean, default=False, comment="새 탭에서 열기 여부")
    
    # 정렬 및 그룹화
    sort_order = Column(Integer, default=0, comment="정렬 순서")
    category = Column(String(50), nullable=True, comment="서비스 카테고리")
    
    # 시스템 정보
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    # 관계 정의
    creator = relationship("User", foreign_keys=[created_by])
    # users = relationship("User", secondary=user_service_association, back_populates="services")
    # roles = relationship("Role", secondary=role_service_association, back_populates="services")

class ServiceCategory(Base):
    """서비스 카테고리 관리"""
    __tablename__ = "service_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, comment="카테고리명")
    display_name = Column(String(100), nullable=False, comment="화면에 표시되는 카테고리명")
    description = Column(Text, nullable=True, comment="카테고리 설명")
    sort_order = Column(Integer, default=0, comment="정렬 순서")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

class UserServicePermission(Base):
    """사용자별 서비스 권한 상세 관리"""
    __tablename__ = "user_service_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    service_id = Column(Integer, ForeignKey('services.id'), nullable=False)
    
    # 권한 세부사항
    permission_level = Column(String(20), default='read', comment="권한 레벨: read, write, admin")
    custom_permissions = Column(Text, nullable=True, comment="JSON 형태의 커스텀 권한")
    
    # 권한 부여 정보
    granted_at = Column(DateTime, default=func.now())
    granted_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    expires_at = Column(DateTime, nullable=True, comment="권한 만료일")
    
    # 상태
    is_active = Column(Boolean, default=True)
    
    # 관계 정의
    user = relationship("User", foreign_keys=[user_id])
    service = relationship("Service")
    granted_by_user = relationship("User", foreign_keys=[granted_by]) 