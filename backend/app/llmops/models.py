"""
LLMOps 모델 정의

멀티테넌트 LLMOps 기능을 위한 데이터베이스 모델들:
- RAGDataSource: RAG용 데이터소스 관리
- Flow: 시각적 워크플로우 정의 (버전 관리 지원)
- FlowExecutionLog: 플로우 실행 기록 및 로깅
- Secret: 민감 정보 관리 (API 키 등)
- 권한 기반 소유권 모델
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, JSON, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum as PyEnum
import uuid
from cryptography.fernet import Fernet
import os

from ..database import Base
from ..models.user import User
from ..models.workspace import Workspace

# 소유자 타입 Enum 정의
class OwnerType(PyEnum):
    GROUP = "GROUP"
    USER = "USER"

# 실행 상태 Enum 정의
class ExecutionStatus(PyEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS" 
    FAILURE = "FAILURE"

def generate_uuid():
    """UUID 생성 함수"""
    return uuid.uuid4()

# 암호화 키 관리
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', Fernet.generate_key().decode())
cipher_suite = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)

class RAGDataSource(Base):
    """
    RAG 데이터소스 모델
    
    워크스페이스 또는 개인 사용자가 소유할 수 있는 벡터 DB 컬렉션을 관리합니다.
    각 데이터소스는 ChromaDB의 고유한 컬렉션과 연결됩니다.
    """
    __tablename__ = "rag_datasources"
    
    # 기본 필드
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="데이터소스 이름")
    description = Column(Text, nullable=True, comment="데이터소스 설명")
    
    # 소유권 정보 (업데이트됨)
    owner_type = Column(Enum(OwnerType), nullable=False, comment="소유자 타입: GROUP 또는 USER")
    owner_id = Column(String(50), nullable=False, comment="소유자 ID (group.id 또는 user.id)")
    
    # ChromaDB 연결 정보
    chroma_collection_name = Column(String(200), unique=True, nullable=False, 
                                  comment="ChromaDB 내 고유 컬렉션 이름")
    
    # 임베딩 설정 (JSON 저장)
    embedding_config = Column(JSON, nullable=True, comment="임베딩 모델 및 설정 정보")
    
    # 상태 정보
    is_active = Column(Boolean, default=True, comment="활성화 상태")
    document_count = Column(Integer, default=0, comment="저장된 문서 수")
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now(), comment="마지막 업데이트 시간")
    
    # 메타데이터
    tags = Column(JSON, nullable=True, comment="태그 목록")
    settings = Column(JSON, nullable=True, comment="추가 설정")
    
    # 시스템 정보
    created_at = Column(DateTime, default=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 관계 정의
    creator = relationship("User", foreign_keys=[created_by])
    flows = relationship("Flow", back_populates="rag_datasource")

    def __repr__(self):
        return f"<RAGDataSource(id={self.id}, name='{self.name}', owner_type='{self.owner_type}')>"

class Flow(Base):
    """
    워크플로우 모델 (버전 관리 지원)
    
    React Flow 기반의 시각적 워크플로우 정의를 저장합니다.
    버전 관리를 통해 변경 이력을 추적하고 특정 버전으로 롤백할 수 있습니다.
    """
    __tablename__ = "flows"
    
    # 기본 필드
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="플로우 이름")
    description = Column(Text, nullable=True, comment="플로우 설명")
    
    # React Flow JSON 데이터
    flow_data = Column(JSON, nullable=False, comment="React Flow 노드 및 엣지 데이터")
    
    # 소유권 정보 (신규 추가)
    owner_type = Column(Enum(OwnerType), nullable=False, comment="소유자 타입: GROUP 또는 USER")
    owner_id = Column(UUID(as_uuid=True), nullable=False, comment="소유자 ID (workspace.id 또는 user.id)")
    
    # 버전 관리 (신규 추가)
    version = Column(Integer, default=1, nullable=False, comment="플로우 버전")
    parent_flow_id = Column(Integer, ForeignKey('flows.id'), nullable=True, 
                           comment="원본 플로우 ID (첫 버전은 null)")
    is_latest = Column(Boolean, default=True, nullable=False, 
                      comment="동일 플로우 그룹 내 최신 버전 여부")
    
    # 워크스페이스 연결 (기존 유지)
    workspace_id = Column(Integer, ForeignKey('workspaces.id'), nullable=True)
    
    # 설정 및 메타데이터
    is_template = Column(Boolean, default=False, comment="템플릿 여부")
    is_public = Column(Boolean, default=False, comment="공개 여부")
    tags = Column(JSON, nullable=True, comment="태그 목록")
    
    # 실행 통계
    execution_count = Column(Integer, default=0, comment="실행 횟수")
    last_executed = Column(DateTime, nullable=True, comment="마지막 실행 시간")
    
    # RAG 데이터소스 연결 (선택적)
    rag_datasource_id = Column(Integer, ForeignKey('rag_datasources.id'), nullable=True)
    
    # 시스템 정보
    created_at = Column(DateTime, default=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 관계 정의
    workspace = relationship("Workspace", foreign_keys=[workspace_id])
    creator = relationship("User", foreign_keys=[created_by])
    rag_datasource = relationship("RAGDataSource", back_populates="flows")
    execution_logs = relationship("FlowExecutionLog", back_populates="flow", cascade="all, delete-orphan")
    
    # 자기 참조 관계 (버전 관리)
    parent_flow = relationship("Flow", remote_side=[id], backref="child_versions")

    def __repr__(self):
        return f"<Flow(id={self.id}, name='{self.name}', version={self.version}, owner_type='{self.owner_type}')>"

class FlowExecutionLog(Base):
    """
    플로우 실행 기록 모델 (신규 생성)
    
    각 플로우 실행에 대한 상세 로그와 결과를 저장합니다.
    실행 추적, 디버깅, 성능 분석에 사용됩니다.
    """
    __tablename__ = "flow_execution_logs"
    
    # 기본 필드
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid, index=True)
    flow_id = Column(Integer, ForeignKey('flows.id'), nullable=False)
    version = Column(Integer, nullable=False, comment="실행된 플로우 버전")
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, comment="실행자")
    
    # 실행 데이터
    inputs = Column(JSON, nullable=True, comment="사용자 입력값")
    outputs = Column(JSON, nullable=True, comment="최종 결과")
    status = Column(Enum(ExecutionStatus), default=ExecutionStatus.PENDING, 
                   nullable=False, comment="실행 상태")
    error_message = Column(Text, nullable=True, comment="에러 메시지 (실패 시)")
    
    # 성능 메트릭
    execution_time_ms = Column(Integer, nullable=True, comment="실행 시간 (밀리초)")
    tokens_used = Column(Integer, nullable=True, comment="사용된 토큰 수")
    
    # 상세 실행 로그
    execution_steps = Column(JSON, nullable=True, comment="단계별 실행 로그")
    node_outputs = Column(JSON, nullable=True, comment="각 노드별 출력 결과")
    
    # 시스템 정보
    created_at = Column(DateTime, default=func.now(), comment="실행 시작 시간")
    completed_at = Column(DateTime, nullable=True, comment="실행 완료 시간")
    
    # 관계 정의
    flow = relationship("Flow", back_populates="execution_logs")
    executor = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<FlowExecutionLog(id={self.id}, flow_id={self.flow_id}, status='{self.status}')>"

class Secret(Base):
    """
    시크릿 관리 모델 (신규 생성)
    
    API 키, 토큰 등 민감한 정보를 안전하게 저장하고 관리합니다.
    값은 암호화되어 저장되며, 소유권 기반으로 접근이 제한됩니다.
    """
    __tablename__ = "secrets"
    
    # 기본 필드
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="시크릿 이름 (예: MY_API_KEY)")
    description = Column(Text, nullable=True, comment="시크릿 설명")
    
    # 암호화된 값
    encrypted_value = Column(Text, nullable=False, comment="암호화된 시크릿 값")
    
    # 소유권 정보
    owner_type = Column(Enum(OwnerType), nullable=False, comment="소유자 타입: GROUP 또는 USER")
    owner_id = Column(UUID(as_uuid=True), nullable=False, comment="소유자 ID")
    
    # 메타데이터
    category = Column(String(50), nullable=True, comment="시크릿 카테고리 (api_key, token, etc.)")
    tags = Column(JSON, nullable=True, comment="태그 목록")
    expires_at = Column(DateTime, nullable=True, comment="만료 일시")
    
    # 사용 통계
    last_used = Column(DateTime, nullable=True, comment="마지막 사용 시간")
    usage_count = Column(Integer, default=0, comment="사용 횟수")
    
    # 시스템 정보
    created_at = Column(DateTime, default=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 관계 정의
    creator = relationship("User", foreign_keys=[created_by])

    def set_value(self, value: str):
        """값을 암호화하여 저장"""
        self.encrypted_value = cipher_suite.encrypt(value.encode()).decode()
    
    def get_value(self) -> str:
        """암호화된 값을 복호화하여 반환"""
        return cipher_suite.decrypt(self.encrypted_value.encode()).decode()
    
    @property
    def value(self) -> str:
        """값 property (getter)"""
        return self.get_value()
    
    @value.setter
    def value(self, value: str):
        """값 property (setter)"""
        self.set_value(value)

    def __repr__(self):
        return f"<Secret(id={self.id}, name='{self.name}', owner_type='{self.owner_type}')>"

# 이전 FlowExecution 모델은 FlowExecutionLog로 대체됨
class FlowExecution(Base):
    """
    플로우 실행 기록 (레거시 - 호환성 유지)
    
    FlowExecutionLog로 대체됨. 기존 데이터 호환성을 위해 유지.
    """
    __tablename__ = "flow_executions"
    
    # 기본 필드
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid, index=True)
    flow_id = Column(Integer, ForeignKey('flows.id'), nullable=False)
    
    # 실행 정보
    input_data = Column(JSON, nullable=True, comment="입력 데이터")
    output_data = Column(JSON, nullable=True, comment="출력 데이터")
    execution_log = Column(JSON, nullable=True, comment="실행 로그")
    status = Column(String(20), default="pending", comment="실행 상태: pending, running, completed, failed")
    error_message = Column(Text, nullable=True, comment="에러 메시지")
    
    # 성능 메트릭
    duration_ms = Column(Integer, nullable=True, comment="실행 시간 (밀리초)")
    tokens_used = Column(Integer, nullable=True, comment="사용된 토큰 수")
    
    # 시스템 정보
    started_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    executed_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    # 관계 정의
    flow = relationship("Flow")
    executor = relationship("User", foreign_keys=[executed_by])

    def __repr__(self):
        return f"<FlowExecution(id={self.id}, flow_id={self.flow_id}, status='{self.status}')>" 