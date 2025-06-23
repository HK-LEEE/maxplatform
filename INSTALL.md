# Jupyter Data Platform 설치 가이드

## 시스템 요구사항

- **운영체제**: Windows 10/11
- **Python**: 3.8 이상
- **Node.js**: 16 이상
- **MySQL**: 8.0 이상

## 설치 단계

### 1. 저장소 클론

```bash
git clone <repository-url>
cd jupyter-data-platform
```

### 2. MySQL 데이터베이스 설정

1. MySQL 서버 설치 및 실행
2. MySQL 클라이언트에서 다음 명령 실행:

```sql
mysql -u root -p < setup_database.sql
```

또는 MySQL Workbench에서 `setup_database.sql` 파일을 실행합니다.

### 3. 환경 변수 설정

`backend/.env` 파일을 편집하여 데이터베이스 연결 정보를 수정합니다:

```env
DATABASE_URL=mysql://root:your_password@localhost/jupyter_platform
SECRET_KEY=your-secret-key-here
```

### 4. 백엔드 실행

```bash
# 방법 1: 배치 파일 사용 (권장)
start_backend.bat

# 방법 2: 수동 실행
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. 프론트엔드 실행

새 터미널에서:

```bash
# 방법 1: 배치 파일 사용 (권장)
start_frontend.bat

# 방법 2: 수동 실행
cd frontend
npm install
npm start
```

## 접속 정보

- **프론트엔드**: http://localhost:3000
- **백엔드 API**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs

## 첫 사용자 생성

1. 브라우저에서 http://localhost:3000 접속
2. "회원가입" 클릭
3. 사용자 정보 입력 후 계정 생성
4. 로그인 후 워크스페이스 생성

## 문제 해결

### 포트 충돌
- 백엔드 포트 8000이 사용 중인 경우: `backend/.env`에서 `PORT` 변경
- 프론트엔드 포트 3000이 사용 중인 경우: `frontend/vite.config.ts`에서 포트 변경

### 데이터베이스 연결 오류
- MySQL 서비스가 실행 중인지 확인
- `backend/.env`의 데이터베이스 연결 정보 확인
- 방화벽 설정 확인

### Jupyter Lab 시작 오류
- Python 가상환경이 활성화되어 있는지 확인
- Jupyter Lab이 설치되어 있는지 확인: `pip install jupyterlab`
- 포트 범위 8888-9000이 사용 가능한지 확인

## 개발 모드

개발 시 다음과 같이 실행하세요:

```bash
# 백엔드 (자동 재시작)
cd backend
uvicorn app.main:app --reload

# 프론트엔드 (자동 재시작)
cd frontend
npm run dev
```

## 프로덕션 배포

프로덕션 환경에서는:

1. `backend/.env`에서 `DEBUG=False` 설정
2. 강력한 `SECRET_KEY` 생성
 