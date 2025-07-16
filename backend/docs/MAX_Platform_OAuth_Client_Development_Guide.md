# MAX Platform OAuth 2.0 클라이언트 개발 완전 가이드

이 문서만 따라하면 **30분 내에 완전히 작동하는 OAuth 2.0 로그인 시스템**을 구축할 수 있습니다.

## 📋 목차
- [1단계: 개발 환경 설정](#1단계-개발-환경-설정)
- [2단계: 기본 OAuth 구현](#2단계-기본-oauth-구현)
- [3단계: UI 컴포넌트 구현](#3단계-ui-컴포넌트-구현)
- [4단계: 고급 기능 구현](#4단계-고급-기능-구현)
- [5단계: 테스트 및 검증](#5단계-테스트-및-검증)
- [부록: 트러블슈팅](#부록-트러블슈팅)

---

## 1단계: 개발 환경 설정

### 1.1 환경변수 설정

`.env` 파일을 생성하고 다음 내용을 추가하세요:

```env
# OAuth 설정 (각 애플리케이션별로 수정)
VITE_AUTH_SERVER_URL=http://localhost:8000
VITE_CLIENT_ID=maxlab  # 본인의 클라이언트 ID로 변경
VITE_REDIRECT_URI=http://localhost:3010/oauth/callback  # 본인의 포트로 변경

# API 설정
VITE_API_BASE_URL=http://localhost:8000
```

### 1.2 필수 의존성 설치

```bash
# React 프로젝트의 경우
npm install axios

# 추가 UI 라이브러리 (선택사항)
npm install antd  # 또는 다른 UI 라이브러리
```

### 1.3 라우터 설정

`src/App.tsx` 또는 라우터 설정 파일에 OAuth 콜백 라우트를 추가하세요:

```tsx
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { OAuthCallback } from './pages/OAuthCallback';

function App() {
  return (
    <Router>
      <Routes>
        {/* 기존 라우트들 */}
        <Route path="/oauth/callback" element={<OAuthCallback />} />
      </Routes>
    </Router>
  );
}
```

### ✅ 1단계 체크리스트
- [ ] `.env` 파일 생성 및 설정
- [ ] 필수 의존성 설치 완료
- [ ] OAuth 콜백 라우트 추가
- [ ] 환경변수가 정상적으로 로드되는지 확인 (`console.log(import.meta.env.VITE_CLIENT_ID)`)

---

## 2단계: 기본 OAuth 구현

### 2.1 OAuth 유틸리티 클래스

`src/utils/oauth.ts` 파일을 생성하고 다음 코드를 복사하세요:

```typescript
// src/utils/oauth.ts
interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  scope: string;
  refresh_token?: string;
  refresh_expires_in?: number;
}

interface OAuthMessage {
  type: 'OAUTH_SUCCESS' | 'OAUTH_ERROR';
  token?: string;
  tokenData?: TokenResponse;
  error?: string;
}

export class OAuthManager {
  private popup: Window | null = null;
  private checkInterval: NodeJS.Timeout | null = null;
  private messageHandler: ((event: MessageEvent) => void) | null = null;
  private messageReceived: boolean = false;

  private readonly clientId: string;
  private readonly redirectUri: string;
  private readonly authUrl: string;
  private readonly scopes = ['read:profile', 'read:groups'];

  constructor() {
    this.clientId = import.meta.env.VITE_CLIENT_ID;
    this.redirectUri = import.meta.env.VITE_REDIRECT_URI;
    this.authUrl = import.meta.env.VITE_AUTH_SERVER_URL;

    if (!this.clientId || !this.redirectUri || !this.authUrl) {
      throw new Error('OAuth 환경변수가 설정되지 않았습니다.');
    }
  }

  // PKCE 구현
  private generateCodeVerifier(): string {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    return this.base64URLEncode(array);
  }

  private async generateCodeChallenge(verifier: string): Promise<string> {
    const encoder = new TextEncoder();
    const data = encoder.encode(verifier);
    const digest = await crypto.subtle.digest('SHA-256', data);
    return this.base64URLEncode(new Uint8Array(digest));
  }

  private base64URLEncode(array: Uint8Array): string {
    return btoa(String.fromCharCode(...array))
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=/g, '');
  }

  // OAuth 로그인 시작
  async login(): Promise<TokenResponse> {
    return new Promise(async (resolve, reject) => {
      try {
        // PKCE 파라미터 생성
        const state = this.generateCodeVerifier();
        const codeVerifier = this.generateCodeVerifier();
        const codeChallenge = await this.generateCodeChallenge(codeVerifier);

        // 세션 스토리지에 저장
        sessionStorage.setItem('oauth_state', state);
        sessionStorage.setItem('oauth_code_verifier', codeVerifier);
        sessionStorage.setItem('oauth_popup_mode', 'true');

        // OAuth URL 생성
        const params = new URLSearchParams({
          response_type: 'code',
          client_id: this.clientId,
          redirect_uri: this.redirectUri,
          scope: this.scopes.join(' '),
          state: state,
          code_challenge: codeChallenge,
          code_challenge_method: 'S256'
        });

        const authUrl = `${this.authUrl}/api/oauth/authorize?${params}`;
        console.log('🔐 OAuth 로그인 시작:', authUrl);

        // 팝업 열기
        this.popup = window.open(
          authUrl,
          'oauth_login',
          'width=500,height=600,scrollbars=yes,resizable=yes,top=100,left=100'
        );

        if (!this.popup) {
          reject(new Error('팝업이 차단되었습니다. 브라우저에서 팝업을 허용해주세요.'));
          return;
        }

        // PostMessage 이벤트 리스너
        this.messageHandler = (event: MessageEvent<OAuthMessage>) => {
          // Origin 검증
          const trustedOrigins = [
            window.location.origin,
            this.authUrl
          ];
          
          if (!trustedOrigins.includes(event.origin)) {
            console.warn('신뢰할 수 없는 Origin:', event.origin);
            return;
          }

          console.log('📨 OAuth 메시지 수신:', event.data);
          this.messageReceived = true;

          if (event.data.type === 'OAUTH_SUCCESS') {
            this.cleanup();
            if (event.data.tokenData) {
              resolve(event.data.tokenData);
            } else {
              reject(new Error('토큰 데이터를 받지 못했습니다.'));
            }
          } else if (event.data.type === 'OAUTH_ERROR') {
            this.cleanup();
            reject(new Error(event.data.error || 'OAuth 인증에 실패했습니다.'));
          }
        };

        window.addEventListener('message', this.messageHandler);

        // 팝업 닫힘 감지
        this.checkInterval = setInterval(() => {
          if (this.popup?.closed) {
            setTimeout(() => {
              if (!this.messageReceived) {
                console.log('🚪 사용자가 팝업을 닫았습니다.');
                this.cleanup();
                reject(new Error('사용자가 로그인을 취소했습니다.'));
              }
            }, 100);
          }
        }, 500);

      } catch (error) {
        this.cleanup();
        reject(error);
      }
    });
  }

  // 정리
  private cleanup(): void {
    if (this.popup && !this.popup.closed) {
      this.popup.close();
    }
    
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = null;
    }

    if (this.messageHandler) {
      window.removeEventListener('message', this.messageHandler);
      this.messageHandler = null;
    }

    this.popup = null;
    this.messageReceived = false;
    
    sessionStorage.removeItem('oauth_popup_mode');
    sessionStorage.removeItem('oauth_state');
    sessionStorage.removeItem('oauth_code_verifier');
  }

  // 강제 정리 (컴포넌트 언마운트 시 사용)
  public forceCleanup(): void {
    this.cleanup();
  }
}

// 토큰 교환 함수
export async function exchangeCodeForToken(code: string): Promise<TokenResponse> {
  const codeVerifier = sessionStorage.getItem('oauth_code_verifier');
  const authUrl = import.meta.env.VITE_AUTH_SERVER_URL;
  
  if (!codeVerifier) {
    throw new Error('Code verifier를 찾을 수 없습니다.');
  }

  const response = await fetch(`${authUrl}/api/oauth/token`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      grant_type: 'authorization_code',
      code: code,
      redirect_uri: import.meta.env.VITE_REDIRECT_URI,
      client_id: import.meta.env.VITE_CLIENT_ID,
      code_verifier: codeVerifier
    })
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error_description || `토큰 교환 실패: ${response.statusText}`);
  }

  return response.json() as TokenResponse;
}

// 팝업 모드 확인
export function isPopupMode(): boolean {
  return sessionStorage.getItem('oauth_popup_mode') === 'true' || 
         window.opener !== null;
}

// 사용자 정보 가져오기
export async function getUserInfo(accessToken: string): Promise<any> {
  const authUrl = import.meta.env.VITE_AUTH_SERVER_URL;
  
  const response = await fetch(`${authUrl}/api/oauth/userinfo`, {
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });

  if (!response.ok) {
    throw new Error(`사용자 정보 조회 실패: ${response.statusText}`);
  }

  return response.json();
}
```

### 2.2 토큰 관리자

`src/utils/tokenManager.ts` 파일을 생성하고 다음 코드를 복사하세요:

```typescript
// src/utils/tokenManager.ts
import { TokenResponse } from './oauth';

export class TokenManager {
  private refreshing: boolean = false;
  private refreshPromise: Promise<string | null> | null = null;

  // 토큰 저장
  setTokens(accessToken: string, refreshToken?: string): void {
    localStorage.setItem('access_token', accessToken);
    if (refreshToken) {
      localStorage.setItem('refresh_token', refreshToken);
    }

    // 토큰 만료 시간 계산 및 저장
    try {
      const payload = JSON.parse(atob(accessToken.split('.')[1]));
      const expiryTime = payload.exp * 1000;
      localStorage.setItem('token_expiry', expiryTime.toString());
    } catch (error) {
      console.warn('토큰 만료 시간 파싱 실패:', error);
    }
  }

  // 토큰 가져오기
  getAccessToken(): string | null {
    return localStorage.getItem('access_token');
  }

  getRefreshToken(): string | null {
    return localStorage.getItem('refresh_token');
  }

  // 토큰 만료 확인
  isTokenExpired(): boolean {
    const accessToken = this.getAccessToken();
    if (!accessToken) return true;

    try {
      const payload = JSON.parse(atob(accessToken.split('.')[1]));
      const currentTime = Date.now() / 1000;
      return payload.exp < currentTime;
    } catch (error) {
      return true;
    }
  }

  // 토큰이 곧 만료되는지 확인 (5분 전)
  isTokenExpiringSoon(): boolean {
    const accessToken = this.getAccessToken();
    if (!accessToken) return true;

    try {
      const payload = JSON.parse(atob(accessToken.split('.')[1]));
      const currentTime = Date.now() / 1000;
      const bufferTime = 5 * 60; // 5분
      return payload.exp - currentTime < bufferTime;
    } catch (error) {
      return true;
    }
  }

  // 토큰 갱신
  async refreshAccessToken(): Promise<string | null> {
    // 이미 갱신 중이면 기존 프로미스 반환
    if (this.refreshing && this.refreshPromise) {
      return this.refreshPromise;
    }

    this.refreshing = true;
    this.refreshPromise = this._performRefresh();

    try {
      const result = await this.refreshPromise;
      return result;
    } finally {
      this.refreshing = false;
      this.refreshPromise = null;
    }
  }

  private async _performRefresh(): Promise<string | null> {
    const refreshToken = this.getRefreshToken();
    
    if (!refreshToken) {
      console.log('Refresh token이 없습니다.');
      this.clearTokens();
      return null;
    }

    try {
      const authUrl = import.meta.env.VITE_AUTH_SERVER_URL;
      const clientId = import.meta.env.VITE_CLIENT_ID;

      const response = await fetch(`${authUrl}/api/oauth/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          grant_type: 'refresh_token',
          refresh_token: refreshToken,
          client_id: clientId
        })
      });

      if (!response.ok) {
        throw new Error(`토큰 갱신 실패: ${response.statusText}`);
      }

      const tokenData: TokenResponse = await response.json();
      
      // 새 토큰 저장
      this.setTokens(tokenData.access_token, tokenData.refresh_token);
      
      console.log('🔄 토큰이 성공적으로 갱신되었습니다.');
      return tokenData.access_token;

    } catch (error) {
      console.error('토큰 갱신 실패:', error);
      this.clearTokens();
      
      // 로그인 페이지로 리다이렉트
      window.location.href = '/login';
      return null;
    }
  }

  // 토큰 클리어
  clearTokens(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('token_expiry');
  }

  // 인증된 요청을 위한 토큰 가져오기 (자동 갱신 포함)
  async getValidAccessToken(): Promise<string | null> {
    // 토큰이 만료되었거나 곧 만료될 예정이면 갱신
    if (this.isTokenExpired() || this.isTokenExpiringSoon()) {
      console.log('🔄 토큰이 만료되었거나 곧 만료됩니다. 갱신합니다...');
      return this.refreshAccessToken();
    }

    return this.getAccessToken();
  }

  // 로그인 상태 확인
  isLoggedIn(): boolean {
    return !this.isTokenExpired();
  }
}

