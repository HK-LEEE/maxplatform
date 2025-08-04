# 일괄 로그아웃 구현 예제

## 서비스 구현

### BatchLogoutService 전체 구현

```python
# app/services/batch_logout_service.py

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_
import logging

from ..models import User
from ..database import SessionLocal
from .notification_service import NotificationService
from ..utils.auth import permission_checker
from ..config import settings

logger = logging.getLogger(__name__)

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

class BatchLogoutPriority(Enum):
    NORMAL = "normal"
    HIGH = "high"
    IMMEDIATE = "immediate"

class BatchLogoutService:
    def __init__(self):
        self.batch_size = settings.batch_logout_batch_size or 100
        self.notification_service = NotificationService()
        self.processing_jobs: Set[str] = set()
        
    async def create_batch_logout_job(
        self,
        job_type: BatchLogoutType,
        initiated_by: str,
        reason: str,
        conditions: Dict,
        priority: BatchLogoutPriority = BatchLogoutPriority.NORMAL,
        dry_run: bool = False,
        notify_users: bool = True,
        db: Session = None
    ) -> str:
        """일괄 로그아웃 작업 생성"""
        if db is None:
            db = SessionLocal()
            close_db = True
        else:
            close_db = False
            
        try:
            job_id = str(uuid.uuid4())
            
            # 작업 레코드 생성
            db.execute(
                text("""
                    INSERT INTO oauth_batch_logout_jobs 
                    (id, job_type, initiated_by, reason, conditions, priority, dry_run)
                    VALUES (:id, :type, :initiated_by, :reason, :conditions::jsonb, :priority, :dry_run)
                """),
                {
                    "id": job_id,
                    "type": job_type.value,
                    "initiated_by": initiated_by,
                    "reason": reason,
                    "conditions": conditions,
                    "priority": priority.value,
                    "dry_run": dry_run
                }
            )
            db.commit()
            
            # 비동기 처리 시작 (긴급이 아닌 경우)
            if priority != BatchLogoutPriority.IMMEDIATE:
                asyncio.create_task(self._process_batch_logout_job(job_id))
            else:
                # 긴급 처리는 동기적으로 시작
                await self._process_batch_logout_job(job_id)
            
            logger.info(f"Batch logout job created: {job_id} (type: {job_type.value})")
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to create batch logout job: {str(e)}")
            if close_db:
                db.rollback()
            raise
        finally:
            if close_db:
                db.close()
    
    async def _process_batch_logout_job(self, job_id: str):
        """일괄 로그아웃 작업 처리"""
        if job_id in self.processing_jobs:
            logger.warning(f"Job {job_id} is already being processed")
            return
            
        self.processing_jobs.add(job_id)
        db = SessionLocal()
        
        try:
            # 작업 상태를 처리 중으로 변경
            self._update_job_status(job_id, BatchLogoutStatus.PROCESSING, db)
            
            # 작업 정보 로드
            job = self._get_job_details(job_id, db)
            if not job:
                raise ValueError(f"Job {job_id} not found")
            
            # 작업 타입별 처리
            if job['job_type'] == BatchLogoutType.GROUP_BASED.value:
                await self._process_group_based_logout(job_id, job, db)
            elif job['job_type'] == BatchLogoutType.CLIENT_BASED.value:
                await self._process_client_based_logout(job_id, job, db)
            elif job['job_type'] == BatchLogoutType.TIME_BASED.value:
                await self._process_time_based_logout(job_id, job, db)
            elif job['job_type'] == BatchLogoutType.CONDITIONAL.value:
                await self._process_conditional_logout(job_id, job, db)
            elif job['job_type'] == BatchLogoutType.EMERGENCY.value:
                await self._process_emergency_logout(job_id, job, db)
            
        except Exception as e:
            logger.error(f"Failed to process batch logout job {job_id}: {str(e)}")
            self._fail_job(job_id, str(e), db)
        finally:
            self.processing_jobs.discard(job_id)
            db.close()
    
    async def _process_group_based_logout(
        self, 
        job_id: str, 
        job: Dict, 
        db: Session
    ):
        """그룹 기반 로그아웃 처리"""
        conditions = job['conditions']
        dry_run = job['dry_run']
        
        # 영향받을 사용자 조회
        users = self._get_users_by_group(
            conditions['group_id'],
            conditions.get('include_subgroups', False),
            conditions.get('exclude_admin_users', True),
            db
        )
        
        if dry_run:
            # Dry run 모드: 시뮬레이션만
            statistics = self._simulate_logout(users, db)
            self._complete_job(job_id, statistics, db)
            return
        
        # 실제 로그아웃 처리
        total_stats = {
            'users_affected': 0,
            'access_tokens_revoked': 0,
            'refresh_tokens_revoked': 0,
            'sessions_terminated': 0,
            'notifications_sent': 0,
            'errors': []
        }
        
        # 배치 처리
        for i in range(0, len(users), self.batch_size):
            user_batch = users[i:i + self.batch_size]
            
            try:
                # 토큰 해지
                stats = self._revoke_tokens_for_users(
                    [u['id'] for u in user_batch], 
                    db
                )
                
                # 통계 업데이트
                total_stats['users_affected'] += len(user_batch)
                total_stats['access_tokens_revoked'] += stats['access_tokens']
                total_stats['refresh_tokens_revoked'] += stats['refresh_tokens']
                total_stats['sessions_terminated'] += stats['sessions']
                
                # 영향받은 사용자 기록
                self._record_affected_users(job_id, user_batch, stats, db)
                
                # 알림 전송
                if conditions.get('notify_users', True):
                    sent = await self._send_logout_notifications(
                        user_batch, 
                        job['reason'],
                        'group_logout'
                    )
                    total_stats['notifications_sent'] += sent
                
                # 진행률 업데이트
                progress = int((i + len(user_batch)) / len(users) * 100)
                self._update_job_progress(job_id, progress, db)
                
            except Exception as e:
                logger.error(f"Error processing batch {i}: {str(e)}")
                total_stats['errors'].append(str(e))
        
        # 작업 완료
        self._complete_job(job_id, total_stats, db)
    
    def _revoke_tokens_for_users(
        self, 
        user_ids: List[str], 
        db: Session
    ) -> Dict[str, int]:
        """사용자들의 토큰 해지"""
        stats = {
            'access_tokens': 0,
            'refresh_tokens': 0,
            'sessions': 0
        }
        
        if not user_ids:
            return stats
        
        # Access tokens 해지
        result = db.execute(
            text("""
                UPDATE oauth_access_tokens 
                SET revoked_at = NOW() 
                WHERE user_id = ANY(:user_ids) 
                AND revoked_at IS NULL
            """),
            {"user_ids": user_ids}
        )
        stats['access_tokens'] = result.rowcount
        
        # Refresh tokens 해지
        result = db.execute(
            text("""
                UPDATE oauth_refresh_tokens 
                SET revoked_at = NOW() 
                WHERE user_id = ANY(:user_ids) 
                AND revoked_at IS NULL
            """),
            {"user_ids": user_ids}
        )
        stats['refresh_tokens'] = result.rowcount
        
        # Sessions 삭제
        result = db.execute(
            text("""
                DELETE FROM oauth_sessions 
                WHERE user_id = ANY(:user_ids)
            """),
            {"user_ids": user_ids}
        )
        stats['sessions'] = result.rowcount
        
        db.commit()
        return stats
    
    def _record_affected_users(
        self,
        job_id: str,
        users: List[Dict],
        stats: Dict,
        db: Session
    ):
        """영향받은 사용자 기록"""
        for user in users:
            db.execute(
                text("""
                    INSERT INTO oauth_batch_logout_affected_users 
                    (job_id, user_id, access_tokens_revoked, 
                     refresh_tokens_revoked, sessions_terminated, processed_at)
                    VALUES (:job_id, :user_id, :access, :refresh, :sessions, NOW())
                    ON CONFLICT (job_id, user_id) DO UPDATE SET
                        access_tokens_revoked = EXCLUDED.access_tokens_revoked,
                        refresh_tokens_revoked = EXCLUDED.refresh_tokens_revoked,
                        sessions_terminated = EXCLUDED.sessions_terminated,
                        processed_at = NOW()
                """),
                {
                    "job_id": job_id,
                    "user_id": user['id'],
                    "access": stats['access_tokens'] // len(users),  # 평균값
                    "refresh": stats['refresh_tokens'] // len(users),
                    "sessions": stats['sessions'] // len(users)
                }
            )
        db.commit()
    
    def cancel_job(self, job_id: str, cancelled_by: str, db: Session) -> bool:
        """작업 취소"""
        result = db.execute(
            text("SELECT cancel_batch_logout_job(:job_id, :cancelled_by)"),
            {"job_id": job_id, "cancelled_by": cancelled_by}
        ).scalar()
        
        if result:
            logger.info(f"Batch logout job {job_id} cancelled by {cancelled_by}")
            # 처리 중인 작업에서 제거
            self.processing_jobs.discard(job_id)
        
        return result
    
    def get_job_status(self, job_id: str, db: Session) -> Optional[Dict]:
        """작업 상태 조회"""
        result = db.execute(
            text("""
                SELECT 
                    j.*,
                    u.email as initiated_by_email,
                    u.display_name as initiated_by_name,
                    get_batch_logout_statistics(j.id) as statistics
                FROM oauth_batch_logout_jobs j
                JOIN users u ON j.initiated_by = u.id
                WHERE j.id = :job_id
            """),
            {"job_id": job_id}
        ).first()
        
        if result:
            return {
                "job_id": str(result.id),
                "type": result.job_type,
                "status": result.status,
                "priority": result.priority,
                "dry_run": result.dry_run,
                "progress": result.progress,
                "initiated_by": {
                    "id": str(result.initiated_by),
                    "email": result.initiated_by_email,
                    "name": result.initiated_by_name
                },
                "reason": result.reason,
                "conditions": result.conditions,
                "statistics": result.statistics._asdict() if result.statistics else None,
                "error_details": result.error_details,
                "created_at": result.created_at,
                "started_at": result.started_at,
                "completed_at": result.completed_at,
                "cancelled_at": result.cancelled_at
            }
        
        return None
    
    # Helper methods
    def _update_job_status(
        self, 
        job_id: str, 
        status: BatchLogoutStatus, 
        db: Session
    ):
        """작업 상태 업데이트"""
        update_fields = {"status": status.value}
        
        if status == BatchLogoutStatus.PROCESSING:
            update_fields["started_at"] = datetime.utcnow()
        elif status in [BatchLogoutStatus.COMPLETED, BatchLogoutStatus.FAILED]:
            update_fields["completed_at"] = datetime.utcnow()
        
        set_clause = ", ".join([f"{k} = :{k}" for k in update_fields.keys()])
        
        db.execute(
            text(f"UPDATE oauth_batch_logout_jobs SET {set_clause} WHERE id = :job_id"),
            {**update_fields, "job_id": job_id}
        )
        db.commit()
    
    def _complete_job(self, job_id: str, statistics: Dict, db: Session):
        """작업 완료 처리"""
        db.execute(
            text("""
                UPDATE oauth_batch_logout_jobs 
                SET status = 'completed', 
                    completed_at = NOW(), 
                    statistics = :statistics::jsonb,
                    progress = 100
                WHERE id = :job_id
            """),
            {"job_id": job_id, "statistics": statistics}
        )
        db.commit()
        logger.info(f"Batch logout job {job_id} completed: {statistics}")
    
    def _fail_job(self, job_id: str, error: str, db: Session):
        """작업 실패 처리"""
        db.execute(
            text("""
                UPDATE oauth_batch_logout_jobs 
                SET status = 'failed', 
                    completed_at = NOW(), 
                    error_details = :error::jsonb
                WHERE id = :job_id
            """),
            {"job_id": job_id, "error": {"error": error, "timestamp": str(datetime.utcnow())}}
        )
        db.commit()
        logger.error(f"Batch logout job {job_id} failed: {error}")

# 싱글톤 인스턴스
batch_logout_service = BatchLogoutService()
```

