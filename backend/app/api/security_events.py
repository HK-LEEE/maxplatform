"""
Security Events API for MAX Platform

보안 이벤트 수집, 조회 및 관리를 위한 API 엔드포인트
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Query, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, text
from pydantic import BaseModel, Field, validator

from ..database import get_db
from ..utils.auth import get_current_user_optional, get_current_user_silent
from ..models.user import User
from ..models.security_event import (
    SecurityEvent, SecurityThreatRule, SecurityAlert, SecurityBlockedIP, SecurityStatistics,
    SecurityEventType, SecurityEventSeverity, SecurityAlertStatus
)
from ..services.security_monitor import security_monitor, SecurityContext

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/security", tags=["Security Events"])


# ============================================================================
# Request/Response Models
# ============================================================================

class SecurityEventRequest(BaseModel):
    """보안 이벤트 요청 모델"""
    eventId: str = Field(..., description="고유 이벤트 ID")
    timestamp: datetime = Field(..., description="이벤트 발생 시간")
    eventType: str = Field(..., description="이벤트 유형")
    severity: str = Field(..., description="심각도 (low/medium/high/critical)")
    details: Dict[str, Any] = Field(default_factory=dict, description="상세 정보")
    
    # 컨텍스트 정보 (클라이언트에서 자동 수집)
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="컨텍스트 정보")
    
    @validator('severity')
    def validate_severity(cls, v):
        valid_severities = ['low', 'medium', 'high', 'critical']
        if v not in valid_severities:
            raise ValueError(f'Severity must be one of: {valid_severities}')
        return v


class SecurityEventBatchRequest(BaseModel):
    """배치 보안 이벤트 요청 모델"""
    events: List[SecurityEventRequest] = Field(..., description="보안 이벤트 목록")
    
    @validator('events')
    def validate_events_count(cls, v):
        if len(v) > 100:  # 한 번에 최대 100개 이벤트
            raise ValueError('Maximum 100 events per batch')
        return v


class SecurityEventResponse(BaseModel):
    """보안 이벤트 응답 모델"""
    id: str
    event_id: str
    timestamp: datetime
    event_type: str
    severity: str
    user_id: Optional[str]
    ip_address: Optional[str]
    details: Dict[str, Any]
    processed: bool
    created_at: datetime


class SecurityEventListResponse(BaseModel):
    """보안 이벤트 목록 응답 모델"""
    events: List[SecurityEventResponse]
    total: int
    page: int
    size: int
    has_next: bool


class SecurityStatisticsResponse(BaseModel):
    """보안 통계 응답 모델"""
    period_hours: int
    total_events: int
    events_by_severity: Dict[str, int]
    events_by_type: Dict[str, int]
    unique_ips: int
    blocked_ips: int
    active_alerts: int
    threat_rules_active: int


class SecurityAlertResponse(BaseModel):
    """보안 알림 응답 모델"""
    id: str
    alert_type: str
    title: str
    message: str
    severity: str
    status: str
    source_ip: Optional[str]
    created_at: datetime
    acknowledged: bool


# ============================================================================
# Utility Functions
# ============================================================================

def extract_client_info(request: Request) -> Dict[str, Any]:
    """요청에서 클라이언트 정보 추출"""
    return {
        'ip_address': request.client.host if request.client else None,
        'user_agent': request.headers.get('User-Agent', ''),
        'url': str(request.url),
        'referrer': request.headers.get('Referer', ''),
        'browser_fingerprint': request.headers.get('X-Browser-Fingerprint', ''),
        'session_id': request.headers.get('X-Session-ID', '')
    }


async def create_security_event(
    event_data: SecurityEventRequest,
    client_info: Dict[str, Any],
    user: Optional[User],
    db: Session
) -> SecurityEvent:
    """보안 이벤트 생성"""
    try:
        # 컨텍스트 정보 병합
        context = {**client_info, **event_data.context}
        
        security_event = SecurityEvent(
            event_id=event_data.eventId,
            timestamp=event_data.timestamp,
            event_type=event_data.eventType,
            severity=event_data.severity,
            user_id=user.id if user else None,
            session_id=context.get('session_id'),
            username=user.username if user else context.get('username'),
            ip_address=context.get('ip_address'),
            user_agent=context.get('user_agent'),
            url=context.get('url'),
            referrer=context.get('referrer'),
            browser_fingerprint=context.get('browser_fingerprint'),
            details=event_data.details
        )
        
        db.add(security_event)
        db.flush()  # ID 생성을 위해 flush
        
        return security_event
        
    except Exception as e:
        logger.error(f"Failed to create security event: {e}")
        raise HTTPException(status_code=500, detail="Failed to create security event")


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/events")
async def log_security_events(
    batch_request: SecurityEventBatchRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_silent)
):
    """
    보안 이벤트 배치 로깅
    
    클라이언트에서 수집한 보안 이벤트들을 배치로 서버에 전송
    """
    try:
        client_info = extract_client_info(request)
        processed_events = []
        threat_detections = []
        
        # 요청 제한 확인
        if security_monitor.is_request_throttled(client_info.get('ip_address', '')):
            raise HTTPException(
                status_code=429, 
                detail="Too many requests. Please try again later."
            )
        
        # IP 차단 확인
        if security_monitor._is_ip_blocked(client_info.get('ip_address', '')):
            raise HTTPException(
                status_code=403,
                detail="Access denied. IP address is blocked."
            )
        
        # 각 이벤트 처리
        for event_data in batch_request.events:
            try:
                # 보안 이벤트 생성
                security_event = await create_security_event(
                    event_data, client_info, current_user, db
                )
                
                # 실시간 위협 탐지
                detection_results = await security_monitor.process_security_event(
                    security_event, db
                )
                
                threat_detections.extend(detection_results)
                processed_events.append(security_event)
                
            except Exception as e:
                logger.error(f"Failed to process event {event_data.eventId}: {e}")
                # 개별 이벤트 실패는 전체 배치를 실패시키지 않음
                continue
        
        # 데이터베이스 커밋
        db.commit()
        
        # 응답 생성
        response_data = {
            'status': 'success',
            'processed_count': len(processed_events),
            'total_count': len(batch_request.events),
            'threats_detected': len([t for t in threat_detections if t.threat_detected]),
            'event_ids': [event.event_id for event in processed_events]
        }
        
        # 위협이 탐지된 경우 추가 정보 포함
        if threat_detections:
            high_confidence_threats = [
                t for t in threat_detections 
                if t.threat_detected and t.confidence > 0.7
            ]
            if high_confidence_threats:
                response_data['high_confidence_threats'] = [
                    {
                        'rule_name': t.rule_name,
                        'confidence': t.confidence,
                        'recommended_action': t.recommended_action
                    }
                    for t in high_confidence_threats
                ]
        
        logger.info(
            f"Processed {len(processed_events)} security events from "
            f"{client_info.get('ip_address', 'unknown')} "
            f"(user: {current_user.username if current_user else 'anonymous'})"
        )
        
        return JSONResponse(content=response_data, status_code=200)
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to process security events: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process security events"
        )


@router.get("/events", response_model=SecurityEventListResponse)
async def get_security_events(
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    event_type: Optional[str] = Query(None, description="이벤트 타입 필터"),
    severity: Optional[str] = Query(None, description="심각도 필터"),
    user_id: Optional[str] = Query(None, description="사용자 ID 필터"),
    ip_address: Optional[str] = Query(None, description="IP 주소 필터"),
    hours: int = Query(24, ge=1, le=168, description="조회 기간 (시간)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)  # 관리자만 접근 가능하도록 수정 가능
):
    """
    보안 이벤트 목록 조회
    """
    try:
        # 기본 쿼리
        query = db.query(SecurityEvent)
        
        # 시간 필터
        since = datetime.utcnow() - timedelta(hours=hours)
        query = query.filter(SecurityEvent.timestamp >= since)
        
        # 선택적 필터들
        if event_type:
            query = query.filter(SecurityEvent.event_type == event_type)
        if severity:
            query = query.filter(SecurityEvent.severity == severity)
        if user_id:
            query = query.filter(SecurityEvent.user_id == user_id)
        if ip_address:
            query = query.filter(SecurityEvent.ip_address == ip_address)
        
        # 총 개수 조회
        total = query.count()
        
        # 페이징 및 정렬
        events = query.order_by(desc(SecurityEvent.timestamp))\
                     .offset((page - 1) * size)\
                     .limit(size)\
                     .all()
        
        # 응답 변환
        event_responses = [
            SecurityEventResponse(
                id=str(event.id),
                event_id=event.event_id,
                timestamp=event.timestamp,
                event_type=event.event_type,
                severity=event.severity,
                user_id=str(event.user_id) if event.user_id else None,
                ip_address=str(event.ip_address) if event.ip_address else None,
                details=event.details or {},
                processed=event.processed,
                created_at=event.created_at
            )
            for event in events
        ]
        
        return SecurityEventListResponse(
            events=event_responses,
            total=total,
            page=page,
            size=size,
            has_next=total > page * size
        )
        
    except Exception as e:
        logger.error(f"Failed to get security events: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve security events")


@router.get("/statistics", response_model=SecurityStatisticsResponse)
async def get_security_statistics(
    hours: int = Query(24, ge=1, le=168, description="통계 기간 (시간)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    보안 통계 조회
    """
    try:
        stats = await security_monitor.get_security_statistics(db, hours)
        
        # 추가 통계 계산
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # 총 이벤트 수
        total_events = db.query(func.count(SecurityEvent.id))\
                        .filter(SecurityEvent.timestamp >= since)\
                        .scalar() or 0
        
        # 심각도별 이벤트 수
        severity_stats = db.query(
            SecurityEvent.severity,
            func.count().label('count')
        ).filter(
            SecurityEvent.timestamp >= since
        ).group_by(SecurityEvent.severity).all()
        
        events_by_severity = {stat.severity: stat.count for stat in severity_stats}
        
        # 타입별 이벤트 수
        type_stats = db.query(
            SecurityEvent.event_type,
            func.count().label('count')
        ).filter(
            SecurityEvent.timestamp >= since
        ).group_by(SecurityEvent.event_type).all()
        
        events_by_type = {stat.event_type: stat.count for stat in type_stats}
        
        # 활성 알림 수
        active_alerts = db.query(func.count(SecurityAlert.id))\
                         .filter(SecurityAlert.status.in_(['new', 'investigating']))\
                         .scalar() or 0
        
        return SecurityStatisticsResponse(
            period_hours=hours,
            total_events=total_events,
            events_by_severity=events_by_severity,
            events_by_type=events_by_type,
            unique_ips=stats.get('unique_ips', 0),
            blocked_ips=stats.get('blocked_ips', 0),
            active_alerts=active_alerts,
            threat_rules_active=stats.get('threat_rules_active', 0)
        )
        
    except Exception as e:
        logger.error(f"Failed to get security statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve security statistics")


