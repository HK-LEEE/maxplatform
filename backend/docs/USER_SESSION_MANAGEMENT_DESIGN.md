# 사용자 세션 관리 기능 설계

## 개요

사용자가 자신의 모든 OAuth 세션을 조회하고 관리할 수 있는 기능을 제공합니다. 이를 통해 사용자는 여러 디바이스나 애플리케이션에서의 로그인 상태를 확인하고, 원하는 세션을 선택적으로 또는 전체적으로 로그아웃할 수 있습니다.

## 주요 기능

### 1. 세션 조회
- 현재 활성화된 모든 세션 목록 표시
- 각 세션의 상세 정보 (클라이언트, 디바이스, 위치, 마지막 사용 시간)
- 현재 세션 표시

### 2. 선택적 로그아웃
- 개별 세션 로그아웃
- 현재 세션만 로그아웃
- 현재 세션을 제외한 모든 세션 로그아웃
- 모든 세션 로그아웃

### 3. 보안 기능
- 의심스러운 세션 감지 및 표시
- 위치 기반 이상 징후 알림
- 로그아웃 시 2차 인증 옵션

## API 설계

### 1. 세션 목록 조회

```http
GET /api/user/sessions
Authorization: Bearer {access_token}

Response:
{
  "current_session_id": "session-123",
  "sessions": [
    {
      "session_id": "session-123",
      "client": {
        "id": "web-app",
        "name": "MAX Platform Web",
        "logo_url": "https://..."
      },
      "device": {
        "type": "desktop",
        "browser": "Chrome 120",
        "os": "Windows 11"
      },
      "location": {
        "ip": "211.xxx.xxx.xxx",
        "city": "Seoul",
        "country": "KR"
      },
      "is_current": true,
      "created_at": "2025-01-29T08:00:00Z",
      "last_used_at": "2025-01-29T10:30:00Z",
      "expires_at": "2025-01-29T11:00:00Z",
      "scopes": ["openid", "profile", "email"]
    },
    {
      "session_id": "session-456",
      "client": {
        "id": "mobile-app",
        "name": "MAX Platform Mobile",
        "logo_url": "https://..."
      },
      "device": {
        "type": "mobile",
        "browser": "MAX App",
        "os": "iOS 17"
      },
      "location": {
        "ip": "223.xxx.xxx.xxx",
        "city": "Busan",
        "country": "KR"
      },
      "is_current": false,
      "is_suspicious": true,
      "suspicious_reason": "Unusual location",
      "created_at": "2025-01-28T15:00:00Z",
      "last_used_at": "2025-01-28T20:00:00Z",
      "expires_at": "2025-02-27T15:00:00Z",
      "scopes": ["openid", "profile"]
    }
  ],
  "total_sessions": 2,
  "suspicious_sessions": 1
}
```

### 2. 단일 세션 로그아웃

```http
POST /api/user/sessions/{session_id}/logout
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "reason": "No longer using this device"
}

Response:
{
  "success": true,
  "message": "Session logged out successfully",
  "revoked_tokens": {
    "access_tokens": 1,
    "refresh_tokens": 1
  }
}
```

### 3. 다중 세션 로그아웃

```http
POST /api/user/sessions/logout-multiple
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "action": "all_except_current", // "all", "all_except_current", "selected"
  "session_ids": ["session-456", "session-789"], // for "selected" action
  "password": "current_password", // optional 2FA
  "reason": "Security precaution"
}

Response:
{
  "success": true,
  "message": "Successfully logged out from 3 sessions",
  "details": {
    "sessions_terminated": 3,
    "access_tokens_revoked": 3,
    "refresh_tokens_revoked": 3,
    "current_session_preserved": true
  },
  "remaining_sessions": 1
}
```

### 4. 현재 세션 정보

```http
GET /api/user/sessions/current
Authorization: Bearer {access_token}

Response:
{
  "session_id": "session-123",
  "user_id": "user-uuid",
  "client": {
    "id": "web-app",
    "name": "MAX Platform Web"
  },
  "created_at": "2025-01-29T08:00:00Z",
  "expires_at": "2025-01-29T11:00:00Z",
  "scopes": ["openid", "profile", "email"],
  "ip_address": "211.xxx.xxx.xxx",
  "user_agent": "Mozilla/5.0..."
}
```