## API Router 구현

```python
# app/routers/batch_logout.py

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Optional, Dict, List
from datetime import datetime

from ..database import get_db
from ..models import User
from ..services.batch_logout_service import (
    batch_logout_service, 
    BatchLogoutType,
    BatchLogoutPriority,
    permission_checker
)
from ..utils.auth import get_current_user
from ..schemas.batch_logout import (
    BatchLogoutJobCreate,
    BatchLogoutJobResponse,
    GroupLogoutRequest,
    ClientLogoutRequest,
    TimeBasedLogoutRequest,
    ConditionalLogoutRequest,
    EmergencyLogoutRequest,
    BatchLogoutJobStatus
)

router = APIRouter(
    prefix="/api/admin/oauth/batch-logout",
    tags=["Batch Logout"],
    dependencies=[Depends(get_current_user)]
)

@router.post("/group", response_model=BatchLogoutJobResponse)
@permission_checker.require_permission(BatchLogoutPermission.EXECUTE_GROUP_LOGOUT)
async def create_group_logout(
    request: GroupLogoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 기반 일괄 로그아웃"""
    # Rate limit 확인
    rate_limiter.check_rate_limit(
        str(current_user.id), 
        BatchLogoutType.GROUP_BASED, 
        db
    )
    
    # Dry run 시 시뮬레이션
    if request.dry_run:
        simulation = batch_logout_service.simulate_group_logout(
            request.group_id,
            request.include_subgroups,
            request.exclude_admin_users,
            db
        )
        return BatchLogoutJobResponse(
            job_id="dry-run",
            status="simulation",
            estimated_affected_users=simulation['affected_users'],
            estimated_affected_tokens=simulation['total_tokens']
        )
    
    # 작업 생성
    job_id = await batch_logout_service.create_batch_logout_job(
        job_type=BatchLogoutType.GROUP_BASED,
        initiated_by=str(current_user.id),
        reason=request.reason,
        conditions={
            "group_id": request.group_id,
            "include_subgroups": request.include_subgroups,
            "exclude_admin_users": request.exclude_admin_users,
            "notify_users": request.notify_users
        },
        dry_run=False,
        db=db
    )
    
    # 감사 로그
    log_batch_logout_action(
        "group_logout_initiated",
        job_id=job_id,
        user_id=str(current_user.id),
        details={
            "group_id": request.group_id,
            "reason": request.reason
        },
        db=db
    )
    
    return BatchLogoutJobResponse(
        job_id=job_id,
        status="processing",
        message="Group logout job created successfully"
    )

@router.post("/emergency", response_model=BatchLogoutJobResponse)
@permission_checker.require_permission(BatchLogoutPermission.EXECUTE_EMERGENCY_LOGOUT)
async def create_emergency_logout(
    request: EmergencyLogoutRequest,
    emergency_key: str = Header(None, alias="X-Emergency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """긴급 전체 로그아웃"""
    # 긴급 키 검증
    if not emergency_auth_service.verify_emergency_key(
        str(current_user.id), 
        emergency_key
    ):
        raise HTTPException(status_code=403, detail="Invalid emergency key")
    
    # 확인 코드 검증
    if request.confirm != "LOGOUT_ALL_USERS":
        raise HTTPException(
            status_code=400, 
            detail="Please confirm with: LOGOUT_ALL_USERS"
        )
    
    # 긴급 로그아웃 실행
    job_id = await batch_logout_service.create_batch_logout_job(
        job_type=BatchLogoutType.EMERGENCY,
        initiated_by=str(current_user.id),
        reason=request.reason,
        conditions={
            "exclude_admin_sessions": request.exclude_admin_sessions,
            "preserve_service_tokens": request.preserve_service_tokens,
            "authorized_by": request.authorized_by
        },
        priority=BatchLogoutPriority.IMMEDIATE,
        dry_run=False,
        notify_users=False,  # 긴급 상황에서는 별도 알림
        db=db
    )
    
    # 긴급 감사 로그
    log_batch_logout_action(
        "emergency_logout_initiated",
        job_id=job_id,
        user_id=str(current_user.id),
        details={
            "reason": request.reason,
            "authorized_by": request.authorized_by
        },
        level=BatchLogoutAuditLevel.CRITICAL,
        db=db
    )
    
    # 보안 팀 즉시 알림
    send_security_alert(
        "Emergency logout initiated",
        {
            "job_id": job_id,
            "initiated_by": current_user.email,
            "reason": request.reason
        }
    )
    
    return BatchLogoutJobResponse(
        job_id=job_id,
        status="processing",
        priority="immediate",
        message="Emergency logout initiated"
    )

@router.get("/jobs/{job_id}", response_model=BatchLogoutJobStatus)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """작업 상태 조회"""
    job_status = batch_logout_service.get_job_status(job_id, db)
    
    if not job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return BatchLogoutJobStatus(**job_status)

@router.delete("/jobs/{job_id}")
@permission_checker.require_permission(BatchLogoutPermission.CANCEL_BATCH_LOGOUT)
async def cancel_job(
    job_id: str,
    reason: str = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """작업 취소"""
    success = batch_logout_service.cancel_job(
        job_id, 
        str(current_user.id), 
        db
    )
    
    if not success:
        raise HTTPException(
            status_code=400, 
            detail="Job cannot be cancelled (already completed or not found)"
        )
    
    # 감사 로그
    log_batch_logout_action(
        "batch_logout_cancelled",
        job_id=job_id,
        user_id=str(current_user.id),
        details={"reason": reason},
        db=db
    )
    
    return {"message": "Job cancelled successfully"}

@router.get("/jobs", response_model=List[BatchLogoutJobStatus])
async def list_jobs(
    status: Optional[str] = None,
    job_type: Optional[str] = None,
    initiated_by: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """작업 목록 조회"""
    # 권한에 따른 필터링
    query = "SELECT * FROM oauth_batch_logout_jobs WHERE 1=1"
    params = {}
    
    # 일반 사용자는 자신이 생성한 작업만 조회
    if not current_user.is_admin:
        query += " AND initiated_by = :user_id"
        params["user_id"] = str(current_user.id)
    elif initiated_by:
        query += " AND initiated_by = :initiated_by"
        params["initiated_by"] = initiated_by
    
    if status:
        query += " AND status = :status"
        params["status"] = status
    
    if job_type:
        query += " AND job_type = :job_type"
        params["job_type"] = job_type
    
    query += " ORDER BY created_at DESC LIMIT :limit OFFSET :skip"
    params["limit"] = limit
    params["skip"] = skip
    
    result = db.execute(text(query), params)
    
    jobs = []
    for row in result:
        job_status = batch_logout_service.get_job_status(str(row.id), db)
        if job_status:
            jobs.append(BatchLogoutJobStatus(**job_status))
    
    return jobs

@router.post("/request-emergency-key")
async def request_emergency_key(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """긴급 키 요청"""
    # 권한 확인
    if not permission_checker.has_permission(
        current_user, 
        BatchLogoutPermission.EXECUTE_EMERGENCY_LOGOUT
    ):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # 긴급 키 생성 및 전송
    result = emergency_auth_service.generate_emergency_key(
        str(current_user.id), 
        db
    )
    
    return {"message": result}
```

