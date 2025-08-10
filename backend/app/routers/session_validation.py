"""
Session Validation API for SSO
Provides session validation endpoints for client applications
"""
from fastapi import APIRouter, HTTPException, status, Header, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import logging
import hashlib

from ..database import get_db
from ..config import settings
from ..core.redis_session import get_session_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/session", tags=["session"])

class SessionValidationRequest(BaseModel):
    """Request model for session validation"""
    session_id: str
    user_id: str
    token_hash: Optional[str] = None  # Optional JWT token hash for additional validation

class SessionValidationResponse(BaseModel):
    """Response model for session validation"""
    valid: bool
    user_id: Optional[str] = None
    reason: Optional[str] = None
    session_data: Optional[Dict[str, Any]] = None

def verify_service_key(x_service_key: str = Header(None)) -> bool:
    """Verify inter-service communication key"""
    if not x_service_key:
        logger.warning("Missing service key in session validation request")
        return False
    
    # Use a secure service key from environment
    expected_key = settings.INTER_SERVICE_KEY if hasattr(settings, 'INTER_SERVICE_KEY') else "default-service-key-change-in-production"
    
    if x_service_key != expected_key:
        logger.warning("Invalid service key in session validation request")
        return False
    
    return True

@router.post("/validate", response_model=SessionValidationResponse)
async def validate_session(
    request: SessionValidationRequest,
    x_service_key: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Validate session for SSO client applications
    
    This endpoint is called by client apps (like maxlab) to validate
    if a session is still valid in the auth server.
    """
    # Verify service key for security
    if not verify_service_key(x_service_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing service key"
        )
    
    try:
        # 1. Check Redis session store
        session_store = get_session_store()
        session_key = f"session:{request.session_id}"
        session_data = None
        
        if session_store:
            session_data = session_store.get(session_key)
            
            if session_data:
                # Verify user_id matches
                if session_data.get("user_id") != request.user_id:
                    logger.warning(f"User ID mismatch for session {request.session_id[:8]}...")
                    return SessionValidationResponse(
                        valid=False,
                        reason="user_id_mismatch"
                    )
                
                # Session exists and is valid
                logger.info(f"Session validated from Redis: {request.session_id[:8]}...")
                return SessionValidationResponse(
                    valid=True,
                    user_id=request.user_id,
                    session_data={
                        "created_at": session_data.get("created_at"),
                        "last_accessed": session_data.get("last_accessed"),
                        "email": session_data.get("email")
                    }
                )
        
        # 2. Check OAuth access tokens if token_hash provided
        if request.token_hash:
            try:
                result = db.execute(
                    text("""
                        SELECT user_id, expires_at, revoked_at
                        FROM oauth_access_tokens
                        WHERE token_hash = :token_hash
                        AND user_id = :user_id
                    """),
                    {
                        "token_hash": request.token_hash,
                        "user_id": request.user_id
                    }
                )
                token = result.fetchone()
                
                if token:
                    # Check if token is revoked
                    if token.revoked_at:
                        logger.info(f"Token is revoked for user {request.user_id}")
                        return SessionValidationResponse(
                            valid=False,
                            reason="token_revoked"
                        )
                    
                    # Check if token is expired
                    if token.expires_at and token.expires_at < datetime.utcnow():
                        logger.info(f"Token is expired for user {request.user_id}")
                        return SessionValidationResponse(
                            valid=False,
                            reason="token_expired"
                        )
                    
                    # Token is valid
                    logger.info(f"Session validated from token: {request.token_hash[:8]}...")
                    return SessionValidationResponse(
                        valid=True,
                        user_id=request.user_id
                    )
            except Exception as e:
                logger.error(f"Error checking OAuth tokens: {e}")
        
        # 3. Check if user exists and is active
        try:
            user_result = db.execute(
                text("""
                    SELECT id, is_active, is_verified
                    FROM users
                    WHERE id = :user_id
                """),
                {"user_id": request.user_id}
            )
            user = user_result.fetchone()
            
            if not user:
                logger.warning(f"User not found: {request.user_id}")
                return SessionValidationResponse(
                    valid=False,
                    reason="user_not_found"
                )
            
            if not user.is_active:
                logger.warning(f"User is inactive: {request.user_id}")
                return SessionValidationResponse(
                    valid=False,
                    reason="user_inactive"
                )
            
            # User exists and is active, but session not found
            # This might happen if Redis was cleared or session expired
            logger.info(f"Session not found but user is active: {request.user_id}")
            return SessionValidationResponse(
                valid=False,
                reason="session_not_found"
            )
            
        except Exception as e:
            logger.error(f"Error checking user status: {e}")
            return SessionValidationResponse(
                valid=False,
                reason="validation_error"
            )
        
    except Exception as e:
        logger.error(f"Session validation error: {e}")
        # On error, we should fail securely
        return SessionValidationResponse(
            valid=False,
            reason="internal_error"
        )

@router.post("/invalidate")
async def invalidate_session(
    session_id: str,
    user_id: str,
    x_service_key: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Invalidate a session (called by client apps during logout)
    """
    # Verify service key
    if not verify_service_key(x_service_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing service key"
        )
    
    try:
        # Remove from Redis
        session_store = get_session_store()
        if session_store:
            session_key = f"session:{session_id}"
            session_store.delete(session_key)
            
            # Also remove from user's session list
            user_sessions_key = f"user_sessions:{user_id}"
            session_store.srem(user_sessions_key, session_id)
            
            logger.info(f"Session invalidated: {session_id[:8]}... for user {user_id}")
        
        # Log the invalidation event
        try:
            db.execute(
                text("""
                    INSERT INTO oauth_audit_logs 
                    (event_type, user_id, success, details)
                    VALUES ('session_invalidated', :user_id, true, :details)
                """),
                {
                    "user_id": user_id,
                    "details": f"Session {session_id[:8]}... invalidated by client app"
                }
            )
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to log session invalidation: {e}")
        
        return {"status": "success", "message": "Session invalidated"}
        
    except Exception as e:
        logger.error(f"Session invalidation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to invalidate session"
        )

@router.get("/active-sessions/{user_id}")
async def get_active_sessions(
    user_id: str,
    x_service_key: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Get all active sessions for a user
    """
    # Verify service key
    if not verify_service_key(x_service_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing service key"
        )
    
    try:
        session_store = get_session_store()
        active_sessions = []
        
        if session_store:
            # Get all sessions for user
            user_sessions_key = f"user_sessions:{user_id}"
            session_ids = session_store.smembers(user_sessions_key)
            
            for session_id in session_ids:
                session_key = f"session:{session_id}"
                session_data = session_store.get(session_key)
                if session_data:
                    active_sessions.append({
                        "session_id": session_id,
                        "created_at": session_data.get("created_at"),
                        "last_accessed": session_data.get("last_accessed")
                    })
        
        return {
            "user_id": user_id,
            "active_sessions": active_sessions,
            "count": len(active_sessions)
        }
        
    except Exception as e:
        logger.error(f"Error getting active sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get active sessions"
        )