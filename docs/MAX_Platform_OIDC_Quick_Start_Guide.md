# MAX Platform OIDC 빠른 시작 가이드

이 가이드는 MAX Platform에서 OpenID Connect (OIDC)를 빠르게 구현하는 방법을 설명합니다.

## 5분 안에 OIDC 구현하기

### 1단계: 클라이언트 설정

```bash
# 기존 OAuth 클라이언트에 OIDC 활성화
UPDATE oauth_clients 
SET oidc_enabled = true,
    allowed_scopes = array_cat(allowed_scopes, ARRAY['openid', 'profile', 'email'])
WHERE client_id = 'your-app-id';
```

### 2단계: 인증 코드 구현

```html
<!DOCTYPE html>
<html>
<head>
    <title>OIDC Login Example</title>
</head>
<body>
    <button onclick="login()">Login with MAX Platform</button>
    
    <script>
    // 설정
    const config = {
        authUrl: 'http://localhost:8000/api/oauth/authorize',
        tokenUrl: 'http://localhost:8000/api/oauth/token',
        clientId: 'your-app-id',
        redirectUri: 'http://localhost:3000/callback',
        scope: 'openid profile email'
    };
    
    // 상태 및 nonce 생성
    function generateRandomString() {
        const array = new Uint8Array(32);
        crypto.getRandomValues(array);
        return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
    }
    
    // 로그인 함수
    function login() {
        const state = generateRandomString();
        const nonce = generateRandomString();
        
        // 세션에 저장
        sessionStorage.setItem('oauth_state', state);
        sessionStorage.setItem('oauth_nonce', nonce);
        
        // 인증 URL 생성
        const params = new URLSearchParams({
            response_type: 'code',
            client_id: config.clientId,
            redirect_uri: config.redirectUri,
            scope: config.scope,
            state: state,
            nonce: nonce
        });
        
        // 리다이렉트
        window.location.href = `${config.authUrl}?${params}`;
    }
    </script>
</body>
</html>
```

### 3단계: 콜백 처리

```javascript
// callback.html 또는 callback route
async function handleCallback() {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const state = urlParams.get('state');
    const error = urlParams.get('error');
    
    // 에러 처리
    if (error) {
        console.error('Authentication error:', error);
        return;
    }
    
    // State 검증
    const savedState = sessionStorage.getItem('oauth_state');
    if (state !== savedState) {
        console.error('Invalid state parameter');
        return;
    }
    
    // 토큰 교환
    try {
        const tokens = await exchangeCodeForTokens(code);
        
        // ID Token 검증
        const userInfo = await verifyIdToken(tokens.id_token);
        console.log('User authenticated:', userInfo);
        
        // 토큰 저장
        sessionStorage.setItem('access_token', tokens.access_token);
        if (tokens.refresh_token) {
            sessionStorage.setItem('refresh_token', tokens.refresh_token);
        }
        
        // 메인 페이지로 이동
        window.location.href = '/dashboard';
        
    } catch (error) {
        console.error('Token exchange failed:', error);
    }
}

// 토큰 교환 함수
async function exchangeCodeForTokens(code) {
    const response = await fetch(config.tokenUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: new URLSearchParams({
            grant_type: 'authorization_code',
            code: code,
            redirect_uri: config.redirectUri,
            client_id: config.clientId,
            client_secret: 'your-client-secret' // 서버 사이드에서만 사용
        })
    });
    
    if (!response.ok) {
        throw new Error('Token exchange failed');
    }
    
    return await response.json();
}

// 페이지 로드 시 실행
window.addEventListener('load', handleCallback);
```

### 4단계: ID Token 검증

```javascript
// ID Token 검증 (간단한 버전)
async function verifyIdToken(idToken) {
    // JWT 디코딩
    const parts = idToken.split('.');
    const payload = JSON.parse(atob(parts[1]));
    
    // 기본 검증
    const now = Date.now() / 1000;
    
    // 만료 시간 확인
    if (payload.exp < now) {
        throw new Error('Token expired');
    }
    
    // 발급자 확인
    if (payload.iss !== 'http://localhost:8000') {
        throw new Error('Invalid issuer');
    }
    
    // 대상 확인
    if (payload.aud !== config.clientId) {
        throw new Error('Invalid audience');
    }
    
    // Nonce 확인
    const savedNonce = sessionStorage.getItem('oauth_nonce');
    if (payload.nonce !== savedNonce) {
        throw new Error('Invalid nonce');
    }
    
    return payload;
}

// 프로덕션에서는 공개 키로 서명 검증 필요
async function verifyIdTokenProduction(idToken) {
    // JWKS 엔드포인트에서 공개 키 가져오기
    const jwks = await fetch('http://localhost:8000/api/oauth/jwks')
        .then(res => res.json());
    
    // jose 라이브러리 사용 예시
    const { payload } = await jose.jwtVerify(idToken, 
        jose.createRemoteJWKSet(new URL('http://localhost:8000/api/oauth/jwks')),
        {
            issuer: 'http://localhost:8000',
            audience: config.clientId
        }
    );
    
    return payload;
}
```

### 5단계: API 호출

