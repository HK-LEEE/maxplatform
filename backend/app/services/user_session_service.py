#%%
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging
import json

from ..models import User
from ..database import SessionLocal
from .user_switch_security_service import user_switch_security_service

logger = logging.getLogger(__name__)

class UserSessionService:
    def __init__(self):
        self.security_service = user_switch_security_service
    
    def get_user_active_sessions(self, user_id: str, db: Session) -> Dict:
        """사용자의 활성 세션 목록 조회"""
        try:
            # 사용자의 활성 세션과 토큰 정보 조회
            result = db.execute(
                text("""
                    SELECT DISTINCT
                        COALESCE(s.id::text, 'token-session-' || at.id::text) as session_id,
                        COALESCE(s.client_id, at.client_id) as client_id,
                        COALESCE(c.client_name, 'Unknown Client') as client_name,
                        COALESCE(s.created_at, at.created_at) as created_at,
                        s.last_used_at,
                        s.ip_address,
                        s.user_agent,
                        CASE WHEN s.id IS NOT NULL THEN 'session' ELSE 'token' END as source_type,
                        at.expires_at as token_expires_at
                    FROM oauth_access_tokens at
                    LEFT JOIN oauth_sessions s ON at.session_id = s.id
                    LEFT JOIN oauth_clients c ON COALESCE(s.client_id, at.client_id) = c.client_id
                    WHERE at.user_id = :user_id 
                    AND at.revoked_at IS NULL
                    AND (at.expires_at IS NULL OR at.expires_at > NOW())
                    ORDER BY COALESCE(s.last_used_at, at.created_at) DESC NULLS LAST
                """),
                {"user_id": user_id}
            )
            
            sessions_data = []
            current_session = None
            
            for i, row in enumerate(result):
                # 의심스러운 세션 판단 (간단한 휴리스틱)
                is_suspicious = self._is_session_suspicious(
                    row.ip_address,
                    row.user_agent,
                    row.created_at,
                    row.last_used_at
                )
                
                # 디바이스 정보 파싱
                device_info = self._parse_user_agent(row.user_agent) if row.user_agent else None
                
                # 위치 정보 (실제 구현에서는 GeoIP 사용)
                location = self._get_location_from_ip(row.ip_address) if row.ip_address else None
                
                session_info = {
                    "session_id": row.session_id,
                    "client_id": row.client_id,
                    "client_name": row.client_name,
                    "created_at": row.created_at,
                    "last_used_at": row.last_used_at,
                    "ip_address": row.ip_address,
                    "user_agent": row.user_agent,
                    "device_info": device_info,
                    "location": location,
                    "is_current_session": (i == 0),
                    "is_suspicious": is_suspicious,
                    "source_type": row.source_type,
                    "token_expires_at": row.token_expires_at
                }
                
                if i == 0:
                    current_session = session_info
                else:
                    sessions_data.append(session_info)
            
            # 현재 세션이 없는 경우 기본 세션 생성
            if not current_session:
                current_session = {
                    "session_id": "current",
                    "client_id": "platform",
                    "client_name": "MAX Platform",
                    "created_at": datetime.utcnow(),
                    "last_used_at": datetime.utcnow(),
                    "ip_address": None,
                    "user_agent": None,
                    "device_info": None,
                    "location": None,
                    "is_current_session": True,
                    "is_suspicious": False,
                    "source_type": "current",
                    "token_expires_at": None
                }
            
            suspicious_count = sum(1 for s in sessions_data if s["is_suspicious"])
            if current_session.get("is_suspicious"):
                suspicious_count += 1
            
            return {
                "current_session": current_session,
                "other_sessions": sessions_data,
                "total_sessions": len(sessions_data) + 1,
                "suspicious_sessions": suspicious_count
            }
            
        except Exception as e:
            logger.error(f"Error getting user sessions for {user_id}: {str(e)}")
            raise
    
    def logout_current_session(self, user_id: str, db: Session) -> Dict:
        """현재 세션만 로그아웃"""
        try:
            # 최신 액세스 토큰 하나만 해지
            result = db.execute(
                text("""
                    UPDATE oauth_access_tokens 
                    SET revoked_at = NOW() 
                    WHERE user_id = :user_id 
                    AND revoked_at IS NULL
                    ORDER BY created_at DESC
                    LIMIT 1
                """),
                {"user_id": user_id}
            )
            tokens_revoked = result.rowcount
            
            # 가장 최근 세션 하나 삭제
            result = db.execute(
                text("""
                    DELETE FROM oauth_sessions 
                    WHERE user_id = :user_id
                    AND id IN (
                        SELECT id FROM oauth_sessions 
                        WHERE user_id = :user_id
                        ORDER BY COALESCE(last_used_at, created_at) DESC
                        LIMIT 1
                    )
                """),
                {"user_id": user_id}
            )
            sessions_terminated = result.rowcount
            
            db.commit()
            
            logger.info(f"Current session logged out for user {user_id}")
            
            return {
                "message": "Current session logged out successfully",
                "logout_type": "current",
                "sessions_terminated": sessions_terminated,
                "tokens_revoked": tokens_revoked
            }
            
        except Exception as e:
            logger.error(f"Error logging out current session for {user_id}: {str(e)}")
            db.rollback()
            raise
    
    def logout_all_sessions(self, user_id: str, db: Session) -> Dict:
        """모든 세션 로그아웃"""
        try:
            # 모든 액세스 토큰 해지
            result = db.execute(
                text("""
                    UPDATE oauth_access_tokens 
                    SET revoked_at = NOW() 
                    WHERE user_id = :user_id 
                    AND revoked_at IS NULL
                """),
                {"user_id": user_id}
            )
            access_tokens_revoked = result.rowcount
            
            # 모든 리프레시 토큰 해지
            result = db.execute(
                text("""
                    UPDATE oauth_refresh_tokens 
                    SET revoked_at = NOW() 
                    WHERE user_id = :user_id 
                    AND revoked_at IS NULL
                """),
                {"user_id": user_id}
            )
            refresh_tokens_revoked = result.rowcount
            
            # 모든 세션 삭제
            result = db.execute(
                text("""
                    DELETE FROM oauth_sessions 
                    WHERE user_id = :user_id
                """),
                {"user_id": user_id}
            )
            sessions_terminated = result.rowcount
            
            db.commit()
            
            total_tokens_revoked = access_tokens_revoked + refresh_tokens_revoked
            
            logger.info(f"All sessions logged out for user {user_id}: {sessions_terminated} sessions, {total_tokens_revoked} tokens")
            
            return {
                "message": "All sessions logged out successfully",
                "logout_type": "all",
                "sessions_terminated": sessions_terminated,
                "tokens_revoked": total_tokens_revoked
            }
            
        except Exception as e:
            logger.error(f"Error logging out all sessions for {user_id}: {str(e)}")
            db.rollback()
            raise
    
    def logout_specific_sessions(self, user_id: str, session_ids: List[str], db: Session) -> Dict:
        """특정 세션들 로그아웃"""
        try:
            # 실제 세션 ID와 토큰 기반 세션 ID 분리
            real_session_ids = []
            token_session_ids = []
            
            for session_id in session_ids:
                if session_id.startswith("token-session-"):
                    # 토큰 기반 세션 - 토큰 ID 추출
                    token_id = session_id.replace("token-session-", "")
                    token_session_ids.append(token_id)
                else:
                    real_session_ids.append(session_id)
            
            sessions_terminated = 0
            tokens_revoked = 0
            failed_sessions = []
            
            # 실제 세션 삭제
            if real_session_ids:
                result = db.execute(
                    text("""
                        DELETE FROM oauth_sessions 
                        WHERE user_id = :user_id 
                        AND id = ANY(:session_ids)
                    """),
                    {"user_id": user_id, "session_ids": real_session_ids}
                )
                sessions_terminated += result.rowcount
                
                # 관련 토큰 해지
                result = db.execute(
                    text("""
                        UPDATE oauth_access_tokens 
                        SET revoked_at = NOW() 
                        WHERE user_id = :user_id 
                        AND session_id = ANY(:session_ids)
                        AND revoked_at IS NULL
                    """),
                    {"user_id": user_id, "session_ids": real_session_ids}
                )
                tokens_revoked += result.rowcount
            
            # 토큰 기반 세션 처리
            if token_session_ids:
                result = db.execute(
                    text("""
                        UPDATE oauth_access_tokens 
                        SET revoked_at = NOW() 
                        WHERE user_id = :user_id 
                        AND id = ANY(:token_ids)
                        AND revoked_at IS NULL
                    """),
                    {"user_id": user_id, "token_ids": token_session_ids}
                )
                tokens_revoked += result.rowcount
            
            db.commit()
            
            logger.info(f"Specific sessions logged out for user {user_id}: {len(session_ids)} requested, {sessions_terminated} sessions, {tokens_revoked} tokens")
            
            return {
                "message": f"Successfully logged out {len(session_ids)} sessions",
                "sessions_terminated": sessions_terminated,
                "tokens_revoked": tokens_revoked,
                "failed_sessions": failed_sessions
            }
            
        except Exception as e:
            logger.error(f"Error logging out specific sessions for {user_id}: {str(e)}")
            db.rollback()
            raise
    
    def get_user_session_activity(self, user_id: str, days: int = 30, db: Session) -> List[Dict]:
        """사용자 세션 활동 기록 조회"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            result = db.execute(
                text("""
                    SELECT 
                        'login' as activity_type,
                        at.created_at as timestamp,
                        at.client_id,
                        c.client_name,
                        s.ip_address,
                        s.user_agent
                    FROM oauth_access_tokens at
                    LEFT JOIN oauth_sessions s ON at.session_id = s.id
                    LEFT JOIN oauth_clients c ON at.client_id = c.client_id
                    WHERE at.user_id = :user_id 
                    AND at.created_at >= :start_date
                    
                    UNION ALL
                    
                    SELECT 
                        'logout' as activity_type,
                        at.revoked_at as timestamp,
                        at.client_id,
                        c.client_name,
                        s.ip_address,
                        s.user_agent
                    FROM oauth_access_tokens at
                    LEFT JOIN oauth_sessions s ON at.session_id = s.id
                    LEFT JOIN oauth_clients c ON at.client_id = c.client_id
                    WHERE at.user_id = :user_id 
                    AND at.revoked_at >= :start_date
                    AND at.revoked_at IS NOT NULL
                    
                    ORDER BY timestamp DESC
                    LIMIT 100
                """),
                {"user_id": user_id, "start_date": start_date}
            )
            
            activities = []
            for row in result:
                activities.append({
                    "activity_type": row.activity_type,
                    "timestamp": row.timestamp,
                    "client_id": row.client_id,
                    "client_name": row.client_name or "Unknown Client",
                    "ip_address": row.ip_address,
                    "user_agent": row.user_agent,
                    "location": self._get_location_from_ip(row.ip_address) if row.ip_address else None
                })
            
            return activities
    
    def secure_user_login(
        self, 
        user_id: str, 
        client_id: str, 
        request_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        db: Session = None
    ) -> Dict:
        """
        Secure user login with automatic user switch detection and cleanup.
        This method should be called when a user successfully authenticates.
        """
        try:
            logger.info(f"🔒 Secure login initiated for user {user_id} from client {client_id}")
            
            # Detect user switch
            switch_detection = self.security_service.detect_user_switch(
                client_id=client_id,
                new_user_id=user_id,
                request_ip=request_ip,
                db=db
            )
            
            cleanup_performed = False
            cleanup_stats = None
            
            if switch_detection["is_user_switch"] and switch_detection["requires_cleanup"]:
                logger.warning(f"🔒 User switch detected during secure login: "
                             f"{switch_detection['switch_type']} (risk: {switch_detection['risk_level']})")
                
                # Perform security cleanup
                cleanup_result = self.security_service.force_previous_user_cleanup(
                    client_id=client_id,
                    previous_user_id=switch_detection["previous_user_id"],
                    new_user_id=user_id,
                    reason="secure_login_cleanup",
                    db=db
                )
                
                cleanup_performed = cleanup_result["success"]
                cleanup_stats = cleanup_result.get("stats")
                
                # Create audit trail
                self.security_service.audit_user_switch(
                    client_id=client_id,
                    previous_user_id=switch_detection["previous_user_id"],
                    new_user_id=user_id,
                    switch_type=switch_detection["switch_type"],
                    risk_level=switch_detection["risk_level"],
                    risk_factors=switch_detection.get("risk_factors", []),
                    request_ip=request_ip,
                    user_agent=user_agent,
                    cleanup_stats=cleanup_stats,
                    db=db
                )
            
            # Get current session info after cleanup
            session_info = self.get_user_active_sessions(user_id, db)
            
            return {
                "success": True,
                "user_id": user_id,
                "client_id": client_id,
                "user_switch_detected": switch_detection["is_user_switch"],
                "switch_type": switch_detection.get("switch_type"),
                "risk_level": switch_detection.get("risk_level"),
                "cleanup_performed": cleanup_performed,
                "cleanup_stats": cleanup_stats,
                "session_info": session_info,
                "security_recommendations": self._get_security_recommendations(
                    switch_detection, request_ip, user_agent
                )
            }
            
        except Exception as e:
            logger.error(f"❌ Secure login failed for user {user_id}: {str(e)}")
            return {
                "success": False,
                "user_id": user_id,
                "client_id": client_id,
                "error": str(e),
                "user_switch_detected": False,
                "cleanup_performed": False
            }
    
    def force_secure_logout_all_clients(
        self, 
        user_id: str, 
        reason: str = "security_logout",
        exclude_client_id: Optional[str] = None,
        db: Session = None
    ) -> Dict:
        """
        Force logout from all clients with enhanced security cleanup.
        Useful for emergency security situations.
        """
        try:
            logger.warning(f"🔒 Force secure logout initiated for user {user_id} (reason: {reason})")
            
            # Get all active clients for this user before cleanup
            result = db.execute(
                text("""
                    SELECT DISTINCT client_id 
                    FROM oauth_access_tokens 
                    WHERE user_id = :user_id 
                    AND revoked_at IS NULL
                    AND (expires_at IS NULL OR expires_at > NOW())
                """),
                {"user_id": user_id}
            )
            
            active_clients = [row[0] for row in result.fetchall()]
            
            if exclude_client_id:
                active_clients = [c for c in active_clients if c != exclude_client_id]
            
            # Perform standard logout
            logout_result = self.logout_all_sessions(user_id, db)
            
            # Additional security cleanup for each client
            total_cleanup_stats = {
                "clients_cleaned": 0,
                "security_cleanups": [],
                "errors": []
            }
            
            for client_id in active_clients:
                try:
                    # Force cleanup for this client
                    cleanup_result = self.security_service.force_previous_user_cleanup(
                        client_id=client_id,
                        previous_user_id=user_id,
                        new_user_id="SECURITY_LOGOUT",  # Special marker
                        reason=f"force_logout_{reason}",
                        db=db
                    )
                    
                    total_cleanup_stats["clients_cleaned"] += 1
                    total_cleanup_stats["security_cleanups"].append({
                        "client_id": client_id,
                        "success": cleanup_result["success"],
                        "stats": cleanup_result.get("stats")
                    })
                    
                    # Audit each client cleanup
                    self.security_service.audit_user_switch(
                        client_id=client_id,
                        previous_user_id=user_id,
                        new_user_id="SECURITY_LOGOUT",
                        switch_type="force_logout",
                        risk_level="high",
                        risk_factors=[reason, "forced_security_logout"],
                        cleanup_stats=cleanup_result.get("stats"),
                        db=db
                    )
                    
                except Exception as client_error:
                    logger.error(f"❌ Client cleanup failed for {client_id}: {str(client_error)}")
                    total_cleanup_stats["errors"].append({
                        "client_id": client_id,
                        "error": str(client_error)
                    })
            
            return {
                "success": True,
                "message": f"Force logout completed for user {user_id}",
                "logout_result": logout_result,
                "security_cleanup": total_cleanup_stats,
                "clients_affected": len(active_clients)
            }
            
        except Exception as e:
            logger.error(f"❌ Force secure logout failed for user {user_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "user_id": user_id
            }
    
    def get_user_security_summary(self, user_id: str, db: Session) -> Dict:
        """
        Get comprehensive security summary for a user including recent switches.
        """
        try:
            # Get basic session info
            session_info = self.get_user_active_sessions(user_id, db)
            
            # Get recent user switch history
            switch_history = db.execute(
                text("""
                    SELECT 
                        client_id,
                        switch_type,
                        risk_level,
                        risk_factors,
                        created_at
                    FROM oauth_user_switch_audit 
                    WHERE new_user_id = :user_id 
                    OR previous_user_id = :user_id
                    ORDER BY created_at DESC 
                    LIMIT 10
                """),
                {"user_id": user_id}
            ).fetchall()
            
            # Get suspicious patterns
            suspicious_patterns = self.security_service.get_suspicious_switch_patterns(
                hours=24, db=db
            )
            
            # Calculate security score
            security_score = self._calculate_user_security_score(
                session_info, switch_history, suspicious_patterns, user_id
            )
            
            return {
                "user_id": user_id,
                "security_score": security_score,
                "session_info": session_info,
                "recent_switches": [
                    {
                        "client_id": row[0],
                        "switch_type": row[1],
                        "risk_level": row[2],
                        "risk_factors": row[3] or [],
                        "timestamp": row[4]
                    } for row in switch_history
                ],
                "suspicious_patterns": suspicious_patterns,
                "recommendations": self._get_user_security_recommendations(
                    session_info, switch_history, security_score
                )
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get security summary for user {user_id}: {str(e)}")
            return {
                "user_id": user_id,
                "error": str(e),
                "security_score": 0
            }
    
    def _get_security_recommendations(
        self, 
        switch_detection: Dict, 
        request_ip: Optional[str],
        user_agent: Optional[str]
    ) -> List[str]:
        """Generate security recommendations based on switch detection."""
        recommendations = []
        
        if switch_detection["is_user_switch"]:
            recommendations.append("브라우저 상태 정리가 수행되었습니다")
            
            if switch_detection.get("risk_level") == "high":
                recommendations.extend([
                    "모든 브라우저 탭을 닫고 새로 시작하는 것을 권장합니다",
                    "비밀번호를 변경하는 것을 고려해보세요",
                    "다른 기기에서의 로그인을 확인해보세요"
                ])
            elif switch_detection.get("risk_level") == "medium":
                recommendations.extend([
                    "다른 브라우저 탭을 확인해보세요",
                    "최근 로그인 활동을 검토해보세요"
                ])
        
        return recommendations
    
    def _calculate_user_security_score(
        self, 
        session_info: Dict, 
        switch_history: List, 
        suspicious_patterns: List,
        user_id: str
    ) -> int:
        """Calculate security score (0-100) for a user."""
        score = 100
        
        # Deduct points for suspicious sessions
        suspicious_sessions = session_info.get("suspicious_sessions", 0)
        score -= min(suspicious_sessions * 10, 30)
        
        # Deduct points for recent high-risk switches
        high_risk_switches = len([s for s in switch_history if s.get("risk_level") == "high"])
        score -= min(high_risk_switches * 15, 45)
        
        # Deduct points for being in suspicious patterns
        user_in_patterns = any(
            pattern for pattern in suspicious_patterns 
            if any(client for client in pattern.get("clients", []))
        )
        if user_in_patterns:
            score -= 20
        
        # Deduct points for multiple active sessions
        total_sessions = session_info.get("total_sessions", 1)
        if total_sessions > 5:
            score -= min((total_sessions - 5) * 5, 25)
        
        return max(score, 0)
    
    def _get_user_security_recommendations(
        self, 
        session_info: Dict, 
        switch_history: List,
        security_score: int
    ) -> List[str]:
        """Generate user-specific security recommendations."""
        recommendations = []
        
        if security_score < 50:
            recommendations.append("보안 점수가 낮습니다. 즉시 보안 검토가 필요합니다.")
        elif security_score < 70:
            recommendations.append("보안 상태를 개선하는 것을 권장합니다.")
        
        if session_info.get("suspicious_sessions", 0) > 0:
            recommendations.append("의심스러운 세션이 감지되었습니다. 해당 세션을 종료하세요.")
        
        if session_info.get("total_sessions", 0) > 5:
            recommendations.append("활성 세션이 많습니다. 불필요한 세션을 정리하세요.")
        
        recent_high_risk = len([s for s in switch_history if s.get("risk_level") == "high"])
        if recent_high_risk > 0:
            recommendations.append("최근 고위험 사용자 전환이 감지되었습니다. 계정 보안을 강화하세요.")
        
        return recommendations
    
    def _is_session_suspicious(
        self, 
        ip_address: str, 
        user_agent: str, 
        created_at: datetime, 
        last_used_at: datetime
    ) -> bool:
        """의심스러운 세션 판단 (간단한 휴리스틱)"""
        # 실제 구현에서는 더 정교한 알고리즘 사용
        
        # 1. 새로운 IP 주소 (실제로는 사용자의 일반적인 IP와 비교)
        if ip_address and self._is_new_ip_address(ip_address):
            return True
        
        # 2. 비정상적인 User Agent
        if user_agent and self._is_suspicious_user_agent(user_agent):
            return True
        
        # 3. 비정상적인 시간대의 로그인
        if created_at and self._is_unusual_login_time(created_at):
            return True
        
        # 4. 장기간 미사용 후 갑작스러운 활동
        if last_used_at and created_at:
            inactive_period = last_used_at - created_at
            if inactive_period.days > 30:  # 30일 이상 미사용 후 활동
                return True
        
        return False
    
    def _is_new_ip_address(self, ip_address: str) -> bool:
        """새로운 IP 주소인지 확인 (간단한 구현)"""
        # 실제로는 사용자의 최근 IP 주소 기록과 비교
        # 현재는 간단히 private IP가 아닌 경우 의심스러운 것으로 처리
        if ip_address.startswith(('192.168.', '10.', '172.')):
            return False
        return True
    
    def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """의심스러운 User Agent인지 확인"""
        suspicious_patterns = [
            'bot', 'crawler', 'spider', 'scraper',
            'curl', 'wget', 'python-requests',
            'automated', 'script'
        ]
        
        user_agent_lower = user_agent.lower()
        return any(pattern in user_agent_lower for pattern in suspicious_patterns)
    
    def _is_unusual_login_time(self, login_time: datetime) -> bool:
        """비정상적인 로그인 시간인지 확인"""
        # 심야 시간대 (02:00 - 05:00) 로그인을 의심스러운 것으로 처리
        hour = login_time.hour
        return 2 <= hour <= 5
    
    def _parse_user_agent(self, user_agent: str) -> Dict:
        """User Agent 파싱 (간단한 구현)"""
        if not user_agent:
            return None
        
        # 실제로는 user-agents 라이브러리 등을 사용
        device_info = {"raw": user_agent}
        
        # 간단한 파싱
        if "mobile" in user_agent.lower():
            device_info["device_type"] = "mobile"
        elif "tablet" in user_agent.lower():
            device_info["device_type"] = "tablet"
        else:
            device_info["device_type"] = "desktop"
        
        # 브라우저 감지
        if "chrome" in user_agent.lower():
            device_info["browser"] = "Chrome"
        elif "firefox" in user_agent.lower():
            device_info["browser"] = "Firefox"
        elif "safari" in user_agent.lower():
            device_info["browser"] = "Safari"
        elif "edge" in user_agent.lower():
            device_info["browser"] = "Edge"
        else:
            device_info["browser"] = "Unknown"
        
        # OS 감지
        if "windows" in user_agent.lower():
            device_info["os"] = "Windows"
        elif "mac" in user_agent.lower():
            device_info["os"] = "macOS"
        elif "linux" in user_agent.lower():
            device_info["os"] = "Linux"
        elif "android" in user_agent.lower():
            device_info["os"] = "Android"
        elif "ios" in user_agent.lower():
            device_info["os"] = "iOS"
        else:
            device_info["os"] = "Unknown"
        
        return device_info
    
    def _get_location_from_ip(self, ip_address: str) -> Dict:
        """IP 주소에서 위치 정보 획득 (간단한 구현)"""
        if not ip_address:
            return None
        
        # 실제로는 GeoIP 데이터베이스나 서비스 사용
        # 현재는 간단한 더미 데이터
        if ip_address.startswith(('192.168.', '10.', '172.')):
            return {
                "country": "Local",
                "country_code": "LOCAL",
                "city": "Internal Network",
                "region": "Private",
                "timezone": "Local"
            }
        
        # 외부 IP의 경우 더미 위치 정보
        return {
            "country": "South Korea",
            "country_code": "KR", 
            "city": "Seoul",
            "region": "Seoul",
            "timezone": "Asia/Seoul"
        }

# 싱글톤 인스턴스
user_session_service = UserSessionService()