### 5. 세션 활동 기록

```http
GET /api/user/sessions/activity
Authorization: Bearer {access_token}
Query Parameters:
  - days: 7 (default 7, max 30)
  - limit: 50

Response:
{
  "activities": [
    {
      "timestamp": "2025-01-29T10:30:00Z",
      "action": "login",
      "client": "web-app",
      "ip_address": "211.xxx.xxx.xxx",
      "location": "Seoul, KR",
      "success": true
    },
    {
      "timestamp": "2025-01-28T15:00:00Z",
      "action": "login",
      "client": "mobile-app",
      "ip_address": "223.xxx.xxx.xxx",
      "location": "Busan, KR",
      "success": true,
      "flagged": true,
      "flag_reason": "New location"
    }
  ],
  "summary": {
    "total_logins": 5,
    "unique_locations": 2,
    "unique_devices": 2,
    "suspicious_activities": 1
  }
}
```

## UI/UX 설계

### 1. 세션 관리 페이지

```typescript
// 세션 관리 컴포넌트
interface SessionManagementProps {
  currentUserId: string;
}

interface Session {
  sessionId: string;
  client: ClientInfo;
  device: DeviceInfo;
  location: LocationInfo;
  isCurrent: boolean;
  isSuspicious?: boolean;
  createdAt: Date;
  lastUsedAt: Date;
  expiresAt: Date;
}

const SessionManagement: React.FC<SessionManagementProps> = () => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [showLogoutModal, setShowLogoutModal] = useState(false);
  const [logoutType, setLogoutType] = useState<'current' | 'all' | 'selected'>('current');
  const [selectedSessions, setSelectedSessions] = useState<string[]>([]);
  
  return (
    <div className="session-management">
      <h2>Active Sessions</h2>
      
      {/* 요약 정보 */}
      <div className="session-summary">
        <Alert type="info">
          You have {sessions.length} active sessions across different devices and applications.
          {sessions.filter(s => s.isSuspicious).length > 0 && (
            <span className="warning"> {sessions.filter(s => s.isSuspicious).length} suspicious sessions detected.</span>
          )}
        </Alert>
      </div>
      
      {/* 세션 목록 */}
      <div className="session-list">
        {sessions.map(session => (
          <SessionCard
            key={session.sessionId}
            session={session}
            onLogout={() => handleSingleLogout(session.sessionId)}
            onSelect={(selected) => handleSessionSelect(session.sessionId, selected)}
          />
        ))}
      </div>
      
      {/* 일괄 작업 버튼 */}
      <div className="bulk-actions">
        <Button
          variant="secondary"
          onClick={() => {
            setLogoutType('all_except_current');
            setShowLogoutModal(true);
          }}
        >
          Log Out Other Sessions
        </Button>
        
        <Button
          variant="danger"
          onClick={() => {
            setLogoutType('all');
            setShowLogoutModal(true);
          }}
        >
          Log Out All Sessions
        </Button>
      </div>
      
      {/* 로그아웃 확인 모달 */}
      <LogoutConfirmationModal
        isOpen={showLogoutModal}
        onClose={() => setShowLogoutModal(false)}
        logoutType={logoutType}
        selectedSessions={selectedSessions}
        onConfirm={handleLogoutConfirm}
      />
    </div>
  );
};
```

### 2. 로그아웃 확인 모달

