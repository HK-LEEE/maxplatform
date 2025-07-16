# Refresh Token Resilience Guide

## 🎯 개요

이 문서는 MAX Platform OAuth 2.0 시스템에서 refresh token을 안전하고 안정적으로 사용하기 위한 클라이언트 가이드라인을 제공합니다.

## 🔄 Graceful Token Rotation 시스템

MAX Platform은 **Graceful Token Rotation**을 구현하여 네트워크 지연이나 일시적 연결 문제에 대한 복원력을 제공합니다.

### 핵심 특징:
- **10초 Grace Period**: 이전 토큰이 즉시 무효화되지 않고 10초간 유효
- **Token Family Tracking**: 토큰 간의 부모-자식 관계 추적
- **Automatic Cleanup**: 만료된 grace period 토큰 자동 정리
- **Enhanced Logging**: 토큰 순환 과정의 상세 로깅

## 📋 클라이언트 구현 가이드라인

### 1. 토큰 저장 및 관리

#### ✅ 권장사항:
```javascript
// 안전한 토큰 저장
class TokenManager {
    private static ACCESS_TOKEN_KEY = 'max_access_token';
    private static REFRESH_TOKEN_KEY = 'max_refresh_token';
    
    static saveTokens(accessToken: string, refreshToken: string) {
        // 암호화된 storage 사용 권장
        localStorage.setItem(this.ACCESS_TOKEN_KEY, accessToken);
        localStorage.setItem(this.REFRESH_TOKEN_KEY, refreshToken);
    }
    
    static getRefreshToken(): string | null {
        return localStorage.getItem(this.REFRESH_TOKEN_KEY);
    }
    
    static clearTokens() {
        localStorage.removeItem(this.ACCESS_TOKEN_KEY);
        localStorage.removeItem(this.REFRESH_TOKEN_KEY);
    }
}
```

#### ❌ 피해야 할 사항:
- 토큰을 URL 파라미터에 포함
- 토큰을 브라우저 콘솔에 출력
- 토큰을 쿠키에 저장 (XSS 취약성)

### 2. Refresh Token 갱신 로직

#### ✅ 권장 구현:
```javascript
class RefreshTokenService {
    private static isRefreshing = false;
    private static refreshSubscribers: Array<(token: string) => void> = [];
    
    static async refreshToken(): Promise<string> {
        // 동시 갱신 방지
        if (this.isRefreshing) {
            return new Promise((resolve) => {
                this.refreshSubscribers.push(resolve);
            });
        }
        
        this.isRefreshing = true;
        
        try {
            const refreshToken = TokenManager.getRefreshToken();
            if (!refreshToken) {
                throw new Error('No refresh token available');
            }
            
            const response = await this.performRefreshRequest(refreshToken);
            
            if (response.ok) {
                const tokens = await response.json();
                TokenManager.saveTokens(tokens.access_token, tokens.refresh_token);
                
                // 대기 중인 요청들에게 새 토큰 제공
                this.refreshSubscribers.forEach(callback => callback(tokens.access_token));
                this.refreshSubscribers = [];
                
                return tokens.access_token;
            } else {
                throw new Error(`Refresh failed: ${response.status}`);
            }
        } catch (error) {
            console.error('Token refresh failed:', error);
            TokenManager.clearTokens();
            // 로그인 페이지로 리디렉션
            window.location.href = '/login';
            throw error;
        } finally {
            this.isRefreshing = false;
        }
    }
    
    private static async performRefreshRequest(refreshToken: string) {
        return fetch('/api/oauth/token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                grant_type: 'refresh_token',
                refresh_token: refreshToken,
                client_id: 'your_client_id',
                client_secret: 'your_client_secret' // Public 클라이언트는 생략
            })
        });
    }
}
```

### 3. 오류 처리 및 재시도 로직

#### ✅ 지수 백오프 재시도:
```javascript
class RetryHandler {
    static async withRetry<T>(
        operation: () => Promise<T>,
        maxRetries: number = 3,
        baseDelay: number = 1000
    ): Promise<T> {
        for (let attempt = 0; attempt <= maxRetries; attempt++) {
            try {
                return await operation();
            } catch (error) {
                if (attempt === maxRetries) {
                    throw error;
                }
                
                // 지수 백오프 대기
                const delay = baseDelay * Math.pow(2, attempt);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
        throw new Error('Max retries exceeded');
    }
}

// 사용 예시
const newToken = await RetryHandler.withRetry(
    () => RefreshTokenService.refreshToken(),
    3, // 최대 3회 재시도
    500 // 초기 지연 500ms
);
```

