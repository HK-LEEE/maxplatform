"""
OAuth 2.0 Admin API Router
Provides OAuth client management endpoints for administrators
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import secrets
import hashlib

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_, func
from pydantic import BaseModel, Field

from ..database import get_db
from ..utils.auth import get_current_user, require_service_auth
from ..models import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/oauth", tags=["OAuth Admin"])


# Pydantic models
class OAuthClientResponse(BaseModel):
    id: str
    client_id: str
    client_name: str
    description: Optional[str]
    redirect_uris: List[str]
    allowed_scopes: List[str]
    is_confidential: bool
    is_active: bool
    logo_url: Optional[str]
    homepage_url: Optional[str]
    created_at: datetime
    updated_at: datetime


class OAuthClientUpdate(BaseModel):
    client_name: Optional[str] = None
    description: Optional[str] = None
    redirect_uris: Optional[List[str]] = None
    allowed_scopes: Optional[List[str]] = None
    is_active: Optional[bool] = None
    logo_url: Optional[str] = None
    homepage_url: Optional[str] = None


class OAuthSessionResponse(BaseModel):
    id: str
    user_id: str
    user_email: str
    user_name: str
    client_id: str
    client_name: str
    granted_scopes: List[str]
    last_used_at: datetime
    created_at: datetime


class OAuthAuditLogResponse(BaseModel):
    id: str
    action: str
    client_id: Optional[str]
    client_name: Optional[str]
    user_id: Optional[str]
    user_email: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    success: bool
    error_code: Optional[str]
    error_description: Optional[str]
    created_at: datetime


class ClientSecretResponse(BaseModel):
    client_secret: str
    message: str


class RefreshTokenResponse(BaseModel):
    id: str
    user_id: str
    user_email: str
    user_name: str
    client_id: str
    client_name: str
    scope: Optional[str]
    expires_at: datetime
    created_at: datetime
    last_used_at: Optional[datetime]
    rotation_count: int
    client_ip: Optional[str]


class RefreshTokenStatsResponse(BaseModel):
    total_active_tokens: int
    total_expired_tokens: int
    tokens_by_client: Dict[str, int]
    recent_rotations: int


# Helper functions
def check_admin_permission(current_user: User):
    """Check if user has admin permission"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin permission required")


def check_service_permission(service_info: dict, required_scopes: list = None):
    """Check if service has required permissions"""
    if required_scopes:
        service_scopes = service_info.get("scopes", [])
        missing_scopes = [scope for scope in required_scopes if scope not in service_scopes]
        if missing_scopes:
            raise HTTPException(
                status_code=403, 
                detail=f"Missing required scopes: {', '.join(missing_scopes)}"
            )


def generate_client_secret() -> str:
    """Generate a secure client secret"""
    return f"secret_{secrets.token_urlsafe(32)}"


