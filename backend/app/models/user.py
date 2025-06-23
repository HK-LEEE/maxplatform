from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from ..database import Base
from .tables import user_permissions, user_features, role_permissions, role_features, group_permissions, group_features

def generate_user_id():
    """사용자 고유 ID 생성 (UUID 기반)"""
    return uuid.uuid4()

class User(Base):
    __tablename__ = "users"
    
    # PostgreSQL 네이티브 UUID 타입 사용
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_user_id, index=True)
    
    # 실제 사용자 정보
    real_name = Column(String(100), nullable=False, comment="실제 사용자 이름")  # 실명
    display_name = Column(String(50), nullable=True, comment="표시될 이름 (닉네임)")  # 표시명/닉네임
    
    # 로그인 정보
    email = Column(String(100), unique=True, index=True, nullable=False, comment="로그인 이메일")
    phone_number = Column(String(20), nullable=True, comment="휴대폰 번호")
    hashed_password = Column(String(255), nullable=False)
    
    # 계정 상태
    is_active = Column(Boolean, default=True, comment="계정 활성화 상태")
    is_admin = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False, comment="이메일 인증 여부")
    approval_status = Column(String(20), default='pending', comment="승인 상태: pending, approved, rejected")
    approval_note = Column(Text, nullable=True, comment="승인/거부 사유")
    approved_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True, comment="승인한 관리자")
    approved_at = Column(DateTime, nullable=True, comment="승인 일시")
    
    # 역할 및 그룹 (직접 참조로 변경)
    role_id = Column(Integer, ForeignKey('roles.id'), nullable=True, comment="사용자 역할 ID")
    group_id = Column(Integer, ForeignKey('groups.id'), nullable=True, comment="사용자 그룹 ID")
    
    # 추가 정보
    department = Column(String(100), nullable=True, comment="부서")
    position = Column(String(100), nullable=True, comment="직책")
    bio = Column(Text, nullable=True, comment="자기소개")
    
    # 시스템 정보
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime, nullable=True)
    login_count = Column(Integer, default=0, comment="로그인 횟수")
    
    # 관계 정의 (직접 참조로 변경)
    workspaces = relationship("Workspace", back_populates="owner")
    role = relationship("Role", foreign_keys=[role_id], back_populates="users")
    group = relationship("Group", foreign_keys=[group_id], back_populates="members")
    approver = relationship("User", foreign_keys=[approved_by], remote_side=[id])
    
    # 권한 및 기능 관계
    permissions = relationship("Permission", secondary=user_permissions, back_populates="users")
    features = relationship("Feature", secondary=user_features, back_populates="users")
    
    # JWT Refresh Token 관계 (새로운 RefreshToken 테이블 사용)
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    
    # 서비스 관련 관계 추가 - 임시로 비활성화
    # services = relationship("Service", secondary="user_services", back_populates="users")

class Group(Base):
    __tablename__ = "groups"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)  # nullable로 변경
    
    # 관계 정의 (1:N 관계로 변경)
    members = relationship("User", foreign_keys='User.group_id', back_populates="group")
    creator = relationship("User", foreign_keys=[created_by])
    
    # 권한 및 기능 관계
    permissions = relationship("Permission", secondary=group_permissions, back_populates="groups")
    features = relationship("Feature", secondary=group_features, back_populates="groups")

class Role(Base):
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    # 관계 정의 (1:N 관계로 변경)
    users = relationship("User", foreign_keys='User.role_id', back_populates="role")
    
    # 권한 및 기능 관계
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")
    features = relationship("Feature", secondary=role_features, back_populates="roles")
    
    # 서비스 관련 관계 추가 - 임시로 비활성화
    # services = relationship("Service", secondary="role_services", back_populates="roles") 