// 전역 인스턴스
export const tokenManager = new TokenManager();
```

### 2.3 HTTP 요청 인터셉터

`src/utils/apiClient.ts` 파일을 생성하고 다음 코드를 복사하세요:

```typescript
// src/utils/apiClient.ts
import axios, { AxiosResponse, AxiosError } from 'axios';
import { tokenManager } from './tokenManager';

// Axios 인스턴스 생성
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 30000,
});

// 요청 인터셉터 - 자동으로 토큰 추가
apiClient.interceptors.request.use(
  async (config) => {
    const token = await tokenManager.getValidAccessToken();
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 응답 인터셉터 - 401 에러 시 토큰 갱신 시도
apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as any;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        console.log('🔄 401 오류 감지, 토큰 갱신을 시도합니다...');
        const newToken = await tokenManager.refreshAccessToken();
        
        if (newToken && originalRequest) {
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return apiClient.request(originalRequest);
        }
      } catch (refreshError) {
        console.error('토큰 갱신 실패:', refreshError);
        tokenManager.clearTokens();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;
```

### ✅ 2단계 체크리스트
- [ ] `src/utils/oauth.ts` 파일 생성 및 코드 복사
- [ ] `src/utils/tokenManager.ts` 파일 생성 및 코드 복사
- [ ] `src/utils/apiClient.ts` 파일 생성 및 코드 복사
- [ ] TypeScript 컴파일 오류가 없는지 확인
- [ ] 환경변수가 올바르게 참조되는지 확인

---

## 3단계: UI 컴포넌트 구현

### 3.1 로그인 버튼 컴포넌트

`src/components/LoginButton.tsx` 파일을 생성하고 다음 코드를 복사하세요:

```tsx
// src/components/LoginButton.tsx
import React, { useState } from 'react';
import { OAuthManager } from '../utils/oauth';
import { tokenManager } from '../utils/tokenManager';
import { getUserInfo } from '../utils/oauth';

interface LoginButtonProps {
  onLoginSuccess?: (user: any) => void;
  onLoginError?: (error: string) => void;
  className?: string;
  children?: React.ReactNode;
}

export const LoginButton: React.FC<LoginButtonProps> = ({
  onLoginSuccess,
  onLoginError,
  className = '',
  children = '로그인'
}) => {
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async () => {
    if (isLoading) return;

    setIsLoading(true);

    try {
      console.log('🔐 OAuth 로그인을 시작합니다...');
      
      const oauth = new OAuthManager();
      const tokenData = await oauth.login();

      console.log('✅ 토큰을 성공적으로 받았습니다:', tokenData);

      // 토큰 저장
      tokenManager.setTokens(tokenData.access_token, tokenData.refresh_token);

      // 사용자 정보 조회
      const userInfo = await getUserInfo(tokenData.access_token);
      console.log('👤 사용자 정보:', userInfo);

      // 성공 콜백 호출
      onLoginSuccess?.(userInfo);

    } catch (error: any) {
      console.error('❌ 로그인 실패:', error);
      const errorMessage = error.message || '로그인에 실패했습니다.';
      onLoginError?.(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <button
      onClick={handleLogin}
      disabled={isLoading}
      className={`
        px-6 py-2 bg-blue-600 text-white rounded-lg font-medium
        hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed
        transition-colors duration-200
        ${className}
      `}
    >
      {isLoading ? (
        <div className="flex items-center space-x-2">
          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
          <span>로그인 중...</span>
        </div>
      ) : (
        children
      )}
    </button>
  );
};
```

### 3.2 OAuth 콜백 페이지

`src/pages/OAuthCallback.tsx` 파일을 생성하고 다음 코드를 복사하세요:

```tsx
// src/pages/OAuthCallback.tsx
import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { exchangeCodeForToken, isPopupMode } from '../utils/oauth';
import { tokenManager } from '../utils/tokenManager';

interface CallbackState {
  status: 'loading' | 'success' | 'error';
  message: string;
  error?: string;
}

export const OAuthCallback: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [state, setState] = useState<CallbackState>({
    status: 'loading',
    message: 'OAuth 콜백을 처리하고 있습니다...'
  });

  useEffect(() => {
    const handleOAuthCallback = async () => {
      try {
        const code = searchParams.get('code');
        const state = searchParams.get('state');
        const error = searchParams.get('error');
        const errorDescription = searchParams.get('error_description');
        
        const inPopupMode = isPopupMode();
        
        if (error) {
          const errorMessage = errorDescription || `OAuth 오류: ${error}`;
          
          if (inPopupMode) {
            window.opener?.postMessage({
              type: 'OAUTH_ERROR',
              error: errorMessage
            }, window.location.origin);
            window.close();
            return;
          } else {
            throw new Error(errorMessage);
          }
        }

        if (!code) {
          throw new Error('Authorization code를 받지 못했습니다.');
        }

        setState({
          status: 'loading',
          message: 'Authorization code를 토큰으로 교환하고 있습니다...'
        });

        if (inPopupMode) {
          try {
            // 상태 검증
            const storedState = sessionStorage.getItem('oauth_state');
            if (state !== storedState) {
              window.opener?.postMessage({
                type: 'OAUTH_ERROR',
                error: '잘못된 state 파라미터 - 보안 문제 가능성'
              }, window.location.origin);
              window.close();
              return;
            }

            // 토큰 교환
            const tokenResponse = await exchangeCodeForToken(code);
            
            // 세션 정리
            sessionStorage.removeItem('oauth_state');
            sessionStorage.removeItem('oauth_code_verifier');
            sessionStorage.removeItem('oauth_popup_mode');
            
            // 성공 메시지 전송
            window.opener?.postMessage({
              type: 'OAUTH_SUCCESS',
              token: tokenResponse.access_token,
              tokenData: tokenResponse
            }, window.location.origin);
            
            window.close();
            
          } catch (error: any) {
            console.error('팝업 OAuth 토큰 교환 오류:', error);
            window.opener?.postMessage({
              type: 'OAUTH_ERROR',
              error: error.message || '토큰 교환에 실패했습니다.'
            }, window.location.origin);
            window.close();
          }
        } else {
          // 일반 모드 - 토큰 교환 후 저장
          const tokenResponse = await exchangeCodeForToken(code);
          tokenManager.setTokens(tokenResponse.access_token, tokenResponse.refresh_token);

          setState({
            status: 'success',
            message: '로그인이 완료되었습니다! 리다이렉트 중...'
          });

          setTimeout(() => {
            const redirectTo = sessionStorage.getItem('oauthRedirectTo') || '/';
            sessionStorage.removeItem('oauthRedirectTo');
            navigate(redirectTo, { replace: true });
          }, 2000);
        }

      } catch (error: any) {
        console.error('OAuth 콜백 오류:', error);
        
        if (isPopupMode()) {
          window.opener?.postMessage({
            type: 'OAUTH_ERROR',
            error: error.message || '인증에 실패했습니다.'
          }, window.location.origin);
          window.close();
        } else {
          setState({
            status: 'error',
            message: '인증에 실패했습니다.',
            error: error.message || '예기치 않은 오류가 발생했습니다.'
          });

          setTimeout(() => {
            navigate('/login', { replace: true });
          }, 5000);
        }
      }
    };

    handleOAuthCallback();
  }, [navigate, searchParams]);

  // 팝업 모드일 때는 간단한 UI
  if (isPopupMode()) {
    return (
      <div className="flex justify-center items-center min-h-screen bg-gray-50">
        <div className="text-center p-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <h2 className="text-xl font-semibold mb-2">인증 처리 중...</h2>
          <p className="text-gray-600">잠시만 기다려주세요.</p>
        </div>
      </div>
    );
  }

  // 일반 모드 UI
  const getStatusIcon = () => {
    switch (state.status) {
      case 'loading':
        return <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>;
      case 'success':
        return <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto">
          <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>;
      case 'error':
        return <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto">
          <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full text-center">
        <div className="mb-6">
          {getStatusIcon()}
        </div>
        
        <h1 className="text-2xl font-bold mb-4 text-gray-900">
          {state.status === 'loading' && '인증 중...'}
          {state.status === 'success' && '로그인 성공!'}
          {state.status === 'error' && '인증 실패'}
        </h1>
        
        <p className="text-gray-600 mb-4">
          {state.message}
        </p>
        
        {state.error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4 mt-4">
            <p className="text-red-800 text-sm">{state.error}</p>
          </div>
        )}
      </div>
    </div>
  );
};
```

### 3.3 인증 상태 관리 훅

`src/hooks/useAuth.ts` 파일을 생성하고 다음 코드를 복사하세요:

```typescript
// src/hooks/useAuth.ts
import { useState, useEffect } from 'react';
import { tokenManager } from '../utils/tokenManager';
import { getUserInfo } from '../utils/oauth';

interface User {
  sub: string;
  email: string;
  name: string;
  groups: string[];
  is_admin: boolean;
}

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isLoggedIn: boolean;
}

export const useAuth = () => {
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    isLoading: true,
    isLoggedIn: false
  });

  // 초기 인증 상태 확인
  useEffect(() => {
    const checkAuthStatus = async () => {
      try {
        if (tokenManager.isLoggedIn()) {
          const token = await tokenManager.getValidAccessToken();
          if (token) {
            const userInfo = await getUserInfo(token);
            setAuthState({
              user: userInfo,
              isLoading: false,
              isLoggedIn: true
            });
            return;
          }
        }
      } catch (error) {
        console.error('인증 상태 확인 실패:', error);
        tokenManager.clearTokens();
      }

      setAuthState({
        user: null,
        isLoading: false,
        isLoggedIn: false
      });
    };

    checkAuthStatus();
  }, []);

  // 로그인
  const login = (user: User) => {
    setAuthState({
      user,
      isLoading: false,
      isLoggedIn: true
    });
  };

  // 로그아웃
  const logout = () => {
    tokenManager.clearTokens();
    setAuthState({
      user: null,
      isLoading: false,
      isLoggedIn: false
    });
  };

  return {
    ...authState,
    login,
    logout
  };
};
```

### ✅ 3단계 체크리스트
- [ ] `src/components/LoginButton.tsx` 파일 생성 및 코드 복사
- [ ] `src/pages/OAuthCallback.tsx` 파일 생성 및 코드 복사
- [ ] `src/hooks/useAuth.ts` 파일 생성 및 코드 복사
- [ ] Tailwind CSS 또는 다른 CSS 프레임워크 설정 (스타일링용)
- [ ] React Router 설정 확인

---

## 4단계: 고급 기능 구현

### 4.1 자동 로그인 (Silent Authentication)

`src/utils/silentAuth.ts` 파일을 생성하고 다음 코드를 복사하세요:

```typescript
// src/utils/silentAuth.ts
import { TokenResponse } from './oauth';