```typescript
interface LogoutModalProps {
  isOpen: boolean;
  onClose: () => void;
  logoutType: 'current' | 'all' | 'all_except_current' | 'selected';
  selectedSessions?: string[];
  onConfirm: (password?: string) => void;
}

const LogoutConfirmationModal: React.FC<LogoutModalProps> = ({
  isOpen,
  onClose,
  logoutType,
  selectedSessions,
  onConfirm
}) => {
  const [password, setPassword] = useState('');
  const [requirePassword, setRequirePassword] = useState(false);
  
  const getModalContent = () => {
    switch (logoutType) {
      case 'current':
        return {
          title: 'Log Out Current Session',
          message: 'Are you sure you want to log out from this session?',
          warning: 'You will need to log in again to continue.',
          requireAuth: false
        };
      
      case 'all_except_current':
        return {
          title: 'Log Out Other Sessions',
          message: 'This will log you out from all other devices and applications.',
          warning: 'Other devices will need to log in again.',
          requireAuth: true
        };
      
      case 'all':
        return {
          title: 'Log Out All Sessions',
          message: 'This will log you out from ALL devices and applications, including this one.',
          warning: 'You will be immediately logged out and need to log in again.',
          requireAuth: true
        };
      
      case 'selected':
        return {
          title: 'Log Out Selected Sessions',
          message: `This will log out ${selectedSessions?.length} selected sessions.`,
          warning: 'Selected devices will need to log in again.',
          requireAuth: selectedSessions && selectedSessions.length > 3
        };
    }
  };
  
  const content = getModalContent();
  
  return (
    <Modal isOpen={isOpen} onClose={onClose} size="medium">
      <Modal.Header>
        <h3>{content.title}</h3>
      </Modal.Header>
      
      <Modal.Body>
        <p>{content.message}</p>
        
        <Alert type="warning" className="mt-4">
          <Icon name="warning" />
          {content.warning}
        </Alert>
        
        {content.requireAuth && (
          <div className="password-confirm mt-4">
            <label htmlFor="password">
              Confirm your password for security
            </label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
            />
          </div>
        )}
        
        {logoutType === 'all' && (
          <Alert type="danger" className="mt-4">
            <strong>Warning:</strong> This action will log you out immediately.
            Make sure you remember your login credentials.
          </Alert>
        )}
      </Modal.Body>
      
      <Modal.Footer>
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button
          variant="danger"
          onClick={() => onConfirm(content.requireAuth ? password : undefined)}
          disabled={content.requireAuth && !password}
        >
          Confirm Log Out
        </Button>
      </Modal.Footer>
    </Modal>
  );
};
```

### 3. 세션 카드 컴포넌트

```typescript
interface SessionCardProps {
  session: Session;
  onLogout: () => void;
  onSelect: (selected: boolean) => void;
}

const SessionCard: React.FC<SessionCardProps> = ({ session, onLogout, onSelect }) => {
  const getDeviceIcon = (type: string) => {
    switch (type) {
      case 'desktop': return 'desktop';
      case 'mobile': return 'smartphone';
      case 'tablet': return 'tablet';
      default: return 'device-unknown';
    }
  };
  
  return (
    <Card className={`session-card ${session.isCurrent ? 'current' : ''} ${session.isSuspicious ? 'suspicious' : ''}`}>
      <Card.Body>
        <div className="session-header">
          <div className="session-info">
            <Icon name={getDeviceIcon(session.device.type)} size="large" />
            <div>
              <h4>{session.client.name}</h4>
              <p className="device-info">
                {session.device.browser} on {session.device.os}
              </p>
            </div>
          </div>
          
          <div className="session-actions">
            {!session.isCurrent && (
              <Checkbox
                onChange={(e) => onSelect(e.target.checked)}
                aria-label="Select session"
              />
            )}
            {session.isCurrent ? (
              <Badge variant="primary">Current Session</Badge>
            ) : (
              <Button
                size="small"
                variant="outline"
                onClick={onLogout}
              >
                Log Out
              </Button>
            )}
          </div>
        </div>
        
        <div className="session-details">
          <div className="detail-item">
            <Icon name="location" />
            <span>{session.location.city}, {session.location.country}</span>
            {session.isSuspicious && (
              <Badge variant="warning" size="small">
                Unusual location
              </Badge>
            )}
          </div>
          
          <div className="detail-item">
            <Icon name="clock" />
            <span>Last active: {formatRelativeTime(session.lastUsedAt)}</span>
          </div>
          
          <div className="detail-item">
            <Icon name="calendar" />
            <span>Logged in: {formatDate(session.createdAt)}</span>
          </div>
        </div>
        
        {session.isSuspicious && (
          <Alert type="warning" size="small" className="mt-3">
            This session was flagged as suspicious due to unusual activity.
            If this wasn't you, log out immediately.
          </Alert>
        )}
      </Card.Body>
    </Card>
  );
};
```

