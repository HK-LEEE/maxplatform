# 문제 해결 가이드 (Troubleshooting)

## 의존성 충돌 문제

### SQLAlchemy 버전 충돌 해결

**문제**: `databases 0.8.0 requires sqlalchemy<1.5,>=1.4.42, but you have sqlalchemy 2.0.23`

**원인**: 
- `databases` 패키지가 SQLAlchemy 1.x 버전만 지원
- 본 프로젝트는 SQLAlchemy 2.0을 사용

**해결 방법**:

### 1. 깨끗한 재설치 (권장)

```bash
# 깨끗한 설치 스크립트 실행
clean_install.bat
```

### 2. 수동 해결

```bash
cd backend

# 기존 가상환경 삭제
rmdir /s /q venv

# 새 가상환경 생성
python -m venv venv
venv\Scripts\activate

# pip 업그레이드
python -m pip install --upgrade pip

# 문제가 되는 패키지 제거
pip uninstall -y databases

# 의존성 재설치
pip install -r requirements.txt
```

### 3. 개별 패키지 수동 설치

```bash
pip install fastapi==0.105.0
pip install sqlalchemy==2.0.23
pip install uvicorn[standard]==0.24.0
# ... 나머지 패키지들
```

## 기타 일반적인 문제

### 1. Python PATH 문제

**문제**: `jupyter-lab.exe`가 PATH에 없다는 경고

**해결 방법**:
```bash
# Windows에서 Python Scripts 폴더를 PATH에 추가
# 또는 가상환경 사용 (권장)
venv\Scripts\activate
```

### 2. MySQL 연결 문제

**문제**: 데이터베이스 연결 실패

**해결 방법**:
1. MySQL 서비스 시작 확인
2. `.env` 파일의 데이터베이스 정보 확인
3. 사용자 권한 확인

```sql
-- MySQL에서 사용자 생성 및 권한 부여
CREATE USER 'test'@'localhost' IDENTIFIED BY 'test';
GRANT ALL PRIVILEGES ON jupyter_platform.* TO 'test'@'localhost';
FLUSH PRIVILEGES;
```

### 3. 포트 충돌 문제

**문제**: 포트 8000 또는 3000이 이미 사용 중

**해결 방법**:

백엔드 포트 변경:
```bash
# .env 파일에서
PORT=8001
```

프론트엔드 포트 변경:
```bash
# vite.config.ts에서
server: { port: 3001 }
```

### 4. Jupyter Lab 시작 실패

**문제**: Jupyter Lab 인스턴스 시작 불가

**해결 방법**:
1. 가상환경에서 Jupyter Lab 설치 확인
2. 포트 범위 확인 (8888-9000)
3. 권한 문제 확인

```bash
# 수동 테스트
venv\Scripts\activate
jupyter lab --version
jupyter lab --port 8888 --no-browser
```

### 5. React/TypeScript 컴파일 오류

**문제**: 프론트엔드 TypeScript 에러

**해결 방법**:
```bash
cd frontend

# 의존성 재설치
rm -rf node_modules package-lock.json
npm install

# 타입 체크
npm run type-check
```

## 환경별 설정

### 개발 환경
```bash
# backend/.env
DEBUG=True
DATABASE_URL=mysql://test:test@localhost/jupyter_platform

# 개발 서버 실행
uvicorn app.main:app --reload
```

### 프로덕션 환경
```bash
# backend/.env
DEBUG=False
SECRET_KEY=your-strong-secret-key-here
DATABASE_URL=mysql://prod_user:prod_password@prod_host/jupyter_platform

# 프로덕션 서버 실행
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 로그 확인

### 백엔드 로그
```bash
# FastAPI 로그는 콘솔에 출력됨
# 파일로 저장하려면:
uvicorn app.main:app --log-file backend.log
```

### Jupyter Lab 로그
```bash
# 각 Jupyter 인스턴스의 로그는 프로세스 출력에서 확인
# 또는 Jupyter Lab 인터페이스에서 확인
```

## 성능 최적화

### 1. MySQL 설정
```sql
-- my.cnf 또는 my.ini에서
[mysqld]
innodb_buffer_pool_size = 256M
max_connections = 100
```

### 2. 파일 시스템 권한
```bash
# 데이터 폴더 권한 설정 (Windows)
icacls data\users /grant Everyone:(OI)(CI)F
```

### 3. 리소스 모니터링
```bash
# 시스템 리소스 확인
psutil을 사용한 모니터링 (코드에 포함됨)
```

## 지원 및 도움

문제가 지속되면 다음을 확인하세요:

1. Python 버전: 3.8 이상
2. Node.js 버전: 16 이상
3. MySQL 버전: 8.0 이상
4. 시스템 메모리: 최소 4GB 권장

## 업데이트 가이드

패키지 업데이트 시:
1. 항상 가상환경 사용
2. requirements.txt 백업
3. 단계별 테스트 수행 