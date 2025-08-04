# MAX Platform OIDC/OAuth 2.0 Client Implementation Guide

## 목차
1. [개요](#개요)
2. [사전 준비](#사전-준비)
3. [인증 흐름](#인증-흐름)
4. [구현 가이드](#구현-가이드)
5. [권한 및 Claims](#권한-및-claims)
6. [Single Logout](#single-logout)
7. [보안 고려사항](#보안-고려사항)
8. [테스트 및 디버깅](#테스트-및-디버깅)
9. [FAQ](#faq)

## 개요

MAX Platform은 OpenID Connect 1.0과 OAuth 2.0을 지원하는 통합 인증 시스템입니다. 이 가이드는 클라이언트 애플리케이션에서 MAX Platform의 인증 시스템을 구현하는 방법을 설명합니다.

### 지원 사양
- **OAuth 2.0** (RFC 6749)
- **OpenID Connect 1.0** Core
- **PKCE** (RFC 7636) - 보안 강화
- **RP-Initiated Logout** - Single Logout 지원

### 지원 Grant Types
- Authorization Code Flow (권장)
- Refresh Token Grant
- Client Credentials (서비스 인증용)

## 사전 준비

### 1. OAuth Client 등록

MAX Platform 관리자에게 다음 정보를 제공하여 OAuth Client를 등록합니다:

```json
{
  "client_name": "Your Application Name",
  "description": "Application description",
  "redirect_uris": [
    "http://localhost:3000/oauth/callback",
    "http://localhost:3000/login"  // Single Logout용
  ],
  "homepage_url": "http://localhost:3000",
  "allowed_scopes": [
    "openid",
    "profile", 
    "email",
    "read:profile",
    "read:features",
    "read:groups"
  ]
}
```

등록 후 다음 정보를 받습니다:
- `client_id`: 클라이언트 식별자
- `client_secret`: 비밀 키 (Confidential Client인 경우)

### 2. Discovery Endpoints

```javascript
// OpenID Connect Discovery
const OIDC_DISCOVERY = 'http://localhost:8000/api/oauth/.well-known/openid-configuration'

// OAuth 2.0 Metadata
const OAUTH_METADATA = 'http://localhost:8000/api/oauth/.well-known/oauth-authorization-server'
```

### 3. 주요 Endpoints

```javascript
const AUTH_ENDPOINTS = {
  authorize: 'http://localhost:8000/api/oauth/authorize',
  token: 'http://localhost:8000/api/oauth/token',
  userinfo: 'http://localhost:8000/api/oauth/userinfo',
  logout: 'http://localhost:8000/api/oauth/logout',
  jwks: 'http://localhost:8000/api/oauth/jwks',
  revoke: 'http://localhost:8000/api/oauth/revoke'
}
```

## 인증 흐름

### 1. Authorization Code Flow (PKCE 포함)

```javascript
// 1. PKCE Code Verifier 및 Challenge 생성
function generateCodeVerifier() {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  return base64URLEncode(array);
}

function generateCodeChallenge(verifier) {
  const encoder = new TextEncoder();
  const data = encoder.encode(verifier);
  return crypto.subtle.digest('SHA-256', data)
    .then(buffer => base64URLEncode(new Uint8Array(buffer)));
}

function base64URLEncode(buffer) {
  const base64 = btoa(String.fromCharCode.apply(null, buffer));
  return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

// 2. Authorization 요청
async function initiateLogin() {
  const codeVerifier = generateCodeVerifier();
  const codeChallenge = await generateCodeChallenge(codeVerifier);
  const state = generateRandomString();
  
  // 세션에 저장 (나중에 검증용)
  sessionStorage.setItem('oauth_code_verifier', codeVerifier);
  sessionStorage.setItem('oauth_state', state);
  
  const params = new URLSearchParams({
    response_type: 'code',
    client_id: CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    scope: 'openid profile email read:profile',
    state: state,
    code_challenge: codeChallenge,
    code_challenge_method: 'S256',
    // prompt: 'login',  // 강제 재인증이 필요한 경우
    // prompt: 'none',   // Silent authentication 시도
  });
  
  window.location.href = `${AUTH_ENDPOINTS.authorize}?${params}`;
}

// 3. Callback 처리
async function handleOAuthCallback() {
  const params = new URLSearchParams(window.location.search);
  const code = params.get('code');
  const state = params.get('state');
  const error = params.get('error');
  
  // 에러 처리
  if (error) {
    console.error('OAuth error:', error, params.get('error_description'));
    return;
  }
  
  // State 검증
  const savedState = sessionStorage.getItem('oauth_state');
  if (state !== savedState) {
    throw new Error('Invalid state parameter');
  }
  
  // Code Verifier 가져오기
  const codeVerifier = sessionStorage.getItem('oauth_code_verifier');
  
  // Token 교환
  const tokenResponse = await exchangeCodeForToken(code, codeVerifier);
  
  // 정리
  sessionStorage.removeItem('oauth_state');
  sessionStorage.removeItem('oauth_code_verifier');
  
  return tokenResponse;
}

// 4. Token 교환
async function exchangeCodeForToken(code, codeVerifier) {
  const response = await fetch(AUTH_ENDPOINTS.token, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      grant_type: 'authorization_code',
      code: code,
      redirect_uri: REDIRECT_URI,
      client_id: CLIENT_ID,
      client_secret: CLIENT_SECRET, // Confidential Client인 경우
      code_verifier: codeVerifier,
    })
  });
  
  const data = await response.json();
  
  if (!response.ok) {
    throw new Error(data.error || 'Token exchange failed');
  }
  
  // 토큰 저장
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('refresh_token', data.refresh_token);
  
  if (data.id_token) {
    localStorage.setItem('id_token', data.id_token);
  }
  
  return data;
}
```

### 2. Refresh Token 사용

```javascript
async function refreshAccessToken() {
  const refreshToken = localStorage.getItem('refresh_token');
  
  if (!refreshToken) {
    throw new Error('No refresh token available');
  }
  
  const response = await fetch(AUTH_ENDPOINTS.token, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      grant_type: 'refresh_token',
      refresh_token: refreshToken,
      client_id: CLIENT_ID,
      client_secret: CLIENT_SECRET, // Confidential Client인 경우
    })
  });
  
  const data = await response.json();
  
  if (!response.ok) {
    // Refresh token이 만료된 경우 재로그인 필요
    if (data.error === 'invalid_grant') {
      clearTokens();
      window.location.href = '/login';
    }
    throw new Error(data.error || 'Token refresh failed');
  }
  
  // 새 토큰 저장
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('refresh_token', data.refresh_token);
  
  if (data.id_token) {
    localStorage.setItem('id_token', data.id_token);
  }
  
  return data;
}
```

### 3. API 호출 시 토큰 사용

```javascript
// Axios Interceptor 예제
import axios from 'axios';

// Request Interceptor
axios.interceptors.request.use(
  config => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  error => Promise.reject(error)
);

// Response Interceptor (자동 토큰 갱신)
axios.interceptors.response.use(
  response => response,
  async error => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        await refreshAccessToken();
        const token = localStorage.getItem('access_token');
        originalRequest.headers.Authorization = `Bearer ${token}`;
        return axios(originalRequest);
      } catch (refreshError) {
        // 리프레시 실패 시 로그인 페이지로
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);
```

## 구현 가이드

### React 구현 예제

#### 1. AuthContext 구현

```typescript
import React, { createContext, useContext, useState, useEffect } from 'react';

interface User {
  id: string;
  email: string;
  name: string;
  groups: string[];
  is_admin: boolean;
  group_id?: string;
  group_name?: string;
  role_id?: string;
  role_name?: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: () => Promise<void>;
  logout: (forceSingleLogout?: boolean) => Promise<void>;
  getAccessToken: () => string | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // 초기화 - 저장된 토큰으로 사용자 정보 로드
  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('access_token');
      
      if (token) {
        try {
          const userInfo = await fetchUserInfo(token);
          setUser(userInfo);
        } catch (error) {
          console.error('Failed to load user info:', error);
          clearTokens();
        }
      }
      
      setIsLoading(false);
    };
    
    initAuth();
  }, []);

  // 사용자 정보 가져오기
  const fetchUserInfo = async (accessToken: string): Promise<User> => {
    const response = await fetch(AUTH_ENDPOINTS.userinfo, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch user info');
    }
    
    const data = await response.json();
    
    // OIDC Claims 또는 OAuth UserInfo 응답 처리
    return {
      id: data.sub,
      email: data.email,
      name: data.name || data.display_name || data.email,
      groups: data.groups || [],
      is_admin: data.is_admin || false,
      group_id: data.group_id,
      group_name: data.group_name,
      role_id: data.role_id,
      role_name: data.role_name,
    };
  };

  // 로그인
  const login = async () => {
    await initiateLogin();
  };

  // 로그아웃 (Single Logout 지원)
  const logout = async (forceSingleLogout: boolean = true) => {
    try {
      // 1. 로컬 토큰 정리
      const currentToken = localStorage.getItem('access_token');
      clearTokens();
      
      // 2. 상태 업데이트
      setUser(null);
      
      // 3. Single Logout 수행 (OIDC End Session)
      if (forceSingleLogout && currentToken) {
        const logoutUrl = new URL(AUTH_ENDPOINTS.logout);
        logoutUrl.searchParams.append(
          'post_logout_redirect_uri',
          `${window.location.origin}/login?logout=success`
        );
        
        const idToken = localStorage.getItem('id_token');
        if (idToken) {
          logoutUrl.searchParams.append('id_token_hint', idToken);
        }
        
        window.location.href = logoutUrl.toString();
      } else {
        window.location.href = '/login?logout=local';
      }
    } catch (error) {
      console.error('Logout error:', error);
      window.location.href = '/login?logout=error';
    }
  };

  const getAccessToken = () => {
    return localStorage.getItem('access_token');
  };

  const clearTokens = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('id_token');
    document.cookie = 'access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
  };

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    logout,
    getAccessToken,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
```

#### 2. OAuth Callback 컴포넌트

```typescript
import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from './AuthContext';

const OAuthCallback: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();

  useEffect(() => {
    const handleCallback = async () => {
      try {
        const tokenData = await handleOAuthCallback();
        
        // 토큰 교환 성공 후 사용자 정보 로드
        window.location.href = '/dashboard';
      } catch (error) {
        console.error('OAuth callback error:', error);
        navigate('/login?error=oauth_failed');
      }
    };

    handleCallback();
  }, [navigate]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <h2>인증 처리 중...</h2>
        <div className="spinner" />
      </div>
    </div>
  );
};

export default OAuthCallback;
```

#### 3. Protected Route 구현

```typescript
import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredScopes?: string[];
  requireAdmin?: boolean;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredScopes = [],
  requireAdmin = false,
}) => {
  const { user, isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    // 현재 경로 저장 (로그인 후 리다이렉트용)
    localStorage.setItem('redirectAfterLogin', location.pathname);
    return <Navigate to="/login" replace />;
  }

  // 관리자 권한 체크
  if (requireAdmin && !user?.is_admin) {
    return <Navigate to="/unauthorized" replace />;
  }

  // 스코프 체크 (필요한 경우)
  // TODO: 토큰에서 스코프 추출하여 검증

  return <>{children}</>;
};

export default ProtectedRoute;
```

## 권한 및 Claims

### 1. 표준 OIDC Claims

```typescript
interface OIDCClaims {
  // 필수 Claims
  sub: string;          // 사용자 고유 ID
  
  // 표준 Profile Claims
  name?: string;        // 전체 이름
  given_name?: string;  // 이름
  family_name?: string; // 성
  email?: string;       // 이메일
  email_verified?: boolean;
  
  // 추가 Claims
  picture?: string;     // 프로필 이미지 URL
  locale?: string;      // 언어 설정
  zoneinfo?: string;    // 시간대
}
```

### 2. MAX Platform 커스텀 Claims

```typescript
interface MAXPlatformClaims extends OIDCClaims {
  // 그룹 정보
  groups?: string[];          // 사용자가 속한 그룹 목록
  group_id?: string;          // 주 그룹 ID
  group_name?: string;        // 주 그룹 이름
  
  // 역할 정보
  role_id?: string;           // 역할 ID
  role_name?: string;         // 역할 이름
  
  // 권한 정보
  is_admin?: boolean;         // 관리자 여부
  permissions?: string[];     // 세부 권한 목록
  
  // 부가 정보
  department?: string;        // 부서
  position?: string;          // 직위
  employee_id?: string;       // 사번
}
```

### 3. 스코프와 권한 매핑

| 스코프 | 설명 | 포함되는 Claims |
|--------|------|----------------|
| `openid` | OIDC 기본 | `sub` |
| `profile` | 프로필 정보 | `name`, `given_name`, `family_name`, `picture` |
| `email` | 이메일 정보 | `email`, `email_verified` |
| `groups` | 그룹 정보 | `groups`, `group_id`, `group_name` |
| `roles` | 역할 정보 | `role_id`, `role_name` |
| `read:profile` | 프로필 읽기 | 프로필 관련 모든 정보 |
| `read:features` | 기능 권한 읽기 | `permissions` |
| `manage:workflows` | 워크플로우 관리 | Flow Studio 권한 |
| `manage:teams` | 팀 관리 | TeamSync 권한 |
| `admin:oauth` | OAuth 관리 | OAuth 클라이언트 관리 권한 |
| `admin:users` | 사용자 관리 | 사용자 관리 권한 |

### 4. 권한 검증 예제

```typescript
// 권한 헬퍼 함수
class PermissionHelper {
  static hasPermission(user: User, permission: string): boolean {
    if (user.is_admin) return true;
    return user.permissions?.includes(permission) || false;
  }
  
  static hasAnyPermission(user: User, permissions: string[]): boolean {
    if (user.is_admin) return true;
    return permissions.some(p => user.permissions?.includes(p));
  }
  
  static hasAllPermissions(user: User, permissions: string[]): boolean {
    if (user.is_admin) return true;
    return permissions.every(p => user.permissions?.includes(p));
  }
  
  static isInGroup(user: User, groupName: string): boolean {
    return user.groups?.includes(groupName) || user.group_name === groupName;
  }
  
  static hasRole(user: User, roleName: string): boolean {
    return user.role_name === roleName;
  }
}

// 사용 예제
const canManageWorkflows = PermissionHelper.hasPermission(user, 'manage:workflows');
const canAccessAdmin = PermissionHelper.hasAnyPermission(user, ['admin:oauth', 'admin:users']);
```

## Single Logout

### 1. 로그아웃 구현

```typescript
// 완전한 로그아웃 (SSO 세션 포함)
async function performSingleLogout() {
  try {
    // 1. 로컬 토큰 정리
    const accessToken = localStorage.getItem('access_token');
    const idToken = localStorage.getItem('id_token');
    
    clearLocalTokens();
    
    // 2. SSO Provider 로그아웃
    if (accessToken) {
      const logoutUrl = new URL(AUTH_ENDPOINTS.logout);
      
      // 로그아웃 후 리다이렉트 URL
      logoutUrl.searchParams.append(
        'post_logout_redirect_uri',
        `${window.location.origin}/login?logout=success`
      );
      
      // ID Token Hint (OIDC)
      if (idToken) {
        logoutUrl.searchParams.append('id_token_hint', idToken);
      }
      
      // SSO 로그아웃 수행
      window.location.href = logoutUrl.toString();
    }
  } catch (error) {
    console.error('Logout error:', error);
    window.location.href = '/login?logout=error';
  }
}

// 로컬 로그아웃만 수행
function performLocalLogout() {
  clearLocalTokens();
  window.location.href = '/login?logout=local';
}

function clearLocalTokens() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('id_token');
  sessionStorage.clear();
  
  // 쿠키 정리
  document.cookie.split(";").forEach(c => {
    document.cookie = c.replace(/^ +/, "")
      .replace(/=.*/, `=;expires=${new Date().toUTCString()};path=/`);
  });
}
```

### 2. 로그아웃 상태 처리

```typescript
// 로그인 페이지에서 로그아웃 상태 메시지 처리
useEffect(() => {
  const params = new URLSearchParams(location.search);
  const logoutStatus = params.get('logout');
  
  switch (logoutStatus) {
    case 'success':
      showToast('성공적으로 로그아웃되었습니다.', 'success');
      break;
    case 'error':
      showToast('로그아웃 중 오류가 발생했습니다.', 'error');
      break;
    case 'local':
      showToast('로컬 세션에서 로그아웃되었습니다.', 'info');
      break;
  }
  
  // URL 정리
  if (logoutStatus) {
    params.delete('logout');
    const newUrl = location.pathname + (params.toString() ? `?${params}` : '');
    window.history.replaceState({}, '', newUrl);
  }
}, [location]);
```

## 보안 고려사항

### 1. PKCE (Proof Key for Code Exchange)
- 모든 OAuth 흐름에서 PKCE 사용 필수
- Code Verifier는 최소 43자, 최대 128자
- Code Challenge는 SHA256 해시 사용

### 2. State Parameter
- CSRF 공격 방지를 위해 필수
- 충분한 엔트로피를 가진 랜덤 값 사용
- 세션 스토리지에 저장하여 검증

### 3. 토큰 저장
- Access Token: 메모리 또는 sessionStorage 권장
- Refresh Token: localStorage 사용 가능 (httpOnly 쿠키 더 안전)
- ID Token: 필요시만 저장, 검증 후 Claims만 추출 권장

### 4. 토큰 검증
```typescript
// ID Token 검증 (선택사항)
import * as jose from 'jose';

async function verifyIdToken(idToken: string) {
  try {
    // JWKS 가져오기
    const jwksResponse = await fetch(AUTH_ENDPOINTS.jwks);
    const jwks = await jwksResponse.json();
    
    // 토큰 검증
    const { payload } = await jose.jwtVerify(
      idToken,
      jose.createRemoteJWKSet(new URL(AUTH_ENDPOINTS.jwks)),
      {
        issuer: 'http://localhost:8000',
        audience: CLIENT_ID,
      }
    );
    
    return payload;
  } catch (error) {
    console.error('ID token verification failed:', error);
    throw error;
  }
}
```

### 5. 보안 헤더
```typescript
// API 요청 시 보안 헤더 추가
const secureHeaders = {
  'X-Requested-With': 'XMLHttpRequest',
  'X-CSRF-Token': getCsrfToken(), // CSRF 토큰이 있는 경우
};
```

## 테스트 및 디버깅

### 1. 개발 환경 설정

```javascript
// 개발 환경용 설정
const DEV_CONFIG = {
  CLIENT_ID: 'your-dev-client-id',
  CLIENT_SECRET: 'your-dev-client-secret', // 개발용만, 프로덕션에서는 제거
  REDIRECT_URI: 'http://localhost:3000/oauth/callback',
  API_BASE_URL: 'http://localhost:8000',
};

// 프로덕션 환경용 설정
const PROD_CONFIG = {
  CLIENT_ID: process.env.REACT_APP_CLIENT_ID,
  REDIRECT_URI: process.env.REACT_APP_REDIRECT_URI,
  API_BASE_URL: process.env.REACT_APP_API_BASE_URL,
};
```

### 2. 디버깅 도구

```typescript
// OAuth 디버그 로거
class OAuthDebugger {
  static logAuthRequest(params: URLSearchParams) {
    console.group('🔐 OAuth Authorization Request');
    console.log('URL:', `${AUTH_ENDPOINTS.authorize}?${params}`);
    console.log('Parameters:', Object.fromEntries(params));
    console.groupEnd();
  }
  
  static logTokenResponse(response: any) {
    console.group('🎫 Token Response');
    console.log('Access Token:', response.access_token?.substring(0, 20) + '...');
    console.log('Token Type:', response.token_type);
    console.log('Expires In:', response.expires_in);
    console.log('Scopes:', response.scope);
    console.log('Has Refresh Token:', !!response.refresh_token);
    console.log('Has ID Token:', !!response.id_token);
    console.groupEnd();
  }
  
  static logUserInfo(userInfo: any) {
    console.group('👤 User Info');
    console.log('User:', userInfo);
    console.log('Groups:', userInfo.groups);
    console.log('Permissions:', userInfo.permissions);
    console.groupEnd();
  }
}
```

### 3. 일반적인 오류 처리

```typescript
// OAuth 오류 처리
class OAuthErrorHandler {
  static handle(error: string, description?: string) {
    switch (error) {
      case 'invalid_request':
        console.error('잘못된 요청입니다.');
        break;
      case 'unauthorized_client':
        console.error('클라이언트가 이 요청을 수행할 권한이 없습니다.');
        break;
      case 'access_denied':
        console.error('사용자가 요청을 거부했습니다.');
        break;
      case 'unsupported_response_type':
        console.error('지원하지 않는 응답 유형입니다.');
        break;
      case 'invalid_scope':
        console.error('요청한 스코프가 유효하지 않습니다.');
        break;
      case 'server_error':
        console.error('서버 오류가 발생했습니다.');
        break;
      case 'temporarily_unavailable':
        console.error('서버가 일시적으로 사용할 수 없습니다.');
        break;
      case 'invalid_grant':
        console.error('제공된 인증 정보가 유효하지 않습니다.');
        // Refresh token 만료 - 재로그인 필요
        window.location.href = '/login';
        break;
      case 'invalid_client':
        console.error('클라이언트 인증에 실패했습니다.');
        break;
      case 'login_required':
        console.error('로그인이 필요합니다.');
        window.location.href = '/login';
        break;
      default:
        console.error(`OAuth 오류: ${error}`, description);
    }
  }
}
```

## FAQ

### Q1: Refresh Token은 언제 사용하나요?
Access Token이 만료되었을 때 사용합니다. 401 응답을 받으면 자동으로 Refresh Token으로 새 Access Token을 발급받도록 구현하세요.

### Q2: PKCE는 필수인가요?
네, 모든 클라이언트(특히 SPA)에서 PKCE 사용을 권장합니다. 보안을 크게 향상시킵니다.

### Q3: ID Token과 Access Token의 차이는?
- ID Token: 사용자 신원 정보 (인증용)
- Access Token: API 접근 권한 (인가용)

### Q4: Silent Authentication(`prompt=none`)은 언제 사용하나요?
사용자 상호작용 없이 토큰을 갱신하고 싶을 때 사용합니다. SSO 환경에서 유용합니다.

### Q5: 로그아웃 후에도 자동 로그인되는 문제는?
Single Logout을 구현하여 SSO Provider의 세션도 함께 종료해야 합니다.

### Q6: 다중 탭에서의 로그아웃 동기화는?
BroadcastChannel API나 localStorage 이벤트를 사용하여 탭 간 로그아웃을 동기화할 수 있습니다:

```javascript
// 로그아웃 브로드캐스트
const channel = new BroadcastChannel('auth');

// 로그아웃 시
channel.postMessage({ type: 'logout' });

// 다른 탭에서 리스닝
channel.addEventListener('message', (event) => {
  if (event.data.type === 'logout') {
    clearLocalTokens();
    window.location.href = '/login';
  }
});
```

## 참고 자료

- [OAuth 2.0 Specification (RFC 6749)](https://tools.ietf.org/html/rfc6749)
- [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html)
- [PKCE (RFC 7636)](https://tools.ietf.org/html/rfc7636)
- [OAuth 2.0 Security Best Practices](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics)

## 부록: 전체 구현 예제

완전한 구현 예제는 [MAX Platform OAuth Client Example](https://github.com/maxplatform/oauth-client-example)에서 확인할 수 있습니다.

---

이 문서는 MAX Platform OIDC/OAuth 2.0 클라이언트 구현을 위한 가이드입니다. 추가 질문이나 지원이 필요한 경우 MAX Platform 팀에 문의하세요.