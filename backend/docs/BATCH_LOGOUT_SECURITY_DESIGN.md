# 일괄 로그아웃 보안 및 권한 설계

## 개요

일괄 로그아웃은 시스템의 중요한 보안 기능으로, 잘못 사용될 경우 서비스 가용성에 심각한 영향을 줄 수 있습니다. 따라서 강력한 보안 및 권한 체계가 필요합니다.

## 권한 체계

### 1. 권한 레벨

```python
class BatchLogoutPermission(Enum):
    # 기본 권한
    VIEW_BATCH_LOGOUT_JOBS = "batch_logout:view"  # 작업 목록 조회
    
    # 실행 권한 (레벨별)
    EXECUTE_GROUP_LOGOUT = "batch_logout:execute:group"  # 그룹 로그아웃
    EXECUTE_CLIENT_LOGOUT = "batch_logout:execute:client"  # 클라이언트 로그아웃
    EXECUTE_TIME_LOGOUT = "batch_logout:execute:time"  # 시간 기반 로그아웃
    EXECUTE_CONDITIONAL_LOGOUT = "batch_logout:execute:conditional"  # 조건부 로그아웃
    EXECUTE_EMERGENCY_LOGOUT = "batch_logout:execute:emergency"  # 긴급 로그아웃
    
    # 관리 권한
    CANCEL_BATCH_LOGOUT = "batch_logout:cancel"  # 작업 취소
    
    # 최고 권한
    BATCH_LOGOUT_ADMIN = "batch_logout:admin"  # 모든 일괄 로그아웃 권한
```

### 2. 역할별 권한 매핑

| 역할 | 권한 |
|------|------|
| Security Admin | 모든 일괄 로그아웃 권한 |
| System Admin | 긴급 로그아웃 제외한 모든 권한 |
| Group Admin | 자신이 관리하는 그룹의 그룹 로그아웃만 |
| OAuth Admin | 클라이언트 로그아웃, 시간 기반 로그아웃 |
| Auditor | 조회 권한만 |

### 3. 권한 검증 구현

```python
from functools import wraps
from typing import List, Optional
from fastapi import HTTPException, Depends

class BatchLogoutPermissionChecker:
    def __init__(self):
        self.permission_hierarchy = {
            BatchLogoutPermission.BATCH_LOGOUT_ADMIN: [
                BatchLogoutPermission.VIEW_BATCH_LOGOUT_JOBS,
                BatchLogoutPermission.EXECUTE_GROUP_LOGOUT,
                BatchLogoutPermission.EXECUTE_CLIENT_LOGOUT,
                BatchLogoutPermission.EXECUTE_TIME_LOGOUT,
                BatchLogoutPermission.EXECUTE_CONDITIONAL_LOGOUT,
                BatchLogoutPermission.EXECUTE_EMERGENCY_LOGOUT,
                BatchLogoutPermission.CANCEL_BATCH_LOGOUT
            ]
        }
    
    def require_permission(self, permission: BatchLogoutPermission):
        """권한 검증 데코레이터"""
        def decorator(func):
            @wraps(func)
            async def wrapper(
                current_user: User = Depends(get_current_user),
                *args, 
                **kwargs
            ):
                if not self.has_permission(current_user, permission):
                    raise HTTPException(
                        status_code=403,
                        detail=f"Permission denied: {permission.value} required"
                    )
                
                # 추가 검증 (그룹 관리자의 경우)
                if permission == BatchLogoutPermission.EXECUTE_GROUP_LOGOUT:
                    group_id = kwargs.get('group_id')
                    if not self.can_manage_group(current_user, group_id):
                        raise HTTPException(
                            status_code=403,
                            detail="You can only logout users from groups you manage"
                        )
                
                return await func(current_user=current_user, *args, **kwargs)
            return wrapper
        return decorator
    
    def has_permission(self, user: User, permission: BatchLogoutPermission) -> bool:
        """사용자 권한 확인"""
        # 최고 관리자 체크
        if user.is_super_admin:
            return True
        
        # 직접 권한 체크
        if permission.value in user.permissions:
            return True
        
        # 상위 권한 체크
        for parent_perm, child_perms in self.permission_hierarchy.items():
            if parent_perm.value in user.permissions and permission in child_perms:
                return True
        
        return False
    
    def can_manage_group(self, user: User, group_id: str) -> bool:
        """그룹 관리 권한 확인"""
        # 시스템 관리자는 모든 그룹 관리 가능
        if user.is_admin or self.has_permission(user, BatchLogoutPermission.BATCH_LOGOUT_ADMIN):
            return True
        
        # 그룹 관리자 확인
        return group_id in user.managed_group_ids

permission_checker = BatchLogoutPermissionChecker()
```

