#%%
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

class UserLogoutRequest(BaseModel):
    """사용자 자체 세션 관리용 로그아웃 요청"""
    logout_type: str = Field(..., description="'current' or 'all' sessions")
    reason: Optional[str] = Field(None, description="Optional reason for logging out")
    
    @validator('logout_type')
    def validate_logout_type(cls, v):
        if v not in ['current', 'all']:
            raise ValueError("logout_type must be 'current' or 'all'")
        return v

class BatchLogoutJobResponse(BaseModel):
    job_id: str
    status: str
    priority: Optional[str] = None
    estimated_affected_users: Optional[int] = None
    estimated_affected_tokens: Optional[int] = None
    estimated_completion: Optional[datetime] = None
    message: Optional[str] = None

class UserLogoutResponse(BaseModel):
    """사용자 로그아웃 응답"""
    message: str
    logout_type: str
    sessions_terminated: int
    tokens_revoked: int

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

class UserSessionInfo(BaseModel):
    """사용자 세션 정보"""
    session_id: str
    client_id: str
    client_name: str
    created_at: datetime
    last_used_at: Optional[datetime] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_info: Optional[Dict[str, Any]] = None
    location: Optional[Dict[str, str]] = None
    is_current_session: bool = False
    is_suspicious: bool = False

class UserSessionsResponse(BaseModel):
    """사용자 세션 목록 응답"""
    current_session: UserSessionInfo
    other_sessions: List[UserSessionInfo]
    total_sessions: int
    suspicious_sessions: int

class SessionLogoutRequest(BaseModel):
    """특정 세션 로그아웃 요청"""
    session_ids: List[str] = Field(..., description="Session IDs to logout")
    reason: Optional[str] = Field(None, description="Reason for logout")

class SessionLogoutResponse(BaseModel):
    """특정 세션 로그아웃 응답"""
    message: str
    sessions_terminated: int
    tokens_revoked: int
    failed_sessions: List[str] = []