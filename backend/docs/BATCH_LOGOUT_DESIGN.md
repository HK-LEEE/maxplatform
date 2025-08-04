# MAX Platform 일괄 로그아웃 기능 설계

## 개요

MAX Platform의 보안 강화 및 관리 효율성 향상을 위해 일괄 로그아웃 기능을 설계합니다. 이 기능은 관리자가 특정 조건에 맞는 여러 사용자의 세션을 한번에 종료할 수 있게 합니다.

## 설계 원칙

1. **보안 우선**: 모든 일괄 로그아웃 작업은 감사 로그에 기록되며, 강력한 권한 검증 필요
2. **점진적 처리**: 대량 작업 시 시스템 부하를 방지하기 위한 배치 처리
3. **투명성**: 영향받는 사용자에게 적절한 통지
4. **복구 가능성**: 실수로 인한 대량 로그아웃 시 빠른 파악 가능
5. **표준 준수**: OAuth 2.0 토큰 해지 표준 준수

## 기능 요구사항

### 1. 그룹 기반 일괄 로그아웃
- 특정 그룹의 모든 사용자 세션 종료
- 하위 그룹 포함 옵션

### 2. 클라이언트 기반 일괄 로그아웃
- 특정 OAuth 클라이언트의 모든 세션 종료
- 보안 사고 시 특정 애플리케이션 접근 차단

### 3. 시간 기반 일괄 로그아웃
- 특정 시간 이전에 생성된 모든 토큰 해지
- 장기 미사용 세션 정리

### 4. 조건부 일괄 로그아웃
- 복합 조건(그룹 + 시간, 클라이언트 + 그룹 등) 지원
- 유연한 필터링 옵션

### 5. 긴급 전체 로그아웃
- 보안 사고 시 모든 활성 세션 즉시 종료
- 시스템 관리자 세션 제외 옵션

## API 설계

### 1. 그룹 기반 일괄 로그아웃

```http
POST /api/admin/oauth/batch-logout/group
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "group_id": "uuid",
  "include_subgroups": true,
  "reason": "Security policy update",
  "notify_users": true,
  "exclude_admin_users": true
}

Response:
{
  "job_id": "batch-logout-job-123",
  "status": "processing",
  "estimated_affected_users": 150,
  "estimated_affected_tokens": 450
}
```

### 2. 클라이언트 기반 일괄 로그아웃

```http
POST /api/admin/oauth/batch-logout/client
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "client_id": "vulnerable-app-v1",
  "revoke_refresh_tokens": true,
  "reason": "Security vulnerability in client application",
  "created_before": "2025-01-29T00:00:00Z"
}

Response:
{
  "job_id": "batch-logout-job-124",
  "status": "processing",
  "affected_sessions": 75,
  "affected_tokens": 150
}
```

### 3. 시간 기반 일괄 로그아웃

```http
POST /api/admin/oauth/batch-logout/time-based
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "created_before": "2025-01-15T00:00:00Z",
  "last_used_before": "2025-01-20T00:00:00Z",
  "token_types": ["access_token", "refresh_token"],
  "reason": "Cleanup inactive sessions"
}

Response:
{
  "job_id": "batch-logout-job-125",
  "status": "completed",
  "revoked_access_tokens": 320,
  "revoked_refresh_tokens": 280,
  "affected_users": 95
}
```

### 4. 조건부 일괄 로그아웃

```http
POST /api/admin/oauth/batch-logout/conditional
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "conditions": {
    "groups": ["developers", "contractors"],
    "clients": ["mobile-app-v1", "web-app-v1"],
    "created_after": "2025-01-25T00:00:00Z",
    "ip_ranges": ["192.168.1.0/24"],
    "exclude_users": ["admin-uuid-1", "admin-uuid-2"]
  },
  "reason": "Security audit requirement",
  "dry_run": true
}

Response:
{
  "job_id": "batch-logout-job-126",
  "status": "dry_run_completed",
  "would_affect": {
    "users": 45,
    "access_tokens": 120,
    "refresh_tokens": 45,
    "sessions": 60
  }
}
```

### 5. 긴급 전체 로그아웃

```http
POST /api/admin/oauth/batch-logout/emergency
Authorization: Bearer {admin_token}
X-Emergency-Key: {emergency_key}
Content-Type: application/json

{
  "confirm": "LOGOUT_ALL_USERS",
  "exclude_admin_sessions": true,
  "preserve_service_tokens": true,
  "reason": "Critical security breach detected",
  "authorized_by": "security-team"
}

Response:
{
  "job_id": "emergency-logout-job-001",
  "status": "processing",
  "priority": "immediate",
  "estimated_completion": "2025-01-29T10:15:00Z"
}
```

### 6. 일괄 로그아웃 작업 상태 조회