## Pydantic Schemas

```python
# app/schemas/batch_logout.py

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum

class GroupLogoutRequest(BaseModel):
    group_id: str = Field(..., description="Target group ID")
    include_subgroups: bool = Field(False, description="Include subgroups")
    exclude_admin_users: bool = Field(True, description="Exclude admin users")
    reason: str = Field(..., min_length=10, description="Reason for logout")
    notify_users: bool = Field(True, description="Send notifications to users")
    dry_run: bool = Field(False, description="Simulate without actual logout")

class ClientLogoutRequest(BaseModel):
    client_id: str = Field(..., description="OAuth client ID")
    revoke_refresh_tokens: bool = Field(True, description="Also revoke refresh tokens")
    reason: str = Field(..., min_length=10, description="Reason for logout")
    created_before: Optional[datetime] = Field(None, description="Only tokens created before this time")
    dry_run: bool = Field(False, description="Simulate without actual logout")

class TimeBasedLogoutRequest(BaseModel):
    created_before: Optional[datetime] = Field(None, description="Tokens created before")
    last_used_before: Optional[datetime] = Field(None, description="Tokens last used before")
    token_types: List[str] = Field(["access_token", "refresh_token"], description="Token types to revoke")
    reason: str = Field(..., min_length=10, description="Reason for logout")
    dry_run: bool = Field(False, description="Simulate without actual logout")
    
    @validator('token_types')
    def validate_token_types(cls, v):
        valid_types = {"access_token", "refresh_token"}
        if not all(t in valid_types for t in v):
            raise ValueError("Invalid token type")
        return v

class ConditionalLogoutRequest(BaseModel):
    conditions: Dict[str, Any] = Field(..., description="Logout conditions")
    reason: str = Field(..., min_length=10, description="Reason for logout")
    dry_run: bool = Field(True, description="Default to dry run for safety")

class EmergencyLogoutRequest(BaseModel):
    confirm: str = Field(..., description="Confirmation code: LOGOUT_ALL_USERS")
    exclude_admin_sessions: bool = Field(True, description="Preserve admin sessions")
    preserve_service_tokens: bool = Field(True, description="Preserve service tokens")
    reason: str = Field(..., min_length=20, description="Detailed reason for emergency logout")
    authorized_by: str = Field(..., description="Authorization source (e.g., security-team)")

class BatchLogoutJobResponse(BaseModel):
    job_id: str
    status: str
    priority: Optional[str] = None
    estimated_affected_users: Optional[int] = None
    estimated_affected_tokens: Optional[int] = None
    estimated_completion: Optional[datetime] = None
    message: Optional[str] = None

class BatchLogoutJobStatus(BaseModel):
    job_id: str
    type: str
    status: str
    priority: str
    dry_run: bool
    progress: int
    initiated_by: Dict[str, str]
    reason: str
    conditions: Dict[str, Any]
    statistics: Optional[Dict[str, Any]] = None
    error_details: Optional[Dict[str, Any]] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
```

