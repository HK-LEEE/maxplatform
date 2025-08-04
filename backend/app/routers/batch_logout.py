#%%
from fastapi import APIRouter, Depends, HTTPException, Body, Header, Request
from sqlalchemy.orm import Session
from typing import Optional, Dict, List
from datetime import datetime
import logging

from ..database import get_db
from ..models import User
from ..services.batch_logout_service import (
    batch_logout_service, 
    BatchLogoutType,
    BatchLogoutPriority
)
from ..utils.auth import get_current_user
from ..middleware.security import (
    BatchLogoutPermission,
    RateLimitType,
    require_batch_logout_permission,
    batch_logout_rate_limit,
    audit_batch_logout_action,
    require_emergency_auth
)
from ..schemas.batch_logout import (
    BatchLogoutJobResponse,
    GroupLogoutRequest,
    ClientLogoutRequest,
    TimeBasedLogoutRequest,
    ConditionalLogoutRequest,
    EmergencyLogoutRequest,
    BatchLogoutJobStatus,
    UserLogoutRequest,
    UserLogoutResponse,
    UserSessionInfo,
    UserSessionsResponse,
    SessionLogoutRequest,
    SessionLogoutResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/admin/oauth/batch-logout",
    tags=["Batch Logout"],
    dependencies=[Depends(get_current_user)]
)

# 사용자 세션 관리용 라우터 (별도)
user_session_router = APIRouter(
    prefix="/api/user/sessions",
    tags=["User Sessions"],
    dependencies=[Depends(get_current_user)]
)

