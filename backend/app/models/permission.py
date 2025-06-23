from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base
from .tables import user_permissions, user_features, role_permissions, role_features, group_permissions, group_features

class FeatureCategory(Base):
    """기능 카테고리 모델"""
    __tablename__ = "feature_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, comment="카테고리명")
    display_name = Column(String(100), nullable=False, comment="화면에 표시되는 카테고리명")
    description = Column(Text, nullable=True, comment="카테고리 설명")
    icon = Column(String(50), nullable=True, comment="카테고리 아이콘")
    color = Column(String(20), nullable=True, comment="카테고리 색상")
    
    # 정렬 및 상태
    sort_order = Column(Integer, default=0, comment="정렬 순서")
    is_active = Column(Boolean, default=True, comment="카테고리 활성화 여부")
    
    # 시스템 정보
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 관계 정의
    features = relationship("Feature", back_populates="feature_category", order_by="Feature.name")

class Permission(Base):
    """권한 정의 모델"""
    __tablename__ = "permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, comment="권한명")
    display_name = Column(String(100), nullable=False, comment="화면에 표시되는 권한명")
    description = Column(Text, nullable=True, comment="권한 설명")
    
    # 권한 카테고리
    category = Column(String(50), nullable=True, comment="권한 카테고리")
    
    # 시스템 정보
    is_active = Column(Boolean, default=True, comment="권한 활성화 여부")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 관계 정의
    users = relationship("User", secondary=user_permissions, back_populates="permissions")
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")
    groups = relationship("Group", secondary=group_permissions, back_populates="permissions")

class Feature(Base):
    """기능 정의 모델"""
    __tablename__ = "features"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, comment="기능명")
    display_name = Column(String(200), nullable=False, comment="화면에 표시되는 기능명")
    description = Column(Text, nullable=True, comment="기능 설명")
    
    # 기능 정보
    category_id = Column(Integer, ForeignKey('feature_categories.id'), nullable=True, comment="카테고리 ID")
    icon = Column(String(50), nullable=True, comment="기능 아이콘")
    url_path = Column(String(200), nullable=True, comment="URL 경로")
    
    # 기능 설정
    auto_grant = Column(Boolean, default=False, comment="자동 부여 여부")
    is_active = Column(Boolean, default=True, comment="기능 활성화 여부")
    requires_approval = Column(Boolean, default=False, comment="승인 필요 여부")
    is_external = Column(Boolean, default=False, comment="외부 링크 여부")
    open_in_new_tab = Column(Boolean, default=False, comment="새 탭에서 열기 여부")
    
    # 정렬
    sort_order = Column(Integer, default=0, comment="카테고리 내 정렬 순서")
    
    # 시스템 정보
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 관계 정의
    feature_category = relationship("FeatureCategory", back_populates="features")
    users = relationship("User", secondary=user_features, back_populates="features")
    roles = relationship("Role", secondary=role_features, back_populates="features")
    groups = relationship("Group", secondary=group_features, back_populates="features") 