# OAuth Client Management Endpoints
@router.get("/clients", response_model=List[OAuthClientResponse])
def list_oauth_clients(
    search: Optional[str] = Query(None, description="Search by client ID or name"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all OAuth clients with optional filtering"""
    check_admin_permission(current_user)
    
    try:
        # Build query
        query = "SELECT * FROM oauth_clients WHERE 1=1"
        params = {}
        
        if search:
            query += " AND (client_id ILIKE :search OR client_name ILIKE :search)"
            params["search"] = f"%{search}%"
        
        if is_active is not None:
            query += " AND is_active = :is_active"
            params["is_active"] = is_active
        
        query += " ORDER BY client_id LIMIT :limit OFFSET :skip"
        params["limit"] = limit
        params["skip"] = skip
        
        result = db.execute(text(query), params)
        
        clients = []
        for row in result:
            clients.append(OAuthClientResponse(
                id=str(row.id),
                client_id=row.client_id,
                client_name=row.client_name,
                description=row.description,
                redirect_uris=row.redirect_uris,
                allowed_scopes=row.allowed_scopes,
                is_confidential=row.is_confidential,
                is_active=row.is_active,
                logo_url=row.logo_url,
                homepage_url=row.homepage_url,
                created_at=row.created_at,
                updated_at=row.updated_at
            ))
        
        return clients
        
    except Exception as e:
        logger.error(f"Error listing OAuth clients: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list OAuth clients")


@router.get("/clients/{client_id}", response_model=OAuthClientResponse)
def get_oauth_client(
    client_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific OAuth client"""
    check_admin_permission(current_user)
    
    try:
        result = db.execute(
            text("SELECT * FROM oauth_clients WHERE client_id = :client_id"),
            {"client_id": client_id}
        )
        row = result.first()
        
        if not row:
            raise HTTPException(status_code=404, detail="OAuth client not found")
        
        return OAuthClientResponse(
            id=str(row.id),
            client_id=row.client_id,
            client_name=row.client_name,
            description=row.description,
            redirect_uris=row.redirect_uris,
            allowed_scopes=row.allowed_scopes,
            is_confidential=row.is_confidential,
            is_active=row.is_active,
            logo_url=row.logo_url,
            homepage_url=row.homepage_url,
            created_at=row.created_at,
            updated_at=row.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting OAuth client: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get OAuth client")


@router.put("/clients/{client_id}", response_model=OAuthClientResponse)
def update_oauth_client(
    client_id: str,
    update_data: OAuthClientUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update OAuth client configuration"""
    check_admin_permission(current_user)
    
    try:
        # Check if client exists
        result = db.execute(
            text("SELECT * FROM oauth_clients WHERE client_id = :client_id"),
            {"client_id": client_id}
        )
        if not result.first():
            raise HTTPException(status_code=404, detail="OAuth client not found")
        
        # Build update query
        update_fields = []
        params = {"client_id": client_id}
        
        if update_data.client_name is not None:
            update_fields.append("client_name = :client_name")
            params["client_name"] = update_data.client_name
        
        if update_data.description is not None:
            update_fields.append("description = :description")
            params["description"] = update_data.description
        
        if update_data.redirect_uris is not None:
            update_fields.append("redirect_uris = :redirect_uris")
            params["redirect_uris"] = update_data.redirect_uris
        
        if update_data.allowed_scopes is not None:
            update_fields.append("allowed_scopes = :allowed_scopes")
            params["allowed_scopes"] = update_data.allowed_scopes
        
        if update_data.is_active is not None:
            update_fields.append("is_active = :is_active")
            params["is_active"] = update_data.is_active
        
        if update_data.logo_url is not None:
            update_fields.append("logo_url = :logo_url")
            params["logo_url"] = update_data.logo_url
        
        if update_data.homepage_url is not None:
            update_fields.append("homepage_url = :homepage_url")
            params["homepage_url"] = update_data.homepage_url
        
        if update_fields:
            update_fields.append("updated_at = NOW()")
            query = f"UPDATE oauth_clients SET {', '.join(update_fields)} WHERE client_id = :client_id RETURNING *"
            
            result = db.execute(text(query), params)
            db.commit()
            
            row = result.first()
            return OAuthClientResponse(
                id=str(row.id),
                client_id=row.client_id,
                client_name=row.client_name,
                description=row.description,
                redirect_uris=row.redirect_uris,
                allowed_scopes=row.allowed_scopes,
                is_confidential=row.is_confidential,
                is_active=row.is_active,
                logo_url=row.logo_url,
                homepage_url=row.homepage_url,
                created_at=row.created_at,
                updated_at=row.updated_at
            )
        else:
            raise HTTPException(status_code=400, detail="No fields to update")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating OAuth client: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update OAuth client")


@router.post("/clients/{client_id}/regenerate-secret", response_model=ClientSecretResponse)
def regenerate_client_secret(
    client_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Regenerate client secret for confidential clients"""
    check_admin_permission(current_user)
    
    try:
        # Check if client exists and is confidential
        result = db.execute(
            text("SELECT is_confidential FROM oauth_clients WHERE client_id = :client_id"),
            {"client_id": client_id}
        )
        row = result.first()
        
        if not row:
            raise HTTPException(status_code=404, detail="OAuth client not found")
        
        if not row.is_confidential:
            raise HTTPException(status_code=400, detail="Cannot regenerate secret for public clients")
        
        # Generate new secret
        new_secret = generate_client_secret()
        
        # Update client secret
        db.execute(
            text("""
                UPDATE oauth_clients 
                SET client_secret = :secret, updated_at = NOW() 
                WHERE client_id = :client_id
            """),
            {"client_id": client_id, "secret": new_secret}
        )
        db.commit()
        
        return ClientSecretResponse(
            client_secret=new_secret,
            message="Client secret regenerated successfully. Please save this secret securely as it won't be shown again."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error regenerating client secret: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to regenerate client secret")


# OAuth Session Management Endpoints
@router.get("/sessions", response_model=List[OAuthSessionResponse])
def list_oauth_sessions(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    client_id: Optional[str] = Query(None, description="Filter by client ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List OAuth sessions with optional filtering"""
    check_admin_permission(current_user)
    
    try:
        # Build query with joins
        query = """
            SELECT 
                s.id, s.user_id, s.client_id, s.granted_scopes, 
                s.last_used_at, s.created_at,
                u.email as user_email, 
                COALESCE(u.display_name, u.real_name, u.email) as user_name,
                c.client_name
            FROM oauth_sessions s
            JOIN users u ON s.user_id = u.id
            JOIN oauth_clients c ON s.client_id = c.client_id
            WHERE 1=1
        """
        params = {}
        
        if user_id:
            query += " AND s.user_id = :user_id"
            params["user_id"] = user_id
        
        if client_id:
            query += " AND s.client_id = :client_id"
            params["client_id"] = client_id
        
        query += " ORDER BY s.last_used_at DESC LIMIT :limit OFFSET :skip"
        params["limit"] = limit
        params["skip"] = skip
        
        result = db.execute(text(query), params)
        
        sessions = []
        for row in result:
            sessions.append(OAuthSessionResponse(
                id=str(row.id),
                user_id=str(row.user_id),
                user_email=row.user_email,
                user_name=row.user_name,
                client_id=row.client_id,
                client_name=row.client_name,
                granted_scopes=row.granted_scopes,
                last_used_at=row.last_used_at,
                created_at=row.created_at
            ))
        
        return sessions
        
    except Exception as e:
        logger.error(f"Error listing OAuth sessions: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list OAuth sessions")


@router.delete("/sessions/{session_id}")
def revoke_oauth_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke an OAuth session"""
    check_admin_permission(current_user)
    
    try:
        # Check if session exists
        result = db.execute(
            text("SELECT user_id, client_id FROM oauth_sessions WHERE id = :id"),
            {"id": session_id}
        )
        row = result.first()
        
        if not row:
            raise HTTPException(status_code=404, detail="OAuth session not found")
        
        # Revoke all access tokens for this session
        db.execute(
            text("""
                UPDATE oauth_access_tokens 
                SET revoked_at = NOW() 
                WHERE user_id = :user_id 
                AND client_id = :client_id 
                AND revoked_at IS NULL
            """),
            {"user_id": row.user_id, "client_id": row.client_id}
        )
        
        # Delete the session
        db.execute(
            text("DELETE FROM oauth_sessions WHERE id = :id"),
            {"id": session_id}
        )
        
        db.commit()
        
        return {"message": "OAuth session revoked successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking OAuth session: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to revoke OAuth session")


# OAuth Audit Log Endpoints
@router.get("/audit-logs", response_model=List[OAuthAuditLogResponse])
def list_oauth_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action type"),
    client_id: Optional[str] = Query(None, description="Filter by client ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    success: Optional[bool] = Query(None, description="Filter by success status"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List OAuth audit logs with optional filtering"""
    check_admin_permission(current_user)
    
    try:
        # Build query with optional joins
        query = """
            SELECT 
                l.id, l.action, l.client_id, l.user_id, l.ip_address,
                l.user_agent, l.success, l.error_code, l.error_description,
                l.created_at,
                c.client_name,
                u.email as user_email
            FROM oauth_audit_logs l
            LEFT JOIN oauth_clients c ON l.client_id = c.client_id
            LEFT JOIN users u ON l.user_id = u.id
            WHERE 1=1
        """
        params = {}
        
        if action:
            query += " AND l.action = :action"
            params["action"] = action
        
        if client_id:
            query += " AND l.client_id = :client_id"
            params["client_id"] = client_id
        
        if user_id:
            query += " AND l.user_id = :user_id"
            params["user_id"] = user_id
        
        if success is not None:
            query += " AND l.success = :success"
            params["success"] = success
        
        if start_date:
            query += " AND l.created_at >= :start_date"
            params["start_date"] = start_date
        
        if end_date:
            query += " AND l.created_at <= :end_date"
            params["end_date"] = end_date
        
        query += " ORDER BY l.created_at DESC LIMIT :limit OFFSET :skip"
        params["limit"] = limit
        params["skip"] = skip
        
        result = db.execute(text(query), params)
        
        logs = []
        for row in result:
            logs.append(OAuthAuditLogResponse(
                id=str(row.id),
                action=row.action,
                client_id=row.client_id,
                client_name=row.client_name,
                user_id=str(row.user_id) if row.user_id else None,
                user_email=row.user_email,
                ip_address=row.ip_address,
                user_agent=row.user_agent,
                success=row.success,
                error_code=row.error_code,
                error_description=row.error_description,
                created_at=row.created_at
            ))
        
        return logs
        
    except Exception as e:
        logger.error(f"Error listing OAuth audit logs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list OAuth audit logs")


# Refresh Token Management Endpoints
@router.get("/refresh-tokens", response_model=List[RefreshTokenResponse])
def list_refresh_tokens(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    client_id: Optional[str] = Query(None, description="Filter by client ID"),
    include_expired: bool = Query(False, description="Include expired tokens"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List refresh tokens with optional filtering"""
    check_admin_permission(current_user)
    
    try:
        # Build query with joins
        query = """
            SELECT 
                r.id, r.user_id, r.client_id, r.scope, r.expires_at, 
                r.created_at, r.last_used_at, r.rotation_count, r.client_ip,
                u.email as user_email,
                COALESCE(u.display_name, u.real_name, u.email) as user_name,
                c.client_name
            FROM oauth_refresh_tokens r
            LEFT JOIN users u ON r.user_id = u.id
            LEFT JOIN oauth_clients c ON r.client_id = c.client_id
            WHERE r.revoked_at IS NULL
        """
        
        params = {}
        
        if not include_expired:
            query += " AND r.expires_at > NOW()"
        
        if user_id:
            query += " AND r.user_id = :user_id"
            params["user_id"] = user_id
        
        if client_id:
            query += " AND r.client_id = :client_id"
            params["client_id"] = client_id
        
        query += " ORDER BY r.created_at DESC LIMIT :limit OFFSET :skip"
        params["limit"] = limit
        params["skip"] = skip
        
        result = db.execute(text(query), params)
        
        tokens = []
        for row in result:
            tokens.append(RefreshTokenResponse(
                id=str(row.id),
                user_id=str(row.user_id),
                user_email=row.user_email or "Unknown",
                user_name=row.user_name or "Unknown",
                client_id=row.client_id,
                client_name=row.client_name or "Unknown",
                scope=row.scope,
                expires_at=row.expires_at,
                created_at=row.created_at,
                last_used_at=row.last_used_at,
                rotation_count=row.rotation_count or 0,
                client_ip=row.client_ip
            ))
        
        return tokens
        
    except Exception as e:
        logger.error(f"Error listing refresh tokens: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list refresh tokens")


@router.delete("/refresh-tokens/{token_id}")
def revoke_refresh_token_by_id(
    token_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke a specific refresh token"""
    check_admin_permission(current_user)
    
    try:
        # Revoke the refresh token
        result = db.execute(
            text("""
                UPDATE oauth_refresh_tokens 
                SET revoked_at = NOW() 
                WHERE id = :token_id AND revoked_at IS NULL
            """),
            {"token_id": token_id}
        )
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Refresh token not found or already revoked")
        
        # Also revoke associated access tokens
        db.execute(
            text("""
                UPDATE oauth_access_tokens 
                SET revoked_at = NOW() 
                WHERE refresh_token_hash = (
                    SELECT token_hash FROM oauth_refresh_tokens WHERE id = :token_id
                ) AND revoked_at IS NULL
            """),
            {"token_id": token_id}
        )
        
        db.commit()
        
        return {"message": "Refresh token revoked successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking refresh token: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to revoke refresh token")


@router.delete("/refresh-tokens/user/{user_id}")
def revoke_user_refresh_tokens(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke all refresh tokens for a specific user"""
    check_admin_permission(current_user)
    
    try:
        # Revoke all refresh tokens for the user
        result = db.execute(
            text("""
                UPDATE oauth_refresh_tokens 
                SET revoked_at = NOW() 
                WHERE user_id = :user_id AND revoked_at IS NULL
            """),
            {"user_id": user_id}
        )
        
        revoked_count = result.rowcount
        
        # Also revoke associated access tokens
        db.execute(
            text("""
                UPDATE oauth_access_tokens 
                SET revoked_at = NOW() 
                WHERE user_id = :user_id AND revoked_at IS NULL
            """),
            {"user_id": user_id}
        )
        
        db.commit()
        
        return {"message": f"Revoked {revoked_count} refresh tokens for user"}
        
    except Exception as e:
        logger.error(f"Error revoking user refresh tokens: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to revoke user refresh tokens")


@router.get("/refresh-tokens/stats", response_model=RefreshTokenStatsResponse)
def get_refresh_token_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get refresh token statistics"""
    check_admin_permission(current_user)
    
    try:
        # Get total active tokens
        active_result = db.execute(
            text("""
                SELECT COUNT(*) as count
                FROM oauth_refresh_tokens 
                WHERE revoked_at IS NULL AND expires_at > NOW()
            """)
        )
        total_active = active_result.scalar()
        
        # Get total expired tokens
        expired_result = db.execute(
            text("""
                SELECT COUNT(*) as count
                FROM oauth_refresh_tokens 
                WHERE revoked_at IS NULL AND expires_at <= NOW()
            """)
        )
        total_expired = expired_result.scalar()
        
        # Get tokens by client
        client_result = db.execute(
            text("""
                SELECT client_id, COUNT(*) as count
                FROM oauth_refresh_tokens 
                WHERE revoked_at IS NULL AND expires_at > NOW()
                GROUP BY client_id
            """)
        )
        tokens_by_client = {row.client_id: row.count for row in client_result}
        
        # Get recent rotations (last 24 hours)
        rotation_result = db.execute(
            text("""
                SELECT COUNT(*) as count
                FROM oauth_refresh_tokens 
                WHERE last_used_at > NOW() - INTERVAL '24 hours'
            """)
        )
        recent_rotations = rotation_result.scalar()
        
        return RefreshTokenStatsResponse(
            total_active_tokens=total_active,
            total_expired_tokens=total_expired,
            tokens_by_client=tokens_by_client,
            recent_rotations=recent_rotations
        )
        
    except Exception as e:
        logger.error(f"Error getting refresh token stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get refresh token statistics")


@router.get("/statistics")
def get_oauth_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get OAuth usage statistics"""
    check_admin_permission(current_user)
    
    try:
        # Total clients
        total_clients = db.execute(
            text("SELECT COUNT(*) FROM oauth_clients")
        ).scalar()
        
        # Active clients
        active_clients = db.execute(
            text("SELECT COUNT(*) FROM oauth_clients WHERE is_active = true")
        ).scalar()
        
        # Total sessions
        total_sessions = db.execute(
            text("SELECT COUNT(*) FROM oauth_sessions")
        ).scalar()
        
        # Active tokens (not expired and not revoked)
        active_tokens = db.execute(
            text("""
                SELECT COUNT(*) FROM oauth_access_tokens 
                WHERE expires_at > NOW() AND revoked_at IS NULL
            """)
        ).scalar()
        
        # Recent activity (last 24 hours)
        recent_authorizations = db.execute(
            text("""
                SELECT COUNT(*) FROM oauth_audit_logs 
                WHERE action = 'authorize' 
                AND success = true 
                AND created_at > NOW() - INTERVAL '24 hours'
            """)
        ).scalar()
        
        # Top clients by session count
        top_clients = db.execute(
            text("""
                SELECT c.client_id, c.client_name, COUNT(s.id) as session_count
                FROM oauth_clients c
                LEFT JOIN oauth_sessions s ON c.client_id = s.client_id
                GROUP BY c.client_id, c.client_name
                ORDER BY session_count DESC
                LIMIT 5
            """)
        ).fetchall()
        
        return {
            "total_clients": total_clients,
            "active_clients": active_clients,
            "total_sessions": total_sessions,
            "active_tokens": active_tokens,
            "recent_authorizations_24h": recent_authorizations,
            "top_clients": [
                {
                    "client_id": row.client_id,
                    "client_name": row.client_name,
                    "session_count": row.session_count
                }
                for row in top_clients
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting OAuth statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get OAuth statistics")


# Service-only endpoints (for service-to-service communication)
@router.get("/service/clients", response_model=List[OAuthClientResponse])
def list_oauth_clients_service(
    search: Optional[str] = Query(None, description="Search by client ID or name"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    service_info: dict = require_service_auth(["admin:oauth"]),
    db: Session = Depends(get_db)
):
    """List OAuth clients using service authentication"""
    check_service_permission(service_info, ["admin:oauth"])
    
    try:
        # Build query (same logic as user endpoint)
        query = "SELECT * FROM oauth_clients WHERE 1=1"
        params = {}
        
        if search:
            query += " AND (client_id ILIKE :search OR client_name ILIKE :search)"
            params["search"] = f"%{search}%"
        
        if is_active is not None:
            query += " AND is_active = :is_active"
            params["is_active"] = is_active
        
        query += " ORDER BY client_id LIMIT :limit OFFSET :skip"
        params["limit"] = limit
        params["skip"] = skip
        
        result = db.execute(text(query), params)
        
        clients = []
        for row in result:
            clients.append(OAuthClientResponse(
                id=str(row.id),
                client_id=row.client_id,
                client_name=row.client_name,
                description=row.description,
                redirect_uris=row.redirect_uris,
                allowed_scopes=row.allowed_scopes,
                is_confidential=row.is_confidential,
                is_active=row.is_active,
                logo_url=row.logo_url,
                homepage_url=row.homepage_url,
                created_at=row.created_at,
                updated_at=row.updated_at
            ))
        
        logger.info(f"Service {service_info['client_id']} accessed OAuth clients list")
        return clients
        
    except Exception as e:
        logger.error(f"Error listing OAuth clients for service: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list OAuth clients")


@router.get("/service/statistics")
def get_oauth_statistics_service(
    service_info: dict = require_service_auth(["admin:oauth"]),
    db: Session = Depends(get_db)
):
    """Get OAuth statistics using service authentication"""
    check_service_permission(service_info, ["admin:oauth"])
    
    try:
        # Same statistics logic as user endpoint
        total_clients = db.execute(
            text("SELECT COUNT(*) FROM oauth_clients")
        ).scalar()
        
        active_clients = db.execute(
            text("SELECT COUNT(*) FROM oauth_clients WHERE is_active = true")
        ).scalar()
        
        total_sessions = db.execute(
            text("SELECT COUNT(*) FROM oauth_sessions")
        ).scalar()
        
        active_tokens = db.execute(
            text("""
                SELECT COUNT(*) FROM oauth_access_tokens 
                WHERE expires_at > NOW() AND revoked_at IS NULL
            """)
        ).scalar()
        
        recent_authorizations = db.execute(
            text("""
                SELECT COUNT(*) FROM oauth_audit_logs 
                WHERE action = 'authorize' 
                AND success = true 
                AND created_at > NOW() - INTERVAL '24 hours'
            """)
        ).scalar()
        
        # Service client statistics
        service_clients = db.execute(
            text("""
                SELECT COUNT(*) FROM oauth_clients 
                WHERE array_length(redirect_uris, 1) IS NULL 
                OR array_length(redirect_uris, 1) = 0
            """)
        ).scalar()
        
        service_tokens = db.execute(
            text("""
                SELECT COUNT(*) FROM oauth_access_tokens 
                WHERE user_id IS NULL 
                AND expires_at > NOW() 
                AND revoked_at IS NULL
            """)
        ).scalar()
        
        statistics = {
            "total_clients": total_clients,
            "active_clients": active_clients,
            "service_clients": service_clients,
            "total_sessions": total_sessions,
            "active_tokens": active_tokens,
            "active_service_tokens": service_tokens,
            "recent_authorizations_24h": recent_authorizations,
            "accessed_by_service": service_info["client_id"],
            "service_scopes": service_info["scopes"]
        }
        
        logger.info(f"Service {service_info['client_id']} accessed OAuth statistics")
        return statistics
        
    except Exception as e:
        logger.error(f"Error getting OAuth statistics for service: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get OAuth statistics")


@router.post("/service/clients/{client_id}/regenerate-secret", response_model=ClientSecretResponse)
def regenerate_client_secret_service(
    client_id: str,
    service_info: dict = require_service_auth(["admin:oauth"]),
    db: Session = Depends(get_db)
):
    """Regenerate client secret using service authentication"""
    check_service_permission(service_info, ["admin:oauth"])
    
    try:
        # Check if client exists and is confidential
        result = db.execute(
            text("SELECT is_confidential FROM oauth_clients WHERE client_id = :client_id"),
            {"client_id": client_id}
        )
        row = result.first()
        
        if not row:
            raise HTTPException(status_code=404, detail="OAuth client not found")
        
        if not row.is_confidential:
            raise HTTPException(status_code=400, detail="Cannot regenerate secret for public clients")
        
        # Generate new secret
        new_secret = generate_client_secret()
        
        # Update client secret
        db.execute(
            text("""
                UPDATE oauth_clients 
                SET client_secret = :secret, updated_at = NOW() 
                WHERE client_id = :client_id
            """),
            {"client_id": client_id, "secret": new_secret}
        )
        db.commit()
        
        logger.info(f"Service {service_info['client_id']} regenerated secret for client {client_id}")
        
        return ClientSecretResponse(
            client_secret=new_secret,
            message=f"Client secret regenerated by service {service_info['client_id']}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error regenerating client secret for service: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to regenerate client secret")