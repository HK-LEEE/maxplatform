"""
Security Monitoring Service for MAX Platform

실시간 보안 위협 탐지 및 대응 서비스
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
from collections import defaultdict, deque
from dataclasses import dataclass
import ipaddress

from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_, func
from ..database import get_db
from ..models.security_event import (
    SecurityEvent, SecurityThreatRule, SecurityAlert, SecurityBlockedIP,
    SecurityEventType, SecurityEventSeverity, SecurityAlertStatus,
    SecurityBlockType, SecurityActionType
)
from ..models.user import User

logger = logging.getLogger(__name__)


@dataclass
class ThreatDetectionResult:
    """위협 탐지 결과"""
    threat_detected: bool
    rule_id: str
    rule_name: str
    confidence: float
    event_count: int
    related_events: List[str]
    recommended_action: str
    details: Dict[str, Any]


@dataclass
class SecurityContext:
    """보안 컨텍스트 정보"""
    ip_address: str
    user_agent: str
    browser_fingerprint: str
    session_id: str
    user_id: Optional[str] = None
    url: str = ""
    referrer: str = ""


class SecurityMonitorService:
    """보안 모니터링 서비스"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 실시간 모니터링을 위한 메모리 캐시
        self.recent_events: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.blocked_ips: Set[str] = set()
        self.suspicious_users: Dict[str, int] = defaultdict(int)
        
        # 위협 탐지 규칙 캐시
        self.threat_rules: List[SecurityThreatRule] = []
        self.last_rules_update = datetime.utcnow()
        
    async def process_security_event(self, event: SecurityEvent, db: Session) -> List[ThreatDetectionResult]:
        """보안 이벤트 처리 및 위협 탐지"""
        try:
            # 이벤트를 메모리 캐시에 추가
            self._add_to_cache(event)
            
            # IP 차단 확인
            if self._is_ip_blocked(event.ip_address):
                self.logger.warning(f"Blocked IP {event.ip_address} attempted access")
                return []
            
            # 위협 탐지 규칙 업데이트 (필요 시)
            await self._update_threat_rules(db)
            
            # 실시간 위협 탐지
            detection_results = []
            for rule in self.threat_rules:
                if rule.is_active:
                    result = await self._detect_threat(event, rule, db)
                    if result.threat_detected:
                        detection_results.append(result)
            
            # 탐지된 위협에 대한 대응
            for result in detection_results:
                await self._handle_threat_detection(result, event, db)
            
            return detection_results
            
        except Exception as e:
            self.logger.error(f"Error processing security event: {e}")
            return []
    
    def _add_to_cache(self, event: SecurityEvent):
        """이벤트를 메모리 캐시에 추가"""
        cache_key = f"{event.event_type}:{event.ip_address}"
        self.recent_events[cache_key].append({
            'timestamp': event.timestamp,
            'event_id': event.event_id,
            'user_id': event.user_id,
            'details': event.details
        })
    
    def _is_ip_blocked(self, ip_address: str) -> bool:
        """IP가 차단되어 있는지 확인"""
        return ip_address in self.blocked_ips
    
    async def _update_threat_rules(self, db: Session):
        """위협 탐지 규칙 업데이트"""
        # 5분마다 업데이트
        if datetime.utcnow() - self.last_rules_update < timedelta(minutes=5):
            return
        
        try:
            rules = db.query(SecurityThreatRule).filter(
                SecurityThreatRule.is_active == True
            ).all()
            self.threat_rules = rules
            self.last_rules_update = datetime.utcnow()
            
            # 차단된 IP 목록도 업데이트
            blocked_ips = db.query(SecurityBlockedIP).filter(
                and_(
                    SecurityBlockedIP.is_active == True,
                    or_(
                        SecurityBlockedIP.expires_at.is_(None),
                        SecurityBlockedIP.expires_at > datetime.utcnow()
                    )
                )
            ).all()
            
            self.blocked_ips = {str(ip.ip_address) for ip in blocked_ips}
            
        except Exception as e:
            self.logger.error(f"Failed to update threat rules: {e}")
    
    async def _detect_threat(self, event: SecurityEvent, rule: SecurityThreatRule, db: Session) -> ThreatDetectionResult:
        """특정 규칙을 사용한 위협 탐지"""
        try:
            conditions = rule.conditions
            event_types = conditions.get('event_types', [])
            
            # 이벤트 타입 매칭
            if event.event_type not in event_types:
                return ThreatDetectionResult(
                    threat_detected=False,
                    rule_id=str(rule.id),
                    rule_name=rule.rule_name,
                    confidence=0.0,
                    event_count=0,
                    related_events=[],
                    recommended_action='none',
                    details={}
                )
            
            # 시간 창 내 관련 이벤트 조회
            time_window = datetime.utcnow() - timedelta(seconds=rule.threshold_window)
            
            # 동일 IP 조건
            if conditions.get('same_ip', False):
                related_events = await self._get_events_by_ip(
                    event.ip_address, event_types, time_window, db
                )
            # 동일 사용자 조건  
            elif conditions.get('same_user', False) and event.user_id:
                related_events = await self._get_events_by_user(
                    event.user_id, event_types, time_window, db
                )
            # 기타 조건들
            else:
                related_events = await self._get_events_by_type(
                    event_types, time_window, db
                )
            
            event_count = len(related_events)
            confidence = min(event_count / rule.threshold_count, 1.0)
            
            # 임계값 확인
            threat_detected = event_count >= rule.threshold_count
            
            # 특별 조건 검사
            if threat_detected:
                threat_detected = await self._check_special_conditions(
                    event, related_events, conditions, db
                )
            
            return ThreatDetectionResult(
                threat_detected=threat_detected,
                rule_id=str(rule.id),
                rule_name=rule.rule_name,
                confidence=confidence,
                event_count=event_count,
                related_events=[e.event_id for e in related_events],
                recommended_action=rule.action_type,
                details={
                    'threshold_count': rule.threshold_count,
                    'threshold_window': rule.threshold_window,
                    'conditions': conditions
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error detecting threat with rule {rule.rule_name}: {e}")
            return ThreatDetectionResult(
                threat_detected=False,
                rule_id=str(rule.id),
                rule_name=rule.rule_name,
                confidence=0.0,
                event_count=0,
                related_events=[],
                recommended_action='none',
                details={'error': str(e)}
            )
    
    async def _get_events_by_ip(self, ip_address: str, event_types: List[str], 
                               since: datetime, db: Session) -> List[SecurityEvent]:
        """IP별 이벤트 조회"""
        return db.query(SecurityEvent).filter(
            and_(
                SecurityEvent.ip_address == ip_address,
                SecurityEvent.event_type.in_(event_types),
                SecurityEvent.timestamp >= since
            )
        ).order_by(SecurityEvent.timestamp.desc()).all()
    
    async def _get_events_by_user(self, user_id: str, event_types: List[str], 
                                 since: datetime, db: Session) -> List[SecurityEvent]:
        """사용자별 이벤트 조회"""
        return db.query(SecurityEvent).filter(
            and_(
                SecurityEvent.user_id == user_id,
                SecurityEvent.event_type.in_(event_types),
                SecurityEvent.timestamp >= since
            )
        ).order_by(SecurityEvent.timestamp.desc()).all()
    
    async def _get_events_by_type(self, event_types: List[str], since: datetime, 
                                 db: Session) -> List[SecurityEvent]:
        """이벤트 타입별 조회"""
        return db.query(SecurityEvent).filter(
            and_(
                SecurityEvent.event_type.in_(event_types),
                SecurityEvent.timestamp >= since
            )
        ).order_by(SecurityEvent.timestamp.desc()).all()
    
    async def _check_special_conditions(self, event: SecurityEvent, 
                                       related_events: List[SecurityEvent],
                                       conditions: Dict, db: Session) -> bool:
        """특별 조건 검사"""
        try:
            # 다른 IP에서의 접근 검사
            if conditions.get('different_ips', False):
                ips = {str(e.ip_address) for e in related_events if e.ip_address}
                return len(ips) > 1
            
            # 위치 이상 검사
            if conditions.get('location_anomaly', False):
                return await self._check_location_anomaly(event, related_events)
            
            # 고빈도 접근 검사
            if conditions.get('high_frequency', False):
                return await self._check_high_frequency(related_events, conditions)
            
            # 관리자 리소스 접근 검사
            if conditions.get('admin_resources', False):
                return await self._check_admin_resource_access(event, related_events)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking special conditions: {e}")
            return False
    
    async def _check_location_anomaly(self, event: SecurityEvent, 
                                     related_events: List[SecurityEvent]) -> bool:
        """위치 이상 탐지 (간단한 구현)"""
        # 실제 구현에서는 GeoIP 데이터베이스를 사용
        # 여기서는 IP 대역이 크게 다른지만 확인
        try:
            current_ip = ipaddress.ip_address(event.ip_address)
            for related_event in related_events[-5:]:  # 최근 5개만 확인
                if related_event.ip_address:
                    related_ip = ipaddress.ip_address(related_event.ip_address)
                    # 다른 /16 네트워크인지 확인 (매우 단순한 방법)
                    if (int(current_ip) >> 16) != (int(related_ip) >> 16):
                        return True
            return False
        except:
            return False
    
    async def _check_high_frequency(self, related_events: List[SecurityEvent], 
                                   conditions: Dict) -> bool:
        """고빈도 접근 검사"""
        if len(related_events) < 2:
            return False
        
        # 이벤트 간 시간 간격 계산
        timestamps = [e.timestamp for e in related_events]
        timestamps.sort()
        
        intervals = []
        for i in range(1, len(timestamps)):
            interval = (timestamps[i] - timestamps[i-1]).total_seconds()
            intervals.append(interval)
        
        # 평균 간격이 너무 짧으면 고빈도로 판단
        avg_interval = sum(intervals) / len(intervals)
        return avg_interval < 1.0  # 1초 미만 간격
    
    async def _check_admin_resource_access(self, event: SecurityEvent,
                                          related_events: List[SecurityEvent]) -> bool:
        """관리자 리소스 접근 검사"""
        admin_paths = ['/admin', '/api/admin', '/dashboard/admin', '/management']
        
        # 현재 이벤트의 URL 확인
        if event.url:
            for admin_path in admin_paths:
                if admin_path in event.url.lower():
                    return True
        
        # 관련 이벤트들의 URL 확인
        for related_event in related_events:
            if related_event.url:
                for admin_path in admin_paths:
                    if admin_path in related_event.url.lower():
                        return True
        
        return False
    
    async def _handle_threat_detection(self, result: ThreatDetectionResult, 
                                      event: SecurityEvent, db: Session):
        """탐지된 위협에 대한 대응"""
        try:
            # 알림 생성
            await self._create_security_alert(result, event, db)
            
            # 대응 액션 실행
            if result.recommended_action == SecurityActionType.BLOCK:
                await self._block_ip(event.ip_address, result, db)
            elif result.recommended_action == SecurityActionType.LOCKOUT:
                await self._lockout_user(event.user_id, result, db)
            elif result.recommended_action == SecurityActionType.THROTTLE:
                await self._throttle_requests(event.ip_address, result)
            
            self.logger.warning(
                f"Security threat detected: {result.rule_name} "
                f"(confidence: {result.confidence:.2f}, events: {result.event_count})"
            )
            
        except Exception as e:
            self.logger.error(f"Error handling threat detection: {e}")
    
    async def _create_security_alert(self, result: ThreatDetectionResult, 
                                    event: SecurityEvent, db: Session):
        """보안 알림 생성"""
        try:
            alert = SecurityAlert(
                alert_type=result.rule_name.lower().replace(' ', '_'),
                title=f"Security Threat Detected: {result.rule_name}",
                message=f"Threat detected with confidence {result.confidence:.2f}. "
                       f"{result.event_count} events in the detection window.",
                severity=SecurityEventSeverity.HIGH if result.confidence > 0.8 else SecurityEventSeverity.MEDIUM,
                rule_id=result.rule_id,
                event_ids=result.related_events,
                affected_user_id=event.user_id,
                source_ip=event.ip_address,
                status=SecurityAlertStatus.NEW
            )
            
            db.add(alert)
            db.commit()
            
            self.logger.info(f"Security alert created: {alert.id}")
            
        except Exception as e:
            self.logger.error(f"Failed to create security alert: {e}")
            db.rollback()
    
    async def _block_ip(self, ip_address: str, result: ThreatDetectionResult, db: Session):
        """IP 차단"""
        try:
            # 기존 차단 확인
            existing_block = db.query(SecurityBlockedIP).filter(
                SecurityBlockedIP.ip_address == ip_address,
                SecurityBlockedIP.is_active == True
            ).first()
            
            if existing_block:
                # 차단 횟수 증가
                existing_block.attempt_count += 1
                existing_block.last_attempt_at = datetime.utcnow()
            else:
                # 새 차단 생성
                block_duration = 3600  # 1시간 기본 차단
                
                blocked_ip = SecurityBlockedIP(
                    ip_address=ip_address,
                    block_reason=result.rule_name,
                    block_type=SecurityBlockType.TEMPORARY,
                    severity=SecurityEventSeverity.HIGH,
                    related_event_ids=result.related_events,
                    expires_at=datetime.utcnow() + timedelta(seconds=block_duration),
                    attempt_count=1,
                    last_attempt_at=datetime.utcnow()
                )
                
                db.add(blocked_ip)
                self.blocked_ips.add(ip_address)
            
            db.commit()
            self.logger.warning(f"IP {ip_address} blocked due to {result.rule_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to block IP {ip_address}: {e}")
            db.rollback()
    
    async def _lockout_user(self, user_id: str, result: ThreatDetectionResult, db: Session):
        """사용자 계정 잠금"""
        if not user_id:
            return
        
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.is_active = False
                user.locked_at = datetime.utcnow()
                user.lock_reason = result.rule_name
                
                db.commit()
                self.logger.warning(f"User {user_id} locked due to {result.rule_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to lock user {user_id}: {e}")
            db.rollback()
    
    async def _throttle_requests(self, ip_address: str, result: ThreatDetectionResult):
        """요청 제한 (메모리 기반 간단 구현)"""
        # 실제 구현에서는 Redis 등을 사용
        self.suspicious_users[ip_address] = int(datetime.utcnow().timestamp()) + 300  # 5분간 제한
        self.logger.info(f"Throttling requests from {ip_address} for 5 minutes")
    
    def is_request_throttled(self, ip_address: str) -> bool:
        """요청이 제한되어 있는지 확인"""
        if ip_address in self.suspicious_users:
            if int(datetime.utcnow().timestamp()) < self.suspicious_users[ip_address]:
                return True
            else:
                del self.suspicious_users[ip_address]
        return False
    
    async def get_security_statistics(self, db: Session, hours: int = 24) -> Dict[str, Any]:
        """보안 통계 조회"""
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            
            # 이벤트 수 통계
            event_stats = db.query(
                SecurityEvent.event_type,
                SecurityEvent.severity,
                func.count().label('count')
            ).filter(
                SecurityEvent.timestamp >= since
            ).group_by(
                SecurityEvent.event_type,
                SecurityEvent.severity
            ).all()
            
            # 알림 수 통계
            alert_stats = db.query(
                SecurityAlert.severity,
                SecurityAlert.status,
                func.count().label('count')
            ).filter(
                SecurityAlert.created_at >= since
            ).group_by(
                SecurityAlert.severity,
                SecurityAlert.status
            ).all()
            
            # 차단된 IP 수
            blocked_ip_count = db.query(SecurityBlockedIP).filter(
                SecurityBlockedIP.is_active == True
            ).count()
            
            # 고유 IP 수
            unique_ips = db.query(func.count(func.distinct(SecurityEvent.ip_address))).filter(
                SecurityEvent.timestamp >= since
            ).scalar()
            
            return {
                'period_hours': hours,
                'event_statistics': [
                    {
                        'event_type': stat.event_type,
                        'severity': stat.severity,
                        'count': stat.count
                    }
                    for stat in event_stats
                ],
                'alert_statistics': [
                    {
                        'severity': stat.severity,
                        'status': stat.status,
                        'count': stat.count
                    }
                    for stat in alert_stats
                ],
                'blocked_ips': blocked_ip_count,
                'unique_ips': unique_ips,
                'threat_rules_active': len([r for r in self.threat_rules if r.is_active])
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get security statistics: {e}")
            return {}
    
    async def cleanup_expired_blocks(self, db: Session) -> int:
        """만료된 IP 차단 해제"""
        try:
            expired_blocks = db.query(SecurityBlockedIP).filter(
                and_(
                    SecurityBlockedIP.is_active == True,
                    SecurityBlockedIP.expires_at <= datetime.utcnow()
                )
            ).all()
            
            count = 0
            for block in expired_blocks:
                block.is_active = False
                self.blocked_ips.discard(str(block.ip_address))
                count += 1
            
            db.commit()
            
            if count > 0:
                self.logger.info(f"Cleaned up {count} expired IP blocks")
            
            return count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup expired blocks: {e}")
            db.rollback()
            return 0


# 전역 보안 모니터 인스턴스
security_monitor = SecurityMonitorService()