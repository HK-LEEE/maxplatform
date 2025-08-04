#%%
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
        self.batch_size = getattr(settings, 'batch_logout_batch_size', 100)
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
                
                # 알림 전송 (필요한 경우)
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
    
    async def _process_client_based_logout(
        self, 
        job_id: str, 
        job: Dict, 
        db: Session
    ):
        """클라이언트 기반 로그아웃 처리"""
        conditions = job['conditions']
        dry_run = job['dry_run']
        
        # 클라이언트별 토큰 조회
        client_tokens = self._get_tokens_by_client(
            conditions['client_id'],
            db,
            conditions.get('created_before')
        )
        
        if dry_run:
            statistics = {
                'users_affected': len(set(t['user_id'] for t in client_tokens)),
                'access_tokens_revoked': len(client_tokens),
                'refresh_tokens_revoked': 0,
                'sessions_terminated': 0
            }
            self._complete_job(job_id, statistics, db)
            return
        
        # 실제 토큰 해지
        token_ids = [t['id'] for t in client_tokens]
        stats = self._revoke_tokens_by_ids(token_ids, db)
        
        # 완료 처리
        self._complete_job(job_id, stats, db)
    
    async def _process_time_based_logout(
        self,
        job_id: str,
        job: Dict,
        db: Session
    ):
        """시간 기반 로그아웃 처리"""
        conditions = job['conditions']
        dry_run = job['dry_run']
        
        # 시간 조건에 맞는 토큰 조회
        old_tokens = self._get_tokens_by_time(
            db,
            conditions.get('created_before'),
            conditions.get('last_used_before'),
            conditions.get('token_types', ['access_token', 'refresh_token'])
        )
        
        if dry_run:
            statistics = {
                'users_affected': len(set(t['user_id'] for t in old_tokens)),
                'access_tokens_revoked': len([t for t in old_tokens if t['type'] == 'access']),
                'refresh_tokens_revoked': len([t for t in old_tokens if t['type'] == 'refresh']),
                'sessions_terminated': 0
            }
            self._complete_job(job_id, statistics, db)
            return
        
        # 실제 토큰 해지
        stats = self._revoke_old_tokens(old_tokens, db)
        self._complete_job(job_id, stats, db)
    
    async def _process_emergency_logout(
        self,
        job_id: str,
        job: Dict,
        db: Session
    ):
        """긴급 로그아웃 처리"""
        conditions = job['conditions']
        
        # 모든 활성 토큰 해지
        stats = self._execute_emergency_logout(
            conditions.get('exclude_admin_sessions', True),
            conditions.get('preserve_service_tokens', True),
            db
        )
        
        logger.warning(f"Emergency logout executed: {stats}")
        self._complete_job(job_id, stats, db)
    
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
    
    def _execute_emergency_logout(
        self,
        exclude_admin_sessions: bool,
        preserve_service_tokens: bool,
        db: Session
    ) -> Dict[str, int]:
        """긴급 로그아웃 실행"""
        stats = {
            'users_affected': 0,
            'access_tokens_revoked': 0,
            'refresh_tokens_revoked': 0,
            'sessions_terminated': 0
        }
        
        # Access tokens 해지
        query = "UPDATE oauth_access_tokens SET revoked_at = NOW() WHERE revoked_at IS NULL"
        params = {}
        
        if exclude_admin_sessions:
            query += " AND user_id NOT IN (SELECT id FROM users WHERE is_admin = true)"
        
        if preserve_service_tokens:
            query += " AND user_id IS NOT NULL"  # 서비스 토큰은 user_id가 NULL
        
        result = db.execute(text(query), params)
        stats['access_tokens_revoked'] = result.rowcount
        
        # Refresh tokens 해지
        query = "UPDATE oauth_refresh_tokens SET revoked_at = NOW() WHERE revoked_at IS NULL"
        
        if exclude_admin_sessions:
            query += " AND user_id NOT IN (SELECT id FROM users WHERE is_admin = true)"
        
        result = db.execute(text(query), params)
        stats['refresh_tokens_revoked'] = result.rowcount
        
        # OAuth sessions 삭제
        query = "DELETE FROM oauth_sessions WHERE 1=1"
        
        if exclude_admin_sessions:
            query += " AND user_id NOT IN (SELECT id FROM users WHERE is_admin = true)"
        
        result = db.execute(text(query), params)
        stats['sessions_terminated'] = result.rowcount
        
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
    
    async def _send_logout_notifications(
        self,
        users: List[Dict],
        reason: str,
        logout_type: str
    ) -> int:
        """로그아웃 알림 전송"""
        # 실제 구현에서는 이메일/SMS 서비스 연동
        # 현재는 로깅만
        sent_count = 0
        for user in users:
            logger.info(f"Notification sent to user {user['id']}: {reason}")
            sent_count += 1
        return sent_count
    
    def _get_users_by_group(
        self,
        group_id: str,
        include_subgroups: bool,
        exclude_admin_users: bool,
        db: Session
    ) -> List[Dict]:
        """그룹별 사용자 조회"""
        query = """
            SELECT u.id, u.email, u.display_name, u.is_admin
            FROM users u
            WHERE u.group_id = :group_id
        """
        params = {"group_id": group_id}
        
        if exclude_admin_users:
            query += " AND u.is_admin = false"
        
        result = db.execute(text(query), params)
        return [{"id": str(row.id), "email": row.email, "display_name": row.display_name} 
                for row in result]
    
    def _simulate_logout(self, users: List[Dict], db: Session) -> Dict:
        """로그아웃 시뮬레이션"""
        user_ids = [u['id'] for u in users]
        
        # 토큰 수 계산
        access_count = db.execute(
            text("SELECT COUNT(*) FROM oauth_access_tokens WHERE user_id = ANY(:user_ids) AND revoked_at IS NULL"),
            {"user_ids": user_ids}
        ).scalar()
        
        refresh_count = db.execute(
            text("SELECT COUNT(*) FROM oauth_refresh_tokens WHERE user_id = ANY(:user_ids) AND revoked_at IS NULL"),
            {"user_ids": user_ids}
        ).scalar()
        
        session_count = db.execute(
            text("SELECT COUNT(*) FROM oauth_sessions WHERE user_id = ANY(:user_ids)"),
            {"user_ids": user_ids}
        ).scalar()
        
        return {
            'users_affected': len(users),
            'access_tokens_revoked': access_count,
            'refresh_tokens_revoked': refresh_count,
            'sessions_terminated': session_count
        }
    
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
                    u.display_name as initiated_by_name
                FROM oauth_batch_logout_jobs j
                JOIN users u ON j.initiated_by = u.id
                WHERE j.id = :job_id
            """),
            {"job_id": job_id}
        ).first()
        
        if result:
            # 통계 조회
            stats_result = db.execute(
                text("SELECT * FROM get_batch_logout_statistics(:job_id)"),
                {"job_id": job_id}
            ).first()
            
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
                "statistics": {
                    "total_users_affected": stats_result.total_users_affected if stats_result else 0,
                    "total_access_tokens_revoked": stats_result.total_access_tokens_revoked if stats_result else 0,
                    "total_refresh_tokens_revoked": stats_result.total_refresh_tokens_revoked if stats_result else 0,
                    "total_sessions_terminated": stats_result.total_sessions_terminated if stats_result else 0,
                    "total_notifications_sent": stats_result.total_notifications_sent if stats_result else 0,
                    "total_notification_failures": stats_result.total_notification_failures if stats_result else 0
                } if stats_result else None,
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
    
    def _update_job_progress(self, job_id: str, progress: int, db: Session):
        """작업 진행률 업데이트"""
        db.execute(
            text("UPDATE oauth_batch_logout_jobs SET progress = :progress WHERE id = :job_id"),
            {"progress": progress, "job_id": job_id}
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
    
    def _get_job_details(self, job_id: str, db: Session) -> Optional[Dict]:
        """작업 상세 정보 조회"""
        result = db.execute(
            text("SELECT * FROM oauth_batch_logout_jobs WHERE id = :job_id"),
            {"job_id": job_id}
        ).first()
        
        if result:
            return {
                "id": str(result.id),
                "job_type": result.job_type,
                "status": result.status,
                "initiated_by": str(result.initiated_by),
                "reason": result.reason,
                "conditions": result.conditions,
                "dry_run": result.dry_run,
                "priority": result.priority,
                "created_at": result.created_at
            }
        
        return None
    
    def _get_tokens_by_client(self, client_id: str, db: Session, created_before: datetime = None) -> List[Dict]:
        """클라이언트별 토큰 조회"""
        query = """
            SELECT id, user_id, 'access' as type
            FROM oauth_access_tokens 
            WHERE client_id = :client_id AND revoked_at IS NULL
        """
        params = {"client_id": client_id}
        
        if created_before:
            query += " AND created_at < :created_before"
            params["created_before"] = created_before
        
        result = db.execute(text(query), params)
        return [{"id": str(row.id), "user_id": str(row.user_id), "type": row.type} for row in result]
    
    def _get_tokens_by_time(self, db: Session, created_before: datetime = None, last_used_before: datetime = None, 
                          token_types: List[str] = None) -> List[Dict]:
        """시간 기반 토큰 조회"""
        tokens = []
        
        if 'access_token' in token_types:
            query = "SELECT id, user_id, 'access' as type FROM oauth_access_tokens WHERE revoked_at IS NULL"
            params = {}
            
            if created_before:
                query += " AND created_at < :created_before"
                params["created_before"] = created_before
                
            result = db.execute(text(query), params)
            tokens.extend([{"id": str(row.id), "user_id": str(row.user_id), "type": row.type} for row in result])
        
        if 'refresh_token' in token_types:
            query = "SELECT id, user_id, 'refresh' as type FROM oauth_refresh_tokens WHERE revoked_at IS NULL"
            params = {}
            
            if created_before:
                query += " AND created_at < :created_before"
                params["created_before"] = created_before
                
            result = db.execute(text(query), params)
            tokens.extend([{"id": str(row.id), "user_id": str(row.user_id), "type": row.type} for row in result])
        
        return tokens
    
    def _revoke_tokens_by_ids(self, token_ids: List[str], db: Session) -> Dict[str, int]:
        """토큰 ID별 해지"""
        if not token_ids:
            return {"access_tokens_revoked": 0, "refresh_tokens_revoked": 0}
        
        # Access tokens 해지
        access_result = db.execute(
            text("UPDATE oauth_access_tokens SET revoked_at = NOW() WHERE id = ANY(:token_ids)"),
            {"token_ids": token_ids}
        )
        
        # Refresh tokens 해지  
        refresh_result = db.execute(
            text("UPDATE oauth_refresh_tokens SET revoked_at = NOW() WHERE id = ANY(:token_ids)"),
            {"token_ids": token_ids}
        )
        
        db.commit()
        return {
            "access_tokens_revoked": access_result.rowcount,
            "refresh_tokens_revoked": refresh_result.rowcount
        }
    
    def _revoke_old_tokens(self, tokens: List[Dict], db: Session) -> Dict[str, int]:
        """오래된 토큰 해지"""
        access_tokens = [t['id'] for t in tokens if t['type'] == 'access']
        refresh_tokens = [t['id'] for t in tokens if t['type'] == 'refresh']
        
        stats = {"access_tokens_revoked": 0, "refresh_tokens_revoked": 0}
        
        if access_tokens:
            result = db.execute(
                text("UPDATE oauth_access_tokens SET revoked_at = NOW() WHERE id = ANY(:token_ids)"),
                {"token_ids": access_tokens}
            )
            stats["access_tokens_revoked"] = result.rowcount
        
        if refresh_tokens:
            result = db.execute(
                text("UPDATE oauth_refresh_tokens SET revoked_at = NOW() WHERE id = ANY(:token_ids)"),
                {"token_ids": refresh_tokens}
            )
            stats["refresh_tokens_revoked"] = result.rowcount
        
        db.commit()
        return stats
    
    async def _process_conditional_logout(self, job_id: str, job: Dict, db: Session):
        """조건부 로그아웃 처리 (향후 구현)"""
        logger.info(f"Conditional logout not yet implemented for job {job_id}")
        self._complete_job(job_id, {"message": "Conditional logout not implemented"}, db)

# 싱글톤 인스턴스
batch_logout_service = BatchLogoutService()