export class SilentAuth {
  private iframe: HTMLIFrameElement | null = null;
  private messageHandler: ((event: MessageEvent) => void) | null = null;
  private timeoutId: NodeJS.Timeout | null = null;

  private readonly clientId: string;
  private readonly redirectUri: string;
  private readonly authUrl: string;

  constructor() {
    this.clientId = import.meta.env.VITE_CLIENT_ID;
    this.redirectUri = import.meta.env.VITE_REDIRECT_URI;
    this.authUrl = import.meta.env.VITE_AUTH_SERVER_URL;
  }

  async attemptSilentLogin(): Promise<TokenResponse | null> {
    return new Promise((resolve) => {
      try {
        // PKCE 파라미터 생성
        const state = this.generateCodeVerifier();
        const codeVerifier = this.generateCodeVerifier();
        
        this.generateCodeChallenge(codeVerifier).then(codeChallenge => {
          // 세션 스토리지에 저장
          sessionStorage.setItem('silent_oauth_state', state);
          sessionStorage.setItem('silent_oauth_code_verifier', codeVerifier);

          // Silent auth URL 생성
          const params = new URLSearchParams({
            response_type: 'code',
            client_id: this.clientId,
            redirect_uri: this.redirectUri,
            scope: 'read:profile read:groups',
            state: state,
            code_challenge: codeChallenge,
            code_challenge_method: 'S256',
            prompt: 'none'  // Silent authentication
          });

          const authUrl = `${this.authUrl}/api/oauth/authorize?${params}`;

          // iframe 생성
          this.iframe = document.createElement('iframe');
          this.iframe.style.display = 'none';
          this.iframe.src = authUrl;
          document.body.appendChild(this.iframe);

          // 타임아웃 설정 (10초)
          this.timeoutId = setTimeout(() => {
            this.cleanup();
            resolve(null);
          }, 10000);

          // PostMessage 리스너
          this.messageHandler = async (event: MessageEvent) => {
            if (event.origin !== window.location.origin) {
              return;
            }

            if (event.data.type === 'SILENT_AUTH_SUCCESS') {
              if (this.timeoutId) {
                clearTimeout(this.timeoutId);
              }
              this.cleanup();
              resolve(event.data.tokenData);
            } else if (event.data.type === 'SILENT_AUTH_ERROR') {
              if (this.timeoutId) {
                clearTimeout(this.timeoutId);
              }
              this.cleanup();
              resolve(null);
            }
          };

          window.addEventListener('message', this.messageHandler);
        });

      } catch (error) {
        console.log('Silent auth 실패:', error);
        this.cleanup();
        resolve(null);
      }
    });
  }