## 보안 메커니즘

### 1. 다단계 인증

긴급 로그아웃의 경우 추가 인증 필요:

```python
class EmergencyAuthService:
    def __init__(self):
        self.emergency_key_duration = timedelta(minutes=5)
        
    def generate_emergency_key(self, user_id: str, db: Session) -> str:
        """긴급 키 생성 (SMS/이메일로 전송)"""
        # 6자리 숫자 코드 생성
        code = f"{random.randint(100000, 999999)}"
        
        # Redis에 저장 (5분 유효)
        redis_key = f"emergency_logout_key:{user_id}"
        redis_client.setex(redis_key, self.emergency_key_duration, code)
        
        # SMS/이메일 전송
        self._send_emergency_code(user_id, code)
        
        # 감사 로그
        log_security_event(
            "emergency_key_generated",
            user_id=user_id,
            ip_address=request.client.host
        )
        
        return "Emergency key sent to registered contact"
    
    def verify_emergency_key(self, user_id: str, key: str) -> bool:
        """긴급 키 검증"""
        redis_key = f"emergency_logout_key:{user_id}"
        stored_key = redis_client.get(redis_key)
        
        if not stored_key or stored_key != key:
            log_security_event(
                "emergency_key_verification_failed",
                user_id=user_id,
                attempted_key=key[:2] + "****"
            )
            return False
        
        # 사용 후 즉시 삭제
        redis_client.delete(redis_key)
        return True
```

### 2. Rate Limiting

일괄 로그아웃 작업에 대한 속도 제한:

```python
from datetime import datetime, timedelta

class BatchLogoutRateLimiter:
    def __init__(self):
        self.limits = {
            BatchLogoutType.GROUP_BASED: {"count": 10, "window": timedelta(hours=1)},
            BatchLogoutType.CLIENT_BASED: {"count": 5, "window": timedelta(hours=1)},
            BatchLogoutType.TIME_BASED: {"count": 3, "window": timedelta(hours=24)},
            BatchLogoutType.CONDITIONAL: {"count": 5, "window": timedelta(hours=6)},
            BatchLogoutType.EMERGENCY: {"count": 1, "window": timedelta(hours=24)}
        }
    
    def check_rate_limit(self, user_id: str, logout_type: BatchLogoutType, db: Session) -> bool:
        """Rate limit 확인"""
        limit_config = self.limits[logout_type]
        window_start = datetime.utcnow() - limit_config["window"]
        
        # 최근 작업 수 확인
        recent_jobs = db.execute(
            text("""
                SELECT COUNT(*) FROM oauth_batch_logout_jobs
                WHERE initiated_by = :user_id
                AND job_type = :job_type
                AND created_at > :window_start
            """),
            {
                "user_id": user_id,
                "job_type": logout_type.value,
                "window_start": window_start
            }
        ).scalar()
        
        if recent_jobs >= limit_config["count"]:
            remaining_time = self._get_remaining_time(user_id, logout_type, db)
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Try again in {remaining_time} minutes."
            )
        
        return True

rate_limiter = BatchLogoutRateLimiter()
```

### 3. 실수 방지 메커니즘

#### Dry Run 모드

```python
class DryRunValidator:
    def simulate_batch_logout(
        self,
        conditions: Dict,
        logout_type: BatchLogoutType,
        db: Session
    ) -> Dict:
        """실제 실행 없이 영향 시뮬레이션"""
        affected_users = set()
        affected_tokens = {"access": 0, "refresh": 0}
        affected_sessions = 0
        
        if logout_type == BatchLogoutType.GROUP_BASED:
            users = self._get_group_users(conditions["group_id"], db)
            affected_users.update(users)
            
        elif logout_type == BatchLogoutType.CLIENT_BASED:
            # 클라이언트별 토큰 수 계산
            result = db.execute(
                text("""
                    SELECT COUNT(DISTINCT user_id) as users,
                           COUNT(*) FILTER (WHERE expires_at > NOW()) as active_tokens
                    FROM oauth_access_tokens
                    WHERE client_id = :client_id
                    AND revoked_at IS NULL
                """),
                {"client_id": conditions["client_id"]}
            ).first()
            
            if result:
                affected_users.add(result.users)
                affected_tokens["access"] = result.active_tokens
        
        # 경고 생성
        warnings = []
        if len(affected_users) > 100:
            warnings.append(f"This will affect {len(affected_users)} users!")
        
        if affected_tokens["access"] + affected_tokens["refresh"] > 1000:
            warnings.append(f"This will revoke over 1000 tokens!")
        
        return {
            "simulation_result": {
                "affected_users": len(affected_users),
                "affected_tokens": affected_tokens,
                "affected_sessions": affected_sessions,
                "warnings": warnings
            }
        }
```

