# MAX Platform SERVICE_TOKEN 사용 가이드

MAX Platform의 서비스 간 인증을 위한 OAuth 2.0 Client Credentials Grant 구현 가이드입니다.

## 📋 목차

1. [개요](#개요)
2. [주요 특징](#주요-특징)
3. [설정 방법](#설정-방법)
4. [사용 방법](#사용-방법)
5. [API 엔드포인트](#api-엔드포인트)
6. [보안 고려사항](#보안-고려사항)
7. [문제해결](#문제해결)

## 개요

SERVICE_TOKEN은 MAX Platform에서 서비스 간 안전한 통신을 위해 구현된 OAuth 2.0 Client Credentials Grant 기반의 인증 시스템입니다.

### 주요 용도
- **서비스 간 API 호출**: 백엔드 서비스들 간의 안전한 통신
- **관리자 API 접근**: 사용자 개입 없이 관리 작업 수행  
- **자동화 스크립트**: 배치 작업, 모니터링, 백업 등
- **마이크로서비스 통신**: 분산 환경에서의 서비스 인증

## 주요 특징

### ✅ OAuth 2.0 RFC 6749 준수
- Client Credentials Grant 완전 구현
- 표준 JWT 토큰 형식
- 스코프 기반 권한 제어

### 🔒 보안 강화
- 24시간 토큰 만료
- 클라이언트 시크릿 검증
- 스코프별 세밀한 권한 제어
- 감사 로그 자동 기록

### 🚀 자동화 지원
- 환경변수 기반 설정
- 토큰 자동 갱신
- 만료 전 자동 재발급

## 설정 방법

### 1. 환경변수 설정

`.env` 파일에 다음 설정을 추가합니다:

```bash
# 서비스 토큰 설정
SERVICE_TOKEN=                                    # 직접 토큰 지정 (선택사항)
SERVICE_CLIENT_ID=maxplatform-service             # 서비스 클라이언트 ID
SERVICE_CLIENT_SECRET=service_maxplatform_2025_dev_secret  # 클라이언트 시크릿
SERVICE_TOKEN_EXPIRE_HOURS=24                     # 토큰 만료 시간 (시간)

# OAuth 설정
SECRET_KEY=your-secret-key-here                   # JWT 서명 키
ALGORITHM=HS256                                   # JWT 알고리즘
```

### 2. 데이터베이스 설정

서비스 스코프를 데이터베이스에 추가합니다:

```bash
# OAuth 스키마 적용
psql -d platform_integration -f database/oauth_schema.sql

# 서비스 클라이언트 등록
psql -d platform_integration -f database/service_oauth_clients.sql
```

### 3. 서비스 클라이언트 확인

등록된 서비스 클라이언트를 확인합니다:

```sql
SELECT client_id, client_name, 
       CASE 
           WHEN array_length(redirect_uris, 1) IS NULL OR array_length(redirect_uris, 1) = 0 
           THEN '서비스 클라이언트' 
           ELSE '웹 클라이언트' 
       END as client_type,
       array_to_string(allowed_scopes, ', ') as allowed_scopes
FROM oauth_clients 
WHERE client_id LIKE '%service%';
```

## 사용 방법

### 1. 수동 토큰 발급

#### curl을 사용한 토큰 발급:

```bash
curl -X POST http://localhost:8000/api/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=maxplatform-service" \
  -d "client_secret=service_maxplatform_2025_dev_secret" \
  -d "scope=admin:oauth admin:users admin:system"
```

#### 응답 예시:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 86400,
  "scope": "admin:oauth admin:users admin:system"
}
```

### 2. Python에서 사용

#### 기본 사용법:

```python
import requests

# 토큰 발급
def get_service_token():
    token_url = "http://localhost:8000/api/oauth/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": "maxplatform-service", 
        "client_secret": "service_maxplatform_2025_dev_secret",
        "scope": "admin:oauth admin:users admin:system"
    }
    
    response = requests.post(token_url, data=data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"토큰 발급 실패: {response.text}")

# API 호출
def call_admin_api():
    token = get_service_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(
        "http://localhost:8000/api/admin/oauth/service/statistics",
        headers=headers
    )
    
    return response.json()
```

#### 자동 토큰 관리 사용:

```python
from backend.app.utils.service_token import (
    get_service_token, 
    create_service_request_headers,
    make_service_api_call
)

# 간편한 API 호출
def get_oauth_statistics():
    response = make_service_api_call(
        "GET", 
        "http://localhost:8000/api/admin/oauth/service/statistics"
    )
    return response.json()

# 토큰 정보 확인
def check_token_status():
    headers = create_service_request_headers()
    print(f"Current token: {headers['Authorization'][:50]}...")
```

### 3. 환경변수 직접 사용

환경변수에 SERVICE_TOKEN을 직접 설정하면 자동으로 사용됩니다:

```bash
export SERVICE_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# 이제 애플리케이션에서 자동으로 이 토큰을 사용
```

## API 엔드포인트

### OAuth 메타데이터
```
GET /api/oauth/.well-known/oauth-authorization-server
```

Client Credentials Grant 지원을 확인할 수 있습니다.

### 토큰 발급
```
POST /api/oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
client_id={CLIENT_ID}
client_secret={CLIENT_SECRET}
scope={REQUESTED_SCOPES}
```

### 서비스 전용 관리 API

#### OAuth 통계 조회
```
GET /api/admin/oauth/service/statistics
Authorization: Bearer {SERVICE_TOKEN}
```

#### OAuth 클라이언트 목록
```
GET /api/admin/oauth/service/clients
Authorization: Bearer {SERVICE_TOKEN}
```

#### 클라이언트 시크릿 재생성
```
POST /api/admin/oauth/service/clients/{client_id}/regenerate-secret
Authorization: Bearer {SERVICE_TOKEN}
```

## 스코프 권한

### 서비스 전용 스코프

| 스코프 | 설명 | 권한 |
|--------|------|------|
| `admin:oauth` | OAuth 관리 | 클라이언트, 토큰, 세션 관리 |
| `admin:users` | 사용자 관리 | 사용자 계정 및 권한 제어 |
| `admin:system` | 시스템 관리 | 시스템 설정 및 구성 관리 |
| `admin:full` | 전체 관리자 | 모든 관리 권한 |

### 일반 스코프

| 스코프 | 설명 |
|--------|------|
| `read:profile` | 사용자 프로필 읽기 |
| `read:features` | 기능 목록 읽기 |
| `read:groups` | 그룹 정보 읽기 |
| `manage:*` | 각종 리소스 관리 |

## 보안 고려사항

### 🔐 클라이언트 시크릿 보안
- 환경변수로만 관리
- 버전 관리에 포함하지 않음
- 주기적 교체 권장

### 🕐 토큰 만료 관리
- 24시간 자동 만료
- 만료 30분 전 자동 갱신
- 만료된 토큰 자동 정리

### 📋 감사 로그
모든 서비스 토큰 사용이 기록됩니다:

```sql
SELECT action, client_id, success, created_at 
FROM oauth_audit_logs 
WHERE client_id LIKE '%service%'
ORDER BY created_at DESC;
```

### 🎯 스코프 최소 권한
- 필요한 최소 스코프만 요청
- 스코프별 세밀한 접근 제어
- 권한 부족 시 403 에러

## 문제해결

### ❌ 토큰 발급 실패

**증상**: `invalid_client` 오류
```json
{"detail": "Invalid client_id"}
```

**해결방법**:
1. 클라이언트 ID 확인
2. 데이터베이스에 클라이언트 등록 확인
3. is_active 상태 확인

```sql
SELECT client_id, is_active, is_confidential 
FROM oauth_clients 
WHERE client_id = 'maxplatform-service';
```

### ❌ API 접근 실패

**증상**: `Could not validate service credentials`
```json
{"detail": "Could not validate service credentials"}
```

**해결방법**:
1. 토큰 형식 확인 (`Bearer {token}`)
2. 토큰 만료 확인
3. 스코프 권한 확인

### ❌ 스코프 부족

**증상**: `Missing required scopes`
```json
{"detail": "Missing required scopes: admin:oauth"}
```

**해결방법**:
1. 토큰 발급 시 필요한 스코프 포함
2. 클라이언트의 allowed_scopes 확인

```sql
SELECT client_id, allowed_scopes 
FROM oauth_clients 
WHERE client_id = 'maxplatform-service';
```

### 🔧 테스트 도구

프로젝트에 포함된 테스트 스크립트로 전체 기능을 검증할 수 있습니다:

```bash
# 전체 테스트 실행
python test_service_token.py

# 특정 서버 테스트
python test_service_token.py http://localhost:8000
```

테스트 항목:
- ✅ OAuth metadata 확인
- ✅ 서비스 토큰 발급
- ✅ 서비스 API 접근
- ✅ OAuth 클라이언트 조회
- ✅ 보안 검증
- ✅ 스코프 권한 확인

## 📞 지원

문제가 발생하면 다음을 확인하세요:

1. **로그 확인**: 애플리케이션 로그에서 상세한 오류 정보 확인
2. **데이터베이스 상태**: oauth_clients, oauth_audit_logs 테이블 확인  
3. **환경변수**: SERVICE_* 관련 설정 확인
4. **네트워크**: 서비스 간 통신 가능 여부 확인

MAX Platform의 SERVICE_TOKEN을 통해 안전하고 효율적인 서비스 간 통신을 구현하세요! 🚀