## 테스트 예제

```python
# tests/test_batch_logout.py

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.services.batch_logout_service import BatchLogoutService, BatchLogoutType
from app.models import User, Group, OAuthClient

@pytest.fixture
def batch_logout_service():
    return BatchLogoutService()

@pytest.fixture
def test_data(db: Session):
    """테스트 데이터 생성"""
    # 그룹 생성
    group = Group(name="test_group")
    db.add(group)
    
    # 사용자 생성
    users = []
    for i in range(10):
        user = User(
            email=f"user{i}@test.com",
            group_id=group.id,
            is_admin=i == 0  # 첫 번째 사용자는 관리자
        )
        db.add(user)
        users.append(user)
    
    # OAuth 클라이언트 생성
    client = OAuthClient(
        client_id="test-client",
        client_name="Test Client"
    )
    db.add(client)
    
    db.commit()
    
    # 토큰 생성
    for user in users:
        # Access tokens
        for j in range(3):
            db.execute(
                text("""
                    INSERT INTO oauth_access_tokens 
                    (user_id, client_id, token_hash, expires_at)
                    VALUES (:user_id, :client_id, :hash, :expires)
                """),
                {
                    "user_id": user.id,
                    "client_id": client.client_id,
                    "hash": f"hash_{user.id}_{j}",
                    "expires": datetime.utcnow() + timedelta(hours=1)
                }
            )
    
    db.commit()
    
    return {
        "group": group,
        "users": users,
        "client": client
    }

class TestBatchLogout:
    def test_group_logout_dry_run(
        self, 
        batch_logout_service: BatchLogoutService,
        test_data: Dict,
        db: Session
    ):
        """그룹 로그아웃 dry run 테스트"""
        job_id = asyncio.run(
            batch_logout_service.create_batch_logout_job(
                job_type=BatchLogoutType.GROUP_BASED,
                initiated_by=str(test_data['users'][0].id),
                reason="Test group logout",
                conditions={
                    "group_id": str(test_data['group'].id),
                    "include_subgroups": False,
                    "exclude_admin_users": True
                },
                dry_run=True,
                db=db
            )
        )
        
        # 작업 완료 대기
        asyncio.run(asyncio.sleep(2))
        
        # 결과 확인
        job_status = batch_logout_service.get_job_status(job_id, db)
        assert job_status['status'] == 'completed'
        assert job_status['statistics']['users_affected'] == 9  # 관리자 제외
        
        # 실제로 토큰이 해지되지 않았는지 확인
        active_tokens = db.execute(
            text("SELECT COUNT(*) FROM oauth_access_tokens WHERE revoked_at IS NULL")
        ).scalar()
        assert active_tokens > 0
    
    def test_emergency_logout(
        self,
        client: TestClient,
        admin_user: User,
        db: Session
    ):
        """긴급 로그아웃 API 테스트"""
        # 긴급 키 요청
        response = client.post(
            "/api/admin/oauth/batch-logout/request-emergency-key",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        # 긴급 키 가져오기 (테스트용)
        emergency_key = "123456"  # 실제로는 Redis에서 가져옴
        
        # 긴급 로그아웃 실행
        response = client.post(
            "/api/admin/oauth/batch-logout/emergency",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Emergency-Key": emergency_key
            },
            json={
                "confirm": "LOGOUT_ALL_USERS",
                "exclude_admin_sessions": True,
                "preserve_service_tokens": True,
                "reason": "Security breach detected in test",
                "authorized_by": "test-security-team"
            }
        )
        
        assert response.status_code == 200
        job_data = response.json()
        assert job_data['priority'] == 'immediate'
        
        # 토큰이 해지되었는지 확인
        active_tokens = db.execute(
            text("""
                SELECT COUNT(*) FROM oauth_access_tokens 
                WHERE revoked_at IS NULL 
                AND user_id NOT IN (SELECT id FROM users WHERE is_admin = true)
            """)
        ).scalar()
        assert active_tokens == 0
```

이로써 일괄 로그아웃 기능의 설계와 구현 예제가 완성되었습니다. 주요 특징:

1. **다양한 로그아웃 유형**: 그룹, 클라이언트, 시간, 조건부, 긴급
2. **강력한 보안**: 권한 검증, 긴급 키, Rate limiting
3. **안전장치**: Dry run, 확인 메커니즘, 관리자 제외
4. **완전한 감사**: 모든 작업 로깅, 통계, 보고서
5. **성능 최적화**: 배치 처리, 비동기 실행, 진행률 추적