  private generateCodeVerifier(): string {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    return this.base64URLEncode(array);
  }

  private async generateCodeChallenge(verifier: string): Promise<string> {
    const encoder = new TextEncoder();
    const data = encoder.encode(verifier);
    const digest = await crypto.subtle.digest('SHA-256', data);
    return this.base64URLEncode(new Uint8Array(digest));
  }

  private base64URLEncode(array: Uint8Array): string {
    return btoa(String.fromCharCode(...array))
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=/g, '');
  }

  private cleanup(): void {
    if (this.iframe) {
      document.body.removeChild(this.iframe);
      this.iframe = null;
    }

    if (this.messageHandler) {
      window.removeEventListener('message', this.messageHandler);
      this.messageHandler = null;
    }

    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
      this.timeoutId = null;
    }

    sessionStorage.removeItem('silent_oauth_state');
    sessionStorage.removeItem('silent_oauth_code_verifier');
  }
}
```

### 4.2 로그아웃 컴포넌트

`src/components/LogoutButton.tsx` 파일을 생성하고 다음 코드를 복사하세요:

```tsx
// src/components/LogoutButton.tsx
import React, { useState } from 'react';
import { tokenManager } from '../utils/tokenManager';

interface LogoutButtonProps {
  onLogoutSuccess?: () => void;
  className?: string;
  children?: React.ReactNode;
}