## 백엔드 구현

### 1. 세션 관리 서비스

```python
# app/services/user_session_service.py

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging
from ipaddress import ip_address
import geoip2.database

from ..models import User
from ..utils.auth import verify_password
from ..config import settings

logger = logging.getLogger(__name__)

class UserSessionService:
    def __init__(self):
        # GeoIP 데이터베이스 (옵션)
        self.geoip_reader = None
        if settings.geoip_database_path:
            try:
                self.geoip_reader = geoip2.database.Reader(settings.geoip_database_path)
            except:
                logger.warning("GeoIP database not available")
    
    def get_user_sessions(self, user_id: str, db: Session) -> Dict:
        """사용자의 모든 활성 세션 조회"""
        # 현재 세션 ID 가져오기 (현재 토큰에서)
        current_session_id = self._get_current_session_id()
        
        # 모든 활성 세션 조회
        query = text("""
            SELECT 
                s.id as session_id,
                s.client_id,
                s.granted_scopes,
                s.created_at,
                s.last_used_at,
                s.client_ip,
                s.user_agent,
                c.client_name,
                c.logo_url,
                c.homepage_url,
                t.expires_at,
                COUNT(DISTINCT at.id) as active_tokens
            FROM oauth_sessions s
            JOIN oauth_clients c ON s.client_id = c.client_id
            LEFT JOIN oauth_refresh_tokens t ON t.user_id = s.user_id 
                AND t.client_id = s.client_id 
                AND t.revoked_at IS NULL
            LEFT JOIN oauth_access_tokens at ON at.user_id = s.user_id 
                AND at.client_id = s.client_id 
                AND at.revoked_at IS NULL
                AND at.expires_at > NOW()
            WHERE s.user_id = :user_id
            GROUP BY s.id, c.client_id, t.expires_at
            ORDER BY s.last_used_at DESC
        """)
        
        result = db.execute(query, {"user_id": user_id})
        sessions = []
        suspicious_count = 0
        
        for row in result:
            session_info = {
                "session_id": str(row.session_id),
                "client": {
                    "id": row.client_id,
                    "name": row.client_name,
                    "logo_url": row.logo_url,
                    "homepage_url": row.homepage_url
                },
                "device": self._parse_user_agent(row.user_agent),
                "location": self._get_location_info(row.client_ip),
                "is_current": str(row.session_id) == current_session_id,
                "created_at": row.created_at.isoformat(),
                "last_used_at": row.last_used_at.isoformat(),
                "expires_at": row.expires_at.isoformat() if row.expires_at else None,
                "scopes": row.granted_scopes or [],
                "active_tokens": row.active_tokens
            }
            
            # 의심스러운 세션 감지
            suspicious_info = self._check_suspicious_session(session_info, user_id, db)
            if suspicious_info["is_suspicious"]:
                session_info.update(suspicious_info)
                suspicious_count += 1
            
            sessions.append(session_info)
        
        return {
            "current_session_id": current_session_id,
            "sessions": sessions,
            "total_sessions": len(sessions),
            "suspicious_sessions": suspicious_count
        }
    
    def logout_single_session(
        self, 
        user_id: str, 
        session_id: str, 
        reason: Optional[str],
        db: Session
    ) -> Dict:
        """단일 세션 로그아웃"""
        # 세션 소유권 확인
        session_check = db.execute(
            text("SELECT 1 FROM oauth_sessions WHERE id = :session_id AND user_id = :user_id"),
            {"session_id": session_id, "user_id": user_id}
        ).first()
        
        if not session_check:
            raise ValueError("Session not found or access denied")
        
        # 해당 세션의 토큰들 해지
        stats = self._revoke_session_tokens(session_id, user_id, db)
        
        # 세션 삭제
        db.execute(
            text("DELETE FROM oauth_sessions WHERE id = :session_id"),
            {"session_id": session_id}
        )
        
        # 감사 로그
        self._log_session_action(
            "user_session_logout",
            user_id=user_id,
            session_id=session_id,
            reason=reason,
            stats=stats,
            db=db
        )
        
        db.commit()
        
        return {
            "success": True,
            "message": "Session logged out successfully",
            "revoked_tokens": stats
        }
    
    def logout_multiple_sessions(
        self,
        user_id: str,
        action: str,
        session_ids: Optional[List[str]],
        password: Optional[str],
        reason: Optional[str],
        current_session_id: str,
        db: Session
    ) -> Dict:
        """다중 세션 로그아웃"""
        # 보안을 위한 비밀번호 확인 (선택적)
        if action in ['all', 'all_except_current'] and settings.require_password_for_bulk_logout:
            if not password:
                raise ValueError("Password required for this action")
            
            user = db.query(User).filter(User.id == user_id).first()
            if not verify_password(password, user.hashed_password):
                raise ValueError("Invalid password")
        
        # 로그아웃할 세션 결정
        sessions_to_logout = self._determine_sessions_to_logout(
            user_id, action, session_ids, current_session_id, db
        )
        
        if not sessions_to_logout:
            return {
                "success": True,
                "message": "No sessions to logout",
                "details": {
                    "sessions_terminated": 0,
                    "access_tokens_revoked": 0,
                    "refresh_tokens_revoked": 0
                }
            }
        
        # 토큰 해지 및 세션 삭제
        total_stats = {
            "sessions_terminated": 0,
            "access_tokens_revoked": 0,
            "refresh_tokens_revoked": 0
        }
        
        for session_id in sessions_to_logout:
            try:
                stats = self._revoke_session_tokens(session_id, user_id, db)
                total_stats["access_tokens_revoked"] += stats["access_tokens"]
                total_stats["refresh_tokens_revoked"] += stats["refresh_tokens"]
                
                # 세션 삭제
                result = db.execute(
                    text("DELETE FROM oauth_sessions WHERE id = :session_id AND user_id = :user_id"),
                    {"session_id": session_id, "user_id": user_id}
                )
                
                if result.rowcount > 0:
                    total_stats["sessions_terminated"] += 1
                    
            except Exception as e:
                logger.error(f"Error logging out session {session_id}: {str(e)}")
        
        # 현재 세션 보존 여부
        current_session_preserved = action == 'all_except_current' and current_session_id not in sessions_to_logout
        
        # 감사 로그
        self._log_session_action(
            "user_multiple_sessions_logout",
            user_id=user_id,
            action=action,
            sessions_count=len(sessions_to_logout),
            reason=reason,
            stats=total_stats,
            db=db
        )
        
        db.commit()
        
        # 남은 세션 수 계산
        remaining_sessions = db.execute(
            text("SELECT COUNT(*) FROM oauth_sessions WHERE user_id = :user_id"),
            {"user_id": user_id}
        ).scalar()
        
        return {
            "success": True,
            "message": f"Successfully logged out from {total_stats['sessions_terminated']} sessions",
            "details": {
                **total_stats,
                "current_session_preserved": current_session_preserved
            },
            "remaining_sessions": remaining_sessions
        }
    
    def get_session_activity(
        self, 
        user_id: str, 
        days: int = 7, 
        limit: int = 50,
        db: Session
    ) -> Dict:
        """세션 활동 기록 조회"""
        # 로그인 시도 및 세션 활동 조회
        query = text("""
            SELECT 
                l.created_at as timestamp,
                l.action,
                l.client_id,
                l.ip_address,
                l.user_agent,
                l.success,
                l.error_code,
                c.client_name
            FROM oauth_audit_logs l
            LEFT JOIN oauth_clients c ON l.client_id = c.client_id
            WHERE l.user_id = :user_id
            AND l.created_at > NOW() - INTERVAL ':days days'
            AND l.action IN ('authorize', 'token', 'login', 'logout', 'revoke')
            ORDER BY l.created_at DESC
            LIMIT :limit
        """)
        
        result = db.execute(
            query, 
            {"user_id": user_id, "days": days, "limit": limit}
        )
        
        activities = []
        locations = set()
        devices = set()
        suspicious_count = 0
        
        for row in result:
            location = self._get_location_info(row.ip_address)
            device = self._parse_user_agent(row.user_agent)
            
            activity = {
                "timestamp": row.timestamp.isoformat(),
                "action": row.action,
                "client": row.client_name or row.client_id,
                "ip_address": self._mask_ip(row.ip_address),
                "location": f"{location['city']}, {location['country']}",
                "success": row.success,
                "device": f"{device['browser']} on {device['os']}"
            }
            
            # 의심스러운 활동 체크
            if self._is_suspicious_activity(activity, user_id, db):
                activity["flagged"] = True
                activity["flag_reason"] = "Unusual activity pattern"
                suspicious_count += 1
            
            activities.append(activity)
            locations.add(activity["location"])
            devices.add(device["type"])
        
        # 통계 생성
        total_logins = len([a for a in activities if a["action"] in ["authorize", "login"]])
        
        return {
            "activities": activities,
            "summary": {
                "total_logins": total_logins,
                "unique_locations": len(locations),
                "unique_devices": len(devices),
                "suspicious_activities": suspicious_count
            }
        }
    
    # Helper methods
    def _revoke_session_tokens(self, session_id: str, user_id: str, db: Session) -> Dict:
        """세션의 모든 토큰 해지"""
        stats = {"access_tokens": 0, "refresh_tokens": 0}
        
        # 세션과 연관된 클라이언트 ID 가져오기
        client_id = db.execute(
            text("SELECT client_id FROM oauth_sessions WHERE id = :session_id"),
            {"session_id": session_id}
        ).scalar()
        
        if client_id:
            # Access tokens 해지
            result = db.execute(
                text("""
                    UPDATE oauth_access_tokens 
                    SET revoked_at = NOW() 
                    WHERE user_id = :user_id 
                    AND client_id = :client_id 
                    AND revoked_at IS NULL
                """),
                {"user_id": user_id, "client_id": client_id}
            )
            stats["access_tokens"] = result.rowcount
            
            # Refresh tokens 해지
            result = db.execute(
                text("""
                    UPDATE oauth_refresh_tokens 
                    SET revoked_at = NOW() 
                    WHERE user_id = :user_id 
                    AND client_id = :client_id 
                    AND revoked_at IS NULL
                """),
                {"user_id": user_id, "client_id": client_id}
            )
            stats["refresh_tokens"] = result.rowcount
        
        return stats
    
    def _parse_user_agent(self, user_agent: str) -> Dict:
        """User Agent 파싱"""
        # 간단한 파싱 (실제로는 user-agents 라이브러리 사용 권장)
        device_type = "desktop"
        if "Mobile" in user_agent:
            device_type = "mobile"
        elif "Tablet" in user_agent:
            device_type = "tablet"
        
        browser = "Unknown"
        if "Chrome" in user_agent:
            browser = "Chrome"
        elif "Firefox" in user_agent:
            browser = "Firefox"
        elif "Safari" in user_agent:
            browser = "Safari"
        elif "Edge" in user_agent:
            browser = "Edge"
        
        os = "Unknown"
        if "Windows" in user_agent:
            os = "Windows"
        elif "Mac OS" in user_agent:
            os = "macOS"
        elif "Linux" in user_agent:
            os = "Linux"
        elif "Android" in user_agent:
            os = "Android"
        elif "iOS" in user_agent or "iPhone" in user_agent:
            os = "iOS"
        
        return {
            "type": device_type,
            "browser": browser,
            "os": os
        }
    
    def _get_location_info(self, ip_addr: str) -> Dict:
        """IP 주소로부터 위치 정보 추출"""
        default_location = {
            "ip": ip_addr,
            "city": "Unknown",
            "country": "Unknown"
        }
        
        if not self.geoip_reader or not ip_addr:
            return default_location
        
        try:
            # 사설 IP 체크
            ip_obj = ip_address(ip_addr)
            if ip_obj.is_private:
                return {
                    "ip": ip_addr,
                    "city": "Local",
                    "country": "Private Network"
                }
            
            # GeoIP 조회
            response = self.geoip_reader.city(ip_addr)
            return {
                "ip": ip_addr,
                "city": response.city.name or "Unknown",
                "country": response.country.iso_code or "Unknown"
            }
        except:
            return default_location
    
    def _check_suspicious_session(self, session: Dict, user_id: str, db: Session) -> Dict:
        """의심스러운 세션 감지"""
        suspicious_info = {
            "is_suspicious": False,
            "suspicious_reasons": []
        }
        
        # 1. 비정상적인 위치 확인
        user_locations = self._get_user_common_locations(user_id, db)
        current_location = session["location"]["country"]
        
        if current_location != "Unknown" and current_location not in user_locations:
            suspicious_info["is_suspicious"] = True
            suspicious_info["suspicious_reasons"].append("Unusual location")
        
        # 2. 장시간 미사용 후 갑작스런 활동
        if session["last_used_at"] and session["created_at"]:
            last_used = datetime.fromisoformat(session["last_used_at"])
            created = datetime.fromisoformat(session["created_at"])
            
            if (datetime.utcnow() - last_used).days > 30 and last_used != created:
                suspicious_info["is_suspicious"] = True
                suspicious_info["suspicious_reasons"].append("Long inactive period")
        
        # 3. 동시 다발적 위치 (불가능한 이동)
        recent_different_location = db.execute(
            text("""
                SELECT COUNT(DISTINCT client_ip) 
                FROM oauth_sessions 
                WHERE user_id = :user_id 
                AND last_used_at > NOW() - INTERVAL '1 hour'
                AND id != :session_id
            """),
            {"user_id": user_id, "session_id": session["session_id"]}
        ).scalar()
        
        if recent_different_location > 2:
            suspicious_info["is_suspicious"] = True
            suspicious_info["suspicious_reasons"].append("Multiple locations in short time")
        
        if suspicious_info["is_suspicious"]:
            suspicious_info["suspicious_reason"] = ", ".join(suspicious_info["suspicious_reasons"])
        
        return suspicious_info
    
    def _get_user_common_locations(self, user_id: str, db: Session) -> set:
        """사용자의 일반적인 위치 목록"""
        result = db.execute(
            text("""
                SELECT DISTINCT 
                    SUBSTRING(client_ip FROM '^[0-9]+\.[0-9]+') as ip_prefix
                FROM oauth_sessions 
                WHERE user_id = :user_id 
                AND created_at > NOW() - INTERVAL '30 days'
                LIMIT 10
            """),
            {"user_id": user_id}
        )
        
        # 실제로는 GeoIP로 국가 정보를 저장하고 조회해야 함
        return {"KR", "US"}  # 예시
    
    def _mask_ip(self, ip_addr: str) -> str:
        """IP 주소 마스킹"""
        if not ip_addr:
            return "Unknown"
        
        parts = ip_addr.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.xxx.xxx.{parts[3]}"
        return "xxx.xxx.xxx.xxx"

# 싱글톤 인스턴스
user_session_service = UserSessionService()
```

