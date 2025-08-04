# 클라이언트 세션 로그아웃 선택 모달 구현 가이드

## 개요

MAX Platform의 배치 로그아웃 시스템을 기반으로 클라이언트 애플리케이션에서 사용자가 세션 로그아웃 방식을 선택할 수 있는 모달을 구현하는 방법을 안내합니다. 사용자는 현재 세션만 로그아웃하거나 모든 세션에서 로그아웃하는 옵션을 선택할 수 있습니다.

## 핵심 기능

- **현재 세션만 로그아웃**: 현재 디바이스/브라우저에서만 로그아웃
- **모든 세션 로그아웃**: 모든 디바이스에서 동시 로그아웃
- **세션 정보 표시**: 현재 세션 및 다른 활성 세션 목록
- **보안 경고**: 의심스러운 세션 감지 시 경고 표시
- **사용자 친화적 UI**: 직관적인 선택 인터페이스

## API 엔드포인트

### 1. 활성 세션 조회

```http
GET /api/user/sessions/active
Authorization: Bearer {access_token}
Content-Type: application/json
```

**응답 예시:**
```json
{
  "current_session": {
    "session_id": "sess-current-123",
    "client_id": "web-app",
    "client_name": "MAX Platform Web",
    "created_at": "2025-01-29T10:00:00Z",
    "last_used_at": "2025-01-29T14:30:00Z",
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0...",
    "device_info": {
      "device_type": "desktop",
      "browser": "Chrome",
      "os": "Windows 10"
    },
    "location": {
      "country": "대한민국",
      "city": "서울"
    },
    "is_current_session": true,
    "is_suspicious": false
  },
  "other_sessions": [
    {
      "session_id": "sess-mobile-456",
      "client_id": "mobile-app",
      "client_name": "MAX Platform Mobile",
      "created_at": "2025-01-28T09:00:00Z",
      "last_used_at": "2025-01-29T12:00:00Z",
      "device_info": {
        "device_type": "mobile",
        "browser": "Safari",
        "os": "iOS 17"
      },
      "is_current_session": false,
      "is_suspicious": false
    }
  ],
  "total_sessions": 2,
  "suspicious_sessions": 0
}
```

### 2. 사용자 로그아웃

```http
POST /api/user/sessions/logout
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "logout_type": "current|all",
  "reason": "User requested logout"
}
```

**응답 예시:**
```json
{
  "message": "Successfully logged out current sessions",
  "logout_type": "current",
  "sessions_terminated": 1,
  "tokens_revoked": 2
}
```

### 3. 특정 세션 로그아웃 (선택사항)

```http
POST /api/user/sessions/logout-sessions
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "session_ids": ["sess-mobile-456", "sess-tablet-789"],
  "reason": "User selected specific sessions"
}
```

## 구현 예시

### 1. React 구현

#### 세션 로그아웃 훅 (useSessionLogout.js)

