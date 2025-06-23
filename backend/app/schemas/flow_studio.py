from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from enum import Enum

class PublishStatus(str, Enum):
    """Publish 상태 열거형"""
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"

class ProjectBase(BaseModel):
    """프로젝트 기본 스키마"""
    name: str = Field(..., min_length=1, max_length=255, description="프로젝트 이름")
    description: Optional[str] = Field(None, description="프로젝트 설명")
    is_default: bool = Field(False, description="기본 프로젝트 여부")

class ProjectCreate(ProjectBase):
    """프로젝트 생성 스키마 - 권한 기능 포함"""
    owner_type: str = Field("user", description="소유자 타입: user 또는 group")

class ProjectUpdate(BaseModel):
    """프로젝트 수정 스키마"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_default: Optional[bool] = None

class ProjectResponse(ProjectBase):
    """프로젝트 응답 스키마 - 권한 정보 포함"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    user_id: str
    group_id: Optional[str] = None
    owner_type: str
    created_at: datetime
    updated_at: datetime
    flows: List["FlowResponse"] = []
    
    @classmethod
    def model_validate(cls, obj, **kwargs):
        # UUID 객체를 문자열로 변환
        if hasattr(obj, 'id') and isinstance(obj.id, uuid.UUID):
            obj.id = str(obj.id)
        if hasattr(obj, 'user_id') and isinstance(obj.user_id, uuid.UUID):
            obj.user_id = str(obj.user_id)
        if hasattr(obj, 'group_id') and obj.group_id and isinstance(obj.group_id, uuid.UUID):
            obj.group_id = str(obj.group_id)
        
        # flows 리스트 내부의 각 Flow 객체들도 UUID 변환
        if hasattr(obj, 'flows') and obj.flows:
            for flow in obj.flows:
                if hasattr(flow, 'id') and isinstance(flow.id, uuid.UUID):
                    flow.id = str(flow.id)
                if hasattr(flow, 'user_id') and isinstance(flow.user_id, uuid.UUID):
                    flow.user_id = str(flow.user_id)
                if hasattr(flow, 'group_id') and flow.group_id and isinstance(flow.group_id, uuid.UUID):
                    flow.group_id = str(flow.group_id)
                if hasattr(flow, 'project_id') and isinstance(flow.project_id, uuid.UUID):
                    flow.project_id = str(flow.project_id)
        
        return super().model_validate(obj, **kwargs)

class FlowBase(BaseModel):
    """플로우 기본 스키마"""
    name: str = Field(..., min_length=1, max_length=255, description="플로우 이름")
    description: Optional[str] = Field(None, description="플로우 설명")
    flow_data: Dict[str, Any] = Field(default_factory=dict, description="플로우 구성 데이터")
    is_active: bool = Field(True, description="활성화 상태")
    publish_status: PublishStatus = Field(PublishStatus.DRAFT, description="배포 상태")
    version: str = Field("1.0.0", description="플로우 버전")
    is_latest_published: bool = Field(False, description="최신 배포 버전 여부")

class FlowCreate(FlowBase):
    """플로우 생성 스키마 - 권한 기능 포함"""
    project_id: str = Field(..., description="소속 프로젝트 ID")
    owner_type: str = Field("user", description="소유자 타입: user 또는 group")

class FlowUpdate(BaseModel):
    """플로우 수정 스키마"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    flow_data: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    publish_status: Optional[PublishStatus] = None
    version: Optional[str] = None

class FlowResponse(FlowBase):
    """플로우 응답 스키마 - 권한 정보 포함"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    project_id: str
    user_id: str
    group_id: Optional[str] = None
    owner_type: str
    created_at: datetime
    updated_at: datetime
    
    @classmethod
    def model_validate(cls, obj, **kwargs):
        # UUID 객체를 문자열로 변환
        if hasattr(obj, 'id') and isinstance(obj.id, uuid.UUID):
            obj.id = str(obj.id)
        if hasattr(obj, 'project_id') and isinstance(obj.project_id, uuid.UUID):
            obj.project_id = str(obj.project_id)
        if hasattr(obj, 'user_id') and isinstance(obj.user_id, uuid.UUID):
            obj.user_id = str(obj.user_id)
        if hasattr(obj, 'group_id') and obj.group_id and isinstance(obj.group_id, uuid.UUID):
            obj.group_id = str(obj.group_id)
        return super().model_validate(obj, **kwargs)

class FlowSaveRequest(BaseModel):
    """플로우 저장 요청 스키마"""
    name: str = Field(..., min_length=1, max_length=255, description="플로우 이름")
    description: Optional[str] = Field(None, description="플로우 설명")
    flow_data: Dict[str, Any] = Field(..., description="플로우 구성 데이터")
    owner_type: str = Field("user", description="소유자 타입: user 또는 group")
    project_id: Optional[str] = Field(None, description="기존 프로젝트 ID (없으면 새 프로젝트 생성)")