### 4. HTTP 인터셉터 구현

#### ✅ Axios 인터셉터 예시:
```javascript
class ApiClient {
    constructor() {
        this.setupInterceptors();
    }
    
    setupInterceptors() {
        // 요청 인터셉터
        this.axios.interceptors.request.use((config) => {
            const token = TokenManager.getAccessToken();
            if (token) {
                config.headers.Authorization = `Bearer ${token}`;
            }
            return config;
        });
        
        // 응답 인터셉터
        this.axios.interceptors.response.use(
            (response) => response,
            async (error) => {
                const originalRequest = error.config;
                
                if (error.response?.status === 401 && !originalRequest._retry) {
                    originalRequest._retry = true;
                    
                    try {
                        const newToken = await RefreshTokenService.refreshToken();
                        originalRequest.headers.Authorization = `Bearer ${newToken}`;
                        return this.axios(originalRequest);
                    } catch (refreshError) {
                        // 리프레시도 실패하면 로그아웃
                        TokenManager.clearTokens();
                        window.location.href = '/login';
                        return Promise.reject(refreshError);
                    }
                }
                
                return Promise.reject(error);
            }
        );
    }
}
```

## 🛡️ 보안 고려사항

### 1. 토큰 저장 보안

#### ✅ 권장사항:
- **메모리 저장**: 가능하면 메모리에만 토큰 저장
- **암호화 저장**: 지속적 저장이 필요하면 암호화 사용
- **HttpOnly 쿠키**: 서버에서 설정하는 HttpOnly 쿠키 고려

#### ❌ 피해야 할 사항:
- 평문으로 localStorage에 저장
- sessionStorage에 민감한 토큰 저장
- 브라우저 히스토리에 토큰 노출

### 2. 토큰 전송 보안

#### ✅ 권장사항:
```javascript
// HTTPS 사용 강제
if (location.protocol !== 'https:' && location.hostname !== 'localhost') {
    location.replace(`https:${location.href.substring(location.protocol.length)}`);
}

// 보안 헤더 설정
const secureHeaders = {
    'Cache-Control': 'no-cache, no-store, must-revalidate',
    'Pragma': 'no-cache',
    'Expires': '0'
};
```

### 3. 토큰 생명주기 관리

#### ✅ 권장 정책:
```javascript
class TokenLifecycleManager {
    private static readonly ACCESS_TOKEN_BUFFER = 5 * 60 * 1000; // 5분 여유
    
    static isTokenExpiringSoon(token: string): boolean {
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            const expiryTime = payload.exp * 1000;
            return Date.now() + this.ACCESS_TOKEN_BUFFER > expiryTime;
        } catch {
            return true; // 파싱 실패하면 만료된 것으로 간주
        }
    }
    
    static async ensureValidToken(): Promise<string> {
        const currentToken = TokenManager.getAccessToken();
        
        if (!currentToken || this.isTokenExpiringSoon(currentToken)) {
            return await RefreshTokenService.refreshToken();
        }
        
        return currentToken;
    }
}
```

## 🔧 문제 해결 가이드

### 1. "Token hash not found" 오류

#### 원인:
- 토큰 전송 과정에서 문자열 손상
- 잘못된 클라이언트 ID 사용
- 토큰이 이미 회전됨

#### 해결방법:
```javascript
// 토큰 유효성 검사
function validateToken(token: string): boolean {
    // Base64 URL 인코딩 검사
    const tokenParts = token.split('.');
    if (tokenParts.length !== 3) {
        console.error('Invalid token format');
        return false;
    }
    
    // 특수 문자 검사
    const validBase64UrlPattern = /^[A-Za-z0-9_-]+$/;
    return tokenParts.every(part => validBase64UrlPattern.test(part));
}
```

### 2. 동시 토큰 갱신 문제