```javascript
import { useState, useCallback } from 'react';

export const useSessionLogout = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [sessionsData, setSessionsData] = useState(null);

  // 활성 세션 조회
  const fetchActiveSessions = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/user/sessions/active', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch sessions: ${response.status}`);
      }

      const data = await response.json();
      setSessionsData(data);
      return data;
    } catch (error) {
      console.error('Error fetching active sessions:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  // 로그아웃 실행
  const executeLogout = useCallback(async (logoutType, reason) => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/user/sessions/logout', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          logout_type: logoutType,
          reason: reason || `User requested ${logoutType} logout`
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Logout failed: ${response.status}`);
      }

      const data = await response.json();

      // 로그아웃 후 처리
      setTimeout(() => {
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        window.location.href = '/login';
      }, 1000);

      return data;
    } catch (error) {
      console.error('Error during logout:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    isLoading,
    sessionsData,
    fetchActiveSessions,
    executeLogout,
  };
};
```

#### 세션 로그아웃 모달 컴포넌트

```jsx
import React, { useState, useEffect } from 'react';
import { useSessionLogout } from './hooks/useSessionLogout';

const SessionLogoutModal = ({ isOpen, onClose, onSuccess }) => {
  const [logoutType, setLogoutType] = useState('current');
  const { isLoading, sessionsData, fetchActiveSessions, executeLogout } = useSessionLogout();

  useEffect(() => {
    if (isOpen) {
      fetchActiveSessions();
    }
  }, [isOpen, fetchActiveSessions]);

  const handleLogout = async () => {
    try {
      await executeLogout(logoutType);
      onSuccess?.();
      onClose();
    } catch (error) {
      alert(`로그아웃 실패: ${error.message}`);
    }
  };

  if (!isOpen) return null;

  const { current_session, other_sessions = [], total_sessions, suspicious_sessions } = sessionsData || {};

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>로그아웃 옵션 선택</h2>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        <div className="modal-body">
          {/* 세션 요약 */}
          <div className="session-summary">
            <p>총 {total_sessions}개의 활성 세션이 있습니다.</p>
            {suspicious_sessions > 0 && (
              <div className="warning-alert">
                ⚠️ {suspicious_sessions}개의 의심스러운 세션이 감지되었습니다. 
                보안을 위해 모든 세션에서 로그아웃하는 것을 권장합니다.
              </div>
            )}
          </div>

          {/* 로그아웃 옵션 선택 */}
          <div className="logout-options">
            <h3>로그아웃 옵션:</h3>
            
            <label className="option-radio">
              <input
                type="radio"
                name="logoutType"
                value="current"
                checked={logoutType === 'current'}
                onChange={(e) => setLogoutType(e.target.value)}
              />
              <div className="option-content">
                <strong>현재 세션만 로그아웃</strong>
                <p>이 디바이스/브라우저에서만 로그아웃됩니다. 다른 디바이스의 세션은 유지됩니다.</p>
              </div>
            </label>

            <label className="option-radio">
              <input
                type="radio"
                name="logoutType"
                value="all"
                checked={logoutType === 'all'}
                onChange={(e) => setLogoutType(e.target.value)}
              />
              <div className="option-content">
                <strong>모든 세션에서 로그아웃</strong>
                <p>모든 디바이스와 브라우저에서 로그아웃됩니다. 다시 로그인해야 합니다.</p>
              </div>
            </label>
          </div>

          {/* 현재 세션 정보 */}
          {current_session && (
            <div className="current-session">
              <h4>현재 세션:</h4>
              <div className="session-item current">
                <div className="session-info">
                  <span className="client-name">{current_session.client_name}</span>
                  <span className="current-badge">(현재 세션)</span>
                  {current_session.is_suspicious && <span className="suspicious-badge">⚠️ 의심스러운 활동</span>}
                </div>
                <div className="session-details">
                  <p>{current_session.device_info?.browser} • {current_session.device_info?.os}</p>
                  <p>{current_session.location?.city}, {current_session.location?.country}</p>
                  <p>마지막 사용: {new Date(current_session.last_used_at || current_session.created_at).toLocaleString('ko-KR')}</p>
                </div>
              </div>
            </div>
          )}

          {/* 다른 세션 목록 */}
          {other_sessions.length > 0 && (
            <div className="other-sessions">
              <h4>다른 활성 세션 ({other_sessions.length}개):</h4>
              <div className="sessions-list">
                {other_sessions.map((session) => (
                  <div key={session.session_id} className="session-item">
                    <div className="session-info">
                      <span className="client-name">{session.client_name}</span>
                      {session.is_suspicious && <span className="suspicious-badge">⚠️ 의심스러운 활동</span>}
                    </div>
                    <div className="session-details">
                      <p>{session.device_info?.browser} • {session.device_info?.os}</p>
                      <p>{session.location?.city}, {session.location?.country}</p>
                      <p>마지막 사용: {new Date(session.last_used_at || session.created_at).toLocaleString('ko-KR')}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 보안 안내 */}
          <div className="security-notice">
            <h4>보안 권고사항:</h4>
            <ul>
              <li>공용 컴퓨터나 의심스러운 디바이스에서 로그인한 경우 모든 세션에서 로그아웃하세요.</li>
              <li>정기적으로 활성 세션을 확인하고 인식하지 못하는 세션을 제거하세요.</li>
            </ul>
          </div>
        </div>

        <div className="modal-footer">
          <button className="cancel-button" onClick={onClose} disabled={isLoading}>
            취소
          </button>
          <button 
            className={`logout-button ${logoutType === 'all' ? 'danger' : 'primary'}`}
            onClick={handleLogout}
            disabled={isLoading}
          >
            {isLoading ? '로그아웃 중...' : (logoutType === 'current' ? '현재 세션 로그아웃' : '모든 세션 로그아웃')}
          </button>
        </div>
      </div>
    </div>
  );
};

export default SessionLogoutModal;
```

### 2. Vue.js 구현

#### 세션 로그아웃 컴포저블

```javascript
// composables/useSessionLogout.js
import { ref, reactive } from 'vue';

export function useSessionLogout() {
  const isLoading = ref(false);
  const sessionsData = ref(null);

  const fetchActiveSessions = async () => {
    isLoading.value = true;
    try {
      const response = await fetch('/api/user/sessions/active', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch sessions: ${response.status}`);
      }

      const data = await response.json();
      sessionsData.value = data;
      return data;
    } catch (error) {
      console.error('Error fetching active sessions:', error);
      throw error;
    } finally {
      isLoading.value = false;
    }
  };

  const executeLogout = async (logoutType, reason) => {
    isLoading.value = true;
    try {
      const response = await fetch('/api/user/sessions/logout', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          logout_type: logoutType,
          reason: reason || `User requested ${logoutType} logout`
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Logout failed: ${response.status}`);
      }

      const data = await response.json();

      // 로그아웃 후 처리
      setTimeout(() => {
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        window.location.href = '/login';
      }, 1000);

      return data;
    } catch (error) {
      console.error('Error during logout:', error);
      throw error;
    } finally {
      isLoading.value = false;
    }
  };

  return {
    isLoading,
    sessionsData,
    fetchActiveSessions,
    executeLogout,
  };
}
```

#### Vue 컴포넌트

```vue
<template>
  <div v-if="isOpen" class="modal-overlay" @click="$emit('close')">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h2>로그아웃 옵션 선택</h2>
        <button class="close-button" @click="$emit('close')">×</button>
      </div>

      <div class="modal-body">
        <!-- 세션 요약 -->
        <div class="session-summary">
          <p>총 {{ sessionsData?.total_sessions || 0 }}개의 활성 세션이 있습니다.</p>
          <div v-if="(sessionsData?.suspicious_sessions || 0) > 0" class="warning-alert">
            ⚠️ {{ sessionsData.suspicious_sessions }}개의 의심스러운 세션이 감지되었습니다. 
            보안을 위해 모든 세션에서 로그아웃하는 것을 권장합니다.
          </div>
        </div>

        <!-- 로그아웃 옵션 선택 -->
        <div class="logout-options">
          <h3>로그아웃 옵션:</h3>
          
          <label class="option-radio">
            <input
              type="radio"
              v-model="logoutType"
              value="current"
            />
            <div class="option-content">
              <strong>현재 세션만 로그아웃</strong>
              <p>이 디바이스/브라우저에서만 로그아웃됩니다. 다른 디바이스의 세션은 유지됩니다.</p>
            </div>
          </label>

          <label class="option-radio">
            <input
              type="radio"
              v-model="logoutType"
              value="all"
            />
            <div class="option-content">
              <strong>모든 세션에서 로그아웃</strong>
              <p>모든 디바이스와 브라우저에서 로그아웃됩니다. 다시 로그인해야 합니다.</p>
            </div>
          </label>
        </div>

        <!-- 현재 세션 정보 -->
        <div v-if="sessionsData?.current_session" class="current-session">
          <h4>현재 세션:</h4>
          <SessionItem :session="sessionsData.current_session" :is-current="true" />
        </div>

        <!-- 다른 세션 목록 -->
        <div v-if="sessionsData?.other_sessions?.length > 0" class="other-sessions">
          <h4>다른 활성 세션 ({{ sessionsData.other_sessions.length }}개):</h4>
          <div class="sessions-list">
            <SessionItem
              v-for="session in sessionsData.other_sessions"
              :key="session.session_id"
              :session="session"
            />
          </div>
        </div>

        <!-- 보안 안내 -->
        <div class="security-notice">
          <h4>보안 권고사항:</h4>
          <ul>
            <li>공용 컴퓨터나 의심스러운 디바이스에서 로그인한 경우 모든 세션에서 로그아웃하세요.</li>
            <li>정기적으로 활성 세션을 확인하고 인식하지 못하는 세션을 제거하세요.</li>
          </ul>
        </div>
      </div>

      <div class="modal-footer">
        <button class="cancel-button" @click="$emit('close')" :disabled="isLoading">
          취소
        </button>
        <button 
          :class="['logout-button', logoutType === 'all' ? 'danger' : 'primary']"
          @click="handleLogout"
          :disabled="isLoading"
        >
          {{ isLoading ? '로그아웃 중...' : (logoutType === 'current' ? '현재 세션 로그아웃' : '모든 세션 로그아웃') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, watch } from 'vue';
import { useSessionLogout } from '@/composables/useSessionLogout';
import SessionItem from './SessionItem.vue';

export default {
  name: 'SessionLogoutModal',
  components: {
    SessionItem,
  },
  props: {
    isOpen: {
      type: Boolean,
      default: false,
    },
  },
  emits: ['close', 'success'],
  setup(props, { emit }) {
    const logoutType = ref('current');
    const { isLoading, sessionsData, fetchActiveSessions, executeLogout } = useSessionLogout();

    watch(() => props.isOpen, (isOpen) => {
      if (isOpen) {
        fetchActiveSessions();
      }
    });

    const handleLogout = async () => {
      try {
        await executeLogout(logoutType.value);
        emit('success');
        emit('close');
      } catch (error) {
        alert(`로그아웃 실패: ${error.message}`);
      }
    };

    return {
      logoutType,
      isLoading,
      sessionsData,
      handleLogout,
    };
  },
};
</script>
```

### 3. Vanilla JavaScript 구현

```javascript
class SessionLogoutModal {
  constructor(options = {}) {
    this.options = {
      modalId: 'sessionLogoutModal',
      onSuccess: null,
      onClose: null,
      ...options
    };
    
    this.isLoading = false;
    this.sessionsData = null;
    this.logoutType = 'current';
    
    this.init();
  }

  init() {
    this.createModal();
    this.bindEvents();
  }

  createModal() {
    const modalHTML = `
      <div id="${this.options.modalId}" class="modal-overlay" style="display: none;">
        <div class="modal-content">
          <div class="modal-header">
            <h2>로그아웃 옵션 선택</h2>
            <button class="close-button">×</button>
          </div>
          <div class="modal-body">
            <div class="session-summary"></div>
            <div class="logout-options">
              <h3>로그아웃 옵션:</h3>
              <label class="option-radio">
                <input type="radio" name="logoutType" value="current" checked>
                <div class="option-content">
                  <strong>현재 세션만 로그아웃</strong>
                  <p>이 디바이스/브라우저에서만 로그아웃됩니다. 다른 디바이스의 세션은 유지됩니다.</p>
                </div>
              </label>
              <label class="option-radio">
                <input type="radio" name="logoutType" value="all">
                <div class="option-content">
                  <strong>모든 세션에서 로그아웃</strong>
                  <p>모든 디바이스와 브라우저에서 로그아웃됩니다. 다시 로그인해야 합니다.</p>
                </div>
              </label>
            </div>
            <div class="sessions-display"></div>
            <div class="security-notice">
              <h4>보안 권고사항:</h4>
              <ul>
                <li>공용 컴퓨터나 의심스러운 디바이스에서 로그인한 경우 모든 세션에서 로그아웃하세요.</li>
                <li>정기적으로 활성 세션을 확인하고 인식하지 못하는 세션을 제거하세요.</li>
              </ul>
            </div>
          </div>
          <div class="modal-footer">
            <button class="cancel-button">취소</button>
            <button class="logout-button primary">현재 세션 로그아웃</button>
          </div>
        </div>
      </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    this.modal = document.getElementById(this.options.modalId);
  }

  bindEvents() {
    // 닫기 버튼
    this.modal.querySelector('.close-button').addEventListener('click', () => this.close());
    this.modal.querySelector('.cancel-button').addEventListener('click', () => this.close());
    
    // 오버레이 클릭
    this.modal.addEventListener('click', (e) => {
      if (e.target === this.modal) this.close();
    });

    // 로그아웃 타입 변경
    this.modal.querySelectorAll('input[name="logoutType"]').forEach(radio => {
      radio.addEventListener('change', (e) => {
        this.logoutType = e.target.value;
        this.updateLogoutButton();
      });
    });

    // 로그아웃 버튼
    this.modal.querySelector('.logout-button').addEventListener('click', () => this.handleLogout());
  }

  async open() {
    this.modal.style.display = 'flex';
    await this.fetchActiveSessions();
  }

  close() {
    this.modal.style.display = 'none';
    if (this.options.onClose) this.options.onClose();
  }

  async fetchActiveSessions() {
    this.setLoading(true);
    try {
      const response = await fetch('/api/user/sessions/active', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch sessions: ${response.status}`);
      }

      this.sessionsData = await response.json();
      this.renderSessions();
    } catch (error) {
      console.error('Error fetching active sessions:', error);
      alert('세션 정보를 가져오는 중 오류가 발생했습니다.');
    } finally {
      this.setLoading(false);
    }
  }

  async handleLogout() {
    this.setLoading(true);
    try {
      const response = await fetch('/api/user/sessions/logout', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          logout_type: this.logoutType,
          reason: `User requested ${this.logoutType} logout`
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Logout failed: ${response.status}`);
      }

      const data = await response.json();
      
      if (this.options.onSuccess) this.options.onSuccess(data);
      this.close();

      // 로그아웃 후 처리
      setTimeout(() => {
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        window.location.href = '/login';
      }, 1000);

    } catch (error) {
      console.error('Error during logout:', error);
      alert(`로그아웃 실패: ${error.message}`);
    } finally {
      this.setLoading(false);
    }
  }

  setLoading(loading) {
    this.isLoading = loading;
    const button = this.modal.querySelector('.logout-button');
    button.disabled = loading;
    button.textContent = loading ? '로그아웃 중...' : 
      (this.logoutType === 'current' ? '현재 세션 로그아웃' : '모든 세션 로그아웃');
  }

  updateLogoutButton() {
    const button = this.modal.querySelector('.logout-button');
    button.textContent = this.logoutType === 'current' ? '현재 세션 로그아웃' : '모든 세션 로그아웃';
    button.className = `logout-button ${this.logoutType === 'all' ? 'danger' : 'primary'}`;
  }

  renderSessions() {
    if (!this.sessionsData) return;

    // 세션 요약 렌더링
    const summaryEl = this.modal.querySelector('.session-summary');
    let summaryHTML = `<p>총 ${this.sessionsData.total_sessions}개의 활성 세션이 있습니다.</p>`;
    
    if (this.sessionsData.suspicious_sessions > 0) {
      summaryHTML += `
        <div class="warning-alert">
          ⚠️ ${this.sessionsData.suspicious_sessions}개의 의심스러운 세션이 감지되었습니다. 
          보안을 위해 모든 세션에서 로그아웃하는 것을 권장합니다.
        </div>
      `;
    }
    summaryEl.innerHTML = summaryHTML;

    // 세션 목록 렌더링
    const sessionsEl = this.modal.querySelector('.sessions-display');
    let sessionsHTML = '';

    if (this.sessionsData.current_session) {
      sessionsHTML += `
        <div class="current-session">
          <h4>현재 세션:</h4>
          ${this.renderSessionItem(this.sessionsData.current_session, true)}
        </div>
      `;
    }

    if (this.sessionsData.other_sessions?.length > 0) {
      sessionsHTML += `
        <div class="other-sessions">
          <h4>다른 활성 세션 (${this.sessionsData.other_sessions.length}개):</h4>
          <div class="sessions-list">
            ${this.sessionsData.other_sessions.map(session => this.renderSessionItem(session)).join('')}
          </div>
        </div>
      `;
    }

    sessionsEl.innerHTML = sessionsHTML;
  }

  renderSessionItem(session, isCurrent = false) {
    return `
      <div class="session-item ${isCurrent ? 'current' : ''}">
        <div class="session-info">
          <span class="client-name">${session.client_name}</span>
          ${isCurrent ? '<span class="current-badge">(현재 세션)</span>' : ''}
          ${session.is_suspicious ? '<span class="suspicious-badge">⚠️ 의심스러운 활동</span>' : ''}
        </div>
        <div class="session-details">
          <p>${session.device_info?.browser || '알 수 없음'} • ${session.device_info?.os || '알 수 없음'}</p>
          <p>${session.location?.city || '위치 정보 없음'}, ${session.location?.country || ''}</p>
          <p>마지막 사용: ${new Date(session.last_used_at || session.created_at).toLocaleString('ko-KR')}</p>
        </div>
      </div>
    `;
  }
}

