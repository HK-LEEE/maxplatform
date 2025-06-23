# MAX (Manufacturing Artificial Intelligence & DX)

**MAX**는 제조업을 위한 차세대 AI 및 디지털 트랜스포메이션 플랫폼입니다.

## 🚀 주요 기능

### 🔧 Flow Studio
- **드래그 앤 드롭 워크플로우 빌더**: 직관적인 인터페이스로 AI 워크플로우 구성
- **프로젝트 기반 관리**: 체계적인 플로우 프로젝트 관리
- **실시간 실행**: 구성한 워크플로우의 즉시 실행 및 결과 확인
- **컴포넌트 라이브러리**: 다양한 AI 모델 및 데이터 처리 컴포넌트

### 🗃️ RAG 데이터소스
- **벡터 데이터베이스 관리**: ChromaDB 기반 문서 임베딩 및 검색
- **문서 업로드**: PDF, TXT, DOCX 등 다양한 형식 지원
- **하이브리드 검색**: 의미 검색과 키워드 검색의 결합
- **권한 관리**: 개인/그룹 기반 데이터소스 접근 제어

### 🤖 LLMOps
- **다중 LLM 지원**: OpenAI, Anthropic, Ollama 등 다양한 모델
- **모델 관리**: API 키 및 설정 중앙 관리
- **실행 기록**: 모든 AI 작업의 추적 및 로깅
- **성능 모니터링**: 응답 시간, 토큰 사용량 등 메트릭

## 🎨 2024-2025 UI 트렌드 적용

### 색상 팔레트
- **Future Dusk** (#4C5578): 깊이 있는 보라빛 회색 - 메인 브랜드 컬러
- **Celestial Yellow** (#EDEAB1): 따뜻한 노란색 - 액센트 컬러
- **Retro Blue** (#71ADBA): 빈티지 블루 - 보조 컬러
- **Off-white** (#FAFAFA): 부드러운 배경색으로 눈의 피로 감소

### 현대적 디자인 요소
- **Soft Shadows**: 부드러운 그림자로 깊이감 표현
- **Rounded Corners**: 12px 라운드 코너로 친근한 느낌
- **Gradient Backgrounds**: 그라데이션으로 시각적 흥미 증대
- **Smooth Animations**: 0.2초 트랜지션으로 부드러운 상호작용

## 🛠️ 기술 스택

### Frontend
- **React 18** + TypeScript
- **Tailwind CSS** (2024-2025 트렌드 색상 적용)
- **React Flow** (워크플로우 빌더)
- **React Query** (상태 관리)
- **Lucide React** (아이콘)

### Backend
- **FastAPI** (Python)
- **PostgreSQL** (메인 데이터베이스)
- **ChromaDB** (벡터 데이터베이스)
- **SQLAlchemy** (ORM)
- **Pydantic** (데이터 검증)

### AI/ML
- **OpenAI GPT** 모델
- **Anthropic Claude** 모델
- **Ollama** (로컬 LLM)
- **Sentence Transformers** (임베딩)

## 🚀 빠른 시작

### 1. 저장소 클론
```bash
git clone https://github.com/your-org/MAX.git
cd MAX
```

### 2. 백엔드 설정
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일에서 데이터베이스 및 API 키 설정

# 데이터베이스 마이그레이션
alembic upgrade head

# 서버 실행
uvicorn app.main:app --reload --port 8000
```

### 3. 프론트엔드 설정
```bash
cd frontend
npm install
npm start
```

### 4. 접속
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs

## 📁 프로젝트 구조

```
MAX/
├── frontend/                 # React 프론트엔드
│   ├── src/
│   │   ├── components/      # 재사용 가능한 컴포넌트
│   │   ├── pages/          # 페이지 컴포넌트
│   │   ├── services/       # API 서비스
│   │   └── types/          # TypeScript 타입 정의
│   └── tailwind.config.js  # Tailwind 설정 (트렌드 색상 포함)
├── backend/                 # FastAPI 백엔드
│   ├── app/
│   │   ├── models/         # 데이터베이스 모델
│   │   ├── routers/        # API 라우터
│   │   ├── services/       # 비즈니스 로직
│   │   └── schemas/        # Pydantic 스키마
│   └── alembic/            # 데이터베이스 마이그레이션
└── docs/                   # 프로젝트 문서
```

## 🔧 주요 설정

### 환경 변수 (.env)
```env
# 데이터베이스
DATABASE_URL=postgresql://user:password@localhost/mai_x

# AI 모델 API 키
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# ChromaDB
CHROMA_HOST=localhost
CHROMA_PORT=8000

# JWT 설정
SECRET_KEY=your_secret_key
ALGORITHM=HS256
```

## 🎯 로드맵

### Phase 1 (현재)
- ✅ Flow Studio 기본 기능
- ✅ RAG 데이터소스 관리
- ✅ 다중 LLM 지원
- ✅ 2024-2025 UI 트렌드 적용

### Phase 2 (계획)
- 🔄 고급 워크플로우 템플릿
- 🔄 실시간 협업 기능
- 🔄 모델 파인튜닝 지원
- 🔄 고급 분석 대시보드

### Phase 3 (미래)
- 📋 제조업 특화 AI 모델
- 📋 IoT 데이터 통합
- 📋 예측 유지보수
- 📋 품질 관리 자동화

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 📞 연락처

- **프로젝트 링크**: [https://github.com/your-org/MAX](https://github.com/your-org/MAX)
- **이슈 리포트**: [https://github.com/your-org/MAX/issues](https://github.com/your-org/MAX/issues)

---

**MAX** - Manufacturing의 미래를 AI와 함께 만들어갑니다. 🚀