@router.post("/group", response_model=BatchLogoutJobResponse)
@require_batch_logout_permission(BatchLogoutPermission.EXECUTE_GROUP_LOGOUT)
@batch_logout_rate_limit(RateLimitType.GROUP_LOGOUT)
@audit_batch_logout_action("group_logout_initiated")
async def create_group_logout(
    request: GroupLogoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """그룹 기반 일괄 로그아웃"""
    
    # Dry run 시 시뮬레이션
    if request.dry_run:
        # 영향받을 사용자 수 계산
        users = batch_logout_service._get_users_by_group(
            request.group_id,
            request.include_subgroups,
            request.exclude_admin_users,
            db
        )
        simulation = batch_logout_service._simulate_logout(users, db)
        
        return BatchLogoutJobResponse(
            job_id="dry-run",
            status="simulation",
            estimated_affected_users=simulation['users_affected'],
            estimated_affected_tokens=simulation['access_tokens_revoked'] + simulation['refresh_tokens_revoked'],
            message=f"Simulation: Would affect {simulation['users_affected']} users"
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
    
    logger.info(f"Group logout job created: {job_id} by user {current_user.email}")
    
    return BatchLogoutJobResponse(
        job_id=job_id,
        status="processing",
        message="Group logout job created successfully"
    )

@router.post("/client", response_model=BatchLogoutJobResponse)
@require_batch_logout_permission(BatchLogoutPermission.EXECUTE_CLIENT_LOGOUT)
@batch_logout_rate_limit(RateLimitType.CLIENT_LOGOUT)
@audit_batch_logout_action("client_logout_initiated")
async def create_client_logout(
    request: ClientLogoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """클라이언트 기반 일괄 로그아웃"""
    
    job_id = await batch_logout_service.create_batch_logout_job(
        job_type=BatchLogoutType.CLIENT_BASED,
        initiated_by=str(current_user.id),
        reason=request.reason,
        conditions={
            "client_id": request.client_id,
            "revoke_refresh_tokens": request.revoke_refresh_tokens,
            "created_before": request.created_before.isoformat() if request.created_before else None
        },
        dry_run=request.dry_run,
        db=db
    )
    
    return BatchLogoutJobResponse(
        job_id=job_id,
        status="processing",
        message="Client logout job created successfully"
    )

@router.post("/time-based", response_model=BatchLogoutJobResponse)
@require_batch_logout_permission(BatchLogoutPermission.EXECUTE_TIME_LOGOUT)
@batch_logout_rate_limit(RateLimitType.TIME_LOGOUT)
@audit_batch_logout_action("time_based_logout_initiated")
async def create_time_based_logout(
    request: TimeBasedLogoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """시간 기반 일괄 로그아웃"""
    
    job_id = await batch_logout_service.create_batch_logout_job(
        job_type=BatchLogoutType.TIME_BASED,
        initiated_by=str(current_user.id),
        reason=request.reason,
        conditions={
            "created_before": request.created_before.isoformat() if request.created_before else None,
            "last_used_before": request.last_used_before.isoformat() if request.last_used_before else None,
            "token_types": request.token_types
        },
        dry_run=request.dry_run,
        db=db
    )
    
    return BatchLogoutJobResponse(
        job_id=job_id,
        status="processing",
        message="Time-based logout job created successfully"
    )

@router.post("/conditional", response_model=BatchLogoutJobResponse)
@require_batch_logout_permission(BatchLogoutPermission.EXECUTE_CONDITIONAL_LOGOUT)
@batch_logout_rate_limit(RateLimitType.CONDITIONAL_LOGOUT)
@audit_batch_logout_action("conditional_logout_initiated", sensitive=True)
async def create_conditional_logout(
    request: ConditionalLogoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """조건부 일괄 로그아웃"""
    
    job_id = await batch_logout_service.create_batch_logout_job(
        job_type=BatchLogoutType.CONDITIONAL,
        initiated_by=str(current_user.id),
        reason=request.reason,
        conditions=request.conditions,
        dry_run=request.dry_run,
        db=db
    )
    
    return BatchLogoutJobResponse(
        job_id=job_id,
        status="processing",
        message="Conditional logout job created successfully"
    )

@router.post("/emergency", response_model=BatchLogoutJobResponse)
@require_batch_logout_permission(BatchLogoutPermission.EXECUTE_EMERGENCY_LOGOUT)
@batch_logout_rate_limit(RateLimitType.EMERGENCY_LOGOUT)
@require_emergency_auth("LOGOUT_ALL_USERS")
@audit_batch_logout_action("emergency_logout_initiated", sensitive=True)
async def create_emergency_logout(
    request: EmergencyLogoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """긴급 전체 로그아웃"""
    
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
    
    logger.critical(f"Emergency logout initiated: {job_id} by user {current_user.email}")
    
    return BatchLogoutJobResponse(
        job_id=job_id,
        status="processing",
        priority="immediate",
        message="Emergency logout initiated"
    )

@router.get("/jobs/{job_id}", response_model=BatchLogoutJobStatus)
@require_batch_logout_permission(BatchLogoutPermission.VIEW_BATCH_LOGOUT_JOBS)
@audit_batch_logout_action("job_status_viewed")
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
@require_batch_logout_permission(BatchLogoutPermission.CANCEL_BATCH_LOGOUT)
@audit_batch_logout_action("job_cancelled")
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
    
    logger.info(f"Batch logout job {job_id} cancelled by {current_user.email}: {reason}")
    
    return {"message": "Job cancelled successfully"}

@router.get("/jobs", response_model=List[BatchLogoutJobStatus])
@require_batch_logout_permission(BatchLogoutPermission.VIEW_BATCH_LOGOUT_JOBS)
@audit_batch_logout_action("job_list_viewed")
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
    
    from sqlalchemy import text
    result = db.execute(text(query), params)
    
    jobs = []
    for row in result:
        job_status = batch_logout_service.get_job_status(str(row.id), db)
        if job_status:
            jobs.append(BatchLogoutJobStatus(**job_status))
    
    return jobs

# 사용자 세션 관리 API
@user_session_router.post("/logout", response_model=UserLogoutResponse)
@batch_logout_rate_limit(RateLimitType.USER_SESSION_LOGOUT)
@audit_batch_logout_action("user_session_logout")
async def user_logout(
    request: UserLogoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자 자체 로그아웃 (현재 세션 또는 모든 세션)"""
    from sqlalchemy import text
    
    if request.logout_type == "current":
        # 현재 세션만 로그아웃 (기존 로직 활용)
        # 현재 액세스 토큰을 해지하는 로직이 필요
        # 현재는 간단하게 사용자의 최신 토큰 하나만 해지
        result = db.execute(
            text("""
                UPDATE oauth_access_tokens 
                SET revoked_at = NOW() 
                WHERE user_id = :user_id 
                AND revoked_at IS NULL
                ORDER BY created_at DESC
                LIMIT 1
            """),
            {"user_id": str(current_user.id)}
        )
        tokens_revoked = result.rowcount
        
        result = db.execute(
            text("""
                DELETE FROM oauth_sessions 
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                LIMIT 1
            """),
            {"user_id": str(current_user.id)}
        )
        sessions_terminated = result.rowcount
        
    else:  # logout_type == "all"
        # 모든 세션 로그아웃
        stats = batch_logout_service._revoke_tokens_for_users([str(current_user.id)], db)
        tokens_revoked = stats['access_tokens'] + stats['refresh_tokens']
        sessions_terminated = stats['sessions']
    
    db.commit()
    
    logger.info(f"User {current_user.email} logged out {request.logout_type} sessions")
    
    return UserLogoutResponse(
        message=f"Successfully logged out {request.logout_type} sessions",
        logout_type=request.logout_type,
        sessions_terminated=sessions_terminated,
        tokens_revoked=tokens_revoked
    )

@user_session_router.get("/active", response_model=UserSessionsResponse)
@audit_batch_logout_action("user_sessions_viewed")
async def get_user_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자의 활성 세션 목록 조회"""
    from sqlalchemy import text
    
    # 사용자의 활성 세션 조회
    result = db.execute(
        text("""
            SELECT 
                s.id as session_id,
                s.client_id,
                c.client_name,
                s.created_at,
                s.last_used_at,
                s.ip_address,
                s.user_agent
            FROM oauth_sessions s
            LEFT JOIN oauth_clients c ON s.client_id = c.client_id
            WHERE s.user_id = :user_id
            ORDER BY s.last_used_at DESC NULLS LAST
        """),
        {"user_id": str(current_user.id)}
    )
    
    sessions = []
    current_session = None
    
    for i, row in enumerate(result):
        session_info = UserSessionInfo(
            session_id=str(row.session_id),
            client_id=row.client_id,
            client_name=row.client_name or "Unknown Client",
            created_at=row.created_at,
            last_used_at=row.last_used_at,
            ip_address=row.ip_address,
            user_agent=row.user_agent,
            is_current_session=(i == 0),  # 가장 최근 세션을 현재 세션으로 가정
            is_suspicious=False  # 간단한 구현
        )
        
        if i == 0:
            current_session = session_info
        else:
            sessions.append(session_info)
    
    if not current_session:
        # 세션이 없는 경우 더미 현재 세션 생성
        current_session = UserSessionInfo(
            session_id="current",
            client_id="platform",
            client_name="MAX Platform",
            created_at=datetime.utcnow(),
            is_current_session=True
        )
    
    return UserSessionsResponse(
        current_session=current_session,
        other_sessions=sessions,
        total_sessions=len(sessions) + 1,
        suspicious_sessions=0
    )

@user_session_router.post("/logout-sessions", response_model=SessionLogoutResponse)
@batch_logout_rate_limit(RateLimitType.USER_SESSION_LOGOUT)
@audit_batch_logout_action("specific_sessions_logout")
async def logout_specific_sessions(
    request: SessionLogoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """특정 세션들 로그아웃"""
    from sqlalchemy import text
    
    # 세션 삭제
    result = db.execute(
        text("""
            DELETE FROM oauth_sessions 
            WHERE user_id = :user_id 
            AND id = ANY(:session_ids)
        """),
        {"user_id": str(current_user.id), "session_ids": request.session_ids}
    )
    sessions_terminated = result.rowcount
    
    # 관련 토큰 해지 (해당 세션의 토큰들)
    result = db.execute(
        text("""
            UPDATE oauth_access_tokens 
            SET revoked_at = NOW() 
            WHERE user_id = :user_id 
            AND session_id = ANY(:session_ids)
            AND revoked_at IS NULL
        """),
        {"user_id": str(current_user.id), "session_ids": request.session_ids}
    )
    tokens_revoked = result.rowcount
    
    db.commit()
    
    logger.info(f"User {current_user.email} logged out {len(request.session_ids)} specific sessions")
    
    return SessionLogoutResponse(
        message=f"Successfully logged out {sessions_terminated} sessions",
        sessions_terminated=sessions_terminated,
        tokens_revoked=tokens_revoked,
        failed_sessions=[]  # 실제 구현에서는 실패한 세션 ID들을 추가
    )