class ComponentTemplateBase(BaseModel):
    """컴포넌트 템플릿 기본 스키마"""
    name: str = Field(..., min_length=1, max_length=255, description="컴포넌트 이름")
    category: str = Field(..., min_length=1, max_length=100, description="카테고리")
    description: Optional[str] = Field(None, description="설명")
    icon: Optional[str] = Field(None, description="아이콘")
    component_type: str = Field(..., min_length=1, max_length=100, description="컴포넌트 타입")
    config_schema: Dict[str, Any] = Field(default_factory=dict, description="설정 스키마")
    input_schema: Dict[str, Any] = Field(default_factory=dict, description="입력 스키마")
    output_schema: Dict[str, Any] = Field(default_factory=dict, description="출력 스키마")
    python_code: Optional[str] = Field(None, description="Python 실행 코드")
    is_builtin: bool = Field(True, description="내장 컴포넌트 여부")

class ComponentTemplateCreate(ComponentTemplateBase):
    """컴포넌트 템플릿 생성 스키마"""
    pass

class ComponentTemplateResponse(ComponentTemplateBase):
    """컴포넌트 템플릿 응답 스키마"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    created_at: datetime

class FlowComponentBase(BaseModel):
    """플로우 컴포넌트 기본 스키마"""
    node_id: str = Field(..., min_length=1, max_length=100, description="노드 ID")
    position_x: int = Field(0, description="X 좌표")
    position_y: int = Field(0, description="Y 좌표")
    config_data: Dict[str, Any] = Field(default_factory=dict, description="설정 데이터")

class FlowComponentCreate(FlowComponentBase):
    """플로우 컴포넌트 생성 스키마"""
    flow_id: str = Field(..., description="플로우 ID")
    template_id: str = Field(..., description="템플릿 ID")

class FlowComponentUpdate(BaseModel):
    """플로우 컴포넌트 수정 스키마"""
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    config_data: Optional[Dict[str, Any]] = None

class FlowComponentResponse(FlowComponentBase):
    """플로우 컴포넌트 응답 스키마"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    flow_id: str
    template_id: str
    created_at: datetime
    updated_at: datetime

class FlowConnectionBase(BaseModel):
    """플로우 연결 기본 스키마"""
    source_handle: str = Field(..., min_length=1, max_length=100, description="소스 핸들")
    target_handle: str = Field(..., min_length=1, max_length=100, description="타겟 핸들")

class FlowConnectionCreate(FlowConnectionBase):
    """플로우 연결 생성 스키마"""
    flow_id: str = Field(..., description="플로우 ID")
    source_component_id: str = Field(..., description="소스 컴포넌트 ID")
    target_component_id: str = Field(..., description="타겟 컴포넌트 ID")

class FlowConnectionResponse(FlowConnectionBase):
    """플로우 연결 응답 스키마"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    flow_id: str
    source_component_id: str
    target_component_id: str
    created_at: datetime

class FlowExecutionBase(BaseModel):
    """플로우 실행 기본 스키마"""
    status: str = Field("running", description="실행 상태")
    input_data: Optional[Dict[str, Any]] = Field(None, description="입력 데이터")
    output_data: Optional[Dict[str, Any]] = Field(None, description="출력 데이터")
    error_message: Optional[str] = Field(None, description="오류 메시지")
    execution_time_ms: Optional[int] = Field(None, description="실행 시간(ms)")

class FlowExecutionCreate(BaseModel):
    """플로우 실행 생성 스키마"""
    flow_id: str = Field(..., description="플로우 ID")
    input_data: Optional[Dict[str, Any]] = Field(None, description="입력 데이터")

class FlowExecutionResponse(FlowExecutionBase):
    """플로우 실행 응답 스키마"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    flow_id: str
    user_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    
    @classmethod
    def model_validate(cls, obj, **kwargs):
        # UUID 객체를 문자열로 변환
        if hasattr(obj, 'id') and isinstance(obj.id, uuid.UUID):
            obj.id = str(obj.id)
        if hasattr(obj, 'flow_id') and isinstance(obj.flow_id, uuid.UUID):
            obj.flow_id = str(obj.flow_id)
        if hasattr(obj, 'user_id') and isinstance(obj.user_id, uuid.UUID):
            obj.user_id = str(obj.user_id)
        return super().model_validate(obj, **kwargs)

class FlowPublishRequest(BaseModel):
    """플로우 배포 요청 스키마"""
    version: Optional[str] = Field(None, description="배포 버전 (없으면 자동 증가)")
    publish_message: Optional[str] = Field(None, description="배포 메시지")
    target_environment: str = Field("production", description="배포 환경")
    deployment_config: Optional[Dict[str, Any]] = Field(None, description="배포 설정")

class FlowPublishResponse(BaseModel):
    """플로우 배포 응답 스키마"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    flow_id: str
    version: str
    publish_status: PublishStatus
    published_by: str
    publish_message: Optional[str] = None
    target_environment: str
    webhook_called: bool
    webhook_response: Optional[Dict[str, Any]] = None
    published_at: datetime

class FlowStudioStats(BaseModel):
    """Flow Studio 통계 스키마"""
    total_projects: int
    total_flows: int
    total_executions: int
    active_flows: int
    published_flows: int
    draft_flows: int 