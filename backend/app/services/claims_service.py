"""
OIDC Claims Service
Manages user claims based on requested scopes
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from ..models import User

class ClaimsService:
    """Service for managing OIDC claims based on scopes"""
    
    # Standard OIDC scope to claims mapping
    SCOPE_CLAIMS_MAP = {
        "profile": [
            "name", "family_name", "given_name", "middle_name",
            "nickname", "preferred_username", "profile", "picture",
            "website", "gender", "birthdate", "zoneinfo", "locale",
            "updated_at"
        ],
        "email": ["email", "email_verified"],
        "address": ["address"],
        "phone": ["phone_number", "phone_number_verified"],
        # Custom scopes for MAX Platform
        "groups": ["groups", "group_id", "group_name"],
        "roles": ["role", "role_id", "role_name", "permissions"]
    }
    
    def get_user_claims(
        self, 
        user: User, 
        scopes: List[str],
        db: Session,
        include_custom: bool = True
    ) -> Dict[str, Any]:
        """
        Get user claims based on requested scopes
        
        Args:
            user: User object
            scopes: List of requested scopes
            db: Database session
            include_custom: Include custom MAX Platform claims
            
        Returns:
            Dictionary of claims
        """
        claims = {}
        
        # Always include sub (subject) - it's the user ID
        # Sub is included in base token, not here
        
        # Process standard OIDC scopes
        for scope in scopes:
            if scope in self.SCOPE_CLAIMS_MAP:
                scope_claims = self.SCOPE_CLAIMS_MAP[scope]
                for claim in scope_claims:
                    value = self._get_claim_value(user, claim, db)
                    if value is not None:
                        claims[claim] = value
        
        # Add custom claims if requested
        if include_custom and any(s.startswith("read:") or s.startswith("manage:") for s in scopes):
            custom_claims = self._get_custom_claims(user, scopes, db)
            claims.update(custom_claims)
        
        return claims
    
    def _get_claim_value(
        self, 
        user: User, 
        claim: str,
        db: Session
    ) -> Any:
        """Get individual claim value from user object"""
        
        # Standard profile claims
        if claim == "name":
            return user.display_name or user.real_name or user.email
        elif claim == "given_name":
            # Extract from real_name if available
            if user.real_name and " " in user.real_name:
                return user.real_name.split(" ")[0]
            return None
        elif claim == "family_name":
            # Extract from real_name if available
            if user.real_name and " " in user.real_name:
                parts = user.real_name.split(" ")
                return " ".join(parts[1:]) if len(parts) > 1 else None
            return None
        elif claim == "preferred_username":
            return user.username if hasattr(user, 'username') else user.email.split("@")[0]
        elif claim == "email":
            return user.email
        elif claim == "email_verified":
            return getattr(user, 'email_verified', True)  # Default to True if not tracked
        elif claim == "updated_at":
            if hasattr(user, 'updated_at') and user.updated_at:
                return int(user.updated_at.timestamp())
            return None
        elif claim == "locale":
            return getattr(user, 'locale', 'ko-KR')  # Default Korean locale
        elif claim == "zoneinfo":
            return getattr(user, 'timezone', 'Asia/Seoul')  # Default Seoul timezone
        
        # Group-related claims
        elif claim == "groups":
            if user.group:
                return [user.group.name]
            return []
        elif claim == "group_id":
            return str(user.group_id) if user.group_id else None
        elif claim == "group_name":
            return user.group.name if user.group else None
        
        # Role-related claims
        elif claim == "role":
            return user.role.name if user.role else None
        elif claim == "role_id":
            return str(user.role_id) if user.role_id else None
        elif claim == "role_name":
            return user.role.name if user.role else None
        elif claim == "permissions":
            # Get permissions from role
            if user.role:
                # This would need to be implemented based on your permission model
                return []
            return []
        
        # Address claim (structured)
        elif claim == "address":
            # Return formatted address if available
            if hasattr(user, 'address') and user.address:
                return {
                    "formatted": user.address,
                    "country": "KR"  # Default to Korea
                }
            return None
        
        # Phone claims
        elif claim == "phone_number":
            return getattr(user, 'phone_number', None)
        elif claim == "phone_number_verified":
            return getattr(user, 'phone_verified', False)
        
        # Profile picture
        elif claim == "picture":
            return getattr(user, 'avatar_url', None)
        
        # Gender
        elif claim == "gender":
            return getattr(user, 'gender', None)
        
        # Birthdate
        elif claim == "birthdate":
            if hasattr(user, 'birthdate') and user.birthdate:
                return user.birthdate.strftime("%Y-%m-%d")
            return None
        
        # Default: try to get attribute directly
        return getattr(user, claim, None)
    
    def _get_custom_claims(
        self,
        user: User,
        scopes: List[str],
        db: Session
    ) -> Dict[str, Any]:
        """Get custom MAX Platform claims"""
        custom_claims = {}
        
        # Admin status
        if user.is_admin:
            custom_claims["is_admin"] = True
        
        # Feature permissions based on scopes
        features = []
        if "read:features" in scopes:
            # Get user's available features
            if user.group:
                # You would fetch features from group permissions
                features = ["dashboard", "analytics", "reports"]
        
        if features:
            custom_claims["features"] = features
        
        # Workspace information
        if "manage:workspaces" in scopes:
            custom_claims["workspace_quota"] = getattr(user, 'workspace_quota', 5)
            custom_claims["active_workspaces"] = getattr(user, 'active_workspace_count', 0)
        
        # API quotas
        if "manage:apis" in scopes:
            custom_claims["api_quota"] = {
                "daily_limit": 10000,
                "rate_limit": "100/minute"
            }
        
        # ML model permissions
        if "manage:models" in scopes:
            custom_claims["ml_models_access"] = ["gpt-4", "llama-2", "stable-diffusion"]
        
        return custom_claims
    
    def get_userinfo_response(
        self,
        user: User,
        scopes: List[str],
        db: Session,
        as_jwt: bool = False,
        client_id: Optional[str] = None
    ) -> Any:
        """
        Get UserInfo endpoint response
        
        Can return either JSON or JWT format
        """
        # Get all claims for the scopes
        claims = self.get_user_claims(user, scopes, db)
        
        # Always include sub
        claims["sub"] = str(user.id)
        
        if as_jwt and client_id:
            # Return as signed JWT (optional per OIDC spec)
            from .id_token_service import id_token_service
            
            # Create a minimal ID token with just userinfo claims
            return id_token_service.create_id_token(
                user=user,
                client_id=client_id,
                nonce=None,  # No nonce for userinfo
                auth_time=datetime.utcnow(),  # Not relevant for userinfo
                scopes=scopes,
                access_token=None,
                authorization_code=None,
                db=db,
                additional_claims=claims
            )
        else:
            # Return as JSON (default)
            return claims

# Singleton instance
claims_service = ClaimsService()