// 사용 예시
const logoutModal = new SessionLogoutModal({
  onSuccess: (data) => {
    console.log('Logout successful:', data);
  },
  onClose: () => {
    console.log('Modal closed');
  }
});

// 모달 열기
document.getElementById('logoutButton').addEventListener('click', () => {
  logoutModal.open();
});
```

## CSS 스타일

```css
/* 모달 기본 스타일 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 8px;
  max-width: 600px;
  width: 90%;
  max-height: 80vh;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #e0e0e0;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
}

.close-button {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #666;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-button:hover {
  color: #333;
}

.modal-body {
  padding: 20px;
  max-height: 60vh;
  overflow-y: auto;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 20px;
  border-top: 1px solid #e0e0e0;
  background: #f8f9fa;
}

/* 세션 요약 */
.session-summary {
  margin-bottom: 20px;
}

.warning-alert {
  background: #fff3cd;
  border: 1px solid #ffeeba;
  color: #856404;
  padding: 12px;
  border-radius: 4px;
  margin-top: 8px;
  font-size: 0.9rem;
}

/* 로그아웃 옵션 */
.logout-options {
  margin-bottom: 20px;
}

.logout-options h3 {
  margin-bottom: 15px;
  font-size: 1.1rem;
  font-weight: 600;
}

