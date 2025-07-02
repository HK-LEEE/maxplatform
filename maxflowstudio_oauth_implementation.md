# maxflowstudio OAuth 2.0 팝업 로그인 구현 가이드

## 1. OAuth 유틸리티 파일 생성

### `/src/utils/popupOAuth.js`

```javascript
const OAUTH_SERVER = 'http://localhost:8000/api/oauth';
const CLIENT_ID = 'maxflowstudio';
const REDIRECT_URI = 'http://localhost:3005/oauth/callback';

// PKCE 구현
function generateCodeVerifier() {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  return base64URLEncode(array);
}

async function generateCodeChallenge(verifier) {
  const encoder = new TextEncoder();
  const data = encoder.encode(verifier);
  const digest = await crypto.subtle.digest('SHA-256', data);
  return base64URLEncode(new Uint8Array(digest));
}

function base64URLEncode(array) {
  return btoa(String.fromCharCode(...array))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');
}

// 팝업 OAuth 로그인 클래스
export class PopupOAuthLogin {
  constructor() {
    this.popup = null;
    this.checkInterval = null;
  }
  
  async exchangeCodeForToken(code) {
    const codeVerifier = sessionStorage.getItem('oauth_code_verifier');
    
    const response = await fetch(`${OAUTH_SERVER}/token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        code: code,
        redirect_uri: REDIRECT_URI,
        client_id: CLIENT_ID,
        client_secret: 'secret_flowstudio_2025_dev', // 프로덕션에서는 백엔드에서 처리
        code_verifier: codeVerifier
      })
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error_description || 'Token exchange failed');
    }
    
    return response.json();
  }

  async startAuth() {
    return new Promise(async (resolve, reject) => {
      try {
        // PKCE 파라미터 생성
        const state = generateCodeVerifier();
        const codeVerifier = generateCodeVerifier();
        const codeChallenge = await generateCodeChallenge(codeVerifier);
        
        // 세션 스토리지에 저장
        sessionStorage.setItem('oauth_state', state);
        sessionStorage.setItem('oauth_code_verifier', codeVerifier);
        
        // OAuth 요청 URL 생성
        const params = new URLSearchParams({
          response_type: 'code',
          client_id: CLIENT_ID,
          redirect_uri: REDIRECT_URI,
          scope: 'read:profile read:groups manage:workflows',
          state: state,
          code_challenge: codeChallenge,
          code_challenge_method: 'S256',
          display: 'popup'  // 팝업 모드 지정
        });
        
        const authUrl = `${OAUTH_SERVER}/authorize?${params}`;
        
        // 표준 OAuth 팝업 열기 (단순하고 안정적인 방법)
        this.popup = window.open(
          authUrl,
          'oauth_login',
          'width=500,height=600,scrollbars=yes,resizable=yes'
        );
        
        if (!this.popup) {
          reject(new Error('팝업이 차단되었습니다. 팝업 차단을 해제하고 다시 시도해주세요.'));
          return;
        }
        
        // PostMessage 이벤트 리스너
        const messageHandler = (event) => {
          // 보안: origin 체크
          if (event.origin !== window.location.origin) {
            return;
          }
          
          if (event.data.type === 'OAUTH_SUCCESS') {
            // 백엔드에서 직접 전달된 authorization code 처리
            if (event.data.code) {
              // 토큰 교환 수행
              this.exchangeCodeForToken(event.data.code).then(tokenData => {
                window.removeEventListener('message', messageHandler);
                this.cleanup();
                resolve(tokenData.access_token);
              }).catch(error => {
                window.removeEventListener('message', messageHandler);
                this.cleanup();
                reject(error);
              });
            } else {
              // 기존 토큰 처리
              window.removeEventListener('message', messageHandler);
              this.cleanup();
              resolve(event.data.token);
            }
          } else if (event.data.type === 'OAUTH_ERROR') {
            window.removeEventListener('message', messageHandler);
            this.cleanup();
            reject(new Error(event.data.error || 'OAuth 인증에 실패했습니다.'));
          }
        };
        
        window.addEventListener('message', messageHandler);
        
        // 팝업 종료 감지
        this.checkInterval = setInterval(() => {
          if (this.popup.closed) {
            window.removeEventListener('message', messageHandler);
            this.cleanup();
            reject(new Error('사용자가 인증을 취소했습니다.'));
          }
        }, 1000);
        
      } catch (error) {
        reject(error);
      }
    });
  }
  
  cleanup() {
    if (this.popup && !this.popup.closed) {
      this.popup.close();
    }
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
    }
    this.popup = null;
    this.checkInterval = null;
  }
}

```

## 2. OAuth 콜백 페이지 생성

### `/src/pages/OAuthCallback.jsx`

```javascript
import React, { useEffect } from 'react';

