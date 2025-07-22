# MAX Platform 배포 가이드

Production 환경 배포를 위한 종합 가이드입니다.

## 목차
1. [환경 변수 설정](#환경-변수-설정)
2. [개발 환경 설정](#개발-환경-설정)
3. [Production 환경 설정](#production-환경-설정)
4. [Docker 배포](#docker-배포)
5. [트러블슈팅](#트러블슈팅)

## 환경 변수 설정

### 📂 환경 파일 구조
```
maxplatform/
├── .env.development        # 개발 환경용
├── .env.production        # 운영 환경용
├── frontend/
│   └── .env.example       # Frontend 환경 변수 예시
└── backend/
    └── .env.example       # Backend 환경 변수 예시
```

### 🔧 기본 설정 단계

#### 1. 개발 환경 설정
```bash
# 프로젝트 루트에서
cp .env.development .env

# Frontend 설정
cd frontend
cp .env.example .env

# Backend 설정  
cd ../backend
cp .env.example .env
```

#### 2. Production 환경 설정
```bash
# 프로젝트 루트에서
cp .env.production .env

# 환경 변수 수정
nano .env
```

## 개발 환경 설정

### Frontend (React)
개발 환경에서는 기본 설정을 그대로 사용할 수 있습니다.

**환경 변수 확인:**
```bash
cd frontend
cat .env
```

**주요 설정:**
- `REACT_APP_API_BASE_URL=http://localhost:8000`
- `REACT_APP_FRONTEND_URL=http://localhost:3000`
- `REACT_APP_DEBUG_MODE=true`

### Backend (FastAPI)
```bash
cd backend
# 환경 변수 로드 확인
python -c "from app.config import settings; print(f'API URL: {settings.max_platform_api_url}')"
```

### 개발 서버 실행
```bash
# Backend 실행
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend 실행 (별도 터미널)
cd frontend
npm start
```

## Production 환경 설정

### 🌐 도메인 및 URL 설정
Production 배포 시 다음 URL들을 실제 도메인으로 변경해야 합니다:

**주요 서비스 도메인:**
```bash
# API 서버
MAX_PLATFORM_API_URL=https://api.maxplatform.com

# Frontend 
MAX_PLATFORM_FRONTEND_URL=https://platform.maxplatform.com

# 각 서비스별 도메인
MAX_FLOWSTUDIO_URL=https://flowstudio.maxplatform.com
MAX_TEAMSYNC_URL=https://teamsync.maxplatform.com
MAX_LAB_URL=https://lab.maxplatform.com
MAX_WORKSPACE_URL=https://workspace.maxplatform.com
MAX_APA_URL=https://apa.maxplatform.com
MAX_MLOPS_URL=https://mlops.maxplatform.com
MAX_QUERYHUB_URL=https://queryhub.maxplatform.com
MAX_LLM_URL=https://llm.maxplatform.com
```

### 🔒 보안 설정

#### 1. JWT 시크릿 키 변경
```bash
# 강력한 시크릿 키 생성
SECRET_KEY=$(openssl rand -hex 32)
echo "SECRET_KEY=${SECRET_KEY}" >> .env
```

#### 2. 데이터베이스 보안
```bash
# Production 데이터베이스 URL
DATABASE_URL=postgresql://username:strong_password@db.maxplatform.com:5432/platform_production
```

#### 3. CORS 설정
```bash
# 허용할 Origin 설정
CORS_ORIGINS=https://platform.maxplatform.com,https://flowstudio.maxplatform.com,https://teamsync.maxplatform.com
```

### 🚀 환경별 배포 스크립트

#### Development 배포
```bash
#!/bin/bash
# deploy-dev.sh

echo "🔧 Development 환경 배포 시작..."

# 환경 변수 설정
export NODE_ENV=development
cp .env.development .env

# Frontend 빌드 및 실행
cd frontend
npm install
npm run build
npm start &

# Backend 실행
cd ../backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &

echo "✅ Development 환경 배포 완료"
echo "🌐 Frontend: http://localhost:3000"
echo "🌐 Backend: http://localhost:8000"
```

#### Production 배포
```bash
#!/bin/bash
# deploy-prod.sh

echo "🚀 Production 환경 배포 시작..."

# 환경 변수 설정
export NODE_ENV=production
cp .env.production .env

# Frontend 빌드
cd frontend
npm install --production
npm run build

# Backend 설정
cd ../backend
pip install -r requirements.txt

# SSL 인증서 확인
if [ ! -f "/etc/ssl/certs/maxplatform.crt" ]; then
    echo "❌ SSL 인증서가 없습니다. SSL 설정을 확인하세요."
    exit 1
fi

# Production 서버 실행 (Gunicorn 사용)
gunicorn app.main:app \
    --bind 0.0.0.0:443 \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --certfile /etc/ssl/certs/maxplatform.crt \
    --keyfile /etc/ssl/private/maxplatform.key

echo "✅ Production 환경 배포 완료"
```

## Docker 배포

### 🐳 Docker Compose 설정

#### docker-compose.yml
```yaml
version: '3.8'
services:
  # Frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_BASE_URL=${MAX_PLATFORM_API_URL}
      - REACT_APP_FRONTEND_URL=${MAX_PLATFORM_FRONTEND_URL}
    env_file:
      - .env

  # Backend
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - SECRET_KEY=${SECRET_KEY}
      - MAX_PLATFORM_API_URL=${MAX_PLATFORM_API_URL}
    env_file:
      - .env
    depends_on:
      - postgres

  # Database
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=platform_production
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/schema.sql:/docker-entrypoint-initdb.d/01-schema.sql
      - ./database/oauth_schema.sql:/docker-entrypoint-initdb.d/02-oauth.sql
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

#### Frontend Dockerfile
```dockerfile
# frontend/Dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# 환경별 빌드
ARG NODE_ENV=production
ENV NODE_ENV=${NODE_ENV}

RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
```

#### Backend Dockerfile
```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker 배포 명령어
```bash
# 개발 환경
docker-compose --env-file .env.development up -d

# Production 환경
docker-compose --env-file .env.production up -d

# 로그 확인
docker-compose logs -f

# 컨테이너 중지
docker-compose down
```

## 환경 변수 관리 팁

### 1. 환경별 설정 분리
```bash
# 환경 확인 스크립트
check-env.sh:
#!/bin/bash
if [ "$MAX_PLATFORM_ENVIRONMENT" = "production" ]; then
    echo "🚀 Production 환경"
    # Production 체크리스트
    [ -z "$SECRET_KEY" ] && echo "❌ SECRET_KEY 미설정" || echo "✅ SECRET_KEY 설정됨"
    [ "$REACT_APP_DEBUG_MODE" = "true" ] && echo "⚠️ 디버그 모드 활성화됨" || echo "✅ 디버그 모드 비활성화"
else
    echo "🔧 Development 환경"
fi
```

### 2. 민감한 정보 관리
```bash
# .env 파일을 .gitignore에 추가
echo ".env" >> .gitignore
echo ".env.local" >> .gitignore

# 환경 변수 검증
python -c "
from app.config import settings
import sys

required_vars = ['SECRET_KEY', 'DATABASE_URL']
missing = [var for var in required_vars if not getattr(settings, var.lower(), None)]

if missing:
    print(f'❌ 필수 환경 변수 누락: {missing}')
    sys.exit(1)
else:
    print('✅ 모든 필수 환경 변수 설정됨')
"
```

## OAuth 클라이언트 업데이트

Production 배포 시 OAuth 클라이언트 정보를 업데이트해야 합니다:

```sql
-- database/update_oauth_clients_production.sql
UPDATE oauth_clients SET 
    redirect_uris = ARRAY['https://flowstudio.maxplatform.com/oauth/callback'],
    homepage_url = 'https://flowstudio.maxplatform.com'
WHERE client_id = 'maxflowstudio';

UPDATE oauth_clients SET 
    redirect_uris = ARRAY['https://teamsync.maxplatform.com/oauth/callback'],
    homepage_url = 'https://teamsync.maxplatform.com'
WHERE client_id = 'maxteamsync';

-- 다른 클라이언트들도 동일하게 업데이트...
```

## 트러블슈팅

### 자주 발생하는 문제들

#### 1. CORS 오류
```
Access to fetch at 'https://api.maxplatform.com' from origin 'https://platform.maxplatform.com' has been blocked by CORS policy
```

**해결 방법:**
```python
# backend/app/main.py에서 CORS 설정 확인
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### 2. 환경 변수 미로드
```
KeyError: 'REACT_APP_API_BASE_URL'
```

**해결 방법:**
```bash
# 환경 변수 로드 확인
printenv | grep REACT_APP

# .env 파일 권한 확인
chmod 644 .env

# Frontend 재시작
npm restart
```

#### 3. OAuth 리다이렉트 오류
```
Invalid redirect_uri
```

**해결 방법:**
```sql
-- 데이터베이스에서 클라이언트 정보 확인
SELECT client_id, redirect_uris FROM oauth_clients WHERE client_id = 'maxlab';

-- 필요 시 업데이트
UPDATE oauth_clients SET 
    redirect_uris = ARRAY['https://lab.maxplatform.com/oauth/callback']
WHERE client_id = 'maxlab';
```

### 로그 확인 방법

#### 1. Backend 로그
```bash
# 애플리케이션 로그
tail -f /var/log/maxplatform/app.log

# Uvicorn 로그
journalctl -u maxplatform-backend -f
```

#### 2. Frontend 로그
```bash
# 브라우저 콘솔 확인
# 개발자 도구 > Console

# Nginx 로그 (프록시 사용 시)
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

## 성능 최적화

### 1. Frontend 최적화
```bash
# 빌드 크기 분석
npm run build -- --analyze

# 환경별 최적화
NODE_ENV=production npm run build
```

### 2. Backend 최적화
```python
# Gunicorn 설정 최적화
# gunicorn.conf.py
bind = "0.0.0.0:8000"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
```

### 3. 데이터베이스 최적화
```sql
-- 인덱스 확인
SELECT indexname, tablename FROM pg_indexes WHERE schemaname = 'public';

-- 성능 모니터링
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;
```

## 모니터링 설정

### 헬스체크 엔드포인트
```python
# backend/app/main.py
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.max_platform_environment,
        "timestamp": datetime.utcnow().isoformat()
    }
```

### 외부 모니터링 도구 연동
```bash
# Prometheus 메트릭 수집
pip install prometheus-fastapi-instrumentator

# Grafana 대시보드 설정
# Health check URL: https://api.maxplatform.com/health
```

---

이 가이드를 통해 MAX Platform을 안전하고 효율적으로 Production 환경에 배포할 수 있습니다. 추가 질문이나 문제가 발생하면 개발팀에 문의하세요.