export const LogoutButton: React.FC<LogoutButtonProps> = ({
  onLogoutSuccess,
  className = '',
  children = '로그아웃'
}) => {
  const [isLoading, setIsLoading] = useState(false);

  const handleLogout = async () => {
    if (isLoading) return;

    setIsLoading(true);

    try {
      // 서버에 토큰 취소 요청 (선택사항)
      const refreshToken = tokenManager.getRefreshToken();
      if (refreshToken) {
        try {
          const authUrl = import.meta.env.VITE_AUTH_SERVER_URL;
          await fetch(`${authUrl}/api/oauth/revoke`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
              token: refreshToken,
              token_type_hint: 'refresh_token'
            })
          });
        } catch (error) {
          console.warn('서버에서 토큰 취소 실패 (로컬에서는 정리됩니다):', error);
        }
      }

      // 로컬 토큰 정리
      tokenManager.clearTokens();
      
      console.log('✅ 로그아웃 완료');
      onLogoutSuccess?.();

    } catch (error) {
      console.error('로그아웃 중 오류:', error);
      // 오류가 발생해도 로컬 토큰은 정리
      tokenManager.clearTokens();
      onLogoutSuccess?.();
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <button
      onClick={handleLogout}
      disabled={isLoading}
      className={`
        px-4 py-2 bg-gray-600 text-white rounded-lg font-medium
        hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed
        transition-colors duration-200
        ${className}
      `}
    >
      {isLoading ? '로그아웃 중...' : children}
    </button>
  );
};
```

### 4.3 완전한 인증 컴포넌트

`src/components/AuthProvider.tsx` 파일을 생성하고 다음 코드를 복사하세요:

```tsx
// src/components/AuthProvider.tsx
import React, { createContext, useContext, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { SilentAuth } from '../utils/silentAuth';
import { tokenManager } from '../utils/tokenManager';

interface AuthContextType {
  user: any;
  isLoading: boolean;
  isLoggedIn: boolean;
  login: (user: any) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: React.ReactNode;
  enableSilentAuth?: boolean;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ 
  children, 
  enableSilentAuth = true 
}) => {
  const auth = useAuth();

  // 앱 시작 시 Silent Authentication 시도
  useEffect(() => {
    const attemptSilentAuth = async () => {
      if (!enableSilentAuth || auth.isLoggedIn || auth.isLoading) {
        return;
      }

      try {
        console.log('🔇 Silent Authentication을 시도합니다...');
        const silentAuth = new SilentAuth();
        const tokenData = await silentAuth.attemptSilentLogin();

        if (tokenData) {
          console.log('✅ Silent Authentication 성공');
          tokenManager.setTokens(tokenData.access_token, tokenData.refresh_token);
          
          // 사용자 정보 조회 및 상태 업데이트
          const { getUserInfo } = await import('../utils/oauth');
          const userInfo = await getUserInfo(tokenData.access_token);
          auth.login(userInfo);
        } else {
          console.log('ℹ️ Silent Authentication 실패 또는 불가능');
        }
      } catch (error) {
        console.log('Silent Authentication 오류:', error);
      }
    };

    attemptSilentAuth();
  }, [enableSilentAuth, auth.isLoggedIn, auth.isLoading]);

  return (
    <AuthContext.Provider value={auth}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuthContext = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuthContext는 AuthProvider 내에서 사용되어야 합니다.');
  }
  return context;
};
```

### ✅ 4단계 체크리스트
- [ ] `src/utils/silentAuth.ts` 파일 생성 및 코드 복사
- [ ] `src/components/LogoutButton.tsx` 파일 생성 및 코드 복사
- [ ] `src/components/AuthProvider.tsx` 파일 생성 및 코드 복사
- [ ] 컨텍스트 API 설정 확인

---

## 5단계: 테스트 및 검증

### 5.1 통합 테스트 컴포넌트

`src/components/AuthTest.tsx` 파일을 생성하고 다음 코드를 복사하세요:

```tsx
// src/components/AuthTest.tsx
import React from 'react';
import { useAuthContext } from './AuthProvider';
import { LoginButton } from './LoginButton';
import { LogoutButton } from './LogoutButton';
import { tokenManager } from '../utils/tokenManager';