#### 확인 메커니즘

```python
def validate_dangerous_operation(
    operation_type: str,
    expected_impact: Dict,
    confirmation_code: str
) -> bool:
    """위험한 작업에 대한 확인"""
    # 영향이 큰 작업은 특별한 확인 코드 필요
    if expected_impact["affected_users"] > 1000:
        expected_code = f"CONFIRM_{operation_type.upper()}_{expected_impact['affected_users']}"
        if confirmation_code != expected_code:
            raise HTTPException(
                status_code=400,
                detail=f"Please confirm by providing: {expected_code}"
            )
    
    return True
```

## 감사 로깅

### 1. 로깅 레벨

```python
class BatchLogoutAuditLevel(Enum):
    INFO = "info"      # 일반 작업
    WARNING = "warning" # 대량 작업
    CRITICAL = "critical" # 긴급 로그아웃

class BatchLogoutAuditLogger:
    def log_batch_logout_event(
        self,
        event_type: str,
        job_id: str,
        user_id: str,
        details: Dict,
        level: BatchLogoutAuditLevel,
        db: Session
    ):
        """일괄 로그아웃 이벤트 로깅"""
        # 데이터베이스 로깅
        db.execute(
            text("""
                INSERT INTO oauth_audit_logs 
                (action, user_id, client_id, success, metadata, ip_address, user_agent)
                VALUES (:action, :user_id, :client_id, :success, :metadata, :ip, :agent)
            """),
            {
                "action": f"batch_logout_{event_type}",
                "user_id": user_id,
                "client_id": None,
                "success": True,
                "metadata": {
                    "job_id": job_id,
                    "level": level.value,
                    **details
                },
                "ip": request.client.host,
                "agent": request.headers.get("User-Agent")
            }
        )
        
        # 중요 이벤트는 외부 SIEM 시스템으로도 전송
        if level in [BatchLogoutAuditLevel.WARNING, BatchLogoutAuditLevel.CRITICAL]:
            self._send_to_siem(event_type, job_id, user_id, details)
        
        # 긴급 로그아웃은 즉시 알림
        if level == BatchLogoutAuditLevel.CRITICAL:
            self._send_security_alert(event_type, job_id, user_id, details)
```

### 2. 감사 보고서

```python
class BatchLogoutAuditReport:
    def generate_monthly_report(self, month: int, year: int, db: Session) -> Dict:
        """월간 일괄 로그아웃 감사 보고서"""
        return {
            "period": f"{year}-{month:02d}",
            "summary": {
                "total_batch_logouts": self._count_total_jobs(month, year, db),
                "by_type": self._count_by_type(month, year, db),
                "by_user": self._count_by_user(month, year, db),
                "emergency_logouts": self._count_emergency(month, year, db)
            },
            "top_reasons": self._get_top_reasons(month, year, db),
            "affected_users": self._count_affected_users(month, year, db),
            "failed_operations": self._get_failed_operations(month, year, db),
            "suspicious_patterns": self._detect_suspicious_patterns(month, year, db)
        }
    
    def _detect_suspicious_patterns(self, month: int, year: int, db: Session) -> List[Dict]:
        """의심스러운 패턴 탐지"""
        patterns = []
        
        # 비정상적으로 많은 로그아웃 실행한 사용자
        frequent_users = db.execute(
            text("""
                SELECT initiated_by, COUNT(*) as count
                FROM oauth_batch_logout_jobs
                WHERE EXTRACT(MONTH FROM created_at) = :month
                AND EXTRACT(YEAR FROM created_at) = :year
                GROUP BY initiated_by
                HAVING COUNT(*) > 10
            """),
            {"month": month, "year": year}
        ).fetchall()
        
        if frequent_users:
            patterns.append({
                "type": "excessive_usage",
                "details": [{"user_id": str(u.initiated_by), "count": u.count} for u in frequent_users]
            })
        
        # 짧은 시간 내 반복적인 로그아웃
        rapid_logouts = db.execute(
            text("""
                SELECT initiated_by, COUNT(*) as count,
                       MIN(created_at) as first_logout,
                       MAX(created_at) as last_logout
                FROM oauth_batch_logout_jobs
                WHERE created_at >= NOW() - INTERVAL '1 hour'
                GROUP BY initiated_by
                HAVING COUNT(*) > 3
            """)
        ).fetchall()
        
        if rapid_logouts:
            patterns.append({
                "type": "rapid_succession",
                "details": [
                    {
                        "user_id": str(r.initiated_by),
                        "count": r.count,
                        "duration": str(r.last_logout - r.first_logout)
                    } for r in rapid_logouts
                ]
            })
        
        return patterns
```