```javascript
// 인증된 API 호출
async function fetchUserProfile() {
    const accessToken = sessionStorage.getItem('access_token');
    
    const response = await fetch('http://localhost:8000/api/oauth/userinfo', {
        headers: {
            'Authorization': `Bearer ${accessToken}`
        }
    });
    
    if (!response.ok) {
        if (response.status === 401) {
            // 토큰 갱신 필요
            await refreshAccessToken();
            return fetchUserProfile(); // 재시도
        }
        throw new Error('API call failed');
    }
    
    return await response.json();
}

// 토큰 갱신
async function refreshAccessToken() {
    const refreshToken = sessionStorage.getItem('refresh_token');
    
    const response = await fetch(config.tokenUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: new URLSearchParams({
            grant_type: 'refresh_token',
            refresh_token: refreshToken,
            client_id: config.clientId
        })
    });
    
    const tokens = await response.json();
    sessionStorage.setItem('access_token', tokens.access_token);
    
    if (tokens.id_token) {
        // 새 ID Token도 검증
        await verifyIdToken(tokens.id_token);
    }
}
```

## React 예제

```jsx
import React, { useEffect, useState } from 'react';

// AuthContext.js
const AuthContext = React.createContext();

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    
    const config = {
        authUrl: 'http://localhost:8000/api/oauth/authorize',
        tokenUrl: 'http://localhost:8000/api/oauth/token',
        userInfoUrl: 'http://localhost:8000/api/oauth/userinfo',
        clientId: process.env.REACT_APP_CLIENT_ID,
        redirectUri: process.env.REACT_APP_REDIRECT_URI,
        scope: 'openid profile email'
    };
    
    const login = () => {
        const state = generateRandomString();
        const nonce = generateRandomString();
        
        sessionStorage.setItem('oauth_state', state);
        sessionStorage.setItem('oauth_nonce', nonce);
        
        const params = new URLSearchParams({
            response_type: 'code',
            client_id: config.clientId,
            redirect_uri: config.redirectUri,
            scope: config.scope,
            state,
            nonce
        });
        
        window.location.href = `${config.authUrl}?${params}`;
    };
    
    const logout = () => {
        sessionStorage.clear();
        setUser(null);
    };
    
    const handleCallback = async () => {
        const urlParams = new URLSearchParams(window.location.search);
        const code = urlParams.get('code');
        const state = urlParams.get('state');
        
        if (code && state === sessionStorage.getItem('oauth_state')) {
            try {
                const tokens = await exchangeCodeForTokens(code);
                const userInfo = await fetchUserInfo(tokens.access_token);
                setUser(userInfo);
                
                // URL에서 파라미터 제거
                window.history.replaceState({}, document.title, window.location.pathname);
            } catch (error) {
                console.error('Authentication failed:', error);
            }
        }
    };
    
    useEffect(() => {
        // 콜백 처리
        if (window.location.search.includes('code=')) {
            handleCallback();
        } else {
            // 기존 토큰 확인
            const accessToken = sessionStorage.getItem('access_token');
            if (accessToken) {
                fetchUserInfo(accessToken)
                    .then(setUser)
                    .catch(() => sessionStorage.clear());
            }
        }
        setLoading(false);
    }, []);
    
    return (
        <AuthContext.Provider value={{ user, login, logout, loading }}>
            {children}
        </AuthContext.Provider>
    );
};

// App.js
function App() {
    const { user, login, logout, loading } = React.useContext(AuthContext);
    
    if (loading) {
        return <div>Loading...</div>;
    }
    
    return (
        <div>
            {user ? (
                <div>
                    <h1>Welcome, {user.name}!</h1>
                    <p>Email: {user.email}</p>
                    <button onClick={logout}>Logout</button>
                </div>
            ) : (
                <div>
                    <h1>Please login</h1>
                    <button onClick={login}>Login with MAX Platform</button>
                </div>
            )}
        </div>
    );
}
```

## 일반적인 시나리오

### 1. SPA (Single Page Application)

```javascript
// PKCE를 사용한 공개 클라이언트 구현
class OIDCClient {
    constructor(config) {
        this.config = config;
    }
    
    async login() {
        // PKCE 코드 생성
        const codeVerifier = generateRandomString(128);
        const codeChallenge = await sha256(codeVerifier);
        
        sessionStorage.setItem('code_verifier', codeVerifier);
        
        const params = new URLSearchParams({
            response_type: 'code',
            client_id: this.config.clientId,
            redirect_uri: this.config.redirectUri,
            scope: 'openid profile email',
            state: generateRandomString(),
            nonce: generateRandomString(),
            code_challenge: codeChallenge,
            code_challenge_method: 'S256'
        });
        
        window.location.href = `${this.config.authUrl}?${params}`;
    }
    
    async handleCallback(code) {
        const codeVerifier = sessionStorage.getItem('code_verifier');
        
        const response = await fetch(this.config.tokenUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: new URLSearchParams({
                grant_type: 'authorization_code',
                code: code,
                redirect_uri: this.config.redirectUri,
                client_id: this.config.clientId,
                code_verifier: codeVerifier
            })
        });
        
        return await response.json();
    }
}

// SHA256 해시 함수
async function sha256(plain) {
    const encoder = new TextEncoder();
    const data = encoder.encode(plain);
    const hash = await crypto.subtle.digest('SHA-256', data);
    return btoa(String.fromCharCode(...new Uint8Array(hash)))
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=+$/, '');
}
```