```http
GET /api/admin/oauth/batch-logout/jobs/{job_id}
Authorization: Bearer {admin_token}

Response:
{
  "job_id": "batch-logout-job-123",
  "type": "group_based",
  "status": "completed",
  "created_at": "2025-01-29T10:00:00Z",
  "completed_at": "2025-01-29T10:02:35Z",
  "initiated_by": "admin@maxplatform.com",
  "reason": "Security policy update",
  "statistics": {
    "total_users_affected": 150,
    "access_tokens_revoked": 420,
    "refresh_tokens_revoked": 150,
    "sessions_terminated": 180,
    "notifications_sent": 150,
    "errors": 0
  },
  "progress": 100
}
```

## 데이터베이스 스키마

### 1. 일괄 로그아웃 작업 테이블

```sql
CREATE TABLE oauth_batch_logout_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type VARCHAR(50) NOT NULL, -- group_based, client_based, time_based, conditional, emergency
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending, processing, completed, failed, cancelled
    initiated_by UUID NOT NULL REFERENCES users(id),
    reason TEXT NOT NULL,
    conditions JSONB NOT NULL, -- 작업 조건 저장
    statistics JSONB, -- 결과 통계
    error_details JSONB, -- 오류 정보
    dry_run BOOLEAN DEFAULT false,
    priority VARCHAR(20) DEFAULT 'normal', -- normal, high, immediate
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    INDEX idx_batch_logout_status (status, created_at),
    INDEX idx_batch_logout_type (job_type, status)
);

-- 영향받은 사용자 추적
CREATE TABLE oauth_batch_logout_affected_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES oauth_batch_logout_jobs(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    tokens_revoked INTEGER DEFAULT 0,
    sessions_terminated INTEGER DEFAULT 0,
    notification_sent BOOLEAN DEFAULT false,
    notification_sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(job_id, user_id),
    INDEX idx_affected_users_job (job_id),
    INDEX idx_affected_users_user (user_id)
);
```

### 2. 감사 로그 확장

```sql
-- oauth_audit_logs 테이블에 batch_logout 관련 action 추가
-- action: 'batch_logout_initiated', 'batch_logout_completed', 'batch_logout_failed'
-- metadata 필드에 job_id와 상세 정보 저장
```

## 구현 상세

### 1. BatchLogoutService