### 2. API Router

```python
# app/routers/user_sessions.py

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from ..database import get_db
from ..models import User
from ..services.user_session_service import user_session_service
from ..utils.auth import get_current_user, get_current_session_id
from ..schemas.user_sessions import (
    SessionListResponse,
    SessionLogoutRequest,
    MultipleSessionLogoutRequest,
    SessionActivityResponse,
    CurrentSessionResponse
)

router = APIRouter(
    prefix="/api/user/sessions",
    tags=["User Sessions"],
    dependencies=[Depends(get_current_user)]
)

@router.get("", response_model=SessionListResponse)
async def get_user_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자의 모든 활성 세션 조회"""
    sessions = user_session_service.get_user_sessions(
        str(current_user.id), 
        db
    )
    return sessions

@router.get("/current", response_model=CurrentSessionResponse)
async def get_current_session(
    current_user: User = Depends(get_current_user),
    current_session_id: str = Depends(get_current_session_id),
    db: Session = Depends(get_db)
):
    """현재 세션 정보 조회"""
    # 현재 세션 정보 조회
    result = db.execute(
        text("""
            SELECT 
                s.id, s.client_id, s.granted_scopes, 
                s.created_at, s.client_ip, s.user_agent,
                c.client_name,
                t.expires_at
            FROM oauth_sessions s
            JOIN oauth_clients c ON s.client_id = c.client_id
            LEFT JOIN oauth_access_tokens t ON t.user_id = s.user_id 
                AND t.client_id = s.client_id 
                AND t.revoked_at IS NULL
                AND t.expires_at > NOW()
            WHERE s.id = :session_id
            LIMIT 1
        """),
        {"session_id": current_session_id}
    ).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Current session not found")
    
    return CurrentSessionResponse(
        session_id=str(result.id),
        user_id=str(current_user.id),
        client={
            "id": result.client_id,
            "name": result.client_name
        },
        created_at=result.created_at,
        expires_at=result.expires_at,
        scopes=result.granted_scopes or [],
        ip_address=result.client_ip,
        user_agent=result.user_agent
    )

@router.post("/{session_id}/logout")
async def logout_single_session(
    session_id: str,
    request: SessionLogoutRequest = Body(default={}),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """단일 세션 로그아웃"""
    try:
        result = user_session_service.logout_single_session(
            user_id=str(current_user.id),
            session_id=session_id,
            reason=request.reason,
            db=db
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/logout-multiple")
async def logout_multiple_sessions(
    request: MultipleSessionLogoutRequest,
    current_user: User = Depends(get_current_user),
    current_session_id: str = Depends(get_current_session_id),
    db: Session = Depends(get_db)
):
    """다중 세션 로그아웃"""
    try:
        result = user_session_service.logout_multiple_sessions(
            user_id=str(current_user.id),
            action=request.action,
            session_ids=request.session_ids,
            password=request.password,
            reason=request.reason,
            current_session_id=current_session_id,
            db=db
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/activity", response_model=SessionActivityResponse)
async def get_session_activity(
    days: int = 7,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """세션 활동 기록 조회"""
    if days > 30:
        days = 30
    if limit > 100:
        limit = 100
    
    activity = user_session_service.get_session_activity(
        user_id=str(current_user.id),
        days=days,
        limit=limit,
        db=db
    )
    return activity

@router.post("/logout-current")
async def logout_current_session(
    current_user: User = Depends(get_current_user),
    current_session_id: str = Depends(get_current_session_id),
    db: Session = Depends(get_db)
):
    """현재 세션만 로그아웃 (일반 로그아웃)"""
    try:
        result = user_session_service.logout_single_session(
            user_id=str(current_user.id),
            session_id=current_session_id,
            reason="User logout",
            db=db
        )
        
        # 로그아웃 후 쿠키 삭제 등의 추가 처리
        response = JSONResponse(content=result)
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        
        return response
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(status_code=500, detail="Logout failed")
```

## 보안 고려사항

### 1. 세션 보안
- 현재 세션 확인을 위한 안전한 방법 구현
- 다른 사용자의 세션에 접근 불가
- 의심스러운 활동 자동 감지

### 2. 인증 강화
- 대량 로그아웃 시 비밀번호 재확인
- 2FA가 활성화된 경우 추가 인증
- Rate limiting으로 악용 방지

### 3. 감사 및 알림
- 모든 로그아웃 활동 기록
- 비정상적인 로그아웃 패턴 감지
- 중요 활동 시 이메일/SMS 알림

## 구현 우선순위

1. **Phase 1: 기본 기능**
   - 세션 목록 조회 API
   - 단일 세션 로그아웃
   - 현재 세션 정보

2. **Phase 2: 다중 로그아웃**
   - 다중 세션 로그아웃 API
   - 로그아웃 확인 모달
   - 세션 관리 UI

3. **Phase 3: 고급 기능**
   - 세션 활동 기록
   - 의심스러운 세션 감지
   - 위치 기반 분석
   - 실시간 알림