@router.get("/alerts", response_model=List[SecurityAlertResponse])
async def get_security_alerts(
    status: Optional[str] = Query(None, description="알림 상태 필터"),
    severity: Optional[str] = Query(None, description="심각도 필터"),
    limit: int = Query(50, ge=1, le=200, description="최대 개수"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    보안 알림 목록 조회
    """
    try:
        query = db.query(SecurityAlert)
        
        if status:
            query = query.filter(SecurityAlert.status == status)
        if severity:
            query = query.filter(SecurityAlert.severity == severity)
        
        alerts = query.order_by(desc(SecurityAlert.created_at))\
                      .limit(limit)\
                      .all()
        
        return [
            SecurityAlertResponse(
                id=str(alert.id),
                alert_type=alert.alert_type,
                title=alert.title,
                message=alert.message,
                severity=alert.severity,
                status=alert.status,
                source_ip=str(alert.source_ip) if alert.source_ip else None,
                created_at=alert.created_at,
                acknowledged=alert.acknowledged
            )
            for alert in alerts
        ]
        
    except Exception as e:
        logger.error(f"Failed to get security alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve security alerts")


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    보안 알림 확인 처리
    """
    try:
        alert = db.query(SecurityAlert).filter(SecurityAlert.id == alert_id).first()
        
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        alert.acknowledged = True
        alert.acknowledged_by = current_user.id if current_user else None
        alert.acknowledged_at = datetime.utcnow()
        
        db.commit()
        
        return {"status": "success", "message": "Alert acknowledged"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to acknowledge alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to acknowledge alert")


@router.get("/blocked-ips")
async def get_blocked_ips(
    active_only: bool = Query(True, description="활성 차단만 조회"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    차단된 IP 목록 조회
    """
    try:
        query = db.query(SecurityBlockedIP)
        
        if active_only:
            query = query.filter(
                and_(
                    SecurityBlockedIP.is_active == True,
                    or_(
                        SecurityBlockedIP.expires_at.is_(None),
                        SecurityBlockedIP.expires_at > datetime.utcnow()
                    )
                )
            )
        
        blocked_ips = query.order_by(desc(SecurityBlockedIP.blocked_at)).all()
        
        return [
            {
                'id': str(ip.id),
                'ip_address': str(ip.ip_address),
                'block_reason': ip.block_reason,
                'block_type': ip.block_type,
                'severity': ip.severity,
                'blocked_at': ip.blocked_at,
                'expires_at': ip.expires_at,
                'is_active': ip.is_active,
                'attempt_count': ip.attempt_count
            }
            for ip in blocked_ips
        ]
        
    except Exception as e:
        logger.error(f"Failed to get blocked IPs: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve blocked IPs")


@router.delete("/blocked-ips/{ip_id}")
async def unblock_ip(
    ip_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    IP 차단 해제
    """
    try:
        blocked_ip = db.query(SecurityBlockedIP).filter(SecurityBlockedIP.id == ip_id).first()
        
        if not blocked_ip:
            raise HTTPException(status_code=404, detail="Blocked IP not found")
        
        blocked_ip.is_active = False
        blocked_ip.updated_at = datetime.utcnow()
        
        # 메모리 캐시에서도 제거
        security_monitor.blocked_ips.discard(str(blocked_ip.ip_address))
        
        db.commit()
        
        return {"status": "success", "message": f"IP {blocked_ip.ip_address} unblocked"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to unblock IP: {e}")
        raise HTTPException(status_code=500, detail="Failed to unblock IP")


@router.post("/cleanup")
async def cleanup_security_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    보안 데이터 정리 (만료된 차단, 오래된 이벤트 등)
    """
    try:
        # 만료된 IP 차단 해제
        unblocked_count = await security_monitor.cleanup_expired_blocks(db)
        
        # 오래된 저심각도 이벤트 정리 (90일 이상)
        old_events_deleted = db.execute(
            text("""
                DELETE FROM security_events 
                WHERE created_at < NOW() - INTERVAL '90 days' 
                AND severity = 'low'
            """)
        ).rowcount
        
        # 해결된 오래된 알림 정리 (30일 이상)
        old_alerts_deleted = db.execute(
            text("""
                DELETE FROM security_alerts 
                WHERE status = 'resolved' 
                AND resolved_at < NOW() - INTERVAL '30 days'
            """)
        ).rowcount
        
        db.commit()
        
        return {
            "status": "success",
            "unblocked_ips": unblocked_count,
            "deleted_events": old_events_deleted,
            "deleted_alerts": old_alerts_deleted
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to cleanup security data: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup security data")


# ============================================================================
# Health Check
# ============================================================================

@router.get("/health")
async def security_health_check(
    db: Session = Depends(get_db)
):
    """
    보안 서비스 상태 확인
    """
    try:
        # 데이터베이스 연결 확인
        db.execute(text("SELECT 1")).fetchone()
        
        # 최근 이벤트 확인 (지난 1시간)
        recent_events = db.query(func.count(SecurityEvent.id))\
                         .filter(SecurityEvent.timestamp >= datetime.utcnow() - timedelta(hours=1))\
                         .scalar()
        
        # 활성 위협 규칙 확인
        active_rules = db.query(func.count(SecurityThreatRule.id))\
                        .filter(SecurityThreatRule.is_active == True)\
                        .scalar()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow(),
            "recent_events_1h": recent_events,
            "active_threat_rules": active_rules,
            "blocked_ips_count": len(security_monitor.blocked_ips),
            "cache_size": sum(len(cache) for cache in security_monitor.recent_events.values())
        }
        
    except Exception as e:
        logger.error(f"Security health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow(),
            "error": str(e)
        }