#### 해결방법:
```javascript
// 싱글톤 패턴으로 토큰 갱신 관리
class TokenRefreshManager {
    private static instance: TokenRefreshManager;
    private refreshPromise: Promise<string> | null = null;
    
    static getInstance(): TokenRefreshManager {
        if (!this.instance) {
            this.instance = new TokenRefreshManager();
        }
        return this.instance;
    }
    
    async getValidToken(): Promise<string> {
        if (this.refreshPromise) {
            return this.refreshPromise;
        }
        
        const currentToken = TokenManager.getAccessToken();
        if (currentToken && !TokenLifecycleManager.isTokenExpiringSoon(currentToken)) {
            return currentToken;
        }
        
        this.refreshPromise = this.performRefresh();
        try {
            const newToken = await this.refreshPromise;
            return newToken;
        } finally {
            this.refreshPromise = null;
        }
    }
    
    private async performRefresh(): Promise<string> {
        // 실제 갱신 로직
        return RefreshTokenService.refreshToken();
    }
}
```

## 📊 모니터링 및 로깅

### 1. 클라이언트 로깅

#### ✅ 권장사항:
```javascript
class TokenLogger {
    static logTokenEvent(event: string, details?: any) {
        // 프로덕션에서는 토큰 값을 로그에 포함하지 않음
        const logData = {
            timestamp: new Date().toISOString(),
            event,
            details: details ? JSON.stringify(details) : undefined,
            userAgent: navigator.userAgent,
            url: window.location.href
        };
        
        // 보안 이벤트 로깅 서비스로 전송
        this.sendToSecurityLogger(logData);
    }
    
    private static sendToSecurityLogger(data: any) {
        // MAX Platform 보안 이벤트 API로 전송
        fetch('/api/security/events', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                events: [{
                    eventId: `token_${Date.now()}_${Math.random()}`,
                    timestamp: new Date().toISOString(),
                    eventType: 'token_management',
                    severity: 'low',
                    details: data
                }]
            })
        }).catch(console.error);
    }
}

// 사용 예시
TokenLogger.logTokenEvent('refresh_attempted');
TokenLogger.logTokenEvent('refresh_failed', { reason: error.message });
```

## 🚀 성능 최적화

### 1. 토큰 캐싱

#### ✅ 권장사항:
```javascript
class TokenCache {
    private static cache = new Map<string, { token: string; expiry: number }>();
    
    static setToken(key: string, token: string, expiryMs: number) {
        this.cache.set(key, {
            token,
            expiry: Date.now() + expiryMs
        });
    }
    
    static getToken(key: string): string | null {
        const cached = this.cache.get(key);
        if (cached && Date.now() < cached.expiry) {
            return cached.token;
        }
        
        this.cache.delete(key);
        return null;
    }
}
```

### 2. 배치 요청 처리

#### ✅ 권장사항:
```javascript
class BatchRequestManager {
    private static pendingRequests: Array<{
        resolve: (token: string) => void;
        reject: (error: any) => void;
    }> = [];
    
    static async getToken(): Promise<string> {
        return new Promise((resolve, reject) => {
            this.pendingRequests.push({ resolve, reject });
            
            if (this.pendingRequests.length === 1) {
                // 첫 번째 요청만 실제 갱신 수행
                this.processTokenRefresh();
            }
        });
    }
    
    private static async processTokenRefresh() {
        try {
            const newToken = await RefreshTokenService.refreshToken();
            
            // 모든 대기 중인 요청에게 토큰 제공
            this.pendingRequests.forEach(({ resolve }) => resolve(newToken));
        } catch (error) {
            // 모든 대기 중인 요청에게 오류 전파
            this.pendingRequests.forEach(({ reject }) => reject(error));
        } finally {
            this.pendingRequests = [];
        }
    }
}
```

## 📖 추가 리소스

- [OAuth 2.0 RFC 6749](https://tools.ietf.org/html/rfc6749)
- [OAuth 2.0 Security Best Practices](https://tools.ietf.org/html/draft-ietf-oauth-security-topics)
- [PKCE RFC 7636](https://tools.ietf.org/html/rfc7636)
- [MAX Platform OAuth 2.0 Developer Guide](./oauth2-developer-guide.md)

---

## 📞 지원

문제가 발생하거나 추가 지원이 필요한 경우:
1. GitHub Issues: [MAX Platform Issues](https://github.com/your-org/maxplatform/issues)
2. 개발자 문서: [Developer Portal](https://dev.maxplatform.com)
3. 기술 지원: dev-support@maxplatform.com