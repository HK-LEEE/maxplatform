# MySQL에서 PostgreSQL로 마이그레이션 및 JWT 인증 업그레이드 가이드

## 개요

이 가이드는 기존 MySQL 기반 백엔드를 PostgreSQL로 마이그레이션하고, JWT 인증을 Access Token + Refresh Token 방식으로 업그레이드하는 과정을 설명합니다.

## 주요 변경사항

### 1. 데이터베이스 변경
- **MySQL → PostgreSQL**
- **pymysql → psycopg2-binary**
- **MySQL 특화 타입 → PostgreSQL 호환 타입**

### 2. JWT 인증 업그레이드
- **기존**: Access Token만 사용
- **새로운**: Access Token + Refresh Token 사용
- **보안 강화**: 토큰 무효화, 기기별 관리

### 3. 모델 변경사항
- `CHAR(36)` → `String(36)` (PostgreSQL 호환)
- 새로운 `RefreshToken` 모델 추가
- User 모델에 refresh token 관계 추가

## PostgreSQL 설치 및 설정

### Docker를 사용한 설치 (추천)

```bash
# PostgreSQL 컨테이너 실행
docker run -d \
  --name platform-integration-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=2300 \
  -e POSTGRES_DB=platform_integration \
  -p 5432:5432 \
  postgres:15

# 데이터베이스 연결 확인
docker exec -it platform-integration-postgres psql -U postgres -d platform_integration
```

### 로컬 설치

1. **PostgreSQL 공식 사이트에서 다운로드**
   - https://www.postgresql.org/download/

2. **데이터베이스 생성**
   ```sql
   CREATE DATABASE platform_integration;
   -- postgres 사용자는 기본적으로 존재하므로 추가 사용자 생성은 선택사항
   -- CREATE USER postgres WITH ENCRYPTED PASSWORD '2300';
   -- GRANT ALL PRIVILEGES ON DATABASE platform_integration TO postgres;
   ```

## 마이그레이션 단계

### 1. 의존성 업데이트

```bash
cd backend
pip install psycopg2-binary==2.9.9
# pip uninstall pymysql pyodbc  # 기존 MySQL 드라이버 제거 (선택사항)
```

### 2. 환경 설정 업데이트

기존 `.env` 파일을 백업하고 새로운 설정으로 변경:

```bash
# 백업
cp .env .env.mysql.backup

# PostgreSQL 설정으로 변경
cp .env.postgresql .env
```

### 3. 데이터베이스 스키마 생성

```bash
cd backend
python -c "
from app.database import create_tables
create_tables()
print('✅ PostgreSQL 테이블 생성 완료')
"
```

### 4. 데이터 마이그레이션 (선택사항)

기존 MySQL 데이터를 PostgreSQL로 마이그레이션하려면:

```bash
# 1. MySQL에서 데이터 백업
mysqldump -u root -p jupyter_platform > backup_mysql.sql

# 2. PostgreSQL로 데이터 변환 및 임포트
# (수동으로 스키마 차이점 조정 필요)
```

## JWT 인증 업그레이드 사용법

### 1. 새로운 로그인 응답 형태

**기존**:
```json
{
  "access_token": "...",
  "token_type": "bearer",
  "user": {...}
}
```

**새로운**:
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {...}
}
```

### 2. 새로운 엔드포인트

#### Refresh Token으로 Access Token 갱신
```bash
POST /api/auth/refresh
Content-Type: application/json

