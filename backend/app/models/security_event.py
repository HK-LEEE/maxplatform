"""
Security Event Models for MAX Platform

보안 이벤트 로깅 및 모니터링을 위한 데이터 모델들
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    Column, String, DateTime, Boolean, Integer, Text, JSON,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from ..database import Base


class SecurityEvent(Base):
    """보안 이벤트 로그 모델"""
    __tablename__ = 'security_events'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 기본 이벤트 정보
    event_id = Column(String(100), unique=True, nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    
    # 사용자 및 세션 정보
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    session_id = Column(String(100), index=True)
    username = Column(String(100))  # 로그인 실패 시에도 기록
    
    # 네트워크 및 클라이언트 정보
    ip_address = Column(INET, index=True)
    user_agent = Column(Text)
    url = Column(Text)
    referrer = Column(Text)
    browser_fingerprint = Column(String(255))
    
    # 상세 정보 (JSON)
    details = Column(JSONB)
    
    # 처리 상태
    processed = Column(Boolean, default=False, index=True)
    processed_at = Column(DateTime(timezone=True))
    
    # 메타데이터
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # 관계
    user = relationship("User", back_populates="security_events", lazy='select')
    
    # 인덱스 정의
    __table_args__ = (
        Index('idx_security_events_type_time', 'event_type', 'timestamp'),
        Index('idx_security_events_ip_time', 'ip_address', 'timestamp'),
        Index('idx_security_events_user_time', 'user_id', 'timestamp'),
        Index('idx_security_events_details_gin', 'details', postgresql_using='gin'),
    )

    def __repr__(self):
        return f"<SecurityEvent(id={self.id}, type={self.event_type}, severity={self.severity})>"

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'id': str(self.id),
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'event_type': self.event_type,
            'severity': self.severity,
            'user_id': str(self.user_id) if self.user_id else None,
            'session_id': self.session_id,
            'username': self.username,
            'ip_address': str(self.ip_address) if self.ip_address else None,
            'user_agent': self.user_agent,
            'url': self.url,
            'referrer': self.referrer,
            'browser_fingerprint': self.browser_fingerprint,
            'details': self.details,
            'processed': self.processed,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class SecurityThreatRule(Base):
    """보안 위협 탐지 규칙 모델"""
    __tablename__ = 'security_threat_rules'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 규칙 정보
    rule_name = Column(String(100), unique=True, nullable=False)
    rule_type = Column(String(50), nullable=False)
    description = Column(Text)
    
    # 규칙 조건
    conditions = Column(JSONB, nullable=False)
    threshold_count = Column(Integer, default=5)
    threshold_window = Column(Integer, default=300)  # 초 단위
    
    # 대응 액션
    action_type = Column(String(50), nullable=False)
    action_config = Column(JSONB)
    
    # 상태
    is_active = Column(Boolean, default=True)
    severity = Column(String(20), default='medium')
    
    # 메타데이터
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    
    # 관계
    creator = relationship("User", lazy='select')
    alerts = relationship("SecurityAlert", back_populates="rule", lazy='dynamic')

    def __repr__(self):
        return f"<SecurityThreatRule(name={self.rule_name}, type={self.rule_type})>"


class SecurityAlert(Base):
    """보안 알림 모델"""
    __tablename__ = 'security_alerts'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 알림 정보
    alert_type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False, index=True)
    
    # 연관 정보
    rule_id = Column(UUID(as_uuid=True), ForeignKey('security_threat_rules.id', ondelete='SET NULL'))
    event_ids = Column(JSONB)  # 관련 이벤트 ID들
    affected_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    source_ip = Column(INET, index=True)
    
    # 상태
    status = Column(String(20), default='new', index=True)  # new, investigating, resolved, false_positive
    acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    acknowledged_at = Column(DateTime(timezone=True))
    
    # 해결 정보
    resolution = Column(Text)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    resolved_at = Column(DateTime(timezone=True))
    
    # 메타데이터
    created_at = Column(DateTime(timezone=True), default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # 관계
    rule = relationship("SecurityThreatRule", back_populates="alerts", lazy='select')
    affected_user = relationship("User", foreign_keys=[affected_user_id], lazy='select')
    acknowledger = relationship("User", foreign_keys=[acknowledged_by], lazy='select')
    resolver = relationship("User", foreign_keys=[resolved_by], lazy='select')

    def __repr__(self):
        return f"<SecurityAlert(id={self.id}, type={self.alert_type}, severity={self.severity})>"


class SecurityBlockedIP(Base):
    """IP 차단 목록 모델"""
    __tablename__ = 'security_blocked_ips'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # IP 정보
    ip_address = Column(INET, unique=True, nullable=False, index=True)
    ip_range = Column(String(50))  # CIDR 표기법
    
    # 차단 정보
    block_reason = Column(String(100), nullable=False)
    block_type = Column(String(20), nullable=False)  # temporary, permanent
    severity = Column(String(20), nullable=False)
    
    # 관련 정보
    related_event_ids = Column(JSONB)
    related_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    
    # 시간 정보
    blocked_at = Column(DateTime(timezone=True), default=func.now())
    expires_at = Column(DateTime(timezone=True), index=True)  # 임시 차단 만료 시간
    last_attempt_at = Column(DateTime(timezone=True))
    attempt_count = Column(Integer, default=0)
    
    # 상태
    is_active = Column(Boolean, default=True, index=True)
    
    # 메타데이터
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # 관계
    related_user = relationship("User", foreign_keys=[related_user_id], lazy='select')
    creator = relationship("User", foreign_keys=[created_by], lazy='select')
    
    # 인덱스
    __table_args__ = (
        Index('idx_security_blocked_ips_active_expires', 'is_active', 'expires_at'),
    )

    def __repr__(self):
        return f"<SecurityBlockedIP(ip={self.ip_address}, active={self.is_active})>"

    def is_expired(self) -> bool:
        """차단이 만료되었는지 확인"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at.replace(tzinfo=None)