### 2. 서버 사이드 애플리케이션

```python
# Python Flask 예제
from flask import Flask, redirect, request, session, url_for
import requests
import secrets
import jwt
from jwt import PyJWKClient

app = Flask(__name__)
app.secret_key = 'your-secret-key'

# 설정
OIDC_CONFIG = {
    'issuer': 'http://localhost:8000',
    'auth_endpoint': 'http://localhost:8000/api/oauth/authorize',
    'token_endpoint': 'http://localhost:8000/api/oauth/token',
    'userinfo_endpoint': 'http://localhost:8000/api/oauth/userinfo',
    'jwks_uri': 'http://localhost:8000/api/oauth/jwks',
    'client_id': 'your-app-id',
    'client_secret': 'your-client-secret',
    'redirect_uri': 'http://localhost:5000/callback'
}

@app.route('/login')
def login():
    # State와 nonce 생성
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    
    session['oauth_state'] = state
    session['oauth_nonce'] = nonce
    
    # 인증 URL 생성
    params = {
        'response_type': 'code',
        'client_id': OIDC_CONFIG['client_id'],
        'redirect_uri': OIDC_CONFIG['redirect_uri'],
        'scope': 'openid profile email',
        'state': state,
        'nonce': nonce
    }
    
    auth_url = f"{OIDC_CONFIG['auth_endpoint']}?" + \
               "&".join([f"{k}={v}" for k, v in params.items()])
    
    return redirect(auth_url)

@app.route('/callback')
def callback():
    # 에러 확인
    error = request.args.get('error')
    if error:
        return f"Authentication error: {error}", 400
    
    # State 검증
    state = request.args.get('state')
    if state != session.get('oauth_state'):
        return "Invalid state parameter", 400
    
    # 코드 교환
    code = request.args.get('code')
    token_response = requests.post(OIDC_CONFIG['token_endpoint'], data={
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': OIDC_CONFIG['redirect_uri'],
        'client_id': OIDC_CONFIG['client_id'],
        'client_secret': OIDC_CONFIG['client_secret']
    })
    
    tokens = token_response.json()
    
    # ID Token 검증
    jwks_client = PyJWKClient(OIDC_CONFIG['jwks_uri'])
    signing_key = jwks_client.get_signing_key_from_jwt(tokens['id_token'])
    
    id_token_payload = jwt.decode(
        tokens['id_token'],
        signing_key.key,
        algorithms=["RS256"],
        audience=OIDC_CONFIG['client_id'],
        issuer=OIDC_CONFIG['issuer']
    )
    
    # Nonce 검증
    if id_token_payload.get('nonce') != session.get('oauth_nonce'):
        return "Invalid nonce", 400
    
    # 세션에 사용자 정보 저장
    session['user'] = id_token_payload
    session['access_token'] = tokens['access_token']
    
    return redirect(url_for('profile'))

@app.route('/profile')
def profile():
    user = session.get('user')
    if not user:
        return redirect(url_for('login'))
    
    return f"""
        <h1>Welcome, {user.get('name', user['sub'])}!</h1>
        <p>Email: {user.get('email', 'N/A')}</p>
        <p>Groups: {', '.join(user.get('groups', []))}</p>
        <a href="/logout">Logout</a>
    """

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
```

## 자주 묻는 질문

### Q: OAuth 2.0과 OIDC의 차이점은?
A: OAuth 2.0은 권한 부여(Authorization)를 위한 프로토콜이고, OIDC는 OAuth 2.0 위에 인증(Authentication) 레이어를 추가한 것입니다. OIDC는 ID Token을 통해 사용자 신원을 확인합니다.

### Q: ID Token과 Access Token의 차이는?
A: 
- **ID Token**: 사용자 정보를 담은 JWT, 클라이언트가 사용
- **Access Token**: API 접근을 위한 토큰, 리소스 서버가 검증

### Q: nonce는 왜 필요한가요?
A: Nonce는 재생 공격을 방지합니다. 각 인증 요청마다 고유한 nonce를 생성하여 ID Token이 해당 요청에 대한 응답인지 확인합니다.

### Q: PKCE는 언제 사용해야 하나요?
A: 공개 클라이언트(SPA, 모바일 앱)에서는 client_secret을 안전하게 보관할 수 없으므로 PKCE를 사용해야 합니다.

## 다음 단계

- [전체 개발자 가이드](./MAX_Platform_OIDC_OAuth2_Developer_Guide.md) 읽기
- [보안 모범 사례](./MAX_Platform_OAuth_Security_Guide.md) 확인
- [API 레퍼런스](./MAX_Platform_OAuth_API_Reference.md) 참조

---

*더 많은 예제와 상세한 구현은 [GitHub 저장소](https://github.com/maxplatform/oidc-examples)를 참조하세요.*