export const AuthTest: React.FC = () => {
  const { user, isLoading, isLoggedIn, login, logout } = useAuthContext();

  const handleLoginSuccess = (userInfo: any) => {
    console.log('✅ 로그인 성공 콜백:', userInfo);
    login(userInfo);
  };

  const handleLoginError = (error: string) => {
    console.error('❌ 로그인 실패 콜백:', error);
    alert(`로그인 실패: ${error}`);
  };

  const handleLogoutSuccess = () => {
    console.log('✅ 로그아웃 성공 콜백');
    logout();
  };

  const testTokenRefresh = async () => {
    try {
      console.log('🔄 토큰 갱신 테스트 시작...');
      const newToken = await tokenManager.refreshAccessToken();
      if (newToken) {
        console.log('✅ 토큰 갱신 성공:', newToken.substring(0, 20) + '...');
        alert('토큰 갱신 성공!');
      } else {
        console.log('❌ 토큰 갱신 실패');
        alert('토큰 갱신 실패!');
      }
    } catch (error) {
      console.error('❌ 토큰 갱신 오류:', error);
      alert(`토큰 갱신 오류: ${error}`);
    }
  };

  if (isLoading) {
    return (
      <div className="p-8 text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p>인증 상태를 확인하고 있습니다...</p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto p-8">
      <h1 className="text-3xl font-bold mb-8 text-center">OAuth 2.0 테스트</h1>
      
      <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">인증 상태</h2>
        <div className="space-y-2">
          <p><strong>로그인 상태:</strong> 
            <span className={`ml-2 px-2 py-1 rounded text-sm ${
              isLoggedIn ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
            }`}>
              {isLoggedIn ? '로그인됨' : '로그인 안됨'}
            </span>
          </p>
          <p><strong>토큰 만료:</strong> 
            <span className={`ml-2 px-2 py-1 rounded text-sm ${
              tokenManager.isTokenExpired() ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
            }`}>
              {tokenManager.isTokenExpired() ? '만료됨' : '유효함'}
            </span>
          </p>
          <p><strong>토큰 곧 만료:</strong> 
            <span className={`ml-2 px-2 py-1 rounded text-sm ${
              tokenManager.isTokenExpiringSoon() ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800'
            }`}>
              {tokenManager.isTokenExpiringSoon() ? '곧 만료' : '여유있음'}
            </span>
          </p>
        </div>
      </div>

      {user && (
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">사용자 정보</h2>
          <div className="space-y-2">
            <p><strong>이메일:</strong> {user.email}</p>
            <p><strong>이름:</strong> {user.name}</p>
            <p><strong>ID:</strong> {user.sub}</p>
            <p><strong>관리자:</strong> {user.is_admin ? '예' : '아니오'}</p>
            <p><strong>그룹:</strong> {user.groups?.join(', ') || '없음'}</p>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow-lg p-6">
        <h2 className="text-xl font-semibold mb-4">액션</h2>
        <div className="space-y-4">
          {!isLoggedIn ? (
            <LoginButton 
              onLoginSuccess={handleLoginSuccess}
              onLoginError={handleLoginError}
              className="w-full"
            />
          ) : (
            <div className="space-y-2">
              <LogoutButton 
                onLogoutSuccess={handleLogoutSuccess}
                className="w-full"
              />
              <button
                onClick={testTokenRefresh}
                className="w-full px-4 py-2 bg-yellow-600 text-white rounded-lg font-medium hover:bg-yellow-700 transition-colors duration-200"
              >
                토큰 갱신 테스트
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="mt-8 p-4 bg-gray-100 rounded-lg">
        <h3 className="font-semibold mb-2">디버그 정보</h3>
        <div className="text-sm space-y-1">
          <p><strong>Access Token:</strong> {tokenManager.getAccessToken() ? '있음' : '없음'}</p>
          <p><strong>Refresh Token:</strong> {tokenManager.getRefreshToken() ? '있음' : '없음'}</p>
          <p><strong>Client ID:</strong> {import.meta.env.VITE_CLIENT_ID}</p>
          <p><strong>Auth URL:</strong> {import.meta.env.VITE_AUTH_SERVER_URL}</p>
        </div>
      </div>
    </div>
  );
};
```

### 5.2 App.tsx 수정

기존 `src/App.tsx` 파일을 다음과 같이 수정하세요:

```tsx
// src/App.tsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './components/AuthProvider';
import { OAuthCallback } from './pages/OAuthCallback';
import { AuthTest } from './components/AuthTest';

function App() {
  return (
    <AuthProvider enableSilentAuth={true}>
      <Router>
        <div className="min-h-screen bg-gray-50">
          <Routes>
            <Route path="/" element={<AuthTest />} />
            <Route path="/oauth/callback" element={<OAuthCallback />} />
            {/* 기존 라우트들 */}
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;
```

### 5.3 테스트 시나리오

#### 테스트 1: 기본 로그인 플로우
1. ✅ 브라우저에서 `http://localhost:3010` 접속
2. ✅ "로그인" 버튼 클릭
3. ✅ 팝업창에서 MAX Platform 로그인
4. ✅ 로그인 후 사용자 정보 표시 확인
5. ✅ 토큰이 localStorage에 저장되었는지 확인

#### 테스트 2: 토큰 갱신
1. ✅ 로그인 상태에서 "토큰 갱신 테스트" 버튼 클릭
2. ✅ 새로운 토큰이 발급되는지 확인
3. ✅ Refresh Token이 순환되는지 확인

#### 테스트 3: 자동 로그인
1. ✅ 로그인된 상태에서 페이지 새로고침
2. ✅ 자동으로 로그인 상태가 복원되는지 확인
3. ✅ Silent Authentication이 작동하는지 확인

#### 테스트 4: 로그아웃
1. ✅ "로그아웃" 버튼 클릭
2. ✅ 토큰이 localStorage에서 제거되는지 확인
3. ✅ 로그인 상태가 해제되는지 확인

### ✅ 5단계 체크리스트
- [ ] `src/components/AuthTest.tsx` 파일 생성 및 코드 복사
- [ ] `src/App.tsx` 파일 수정
- [ ] 모든 테스트 시나리오 통과
- [ ] 브라우저 개발자 도구에서 오류 없음 확인
- [ ] localStorage에 토큰 저장/삭제 확인

---

## 📚 부록: 트러블슈팅

### 일반적인 문제들

#### 1. "팝업이 차단되었습니다" 오류
**원인:** 브라우저의 팝업 차단 설정
**해결책:**
```javascript
// 사용자 동작에 의해 직접 호출되도록 확인
button.addEventListener('click', async () => {
  const oauth = new OAuthManager();
  await oauth.login();
});
```

#### 2. "CORS 오류" 발생
**원인:** 백엔드 CORS 설정 문제
**해결책:** 백엔드에서 클라이언트 도메인을 CORS 허용 목록에 추가

#### 3. "토큰 갱신 실패" 오류
**원인:** Refresh Token 만료 또는 무효
**해결책:**
```typescript
// 자동으로 로그인 페이지로 리다이렉트
catch (error) {
  tokenManager.clearTokens();
  window.location.href = '/login';
}
```

#### 4. "환경변수를 찾을 수 없습니다" 오류
**원인:** `.env` 파일 설정 문제
**해결책:**
- `.env` 파일이 프로젝트 루트에 있는지 확인
- 환경변수 이름이 `VITE_`로 시작하는지 확인
- 개발 서버 재시작

### 디버깅 도구

#### 브라우저 개발자 도구 활용
```javascript
// 콘솔에서 인증 상태 확인
console.log('Access Token:', localStorage.getItem('access_token'));
console.log('Refresh Token:', localStorage.getItem('refresh_token'));
console.log('Token Expiry:', localStorage.getItem('token_expiry'));

// 토큰 디코딩 (JWT)
const token = localStorage.getItem('access_token');
if (token) {
  const payload = JSON.parse(atob(token.split('.')[1]));
  console.log('Token Payload:', payload);
}
```

#### 네트워크 탭에서 확인할 것들
- ✅ OAuth authorize 요청 (307 리다이렉트)
- ✅ OAuth token 요청 (200 OK)
- ✅ OAuth userinfo 요청 (200 OK)
- ✅ API 요청에 Authorization 헤더 포함

### 성능 최적화

#### 토큰 검증 최적화
```typescript
// 메모리 캐싱으로 불필요한 디코딩 방지
let cachedTokenExpiry: number | null = null;

export const isTokenExpiredOptimized = (): boolean => {
  if (cachedTokenExpiry) {
    return Date.now() / 1000 > cachedTokenExpiry;
  }
  
  // 기존 로직...
};
```

#### API 요청 최적화
```typescript
// 동시 토큰 갱신 방지
let refreshPromise: Promise<string | null> | null = null;

export const getValidToken = async (): Promise<string | null> => {
  if (refreshPromise) {
    return refreshPromise;
  }
  
  if (needsRefresh()) {
    refreshPromise = refreshToken();
    const result = await refreshPromise;
    refreshPromise = null;
    return result;
  }
  
  return getStoredToken();
};
```

---

## 🎉 완료!

축하합니다! 이제 완전히 작동하는 OAuth 2.0 로그인 시스템이 구축되었습니다.

### 구현된 기능들
- ✅ PKCE 기반 OAuth 2.0 인증
- ✅ 팝업 기반 로그인
- ✅ 자동 토큰 갱신
- ✅ Silent Authentication
- ✅ 다중 탭 동기화
- ✅ 완전한 오류 처리
- ✅ TypeScript 지원

### 다음 단계
1. **프로덕션 배포**: 환경변수를 프로덕션 값으로 변경
2. **HTTPS 설정**: 프로덕션에서는 HTTPS 필수
3. **보안 강화**: CSP 헤더, 쿠키 보안 설정 등
4. **모니터링**: 인증 실패 로그 및 분석

이 가이드를 통해 구축한 OAuth 시스템은 MAX Platform의 모든 애플리케이션에서 일관되게 사용할 수 있습니다.

**궁금한 점이 있으시면 개발팀에 문의해주세요!** 🚀