.option-radio {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 15px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  margin-bottom: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.option-radio:hover {
  border-color: #007bff;
  background: #f8f9ff;
}

.option-radio input[type="radio"] {
  margin-top: 2px;
}

.option-radio input[type="radio"]:checked + .option-content {
  color: #007bff;
}

.option-content strong {
  display: block;
  margin-bottom: 4px;
  font-weight: 600;
}

.option-content p {
  margin: 0;
  font-size: 0.9rem;
  color: #666;
  line-height: 1.4;
}

/* 세션 정보 */
.current-session,
.other-sessions {
  margin-bottom: 20px;
}

.current-session h4,
.other-sessions h4 {
  margin-bottom: 10px;
  font-size: 1rem;
  font-weight: 600;
}

.sessions-list {
  max-height: 200px;
  overflow-y: auto;
}

.session-item {
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 8px;
  background: white;
}

.session-item.current {
  border-color: #007bff;
  background: #f8f9ff;
}

.session-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.client-name {
  font-weight: 600;
  font-size: 0.9rem;
}

.current-badge {
  background: #007bff;
  color: white;
  font-size: 0.75rem;
  padding: 2px 6px;
  border-radius: 4px;
}

.suspicious-badge {
  background: #dc3545;
  color: white;
  font-size: 0.75rem;
  padding: 2px 6px;
  border-radius: 4px;
}

.session-details p {
  margin: 2px 0;
  font-size: 0.8rem;
  color: #666;
}

/* 보안 안내 */
.security-notice {
  background: #e7f3ff;
  border: 1px solid #b3d7ff;
  border-radius: 6px;
  padding: 15px;
  margin-top: 20px;
}

.security-notice h4 {
  margin: 0 0 10px 0;
  font-size: 0.95rem;
  color: #0056b3;
}

.security-notice ul {
  margin: 0;
  padding-left: 20px;
}

.security-notice li {
  font-size: 0.85rem;
  color: #0056b3;
  margin-bottom: 5px;
  line-height: 1.4;
}

/* 버튼 스타일 */
.cancel-button {
  background: none;
  border: 1px solid #ddd;
  color: #666;
  padding: 10px 20px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s ease;
}

.cancel-button:hover:not(:disabled) {
  background: #f5f5f5;
  border-color: #ccc;
}

.logout-button {
  border: none;
  color: white;
  padding: 10px 20px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.2s ease;
}

.logout-button.primary {
  background: #007bff;
}

.logout-button.primary:hover:not(:disabled) {
  background: #0056b3;
}

.logout-button.danger {
  background: #dc3545;
}

.logout-button.danger:hover:not(:disabled) {
  background: #c82333;
}

.logout-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 반응형 */
@media (max-width: 768px) {
  .modal-content {
    width: 95%;
    margin: 20px;
  }
  
  .modal-body {
    max-height: 70vh;
  }
  
  .option-radio {
    padding: 12px;
  }
  
  .session-item {
    padding: 10px;
  }
  
  .modal-footer {
    flex-direction: column;
  }
  
  .modal-footer button {
    width: 100%;
  }
}
```

## 보안 고려사항

### 1. 인증 및 권한 검증
- 모든 API 호출에 유효한 액세스 토큰 필요
- 사용자는 본인의 세션만 관리 가능
- 세션 정보는 민감한 데이터를 최소화하여 제공

### 2. 세션 보안
- 의심스러운 세션 감지 시 경고 표시
- 공용 디바이스 사용 시 모든 세션 로그아웃 권장
- 로그아웃 후 클라이언트 토큰 즉시 제거

### 3. UI/UX 보안
- 로그아웃 타입별로 적절한 경고 메시지 표시
- 의심스러운 세션 존재 시 시각적 경고
- 사용자 실수 방지를 위한 명확한 옵션 설명

### 4. 에러 처리
- 네트워크 오류 시 사용자 친화적 메시지
- 세션 만료 시 자동 로그인 페이지 리다이렉트
- API 오류 시 상세 오류 정보 로깅 (사용자에게는 일반 메시지)

## UI/UX 가이드라인

### 1. 사용자 선택 지원
- 기본값은 '현재 세션만 로그아웃'으로 설정
- 의심스러운 세션 감지 시 '모든 세션 로그아웃' 권장
- 각 옵션의 결과를 명확히 설명

### 2. 세션 정보 표시
- 현재 세션과 다른 세션을 명확히 구분
- 디바이스 타입, 브라우저, 위치 정보 표시
- 마지막 사용 시간으로 세션 활성도 표시

### 3. 접근성 고려
- 키보드 네비게이션 지원
- 스크린 리더 호환성
- 적절한 색상 대비
- 모바일 친화적 터치 인터페이스

### 4. 반응형 디자인
- 다양한 화면 크기 대응
- 모바일에서도 편리한 사용성
- 터치 친화적 버튼 크기

## 구현 체크리스트

### 필수 기능
- [ ] 활성 세션 목록 조회
- [ ] 현재 세션만 로그아웃 기능
- [ ] 모든 세션 로그아웃 기능
- [ ] 세션 정보 표시 (디바이스, 위치, 시간)
- [ ] 의심스러운 세션 감지 및 경고
- [ ] 로그아웃 후 토큰 정리 및 리다이렉트

### 선택 기능
- [ ] 특정 세션 선택 로그아웃
- [ ] 세션 활동 기록 조회
- [ ] 다국어 지원
- [ ] 다크 모드 지원
- [ ] 애니메이션 효과

### 보안 체크리스트
- [ ] API 인증 토큰 검증
- [ ] 클라이언트 토큰 안전한 저장
- [ ] 로그아웃 후 토큰 완전 제거
- [ ] 의심스러운 활동 감지 로직
- [ ] 에러 정보 보안 처리

### 테스트 항목
- [ ] 정상 로그아웃 플로우
- [ ] 네트워크 오류 처리
- [ ] 토큰 만료 시나리오
- [ ] 다양한 디바이스에서 동작 확인
- [ ] 접근성 테스트
- [ ] 성능 테스트

## 마무리

이 가이드를 통해 사용자 친화적이고 보안성이 높은 세션 로그아웃 선택 모달을 구현할 수 있습니다. 각 프레임워크별 예시 코드를 참고하여 프로젝트에 맞는 구현을 선택하고, 보안 고려사항과 UI/UX 가이드라인을 준수하여 안전하고 사용하기 쉬운 기능을 제공하세요.

추가 질문이나 구현 과정에서 문제가 발생하면 MAX Platform 개발팀에 문의하시기 바랍니다.