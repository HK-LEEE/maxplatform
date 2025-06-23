# Central Authentication System

독립적인 중앙 집중형 인증 시스템으로, OAuth 2.0 및 JWT 기반의 보안 인증을 제공합니다.

## 시스템 구성

### 1. 인증 서버 (Auth Server) - Port 8001
- **기술 스택**: Python FastAPI
- **역할**: JWT 토큰 발급, 사용자 인증, 토큰 갱신
- **주요 기능**:
  - 로그인/로그아웃
  - JWT Access Token 및 Refresh Token 발급
  - 토큰 갱신 (Refresh Token Rotation)
  - JWKS 엔드포인트 제공
  - Rate Limiting 및 보안 미들웨어

### 2. 백엔드 API 서버 (Resource Server) - Port 8000
- **기술 스택**: Python FastAPI
- **역할**: 보호된 리소스 제공, JWT 토큰 검증
- **주요 기능**:
  - JWT 토큰 검증 (JWKS 기반)
  - 보호된 API 엔드포인트
  - 권한 기반 접근 제어 (그룹/부서별)

### 3. 클라이언트 (Client) - Port 3000
- **기술 스택**: Node.js Express
- **역할**: 웹 인터페이스, API 프록시
- **주요 기능**:
  - 로그인 폼 및 대시보드
  - 자동 토큰 갱신 (Axios 인터셉터)
  - API 요청 프록시

### 4. 데이터베이스
- **기술 스택**: PostgreSQL
- **포함 내용**: 사용자 정보, Refresh Token 저장
- **마이그레이션**: MySQL에서 PostgreSQL로 자동 마이그레이션

## 필수 요구사항

### 소프트웨어
- Python 3.8+
- Node.js 16+
- PostgreSQL 12+
- Redis (선택사항, 캐싱용)

### Python 패키지
```bash
pip install fastapi uvicorn python-jose[cryptography] passlib[bcrypt] psycopg2-binary sqlalchemy python-dotenv
```

### Node.js 패키지
```bash
npm install express axios cookie-parser cors dotenv express-session helmet morgan
```

## 설치 및 실행 가이드

### 1. 빠른 시작 (권장)

```bash
# 모든 서비스 한 번에 시작
start_all_services.bat
```

### 2. 개별 서비스 시작

#### 데이터베이스 설정
```bash
# PostgreSQL 데이터베이스 생성
createdb -U postgres auth_system

# 스키마 생성 및 데이터 마이그레이션
setup_database.bat
```

#### 인증 서버 시작
```bash
start_auth_server.bat
```

#### 백엔드 API 서버 시작
```bash
start_backend_api.bat
```

#### 클라이언트 시작
```bash
start_client.bat
```

## 환경 설정

### 인증 서버 (.env)
```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/auth_system
JWT_ALGORITHM=RS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
HOST=0.0.0.0
PORT=8001
```

### 백엔드 API 서버 (.env)
```env
AUTH_SERVER_URL=http://localhost:8001
JWKS_URL=http://localhost:8001/auth/.well-known/jwks.json
HOST=0.0.0.0
PORT=8000
```

### 클라이언트 (.env)
```env
AUTH_SERVER_URL=http://localhost:8001
BACKEND_API_URL=http://localhost:8000
PORT=3000
SESSION_SECRET=your-secret-key
```

## API 엔드포인트

### 인증 서버 (Port 8001)
- `POST /auth/login` - 사용자 로그인
- `POST /auth/refresh` - 토큰 갱신
- `POST /auth/logout` - 로그아웃
- `GET /auth/.well-known/jwks.json` - JWKS 공개 키
- `GET /auth/health` - 헬스 체크

### 백엔드 API 서버 (Port 8000)
- `GET /api/protected-data` - 보호된 데이터 (인증 필요)
- `GET /api/user-profile` - 사용자 프로필
- `GET /api/admin-only` - 관리자 전용 (admin 그룹 필요)
- `GET /api/it-department` - IT 부서 전용 (IT 부서 필요)

### 클라이언트 (Port 3000)
- `GET /` - 홈페이지 (자동 리다이렉트)
- `GET /login` - 로그인 페이지
- `GET /dashboard` - 대시보드 (인증 필요)

## 보안 기능

### JWT 토큰 관리
- **Access Token**: 15분 만료, Bearer 토큰으로 전송
- **Refresh Token**: 7일 만료, HttpOnly 쿠키로 저장
- **토큰 순환**: Refresh Token Rotation 구현
- **비대칭 암호화**: RS256 알고리즘 사용

### 보안 미들웨어
- **Rate Limiting**: 로그인 시도 제한
- **CORS**: 적절한 Origin 설정
- **Helmet**: 보안 헤더 설정
- **Session 보안**: HttpOnly, Secure 쿠키

### 권한 관리
- **그룹 기반**: admin, user 그룹 지원
- **부서 기반**: IT, HR, Finance 등 부서별 접근 제어

## 테스트 계정

기본 테스트 계정이 설정되어 있습니다:

| 사용자명 | 비밀번호 | 그룹 | 부서 |
|---------|---------|------|------|
| admin | password | admin | IT |
| user1 | password | user | HR |
| user2 | password | user | Finance |

## 아키텍처 다이어그램

```
[클라이언트 :3000] 
       ↓
[인증 서버 :8001] ←→ [PostgreSQL]
       ↓ (JWT)
[백엔드 API :8000]
```

## 주요 특징

1. **토큰 기반 인증**: JWT Access/Refresh Token 사용
2. **자동 토큰 갱신**: 클라이언트에서 자동 처리
3. **JWKS 기반 검증**: 공개 키로 토큰 서명 검증
4. **마이크로서비스 아키텍처**: 독립적인 서비스 분리
5. **보안 모범 사례**: Rate limiting, CORS, 보안 헤더 적용

## 문제 해결

### 포트 충돌
다른 서비스가 포트를 사용 중인 경우 .env 파일에서 포트 변경

### 데이터베이스 연결 오류
PostgreSQL 서비스 실행 상태 확인 및 연결 정보 검증

### JWT 검증 실패
JWKS 엔드포인트 접근 가능 여부 확인

### 토큰 갱신 실패
Refresh Token 쿠키 설정 및 만료 시간 확인

## 개발 모드

개발 중에는 다음 URL에서 API 문서를 확인할 수 있습니다:
- 인증 서버: http://localhost:8001/docs
- 백엔드 API: http://localhost:8000/docs

## 프로덕션 배포

프로덕션 환경에서는 다음 사항을 확인하세요:

1. **환경 변수**: 실제 암호 및 비밀 키 설정
2. **HTTPS**: SSL/TLS 인증서 적용
3. **보안 쿠키**: Secure 플래그 활성화
4. **방화벽**: 필요한 포트만 개방
5. **로깅**: 적절한 로그 레벨 설정
6. **백업**: 데이터베이스 정기 백업

## 라이선스

MIT License

## 지원

문제가 발생하거나 질문이 있으시면 개발팀에 문의하세요. 