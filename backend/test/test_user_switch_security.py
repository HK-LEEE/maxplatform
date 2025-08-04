"""
Test suite for User Switch Security Service
Tests the security features that prevent session contamination and privilege escalation
"""

import pytest
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.services.user_switch_security_service import user_switch_security_service
from app.services.user_session_service import user_session_service
from app.database import get_db, SessionLocal
from app.models import User


class TestUserSwitchSecurity:
    """Test cases for user switch security functionality."""
    
    @pytest.fixture
    def db_session(self):
        """Create a test database session."""
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    @pytest.fixture
    def test_users(self, db_session):
        """Create test users for security testing."""
        users = []
        
        # Create regular user
        regular_user_id = str(uuid.uuid4())
        db_session.execute(
            text("""
                INSERT INTO users (id, email, password_hash, is_admin, created_at)
                VALUES (:id, :email, :password, :is_admin, NOW())
            """),
            {
                "id": regular_user_id,
                "email": "regular@test.com",
                "password": "hashed_password",
                "is_admin": False
            }
        )
        users.append({"id": regular_user_id, "email": "regular@test.com", "is_admin": False})
        
        # Create admin user
        admin_user_id = str(uuid.uuid4())
        db_session.execute(
            text("""
                INSERT INTO users (id, email, password_hash, is_admin, created_at)
                VALUES (:id, :email, :password, :is_admin, NOW())
            """),
            {
                "id": admin_user_id,
                "email": "admin@test.com",
                "password": "hashed_password",
                "is_admin": True
            }
        )
        users.append({"id": admin_user_id, "email": "admin@test.com", "is_admin": True})
        
        db_session.commit()
        return users
    
    @pytest.fixture
    def test_client(self, db_session):
        """Create a test OAuth client."""
        client_id = "test-client"
        db_session.execute(
            text("""
                INSERT INTO oauth_clients 
                (client_id, client_name, client_secret, is_confidential, is_active, redirect_uris, allowed_scopes)
                VALUES (:client_id, :name, :secret, :confidential, :active, :uris, :scopes)
            """),
            {
                "client_id": client_id,
                "name": "Test Client",
                "secret": "test_secret",
                "confidential": True,
                "active": True,
                "uris": ["http://localhost:3000/callback"],
                "scopes": ["read:profile", "manage:workflows"]
            }
        )
        db_session.commit()
        return client_id
    
    def create_active_session(self, db_session, user_id: str, client_id: str):
        """Helper to create an active session and tokens."""
        # Create access token
        db_session.execute(
            text("""
                INSERT INTO oauth_access_tokens 
                (token_hash, client_id, user_id, scope, expires_at, created_at)
                VALUES (:token_hash, :client_id, :user_id, :scope, :expires_at, NOW())
            """),
            {
                "token_hash": f"token_hash_{user_id}_{client_id}",
                "client_id": client_id,
                "user_id": user_id,
                "scope": "read:profile",
                "expires_at": datetime.utcnow() + timedelta(hours=1)
            }
        )
        
        # Create refresh token
        db_session.execute(
            text("""
                INSERT INTO oauth_refresh_tokens 
                (token_hash, client_id, user_id, scope, expires_at, created_at)
                VALUES (:token_hash, :client_id, :user_id, :scope, :expires_at, NOW())
            """),
            {
                "token_hash": f"refresh_hash_{user_id}_{client_id}",
                "client_id": client_id,
                "user_id": user_id,
                "scope": "read:profile",
                "expires_at": datetime.utcnow() + timedelta(days=30)
            }
        )
        
        # Create session
        db_session.execute(
            text("""
                INSERT INTO oauth_sessions 
                (id, user_id, client_id, granted_scopes, created_at, updated_at)
                VALUES (:id, :user_id, :client_id, :scopes, NOW(), NOW())
            """),
            {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "client_id": client_id,
                "scopes": ["read:profile"]
            }
        )
        
        db_session.commit()

    def test_no_user_switch_detection(self, db_session, test_users, test_client):
        """Test that no user switch is detected for first login."""
        user = test_users[0]
        
        result = user_switch_security_service.detect_user_switch(
            client_id=test_client,
            new_user_id=user["id"],
            db=db_session
        )
        
        assert result["is_user_switch"] is False
        assert result["switch_type"] == "first_login"
        assert result["risk_level"] == "low"
        assert result["requires_cleanup"] is False

    def test_same_user_login_detection(self, db_session, test_users, test_client):
        """Test that same user login is detected correctly."""
        user = test_users[0]
        
        # Create existing session
        self.create_active_session(db_session, user["id"], test_client)
        
        result = user_switch_security_service.detect_user_switch(
            client_id=test_client,
            new_user_id=user["id"],
            db=db_session
        )
        
        assert result["is_user_switch"] is False
        assert result["switch_type"] == "same_user"
        assert result["requires_cleanup"] is False

    def test_user_switch_detection(self, db_session, test_users, test_client):
        """Test that user switch is detected correctly."""
        regular_user = test_users[0]
        admin_user = test_users[1]
        
        # Create session for regular user
        self.create_active_session(db_session, regular_user["id"], test_client)
        
        # Admin user tries to login (higher risk)
        result = user_switch_security_service.detect_user_switch(
            client_id=test_client,
            new_user_id=admin_user["id"],
            db=db_session
        )
        
        assert result["is_user_switch"] is True
        assert result["switch_type"] == "user_change"
        assert result["previous_user_id"] == regular_user["id"]
        assert result["new_user_id"] == admin_user["id"]
        assert result["requires_cleanup"] is True
        assert result["risk_level"] in ["medium", "high"]  # Admin login increases risk

    def test_admin_to_regular_switch_risk_assessment(self, db_session, test_users, test_client):
        """Test that admin to regular user switch is high risk."""
        regular_user = test_users[0]
        admin_user = test_users[1]
        
        # Create session for admin user
        self.create_active_session(db_session, admin_user["id"], test_client)
        
        # Regular user tries to login after admin
        result = user_switch_security_service.detect_user_switch(
            client_id=test_client,
            new_user_id=regular_user["id"],
            db=db_session
        )
        
        assert result["is_user_switch"] is True
        assert result["risk_level"] in ["medium", "high"]  # Previous admin user increases risk
        assert "previous_user_admin" in result.get("risk_factors", [])

    def test_force_previous_user_cleanup(self, db_session, test_users, test_client):
        """Test that cleanup properly removes previous user's tokens and sessions."""
        regular_user = test_users[0]
        admin_user = test_users[1]
        
        # Create session for regular user
        self.create_active_session(db_session, regular_user["id"], test_client)
        
        # Verify tokens exist
        token_count = db_session.execute(
            text("""
                SELECT COUNT(*) FROM oauth_access_tokens 
                WHERE user_id = :user_id AND client_id = :client_id AND revoked_at IS NULL
            """),
            {"user_id": regular_user["id"], "client_id": test_client}
        ).scalar()
        assert token_count > 0
        
        # Perform cleanup
        cleanup_result = user_switch_security_service.force_previous_user_cleanup(
            client_id=test_client,
            previous_user_id=regular_user["id"],
            new_user_id=admin_user["id"],
            reason="test_cleanup",
            db=db_session
        )
        
        assert cleanup_result["success"] is True
        assert cleanup_result["cleanup_performed"] is True
        assert cleanup_result["stats"]["access_tokens_revoked"] > 0
        
        # Verify tokens were revoked
        active_token_count = db_session.execute(
            text("""
                SELECT COUNT(*) FROM oauth_access_tokens 
                WHERE user_id = :user_id AND client_id = :client_id AND revoked_at IS NULL
            """),
            {"user_id": regular_user["id"], "client_id": test_client}
        ).scalar()
        assert active_token_count == 0

    def test_audit_trail_creation(self, db_session, test_users, test_client):
        """Test that user switch events are properly audited."""
        regular_user = test_users[0]
        admin_user = test_users[1]
        
        # Create audit record
        success = user_switch_security_service.audit_user_switch(
            client_id=test_client,
            previous_user_id=regular_user["id"],
            new_user_id=admin_user["id"],
            switch_type="user_change",
            risk_level="high",
            risk_factors=["test_factor"],
            request_ip="192.168.1.100",
            user_agent="Test Browser",
            cleanup_stats={"access_tokens_revoked": 1},
            db=db_session
        )
        
        assert success is True
        
        # Verify audit record exists
        audit_count = db_session.execute(
            text("""
                SELECT COUNT(*) FROM oauth_user_switch_audit 
                WHERE client_id = :client_id 
                AND previous_user_id = :prev_user 
                AND new_user_id = :new_user
            """),
            {
                "client_id": test_client,
                "prev_user": regular_user["id"],
                "new_user": admin_user["id"]
            }
        ).scalar()
        assert audit_count == 1

    def test_suspicious_pattern_detection(self, db_session, test_users, test_client):
        """Test detection of suspicious switching patterns."""
        regular_user = test_users[0]
        admin_user = test_users[1]
        
        # Create multiple rapid switches
        for i in range(6):  # Above threshold of 5
            user_switch_security_service.audit_user_switch(
                client_id=test_client,
                previous_user_id=regular_user["id"] if i % 2 == 0 else admin_user["id"],
                new_user_id=admin_user["id"] if i % 2 == 0 else regular_user["id"],
                switch_type="user_change",
                risk_level="medium",
                risk_factors=["rapid_switching"],
                db=db_session
            )
        
        # Check for suspicious patterns
        patterns = user_switch_security_service.get_suspicious_switch_patterns(
            hours=1, db=db_session
        )
        
        assert len(patterns) > 0
        client_pattern = next((p for p in patterns if p["client_id"] == test_client), None)
        assert client_pattern is not None
        assert client_pattern["switch_count"] >= 5

    def test_secure_user_login_integration(self, db_session, test_users, test_client):
        """Test the integrated secure login functionality."""
        regular_user = test_users[0]
        admin_user = test_users[1]
        
        # Create existing session for regular user
        self.create_active_session(db_session, regular_user["id"], test_client)
        
        # Admin user performs secure login
        result = user_session_service.secure_user_login(
            user_id=admin_user["id"],
            client_id=test_client,
            request_ip="192.168.1.100",
            user_agent="Test Browser",
            db=db_session
        )
        
        assert result["success"] is True
        assert result["user_switch_detected"] is True
        assert result["cleanup_performed"] is True
        assert result["risk_level"] in ["medium", "high"]
        assert len(result["security_recommendations"]) > 0

    def test_force_secure_logout_all_clients(self, db_session, test_users, test_client):
        """Test emergency logout functionality."""
        admin_user = test_users[1]
        
        # Create sessions on multiple clients
        clients = [test_client, "another-client"]
        for client in clients:
            try:
                # Create client if it doesn't exist
                db_session.execute(
                    text("""
                        INSERT INTO oauth_clients 
                        (client_id, client_name, client_secret, is_confidential, is_active, redirect_uris, allowed_scopes)
                        VALUES (:client_id, :name, :secret, :confidential, :active, :uris, :scopes)
                    """),
                    {
                        "client_id": client,
                        "name": f"Client {client}",
                        "secret": "secret",
                        "confidential": True,
                        "active": True,
                        "uris": ["http://localhost:3000/callback"],
                        "scopes": ["read:profile"]
                    }
                )
            except:
                pass  # Client might already exist
            
            self.create_active_session(db_session, admin_user["id"], client)
        
        # Perform emergency logout
        result = user_session_service.force_secure_logout_all_clients(
            user_id=admin_user["id"],
            reason="security_breach",
            db=db_session
        )
        
        assert result["success"] is True
        assert result["clients_affected"] >= 1
        assert result["security_cleanup"]["clients_cleaned"] >= 1

    def test_user_security_summary(self, db_session, test_users, test_client):
        """Test comprehensive security summary generation."""
        admin_user = test_users[1]
        
        # Create some session activity
        self.create_active_session(db_session, admin_user["id"], test_client)
        
        # Create some switch history
        user_switch_security_service.audit_user_switch(
            client_id=test_client,
            previous_user_id="other_user",
            new_user_id=admin_user["id"],
            switch_type="user_change",
            risk_level="medium",
            risk_factors=["test"],
            db=db_session
        )
        
        # Get security summary
        summary = user_session_service.get_user_security_summary(
            user_id=admin_user["id"],
            db=db_session
        )
        
        assert summary["user_id"] == admin_user["id"]
        assert "security_score" in summary
        assert 0 <= summary["security_score"] <= 100
        assert "session_info" in summary
        assert "recent_switches" in summary
        assert "recommendations" in summary

    def test_cleanup_old_audit_records(self, db_session, test_users, test_client):
        """Test that old audit records are properly cleaned up."""
        # Create old audit record
        db_session.execute(
            text("""
                INSERT INTO oauth_user_switch_audit 
                (client_id, new_user_id, switch_type, risk_level, created_at)
                VALUES (:client_id, :user_id, :type, :level, :created_at)
            """),
            {
                "client_id": test_client,
                "user_id": test_users[0]["id"],
                "type": "user_change",
                "level": "low",
                "created_at": datetime.utcnow() - timedelta(days=95)  # Older than retention
            }
        )
        db_session.commit()
        
        # Run cleanup
        deleted_count = user_switch_security_service.cleanup_old_audit_records(db=db_session)
        
        assert deleted_count >= 1

    def teardown_method(self):
        """Clean up after each test."""
        # This would normally clean up test data
        # In a real test environment, you'd use test database transactions
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])