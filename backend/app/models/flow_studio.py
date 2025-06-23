from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from ..database import Base

class PublishStatus(enum.Enum):
    """Publish 상태 열거형"""
    DRAFT = "DRAFT"           # 초안 (저장만 됨)
    PUBLISHED = "PUBLISHED"   # 배포됨 (운영 환경에서 실행 가능)
    DEPRECATED = "DEPRECATED" # 사용 중단 (기존 버전 유지하지만 새로운 실행 불가)
    ARCHIVED = "ARCHIVED"     # 아카이브됨 (완전히 비활성화)

class Project(Base):
    """Flow Studio 프로젝트 모델"""
    __tablename__ = "flow_studio_projects"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    user_id = Column(String(36), nullable=False, index=True)
    group_id = Column(String(36), nullable=True, index=True)  # 그룹 소유 프로젝트용
    owner_type = Column(String(20), nullable=False, default="user")  # "user" or "group"
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계 정의
    flows = relationship("FlowStudioFlow", back_populates="project", cascade="all, delete-orphan")

class FlowStudioFlow(Base):
    """플로우 모델 - 권한 기능 및 Publish 상태 관리 포함"""
    __tablename__ = "flow_studio_flows"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("flow_studio_projects.id"), nullable=False)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    flow_data = Column(JSON, nullable=False, default=dict)  # 플로우 노드 및 연결 정보
    
    # 권한 관련 필드
    user_id = Column(String(36), nullable=False, index=True)  # 플로우 생성자
    group_id = Column(String(36), nullable=True, index=True)  # 그룹 소유 플로우용
    owner_type = Column(String(20), nullable=False, default="user")  # "user" or "group"
    
    # Publish 상태 관리 (신규 추가)
    publish_status = Column(SQLEnum(PublishStatus), nullable=False, default=PublishStatus.DRAFT, index=True)
    version = Column(String(50), nullable=False, default="1.0.0")  # 시맨틱 버저닝
    is_latest_published = Column(Boolean, default=False, index=True)  # 최신 배포 버전 여부
    
    # 상태 및 메타데이터
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계 정의
    project = relationship("Project", back_populates="flows")
    components = relationship("FlowComponent", back_populates="flow", cascade="all, delete-orphan")
    connections = relationship("FlowConnection", back_populates="flow", cascade="all, delete-orphan")
    executions = relationship("FlowStudioExecution", back_populates="flow", cascade="all, delete-orphan")
    publish_history = relationship("FlowStudioPublish", back_populates="flow", cascade="all, delete-orphan")

class FlowStudioPublish(Base):
    """플로우 배포 이력 관리 테이블"""
    __tablename__ = "flow_studio_publishes"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    flow_id = Column(String(36), ForeignKey("flow_studio_flows.id"), nullable=False, index=True)
    
    # 배포 정보
    version = Column(String(50), nullable=False)  # 배포된 버전
    publish_status = Column(SQLEnum(PublishStatus), nullable=False, index=True)
    
    # 배포자 정보
    published_by = Column(String(36), nullable=False, index=True)  # 배포한 사용자 ID
    publish_message = Column(Text, nullable=True)  # 배포 메시지/설명
    
    # 배포 시점의 플로우 데이터 스냅샷
    flow_data_snapshot = Column(JSON, nullable=False)  # 배포 시점의 플로우 구성
    
    # 웹훅 및 알림 정보
    webhook_url = Column(String(500), nullable=True)  # LLMOps 시스템 웹훅 URL
    webhook_called = Column(Boolean, default=False)   # 웹훅 호출 여부
    webhook_response = Column(JSON, nullable=True)    # 웹훅 응답 정보
    
    # 배포 환경 정보
    target_environment = Column(String(50), nullable=False, default="production")  # production, staging, development
    deployment_config = Column(JSON, nullable=True)  # 배포 설정 (포트, 리소스 등)
    
    # 시간 정보
    published_at = Column(DateTime, default=datetime.utcnow, index=True)
    deprecated_at = Column(DateTime, nullable=True)  # 사용 중단 시간
    
    # 관계 정의
    flow = relationship("FlowStudioFlow", back_populates="publish_history")

class ComponentTemplate(Base):
    """컴포넌트 템플릿 모델"""
    __tablename__ = "flow_studio_component_templates"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    icon = Column(String(100), nullable=True)
    component_type = Column(String(100), nullable=False)  # input, output, processing, model, etc.
    config_schema = Column(JSON, nullable=False, default=dict)  # 컴포넌트 설정 스키마
    input_schema = Column(JSON, nullable=False, default=dict)   # 입력 스키마
    output_schema = Column(JSON, nullable=False, default=dict)  # 출력 스키마
    python_code = Column(Text, nullable=True)  # 실행 가능한 Python 코드
    is_builtin = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 정의
    flow_components = relationship("FlowComponent", back_populates="template")

class FlowComponent(Base):
    """플로우 내 컴포넌트 인스턴스 모델"""
    __tablename__ = "flow_studio_components"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    flow_id = Column(String(36), ForeignKey("flow_studio_flows.id"), nullable=False)
    template_id = Column(String(36), ForeignKey("flow_studio_component_templates.id"), nullable=False)
    node_id = Column(String(100), nullable=False)  # 프론트엔드에서 사용하는 노드 ID
    position_x = Column(Integer, default=0)
    position_y = Column(Integer, default=0)
    config_data = Column(JSON, nullable=False, default=dict)  # 컴포넌트별 설정값
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계 정의
    flow = relationship("FlowStudioFlow", back_populates="components")
    template = relationship("ComponentTemplate", back_populates="flow_components")

class FlowConnection(Base):
    """플로우 컴포넌트 간 연결 모델"""
    __tablename__ = "flow_studio_connections"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    flow_id = Column(String(36), ForeignKey("flow_studio_flows.id"), nullable=False)
    source_component_id = Column(String(36), ForeignKey("flow_studio_components.id"), nullable=False)
    target_component_id = Column(String(36), ForeignKey("flow_studio_components.id"), nullable=False)
    source_handle = Column(String(100), nullable=False)  # 출력 핸들
    target_handle = Column(String(100), nullable=False)  # 입력 핸들
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 정의
    flow = relationship("FlowStudioFlow", back_populates="connections")

class FlowStudioExecution(Base):
    """플로우 실행 로그 모델"""
    __tablename__ = "flow_studio_executions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    flow_id = Column(String(36), ForeignKey("flow_studio_flows.id"), nullable=False)
    user_id = Column(String(36), nullable=False)
    status = Column(String(50), nullable=False, default="running")  # running, completed, failed
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # 관계 정의
    flow = relationship("FlowStudioFlow", back_populates="executions") 