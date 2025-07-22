# MAX Platform OAuth 2.0 및 UUID 기반 통신 가이드

## 목차
1. [개요](#개요)
2. [OAuth 2.0 인증 플로우](#oauth-20-인증-플로우)
3. [API 엔드포인트](#api-엔드포인트)
4. [UUID 기반 통신](#uuid-기반-통신)
5. [토큰 구조 및 정보](#토큰-구조-및-정보)
6. [구현 예제](#구현-예제)
7. [보안 고려사항](#보안-고려사항)
8. [오류 처리](#오류-처리)

## 개요

MAX Platform은 중앙 인증 서버로서 OAuth 2.0 표준을 준수하는 인증 서비스를 제공합니다. 모든 사용자와 그룹은 UUID를 기반으로 식별되며, 다양한 MAX 플랫폼 서비스들이 이를 통해 안전하게 통신할 수 있습니다.

### 주요 특징
- **OAuth 2.0 표준 준수**: RFC 6749 표준을 따르는 인증 구현
- **UUID 기반 식별**: 모든 사용자와 그룹은 고유한 UUID로 식별
- **JWT 토큰**: 사용자 정보가 포함된 자체 검증 가능한 토큰
- **PKCE 지원**: 보안 강화를 위한 Proof Key for Code Exchange 지원
- **다중 Grant Type**: Authorization Code, Refresh Token, Client Credentials 지원

### 지원하는 OAuth 2.0 Grant Types
1. **Authorization Code Grant**: 웹 애플리케이션용 (PKCE 지원)
2. **Refresh Token Grant**: 토큰 갱신용
3. **Client Credentials Grant**: 서비스 간 통신용

### 서버 정보
- **기본 URL**: `http://localhost:8000`
- **OAuth 메타데이터**: `http://localhost:8000/api/oauth/.well-known/oauth-authorization-server`

## OAuth 2.0 인증 플로우

### 1. Authorization Code Flow (권장)

웹 애플리케이션에서 사용자 인증을 위한 표준 플로우입니다.

#### 1.1 인증 요청
```
GET http://localhost:8000/api/oauth/authorize
```

**필수 파라미터:**
- `response_type=code`: 인증 코드를 요청
- `client_id`: 등록된 클라이언트 ID
- `redirect_uri`: 등록된 리다이렉트 URI
- `state`: CSRF 방지를 위한 임의 문자열

**선택 파라미터:**
- `scope`: 요청할 권한 (기본값: `read:profile`)
- `code_challenge`: PKCE 코드 챌린지
- `code_challenge_method`: PKCE 방식 (S256 또는 plain)
- `display=popup`: 팝업 모드 사용
- `prompt=none`: 자동 인증 (사용자 상호작용 없음)

**예시:**
```
http://localhost:8000/api/oauth/authorize?
  response_type=code&
  client_id=maxlab&
  redirect_uri=http://localhost:3003/oauth/callback&
  state=xyz123&
  scope=read:profile read:groups&
  code_challenge=E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM&
  code_challenge_method=S256
```

#### 1.2 토큰 교환
```
POST http://localhost:8000/api/oauth/token
Content-Type: application/x-www-form-urlencoded
```

**필수 파라미터:**
- `grant_type=authorization_code`
- `code`: 받은 인증 코드
- `redirect_uri`: 인증 요청 시 사용한 URI
- `client_id`: 클라이언트 ID

**선택 파라미터:**
- `client_secret`: 기밀 클라이언트인 경우
- `code_verifier`: PKCE 코드 검증자

**응답 예시:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "read:profile read:groups",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### 2. Refresh Token Flow

액세스 토큰 만료 시 새로운 토큰을 발급받는 플로우입니다.

```
POST http://localhost:8000/api/oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token&
refresh_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...&
client_id=maxlab&
client_secret=secret_lab_2025_dev
```

### 3. Client Credentials Grant (서비스 인증)

서비스 간 통신을 위한 인증 방식입니다. 사용자 컨텍스트 없이 서비스 자체를 인증합니다.

```
POST http://localhost:8000/api/oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials&
client_id=maxlab&
client_secret=secret_lab_2025_dev&
scope=admin:oauth admin:users
```

## API 엔드포인트

### OAuth 엔드포인트

#### 1. 인증 엔드포인트
```
GET /api/oauth/authorize
```
OAuth 2.0 인증 플로우를 시작합니다.

#### 2. 토큰 엔드포인트
```
POST /api/oauth/token
```
인증 코드를 액세스 토큰으로 교환하거나 토큰을 갱신합니다.

#### 3. 사용자 정보 엔드포인트
```
GET /api/oauth/userinfo
Authorization: Bearer {access_token}
```

**응답 예시:**
```json
{
  "sub": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "name": "홍길동",
  "groups": ["개발팀"],
  "is_admin": false,
  "group_id": "456e7890-e89b-12d3-a456-426614174000",
  "group_name": "개발팀",
  "role_id": "789e0123-e89b-12d3-a456-426614174000",
  "role_name": "개발자"
}
```

#### 4. 토큰 취소 엔드포인트
```
POST /api/oauth/revoke
Content-Type: application/x-www-form-urlencoded

token={access_token}&
token_type_hint=access_token&
client_id=maxlab
```

### 사용자 API

모든 사용자 API는 유효한 액세스 토큰이 필요합니다.

#### 1. 사용자 검색
```
GET /api/users/search?email=user@example.com
GET /api/users/search?name=홍길동
Authorization: Bearer {access_token}
```

**응답 예시:**
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "real_name": "홍길동",
    "display_name": "길동",
    "department": "개발팀",
    "position": "선임개발자",
    "is_active": true,
    "group_id": "456e7890-e89b-12d3-a456-426614174000",
    "group_name": "개발팀"
  }
]
```

#### 2. 내 프로필 조회
```
GET /api/users/me
Authorization: Bearer {access_token}
```

#### 3. UUID로 사용자 조회
```
GET /api/users/{user_id}
Authorization: Bearer {access_token}
```

#### 4. 이메일로 사용자 UUID 조회
```
GET /api/users/email/{email}
Authorization: Bearer {access_token}
```

이 엔드포인트는 이메일을 UUID로 변환할 때 사용합니다.

### 그룹 API

#### 1. 그룹 검색
```
GET /api/groups/search?name=개발팀
Authorization: Bearer {access_token}
```

**응답 예시:**
```json
[
  {
    "id": "456e7890-e89b-12d3-a456-426614174000",
    "name": "dev-team",
    "display_name": "개발팀",
    "description": "소프트웨어 개발팀",
    "is_active": true,
    "member_count": 15
  }
]
```

#### 2. 내 그룹 조회
```
GET /api/groups/my
Authorization: Bearer {access_token}
```

#### 3. UUID로 그룹 조회
```
GET /api/groups/{group_id}
Authorization: Bearer {access_token}
```

#### 4. 그룹명으로 그룹 정보 조회
```
GET /api/groups/name/{group_name}
Authorization: Bearer {access_token}
```

#### 5. 그룹 멤버 목록 조회
```
GET /api/groups/{group_id}/members?limit=50&skip=0
Authorization: Bearer {access_token}
```

## UUID 기반 통신

MAX Platform의 모든 엔티티는 UUID(Universally Unique Identifier)를 사용하여 식별됩니다.

### UUID 형식
- **표준 UUID v4 형식**: `123e4567-e89b-12d3-a456-426614174000`
- **PostgreSQL UUID 타입** 사용

### 사용자 UUID
- 모든 사용자는 생성 시 고유한 UUID를 부여받습니다
- JWT 토큰의 `sub` 클레임에 사용자 UUID가 포함됩니다
- API 응답의 `id` 필드가 사용자 UUID입니다

### 그룹 UUID
- 모든 그룹은 고유한 UUID를 가집니다
- 사용자는 하나의 그룹에만 속할 수 있습니다
- JWT 토큰에 `group_id`로 포함됩니다

### UUID 매핑
다른 시스템에서 이메일이나 그룹명만 알고 있을 때 UUID로 변환하는 방법:

1. **이메일 → 사용자 UUID**
   ```
   GET /api/users/email/user@example.com
   ```

2. **그룹명 → 그룹 UUID**
   ```
   GET /api/groups/name/dev-team
   ```

## 토큰 구조 및 정보

MAX Platform은 JWT(JSON Web Token)를 사용합니다.

### 액세스 토큰 페이로드
```json
{
  "sub": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "is_admin": false,
  "group_id": "456e7890-e89b-12d3-a456-426614174000",
  "group_name": "개발팀",
  "role_id": "789e0123-e89b-12d3-a456-426614174000",
  "role_name": "개발자",
  "type": "access",
  "iat": 1704067200,
  "exp": 1704070800,
  "jti": "unique-token-id",
  "iss": "maxplatform"
}
```

### 서비스 토큰 페이로드 (Client Credentials)
```json
{
  "sub": "service:maxlab",
  "client_id": "maxlab",
  "scope": "admin:oauth admin:users",
  "token_type": "service",
  "iss": "maxplatform",
  "iat": 1704067200,
  "exp": 1704153600
}
```

### 스코프(Scope) 설명

#### 기본 스코프
- `read:profile`: 사용자 프로필 정보 읽기
- `read:features`: 기능 목록 및 권한 정보 읽기
- `read:groups`: 그룹 정보 읽기

#### 관리 스코프
- `manage:workflows`: 워크플로우 생성, 편집, 삭제
- `manage:teams`: 팀 관리 및 멤버 관리
- `manage:experiments`: 실험 및 연구 데이터 관리
- `manage:workspaces`: 작업공간 관리
- `manage:apis`: API 관리 및 자동화
- `manage:models`: 머신러닝 모델 관리

#### 관리자 스코프 (서비스 토큰 전용)
- `admin:oauth`: OAuth 클라이언트 및 토큰 관리
- `admin:users`: 사용자 관리 및 계정 제어
- `admin:system`: 시스템 설정 및 구성 관리

## 구현 예제

### JavaScript/TypeScript 예제

#### PKCE 헬퍼 함수
```javascript
// PKCE 코드 생성
function generateCodeVerifier() {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  return base64URLEncode(array);
}

function base64URLEncode(buffer) {
  return btoa(String.fromCharCode.apply(null, new Uint8Array(buffer)))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');
}

async function generateCodeChallenge(verifier) {
  const encoder = new TextEncoder();
  const data = encoder.encode(verifier);
  const digest = await crypto.subtle.digest('SHA-256', data);
  return base64URLEncode(digest);
}
```

#### OAuth 로그인 구현
```javascript
class OAuthClient {
  constructor(config) {
    this.clientId = config.clientId;
    this.redirectUri = config.redirectUri;
    this.authUrl = 'http://localhost:8000/api/oauth/authorize';
    this.tokenUrl = 'http://localhost:8000/api/oauth/token';
  }

  async login() {
    // PKCE 준비
    const codeVerifier = generateCodeVerifier();
    const codeChallenge = await generateCodeChallenge(codeVerifier);
    const state = generateRandomString();
    
    // 세션에 저장
    sessionStorage.setItem('code_verifier', codeVerifier);
    sessionStorage.setItem('oauth_state', state);
    
    // 인증 URL 생성
    const params = new URLSearchParams({
      response_type: 'code',
      client_id: this.clientId,
      redirect_uri: this.redirectUri,
      state: state,
      scope: 'read:profile read:groups',
      code_challenge: codeChallenge,
      code_challenge_method: 'S256'
    });
    
    // 리다이렉트
    window.location.href = `${this.authUrl}?${params}`;
  }

  async handleCallback(code, state) {
    // State 검증
    const savedState = sessionStorage.getItem('oauth_state');
    if (state !== savedState) {
      throw new Error('Invalid state parameter');
    }
    
    // Code Verifier 가져오기
    const codeVerifier = sessionStorage.getItem('code_verifier');
    
    // 토큰 교환
    const response = await fetch(this.tokenUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        code: code,
        redirect_uri: this.redirectUri,
        client_id: this.clientId,
        code_verifier: codeVerifier
      })
    });
    
    if (!response.ok) {
      throw new Error('Token exchange failed');
    }
    
    const tokens = await response.json();
    
    // 토큰 저장
    localStorage.setItem('access_token', tokens.access_token);
    localStorage.setItem('refresh_token', tokens.refresh_token);
    
    // 세션 정리
    sessionStorage.removeItem('code_verifier');
    sessionStorage.removeItem('oauth_state');
    
    return tokens;
  }
}
```

#### API 호출 예제
```javascript
class MaxPlatformAPI {
  constructor(accessToken) {
    this.accessToken = accessToken;
    this.apiUrl = 'http://localhost:8000/api';
  }

  async request(endpoint, options = {}) {
    const response = await fetch(`${this.apiUrl}${endpoint}`, {
      ...options,
      headers: {
        'Authorization': `Bearer ${this.accessToken}`,
        'Content-Type': 'application/json',
        ...options.headers
      }
    });
    
    if (!response.ok) {
      throw new Error(`API request failed: ${response.statusText}`);
    }
    
    return response.json();
  }

  // 내 정보 조회
  async getMyProfile() {
    return this.request('/users/me');
  }

  // 이메일로 사용자 UUID 조회
  async getUserUUIDByEmail(email) {
    const user = await this.request(`/users/email/${encodeURIComponent(email)}`);
    return user.id;
  }

  // 그룹 멤버 조회
  async getGroupMembers(groupId, limit = 50, skip = 0) {
    return this.request(`/groups/${groupId}/members?limit=${limit}&skip=${skip}`);
  }

  // 토큰 갱신
  async refreshToken(refreshToken) {
    const response = await fetch('http://localhost:8000/api/oauth/token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: new URLSearchParams({
        grant_type: 'refresh_token',
        refresh_token: refreshToken,
        client_id: 'maxlab',
        client_secret: 'secret_lab_2025_dev'
      })
    });
    
    if (!response.ok) {
      throw new Error('Token refresh failed');
    }
    
    return response.json();
  }
}
```

### Python 예제

```python
import requests
import secrets
import hashlib
import base64
from urllib.parse import urlencode

