# MAX Platform OAuth 2.0 Integration Guide

## 목차
1. [시스템 개요](#시스템-개요)
2. [OAuth 2.0 서버 정보](#oauth-20-서버-정보)
3. [클라이언트 등록](#클라이언트-등록)
4. [Authorization Code Flow 구현](#authorization-code-flow-구현)
5. [API 레퍼런스](#api-레퍼런스)
6. [보안 고려사항](#보안-고려사항)
7. [예제 코드](#예제-코드)
8. [문제 해결](#문제-해결)

---

## 시스템 개요

MAX Platform OAuth 2.0 서버는 MAX 생태계의 여러 서비스 간 안전한 인증 및 권한 부여를 제공하는 중앙 집중식 인증 서버입니다.

### 주요 특징
- **OAuth 2.0 표준 준수**: RFC 6749, RFC 7636 (PKCE) 지원
- **PKCE 지원**: 공개 클라이언트를 위한 추가 보안
- **JWT 토큰**: 자체 포함된 액세스 토큰으로 확장성 향상
- **스코프 기반 권한**: 세밀한 권한 제어
- **감사 로깅**: 모든 인증 활동 추적
- **자동 승인**: 신뢰할 수 있는 클라이언트를 위한 사용자 경험 개선

### 지원하는 OAuth 2.0 플로우
- **Authorization Code Flow**: 기밀 및 공개 클라이언트
- **Authorization Code Flow with PKCE**: 보안 강화된 공개 클라이언트

---

## OAuth 2.0 서버 정보

### 서버 엔드포인트
```
Base URL: http://localhost:8000/api/oauth
Discovery URL: http://localhost:8000/api/oauth/.well-known/oauth-authorization-server
```

### 핵심 엔드포인트
- **Authorization Endpoint**: `GET /api/oauth/authorize`
- **Token Endpoint**: `POST /api/oauth/token`
- **UserInfo Endpoint**: `GET /api/oauth/userinfo`
- **Revocation Endpoint**: `POST /api/oauth/revoke`
- **Introspection Endpoint**: `POST /api/oauth/introspect`

---

## 클라이언트 등록

### 관리자를 통한 등록
외부 시스템이 MAX Platform OAuth 2.0을 사용하려면 먼저 클라이언트를 등록해야 합니다.

#### 필수 정보
```json
{
  "client_id": "your-app-name",
  "client_secret": "generated-secret",
  "redirect_uris": [
    "https://your-app.com/oauth/callback",
    "https://your-app.com/auth/callback"
  ],
  "allowed_scopes": [
    "read:profile",
    "read:features",
    "read:groups"
  ],
  "is_confidential": true,
  "is_active": true
}
```

#### 사용 가능한 스코프
- `read:profile`: 사용자 프로필 정보 읽기
- `read:features`: 기능 정보 읽기
- `read:groups`: 그룹 정보 읽기
- `manage:workflows`: 워크플로우 관리
- `manage:teams`: 팀 관리
- `manage:experiments`: 실험 관리
- `manage:workspaces`: 작업공간 관리
- `manage:apis`: API 관리
- `manage:models`: 모델 관리

---

## Authorization Code Flow 구현

### 1단계: 인증 요청
사용자를 Authorization 엔드포인트로 리디렉트합니다.

```http
GET /api/oauth/authorize?
  response_type=code&
  client_id=YOUR_CLIENT_ID&
  redirect_uri=YOUR_REDIRECT_URI&
  scope=read:profile read:features&
  state=RANDOM_STATE_VALUE&
  code_challenge=CODE_CHALLENGE&
  code_challenge_method=S256
```

#### 필수 파라미터
- `response_type`: 항상 "code"
- `client_id`: 등록된 클라이언트 ID
- `redirect_uri`: 등록된 리디렉트 URI 중 하나

#### 선택적 파라미터
- `scope`: 요청할 권한 (공백으로 구분)
- `state`: CSRF 방지를 위한 랜덤 값
- `code_challenge`: PKCE용 코드 챌린지
- `code_challenge_method`: "S256" 또는 "plain"

### 2단계: 인증 코드 수신
사용자가 권한을 승인하면 리디렉트 URI로 인증 코드가 전송됩니다.

```http
HTTP/1.1 302 Found
Location: YOUR_REDIRECT_URI?code=AUTHORIZATION_CODE&state=RANDOM_STATE_VALUE
```

### 3단계: 액세스 토큰 교환
인증 코드를 액세스 토큰으로 교환합니다.

```http
POST /api/oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&
code=AUTHORIZATION_CODE&
redirect_uri=YOUR_REDIRECT_URI&
client_id=YOUR_CLIENT_ID&
client_secret=YOUR_CLIENT_SECRET&
code_verifier=CODE_VERIFIER
```

#### 성공 응답
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "scope": "read:profile read:features"
}
```

### 4단계: 사용자 정보 조회
액세스 토큰을 사용하여 사용자 정보를 조회합니다.

```http
GET /api/oauth/userinfo
Authorization: Bearer ACCESS_TOKEN
```

#### 응답
```json
{
  "sub": "21a2aaa7-444a-4038-bda3-d8bf2c4ef162",
  "email": "admin@test.com",
  "real_name": "관리자",
  "display_name": "admin",
  "is_admin": true,
  "is_verified": true,
  "groups": [
    {
      "id": "932d657e-55df-49d7-9cc5-d86e7623df8e",
      "name": "관리자"
    }
  ]
}
```

---

## API 레퍼런스

### Authorization Endpoint

#### 요청
```http
GET /api/oauth/authorize
```

#### 파라미터
| 파라미터 | 필수 | 설명 |
|---------|------|------|
| response_type | ✅ | "code" 고정 |
| client_id | ✅ | 클라이언트 식별자 |
| redirect_uri | ✅ | 등록된 리디렉트 URI |
| scope | ❌ | 요청할 권한 목록 |
| state | ❌ | CSRF 방지용 상태값 |
| code_challenge | ❌ | PKCE 코드 챌린지 |
| code_challenge_method | ❌ | "S256" 또는 "plain" |

#### 응답
- **성공**: 302 Redirect to redirect_uri with code
- **오류**: 400 Bad Request with error details

### Token Endpoint

#### 요청
```http
POST /api/oauth/token
Content-Type: application/x-www-form-urlencoded
```

#### 파라미터
| 파라미터 | 필수 | 설명 |
|---------|------|------|
| grant_type | ✅ | "authorization_code" |
| code | ✅ | 인증 코드 |
| redirect_uri | ✅ | 인증 요청 시와 동일한 URI |
| client_id | ✅ | 클라이언트 식별자 |
| client_secret | ❌ | 기밀 클라이언트만 필요 |
| code_verifier | ❌ | PKCE 사용 시 필요 |

#### 응답
```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 1800,
  "scope": "string"
}
```

#### 오류 응답
```json
{
  "error": "invalid_grant",
  "error_description": "The authorization code is invalid or expired"
}
```

### UserInfo Endpoint

#### 요청
```http
GET /api/oauth/userinfo
Authorization: Bearer ACCESS_TOKEN
```

#### 응답
```json
{
  "sub": "string",
  "email": "string",
  "real_name": "string",
  "display_name": "string",
  "is_admin": boolean,
  "is_verified": boolean,
  "groups": [
    {
      "id": "string",
      "name": "string"
    }
  ]
}
```

### Revocation Endpoint

#### 요청
```http
POST /api/oauth/revoke
Content-Type: application/x-www-form-urlencoded

token=ACCESS_TOKEN&
client_id=YOUR_CLIENT_ID&
client_secret=YOUR_CLIENT_SECRET
```

#### 응답
```json
{
  "revoked": true
}
```

### Introspection Endpoint

#### 요청
```http
POST /api/oauth/introspect
Content-Type: application/x-www-form-urlencoded

token=ACCESS_TOKEN&
client_id=YOUR_CLIENT_ID&
client_secret=YOUR_CLIENT_SECRET
```

#### 응답
```json
{
  "active": true,
  "scope": "read:profile read:features",
  "client_id": "your-client-id",
  "username": "admin@test.com",
  "exp": 1751423519
}
```

---

## 보안 고려사항

### PKCE (Proof Key for Code Exchange)
공개 클라이언트는 반드시 PKCE를 사용해야 합니다.

#### Code Verifier 생성
```javascript
function generateCodeVerifier() {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  return base64URLEncode(array);
}
```

#### Code Challenge 생성
```javascript
async function generateCodeChallenge(verifier) {
  const encoder = new TextEncoder();
  const data = encoder.encode(verifier);
  const digest = await crypto.subtle.digest('SHA-256', data);
  return base64URLEncode(new Uint8Array(digest));
}
```

### State 파라미터
CSRF 공격을 방지하기 위해 항상 state 파라미터를 사용하세요.

```javascript
function generateState() {
  const array = new Uint8Array(16);
  crypto.getRandomValues(array);
  return base64URLEncode(array);
}
```

### 토큰 저장
- **웹 애플리케이션**: HttpOnly 쿠키 사용 권장
- **SPA**: Secure Storage 또는 메모리에 저장
- **모바일 앱**: Keychain (iOS) 또는 KeyStore (Android) 사용

---

## 예제 코드

### JavaScript (Frontend)

```javascript
class MaxPlatformOAuth {
  constructor(clientId, redirectUri) {
    this.clientId = clientId;
    this.redirectUri = redirectUri;
    this.authUrl = 'http://localhost:8000/api/oauth';
  }

  // PKCE 구현
  async generatePKCE() {
    const codeVerifier = this.generateCodeVerifier();
    const codeChallenge = await this.generateCodeChallenge(codeVerifier);
    
    return { codeVerifier, codeChallenge };
  }

  generateCodeVerifier() {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    return this.base64URLEncode(array);
  }

  async generateCodeChallenge(verifier) {
    const encoder = new TextEncoder();
    const data = encoder.encode(verifier);
    const digest = await crypto.subtle.digest('SHA-256', data);
    return this.base64URLEncode(new Uint8Array(digest));
  }

  base64URLEncode(array) {
    return btoa(String.fromCharCode(...array))
      .replace(/\\+/g, '-')
      .replace(/\\//g, '_')
      .replace(/=/g, '');
  }

  // 인증 시작
  async startAuth(scopes = ['read:profile']) {
    const state = this.generateCodeVerifier(); // 간단한 state 생성
    const { codeVerifier, codeChallenge } = await this.generatePKCE();
    
    // 세션 스토리지에 저장
    sessionStorage.setItem('oauth_state', state);
    sessionStorage.setItem('oauth_code_verifier', codeVerifier);
    
    const params = new URLSearchParams({
      response_type: 'code',
      client_id: this.clientId,
      redirect_uri: this.redirectUri,
      scope: scopes.join(' '),
      state: state,
      code_challenge: codeChallenge,
      code_challenge_method: 'S256'
    });
    
    window.location.href = `${this.authUrl}/authorize?${params}`;
  }

  // 콜백 처리
  async handleCallback() {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const state = urlParams.get('state');
    const error = urlParams.get('error');
    
    if (error) {
      throw new Error(`OAuth Error: ${error}`);
    }
    
    const storedState = sessionStorage.getItem('oauth_state');
    if (state !== storedState) {
      throw new Error('Invalid state parameter');
    }
    
    const codeVerifier = sessionStorage.getItem('oauth_code_verifier');
    sessionStorage.removeItem('oauth_state');
    sessionStorage.removeItem('oauth_code_verifier');
    
    return await this.exchangeCodeForToken(code, codeVerifier);
  }

  // 토큰 교환
  async exchangeCodeForToken(code, codeVerifier) {
    const response = await fetch(`${this.authUrl}/token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
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
      const error = await response.json();
      throw new Error(error.error_description || 'Token exchange failed');
    }
    
    return await response.json();
  }

  // 사용자 정보 조회
  async getUserInfo(accessToken) {
    const response = await fetch(`${this.authUrl}/userinfo`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch user info');
    }
    
    return await response.json();
  }
}

// 사용 예제
const oauth = new MaxPlatformOAuth('your-client-id', 'https://your-app.com/callback');

// 로그인 시작
oauth.startAuth(['read:profile', 'read:features']);

// 콜백 페이지에서
oauth.handleCallback()
  .then(tokenResponse => {
    console.log('Access Token:', tokenResponse.access_token);
    return oauth.getUserInfo(tokenResponse.access_token);
  })
  .then(userInfo => {
    console.log('User Info:', userInfo);
  })
  .catch(error => {
    console.error('OAuth Error:', error);
  });
```

### Python (Backend)

```python
import requests
import secrets
import hashlib
import base64
from urllib.parse import urlencode, parse_qs

class MaxPlatformOAuth:
    def __init__(self, client_id, client_secret, redirect_uri):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.auth_url = 'http://localhost:8000/api/oauth'
    
    def generate_pkce(self):
        """PKCE 코드 챌린지 생성"""
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        return code_verifier, code_challenge
    
    def get_authorization_url(self, scopes=None):
        """인증 URL 생성"""
        if scopes is None:
            scopes = ['read:profile']
        
        state = secrets.token_urlsafe(32)
        code_verifier, code_challenge = self.generate_pkce()
        
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(scopes),
            'state': state,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256'
        }
        
        auth_url = f"{self.auth_url}/authorize?{urlencode(params)}"
        
        return {
            'auth_url': auth_url,
            'state': state,
            'code_verifier': code_verifier
        }
    
    def exchange_code_for_token(self, code, code_verifier):
        """인증 코드를 액세스 토큰으로 교환"""
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code_verifier': code_verifier
        }
        
        response = requests.post(f"{self.auth_url}/token", data=data)
        response.raise_for_status()
        
        return response.json()
    
    def get_user_info(self, access_token):
        """사용자 정보 조회"""
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(f"{self.auth_url}/userinfo", headers=headers)
        response.raise_for_status()
        
        return response.json()
    
    def revoke_token(self, token):
        """토큰 취소"""
        data = {
            'token': token,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        response = requests.post(f"{self.auth_url}/revoke", data=data)
        response.raise_for_status()
        
        return response.json()

# 사용 예제
oauth = MaxPlatformOAuth('your-client-id', 'your-client-secret', 'https://your-app.com/callback')

# 1. 인증 URL 생성
auth_data = oauth.get_authorization_url(['read:profile', 'read:features'])
print(f"Visit: {auth_data['auth_url']}")

# 2. 콜백에서 토큰 교환 (Flask 예제)
from flask import Flask, request, redirect

app = Flask(__name__)

@app.route('/callback')
def oauth_callback():
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')
    
    if error:
        return f"OAuth Error: {error}", 400
    
    # state 검증 로직 필요
    code_verifier = session.get('oauth_code_verifier')  # 세션에서 가져오기
    
    try:
        token_response = oauth.exchange_code_for_token(code, code_verifier)
        user_info = oauth.get_user_info(token_response['access_token'])
        
        # 사용자 정보로 로그인 처리
        return f"Welcome {user_info['display_name']}!"
        
    except Exception as e:
        return f"Error: {str(e)}", 500
```

### Java (Spring Boot)

```java
@Component
public class MaxPlatformOAuthClient {
    
    private final String clientId;
    private final String clientSecret;
    private final String redirectUri;
    private final String authUrl = "http://localhost:8000/api/oauth";
    private final RestTemplate restTemplate;
    
    public MaxPlatformOAuthClient(@Value("${oauth.client-id}") String clientId,
                                  @Value("${oauth.client-secret}") String clientSecret,
                                  @Value("${oauth.redirect-uri}") String redirectUri) {
        this.clientId = clientId;
        this.clientSecret = clientSecret;
        this.redirectUri = redirectUri;
        this.restTemplate = new RestTemplate();
    }
    
    public static class PKCEData {
        public final String codeVerifier;
        public final String codeChallenge;
        
        public PKCEData(String codeVerifier, String codeChallenge) {
            this.codeVerifier = codeVerifier;
            this.codeChallenge = codeChallenge;
        }
    }
    
    public PKCEData generatePKCE() throws NoSuchAlgorithmException {
        SecureRandom random = new SecureRandom();
        byte[] bytes = new byte[32];
        random.nextBytes(bytes);
        
        String codeVerifier = Base64.getUrlEncoder()
            .withoutPadding()
            .encodeToString(bytes);
        
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        byte[] hash = digest.digest(codeVerifier.getBytes(StandardCharsets.UTF_8));
        String codeChallenge = Base64.getUrlEncoder()
            .withoutPadding()
            .encodeToString(hash);
        
        return new PKCEData(codeVerifier, codeChallenge);
    }
    
    public String getAuthorizationUrl(List<String> scopes) throws NoSuchAlgorithmException {
        PKCEData pkce = generatePKCE();
        String state = generateState();
        
        UriComponentsBuilder builder = UriComponentsBuilder.fromHttpUrl(authUrl + "/authorize")
            .queryParam("response_type", "code")
            .queryParam("client_id", clientId)
            .queryParam("redirect_uri", redirectUri)
            .queryParam("scope", String.join(" ", scopes))
            .queryParam("state", state)
            .queryParam("code_challenge", pkce.codeChallenge)
            .queryParam("code_challenge_method", "S256");
        
        // state와 codeVerifier를 세션에 저장해야 함
        
        return builder.toUriString();
    }
    
    public TokenResponse exchangeCodeForToken(String code, String codeVerifier) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_FORM_URLENCODED);
        
        MultiValueMap<String, String> params = new LinkedMultiValueMap<>();
        params.add("grant_type", "authorization_code");
        params.add("code", code);
        params.add("redirect_uri", redirectUri);
        params.add("client_id", clientId);
        params.add("client_secret", clientSecret);
        params.add("code_verifier", codeVerifier);
        
        HttpEntity<MultiValueMap<String, String>> request = new HttpEntity<>(params, headers);
        
        return restTemplate.postForObject(authUrl + "/token", request, TokenResponse.class);
    }
    
    public UserInfo getUserInfo(String accessToken) {
        HttpHeaders headers = new HttpHeaders();
        headers.setBearerAuth(accessToken);
        
        HttpEntity<?> request = new HttpEntity<>(headers);
        
        return restTemplate.exchange(
            authUrl + "/userinfo",
            HttpMethod.GET,
            request,
            UserInfo.class
        ).getBody();
    }
    
    private String generateState() {
        SecureRandom random = new SecureRandom();
        byte[] bytes = new byte[16];
        random.nextBytes(bytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }
}

// DTO 클래스들
public class TokenResponse {
    public String access_token;
    public String token_type;
    public int expires_in;
    public String scope;
}

public class UserInfo {
    public String sub;
    public String email;
    public String real_name;
    public String display_name;
    public boolean is_admin;
    public boolean is_verified;
    public List<Group> groups;
    
    public static class Group {
        public String id;
        public String name;
    }
}
```

---

## 문제 해결

### 일반적인 오류

#### 1. invalid_client
```json
{
  "error": "invalid_client",
  "error_description": "Client authentication failed"
}
```
**해결방법**: client_id와 client_secret이 올바른지 확인하세요.

#### 2. invalid_grant
```json
{
  "error": "invalid_grant",
  "error_description": "The authorization code is invalid or expired"
}
```
**해결방법**: 
- 인증 코드가 5분 이내에 사용되었는지 확인
- 인증 코드가 이미 사용되지 않았는지 확인
- redirect_uri가 인증 요청 시와 동일한지 확인

#### 3. invalid_scope
```json
{
  "error": "invalid_scope",
  "error_description": "The requested scope is invalid"
}
```
**해결방법**: 요청한 스코프가 클라이언트에 허용된 스코프인지 확인하세요.

#### 4. invalid_request
```json
{
  "error": "invalid_request",
  "error_description": "Missing required parameter: code_challenge"
}
```
**해결방법**: PKCE가 필수인 클라이언트는 code_challenge를 포함해야 합니다.

### 디버깅 팁

1. **요청 로그 확인**: 모든 OAuth 활동은 감사 로그에 기록됩니다.
2. **토큰 검증**: `/api/oauth/introspect` 엔드포인트로 토큰 상태를 확인하세요.
3. **브라우저 개발자 도구**: 네트워크 탭에서 요청/응답을 확인하세요.
4. **CORS 문제**: 프론트엔드에서 직접 호출 시 CORS 설정을 확인하세요.

### 성능 최적화

1. **토큰 캐싱**: 액세스 토큰을 적절히 캐싱하여 불필요한 요청을 줄이세요.
2. **배치 요청**: 여러 리소스가 필요한 경우 한 번에 요청하세요.
3. **스코프 최적화**: 필요한 최소한의 스코프만 요청하세요.

---

## 지원 및 문의

- **기술 문서**: 이 가이드
- **API 테스트**: http://localhost:8000/docs (Swagger UI)
- **관리자 페이지**: http://localhost:3000/admin (OAuth 클라이언트 관리)

이 가이드를 통해 MAX Platform OAuth 2.0을 성공적으로 통합하실 수 있습니다. 추가 질문이 있으시면 관리자에게 문의하세요.