const OAuthCallback = () => {
  useEffect(() => {
    const handleCallback = async () => {
      try {
        const urlParams = new URLSearchParams(window.location.search);
        const code = urlParams.get('code');
        const state = urlParams.get('state');
        const error = urlParams.get('error');
        
        if (error) {
          // 부모 창에 오류 전달
          window.opener?.postMessage({
            type: 'OAUTH_ERROR',
            error: error
          }, window.location.origin);
          window.close();
          return;
        }
        
        // state 검증
        const storedState = sessionStorage.getItem('oauth_state');
        if (state !== storedState) {
          window.opener?.postMessage({
            type: 'OAUTH_ERROR',
            error: 'Invalid state parameter'
          }, window.location.origin);
          window.close();
          return;
        }
        
        // 부모 창에 authorization code 전달 (토큰 교환은 부모에서 처리)
        window.opener?.postMessage({
          type: 'OAUTH_SUCCESS',
          code: code,
          state: state,
          redirect_uri: window.location.origin + '/oauth/callback'
        }, window.location.origin);
        
        window.close();
        
      } catch (error) {
        console.error('OAuth callback error:', error);
        window.opener?.postMessage({
          type: 'OAUTH_ERROR',
          error: error.message
        }, window.location.origin);
        window.close();
      }
    };
    
    handleCallback();
  }, []);
  
  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      height: '100vh',
      fontFamily: 'Arial, sans-serif'
    }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{
          border: '4px solid #f3f3f3',
          borderTop: '4px solid #3498db',
          borderRadius: '50%',
          width: '40px',
          height: '40px',
          animation: 'spin 2s linear infinite',
          margin: '0 auto 20px'
        }}></div>
        <h2>인증 처리 중...</h2>
        <p>잠시만 기다려주세요.</p>
        <style>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    </div>
  );
};

export default OAuthCallback;
```

## 3. 로그인 페이지에 OAuth 버튼 추가

### 기존 로그인 페이지 수정 예제

```javascript
import React, { useState } from 'react';
import { PopupOAuthLogin } from '../utils/popupOAuth';

const LoginPage = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const handleOAuthLogin = async () => {
    setLoading(true);
    setError('');
    
    const oauthLogin = new PopupOAuthLogin();
    
    try {
      const accessToken = await oauthLogin.startAuth();
      
      // 토큰 저장
      localStorage.setItem('access_token', accessToken);
      
      // 사용자 정보 가져오기
      const userResponse = await fetch('http://localhost:8000/api/oauth/userinfo', {
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      });
      
      if (userResponse.ok) {
        const userData = await userResponse.json();
        console.log('User data:', userData);
        
        // 로그인 성공 처리 (예: 상태 업데이트, 페이지 이동 등)
        window.location.href = '/dashboard';
      } else {
        throw new Error('사용자 정보를 가져올 수 없습니다.');
      }
      
    } catch (error) {
      console.error('OAuth login error:', error);
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="login-container">
      {/* 기존 로그인 폼 */}
      
      <div className="oauth-section">
        <div className="divider">
          <span>또는</span>
        </div>
        
        <button
          onClick={handleOAuthLogin}
          disabled={loading}
          className="oauth-login-button"
        >
          {loading ? '인증 중...' : 'MAX Platform으로 로그인'}
        </button>
        
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}
      </div>
    </div>
  );
};

export default LoginPage;
```

## 4. 라우팅 설정

### React Router 설정에 OAuth 콜백 경로 추가

```javascript
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import OAuthCallback from './pages/OAuthCallback';

function App() {
  return (
    <Router>
      <Routes>
        {/* 기존 라우트들 */}
        <Route path="/oauth/callback" element={<OAuthCallback />} />
        {/* 다른 라우트들 */}
      </Routes>
    </Router>
  );
}
```

## 5. CSS 스타일링 예제

```css
.oauth-section {
  margin-top: 20px;
  text-align: center;
}

.divider {
  margin: 20px 0;
  position: relative;
  text-align: center;
}

.divider::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 1px;
  background: #ddd;
}

.divider span {
  background: white;
  padding: 0 15px;
  color: #666;
  position: relative;
}

.oauth-login-button {
  width: 100%;
  padding: 12px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 5px;
  font-size: 16px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.oauth-login-button:hover {
  background: #0056b3;
}

.oauth-login-button:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.error-message {
  color: red;
  margin-top: 10px;
  padding: 10px;
  background: #ffebee;
  border-radius: 5px;
}
```

## 사용 방법

1. 위의 파일들을 maxflowstudio 프로젝트에 추가
2. OAuth 콜백 라우트를 라우터에 등록
3. 로그인 페이지에 OAuth 로그인 버튼 추가
4. 사용자가 "MAX Platform으로 로그인" 버튼 클릭
5. 팝업 창에서 MAX Platform 로그인 진행
6. 로그인 완료 후 자동으로 maxflowstudio로 복귀

이 구현을 통해 사용자는 maxflowstudio를 벗어나지 않고도 MAX Platform 계정으로 SSO 로그인을 할 수 있습니다.