class MaxPlatformOAuth:
    def __init__(self, client_id, client_secret, redirect_uri):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.base_url = 'http://localhost:8000'
        
    def generate_pkce_pair():
        """PKCE 코드 생성"""
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b'=').decode('utf-8')
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).rstrip(b'=').decode('utf-8')
        return code_verifier, code_challenge
    
    def get_authorization_url(self, state, scope='read:profile read:groups'):
        """인증 URL 생성"""
        code_verifier, code_challenge = self.generate_pkce_pair()
        
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'state': state,
            'scope': scope,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256'
        }
        
        auth_url = f"{self.base_url}/api/oauth/authorize?{urlencode(params)}"
        return auth_url, code_verifier
    
    def exchange_code_for_token(self, code, code_verifier):
        """인증 코드를 토큰으로 교환"""
        token_url = f"{self.base_url}/api/oauth/token"
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code_verifier': code_verifier
        }
        
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        
        return response.json()
    
    def refresh_access_token(self, refresh_token):
        """액세스 토큰 갱신"""
        token_url = f"{self.base_url}/api/oauth/token"
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        
        return response.json()

class MaxPlatformAPI:
    def __init__(self, access_token):
        self.access_token = access_token
        self.base_url = 'http://localhost:8000/api'
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
    
    def get_user_info(self):
        """현재 사용자 정보 조회"""
        response = requests.get(f"{self.base_url}/oauth/userinfo", headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_user_by_email(self, email):
        """이메일로 사용자 조회"""
        response = requests.get(f"{self.base_url}/users/email/{email}", headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_group_members(self, group_id, limit=50, skip=0):
        """그룹 멤버 목록 조회"""
        params = {'limit': limit, 'skip': skip}
        response = requests.get(
            f"{self.base_url}/groups/{group_id}/members", 
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def search_users(self, email=None, name=None, limit=10):
        """사용자 검색"""
        params = {'limit': limit}
        if email:
            params['email'] = email
        if name:
            params['name'] = name
            
        response = requests.get(
            f"{self.base_url}/users/search",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        return response.json()

# 서비스 간 통신 (Client Credentials)
class MaxPlatformService:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = 'http://localhost:8000'
        self.access_token = None
    
    def authenticate(self):
        """서비스 인증"""
        token_url = f"{self.base_url}/api/oauth/token"
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'admin:oauth admin:users'
        }
        
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        self.access_token = token_data['access_token']
        return token_data
```

### cURL 예제

#### 사용자 인증 (Authorization Code)
```bash
# 1. 브라우저에서 인증 URL 접속
# http://localhost:8000/api/oauth/authorize?response_type=code&client_id=maxlab&redirect_uri=http://localhost:3003/oauth/callback&state=xyz123

# 2. 받은 인증 코드로 토큰 교환
curl -X POST http://localhost:8000/api/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code=RECEIVED_AUTH_CODE" \
  -d "redirect_uri=http://localhost:3003/oauth/callback" \
  -d "client_id=maxlab" \
  -d "client_secret=secret_lab_2025_dev"
```

#### 서비스 인증 (Client Credentials)
```bash
curl -X POST http://localhost:8000/api/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=maxlab" \
  -d "client_secret=secret_lab_2025_dev" \
  -d "scope=admin:oauth admin:users"
```

#### API 호출
```bash
# 사용자 정보 조회
curl -X GET http://localhost:8000/api/oauth/userinfo \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# 이메일로 사용자 UUID 조회
curl -X GET http://localhost:8000/api/users/email/user@example.com \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# 그룹 멤버 조회
curl -X GET http://localhost:8000/api/groups/GROUP_UUID/members?limit=10 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 보안 고려사항

### 1. PKCE (Proof Key for Code Exchange) 사용
공개 클라이언트(SPA, 모바일 앱)는 반드시 PKCE를 사용해야 합니다.

### 2. 토큰 저장
- **액세스 토큰**: 메모리 또는 sessionStorage에 저장 (XSS 위험 최소화)
- **리프레시 토큰**: HttpOnly 쿠키 또는 안전한 저장소에 저장
- **절대 localStorage에 민감한 토큰을 저장하지 마세요**

### 3. CORS 설정
MAX Platform은 등록된 클라이언트의 origin만 허용합니다:
```
Access-Control-Allow-Origin: http://localhost:3003
Access-Control-Allow-Credentials: true
```

### 4. HTTPS 사용
프로덕션 환경에서는 반드시 HTTPS를 사용하세요.

### 5. State 파라미터
CSRF 공격을 방지하기 위해 항상 state 파라미터를 사용하고 검증하세요.

### 6. 토큰 만료 처리
- 액세스 토큰: 1시간 (3600초)
- 리프레시 토큰: 30일
- 서비스 토큰: 24시간

## 오류 처리

### 일반적인 오류 코드

#### OAuth 오류
| 오류 코드 | 설명 | 해결 방법 |
|---------|------|----------|
| `invalid_request` | 필수 파라미터 누락 | 요청 파라미터 확인 |
| `invalid_client` | 잘못된 클라이언트 정보 | client_id와 client_secret 확인 |
| `invalid_grant` | 잘못되거나 만료된 인증 코드/리프레시 토큰 | 새로운 인증 플로우 시작 |
| `unauthorized_client` | 클라이언트가 해당 grant type 사용 불가 | 클라이언트 설정 확인 |
| `unsupported_grant_type` | 지원하지 않는 grant type | grant_type 파라미터 확인 |
| `invalid_scope` | 요청한 스코프가 허용되지 않음 | 허용된 스코프 확인 |

#### API 오류
| HTTP 상태 | 설명 | 해결 방법 |
|----------|------|----------|
| 401 | 인증 실패 | 토큰 유효성 확인 |
| 403 | 권한 없음 | 필요한 스코프나 권한 확인 |
| 404 | 리소스 없음 | UUID나 엔드포인트 확인 |
| 429 | 요청 제한 초과 | 잠시 후 재시도 |

### 토큰 만료 처리 예제

```javascript
class APIClient {
  async makeRequest(endpoint, options = {}) {
    try {
      const response = await fetch(endpoint, {
        ...options,
        headers: {
          'Authorization': `Bearer ${this.accessToken}`,
          ...options.headers
        }
      });
      
      if (response.status === 401) {
        // 토큰 만료, 갱신 시도
        await this.refreshAccessToken();
        
        // 재시도
        return fetch(endpoint, {
          ...options,
          headers: {
            'Authorization': `Bearer ${this.accessToken}`,
            ...options.headers
          }
        });
      }
      
      return response;
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }
  
  async refreshAccessToken() {
    const response = await fetch('http://localhost:8000/api/oauth/token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: new URLSearchParams({
        grant_type: 'refresh_token',
        refresh_token: this.refreshToken,
        client_id: this.clientId,
        client_secret: this.clientSecret
      })
    });
    
    if (!response.ok) {
      // 리프레시 토큰도 만료, 재로그인 필요
      throw new Error('Token refresh failed, re-authentication required');
    }
    
    const tokens = await response.json();
    this.accessToken = tokens.access_token;
    this.refreshToken = tokens.refresh_token;
    
    // 새 토큰 저장
    this.saveTokens(tokens);
  }
}
```

## 참고사항

### 등록된 클라이언트 정보
| Client ID | 설명 | Redirect URI |
|-----------|------|-------------|
| maxflowstudio | 비주얼 워크플로우 디자인 플랫폼 | http://localhost:3005/oauth/callback |
| maxteamsync | 팀 협업 및 동기화 플랫폼 | http://localhost:3015/oauth/callback |
| maxlab | 실험 및 연구개발 플랫폼 | http://localhost:3010/oauth/callback |
| maxworkspace | 통합 작업공간 플랫폼 | http://localhost:3020/oauth/callback |
| maxapa | API 관리 및 자동화 플랫폼 | http://localhost:3035/oauth/callback |
| maxmlops | 머신러닝 운영 및 배포 플랫폼 | http://localhost:3040/oauth/callback |
| maxqueryhub | Query 종합 Platform | http://localhost:3025/oauth/callback |
| maxllm | maxllm | http://localhost:3030/oauth/callback |

### 추가 리소스
- [OAuth 2.0 RFC 6749](https://tools.ietf.org/html/rfc6749)
- [PKCE RFC 7636](https://tools.ietf.org/html/rfc7636)
- [JWT RFC 7519](https://tools.ietf.org/html/rfc7519)

### 지원 및 문의
기술 지원이 필요하신 경우 MAX Platform 관리자에게 문의하세요.