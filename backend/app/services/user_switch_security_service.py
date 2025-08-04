"""
User Switch Security Service
Handles secure user switching to prevent session contamination and privilege escalation.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..models import User
from ..utils.logging_config import log_oauth_event

logger = logging.getLogger(__name__)

class UserSwitchSecurityService:
    """
    Comprehensive security service for handling user switches in OAuth flow.
    Prevents session contamination, token persistence, and privilege escalation.
    """
    
    def __init__(self):
        self.suspicious_switch_threshold = 5  # Max switches per hour
        self.audit_retention_days = 90
    
    def detect_user_switch(
        self, 
        client_id: str, 
        new_user_id: str, 
        request_ip: Optional[str] = None,
        db: Session = None
    ) -> Dict:
        """
        Detect if this is a user switch for the given client.
        Returns switch detection result with security assessment.
        """
        try:
            # Get the most recent active session for this client
            # oauth_sessions 테이블에서 세션 정보 조회 (DISTINCT 제거하여 ORDER BY 오류 해결)
            result = db.execute(
                text("""
                    SELECT 
                        s.user_id as session_user_id,
                        at.user_id as token_user_id,
                        s.last_used_at,
                        at.created_at as token_created_at,
                        s.ip_address,
                        s.user_agent
                    FROM oauth_access_tokens at
                    LEFT JOIN oauth_sessions s ON at.client_id = s.client_id
                    WHERE at.client_id = :client_id 
                    AND at.revoked_at IS NULL
                    AND (at.expires_at IS NULL OR at.expires_at > NOW())
                    ORDER BY COALESCE(s.last_used_at, at.created_at) DESC
                    LIMIT 1
                """),
                {"client_id": client_id}
            )
            
            previous_user_data = result.first()
            
            if not previous_user_data:
                # First login for this client
                return {
                    "is_user_switch": False,
                    "previous_user_id": None,
                    "switch_type": "first_login",
                    "risk_level": "low",
                    "requires_cleanup": False
                }
            
            # Determine the previous user ID (prefer session data over token data)
            previous_user_id = (previous_user_data.session_user_id or 
                              previous_user_data.token_user_id)
            
            if not previous_user_id or str(previous_user_id) == str(new_user_id):
                # Same user logging in again
                return {
                    "is_user_switch": False,
                    "previous_user_id": previous_user_id,
                    "switch_type": "same_user",
                    "risk_level": "low",
                    "requires_cleanup": False
                }
            
            # This is a user switch - assess security risk
            risk_assessment = self._assess_switch_risk(
                client_id, previous_user_id, new_user_id, request_ip, db
            )
            
            return {
                "is_user_switch": True,
                "previous_user_id": str(previous_user_id),
                "new_user_id": str(new_user_id),
                "switch_type": "user_change",
                "risk_level": risk_assessment["risk_level"],
                "risk_factors": risk_assessment["risk_factors"],
                "requires_cleanup": True,
                "previous_session_data": {
                    "last_used_at": previous_user_data.last_used_at,
                    "ip_address": previous_user_data.ip_address,
                    "user_agent": previous_user_data.user_agent
                }
            }
            
        except Exception as e:
            logger.error(f"Error detecting user switch for client {client_id}: {str(e)}")
            # 트랜잭션 롤백하여 오류 전파 방지
            if db:
                try:
                    db.rollback()
                except:
                    pass
            
            # Fail secure - assume it's a switch requiring cleanup
            return {
                "is_user_switch": True,
                "previous_user_id": None,
                "new_user_id": str(new_user_id),
                "switch_type": "error_detected",
                "risk_level": "high",
                "risk_factors": ["detection_error"],
                "requires_cleanup": True,
                "error": str(e)
            }
    
    def _assess_switch_risk(
        self, 
        client_id: str, 
        previous_user_id: str, 
        new_user_id: str,
        request_ip: Optional[str],
        db: Session
    ) -> Dict:
        """Assess the security risk level of a user switch."""
        risk_factors = []
        risk_score = 0
        
        try:
            # Check if previous user was admin
            prev_user_result = db.execute(
                text("SELECT is_admin, role_id FROM users WHERE id = :user_id"),
                {"user_id": previous_user_id}
            )
            prev_user = prev_user_result.first()
            
            if prev_user and prev_user.is_admin:
                risk_factors.append("previous_user_admin")
                risk_score += 3
            
            # Check if new user is admin (privilege escalation attempt)
            new_user_result = db.execute(
                text("SELECT is_admin, role_id FROM users WHERE id = :user_id"),
                {"user_id": new_user_id}
            )
            new_user = new_user_result.first()
            
            if new_user and new_user.is_admin:
                risk_factors.append("new_user_admin")
                risk_score += 2
            
            # Check for rapid user switching (suspicious behavior)
            recent_switches = db.execute(
                text("""
                    SELECT COUNT(*) as switch_count
                    FROM oauth_user_switch_audit 
                    WHERE client_id = :client_id 
                    AND created_at > :threshold
                """),
                {
                    "client_id": client_id,
                    "threshold": datetime.utcnow() - timedelta(hours=1)
                }
            ).first()
            
            if recent_switches and recent_switches.switch_count >= self.suspicious_switch_threshold:
                risk_factors.append("rapid_switching")
                risk_score += 4
            
            # Check for IP address changes
            if request_ip:
                recent_ip_result = db.execute(
                    text("""
                        SELECT ip_address FROM oauth_sessions 
                        WHERE user_id = :user_id AND client_id = :client_id
                        ORDER BY last_used_at DESC LIMIT 1
                    """),
                    {"user_id": previous_user_id, "client_id": client_id}
                )
                recent_ip = recent_ip_result.first()
                
                if recent_ip and recent_ip.ip_address != request_ip:
                    risk_factors.append("ip_address_change")
                    risk_score += 1
            
            # Determine risk level
            if risk_score >= 6:
                risk_level = "critical"
            elif risk_score >= 4:
                risk_level = "high"
            elif risk_score >= 2:
                risk_level = "medium"
            else:
                risk_level = "low"
            
            return {
                "risk_level": risk_level,
                "risk_score": risk_score,
                "risk_factors": risk_factors
            }
            
        except Exception as e:
            logger.error(f"Error assessing switch risk: {str(e)}")
            return {
                "risk_level": "high",
                "risk_score": 5,
                "risk_factors": ["assessment_error"]
            }
    
    def force_previous_user_cleanup(
        self, 
        client_id: str, 
        previous_user_id: str, 
        new_user_id: str,
        reason: str = "user_switch",
        db: Session = None
    ) -> Dict:
        """
        Force cleanup of previous user's sessions and tokens for the given client.
        This is the critical security function that prevents session contamination.
        """
        try:
            # previous_user_id가 None인 경우 정리할 세션이 없으므로 조기 반환
            if previous_user_id is None:
                logger.info(f"🔒 SECURITY: No previous user to cleanup for client {client_id}")
                return {
                    "success": True,
                    "cleanup_performed": False,
                    "message": "No previous user sessions to cleanup",
                    "stats": {
                        "access_tokens_revoked": 0,
                        "refresh_tokens_revoked": 0,
                        "sessions_terminated": 0,
                        "client_tokens_cleaned": 0,
                        "errors": []
                    }
                }
            
            cleanup_stats = {
                "access_tokens_revoked": 0,
                "refresh_tokens_revoked": 0,
                "sessions_terminated": 0,
                "client_tokens_cleaned": 0,
                "errors": []
            }
            
            logger.warning(f"🔒 SECURITY: Force cleanup initiated - Client: {client_id}, "
                          f"Previous User: {previous_user_id}, New User: {new_user_id}")
            
            # 1. Revoke all access tokens for previous user on this client
            access_result = db.execute(
                text("""
                    UPDATE oauth_access_tokens 
                    SET revoked_at = NOW(), 
                        revocation_reason = :reason
                    WHERE client_id = :client_id 
                    AND user_id = :previous_user_id
                    AND revoked_at IS NULL
                """),
                {
                    "client_id": client_id,
                    "previous_user_id": previous_user_id,
                    "reason": f"user_switch_to_{new_user_id}"
                }
            )
            cleanup_stats["access_tokens_revoked"] = access_result.rowcount
            
            # 2. Revoke all refresh tokens for previous user on this client
            refresh_result = db.execute(
                text("""
                    UPDATE oauth_refresh_tokens 
                    SET revoked_at = NOW(),
                        token_status = 'revoked'
                    WHERE client_id = :client_id 
                    AND user_id = :previous_user_id
                    AND revoked_at IS NULL
                """),
                {
                    "client_id": client_id,
                    "previous_user_id": previous_user_id
                }
            )
            cleanup_stats["refresh_tokens_revoked"] = refresh_result.rowcount
            
            # 3. Terminate OAuth sessions for previous user on this client
            session_result = db.execute(
                text("""
                    DELETE FROM oauth_sessions 
                    WHERE client_id = :client_id 
                    AND user_id = :previous_user_id
                """),
                {
                    "client_id": client_id,
                    "previous_user_id": previous_user_id
                }
            )
            cleanup_stats["sessions_terminated"] = session_result.rowcount
            
            # 4. Clean up any orphaned tokens that might belong to the client
            # Only clean up orphaned tokens if we have a valid new_user_id
            if new_user_id:
                orphan_result = db.execute(
                    text("""
                        UPDATE oauth_access_tokens 
                        SET revoked_at = NOW(),
                            revocation_reason = 'orphaned_client_switch'
                        WHERE client_id = :client_id 
                        AND user_id != :new_user_id
                        AND revoked_at IS NULL
                        AND created_at < NOW() - INTERVAL '5 minutes'
                    """),
                    {
                        "client_id": client_id,
                        "new_user_id": new_user_id
                    }
                )
                cleanup_stats["client_tokens_cleaned"] = orphan_result.rowcount
            
            db.commit()
            
            total_cleaned = (cleanup_stats["access_tokens_revoked"] + 
                           cleanup_stats["refresh_tokens_revoked"] + 
                           cleanup_stats["sessions_terminated"] + 
                           cleanup_stats["client_tokens_cleaned"])
            
            logger.info(f"✅ User switch cleanup completed - {total_cleaned} items cleaned")
            
            return {
                "success": True,
                "cleanup_performed": total_cleaned > 0,
                "stats": cleanup_stats,
                "message": f"Successfully cleaned {total_cleaned} authentication items"
            }
            
        except Exception as e:
            logger.error(f"❌ Critical error in force cleanup: {str(e)}")
            db.rollback()
            return {
                "success": False,
                "cleanup_performed": False,
                "stats": cleanup_stats,
                "error": str(e),
                "message": "Failed to perform security cleanup"
            }
    
    def audit_user_switch(
        self,
        client_id: str,
        previous_user_id: Optional[str],
        new_user_id: str,
        switch_type: str,
        risk_level: str,
        risk_factors: List[str],
        request_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        cleanup_stats: Optional[Dict] = None,
        db: Session = None
    ) -> bool:
        """
        Create comprehensive audit trail for user switches.
        Essential for security monitoring and compliance.
        """
        try:
            # Create audit record - JSON 파라미터를 올바르게 처리하여 SQL 구문 오류 방지
            db.execute(
                text("""
                    INSERT INTO oauth_user_switch_audit 
                    (client_id, previous_user_id, new_user_id, switch_type, 
                     risk_level, risk_factors, request_ip, user_agent, 
                     cleanup_stats, created_at)
                    VALUES (:client_id, :previous_user_id, :new_user_id, :switch_type,
                            :risk_level, :risk_factors, :request_ip, :user_agent,
                            :cleanup_stats, NOW())
                """),
                {
                    "client_id": client_id,
                    "previous_user_id": previous_user_id,
                    "new_user_id": new_user_id,
                    "switch_type": switch_type,
                    "risk_level": risk_level,
                    "risk_factors": json.dumps(risk_factors or []),
                    "request_ip": request_ip,
                    "user_agent": user_agent,
                    "cleanup_stats": json.dumps(cleanup_stats or {})
                }
            )
            
            # Log OAuth event for monitoring - extra_data 파라미터 제거하여 함수 시그니처 오류 방지
            log_oauth_event(
                event_type="user_switch",
                client_id=client_id,
                user_id=new_user_id,
                success=True,
                ip_address=request_ip,
                user_agent=user_agent
            )
            
            db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to create user switch audit: {str(e)}")
            # 트랜잭션 롤백하여 오류 전파 방지
            if db:
                try:
                    db.rollback()
                except:
                    pass
            return False
    
    def get_suspicious_switch_patterns(
        self, 
        hours: int = 24, 
        db: Session = None
    ) -> List[Dict]:
        """
        Identify suspicious user switching patterns for security monitoring.
        """
        try:
            result = db.execute(
                text("""
                    SELECT 
                        client_id,
                        COUNT(*) as switch_count,
                        COUNT(DISTINCT new_user_id) as unique_users,
                        COUNT(DISTINCT request_ip) as unique_ips,
                        MAX(risk_level) as max_risk_level,
                        string_agg(DISTINCT risk_level, ', ') as risk_levels,
                        MIN(created_at) as first_switch,
                        MAX(created_at) as last_switch
                    FROM oauth_user_switch_audit 
                    WHERE created_at > NOW() - INTERVAL '%s hours'
                    GROUP BY client_id
                    HAVING COUNT(*) >= :threshold
                    ORDER BY switch_count DESC, max_risk_level DESC
                """ % hours),
                {"threshold": self.suspicious_switch_threshold}
            )
            
            suspicious_patterns = []
            for row in result:
                suspicious_patterns.append({
                    "client_id": row.client_id,
                    "switch_count": row.switch_count,
                    "unique_users": row.unique_users,
                    "unique_ips": row.unique_ips,
                    "max_risk_level": row.max_risk_level,
                    "risk_levels": row.risk_levels.split(', ') if row.risk_levels else [],
                    "first_switch": row.first_switch,
                    "last_switch": row.last_switch,
                    "time_span_hours": (row.last_switch - row.first_switch).total_seconds() / 3600
                })
            
            return suspicious_patterns
            
        except Exception as e:
            logger.error(f"Error identifying suspicious patterns: {str(e)}")
            return []
    
    def cleanup_old_audit_records(self, db: Session = None) -> int:
        """Clean up old audit records beyond retention period."""
        try:
            result = db.execute(
                text("""
                    DELETE FROM oauth_user_switch_audit 
                    WHERE created_at < NOW() - INTERVAL '%s days'
                """ % self.audit_retention_days)
            )
            
            deleted_count = result.rowcount
            db.commit()
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old user switch audit records")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up audit records: {str(e)}")
            return 0

# Singleton instance
user_switch_security_service = UserSwitchSecurityService()