class SecurityStatistics(Base):
    """보안 통계 집계 모델"""
    __tablename__ = 'security_statistics'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 집계 정보
    date_hour = Column(DateTime(timezone=True), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    
    # 통계 데이터
    event_count = Column(Integer, default=0)
    unique_users = Column(Integer, default=0)
    unique_ips = Column(Integer, default=0)
    
    # 메타데이터
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # 복합 유니크 제약
    __table_args__ = (
        UniqueConstraint('date_hour', 'event_type', 'severity'),
        Index('idx_security_statistics_type_date', 'event_type', 'date_hour'),
    )

    def __repr__(self):
        return f"<SecurityStatistics(type={self.event_type}, hour={self.date_hour})>"


# User 모델 관계는 user.py에서 직접 정의됨


# 보안 이벤트 타입 상수
class SecurityEventType:
    """보안 이벤트 타입 상수"""
    
    # 인증 관련
    AUTH_LOGIN_SUCCESS = 'auth_login_success'
    AUTH_LOGIN_FAILED = 'auth_login_failed'
    AUTH_LOGOUT = 'auth_logout'
    AUTH_TOKEN_REFRESH = 'auth_token_refresh'
    AUTH_TOKEN_EXPIRED = 'auth_token_expired'
    AUTH_TOKEN_INVALID = 'auth_token_invalid'
    AUTH_ACCESS_DENIED = 'auth_access_denied'
    AUTH_ACCOUNT_LOCKED = 'auth_account_locked'
    
    # 토큰 관리
    TOKEN_CREATED = 'token_created'
    TOKEN_USED = 'token_used'
    TOKEN_ROTATED = 'token_rotated'
    TOKEN_REVOKED = 'token_revoked'
    TOKEN_THEFT_DETECTED = 'token_theft_detected'
    
    # 브루트 포스
    BRUTE_FORCE_DETECTED = 'brute_force_detected'
    RATE_LIMIT_EXCEEDED = 'rate_limit_exceeded'
    
    # API 보안
    API_CALL = 'api_call'
    API_ERROR = 'api_error'
    API_ABUSE_DETECTED = 'api_abuse_detected'
    
    # 데이터 보안
    DATA_ACCESS = 'data_access'
    DATA_MODIFICATION = 'data_modification'
    DATA_EXPORT = 'data_export'
    
    # 시스템 보안
    SYSTEM_CONFIG_CHANGE = 'system_config_change'
    ADMIN_ACTION = 'admin_action'
    PRIVILEGE_ESCALATION = 'privilege_escalation'


class SecurityEventSeverity:
    """보안 이벤트 심각도 상수"""
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


class SecurityAlertStatus:
    """보안 알림 상태 상수"""
    NEW = 'new'
    INVESTIGATING = 'investigating'
    RESOLVED = 'resolved'
    FALSE_POSITIVE = 'false_positive'


class SecurityBlockType:
    """보안 차단 유형 상수"""
    TEMPORARY = 'temporary'
    PERMANENT = 'permanent'


class SecurityActionType:
    """보안 대응 액션 유형 상수"""
    ALERT = 'alert'
    BLOCK = 'block'
    LOCKOUT = 'lockout'
    THROTTLE = 'throttle'
    QUARANTINE = 'quarantine'