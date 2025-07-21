# Jupyter 기반 Python 데이터 분석 웹사이트 구현 완료

## 🎯 프로젝트 개요

Windows 환경에서 Jupyter Lab/Notebook 기능을 웹 기반으로 제공하여, 사용자별 독립적인 Python 개발 및 데이터 분석 환경을 구축하는 플랫폼을 성공적으로 구현했습니다.

## 🏗️ 구현된 시스템 아키텍처

### 백엔드 (Python FastAPI)
- **포트**: 8000
- **주요 기능**:
  - JWT 기반 사용자 인증 시스템
  - 사용자별 워크스페이스 관리
  - Jupyter Lab 인스턴스 동적 생성/관리
  - 파일 업로드/다운로드/관리
  - RESTful API 제공

### 프론트엔드 (React + Vite)
- **포트**: 3000
- **주요 기능**:
  - 사용자 인증 UI (로그인/회원가입)
  - 워크스페이스 관리 대시보드
  - 파일 브라우저 (드래그 앤 드롭 지원)
  - Jupyter Lab 임베딩
  - 반응형 디자인 (Tailwind CSS)

### 데이터베이스 (MySQL)
- 사용자 정보 관리
- 워크스페이스 메타데이터
- Jupyter 인스턴스 상태 관리

## 📁 프로젝트 구조

```
jupyter-data-platform/
├── backend/                    # Python FastAPI 백엔드
│   ├── app/
│   │   ├── models/            # SQLAlchemy 모델
│   │   ├── routers/           # API 라우터
│   │   ├── services/          # 비즈니스 로직
│   │   ├── schemas/           # Pydantic 스키마
│   │   ├── utils/             # 유틸리티 함수
│   │   ├── config.py          # 설정 관리
│   │   ├── database.py        # 데이터베이스 연결
│   │   └── main.py            # FastAPI 애플리케이션
│   ├── requirements.txt       # Python 의존성
│   └── .env                   # 환경 변수
├── frontend/                   # React 프론트엔드
│   ├── src/
│   │   ├── components/        # React 컴포넌트
│   │   ├── pages/             # 페이지 컴포넌트
│   │   ├── contexts/          # React Context
│   │   ├── services/          # API 서비스
│   │   ├── types/             # TypeScript 타입
│   │   └── main.tsx           # 애플리케이션 진입점
│   ├── package.json           # Node.js 의존성
│   └── vite.config.ts         # Vite 설정
├── data/                       # 사용자 데이터
│   └── users/                 # 사용자별 워크스페이스
├── start_backend.bat          # 백엔드 실행 스크립트
├── start_frontend.bat         # 프론트엔드 실행 스크립트
├── setup_database.sql         # 데이터베이스 설정
├── INSTALL.md                 # 설치 가이드
└── README.md                  # 프로젝트 문서
```

## 🔧 구현된 핵심 기능

### 1. 사용자 관리
- ✅ JWT 기반 인증 시스템
- ✅ 회원가입/로그인/로그아웃
- ✅ 사용자별 권한 관리
- ✅ 보안 강화 (비밀번호 해싱)

### 2. 워크스페이스 관리
- ✅ 사용자별 독립 워크스페이스 생성
- ✅ 워크스페이스 목록 조회/삭제
- ✅ 자동 폴더 구조 생성 (notebooks/, data/, outputs/)
- ✅ 환영 노트북 자동 생성

### 3. Jupyter 인스턴스 관리
- ✅ 동적 Jupyter Lab 인스턴스 생성
- ✅ 사용자별 포트 할당 (8888-9000)
- ✅ 보안 토큰 생성 및 관리
- ✅ 프로세스 상태 모니터링
- ✅ 인스턴스 시작/중지 제어

### 4. 파일 관리
- ✅ 파일/폴더 목록 조회
- ✅ 다중 파일 업로드 (드래그 앤 드롭)
- ✅ 파일 다운로드
- ✅ 파일/폴더 삭제
- ✅ 새 폴더 생성

### 5. 단계별 실행 결과 저장 및 재사용
- ✅ Jupyter Notebook 셀 단위 실행
- ✅ 실행 결과 .ipynb 파일에 저장
- ✅ 중간 결과 CSV/데이터 파일 저장
- ✅ 다음 노트북에서 이전 결과 재사용

## 🛠️ 사용된 기술 스택

### 백엔드
- **FastAPI**: 고성능 웹 프레임워크
- **SQLAlchemy**: ORM
- **Pydantic**: 데이터 유효성 검사
- **JWT**: 인증 토큰
- **bcrypt**: 비밀번호 암호화
- **Jupyter Lab**: 데이터 분석 환경
- **pandas, numpy, matplotlib**: 데이터 분석 라이브러리

### 프론트엔드
- **React 18**: UI 라이브러리
- **Vite**: 빌드 도구
- **React Router**: 라우팅
- **React Query**: 서버 상태 관리
- **Axios**: HTTP 클라이언트
- **Tailwind CSS**: 스타일링
- **TypeScript**: 타입 안전성

### 데이터베이스
- **MySQL**: 관계형 데이터베이스

## 🚀 실행 방법

### 1. 간편 실행 (Windows)
```bash
# 백엔드 실행
start_backend.bat

# 프론트엔드 실행 (새 터미널)
start_frontend.bat
```

### 2. 수동 실행
```bash
# 백엔드
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# 프론트엔드
cd frontend
npm install
npm start
```

## 🌐 접속 정보
- **웹 애플리케이션**: http://localhost:3000
- **API 서버**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs

## 📋 사용 시나리오

### 1. 사용자 등록 및 로그인
1. 웹사이트 접속 → 회원가입
2. 로그인 → 대시보드 이동

### 2. 워크스페이스 생성
1. "새 워크스페이스" 버튼 클릭
2. 이름과 설명 입력
3. 자동으로 폴더 구조 생성

### 3. 데이터 분석 워크플로우
1. **데이터 업로드**: 파일 브라우저에서 CSV 파일 업로드
2. **Jupyter Lab 시작**: "Jupyter 시작" 버튼 클릭
3. **전처리 노트북**: 
   ```python
   import pandas as pd
   df = pd.read_csv('data/raw_data.csv')
   # 데이터 전처리
   df.to_csv('data/cleaned_data.csv')
   ```
4. **분석 노트북**:
   ```python
   df = pd.read_csv('data/cleaned_data.csv')
   # 데이터 분석 및 시각화
   results.to_csv('outputs/analysis_results.csv')
   ```
5. **결과 다운로드**: 파일 브라우저에서 결과 파일 다운로드

## 🔒 보안 기능
- JWT 토큰 기반 인증
- 비밀번호 bcrypt 해싱
- 사용자별 워크스페이스 격리
- Jupyter 토큰 보안
- CORS 설정

## 📈 확장 가능성
- Docker 컨테이너 기반 격리
- Kubernetes 클러스터 배포
- 리소스 사용량 모니터링
- 다중 Python 환경 지원
- 협업 기능 추가

## ✅ 상업적 무료 사용
모든 사용된 라이브러리와 프레임워크는 상업적으로 무료 사용이 가능한 오픈소스입니다.

## 🎉 구현 완료 상태
이 프로젝트는 기획서의 1단계 MVP(Minimum Viable Product)가 완전히 구현되었으며, 즉시 사용 가능한 상태입니다. 사용자는 웹 브라우저를 통해 개인 Jupyter 환경에 접속하여 데이터 분석 작업을 수행할 수 있습니다. 