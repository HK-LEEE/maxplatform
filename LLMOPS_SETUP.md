# LLMOps Platform 설치 및 사용 가이드

## 개요
GenbaX 플랫폼에 통합된 Langflow 기반 LLMOps UI Platform입니다. 사용자가 시각적으로 LLM 워크플로우를 구성하고 실행할 수 있습니다.

## 주요 기능
- JWT 토큰 기반 인증 시스템
- 사용자별 Langflow 인스턴스 관리
- 시각적 LLM 워크플로우 구성
- 플로우 저장 및 관리
- 실시간 상태 모니터링

## 설치 방법

### 1. 백엔드 의존성 설치
```bash
cd backend
pip install -r requirements.txt
```

### 2. 프론트엔드 의존성 설치
```bash
cd frontend
npm install
```

### 3. 환경 설정
백엔드 `.env` 파일에 다음 설정 추가:
```env
# Langflow 설정
LANGFLOW_DATABASE_URL=sqlite:///data/langflow_workspaces/
LANGFLOW_CONFIG_DIR=data/langflow_workspaces/
LANGFLOW_LOG_LEVEL=INFO
```

## 사용 방법

### 1. 서버 시작
```bash
# 백엔드 시작
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 프론트엔드 시작 (새 터미널)
cd frontend
npm run dev
```

### 2. LLMOps 접근
1. 브라우저에서 `http://localhost:3000` 접속
2. 로그인 후 메인 페이지에서 🧪 LLMOps 버튼 클릭
3. 또는 직접 `http://localhost:3000/llmops` 접속

### 3. LLMOps 사용법
1. **인스턴스 시작**: "인스턴스 시작" 버튼 클릭
2. **워크플로우 구성**: Langflow UI에서 드래그 앤 드롭으로 LLM 파이프라인 구성
3. **플로우 실행**: 구성한 워크플로우 실행 및 테스트
4. **플로우 관리**: "플로우 목록 보기"에서 저장된 플로우 확인

## API 엔드포인트

### 인증이 필요한 엔드포인트
- `GET /api/llmops/health` - 서비스 상태 확인
- `GET /api/llmops/ui` - Langflow UI 임베딩 페이지
- `POST /api/llmops/start` - Langflow 인스턴스 시작
- `POST /api/llmops/stop` - Langflow 인스턴스 중지
- `GET /api/llmops/status` - 인스턴스 상태 확인
- `GET /api/llmops/flows` - 사용자 플로우 목록
- `POST /api/llmops/flows/export` - 플로우 내보내기

## 기술 스택
- **Backend**: FastAPI, Python
- **Frontend**: React, TypeScript, Tailwind CSS
- **LLMOps**: Langflow, LangChain
- **인증**: JWT Token
- **데이터베이스**: SQLite (Langflow 워크스페이스별)

## 포트 할당
- 메인 백엔드: 8000
- 프론트엔드: 3000
- Langflow 인스턴스: 7860 + (사용자 ID % 100)

## 디렉토리 구조
```
data/
└── langflow_workspaces/
    └── user_{user_id}/
        ├── langflow.db
        ├── flows/
        └── logs/
```

## 문제 해결

### Langflow 설치 오류
```bash
pip install langflow==1.0.12 --no-deps
pip install langflow-base==0.0.84
```

### 포트 충돌 해결
사용자별로 다른 포트를 자동 할당하므로 일반적으로 충돌이 발생하지 않습니다.
만약 충돌이 발생하면 `llmops.py`의 포트 계산 로직을 수정하세요.

### 권한 문제
```bash
# Windows에서 실행 권한 문제 시
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## 보안 고려사항
- JWT 토큰 검증을 통한 인증
- 사용자별 격리된 워크스페이스
- 프로세스 수준 격리
- 포트 기반 접근 제어

## 업데이트
```bash
# Langflow 업데이트
pip install --upgrade langflow

# 프론트엔드 의존성 업데이트
cd frontend
npm update
```

## 지원 및 문의
문제가 발생하거나 기능 요청이 있으시면 시스템 관리자에게 문의하세요. 