{
  "refresh_token": "your-refresh-token"
}
```

응답:
```json
{
  "access_token": "new-access-token",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### 로그아웃 (토큰 무효화)
```bash
POST /api/auth/logout
Authorization: Bearer your-access-token

# 선택적으로 refresh_token도 전달 가능
{
  "refresh_token": "your-refresh-token"
}
```

#### 모든 기기의 토큰 무효화
```bash
POST /api/auth/revoke-all-tokens
Authorization: Bearer your-access-token
```

### 3. 클라이언트 측 구현 예제

```javascript
// 토큰 저장
const loginResponse = await login(email, password);
localStorage.setItem('access_token', loginResponse.access_token);
localStorage.setItem('refresh_token', loginResponse.refresh_token);

// Access Token 만료 시 자동 갱신
async function refreshAccessToken() {
  const refreshToken = localStorage.getItem('refresh_token');
  const response = await fetch('/api/auth/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken })
  });
  
  if (response.ok) {
    const data = await response.json();
    localStorage.setItem('access_token', data.access_token);
    return data.access_token;
  } else {
    // Refresh Token도 만료된 경우 재로그인 필요
    redirectToLogin();
  }
}

// API 요청 인터셉터 예제
async function apiRequest(url, options = {}) {
  let token = localStorage.getItem('access_token');
  
  let response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${token}`
    }
  });
  
  // 401 에러 시 토큰 갱신 시도
  if (response.status === 401) {
    token = await refreshAccessToken();
    response = await fetch(url, {
      ...options,
      headers: {
        ...options.headers,
        'Authorization': `Bearer ${token}`
      }
    });
  }
  
  return response;
}
```

## 보안 강화 기능

### 1. 기기별 토큰 관리
- 각 로그인 세션마다 별도의 Refresh Token 발급
- 기기 정보, IP 주소, User Agent 기록
- 의심스러운 활동 추적 가능

### 2. 토큰 무효화
- 개별 토큰 무효화
- 모든 기기의 토큰 일괄 무효화
- 로그아웃 시 자동 토큰 무효화

### 3. 토큰 생명주기 관리
- Access Token: 30분 (기본값)
- Refresh Token: 7일 (기본값)
- 환경변수로 조정 가능

## 테스트

### 1. 데이터베이스 연결 테스트
```bash
cd backend
python -c "
from app.database import test_connection
if test_connection():
    print('✅ PostgreSQL 연결 성공')
else:
    print('❌ PostgreSQL 연결 실패')
"
```

### 2. 인증 테스트
```bash
# 회원가입
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "real_name": "테스트 사용자",
    "email": "test@example.com",
    "phone_number": "010-1234-5678",
    "password": "testpassword123"
  }'

# 로그인
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123"
  }'

# 토큰 갱신
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "your-refresh-token-here"
  }'
```

## 문제 해결

### 1. PostgreSQL 연결 실패
```bash
# 서비스 상태 확인
sudo systemctl status postgresql  # Linux
brew services list postgresql    # macOS

# 포트 확인
netstat -an | grep 5432
```

### 2. 모듈 임포트 에러
```bash
# 가상환경 활성화 확인
source venv/bin/activate  # Linux/macOS
# 또는
venv\Scripts\activate     # Windows

# 의존성 재설치
pip install -r requirements.txt
```

### 3. 마이그레이션 에러
```bash
# 테이블 초기화 (주의: 기존 데이터 삭제됨)
python -c "
from app.database import engine, Base
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
print('✅ 테이블 재생성 완료')
"
```

## 환경별 설정

### 개발 환경
```bash
# .env
DEBUG=True
DATABASE_URL=postgresql://postgres:2300@localhost:5432/platform_integration_dev
```

### 프로덕션 환경
```bash
# .env
DEBUG=False
SECRET_KEY=your-strong-secret-key-change-this
DATABASE_URL=postgresql://postgres:2300@host:5432/platform_integration
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30
```

## 성능 최적화

### 1. 데이터베이스 인덱스
```sql
-- 자주 조회되는 컬럼에 인덱스 추가
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_token ON refresh_tokens(token);
```

### 2. 연결 풀 설정
```python
# config.py에서 조정
engine = create_engine(
    database_url,
    pool_size=20,
    max_overflow=30,
    pool_recycle=3600
)
```

## 마이그레이션 완료 확인

✅ PostgreSQL 설치 및 연결 확인  
✅ 의존성 업데이트 완료  
✅ 환경 설정 변경 완료  
✅ 데이터베이스 스키마 생성 완료  
✅ JWT 인증 테스트 완료  
✅ 새로운 API 엔드포인트 테스트 완료  

모든 단계가 완료되면 MySQL에서 PostgreSQL로의 마이그레이션과 JWT 인증 업그레이드가 성공적으로 완료됩니다. 