```python
from typing import Dict, List, Optional, Set
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
import uuid
import asyncio
from enum import Enum

class BatchLogoutType(Enum):
    GROUP_BASED = "group_based"
    CLIENT_BASED = "client_based"
    TIME_BASED = "time_based"
    CONDITIONAL = "conditional"
    EMERGENCY = "emergency"

class BatchLogoutStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class BatchLogoutService:
    def __init__(self):
        self.batch_size = 100  # 한 번에 처리할 토큰 수
        self.notification_service = NotificationService()
        
    async def create_group_logout_job(
        self,
        group_id: str,
        include_subgroups: bool,
        reason: str,
        initiated_by: str,
        notify_users: bool,
        exclude_admin_users: bool,
        db: Session
    ) -> str:
        """그룹 기반 일괄 로그아웃 작업 생성"""
        # 영향받을 사용자 예상
        affected_users = self._estimate_affected_users_by_group(
            group_id, include_subgroups, exclude_admin_users, db
        )
        
        # 작업 생성
        job_id = str(uuid.uuid4())
        conditions = {
            "group_id": group_id,
            "include_subgroups": include_subgroups,
            "exclude_admin_users": exclude_admin_users,
            "notify_users": notify_users
        }
        
        db.execute(
            text("""
                INSERT INTO oauth_batch_logout_jobs 
                (id, job_type, initiated_by, reason, conditions)
                VALUES (:id, :type, :initiated_by, :reason, :conditions)
            """),
            {
                "id": job_id,
                "type": BatchLogoutType.GROUP_BASED.value,
                "initiated_by": initiated_by,
                "reason": reason,
                "conditions": conditions
            }
        )
        db.commit()
        
        # 비동기 처리 시작
        asyncio.create_task(self._process_group_logout(job_id, db))
        
        return job_id
    
    async def _process_group_logout(self, job_id: str, db: Session):
        """그룹 로그아웃 처리"""
        try:
            # 작업 상태 업데이트
            self._update_job_status(job_id, BatchLogoutStatus.PROCESSING, db)
            
            # 조건 로드
            job = self._get_job(job_id, db)
            conditions = job['conditions']
            
            # 영향받을 사용자 조회
            users = self._get_users_by_group(
                conditions['group_id'],
                conditions['include_subgroups'],
                conditions['exclude_admin_users'],
                db
            )
            
            # 배치 처리
            total_tokens_revoked = 0
            total_sessions_terminated = 0
            
            for user_batch in self._batch_users(users, self.batch_size):
                tokens_revoked, sessions_terminated = self._revoke_user_batch_tokens(
                    user_batch, db
                )
                total_tokens_revoked += tokens_revoked
                total_sessions_terminated += sessions_terminated
                
                # 영향받은 사용자 기록
                self._record_affected_users(job_id, user_batch, db)
                
                # 알림 전송
                if conditions['notify_users']:
                    await self._notify_users(user_batch, job['reason'])
                
                # 진행률 업데이트
                self._update_job_progress(job_id, len(user_batch), db)
            
            # 완료 처리
            statistics = {
                "total_users_affected": len(users),
                "access_tokens_revoked": total_tokens_revoked,
                "refresh_tokens_revoked": total_sessions_terminated,
                "notifications_sent": len(users) if conditions['notify_users'] else 0
            }
            
            self._complete_job(job_id, statistics, db)
            
        except Exception as e:
            self._fail_job(job_id, str(e), db)
            raise
    
    def create_emergency_logout(
        self,
        initiated_by: str,
        reason: str,
        exclude_admin_sessions: bool,
        preserve_service_tokens: bool,
        db: Session
    ) -> str:
        """긴급 전체 로그아웃"""
        # 즉시 모든 토큰 해지 시작
        job_id = str(uuid.uuid4())
        
        # 높은 우선순위로 작업 생성
        db.execute(
            text("""
                INSERT INTO oauth_batch_logout_jobs 
                (id, job_type, initiated_by, reason, conditions, priority)
                VALUES (:id, :type, :initiated_by, :reason, :conditions, 'immediate')
            """),
            {
                "id": job_id,
                "type": BatchLogoutType.EMERGENCY.value,
                "initiated_by": initiated_by,
                "reason": reason,
                "conditions": {
                    "exclude_admin_sessions": exclude_admin_sessions,
                    "preserve_service_tokens": preserve_service_tokens
                }
            }
        )
        
        # 즉시 실행 (비동기 아님)
        self._execute_emergency_logout(
            exclude_admin_sessions,
            preserve_service_tokens,
            db
        )
        
        db.commit()
        return job_id
    
    def _execute_emergency_logout(
        self,
        exclude_admin_sessions: bool,
        preserve_service_tokens: bool,
        db: Session
    ):
        """긴급 로그아웃 실행"""
        # Access tokens 해지
        query = "UPDATE oauth_access_tokens SET revoked_at = NOW() WHERE revoked_at IS NULL"
        params = {}
        
        if exclude_admin_sessions:
            query += " AND user_id NOT IN (SELECT id FROM users WHERE is_admin = true)"
        
        if preserve_service_tokens:
            query += " AND user_id IS NOT NULL"  # 서비스 토큰은 user_id가 NULL
        
        result = db.execute(text(query), params)
        access_tokens_revoked = result.rowcount
        
        # Refresh tokens 해지
        query = "UPDATE oauth_refresh_tokens SET revoked_at = NOW() WHERE revoked_at IS NULL"
        
        if exclude_admin_sessions:
            query += " AND user_id NOT IN (SELECT id FROM users WHERE is_admin = true)"
        
        result = db.execute(text(query), params)
        refresh_tokens_revoked = result.rowcount
        
        # OAuth sessions 삭제
        query = "DELETE FROM oauth_sessions WHERE 1=1"
        
        if exclude_admin_sessions:
            query += " AND user_id NOT IN (SELECT id FROM users WHERE is_admin = true)"
        
        result = db.execute(text(query), params)
        sessions_terminated = result.rowcount
        
        logger.warning(
            f"Emergency logout executed: "
            f"{access_tokens_revoked} access tokens, "
            f"{refresh_tokens_revoked} refresh tokens revoked, "
            f"{sessions_terminated} sessions terminated"
        )

batch_logout_service = BatchLogoutService()
```

## 보안 고려사항

### 1. 권한 검증
- 일괄 로그아웃은 `admin:oauth` 권한 필요
- 긴급 로그아웃은 추가 비상 키 필요
- 모든 작업은 감사 로그에 기록

### 2. 실수 방지
- Dry run 모드 지원
- 영향받을 사용자 수 사전 확인
- 관리자 세션 제외 옵션
- 작업 취소 기능

### 3. 성능 고려
- 배치 처리로 DB 부하 분산
- 비동기 처리로 응답 지연 방지
- 진행률 추적 가능

### 4. 알림 시스템
- 영향받는 사용자에게 이메일/SMS 알림
- 로그아웃 사유 설명
- 재로그인 안내

## 구현 우선순위

1. **Phase 1**: 기본 기능 구현
   - 그룹 기반 일괄 로그아웃
   - 작업 상태 조회 API
   - 감사 로깅

2. **Phase 2**: 확장 기능
   - 클라이언트 기반 로그아웃
   - 시간 기반 로그아웃
   - Dry run 모드

3. **Phase 3**: 고급 기능
   - 조건부 로그아웃
   - 긴급 로그아웃
   - 알림 시스템 통합

## 테스트 계획

### 1. 단위 테스트
- 각 로그아웃 유형별 로직 테스트
- 권한 검증 테스트
- 에러 처리 테스트

### 2. 통합 테스트
- 대량 데이터 처리 테스트
- 동시성 테스트
- 성능 테스트

### 3. 시나리오 테스트
- 보안 사고 대응 시나리오
- 실수 복구 시나리오
- 부분 실패 처리 시나리오