## 알림 시스템 보안

### 1. 알림 템플릿

```python
class SecureNotificationService:
    def __init__(self):
        self.templates = {
            "group_logout": {
                "subject": "Security Notice: Your session has been terminated",
                "body": """
                Dear {user_name},
                
                Your MAX Platform session has been terminated as part of a security update 
                affecting your group: {group_name}.
                
                Reason: {reason}
                Time: {timestamp}
                
                Please log in again to continue using the platform.
                If you believe this is an error, please contact your administrator.
                
                Thank you for your understanding.
                MAX Platform Security Team
                """
            },
            "emergency_logout": {
                "subject": "URGENT: Emergency Security Logout",
                "body": """
                IMPORTANT SECURITY NOTICE
                
                All sessions have been terminated due to a security incident.
                
                Action Required:
                1. Change your password immediately upon next login
                2. Review your recent account activity
                3. Report any suspicious activity to security@maxplatform.com
                
                We apologize for the inconvenience.
                MAX Platform Security Team
                """
            }
        }
    
    def send_batch_logout_notification(
        self,
        user: User,
        logout_type: BatchLogoutType,
        reason: str,
        additional_info: Dict
    ):
        """안전한 알림 전송"""
        # 민감한 정보 필터링
        safe_reason = self._sanitize_reason(reason)
        
        # 템플릿 선택
        template = self.templates.get(
            logout_type.value,
            self.templates["group_logout"]
        )
        
        # 개인화된 메시지 생성 (민감 정보 제외)
        message = template["body"].format(
            user_name=user.display_name or "User",
            group_name=additional_info.get("group_name", "N/A"),
            reason=safe_reason,
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        )
        
        # 전송
        self._send_email(user.email, template["subject"], message)
        
        # 알림 로깅 (내용은 저장하지 않음)
        self._log_notification(user.id, logout_type, "email_sent")
    
    def _sanitize_reason(self, reason: str) -> str:
        """민감한 정보 제거"""
        # IP 주소, 사용자 이름 등 제거
        import re
        
        # IP 주소 패턴 제거
        reason = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP_REMOVED]', reason)
        
        # 이메일 주소 제거
        reason = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[EMAIL_REMOVED]', reason)
        
        return reason
```

## 보안 체크리스트

### 구현 시 확인사항

- [ ] 모든 일괄 로그아웃 API는 적절한 권한 검증 구현
- [ ] 긴급 로그아웃은 다단계 인증 필수
- [ ] Rate limiting이 모든 엔드포인트에 적용
- [ ] Dry run 모드가 정상 작동
- [ ] 모든 작업이 감사 로그에 기록
- [ ] 대량 작업 시 확인 메커니즘 작동
- [ ] 알림에 민감한 정보 포함되지 않음
- [ ] 실패 시 롤백 메커니즘 구현
- [ ] SIEM 시스템 연동 (중요 이벤트)
- [ ] 정기적인 감사 보고서 생성

### 보안 테스트

1. **권한 우회 시도**
   - 낮은 권한으로 높은 권한 작업 시도
   - 다른 그룹의 사용자 로그아웃 시도

2. **Rate Limit 테스트**
   - 제한 초과 시 적절한 차단
   - 제한 해제 시간 정확성

3. **대량 작업 보호**
   - Dry run 결과 정확성
   - 확인 코드 검증

4. **감사 로그 완전성**
   - 모든 작업이 로그에 기록
   - 로그 변조 방지

5. **알림 보안**
   - 민감 정보 노출 없음
   - 피싱 방지 메커니즘